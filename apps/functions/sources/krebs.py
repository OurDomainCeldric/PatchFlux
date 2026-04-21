"""Krebs on Security — US security journalism.

Same legal tier as the existing heise / borns-it / bleeping adapters:
headline + URL + pubDate only, no excerpts or article bodies stored.
"""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class KrebsAdapter(SourceAdapter):
    source_id = "krebs"
    source_name = "Krebs on Security"
    feed_url = "https://krebsonsecurity.com/feed/"

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
        )
