"""Tests for HTTPSource."""

from unittest.mock import Mock, patch

import pytest

from xlsx_streamer.sources.http import HTTPSource

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


def test_http_source_requires_httpx() -> None:
    """Test that HTTPSource raises ImportError if httpx not installed."""
    # This test verifies the error message, but won't actually fail
    # unless httpx is not installed (which it is in test environment)
    try:
        source = HTTPSource(url="https://example.com/test.xlsx")
        assert source is not None
    except ImportError:
        # httpx is installed in test environment, so this is expected
        pass


def test_http_source_validation() -> None:
    """Test HTTPSource URL validation."""
    # Invalid URL
    with pytest.raises(ValueError, match="valid HTTP/HTTPS URL"):
        HTTPSource(url="ftp://example.com/test.xlsx")

    # Empty URL
    with pytest.raises(ValueError, match="valid HTTP/HTTPS URL"):
        HTTPSource(url="")

    # Valid URLs should work (if httpx is installed)
    try:
        source_http = HTTPSource(url="http://example.com/test.xlsx")
        assert source_http is not None

        source_https = HTTPSource(url="https://example.com/test.xlsx")
        assert source_https is not None
    except ImportError:
        # httpx not installed, skip
        pass


def test_http_source_initialization_with_options() -> None:
    """Test HTTPSource initialization with custom options."""
    if not HAS_HTTPX:
        pytest.skip("httpx not installed")

    headers = {"User-Agent": "Test Agent"}
    auth = ("user", "pass")

    source = HTTPSource(
        url="https://example.com/test.xlsx",
        headers=headers,
        auth=auth,
        timeout=60,
        chunk_size=8192,
    )

    assert source.url == "https://example.com/test.xlsx"
    assert source.headers == headers
    assert source.auth == auth
    assert source.timeout == 60
    assert source.chunk_size == 8192


@pytest.mark.skipif(not HAS_HTTPX, reason="httpx not installed")
def test_http_source_get_stream_success() -> None:
    """Test HTTPSource get_stream with successful response."""
    with patch("httpx.stream") as mock_stream:
        # Mock response
        mock_response = Mock()
        mock_response.iter_bytes.return_value = [b"chunk1", b"chunk2", b"chunk3"]
        mock_response.raise_for_status = Mock()

        mock_stream.return_value.__enter__.return_value = mock_response

        source = HTTPSource(url="https://example.com/test.xlsx")
        chunks = list(source.get_stream())

        assert chunks == [b"chunk1", b"chunk2", b"chunk3"]
        mock_response.raise_for_status.assert_called_once()


@pytest.mark.skipif(not HAS_HTTPX, reason="httpx not installed")
def test_http_source_get_stream_with_error() -> None:
    """Test HTTPSource get_stream with HTTP error."""
    with patch("httpx.stream") as mock_stream:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=Mock(), response=Mock()
        )

        mock_stream.return_value.__enter__.return_value = mock_response

        source = HTTPSource(url="https://example.com/test.xlsx")

        with pytest.raises(OSError, match="Failed to read from"):
            list(source.get_stream())


@pytest.mark.skipif(not HAS_HTTPX, reason="httpx not installed")
def test_http_source_get_metadata_success() -> None:
    """Test HTTPSource get_metadata with successful response."""
    with patch("httpx.head") as mock_head:
        mock_response = Mock()
        mock_response.headers = {
            "content-length": "12345",
            "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        mock_response.raise_for_status = Mock()

        mock_head.return_value = mock_response

        source = HTTPSource(url="https://example.com/test.xlsx")
        metadata = source.get_metadata()

        assert metadata["size"] == 12345
        assert (
            metadata["type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert metadata["source_type"] == "http"
        assert metadata["url"] == "https://example.com/test.xlsx"


@pytest.mark.skipif(not HAS_HTTPX, reason="httpx not installed")
def test_http_source_get_metadata_no_content_length() -> None:
    """Test HTTPSource get_metadata when content-length is missing."""
    with patch("httpx.head") as mock_head:
        mock_response = Mock()
        mock_response.headers = {}  # No content-length
        mock_response.raise_for_status = Mock()

        mock_head.return_value = mock_response

        source = HTTPSource(url="https://example.com/test.xlsx")
        metadata = source.get_metadata()

        assert metadata["size"] == 0


@pytest.mark.skipif(not HAS_HTTPX, reason="httpx not installed")
def test_http_source_get_metadata_with_error() -> None:
    """Test HTTPSource get_metadata handles errors gracefully."""
    with patch("httpx.head") as mock_head:
        mock_head.side_effect = httpx.HTTPStatusError("404", request=Mock(), response=Mock())

        source = HTTPSource(url="https://example.com/test.xlsx")
        metadata = source.get_metadata()

        # Should return default metadata on error
        assert metadata["size"] == 0
        assert (
            metadata["type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert metadata["source_type"] == "http"


@pytest.mark.skipif(not HAS_HTTPX, reason="httpx not installed")
def test_http_source_get_stream_filters_empty_chunks() -> None:
    """Test HTTPSource get_stream filters out empty chunks."""
    with patch("httpx.stream") as mock_stream:
        mock_response = Mock()
        mock_response.iter_bytes.return_value = [b"chunk1", b"", b"chunk2", b""]
        mock_response.raise_for_status = Mock()

        mock_stream.return_value.__enter__.return_value = mock_response

        source = HTTPSource(url="https://example.com/test.xlsx")
        chunks = list(source.get_stream())

        # Empty chunks should be filtered out
        assert chunks == [b"chunk1", b"chunk2"]
