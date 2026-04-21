"""NewsItem domain model — legally-safe metadata only.

IMPORTANT: This model is a *whitelist*. Adding fields that carry third-party
article content (body, snippet, summary, description, image_url, …) violates
the project's legal guardrails (see LEGAL.md) and will be rejected in review.
"""
from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

# Tracking query parameters to strip for canonicalization / deduplication.
_TRACKING_PARAM_PREFIXES = ("utm_",)
_TRACKING_PARAMS = {
    "gclid", "fbclid", "mc_cid", "mc_eid", "yclid", "msclkid", "ref", "ref_src",
}


def normalize_url(url: str) -> str:
    """Return a canonical form of *url* suitable for deduplication.

    Drops fragments, lowercases scheme/host, strips common tracking params,
    and sorts remaining query parameters.
    """
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    # Remove default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    kept_query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if k.lower() not in _TRACKING_PARAMS
        and not any(k.lower().startswith(p) for p in _TRACKING_PARAM_PREFIXES)
    ]
    kept_query.sort()
    query = urlencode(kept_query)

    path = re.sub(r"/+", "/", parts.path) or "/"
    # Strip trailing slash except for root
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    return urlunsplit((scheme, netloc, path, query, ""))


def compute_dedup_hash(url: str, title: str) -> str:
    """SHA-256 hash over canonical URL and lower-cased title."""
    normalized = normalize_url(url)
    payload = f"{normalized}\n{title.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class NewsItem(BaseModel):
    """Legally-safe metadata record for a single news item.

    Any attempt to set an unknown field (e.g. `body`, `content`, `summary`,
    `description`, `snippet`, `image_url`) raises a validation error at
    construction time thanks to ``extra='forbid'``.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    title: str = Field(min_length=1, max_length=300)
    published_at: datetime
    source_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9\-]+$")
    source_name: str = Field(min_length=1, max_length=128)
    author: str | None = Field(default=None, max_length=200)
    canonical_url: HttpUrl
    products: tuple[str, ...] = Field(default_factory=tuple)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    language: Literal["de", "en"] = "en"

    @field_validator("published_at")
    @classmethod
    def _ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @field_validator("products", "tags", mode="before")
    @classmethod
    def _coerce_sequence(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return tuple(v.strip().lower() for v in value.split(",") if v.strip())
        if isinstance(value, (list, tuple, set)):
            return tuple(sorted({str(v).strip().lower() for v in value if str(v).strip()}))
        raise TypeError(f"Unsupported type for products/tags: {type(value)!r}")

    @property
    def dedup_hash(self) -> str:
        return compute_dedup_hash(str(self.canonical_url), self.title)
