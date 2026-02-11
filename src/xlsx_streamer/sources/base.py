"""Abstract base class for streaming data sources."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any


class StreamSource(ABC):
    """
    Abstract base class for streaming data sources.

    Provides a unified interface for reading from different sources (S3, HTTP, local files)
    without loading entire files into memory.
    """

    @abstractmethod
    def get_stream(self) -> Iterator[bytes]:
        """
        Return an iterator of byte chunks from the source.

        This method should yield byte chunks of configurable size.
        Must not load the entire file into memory.

        Yields:
            bytes: Chunks of data from the source.

        Raises:
            IOError: If the source cannot be read.
        """
        ...

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """
        Return metadata about the source.

        Returns:
            dict[str, Any]: Metadata dictionary containing:
                - 'size': File size in bytes (if available)
                - 'type': MIME type (default:
                  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                - 'source_type': Type of source ('s3', 'http', 'local')
        """
        ...
