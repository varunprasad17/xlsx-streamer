"""AWS S3 data source implementation."""

from collections.abc import Iterator
import logging
from typing import Any

from typing_extensions import override

from xlsx_streamer.sources.base import StreamSource

logger = logging.getLogger(__name__)


class S3Source(StreamSource):
    """
    Stream XLSX files from AWS S3.

    Uses boto3 S3 client to stream files without loading entire files into memory.
    """

    def __init__(
        self,
        bucket: str,
        key: str,
        client: Any = None,
        chunk_size: int = 16777216,
    ) -> None:
        """
        Initialize S3Source.

        Args:
            bucket: S3 bucket name.
            key: S3 object key (file path).
            client: Boto3 S3 client instance. If None, will create default client.
            chunk_size: Size of chunks to read from S3 (default: 16MB).

        Raises:
            ImportError: If boto3 is not installed.
            ValueError: If bucket or key is empty.
        """
        try:
            import boto3
        except ImportError as e:
            raise ImportError(
                "boto3 is required for S3Source. Install with: pip install xlsx-streamer[s3]"
            ) from e

        if not bucket or not key:
            raise ValueError("bucket and key must be non-empty")

        self.bucket = bucket
        self.key = key
        self.chunk_size = chunk_size
        self.client = client or boto3.client("s3")

        logger.info("S3Source initialized for s3://%s/%s", bucket, key)

    @override
    def get_stream(self) -> Iterator[bytes]:
        """
        Stream the S3 object in chunks.

        Yields:
            bytes: Chunks of S3 object data.

        Raises:
            IOError: If the S3 object cannot be read.
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self.key)
            stream = response["Body"]

            while True:
                chunk = stream.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk
        except Exception as e:
            logger.exception("Error reading S3 object s3://%s/%s: %s", self.bucket, self.key, e)
            raise OSError(f"Failed to read S3 object s3://{self.bucket}/{self.key}: {e}") from e

    @override
    def get_metadata(self) -> dict[str, Any]:
        """
        Return metadata about the S3 object.

        Returns:
            dict[str, Any]: Metadata containing object size, type, and source type.
        """
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=self.key)
            size = response.get("ContentLength", 0)
            content_type = response.get(
                "ContentType",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            logger.warning(
                "Could not retrieve metadata for s3://%s/%s: %s",
                self.bucket,
                self.key,
                e,
            )
            size = 0
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        return {
            "size": size,
            "type": content_type,
            "source_type": "s3",
            "bucket": self.bucket,
            "key": self.key,
        }
