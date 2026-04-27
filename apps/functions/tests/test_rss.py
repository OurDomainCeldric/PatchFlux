from __future__ import annotations

from datetime import UTC, datetime

from sources import _rss


def test_fetch_and_parse_retries_fallback_after_403(monkeypatch) -> None:
    published = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
    calls: list[str] = []

    def fake_fetch_feed(  # noqa: ANN001
        url,
        *,
        user_agent,
        etag=None,
        last_modified=None,
        timeout=20.0,
    ):
        calls.append(url)
        if "old.reddit.com" not in url:
            return (403, None, None, b"")
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Windows admins discuss patching</title>
      <link>https://example.com/post</link>
      <pubDate>{published.strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
    </item>
  </channel>
</rss>
""".encode("utf-8")
        return (200, "etag-2", "Mon, 27 Apr 2026 12:00:00 GMT", body)

    monkeypatch.setattr(_rss, "fetch_feed", fake_fetch_feed)

    result = _rss.fetch_and_parse(
        url="https://www.reddit.com/r/microsoft/new.rss?limit=50",
        fallback_urls=("https://old.reddit.com/r/microsoft/new.rss?limit=50",),
        source_id="reddit-microsoft",
        source_name="r/microsoft",
        user_agent="PatchFlux/1.0",
        default_language="en",
    )

    assert calls == [
        "https://www.reddit.com/r/microsoft/new.rss?limit=50",
        "https://old.reddit.com/r/microsoft/new.rss?limit=50",
    ]
    assert result.status == "ok"
    assert result.error is None
    assert result.etag == "etag-2"
    assert len(result.items) == 1
    assert result.items[0].source_id == "reddit-microsoft"
