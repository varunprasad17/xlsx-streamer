from enum import Enum
import logging
from typing import Any
import xml.etree.ElementTree as ET

from stream_unzip import stream_unzip

from xlsx_streamer.sources.base import StreamSource


class XLSXMetadataExtractor:
    """
    Efficiently extract metadata from XLSX files using streaming.

    Extracts shared strings and target worksheet path in a single pass
    without loading large sheet data files into memory.
    """

    class XlsxMetadataPaths(Enum):
        """Standard file paths for core XLSX metadata components."""

        WORKBOOK = "xl/workbook.xml"
        SHARED_STRINGS = "xl/sharedStrings.xml"
        WORKBOOK_RELS = "xl/_rels/workbook.xml.rels"
        DEFAULT_WORKSHEET = "xl/worksheets/sheet1.xml"

    class XlsxNamespaces(Enum):
        """Standard XML namespace URIs used in XLSX files."""

        MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

    def __init__(self, source: StreamSource) -> None:
        """
        Initialize the metadata extractor.

        Args:
            source: StreamSource instance for reading the XLSX file.

        Raises:
            IOError: If the source stream cannot be opened.
        """
        self.source = source
        logging.debug(
            "XLSXMetadataExtractor initialized for source type: %s",
            source.get_metadata().get("source_type"),
        )

    def _parse_workbook_xml(self, chunks: list[bytes], sheet_name: str) -> str | None:
        """
        Parses xl/workbook.xml to find the r:id of the sheet matching the name.
        """
        xml_data = b"".join(chunks)
        if not xml_data:
            return None

        try:
            root = ET.fromstring(xml_data)

            main_namespace = self.XlsxNamespaces.MAIN.value
            rel_namespace = self.XlsxNamespaces.REL.value
            # Search for the sheet element by iterating and matching name attribute
            # This avoids XPath injection vulnerabilities
            sheets_element = root.find(f"{{{main_namespace}}}sheets")
            if sheets_element is not None:
                for sheet_element in sheets_element.findall(f"{{{main_namespace}}}sheet"):
                    if sheet_element.get("name") == sheet_name:
                        # The 'r' prefix is defined as r:id="rId1", so we still need to
                        # get the attribute
                        # using the full namespace URI (REL_NS).
                        return sheet_element.get(f"{{{rel_namespace}}}id")

        except ET.ParseError as e:
            logging.exception(f"Error parsing {self.XlsxMetadataPaths.WORKBOOK.value}: {e}")

        return None

    def _parse_rels_xml(self, chunks: list[bytes], r_id: str) -> str | None:
        """
        Parses xl/_rels/workbook.xml.rels to map the r:id to the target file path.
        Returns the path relative to xl/, e.g., 'worksheets/sheet1.xml'.
        """
        xml_data = b"".join(chunks)
        if not xml_data:
            return None

        try:
            root = ET.fromstring(xml_data)

            rel_namespace = "http://schemas.openxmlformats.org/package/2006/relationships"

            # Find the relationship element by Id
            target_rel_element = root.find(f'{{{rel_namespace}}}Relationship[@Id="{r_id}"]')

            if target_rel_element is not None:
                target = target_rel_element.get("Target")
                return target if target else None

        except ET.ParseError as e:
            logging.exception(f"Error parsing {self.XlsxMetadataPaths.WORKBOOK_RELS.value}: {e}")

        return None

    def _parse_shared_strings_xml(self, chunk_iter: Any) -> list[str]:
        """
        Stream-parses xl/sharedStrings.xml directly from an iterator of byte chunks.
        Avoids loading the full file into memory.
        """
        shared_strings: list[str] = []
        parser = ET.XMLPullParser(events=("end",))

        try:
            for chunk in chunk_iter:
                parser.feed(chunk)
                while True:
                    try:
                        event_elem = next(parser.read_events())
                    except StopIteration:
                        break
                    if not isinstance(event_elem, tuple) or len(event_elem) != 2:
                        continue
                    event, elem = event_elem
                    # Only process if elem is an Element
                    if not isinstance(elem, ET.Element):
                        continue
                    if event == "end" and elem.tag.endswith("si"):
                        text_parts = [
                            t.text
                            for t in elem.iter()
                            if isinstance(t, ET.Element) and t.tag.endswith("t") and t.text
                        ]
                        shared_strings.append("".join(text_parts))
                        elem.clear()
        except ET.ParseError as e:
            logging.exception(f"Error parsing {self.XlsxMetadataPaths.SHARED_STRINGS.value}: {e}")

        return shared_strings

    def extract_metadata(self, sheet_name: str | None) -> tuple[list[str], str]:
        """
        Extract shared strings and target worksheet path from XLSX.

        Efficiently streams the XLSX file to extract metadata in a single pass.

        Args:
            sheet_name: The human-readable name of the sheet to target
                        (e.g., "Invoice Data"). If None, defaults to first sheet.

        Returns:
            A tuple: (shared_strings_list, target_worksheet_filepath).
            - shared_strings_list: list[str] containing shared strings, indexed by ID.
            - target_worksheet_filepath: str (e.g., 'xl/worksheets/sheet3.xml').

        Raises:
            ValueError: If the required metadata files are missing or the sheet
                        name cannot be resolved.
        """
        # Storage for the chunks of the three required metadata files
        workbook_chunks: list[bytes] = []
        rels_chunks: list[bytes] = []
        shared_strings_list: list[str] = []

        if not sheet_name:
            logging.warning("Sheet name not provided, using first sheet")

        # Stream through the ZIP content once using stream_unzip
        for file_name, _, chunks in stream_unzip(self.source.get_stream()):
            try:
                file_name_str = file_name.decode("utf-8")
            except UnicodeDecodeError:
                continue

            if file_name_str == self.XlsxMetadataPaths.SHARED_STRINGS.value:
                shared_strings_list = self._parse_shared_strings_xml(chunks)
            # Only collect workbook and rels if a sheet name is provided for lookup
            elif sheet_name and file_name_str == self.XlsxMetadataPaths.WORKBOOK.value:
                workbook_chunks.extend(chunks)
            elif sheet_name and file_name_str == self.XlsxMetadataPaths.WORKBOOK_RELS.value:
                rels_chunks.extend(chunks)
            else:
                # Consume chunks for all other files to proceed quickly
                for _ in chunks:
                    pass

        # Process the collected metadata
        logging.debug("Metadata extracted, processing...")

        if not sheet_name:
            logging.warning("Using default first sheet")
            return (shared_strings_list, self.XlsxMetadataPaths.DEFAULT_WORKSHEET.value)

        # Step 1: Find r:id (relationship ID) from xl/workbook.xml
        r_id = self._parse_workbook_xml(workbook_chunks, sheet_name)

        target_filepath = None
        if r_id:
            # Step 2: Map r:id to internal file path from xl/_rels/workbook.xml.rels
            relative_path = self._parse_rels_xml(rels_chunks, r_id)

            if relative_path:
                # The full path is relative_path, prepended with 'xl/'
                cleaned_path = relative_path.lstrip("/").lstrip("xl/")
                target_filepath = f"xl/{cleaned_path}"

        if not target_filepath:
            raise ValueError(f"Sheet '{sheet_name}' not found in workbook or metadata missing")

        return shared_strings_list, target_filepath
