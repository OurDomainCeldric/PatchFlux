"""RSS/Atom parser tests using tiny inline fixtures."""
from __future__ import annotations

from sources._rss import extract_products, parse_feed_to_items

ATOM_MIN = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example</title>
  <entry>
    <title>Azure Storage gets a new feature</title>
    <link href="https://example.com/a"/>
    <updated>2026-04-10T12:00:00Z</updated>
  </entry>
  <entry>
    <title>Microsoft Teams adds Copilot actions</title>
    <link href="https://example.com/b"/>
    <updated>2026-04-09T08:30:00Z</updated>
  </entry>
  <entry>
    <title>Unrelated kernel patch</title>
    <link href="https://example.com/c"/>
    <updated>2026-04-08T01:00:00Z</updated>
  </entry>
</feed>
""".strip()


def test_parse_feed_returns_all_entries():
    items = parse_feed_to_items(
        ATOM_MIN, source_id="t", source_name="Test", default_language="en"
    )
    assert len(items) == 3
    assert items[0].title.startswith("Azure")


def test_parse_feed_title_keyword_filter():
    items = parse_feed_to_items(
        ATOM_MIN,
        source_id="t",
        source_name="Test",
        default_language="en",
        title_keywords=("azure", "teams"),
    )
    assert len(items) == 2
    assert all(
        ("azure" in i.title.lower()) or ("teams" in i.title.lower()) for i in items
    )


def test_extract_products_matches_expected_keywords():
    assert "azure" in extract_products("New Azure Storage feature")
    assert "teams" in extract_products("Microsoft Teams update")
    # Case-insensitive
    assert "copilot" in extract_products("GitHub Copilot gains new feature")
    # No false positives on random titles
    assert extract_products("Random news about cats") == ()
