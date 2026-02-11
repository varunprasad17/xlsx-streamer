"""Unified public API for reading XLSX files from any source."""

from collections.abc import Iterator
import csv
import io
import logging
from pathlib import Path
from typing import Any, BinaryIO, TextIO
from urllib.parse import urlparse

from xlsx_streamer.sources.base import StreamSource
from xlsx_streamer.sources.http import HTTPSource
from xlsx_streamer.sources.local import LocalFileSource
from xlsx_streamer.sources.s3 import S3Source
from xlsx_streamer.xlsx_handler import XlsxHandler

logger = logging.getLogger(__name__)


class XLSXReader:
    """
    Unified XLSX reader supporting multiple data sources.

    Provides a simple, intuitive API for reading XLSX files from S3, HTTP, or local
    filesystem. Automatically detects source type from URI or accepts explicit StreamSource.
    """

    def __init__(
        self,
        source: str | StreamSource,
        sheet_name: str | None = None,
        chunk_size: int = 16777216,
        **source_options: Any,
    ) -> None:
        """
        Initialize the XLSX reader.

        Args:
            source: Data source. Can be:
                - StreamSource instance
                - S3 URI: 's3://bucket/key'
                - HTTP URL: 'https://example.com/file.xlsx'
                - Local path: '/path/to/file.xlsx'
            sheet_name: Name of the sheet to read (default: first sheet).
            chunk_size: Size of chunks to read from source (default: 16MB).
            **source_options: Additional options for specific source types:
                - For S3: client, region, profile, access_key, secret_key
                - For HTTP: headers, auth, timeout
                - For local files: (none)

        Raises:
            ValueError: If source format is invalid.
            ImportError: If required libraries are not installed.
        """
        # Resolve the source if it's a string
        if isinstance(source, str):
            self.source = self._create_source(source, chunk_size, source_options)
        else:
            self.source = source

        self.sheet_name = sheet_name
        self.chunk_size = chunk_size
        self.handler = XlsxHandler(
            source=self.source,
            sheet_name=sheet_name,
            chunk_size=chunk_size,
        )

        logger.info(
            "XLSXReader initialized (source=%s, sheet=%s)",
            self.source.get_metadata().get("source_type"),
            sheet_name,
        )

    @staticmethod
    def _create_source(
        source_str: str,
        chunk_size: int,
        options: dict[str, Any],
    ) -> StreamSource:
        """
        Create a StreamSource from a URI string.

        Args:
            source_str: Source URI (s3://, http://, https://, or local path)
            chunk_size: Default chunk size for streaming
            options: Source-specific options

        Returns:
            StreamSource: Appropriate source implementation

        Raises:
            ValueError: If URI format is not recognized
        """
        # Try to parse as URI
        parsed = urlparse(source_str)

        if parsed.scheme == "s3":
            # S3 URI: s3://bucket/key
            bucket = parsed.netloc
            key = parsed.path.lstrip("/")

            if not bucket or not key:
                raise ValueError(f"Invalid S3 URI: {source_str}. Expected: s3://bucket/key")

            logger.info("Creating S3Source for s3://%s/%s", bucket, key)
            return S3Source(
                bucket=bucket,
                key=key,
                chunk_size=chunk_size,
                **{k: v for k, v in options.items() if k in ("client", "region", "profile")},
            )

        elif parsed.scheme in ("http", "https"):
            # HTTP/HTTPS URL
            logger.info("Creating HTTPSource for %s", source_str)
            return HTTPSource(
                url=source_str,
                chunk_size=chunk_size,
                **{k: v for k, v in options.items() if k in ("headers", "auth", "timeout")},
            )

        else:
            # Assume local file path
            logger.info("Creating LocalFileSource for %s", source_str)
            return LocalFileSource(
                file_path=source_str,
                chunk_size=chunk_size,
            )

    def stream_rows(self) -> Iterator[list[Any]]:
        """
        Stream rows from the XLSX file.

        Each row is a list of cell values. Empty cells are represented as empty strings.

        Yields:
            list[Any]: Row data as list of cell values.

        Raises:
            IOError: If the XLSX file cannot be read.
        """
        for row_bytes in self.handler.stream_rows():
            # Parse CSV bytes back to list
            row_str = row_bytes.decode("utf-8").strip()
            if row_str:
                reader = csv.reader(io.StringIO(row_str))
                row = next(reader, [])
                yield row

    def to_csv(self, output: str | BinaryIO | TextIO) -> None:
        """
        Convert XLSX to CSV format and write to output.

        Args:
            output: Output destination. Can be:
                - File path (str): writes to file
                - Binary file object: writes bytes
                - Text file object: writes strings

        Raises:
            IOError: If output cannot be written.
        """
        try:
            # Determine output mode
            if isinstance(output, str):
                # File path - open for writing
                with Path(output).open("w", encoding="utf-8", newline="") as f:
                    for row_bytes in self.handler.stream_rows():
                        row_str = row_bytes.decode("utf-8")
                        f.write(row_str)
            elif isinstance(output, BinaryIO):
                # Binary file object
                for row_bytes in self.handler.stream_rows():
                    output.write(row_bytes)
            else:
                # Text file object
                for row_bytes in self.handler.stream_rows():
                    row_str = row_bytes.decode("utf-8")
                    output.write(row_str)

            logger.info("CSV conversion complete")

        except Exception as e:
            logger.exception("Error converting to CSV: %s", e)
            raise OSError(f"Failed to convert to CSV: {e}") from e

    def get_metadata(self) -> dict[str, Any]:
        """
        Get metadata about the XLSX source.

        Returns:
            dict[str, Any]: Source metadata including size, type, and source type.
        """
        return self.source.get_metadata()
