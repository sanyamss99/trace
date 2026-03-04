"""Cost computation for LLM spans based on model pricing.

Pricing is per 1M tokens. Updated periodically — add new models as needed.
"""

from __future__ import annotations

from decimal import Decimal

# ---------------------------------------------------------------------------
# Pricing table — cost per 1M tokens (prompt_input, completion_output)
# ---------------------------------------------------------------------------

# fmt: off
_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    # OpenAI
    "gpt-4o":               (Decimal("2.50"),  Decimal("10.00")),
    "gpt-4o-2024-08-06":    (Decimal("2.50"),  Decimal("10.00")),
    "gpt-4o-2024-11-20":    (Decimal("2.50"),  Decimal("10.00")),
    "gpt-4o-mini":          (Decimal("0.15"),  Decimal("0.60")),
    "gpt-4o-mini-2024-07-18": (Decimal("0.15"), Decimal("0.60")),
    "gpt-4-turbo":          (Decimal("10.00"), Decimal("30.00")),
    "gpt-4":                (Decimal("30.00"), Decimal("60.00")),
    "gpt-3.5-turbo":        (Decimal("0.50"),  Decimal("1.50")),
    "o1":                   (Decimal("15.00"), Decimal("60.00")),
    "o1-mini":              (Decimal("3.00"),  Decimal("12.00")),
    "o1-pro":               (Decimal("150.00"), Decimal("600.00")),
    "o3":                   (Decimal("10.00"), Decimal("40.00")),
    "o3-mini":              (Decimal("1.10"),  Decimal("4.40")),
    "o4-mini":              (Decimal("1.10"),  Decimal("4.40")),

    # Anthropic
    "claude-opus-4-0":      (Decimal("15.00"), Decimal("75.00")),
    "claude-sonnet-4-0":    (Decimal("3.00"),  Decimal("15.00")),
    "claude-3-5-sonnet-20241022": (Decimal("3.00"), Decimal("15.00")),
    "claude-3-5-haiku-20241022": (Decimal("0.80"), Decimal("4.00")),
    "claude-3-opus-20240229": (Decimal("15.00"), Decimal("75.00")),
    "claude-3-haiku-20240307": (Decimal("0.25"), Decimal("1.25")),

    # Google Gemini
    "gemini-2.0-flash":     (Decimal("0.10"),  Decimal("0.40")),
    "gemini-2.0-flash-lite": (Decimal("0.075"), Decimal("0.30")),
    "gemini-1.5-pro":       (Decimal("1.25"),  Decimal("5.00")),
    "gemini-1.5-flash":     (Decimal("0.075"), Decimal("0.30")),

    # Together / open-source hosted
    "meta-llama/llama-3-70b-instruct": (Decimal("0.90"), Decimal("0.90")),
    "meta-llama/llama-3-8b-instruct":  (Decimal("0.20"), Decimal("0.20")),
    "mistralai/mixtral-8x7b-instruct": (Decimal("0.60"), Decimal("0.60")),
}
# fmt: on

_MILLION = Decimal("1000000")


def compute_cost(
    model: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> Decimal | None:
    """Compute cost in USD for a span given model and token counts.

    Returns None if model is unknown or token counts are missing.
    """
    if not model or prompt_tokens is None or completion_tokens is None:
        return None

    # Try exact match first, then prefix match for versioned model names
    pricing = _PRICING.get(model)
    if pricing is None:
        for key, value in _PRICING.items():
            if model.startswith(key) or key.startswith(model):
                pricing = value
                break

    if pricing is None:
        return None

    input_cost, output_cost = pricing
    total = (
        Decimal(prompt_tokens) * input_cost / _MILLION
        + Decimal(completion_tokens) * output_cost / _MILLION
    )
    return total.quantize(Decimal("0.000001"))
