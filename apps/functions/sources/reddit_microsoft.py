"""r/microsoft — community RSS feed.

Legal notes
-----------
- Reddit provides per-subreddit RSS feeds publicly (no authentication
  required, no scraping).
- We store only headline + URL + publication date. See LEGAL.md.
- r/microsoft is entirely Microsoft-scoped by definition; no additional
  keyword filter is needed.
"""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class RedditMicrosoftAdapter(SourceAdapter):
    source_id = "reddit-microsoft"
    source_name = "r/microsoft"
    source_tier = 3
    # Newest posts — every submission is on-topic by subreddit definition.
    feed_url = "https://www.reddit.com/r/microsoft/new.rss?limit=50"
    fallback_urls = ("https://old.reddit.com/r/microsoft/new.rss?limit=50",)

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
            fallback_urls=self.fallback_urls,
        )
