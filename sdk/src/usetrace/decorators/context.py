"""Per-thread trace context for parent-child span linking."""

from __future__ import annotations

import threading


class TraceContext:
    """Maintains a per-thread stack of active spans to track parent-child relationships.

    Uses ``threading.local()`` so each thread gets its own independent span stack.
    """

    def __init__(self) -> None:
        self._local = threading.local()

    def _get_stack(self) -> list[str]:
        if not hasattr(self._local, "stack"):
            self._local.stack = []
            self._local.trace_id = None
        return self._local.stack

    @property
    def trace_id(self) -> str | None:
        """The trace ID for the current thread, set by the root span."""
        self._get_stack()  # ensure initialised
        return getattr(self._local, "trace_id", None)

    @trace_id.setter
    def trace_id(self, value: str | None) -> None:
        self._get_stack()  # ensure initialised
        self._local.trace_id = value

    @property
    def current_parent_span_id(self) -> str | None:
        """The span ID at the top of the stack (the current parent)."""
        stack = self._get_stack()
        return stack[-1] if stack else None

    def is_root(self) -> bool:
        """True if no spans are currently on the stack."""
        return len(self._get_stack()) == 0

    def push_span(self, span_id: str) -> None:
        """Push a span ID onto the stack."""
        self._get_stack().append(span_id)

    def pop_span(self) -> str | None:
        """Pop the top span ID from the stack."""
        stack = self._get_stack()
        return stack.pop() if stack else None

    def reset(self) -> None:
        """Clear the span stack and trace ID for the current thread."""
        self._local.stack = []
        self._local.trace_id = None
