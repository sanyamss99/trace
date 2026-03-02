"""Capture function arguments as a serializable dict."""

from __future__ import annotations

import inspect
import logging
from typing import Any

logger = logging.getLogger("usetrace")

MAX_STRING_LENGTH = 2000
MAX_LIST_ITEMS = 10
MAX_DICT_KEYS = 20


def _truncate_value(value: Any) -> Any:
    """Truncate a single value to keep payloads bounded."""
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            return value[:MAX_STRING_LENGTH] + "...[truncated]"
        return value
    if isinstance(value, list):
        truncated = [_truncate_value(item) for item in value[:MAX_LIST_ITEMS]]
        if len(value) > MAX_LIST_ITEMS:
            truncated.append(f"...[{len(value) - MAX_LIST_ITEMS} more items]")
        return truncated
    if isinstance(value, dict):
        keys = list(value.keys())[:MAX_DICT_KEYS]
        truncated = {k: _truncate_value(value[k]) for k in keys}
        if len(value) > MAX_DICT_KEYS:
            truncated["__truncated__"] = f"{len(value) - MAX_DICT_KEYS} more keys"
        return truncated
    if isinstance(value, (int, float, bool, type(None))):
        return value
    # Non-serializable objects: fall back to repr
    try:
        return repr(value)[:MAX_STRING_LENGTH]
    except Exception:
        return "<unrepresentable>"


def capture_locals(
    func: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Bind function arguments and return a truncated, serializable dict.

    Never raises — returns an empty dict on any failure.
    """
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return {name: _truncate_value(val) for name, val in bound.arguments.items()}
    except Exception:
        logger.debug("Failed to capture locals for %s", getattr(func, "__name__", "?"))
        return {}
