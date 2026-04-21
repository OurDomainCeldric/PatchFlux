"""BleepingComputer — US security-news aggregator.

Same legal tier as the existing heise / borns-it adapters: headline + URL +
pubDate only, no excerpts or article bodies stored.
"""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class BleepingComputerAdapter(SourceAdapter):
    source_id = "bleeping-computer"
    source_name = "BleepingComputer"
    feed_url = "https://www.bleepingcomputer.com/feed/"
    # Filter to the project's Microsoft/IT scope; keyword set mirrors the
    # heise adapter plus generic security terms already classified downstream.
    title_keywords: tuple[str, ...] = (
        "microsoft",
        "windows",
        "azure",
        "office",
        "microsoft 365",
        "m365",
        "teams",
        "outlook",
        "exchange",
        "sharepoint",
        "onedrive",
        "intune",
        "entra",
        "defender",
        "sentinel",
        "copilot",
        "github",
        ".net",
        "visual studio",
        "powershell",
        "hyper-v",
        "wsl",
    )

    def fetch(
        self,
        *,
        user_agent: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> SourceFetchResult:
        return fetch_and_parse(
            url=self.feed_url,
            source_id=self.source_id,
            source_name=self.source_name,
            user_agent=user_agent,
            etag=etag,
            last_modified=last_modified,
            default_language="en",
            title_keywords=self.title_keywords,
        )
