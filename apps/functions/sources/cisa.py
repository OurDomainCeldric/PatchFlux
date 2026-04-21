"""CISA Cybersecurity Advisories.

U.S. Government public-domain feed. Headline + URL + pubDate only; no bodies.
See LEGAL.md.
"""
from __future__ import annotations

from sources._rss import fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class CISAAdvisoriesAdapter(SourceAdapter):
    source_id = "cisa-advisories"
    source_name = "CISA Advisories"
    feed_url = "https://www.cisa.gov/cybersecurity-advisories/all.xml"

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
