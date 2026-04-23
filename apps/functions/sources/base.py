"""Base class for source adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from models.news_item import NewsItem


@dataclass
class SourceFetchResult:
    source_id: str
    items: list[NewsItem] = field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    status: str = "ok"
    error: str | None = None


class SourceAdapter(ABC):
    """Abstract interface for all news sources.

    Implementations must:
      * only use official APIs or RSS/Atom feeds;
      * use Conditional GET when the protocol supports it (``If-None-Match`` /
        ``If-Modified-Since``);
      * **never** return article bodies, descriptions, or snippets in
        :class:`NewsItem`;
      * set a transparent ``User-Agent``.
    """

    #: Stable machine identifier, e.g. ``"m365-roadmap"``. Must match ``^[a-z0-9-]+$``.
    source_id: str
    #: Human-readable name shown in the UI.
    source_name: str
    #: Editorial trust tier:
    #:   1 – Official (vendor-operated / government)
    #:   2 – Established press (editorial standards, clear authorship)
    #:   3 – Community (forums, aggregators, social RSS)
    source_tier: int = 2

    @abstractmethod
    def fetch(
        self,
        *,
        user_agent: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> SourceFetchResult:
        """Fetch latest items from the source.

        Parameters
        ----------
        user_agent:
            Transparent user-agent identifying the bot.
        etag, last_modified:
            Values from the previous successful fetch for Conditional GET.
        """
