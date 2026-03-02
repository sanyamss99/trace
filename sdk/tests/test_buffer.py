"""Tests for usetrace.transport.buffer."""

from usetrace.models.span import SpanData
from usetrace.transport.buffer import SpanBuffer


def _make_span(**overrides: object) -> SpanData:
    defaults = {"trace_id": "t1", "span_id": "s1"}
    defaults.update(overrides)
    return SpanData(**defaults)  # type: ignore[arg-type]


def test_put_and_drain() -> None:
    buf = SpanBuffer()
    span = _make_span()
    assert buf.put(span) is True
    items = buf.drain(10)
    assert len(items) == 1
    assert items[0].span_id == "s1"


def test_drain_respects_max_items() -> None:
    buf = SpanBuffer()
    for i in range(10):
        buf.put(_make_span(span_id=f"s{i}"))
    items = buf.drain(3)
    assert len(items) == 3


def test_drain_all() -> None:
    buf = SpanBuffer()
    for i in range(5):
        buf.put(_make_span(span_id=f"s{i}"))
    items = buf.drain_all()
    assert len(items) == 5
    assert buf.pending_bytes == 0


def test_memory_ceiling_drops_spans() -> None:
    """Spans that exceed the memory ceiling should be silently dropped."""
    # Use a very small buffer so we can trigger drops
    buf = SpanBuffer(max_bytes=500)
    accepted = 0
    for i in range(100):
        if buf.put(_make_span(span_id=f"s{i}")):
            accepted += 1
    assert accepted > 0
    assert buf.dropped_spans > 0
    assert buf.dropped_spans + accepted == 100


def test_pending_bytes_tracks_usage() -> None:
    buf = SpanBuffer()
    span = _make_span()
    buf.put(span)
    assert buf.pending_bytes > 0
    buf.drain(1)
    assert buf.pending_bytes == 0


def test_empty_drain_returns_empty_list() -> None:
    buf = SpanBuffer()
    assert buf.drain(10) == []
    assert buf.drain_all() == []
