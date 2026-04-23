"""r/sysadmin — community RSS feed (Microsoft/Windows-scoped).

Legal notes
-----------
- Reddit provides per-subreddit RSS feeds publicly (no authentication
  required, no scraping).
- We store only headline + URL + publication date (same metadata-only
  model as all other adapters). See LEGAL.md.
- Post titles on Reddit are authored by the submitters; they are
  descriptive headlines (typically a sentence or a link title), not
  the full article body — the same ratio as any other news source.
- We apply MICROSOFT_TITLE_KEYWORDS so only Microsoft/Windows-scoped
  submissions enter storage.
"""
from __future__ import annotations

from sources._rss import MICROSOFT_TITLE_KEYWORDS, fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class RedditSysadminAdapter(SourceAdapter):
    source_id = "reddit-sysadmin"
    source_name = "r/sysadmin"
    source_tier = 3
    # Search RSS: newest posts mentioning microsoft/windows/azure in r/sysadmin.
    # Reddit search RSS is public and documented in their API.
    feed_url = (
        "https://www.reddit.com/r/sysadmin/search.rss"
        "?q=microsoft+OR+windows+OR+azure&sort=new&restrict_sr=1&limit=50"
    )
    title_keywords: tuple[str, ...] = MICROSOFT_TITLE_KEYWORDS

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
