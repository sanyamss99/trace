"""In-memory sliding-window rate limiter for authentication failures."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict


class AuthFailureRateLimiter:
    """Track failed auth attempts per IP using a sliding window.

    Async-safe via an asyncio.Lock. Stale entries are pruned lazily
    on each is_blocked() call.
    """

    def __init__(self, max_failures: int = 10, window_seconds: int = 60) -> None:
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_blocked(self, ip: str) -> bool:
        """Return True if the IP has exceeded the failure threshold."""
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self._window_seconds
            if ip in self._failures:
                self._failures[ip] = [t for t in self._failures[ip] if t > cutoff]
                if not self._failures[ip]:
                    del self._failures[ip]
                    return False
                return len(self._failures[ip]) >= self._max_failures
            return False

    async def record_failure(self, ip: str) -> None:
        """Record a failed auth attempt for the given IP."""
        async with self._lock:
            self._failures[ip].append(time.monotonic())

    async def reset(self) -> None:
        """Clear all tracked failures. Used in tests."""
        async with self._lock:
            self._failures.clear()


class OrgRequestRateLimiter:
    """Track request volume per org using a sliding window.

    Limits total API requests per org_id. Async-safe via asyncio.Lock.
    Stale entries are pruned lazily on each check_and_record() call.
    """

    def __init__(self, max_requests: int = 10_000, window_seconds: int = 60) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check_and_record(self, org_id: str) -> bool:
        """Record a request and return True if the org is over the limit."""
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self._window_seconds
            timestamps = self._requests[org_id]
            self._requests[org_id] = [t for t in timestamps if t > cutoff]
            if len(self._requests[org_id]) >= self._max_requests:
                return True
            self._requests[org_id].append(now)
            return False

    async def reset(self) -> None:
        """Clear all tracked requests. Used in tests."""
        async with self._lock:
            self._requests.clear()


# Module-level singletons
auth_rate_limiter = AuthFailureRateLimiter(max_failures=10, window_seconds=60)
org_rate_limiter = OrgRequestRateLimiter(max_requests=10_000, window_seconds=60)
