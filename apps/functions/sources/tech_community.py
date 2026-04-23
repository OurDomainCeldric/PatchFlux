"""Microsoft Tech Community — aggregated Atom feed across all blogs."""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class TechCommunityAdapter(SourceAdapter):
    source_id = "ms-tech-community"
    source_name = "Microsoft Tech Community"
    source_tier = 1
    # Khoros board RSS (legacy path still served by the TC CDN).
    feed_url = "https://techcommunity.microsoft.com/t5/s/gxcuf89792/rss/board?board.id=MicrosoftTeamsBlog"

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
