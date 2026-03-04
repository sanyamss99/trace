"""Tests for cost computation service."""

from decimal import Decimal

from api.services.cost import compute_cost


class TestComputeCost:
    """Unit tests for compute_cost."""

    def test_gpt4o_mini(self) -> None:
        """GPT-4o-mini pricing: $0.15/1M input, $0.60/1M output."""
        cost = compute_cost("gpt-4o-mini", prompt_tokens=1000, completion_tokens=500)
        assert cost is not None
        # 1000 * 0.15/1M + 500 * 0.60/1M = 0.000150 + 0.000300 = 0.000450
        assert cost == Decimal("0.000450")

    def test_gpt4o(self) -> None:
        """GPT-4o pricing: $2.50/1M input, $10.00/1M output."""
        cost = compute_cost("gpt-4o", prompt_tokens=10000, completion_tokens=2000)
        assert cost is not None
        # 10000 * 2.50/1M + 2000 * 10.00/1M = 0.025000 + 0.020000 = 0.045000
        assert cost == Decimal("0.045000")

    def test_claude_opus(self) -> None:
        """Claude Opus pricing."""
        cost = compute_cost("claude-opus-4-0", prompt_tokens=5000, completion_tokens=1000)
        assert cost is not None
        assert cost > Decimal("0")

    def test_unknown_model_returns_none(self) -> None:
        """Unknown model returns None."""
        assert compute_cost("unknown-model-v9", 100, 50) is None

    def test_missing_model_returns_none(self) -> None:
        """None model returns None."""
        assert compute_cost(None, 100, 50) is None

    def test_missing_tokens_returns_none(self) -> None:
        """Missing token counts return None."""
        assert compute_cost("gpt-4o-mini", None, 50) is None
        assert compute_cost("gpt-4o-mini", 100, None) is None

    def test_zero_tokens(self) -> None:
        """Zero tokens = zero cost."""
        cost = compute_cost("gpt-4o-mini", 0, 0)
        assert cost == Decimal("0.000000")

    def test_prefix_match(self) -> None:
        """Versioned model names match via prefix."""
        cost = compute_cost("gpt-4o-mini-2024-07-18", prompt_tokens=1000, completion_tokens=500)
        assert cost is not None
        assert cost == Decimal("0.000450")

    def test_gemini_flash(self) -> None:
        """Gemini 2.0 Flash pricing."""
        cost = compute_cost("gemini-2.0-flash", prompt_tokens=100000, completion_tokens=10000)
        assert cost is not None
        assert cost > Decimal("0")
