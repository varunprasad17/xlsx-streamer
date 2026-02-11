"""Tests for LocalFileSource."""

from pathlib import Path
import tempfile

import pytest

from xlsx_streamer.sources.local import LocalFileSource


def test_local_file_source_with_valid_file() -> None:
    """Test LocalFileSource with valid file."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".xlsx") as f:
        f.write(b"test content")
        temp_path = f.name

    try:
        source = LocalFileSource(temp_path, chunk_size=4)
        chunks = list(source.get_stream())

        assert len(chunks) > 0
        assert b"".join(chunks) == b"test content"

        metadata = source.get_metadata()
        assert metadata["source_type"] == "local"
        assert metadata["size"] == 12
        assert "path" in metadata
    finally:
        Path(temp_path).unlink()


def test_local_file_source_with_nonexistent_file() -> None:
    """Test LocalFileSource with nonexistent file."""
    with pytest.raises(FileNotFoundError):
        LocalFileSource("/nonexistent/path/file.xlsx")


def test_local_file_source_with_directory() -> None:
    """Test LocalFileSource with directory path."""
    with tempfile.TemporaryDirectory() as tmpdir, pytest.raises(ValueError, match="not a file"):
        LocalFileSource(tmpdir)


def test_local_file_source_chunking() -> None:
    """Test that LocalFileSource properly chunks data."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".xlsx") as f:
        f.write(b"0123456789")
        temp_path = f.name

    try:
        source = LocalFileSource(temp_path, chunk_size=3)
        chunks = list(source.get_stream())

        assert chunks == [b"012", b"345", b"678", b"9"]
    finally:
        Path(temp_path).unlink()


def test_local_file_source_metadata() -> None:
    """Test LocalFileSource metadata."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".xlsx") as f:
        f.write(b"content")
        temp_path = f.name

    try:
        source = LocalFileSource(temp_path)
        metadata = source.get_metadata()

        assert metadata["source_type"] == "local"
        assert metadata["size"] == 7
        assert (
            metadata["type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert metadata["path"] == temp_path
    finally:
        Path(temp_path).unlink()
