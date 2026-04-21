"""Configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    table_connection: str
    news_table_name: str
    source_health_table_name: str
    user_agent: str


def get_settings() -> Settings:
    return Settings(
        table_connection=os.environ.get("NEWS_TABLE_CONNECTION", "UseDevelopmentStorage=true"),
        news_table_name=os.environ.get("NEWS_TABLE_NAME", "NewsItems"),
        source_health_table_name=os.environ.get("SOURCE_HEALTH_TABLE_NAME", "SourceHealth"),
        user_agent=os.environ.get(
            "USER_AGENT",
            "PatchFlux/1.0 (+https://github.com/OurDomainCeldric/PatchFlux)",
        ),
    )
