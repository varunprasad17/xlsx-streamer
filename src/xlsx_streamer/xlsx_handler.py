import csv
import io
import logging
from typing import Any

from xlsx_streamer.sources.base import StreamSource
from xlsx_streamer.xlsx_generator import StreamingXlsxReader
from xlsx_streamer.xlsx_metadata_extractor import XLSXMetadataExtractor

logger = logging.getLogger(__name__)


class XlsxHandler:
    """
    Orchestrate XLSX streaming from any source.

    Coordinates metadata extraction and row-level streaming
    using a source-agnostic interface.
    """

    def __init__(
        self,
        source: StreamSource,
        sheet_name: str | None = None,
        chunk_size: int = 16777216,
    ) -> None:
        """
        Initialize the XLSX handler.

        Args:
            source: StreamSource instance for reading the XLSX file.
            sheet_name: Name of the sheet to read (default: first sheet).
            chunk_size: Size of chunks for processing (default: 16MB).
        """
        self.source = source
        self.sheet_name = sheet_name
        self.chunk_size = chunk_size
        self.delimiter = ","
        self.quotechar = '"'

        logger.info(
            "XlsxHandler initialized (source=%s, sheet=%s, chunk_size=%d)",
            source.get_metadata().get("source_type"),
            sheet_name,
            chunk_size,
        )

    def _row_to_bytes(self, row: list[Any]) -> bytes:
        """
        Convert a list of row values into a CSV byte chunk.

        Args:
            row: List of cell values.

        Returns:
            bytes: CSV-formatted row as bytes.
        """
        values = [str(value) if value is not None else "" for value in row]

        # Use an in-memory string buffer and csv.writer
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.delimiter, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(values)

        return output.getvalue().encode("utf-8")

    def stream_rows(self) -> Any:
        """
        Stream rows from the XLSX file as bytes.

        Yields:
            bytes: CSV-formatted row bytes.

        Raises:
            IOError: If the XLSX file cannot be read or parsed.
        """
        try:
            # 1. Extract Metadata
            logger.info("Extracting metadata for sheet: %s", self.sheet_name)
            extractor = XLSXMetadataExtractor(self.source)

            shared_strings_list, target_worksheet_filepath = extractor.extract_metadata(
                sheet_name=self.sheet_name
            )

            logger.info(
                "Metadata extracted: %d shared strings, worksheet path: %s",
                len(shared_strings_list),
                target_worksheet_filepath,
            )

            # 2. Stream Rows using the extracted metadata
            logger.info("Initializing row streaming")
            reader = StreamingXlsxReader(
                source=self.source,
                target_worksheet_filepath=target_worksheet_filepath,
                chunk_size=self.chunk_size,
            )

            row_count = 0
            for row_values in reader.stream_rows(shared_strings_list):
                row_count += 1
                if row_count % 10000 == 0:
                    logger.info("Processed %d rows", row_count)

                # Convert the row of values into a CSV byte chunk
                chunk = self._row_to_bytes(row_values)
                yield chunk

            logger.info("Completed streaming %d rows", row_count)

        except Exception as e:
            logger.exception("Error streaming rows: %s", e)
            raise OSError(f"Failed to stream XLSX rows: {e}") from e
