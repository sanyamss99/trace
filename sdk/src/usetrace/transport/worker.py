"""Background daemon thread that flushes span batches to the API."""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from usetrace.transport.buffer import SpanBuffer

logger = logging.getLogger("usetrace")

DEFAULT_FLUSH_INTERVAL = 5.0  # seconds
DEFAULT_BATCH_SIZE = 50


class FlushWorker:
    """Daemon thread that periodically drains the span buffer and POSTs batches.

    Fire-and-forget with one retry: all HTTP errors are caught and logged
    at DEBUG level.  The worker wakes on *either* a timer expiry or the
    shared ``flush_event`` being signalled by the buffer.
    """

    def __init__(
        self,
        buffer: SpanBuffer,
        base_url: str,
        api_key: str,
        flush_interval: float = DEFAULT_FLUSH_INTERVAL,
        batch_size: int = DEFAULT_BATCH_SIZE,
        flush_event: threading.Event | None = None,
    ) -> None:
        self._buffer = buffer
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._flush_interval = flush_interval
        self._batch_size = batch_size
        self._stop_event = threading.Event()
        self._flush_event = flush_event or threading.Event()
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"X-Trace-Key": self._api_key},
            timeout=10.0,
        )
        self._thread = threading.Thread(target=self._run, daemon=True, name="usetrace-flush")

    def start(self) -> None:
        """Start the background flush thread."""
        self._thread.start()

    def stop(self) -> None:
        """Signal the worker to stop and perform a final drain."""
        self._stop_event.set()
        self._flush_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._client.close()

    def trigger_flush(self) -> None:
        """Wake the worker to flush immediately (e.g. for serverless)."""
        self._flush_event.set()

    def _run(self) -> None:
        """Main loop: wait for flush interval or signal, then drain and send."""
        while not self._stop_event.is_set():
            self._flush_event.wait(timeout=self._flush_interval)
            self._flush_event.clear()
            self._flush_batch()

        # Final drain on shutdown
        self._flush_batch(drain_all=True)

    def _flush_batch(self, *, drain_all: bool = False) -> None:
        """Drain spans from the buffer and POST them with one retry."""
        spans = self._buffer.drain_all() if drain_all else self._buffer.drain(self._batch_size)

        if not spans:
            return

        payload = [span.model_dump(mode="json") for span in spans]
        for attempt in range(2):
            try:
                self._client.post("/ingest/batch", json=payload)
                return
            except Exception:
                if attempt == 0:
                    logger.debug("Flush attempt failed, retrying in 1s (%d spans)", len(spans))
                    time.sleep(1.0)
                else:
                    logger.debug("Failed to flush %d spans after retry", len(spans))
