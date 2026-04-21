"""Legal guardrail + dedup hash tests for NewsItem."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from models.news_item import NewsItem, compute_dedup_hash, normalize_url


def _base_kwargs() -> dict:
    return dict(
        title="Patch KB12345 fixes issue X",
        published_at=datetime(2026, 4, 20, 12, 0, tzinfo=UTC),
        source_id="m365-roadmap",
        source_name="Microsoft 365 Roadmap",
        canonical_url="https://example.com/path/article",
    )


def test_newsitem_minimal_ok():
    item = NewsItem(**_base_kwargs())
    assert item.title.startswith("Patch")
    assert item.dedup_hash
    assert item.published_at.tzinfo is not None


@pytest.mark.parametrize(
    "forbidden_field",
    ["body", "content", "summary", "description", "snippet", "image_url"],
)
def test_newsitem_rejects_forbidden_fields(forbidden_field: str):
    """Core legal guardrail: body/snippet/etc. must never be accepted."""
    kwargs = _base_kwargs()
    kwargs[forbidden_field] = "Some copyrighted article text"
    with pytest.raises(ValidationError):
        NewsItem(**kwargs)


def test_dedup_hash_ignores_utm_tracking():
    a = compute_dedup_hash(
        "https://example.com/a?utm_source=x&utm_medium=rss", "Same Title"
    )
    b = compute_dedup_hash("https://example.com/a", "Same Title")
    assert a == b


def test_dedup_hash_ignores_fragment_and_case():
    a = compute_dedup_hash("https://Example.COM/A/#section", "Title")
    b = compute_dedup_hash("https://example.com/a", "Title")
    assert a == b


def test_dedup_hash_differs_for_different_titles():
    a = compute_dedup_hash("https://example.com/a", "Title one")
    b = compute_dedup_hash("https://example.com/a", "Title two")
    assert a != b


def test_normalize_url_sorts_query():
    assert normalize_url("https://e.com/p?b=2&a=1") == normalize_url("https://e.com/p?a=1&b=2")


def test_products_and_tags_coerce_and_sort():
    item = NewsItem(
        **_base_kwargs(),
        products=["Azure", "azure", " Teams "],
        tags="security, preview",
    )
    assert item.products == ("azure", "teams")
    assert item.tags == ("security", "preview")


def test_naive_datetime_assumed_utc():
    kwargs = _base_kwargs()
    kwargs["published_at"] = datetime(2026, 4, 20, 12, 0)
    item = NewsItem(**kwargs)
    assert item.published_at.tzinfo == UTC
