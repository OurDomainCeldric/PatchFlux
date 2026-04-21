"""CISA Known Exploited Vulnerabilities (KEV) — JSON feed.

U.S. Government, public-domain data. Every entry is, by definition, actively
exploited in the wild; the priority module promotes them to ``hot``.

We fetch the JSON with Conditional GET (ETag / Last-Modified). Only headline
metadata is kept: ``title``, ``canonical_url`` (NVD link), ``published_at``
(``dateAdded``). No KEV body fields are persisted.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import httpx

from models.news_item import NewsItem
from sources._rss import MICROSOFT_TITLE_KEYWORDS
from sources.base import SourceAdapter, SourceFetchResult

log = logging.getLogger(__name__)

_FEED_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
# Limit to the newest N entries per poll; the feed holds 1000+ historical CVEs.
_MAX_ITEMS = 200

# PatchFlux is Microsoft-scoped. KEV lists advisories for all vendors (Fortinet,
# Cisco, Ivanti, Apple, \u2026) so we filter entries to those whose vendor /
# product / vulnerability-name mention a Microsoft product or platform.
_KEV_KEYWORDS: tuple[str, ...] = MICROSOFT_TITLE_KEYWORDS


def _is_microsoft_relevant(entry: dict) -> bool:
    haystack = " ".join(
        str(entry.get(key) or "")
        for key in ("vendorProject", "product", "vulnerabilityName")
    ).lower()
    if not haystack.strip():
        return False
    return any(k in haystack for k in _KEV_KEYWORDS)


def _nvd_url(cve_id: str) -> str:
    return f"https://nvd.nist.gov/vuln/detail/{cve_id}"


def _build_title(entry: dict) -> str:
    vendor = (entry.get("vendorProject") or "").strip()
    product = (entry.get("product") or "").strip()
    name = (entry.get("vulnerabilityName") or "").strip()
    cve = (entry.get("cveID") or "").strip()
    parts: list[str] = []
    if vendor or product:
        parts.append(f"{vendor} {product}".strip())
    if name:
        parts.append(name)
    if cve:
        parts.append(f"({cve})")
    title = "KEV: " + " — ".join(p for p in parts if p)
    # NewsItem max title length is 300.
    return title[:300]


def parse_kev_payload(body: bytes) -> list[NewsItem]:
    data = json.loads(body)
    vulns = data.get("vulnerabilities") or []
    items: list[NewsItem] = []
    # Sort newest-first by dateAdded, filter to Microsoft-relevant entries, and
    # cap to _MAX_ITEMS.
    vulns_sorted = sorted(
        (
            v
            for v in vulns
            if v.get("dateAdded") and v.get("cveID") and _is_microsoft_relevant(v)
        ),
        key=lambda v: v.get("dateAdded", ""),
        reverse=True,
    )[:_MAX_ITEMS]

    for entry in vulns_sorted:
        cve_id = str(entry.get("cveID") or "").strip()
        date_added = str(entry.get("dateAdded") or "").strip()
        if not cve_id or not date_added:
            continue
        try:
            published = datetime.strptime(date_added, "%Y-%m-%d").replace(
                tzinfo=UTC
            )
        except ValueError:
            continue

        title = _build_title(entry)
        try:
            item = NewsItem(
                title=title,
                published_at=published,
                source_id=CISAKEVAdapter.source_id,
                source_name=CISAKEVAdapter.source_name,
                author=None,
                canonical_url=_nvd_url(cve_id),
                products=(),
                tags=(),
                language="en",
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Skipping malformed KEV entry %s: %s", cve_id, exc)
            continue
        items.append(item)
    return items


class CISAKEVAdapter(SourceAdapter):
    source_id = "cisa-kev"
    source_name = "CISA KEV"
    feed_url = _FEED_URL

    def fetch(
        self,
        *,
        user_agent: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> SourceFetchResult:
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, */*;q=0.5",
        }
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                response = client.get(self.feed_url, headers=headers)
        except httpx.HTTPError as exc:
            return SourceFetchResult(source_id=self.source_id, status="error", error=str(exc))

        if response.status_code == 304:
            return SourceFetchResult(
                source_id=self.source_id,
                items=[],
                etag=etag,
                last_modified=last_modified,
                status="not_modified",
            )
        if response.status_code >= 400:
            return SourceFetchResult(
                source_id=self.source_id,
                status="error",
                error=f"HTTP {response.status_code}",
            )

        try:
            items = parse_kev_payload(response.content)
        except Exception as exc:  # noqa: BLE001
            return SourceFetchResult(
                source_id=self.source_id,
                status="error",
                error=f"parse error: {exc!s:.200}",
            )

        return SourceFetchResult(
            source_id=self.source_id,
            items=items,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
            status="ok",
        )
