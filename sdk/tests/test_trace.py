"""Tests for the main Trace client and observe() decorator."""

from types import SimpleNamespace

import pytest

from usetrace.decorators.trace import Trace
from usetrace.models.span import SpanData


@pytest.fixture()
def tracer() -> Trace:
    """Create a Trace client with transport disabled for unit testing."""
    t = Trace(api_key="test-key", enabled=False)
    # Re-enable after construction but skip the worker so we can inspect the buffer
    t._enabled = True
    from usetrace.transport.buffer import SpanBuffer

    t._buffer = SpanBuffer()
    from usetrace.decorators.context import TraceContext

    t._context = TraceContext()
    return t


def _drain_spans(tracer: Trace) -> list[SpanData]:
    return tracer._buffer.drain_all()


class TestSyncDecorator:
    def test_captures_return_value(self, tracer: Trace) -> None:
        @tracer.observe()
        def add(a: int, b: int) -> int:
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_captures_inputs_and_output(self, tracer: Trace) -> None:
        @tracer.observe()
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        greet("Alice")
        spans = _drain_spans(tracer)
        assert len(spans) == 1
        span = spans[0]
        assert span.inputs == {"name": "Alice"}
        assert span.output == "Hello, Alice!"
        assert span.status == "ok"
        assert span.function_name.endswith("greet")

    def test_propagates_exceptions(self, tracer: Trace) -> None:
        @tracer.observe()
        def fail() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            fail()

        spans = _drain_spans(tracer)
        assert len(spans) == 1
        assert spans[0].status == "error"
        assert spans[0].error_type == "ValueError"
        assert spans[0].error_message == "boom"

    def test_records_duration(self, tracer: Trace) -> None:
        @tracer.observe()
        def noop() -> None:
            pass

        noop()
        spans = _drain_spans(tracer)
        assert spans[0].duration_ms >= 0

    def test_respects_capture_input_false(self, tracer: Trace) -> None:
        @tracer.observe(capture_input=False)
        def secret(password: str) -> str:
            return "ok"

        secret("hunter2")
        spans = _drain_spans(tracer)
        assert spans[0].inputs is None

    def test_respects_capture_output_false(self, tracer: Trace) -> None:
        @tracer.observe(capture_output=False)
        def secret() -> str:
            return "sensitive-data"

        secret()
        spans = _drain_spans(tracer)
        assert spans[0].output is None

    def test_span_type_and_tags(self, tracer: Trace) -> None:
        @tracer.observe(span_type="tool", tags={"version": "2"})
        def my_tool() -> str:
            return "done"

        my_tool()
        spans = _drain_spans(tracer)
        assert spans[0].span_type == "tool"
        assert spans[0].tags == {"version": "2"}


class TestAsyncDecorator:
    @pytest.mark.asyncio()
    async def test_captures_async_return_value(self, tracer: Trace) -> None:
        @tracer.observe()
        async def add(a: int, b: int) -> int:
            return a + b

        result = await add(2, 3)
        assert result == 5

    @pytest.mark.asyncio()
    async def test_captures_async_inputs_and_output(self, tracer: Trace) -> None:
        @tracer.observe()
        async def greet(name: str) -> str:
            return f"Hello, {name}!"

        await greet("Bob")
        spans = _drain_spans(tracer)
        assert len(spans) == 1
        assert spans[0].inputs == {"name": "Bob"}
        assert spans[0].output == "Hello, Bob!"

    @pytest.mark.asyncio()
    async def test_propagates_async_exceptions(self, tracer: Trace) -> None:
        @tracer.observe()
        async def fail() -> None:
            raise RuntimeError("async boom")

        with pytest.raises(RuntimeError, match="async boom"):
            await fail()

        spans = _drain_spans(tracer)
        assert spans[0].status == "error"
        assert spans[0].error_type == "RuntimeError"


class TestNestedSpans:
    def test_parent_child_linking(self, tracer: Trace) -> None:
        @tracer.observe(span_type="chain")
        def outer() -> str:
            return inner()

        @tracer.observe(span_type="llm")
        def inner() -> str:
            return "result"

        outer()
        spans = _drain_spans(tracer)
        assert len(spans) == 2

        # Inner span is emitted first (before outer returns)
        inner_span = spans[0]
        outer_span = spans[1]

        assert inner_span.parent_span_id == outer_span.span_id
        assert outer_span.parent_span_id is None
        assert inner_span.trace_id == outer_span.trace_id

    @pytest.mark.asyncio()
    async def test_async_parent_child_linking(self, tracer: Trace) -> None:
        @tracer.observe(span_type="chain")
        async def outer() -> str:
            return await inner()

        @tracer.observe(span_type="llm")
        async def inner() -> str:
            return "result"

        await outer()
        spans = _drain_spans(tracer)
        assert len(spans) == 2

        inner_span = spans[0]
        outer_span = spans[1]

        assert inner_span.parent_span_id == outer_span.span_id
        assert outer_span.parent_span_id is None


class TestLLMExtraction:
    def test_extracts_llm_fields_on_llm_span_type(self, tracer: Trace) -> None:
        mock_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="AI says hi"), logprobs=None)],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

        @tracer.observe(span_type="llm", model="gpt-4")
        def call_llm() -> SimpleNamespace:
            return mock_response

        call_llm()
        spans = _drain_spans(tracer)
        assert spans[0].completion_text == "AI says hi"
        assert spans[0].prompt_tokens == 10
        assert spans[0].completion_tokens == 5
        assert spans[0].model == "gpt-4"


class TestDisabledMode:
    def test_disabled_tracer_passes_through(self) -> None:
        tracer = Trace(enabled=False)

        @tracer.observe()
        def add(a: int, b: int) -> int:
            return a + b

        # The decorator should be a no-op
        result = add(2, 3)
        assert result == 5

    def test_disabled_tracer_does_not_wrap(self) -> None:
        tracer = Trace(enabled=False)

        def original(x: int) -> int:
            return x

        decorated = tracer.observe()(original)
        # When disabled, observe() returns the original function
        assert decorated is original


class TestStats:
    def test_stats_reports_pending_bytes(self, tracer: Trace) -> None:
        @tracer.observe()
        def noop() -> None:
            pass

        noop()
        assert tracer.stats.pending_bytes > 0
        _drain_spans(tracer)
        assert tracer.stats.pending_bytes == 0

    def test_stats_reports_dropped_spans(self) -> None:
        t = Trace(enabled=False)
        t._enabled = True
        from usetrace.transport.buffer import SpanBuffer

        t._buffer = SpanBuffer(max_bytes=100)  # very small
        from usetrace.decorators.context import TraceContext

        t._context = TraceContext()

        @t.observe()
        def big_output() -> str:
            return "x" * 5000

        for _ in range(10):
            big_output()

        assert t.stats.dropped_spans > 0
