"""Memory-bounded span buffer using a lock-free SimpleQueue."""

from __future__ import annotations

import logging
import threading
from queue import SimpleQueue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from usetrace.models.span import SpanData

logger = logging.getLogger("usetrace")

DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


class SpanBuffer:
    """Thread-safe, memory-bounded buffer for SpanData objects.

    Uses ``queue.SimpleQueue`` for lock-free ingestion. Silently drops
    spans when the byte ceiling is exceeded.
    """

    def __init__(self, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        self._queue: SimpleQueue[SpanData] = SimpleQueue()
        self._max_bytes = max_bytes
        self._pending_bytes = 0
        self._dropped_spans = 0
        self._lock = threading.Lock()

    @property
    def pending_bytes(self) -> int:
        """Current estimated byte usage of buffered spans."""
        return self._pending_bytes

    @property
    def dropped_spans(self) -> int:
        """Number of spans dropped due to memory ceiling."""
        return self._dropped_spans

    def put(self, span: SpanData) -> bool:
        """Enqueue a span if within memory budget.

        Returns True if enqueued, False if dropped.
        """
        span_bytes = span.estimated_bytes()
        with self._lock:
            if self._pending_bytes + span_bytes > self._max_bytes:
                self._dropped_spans += 1
                logger.debug("Span dropped — buffer at %d bytes", self._pending_bytes)
                return False
            self._pending_bytes += span_bytes
        self._queue.put(span)
        return True

    def drain(self, max_items: int) -> list[SpanData]:
        """Remove up to ``max_items`` spans from the buffer."""
        items: list[SpanData] = []
        drained_bytes = 0
        for _ in range(max_items):
            if self._queue.empty():
                break
            try:
                span = self._queue.get_nowait()
            except Exception:
                break
            drained_bytes += span.estimated_bytes()
            items.append(span)
        if drained_bytes:
            with self._lock:
                self._pending_bytes = max(0, self._pending_bytes - drained_bytes)
        return items

    def drain_all(self) -> list[SpanData]:
        """Remove all spans from the buffer."""
        items: list[SpanData] = []
        while not self._queue.empty():
            try:
                items.append(self._queue.get_nowait())
            except Exception:
                break
        with self._lock:
            self._pending_bytes = 0
        return items
