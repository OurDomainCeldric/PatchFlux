"""Tests for the AI pricing helper."""
from __future__ import annotations

from ai.pricing import cost_usd, get_price


def test_known_model_uses_listed_prices() -> None:
    # gpt-4o-mini: $0.15 / 1M in, $0.60 / 1M out.
    assert cost_usd("gpt-4o-mini", 1_000_000, 0) == 0.15
    assert cost_usd("gpt-4o-mini", 0, 1_000_000) == 0.60
    # 1,000 input + 500 output -> $0.00015 + $0.00030 = $0.00045.
    assert abs(cost_usd("gpt-4o-mini", 1_000, 500) - 0.00045) < 1e-9


def test_unknown_model_falls_back_to_conservative_pricing() -> None:
    # Fallback price must be >= gpt-4o-mini pricing so budget checks are
    # pessimistic, never optimistic.
    mini = get_price("gpt-4o-mini")
    fallback = get_price("some-future-model-xyz")
    assert fallback.input_per_1m_usd >= mini.input_per_1m_usd
    assert fallback.output_per_1m_usd >= mini.output_per_1m_usd
