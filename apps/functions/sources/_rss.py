"""Shared helpers for RSS/Atom-based source adapters."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

import feedparser
import httpx

from models.news_item import NewsItem
from sources.base import SourceFetchResult

log = logging.getLogger(__name__)

# Shared Microsoft / IT-scope keyword gate. Used by general-news adapters
# (heise, bleeping_computer, krebs, cisa, borns-it, cisa-kev) to filter out
# non-Microsoft items before they enter storage. Matching is case-insensitive
# against the item title only — we never inspect article bodies.
MICROSOFT_TITLE_KEYWORDS: tuple[str, ...] = (
    "microsoft",
    "windows",
    "azure",
    "office",
    "microsoft 365",
    "m365",
    "office 365",
    "teams",
    "outlook",
    "exchange",
    "sharepoint",
    "onedrive",
    "intune",
    "entra",
    "azure ad",
    "active directory",
    "defender",
    "sentinel",
    "purview",
    "copilot",
    "xbox",
    "github",
    ".net",
    "dotnet",
    "visual studio",
    "vscode",
    "vs code",
    "powershell",
    "hyper-v",
    "hyperv",
    "wsl",
    "sql server",
    "power platform",
    "power automate",
    "power apps",
    "power bi",
    "dynamics 365",
    "dynamics365",
    "fabric",
    "viva",
    "loop",
    "sysinternals",
    "edge browser",
    "microsoft edge",
    "bitlocker",
    "winget",
    "patch tuesday",
)

# Simple keyword -> product mapping. Matching is case-insensitive against the
# item title only (never against article body, which we do not store).
PRODUCT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "azure": ("azure",),
    "windows-server": ("windows server",),
    "windows": ("windows 10", "windows 11", "windows"),
    "microsoft-365": ("microsoft 365", "m365", "office 365"),
    "teams": ("teams",),
    "exchange": ("exchange",),
    "sharepoint": ("sharepoint",),
    "outlook": ("outlook",),
    "onedrive": ("onedrive",),
    "intune": ("intune",),
    "entra": ("entra", "azure ad", "azure active directory"),
    "defender": ("defender",),
    "sentinel": ("sentinel",),
    "purview": ("purview",),
    "sql-server": ("sql server",),
    "power-platform": ("power platform", "power automate", "power apps", "power bi"),
    "fabric": ("microsoft fabric", "fabric "),
    "dynamics-365": ("dynamics 365", "dynamics365", "d365"),
    "viva": ("microsoft viva", "viva engage"),
    "loop": ("microsoft loop", "ms loop"),
    "powershell": ("powershell",),
    "visual-studio": ("visual studio",),
    "vs-code": ("vs code", "vscode", "visual studio code"),
    "wsl": ("wsl", "windows subsystem for linux"),
    "hyper-v": ("hyper-v", "hyperv"),
    "xbox": ("xbox",),
    "copilot": ("copilot",),
    "github": ("github",),
    "dotnet": (".net", "dotnet"),
}


def extract_products(title: str) -> tuple[str, ...]:
    haystack = title.lower()
    found = {
        product
        for product, needles in PRODUCT_KEYWORDS.items()
        if any(n in haystack for n in needles)
    }
    return tuple(sorted(found))


def _parse_published(entry: feedparser.FeedParserDict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key)
        if value:
            return datetime(*value[:6], tzinfo=UTC)
    return None


def fetch_feed(
    url: str,
    *,
    user_agent: str,
    etag: str | None = None,
    last_modified: str | None = None,
    timeout: float = 20.0,
) -> tuple[int, str | None, str | None, bytes]:
    """Fetch a feed URL with Conditional GET. Returns (status, etag, last_modified, body)."""
    headers = {"User-Agent": user_agent, "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5"}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url, headers=headers)

    return (
        response.status_code,
        response.headers.get("ETag"),
        response.headers.get("Last-Modified"),
        response.content,
    )


def parse_feed_to_items(
    body: bytes,
    *,
    source_id: str,
    source_name: str,
    default_language: str = "en",
    title_keywords: tuple[str, ...] | None = None,
) -> list[NewsItem]:
    """Parse a feed body into NewsItems. Skips entries without URL/title/date.

    If ``title_keywords`` is given, only entries whose title contains at least
    one of the keywords (case-insensitive) are kept. This is used for broad
    feeds (e.g. Heise newsticker) to narrow down to the project's topic.
    """
    feed = feedparser.parse(body)
    items: list[NewsItem] = []
    needles = tuple(k.lower() for k in title_keywords) if title_keywords else None
    for entry in feed.entries:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        published = _parse_published(entry)
        if not title or not link or not published:
            continue
        if needles is not None:
            low = title.lower()
            if not any(n in low for n in needles):
                continue

        author = None
        if entry.get("author"):
            author = str(entry.get("author")).strip() or None

        language = default_language
        entry_lang = entry.get("language") or getattr(feed.feed, "language", None)
        if isinstance(entry_lang, str):
            low = entry_lang.lower()
            if low.startswith("de"):
                language = "de"
            elif low.startswith("en"):
                language = "en"

        try:
            item = NewsItem(
                title=title[:300],
                published_at=published,
                source_id=source_id,
                source_name=source_name,
                author=author,
                canonical_url=link,
                products=extract_products(title),
                tags=(),
                language=language,
            )
        except Exception as exc:  # noqa: BLE001 — log & skip malformed entries
            log.warning("Skipping malformed entry from %s: %s", source_id, exc)
            continue
        items.append(item)
    return items


def fetch_and_parse(
    *,
    url: str,
    source_id: str,
    source_name: str,
    user_agent: str,
    etag: str | None = None,
    last_modified: str | None = None,
    default_language: str = "en",
    title_keywords: tuple[str, ...] | None = None,
) -> SourceFetchResult:
    try:
        status, new_etag, new_last_modified, body = fetch_feed(
            url, user_agent=user_agent, etag=etag, last_modified=last_modified
        )
    except httpx.HTTPError as exc:
        return SourceFetchResult(source_id=source_id, status="error", error=str(exc))

    if status == 304:  # Not Modified
        return SourceFetchResult(
            source_id=source_id,
            items=[],
            etag=etag,
            last_modified=last_modified,
            status="not_modified",
        )
    if status >= 400:
        return SourceFetchResult(
            source_id=source_id,
            status="error",
            error=f"HTTP {status}",
        )

    items = parse_feed_to_items(
        body,
        source_id=source_id,
        source_name=source_name,
        default_language=default_language,
        title_keywords=title_keywords,
    )
    return SourceFetchResult(
        source_id=source_id,
        items=items,
        etag=new_etag,
        last_modified=new_last_modified,
        status="ok",
    )
