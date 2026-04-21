"""Configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    table_connection: str
    news_table_name: str
    source_health_table_name: str
    ai_budget_table_name: str
    user_agent: str
    # --- AI relevance gate (all optional; off by default) --------------------
    ai_gate_enabled: bool
    ai_endpoint: str
    ai_api_key: str
    ai_deployment: str
    ai_model: str
    ai_api_version: str
    # Hard monthly spend ceiling in USD. The gate refuses to call the API once
    # projected spend would exceed this value. Default keeps the AGENTS.md
    # "stay on free / consumption tiers" posture.
    ai_max_monthly_usd: float
    # Defence in depth: per-ingest-run cap so a runaway feed cannot burn the
    # whole monthly budget in a single iteration.
    ai_max_calls_per_run: int
    ai_max_output_tokens: int


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_settings() -> Settings:
    return Settings(
        table_connection=os.environ.get("NEWS_TABLE_CONNECTION", "UseDevelopmentStorage=true"),
        news_table_name=os.environ.get("NEWS_TABLE_NAME", "NewsItems"),
        source_health_table_name=os.environ.get("SOURCE_HEALTH_TABLE_NAME", "SourceHealth"),
        ai_budget_table_name=os.environ.get("AI_BUDGET_TABLE_NAME", "AiBudget"),
        user_agent=os.environ.get(
            "USER_AGENT",
            "PatchFlux/1.0 (+https://github.com/OurDomainCeldric/PatchFlux)",
        ),
        ai_gate_enabled=_env_flag("AI_GATE_ENABLED", default=False),
        ai_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip(),
        ai_api_key=os.environ.get("AZURE_OPENAI_API_KEY", "").strip(),
        ai_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip(),
        ai_model=os.environ.get("AZURE_OPENAI_MODEL", "gpt-4o-mini").strip(),
        ai_api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21").strip(),
        ai_max_monthly_usd=_env_float("AI_MAX_MONTHLY_USD", 5.0),
        ai_max_calls_per_run=_env_int("AI_MAX_CALLS_PER_RUN", 100),
        ai_max_output_tokens=_env_int("AI_MAX_OUTPUT_TOKENS", 150),
    )
