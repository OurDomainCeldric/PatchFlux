"""Azure Updates feed."""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class AzureUpdatesAdapter(SourceAdapter):
    source_id = "azure-updates"
    source_name = "Azure Updates"
    feed_url = "https://www.microsoft.com/releasecommunications/api/v2/azure/rss"

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
