"""Source adapters.

Each adapter implements :class:`SourceAdapter` and returns a list of
:class:`~apps.functions.models.news_item.NewsItem` without ever persisting
third-party article bodies. See LEGAL.md.
"""
from .base import SourceAdapter, SourceFetchResult  # noqa: F401
