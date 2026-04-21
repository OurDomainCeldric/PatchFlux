"""Microsoft 365 Public Roadmap adapter (RSS)."""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class M365RoadmapAdapter(SourceAdapter):
    source_id = "m365-roadmap"
    source_name = "Microsoft 365 Roadmap"
    feed_url = "https://www.microsoft.com/releasecommunications/api/v2/m365/rss"

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
