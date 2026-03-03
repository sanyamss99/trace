"""Tests for usetrace.decorators.context."""

import asyncio

import pytest

from usetrace.decorators.context import TraceContext, _span_stack_var, _trace_id_var


@pytest.fixture(autouse=True)
def _reset_contextvars() -> None:
    """Ensure each test starts with clean context."""
    _trace_id_var.set(None)
    _span_stack_var.set(())


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


@pytest.mark.asyncio()
async def test_asyncio_task_isolation() -> None:
    """Each asyncio task should get its own independent span stack."""
    ctx = TraceContext()
    ctx.push_span("main-span")
    ctx.trace_id = "main-trace"

    task_results: dict[str, object] = {}

    async def child_task() -> None:
        # asyncio.create_task copies the parent's context, but our
        # immutable tuples mean mutations here don't affect the parent
        task_results["inherited_parent"] = ctx.current_parent_span_id
        ctx.push_span("child-span")
        task_results["child_parent"] = ctx.current_parent_span_id

    await asyncio.create_task(child_task())

    # Child inherited the parent's stack (main-span) at creation time
    assert task_results["inherited_parent"] == "main-span"
    assert task_results["child_parent"] == "child-span"

    # Main context is unaffected by child's push
    assert ctx.current_parent_span_id == "main-span"
    assert ctx.trace_id == "main-trace"


@pytest.mark.asyncio()
async def test_asyncio_gather_isolation() -> None:
    """Concurrent tasks under asyncio.gather must not corrupt each other."""
    ctx = TraceContext()
    ctx.push_span("root")

    results: dict[str, str | None] = {}

    async def task_a() -> None:
        ctx.push_span("a-span")
        await asyncio.sleep(0.01)  # yield to let task_b run
        results["a_parent"] = ctx.current_parent_span_id

    async def task_b() -> None:
        ctx.push_span("b-span")
        await asyncio.sleep(0.01)  # yield to let task_a run
        results["b_parent"] = ctx.current_parent_span_id

    await asyncio.gather(
        asyncio.create_task(task_a()),
        asyncio.create_task(task_b()),
    )

    # Each task sees its own span, not the other's
    assert results["a_parent"] == "a-span"
    assert results["b_parent"] == "b-span"

    # Root context unaffected
    assert ctx.current_parent_span_id == "root"
