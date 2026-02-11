from collections.abc import Iterator
from enum import Enum
import logging
from typing import Any, BinaryIO, cast, overload
import xml.etree.ElementTree as ET

from stream_unzip import stream_unzip

from xlsx_streamer.sources.base import StreamSource

logger = logging.getLogger(__name__)

# Define a type alias for the row dictionary for clarity
# The key is the column index (int), the value is the cell content (Any)
RowDict = dict[int, Any]


class StreamingXlsxReader:
    """
    Stream-based XLSX reader with minimal memory footprint.

    Parses XLSX files without loading entire files into memory,
    using a source-agnostic interface that works with any StreamSource.
    """

    class XlsxFilePaths(Enum):
        """Standard file paths within an XLSX ZIP archive."""

        DEFAULT_WORKSHEET = "xl/worksheets/sheet1.xml"

    def __init__(
        self,
        source: StreamSource,
        target_worksheet_filepath: str = XlsxFilePaths.DEFAULT_WORKSHEET.value,
        chunk_size: int = 16777216,
    ) -> None:
        """
        Initialize the streaming XLSX reader.

        Args:
            source: StreamSource instance for reading the XLSX file.
            target_worksheet_filepath: Internal path to worksheet XML
                                      (e.g., 'xl/worksheets/sheet1.xml').
            chunk_size: Size of chunks to read from source (default: 16MB).
        """
        self.source = source
        self.chunk_size = chunk_size
        self.worksheet_filepath = target_worksheet_filepath
        logger.debug(
            "StreamingXlsxReader initialized for worksheet: %s", target_worksheet_filepath
        )

    # The _streaming_parse_shared_strings method is removed entirely

    def _streaming_parse_worksheet(
        self,
        chunks: Iterator[bytes],
        shared_strings: list[str],
    ) -> Iterator[list[Any]]:
        """
        Parse worksheet XML using true streaming, using the provided shared_strings.
        """
        # ElementTree.iterparse yields elements which are mutable and should be cleared.
        chunks_stream = IterableToFile(chunks)
        # Cast the object to the expected BinaryIO protocol
        xml_input: BinaryIO = cast(BinaryIO, chunks_stream)
        context = ET.iterparse(xml_input, events=("start", "end"))

        # current_row must be typed as RowDict
        current_row: RowDict = {}
        # current_cell_address can be None initially
        current_cell_address: str | None = None
        # current_cell_type can be None initially
        current_cell_type: str | None = None
        collecting_value: bool = False
        # NEW: Flag to check if we are inside an <is> element for inline text
        collecting_inline_text: bool = False
        current_value_parts: list[str] = []

        for event, elem in context:
            # Efficiently get local tag name without the XML namespace prefix
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            if event == "start":
                if tag == "row":
                    current_row = {}
                elif tag == "c":  # cell
                    current_cell_address = elem.attrib.get("r")
                    current_cell_type = elem.attrib.get("t")
                elif tag == "v" and current_cell_address:  # value for shared string or number
                    collecting_value = True
                    current_value_parts = []
                # NEW LOGIC: Start collecting inline text for <is><t> structure
                elif tag == "is" and current_cell_type == "inlineStr" and current_cell_address:
                    collecting_inline_text = True
                    current_value_parts = []
                elif tag == "t" and collecting_inline_text:
                    pass

            elif event == "end":
                if tag == "v" and collecting_value:
                    # Capture text attached to the closing 'v' element
                    if elem.text is not None:
                        current_value_parts.append(elem.text)

                    # Complete cell value (now correctly includes all parts)
                    cell_value: str | int | float = "".join(current_value_parts)

                    if current_cell_type == "s":  # shared string
                        # Lookup text using the required shared_strings dict
                        try:
                            str_index = int(cell_value)
                        except ValueError:
                            # Handle cases where value is not a valid index
                            str_index = -1

                        # Read the shared strings
                        if str_index >= 0 and str_index < len(shared_strings):
                            cell_value = shared_strings[str_index]
                        else:
                            # Handle out-of-bounds index (shouldn't happen with valid file)
                            cell_value = ""

                    # Numeric/Default type conversion logic (Applies to non-shared strings)
                    elif cell_value and isinstance(
                        cell_value, str
                    ):  # Convert only if its a non empty string
                        try:
                            # Check for float (has decimal) or integer
                            if "." in cell_value:
                                cell_value = float(cell_value)
                            else:
                                cell_value = int(cell_value)
                        except ValueError:
                            # If conversion fails(e.g., cell contained an error string like #N/A),
                            # we keep it as the string value.
                            pass

                    if current_cell_address:
                        # Ensure we convert the address to an integer index
                        col_index: int = self._address_to_index(current_cell_address)
                        current_row[col_index] = cell_value

                    collecting_value = False
                    current_value_parts = []

                # NEW LOGIC: End of the inline string
                elif tag == "is" and collecting_inline_text:
                    # This happens after the nested <t> tag, so the content is already collected
                    # If the type is 'inlineStr', the value is the collected text.

                    inline_value = "".join(current_value_parts)

                    if current_cell_address:
                        column_index: int = self._address_to_index(current_cell_address)
                        current_row[column_index] = inline_value

                    collecting_inline_text = False
                    current_value_parts = []

                elif tag == "row":
                    # Yield completed row
                    if current_row:
                        dense_row = self._sparse_to_dense_row(current_row)
                        yield dense_row
                    current_row = {}

                elif (collecting_value or collecting_inline_text) and elem.text is not None:
                    current_value_parts.append(elem.text)

                # CRITICAL: Free memory after processing
                elem.clear()

    # --------------------------------------------------------------------------

    def stream_rows(self, shared_strings: list[str]) -> Iterator[list[Any]]:
        """
        Stream rows from the target worksheet.

        Yields:
            list[Any]: Each row as a list of cell values.

        Raises:
            IOError: If the source stream cannot be read.
        """
        try:
            # Stream through ZIP once using the source stream
            for file_name, _, chunks in stream_unzip(self.source.get_stream()):
                # file_name is bytes, decode it
                file_name_str = file_name.decode("utf-8")

                if file_name_str == self.worksheet_filepath:
                    # Process the worksheet if found
                    yield from self._streaming_parse_worksheet(chunks, shared_strings)
                else:
                    # Skip other files
                    for _ in chunks:
                        pass
        except Exception as e:
            logger.exception("Error streaming rows: %s", e)
            raise OSError(f"Failed to stream rows: {e}") from e

    def _sparse_to_dense_row(self, sparse_row: dict[int, Any]) -> list[Any]:
        """
        Converts a sparse row dictionary (col_index: value) into a dense list,
        padding missing columns with empty strings.
        """
        if not sparse_row:
            return []

        # 1. Determine the maximum column index to define the required row width.
        # The length of the dense list will be (max_col_index + 1).

        try:
            max_col_index = max(sparse_row.keys())
        except ValueError:
            # Should not happen if 'if not sparse_row' check passes, but for safety.
            return []

        # 2. Initialize the dense list with the appropriate size.
        # This ensures that empty cells are represented as empty strings.
        dense_row = [""] * (max_col_index + 1)

        # 3. Fill the list using the data from the sparse dictionary.
        for col_index, value in sparse_row.items():
            dense_row[col_index] = value
        return dense_row

    def _address_to_index(self, address: str) -> int:
        """Convert Excel address to column index (zero-based)."""
        col_part = "".join(filter(str.isalpha, address.upper()))
        index = 0
        for char in col_part:
            index = index * 26 + (ord(char) - ord("A") + 1)
        return index - 1


class IterableToFile:
    """Wraps an iterator of bytes as a file-like object with a .read() method."""

    # Fix: Added type hints to __init__
    def __init__(self, iterator: Iterator[bytes]) -> None:
        self.iterator = iterator
        self.buffer: bytes = b""

    # Fix: Added overloads for read method to cover size=-1 default
    @overload
    def read(self) -> bytes: ...
    @overload
    def read(self, size: int) -> bytes: ...

    def read(self, size: int = -1) -> bytes:
        """
        Reads up to 'size' bytes from the stream.
        If size is -1, reads all remaining bytes.
        """
        # Fill buffer until we have enough or iterator is exhausted
        while size < 0 or len(self.buffer) < size:
            try:
                # Fix: chunk is bytes
                chunk: bytes = next(self.iterator)
                self.buffer += chunk
            except StopIteration:
                break

        # Determine the result based on 'size'
        if size < 0:
            result, self.buffer = self.buffer, b""
        else:
            result, self.buffer = self.buffer[:size], self.buffer[size:]

        return result
