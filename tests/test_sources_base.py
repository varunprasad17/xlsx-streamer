"""Tests for StreamSource base class."""

from collections.abc import Iterator
from typing import Any

import pytest
from typing_extensions import override

from xlsx_streamer.sources.base import StreamSource


def test_stream_source_is_abstract() -> None:
    """Test that StreamSource is abstract and cannot be instantiated."""
    with pytest.raises(TypeError):
        StreamSource()  # type: ignore[abstract]


def test_stream_source_requires_get_stream() -> None:
    """Test that subclasses must implement get_stream."""

    class IncompleteSource(StreamSource):
        @override
        def get_metadata(self) -> dict[str, Any]:
            return {}

    with pytest.raises(TypeError):
        IncompleteSource()  # type: ignore[abstract]


def test_stream_source_requires_get_metadata() -> None:
    """Test that subclasses must implement get_metadata."""

    class IncompleteSource(StreamSource):
        @override
        def get_stream(self) -> Iterator[bytes]:
            yield b""

    with pytest.raises(TypeError):
        IncompleteSource()  # type: ignore[abstract]
