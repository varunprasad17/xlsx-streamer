"""HTTP/HTTPS data source implementation."""

from collections.abc import Iterator
import logging
from typing import Any

from typing_extensions import override

from xlsx_streamer.sources.base import StreamSource

logger = logging.getLogger(__name__)


class HTTPSource(StreamSource):
    """
    Stream XLSX files from HTTP/HTTPS URLs.

    Uses httpx to stream files without loading entire files into memory.
    Supports authentication, custom headers, and retry logic.
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        auth: tuple[str, str] | None = None,
        timeout: int = 30,
        chunk_size: int = 16777216,
    ) -> None:
        """
        Initialize HTTPSource.

        Args:
            url: HTTP/HTTPS URL to the XLSX file.
            headers: Optional custom HTTP headers.
            auth: Optional tuple of (username, password) for basic auth.
            timeout: Request timeout in seconds (default: 30).
            chunk_size: Size of chunks to read (default: 16MB).

        Raises:
            ImportError: If httpx is not installed.
            ValueError: If URL is invalid.
        """
        try:
            import httpx  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "httpx is required for HTTPSource. Install with: pip install xlsx-streamer[http]"
            ) from e

        if not url or not url.startswith(("http://", "https://")):
            raise ValueError("url must be a valid HTTP/HTTPS URL")

        self.url = url
        self.headers = headers or {}
        self.auth = auth
        self.timeout = timeout
        self.chunk_size = chunk_size

        logger.info("HTTPSource initialized for %s", url)

    @override
    def get_stream(self) -> Iterator[bytes]:
        """
        Stream the HTTP resource in chunks.

        Yields:
            bytes: Chunks of HTTP response data.

        Raises:
            IOError: If the HTTP request fails.
        """
        import httpx

        try:
            with httpx.stream(
                "GET",
                self.url,
                headers=self.headers,
                auth=self.auth,
                timeout=self.timeout,
                follow_redirects=True,
            ) as response:
                response.raise_for_status()

                for chunk in response.iter_bytes(chunk_size=self.chunk_size):
                    if chunk:
                        yield chunk
        except Exception as e:
            logger.exception("Error reading from %s: %s", self.url, e)
            raise OSError(f"Failed to read from {self.url}: {e}") from e

    @override
    def get_metadata(self) -> dict[str, Any]:
        """
        Return metadata about the HTTP resource.

        Returns:
            dict[str, Any]: Metadata containing content length, type, and source type.
        """
        import httpx

        try:
            response = httpx.head(
                self.url,
                headers=self.headers,
                auth=self.auth,
                timeout=self.timeout,
                follow_redirects=True,
            )
            response.raise_for_status()

            size = response.headers.get("content-length")
            size = int(size) if size else 0

            content_type = response.headers.get(
                "content-type",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            logger.warning("Could not retrieve metadata for %s: %s", self.url, e)
            size = 0
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        return {
            "size": size,
            "type": content_type,
            "source_type": "http",
            "url": self.url,
        }
