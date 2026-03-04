"""Extract prompt text from LLM call arguments via duck-typing.

Supports:
- OpenAI / xAI / Together / Ollama: messages=[{role, content}] kwargs
- Anthropic: messages=[{role, content}] + system=str kwargs
- Google Gemini: positional string arg or contents= kwarg
- Raw completions: prompt= kwarg or first positional string arg
- Wrapper functions: messages list in positional args or all string args
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("usetrace")


def _is_messages_list(obj: object) -> bool:
    """Check if an object looks like a chat messages list."""
    if not isinstance(obj, list) or not obj:
        return False
    first = obj[0]
    return isinstance(first, dict) and "role" in first


def _format_messages(messages: list[dict[str, Any]]) -> str:
    """Convert a list of chat messages to a flat prompt string.

    Each message is formatted as ``[role]\\ncontent`` with blank-line
    separators between messages.
    """
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            # Multi-part content blocks (Anthropic / OpenAI vision)
            text_parts: list[str] = []
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text", "")
                    if text:
                        text_parts.append(text)
                elif isinstance(block, str):
                    text_parts.append(block)
            content = "\n".join(text_parts)
        if content:
            parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts)


def extract_llm_prompt(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str | None:
    """Extract prompt text from LLM call arguments.

    Uses duck-typing to probe for ``messages``, ``prompt``, or
    ``contents`` parameters.  Never raises — returns ``None`` on any
    failure.
    """
    try:
        # Chat-style: messages kwarg (OpenAI, Anthropic, Together, Ollama)
        messages = kwargs.get("messages")
        if isinstance(messages, list) and messages:
            text = _format_messages(messages)
            # Anthropic: system prompt is a separate kwarg
            system = kwargs.get("system")
            if isinstance(system, str) and system:
                text = f"[system]\n{system}\n\n{text}"
            return text

        # Raw string prompt kwarg (OpenAI completions API)
        prompt = kwargs.get("prompt")
        if isinstance(prompt, str):
            return prompt

        # Google Gemini: contents kwarg
        contents = kwargs.get("contents")
        if isinstance(contents, str):
            return contents

        # Check positional args for a messages list (wrapper functions
        # that receive messages as a positional arg rather than kwarg)
        for arg in args:
            if _is_messages_list(arg):
                return _format_messages(arg)

        # Check all kwargs values for a messages list (e.g. custom kwarg names)
        for val in kwargs.values():
            if _is_messages_list(val):
                return _format_messages(val)

        # Fallback: concatenate all string positional args.
        # Captures prompt components passed as separate args to wrapper
        # functions like ask_with_context(question, context).
        str_args = [a for a in args if isinstance(a, str) and a.strip()]
        if str_args:
            return "\n\n".join(str_args)

        return None
    except Exception:
        logger.debug("Failed to extract prompt text from call arguments")
        return None
