"""Main Trace client class with the ``observe()`` decorator."""

from __future__ import annotations

import atexit
import functools
import inspect
import logging
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar

from usetrace.capture.llm_response import extract_llm_response
from usetrace.capture.locals import _truncate_value, capture_locals
from usetrace.decorators.context import TraceContext
from usetrace.models.span import SpanData
from usetrace.transport.buffer import SpanBuffer
from usetrace.transport.worker import FlushWorker

logger = logging.getLogger("usetrace")

F = TypeVar("F", bound=Callable[..., Any])


class TraceStats:
    """Read-only snapshot of SDK telemetry stats."""

    def __init__(self, pending_bytes: int, dropped_spans: int) -> None:
        self.pending_bytes = pending_bytes
        self.dropped_spans = dropped_spans


class Trace:
    """The main SDK entry point. Initialize once at application startup.

    Usage::

        tracer = Trace(api_key="sk-...", base_url="http://localhost:8000")

        @tracer.observe(span_type="llm", model="gpt-4")
        def call_llm(prompt: str) -> str:
            ...
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "http://localhost:8000",
        environment: str = "development",
        enabled: bool = True,
        flush_interval: float = 5.0,
        batch_size: int = 50,
        max_buffer_bytes: int = 10 * 1024 * 1024,
        max_string_length: int | None = None,
        flush_threshold: int | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._environment = environment
        self._enabled = enabled
        self._context = TraceContext()
        self._max_string_length = max_string_length or max(
            500, min(50_000, max_buffer_bytes // 1024)
        )

        # Shared event: buffer signals the worker when span count hits threshold
        flush_event = threading.Event()
        resolved_threshold = flush_threshold if flush_threshold is not None else batch_size

        self._buffer = SpanBuffer(
            max_bytes=max_buffer_bytes,
            flush_event=flush_event,
            flush_threshold=resolved_threshold,
        )

        if self._enabled:
            self._worker = FlushWorker(
                buffer=self._buffer,
                base_url=self._base_url,
                api_key=self._api_key,
                flush_interval=flush_interval,
                batch_size=batch_size,
                flush_event=flush_event,
            )
            self._worker.start()
            atexit.register(self.shutdown)
        else:
            self._worker = None

    @property
    def stats(self) -> TraceStats:
        """Current buffer statistics."""
        return TraceStats(
            pending_bytes=self._buffer.pending_bytes,
            dropped_spans=self._buffer.dropped_spans,
        )

    def observe(
        self,
        span_type: str = "generic",
        model: str | None = None,
        capture_input: bool = True,
        capture_output: bool = True,
        tags: dict[str, str] | None = None,
    ) -> Callable[[F], F]:
        """Decorator that traces a function's execution as a span.

        Automatically detects sync vs async functions.
        """

        def decorator(func: F) -> F:
            if not self._enabled:
                return func

            if inspect.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    return await self._execute_span_async(
                        func, args, kwargs, span_type, model, capture_input, capture_output, tags
                    )

                return async_wrapper  # type: ignore[return-value]

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return self._execute_span(
                    func, args, kwargs, span_type, model, capture_input, capture_output, tags
                )

            return sync_wrapper  # type: ignore[return-value]

        return decorator

    def _execute_span(
        self,
        func: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        span_type: str,
        model: str | None,
        capture_input: bool,
        capture_output: bool,
        tags: dict[str, str] | None,
    ) -> Any:
        """Execute a sync function within a traced span."""
        span_id = uuid.uuid4().hex
        is_root = self._context.is_root()
        if is_root:
            self._context.trace_id = uuid.uuid4().hex
        trace_id = self._context.trace_id or uuid.uuid4().hex
        parent_span_id = self._context.current_parent_span_id

        self._context.push_span(span_id)
        inputs = (
            capture_locals(func, args, kwargs, max_string_length=self._max_string_length)
            if capture_input
            else None
        )
        start = time.perf_counter()
        start_time = datetime.now(UTC)

        try:
            result = func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start) * 1000
            self._emit_span(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                span_type=span_type,
                func=func,
                start_time=start_time,
                duration_ms=duration_ms,
                status="ok",
                inputs=inputs,
                output=result if capture_output else None,
                model=model,
                tags=tags,
            )
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            self._emit_span(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                span_type=span_type,
                func=func,
                start_time=start_time,
                duration_ms=duration_ms,
                status="error",
                inputs=inputs,
                output=None,
                model=model,
                tags=tags,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise
        finally:
            self._context.pop_span()
            if is_root:
                self._context.reset()

    async def _execute_span_async(
        self,
        func: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        span_type: str,
        model: str | None,
        capture_input: bool,
        capture_output: bool,
        tags: dict[str, str] | None,
    ) -> Any:
        """Execute an async function within a traced span."""
        span_id = uuid.uuid4().hex
        is_root = self._context.is_root()
        if is_root:
            self._context.trace_id = uuid.uuid4().hex
        trace_id = self._context.trace_id or uuid.uuid4().hex
        parent_span_id = self._context.current_parent_span_id

        self._context.push_span(span_id)
        inputs = (
            capture_locals(func, args, kwargs, max_string_length=self._max_string_length)
            if capture_input
            else None
        )
        start = time.perf_counter()
        start_time = datetime.now(UTC)

        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start) * 1000
            self._emit_span(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                span_type=span_type,
                func=func,
                start_time=start_time,
                duration_ms=duration_ms,
                status="ok",
                inputs=inputs,
                output=result if capture_output else None,
                model=model,
                tags=tags,
            )
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            self._emit_span(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                span_type=span_type,
                func=func,
                start_time=start_time,
                duration_ms=duration_ms,
                status="error",
                inputs=inputs,
                output=None,
                model=model,
                tags=tags,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise
        finally:
            self._context.pop_span()
            if is_root:
                self._context.reset()

    def _emit_span(
        self,
        *,
        trace_id: str,
        span_id: str,
        parent_span_id: str | None,
        span_type: str,
        func: Callable[..., Any],
        start_time: datetime,
        duration_ms: float,
        status: str,
        inputs: dict[str, Any] | None,
        output: Any | None,
        model: str | None,
        tags: dict[str, str] | None,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Build a SpanData and enqueue it in the buffer."""
        try:
            llm_fields: dict[str, Any] = {}
            if span_type == "llm" and output is not None:
                llm_fields = extract_llm_response(output)

            span = SpanData(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                span_type=span_type,
                function_name=getattr(func, "__qualname__", getattr(func, "__name__", "unknown")),
                module=getattr(func, "__module__", ""),
                start_time=start_time,
                end_time=datetime.now(UTC),
                duration_ms=duration_ms,
                status=status,
                error_type=error_type,
                error_message=error_message,
                inputs=inputs,
                output=_truncate_value(output, self._max_string_length) if not llm_fields else None,
                model=model or llm_fields.get("model"),
                completion_text=llm_fields.get("completion_text"),
                prompt_tokens=llm_fields.get("prompt_tokens"),
                completion_tokens=llm_fields.get("completion_tokens"),
                completion_logprobs=llm_fields.get("completion_logprobs"),
                environment=self._environment,
                tags=tags,
            )
            self._buffer.put(span)
        except Exception:
            logger.debug("Failed to emit span for %s", getattr(func, "__name__", "?"))

    def flush(self) -> None:
        """Force an immediate flush of buffered spans (useful for serverless/Lambda)."""
        if self._worker:
            self._worker.trigger_flush()

    def shutdown(self) -> None:
        """Stop the background worker and drain remaining spans."""
        if self._worker:
            self._worker.stop()
