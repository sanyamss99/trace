"""Extract LLM-specific fields from response objects via duck-typing.

Supports multiple vendor response shapes:
- OpenAI / xAI (Grok) / Together: .choices[0].message.content
- Anthropic (Claude): .content[0].text
- Google Gemini: .text / .candidates[0].content.parts[0].text
- Ollama: .message.content
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("usetrace")


def _extract_completion_text(result: Any) -> str | None:
    """Try each vendor's text path in order of specificity."""
    # OpenAI / xAI / Together: result.choices[0].message.content
    choices = getattr(result, "choices", None)
    if choices and len(choices) > 0:
        message = getattr(choices[0], "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if content is not None:
                return str(content)

    # Anthropic: result.content[0].text (content is a list of typed blocks)
    content_blocks = getattr(result, "content", None)
    if isinstance(content_blocks, list) and len(content_blocks) > 0:
        text = getattr(content_blocks[0], "text", None)
        if text is not None:
            return str(text)

    # Google Gemini: result.text (convenience accessor)
    text_attr = getattr(result, "text", None)
    if isinstance(text_attr, str):
        return text_attr

    # Ollama: result.message.content (no choices array)
    message = getattr(result, "message", None)
    if message is not None and not isinstance(message, str):
        content = getattr(message, "content", None)
        if content is not None:
            return str(content)

    return None


def _extract_token_counts(result: Any) -> dict[str, int]:
    """Try each vendor's token count path."""
    counts: dict[str, int] = {}

    # OpenAI / xAI / Together: result.usage.prompt_tokens / completion_tokens
    usage = getattr(result, "usage", None)
    if usage is not None:
        for src, dest in [
            ("prompt_tokens", "prompt_tokens"),
            ("completion_tokens", "completion_tokens"),
            # Anthropic: usage.input_tokens / output_tokens
            ("input_tokens", "prompt_tokens"),
            ("output_tokens", "completion_tokens"),
        ]:
            if dest not in counts:
                val = getattr(usage, src, None)
                if val is not None:
                    counts[dest] = int(val)
        return counts

    # Google Gemini: result.usage_metadata.prompt_token_count / candidates_token_count
    usage_metadata = getattr(result, "usage_metadata", None)
    if usage_metadata is not None:
        prompt_count = getattr(usage_metadata, "prompt_token_count", None)
        if prompt_count is not None:
            counts["prompt_tokens"] = int(prompt_count)
        completion_count = getattr(usage_metadata, "candidates_token_count", None)
        if completion_count is not None:
            counts["completion_tokens"] = int(completion_count)
        return counts

    # Ollama: result.prompt_eval_count / eval_count (directly on response)
    prompt_eval = getattr(result, "prompt_eval_count", None)
    if prompt_eval is not None:
        counts["prompt_tokens"] = int(prompt_eval)
    eval_count = getattr(result, "eval_count", None)
    if eval_count is not None:
        counts["completion_tokens"] = int(eval_count)

    return counts


def _extract_logprobs(result: Any) -> list[float] | None:
    """Try each vendor's logprobs path."""
    # OpenAI / xAI: result.choices[0].logprobs.content[].logprob
    # Together: result.choices[0].logprobs.token_logprobs (parallel array)
    choices = getattr(result, "choices", None)
    if choices and len(choices) > 0:
        logprobs = getattr(choices[0], "logprobs", None)
        if logprobs is not None:
            # Together flat format: logprobs.token_logprobs
            token_logprobs = getattr(logprobs, "token_logprobs", None)
            if isinstance(token_logprobs, list) and token_logprobs:
                return [float(lp) for lp in token_logprobs if lp is not None]

            # OpenAI newer format: logprobs.content[].logprob
            content_logprobs = getattr(logprobs, "content", None)
            if isinstance(content_logprobs, list) and content_logprobs:
                values = [getattr(entry, "logprob", None) for entry in content_logprobs]
                values = [float(lp) for lp in values if lp is not None]
                if values:
                    return values

    # Google Gemini: result.candidates[0].logprobs_result.chosen_candidates[].log_probability
    candidates = getattr(result, "candidates", None)
    if candidates and len(candidates) > 0:
        logprobs_result = getattr(candidates[0], "logprobs_result", None)
        if logprobs_result is not None:
            chosen = getattr(logprobs_result, "chosen_candidates", None)
            if isinstance(chosen, list) and chosen:
                values = [getattr(c, "log_probability", None) for c in chosen]
                values = [float(lp) for lp in values if lp is not None]
                if values:
                    return values

    # Ollama: result.logprobs[].logprob (list of Logprob objects, directly on response)
    logprobs_list = getattr(result, "logprobs", None)
    if isinstance(logprobs_list, list) and logprobs_list:
        # Check that items are objects with .logprob (not raw floats)
        first = logprobs_list[0]
        if hasattr(first, "logprob"):
            values = [getattr(lp, "logprob", None) for lp in logprobs_list]
            values = [float(v) for v in values if v is not None]
            if values:
                return values

    return None


def extract_llm_response(result: Any) -> dict[str, Any]:
    """Extract LLM metadata from a vendor response object.

    Uses duck-typing to probe for attributes from OpenAI, Anthropic,
    Google Gemini, Together, Ollama, and xAI response shapes.
    Never raises — returns an empty dict on any failure.
    """
    try:
        extracted: dict[str, Any] = {}

        text = _extract_completion_text(result)
        if text is not None:
            extracted["completion_text"] = text

        counts = _extract_token_counts(result)
        extracted.update(counts)

        logprobs = _extract_logprobs(result)
        if logprobs is not None:
            extracted["completion_logprobs"] = logprobs

        return extracted
    except Exception:
        logger.debug("Failed to extract LLM response fields")
        return {}
