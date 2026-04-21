"""Windows (IT Pro) Blog."""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class WindowsBlogAdapter(SourceAdapter):
    source_id = "windows-blog"
    source_name = "Windows Blog"
    feed_url = "https://blogs.windows.com/feed"

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


class WindowsITProBlogAdapter(SourceAdapter):
    source_id = "windows-it-pro-blog"
    source_name = "Windows IT Pro Blog"
    feed_url = "https://techcommunity.microsoft.com/t5/s/gxcuf89792/rss/board?board.id=Windows-ITPro-Blog"

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
