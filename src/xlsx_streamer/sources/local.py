"""Local file system data source implementation."""

from collections.abc import Iterator
import logging
from pathlib import Path
from typing import Any

from typing_extensions import override

from xlsx_streamer.sources.base import StreamSource

logger = logging.getLogger(__name__)


class LocalFileSource(StreamSource):
    """
    Stream XLSX files from the local file system.

    Reads files in configurable chunks without loading entire files into memory.
    """

    def __init__(self, file_path: str, chunk_size: int = 16777216) -> None:
        """
        Initialize LocalFileSource.

        Args:
            file_path: Path to the local XLSX file.
            chunk_size: Size of chunks to read (default: 16MB).

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file path is invalid.
        """
        self.file_path = Path(file_path)
        self.chunk_size = chunk_size

        # Validate file exists and is a file
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self.file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        logger.info("LocalFileSource initialized for: %s", self.file_path)

    @override
    def get_stream(self) -> Iterator[bytes]:
        """
        Stream the file in chunks.

        Yields:
            bytes: Chunks of file data.

        Raises:
            IOError: If the file cannot be read.
        """
        try:
            with self.file_path.open("rb") as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            logger.exception("Error reading file %s: %s", self.file_path, e)
            raise OSError(f"Failed to read file {self.file_path}: {e}") from e

    @override
    def get_metadata(self) -> dict[str, Any]:
        """
        Return metadata about the local file.

        Returns:
            dict[str, Any]: Metadata containing file size, type, and source type.
        """
        try:
            size = self.file_path.stat().st_size
        except OSError:
            size = 0

        return {
            "size": size,
            "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "source_type": "local",
            "path": str(self.file_path),
        }
