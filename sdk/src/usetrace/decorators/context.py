"""Per-task trace context for parent-child span linking.

Uses ``contextvars.ContextVar`` so each asyncio task (and each thread)
gets its own independent span stack.  The stack is stored as an
immutable tuple to prevent mutation from leaking between tasks.
"""

from __future__ import annotations

from contextvars import ContextVar

_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_stack_var: ContextVar[tuple[str, ...]] = ContextVar("span_stack", default=())


class TraceContext:
    """Maintains a per-task stack of active spans to track parent-child relationships.

    Uses ``contextvars.ContextVar`` so each asyncio task automatically
    inherits a *copy* of the parent task's context, preventing
    concurrent tasks from corrupting each other's span stacks.
    """

    @property
    def trace_id(self) -> str | None:
        """The trace ID for the current context, set by the root span."""
        return _trace_id_var.get()

    @trace_id.setter
    def trace_id(self, value: str | None) -> None:
        _trace_id_var.set(value)

    @property
    def current_parent_span_id(self) -> str | None:
        """The span ID at the top of the stack (the current parent)."""
        stack = _span_stack_var.get()
        return stack[-1] if stack else None

    def is_root(self) -> bool:
        """True if no spans are currently on the stack."""
        return len(_span_stack_var.get()) == 0

    def push_span(self, span_id: str) -> None:
        """Push a span ID onto the stack (creates a new immutable tuple)."""
        stack = _span_stack_var.get()
        _span_stack_var.set((*stack, span_id))

    def pop_span(self) -> str | None:
        """Pop the top span ID from the stack."""
        stack = _span_stack_var.get()
        if not stack:
            return None
        _span_stack_var.set(stack[:-1])
        return stack[-1]

    def reset(self) -> None:
        """Clear the span stack and trace ID for the current context."""
        _trace_id_var.set(None)
        _span_stack_var.set(())
