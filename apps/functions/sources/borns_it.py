"""Borns IT- und Windows-Blog (borncity.com).

Legal note: same ancillary copyright considerations as other German publishers.
Only metadata is stored; see LEGAL.md.
"""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class BornsITAdapter(SourceAdapter):
    source_id = "borns-it"
    source_name = "Borns IT- und Windows-Blog"
    feed_url = "https://www.borncity.com/blog/feed/"

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
            default_language="de",
        )
