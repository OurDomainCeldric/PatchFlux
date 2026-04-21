"""Azure OpenAI price table (USD per 1M tokens).

Prices are intentionally kept conservative (list price, no regional discount,
no batch discount) so that budget projections never *underestimate* spend.
Values are loosely tied to Azure OpenAI pricing as of 2026-Q1 — adjust here
when Microsoft changes prices.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    input_per_1m_usd: float
    output_per_1m_usd: float


# Conservative list prices. If a configured model is not found we fall back
# to GPT-4.1-mini pricing, which is on the higher end of the "low tier"
# family — again biased toward overestimating cost.
_PRICES: dict[str, ModelPrice] = {
    "gpt-4o-mini": ModelPrice(0.15, 0.60),
    "gpt-4.1-mini": ModelPrice(0.40, 1.60),
    "gpt-4.1-nano": ModelPrice(0.10, 0.40),
    "gpt-5-mini": ModelPrice(0.25, 2.00),
    "gpt-5-nano": ModelPrice(0.05, 0.40),
}

_FALLBACK = _PRICES["gpt-4.1-mini"]


def get_price(model: str) -> ModelPrice:
    return _PRICES.get(model.strip().lower(), _FALLBACK)


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = get_price(model)
    return (
        input_tokens * price.input_per_1m_usd / 1_000_000.0
        + output_tokens * price.output_per_1m_usd / 1_000_000.0
    )
