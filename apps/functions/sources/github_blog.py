"""GitHub Changelog — official product change feed."""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class GitHubBlogAdapter(SourceAdapter):
    source_id = "github-blog"
    source_name = "GitHub Changelog"
    # Changelog feed has a much higher signal-to-noise ratio than the main
    # blog for "new features / changes" classification.
    feed_url = "https://github.blog/changelog/feed/"

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
