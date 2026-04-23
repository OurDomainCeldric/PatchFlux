"""Heise Online — category feed for Microsoft-related news.

Note
----
Heise is a commercial German press publisher. The ancillary copyright for
press publishers (Leistungsschutzrecht, §§ 87f ff. UrhG) means we MUST NOT
store article bodies, excerpts, descriptions, or summaries. We only keep
headline + URL + publication metadata — see LEGAL.md and the enforced
whitelist in ``models/news_item.py``.
"""
from __future__ import annotations

from sources._rss import MICROSOFT_TITLE_KEYWORDS, fetch_and_parse
from sources.base import SourceAdapter, SourceFetchResult


class HeiseAdapter(SourceAdapter):
    source_id = "heise"
    source_name = "heise online"
    source_tier = 2
    # Heise's public newsticker Atom feed. We filter locally by Microsoft-
    # related keywords in the title to honour our topical scope without
    # storing any snippets/descriptions.
    feed_url = "https://www.heise.de/newsticker/heise-atom.xml"
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
            default_language="de",
            title_keywords=self.title_keywords,
        )
