"""Tests for usetrace.decorators.context."""

import threading

from usetrace.decorators.context import TraceContext


def test_starts_as_root() -> None:
    ctx = TraceContext()
    assert ctx.is_root() is True
    assert ctx.current_parent_span_id is None


def test_push_pop_spans() -> None:
    ctx = TraceContext()
    ctx.push_span("span-1")
    assert ctx.is_root() is False
    assert ctx.current_parent_span_id == "span-1"

    ctx.push_span("span-2")
    assert ctx.current_parent_span_id == "span-2"

    popped = ctx.pop_span()
    assert popped == "span-2"
    assert ctx.current_parent_span_id == "span-1"

    popped = ctx.pop_span()
    assert popped == "span-1"
    assert ctx.is_root() is True


def test_pop_on_empty_returns_none() -> None:
    ctx = TraceContext()
    assert ctx.pop_span() is None


def test_reset_clears_state() -> None:
    ctx = TraceContext()
    ctx.trace_id = "trace-123"
    ctx.push_span("span-1")
    ctx.push_span("span-2")
    ctx.reset()
    assert ctx.is_root() is True
    assert ctx.trace_id is None


def test_trace_id_property() -> None:
    ctx = TraceContext()
    assert ctx.trace_id is None
    ctx.trace_id = "abc-123"
    assert ctx.trace_id == "abc-123"


def test_thread_isolation() -> None:
    """Each thread should have its own independent span stack."""
    ctx = TraceContext()
    ctx.push_span("main-span")
    ctx.trace_id = "main-trace"

    child_results: dict[str, object] = {}

    def child_thread() -> None:
        child_results["is_root"] = ctx.is_root()
        child_results["parent_id"] = ctx.current_parent_span_id
        child_results["trace_id"] = ctx.trace_id
        ctx.push_span("child-span")
        child_results["child_parent_id"] = ctx.current_parent_span_id

    t = threading.Thread(target=child_thread)
    t.start()
    t.join()

    # Child thread should have its own empty stack
    assert child_results["is_root"] is True
    assert child_results["parent_id"] is None
    assert child_results["trace_id"] is None
    assert child_results["child_parent_id"] == "child-span"

    # Main thread should be unaffected
    assert ctx.current_parent_span_id == "main-span"
    assert ctx.trace_id == "main-trace"
