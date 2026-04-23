"""Microsoft Security Response Center (MSRC) blog."""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class MSRCAdapter(SourceAdapter):
    source_id = "msrc"
    source_name = "Microsoft Security Response Center"
    source_tier = 1
    # Official Security Update Guide RSS (CVE advisories).
    feed_url = "https://api.msrc.microsoft.com/update-guide/rss"

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
