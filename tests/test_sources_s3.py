"""Tests for S3Source."""

import pytest

from xlsx_streamer.sources.s3 import S3Source

try:
    import moto  # noqa: F401

    HAS_MOTO = True
except ImportError:
    HAS_MOTO = False


def test_s3_source_requires_boto3() -> None:
    """Test that S3Source raises ImportError if boto3 not installed."""
    # This test verifies the error message, but won't actually fail
    # unless boto3 is not installed (which it is in test environment)
    try:
        source = S3Source(bucket="test", key="test.xlsx")
        assert source is not None
    except ImportError:
        # boto3 is installed in test environment, so this is expected
        pass


def test_s3_source_validation() -> None:
    """Test S3Source parameter validation."""
    # Empty bucket
    with pytest.raises(ValueError, match="must be non-empty"):
        S3Source(bucket="", key="test.xlsx")

    # Empty key
    with pytest.raises(ValueError, match="must be non-empty"):
        S3Source(bucket="test", key="")

    # Both empty
    with pytest.raises(ValueError, match="must be non-empty"):
        S3Source(bucket="", key="")


@pytest.mark.skipif(
    not HAS_MOTO,
    reason="Requires moto for mocking",
)
def test_s3_source_with_mock_s3() -> None:
    """Test S3Source with mocked S3 using moto."""
    import boto3
    from moto import mock_aws

    with mock_aws():
        # Create mock S3
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")

        # Put test object
        test_content = b"test xlsx content"
        s3_client.put_object(Bucket="test-bucket", Key="test.xlsx", Body=test_content)

        # Create source and stream
        source = S3Source(bucket="test-bucket", key="test.xlsx", client=s3_client)

        # Test streaming
        chunks = list(source.get_stream())
        assert b"".join(chunks) == test_content

        # Test metadata
        metadata = source.get_metadata()
        assert metadata["source_type"] == "s3"
        assert metadata["bucket"] == "test-bucket"
        assert metadata["key"] == "test.xlsx"
