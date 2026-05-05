from __future__ import annotations

import json
from datetime import UTC, datetime

import azure.functions as func

import function_app
from storage.table_client import QueryPage


class _FakeStore:
    def query_page(self, **_: object) -> QueryPage:
        published = datetime(2026, 4, 28, 8, 0, tzinfo=UTC)
        return QueryPage(
            items=[
                {
                    "RowKey": "1",
                    "Title": "CVE-2026-12345 Microsoft Edge Vulnerability",
                    "PublishedAt": published,
                    "SourceId": "msrc",
                    "SourceName": "Microsoft Security Response Center",
                    "SourceTier": 2,
                    "Author": "",
                    "CanonicalUrl": "https://example.com/cve",
                    "Products": "",
                    "Tags": "",
                    "Language": "en",
                },
                {
                    "RowKey": "2",
                    "Title": "Windows admins discuss April servicing rollout",
                    "PublishedAt": published,
                    "SourceId": "heise",
                    "SourceName": "heise online",
                    "SourceTier": 2,
                    "Author": "",
                    "CanonicalUrl": "https://example.com/untagged",
                    "Products": "",
                    "Tags": "",
                    "Language": "en",
                },
            ],
            next_cursor=None,
        )


def test_api_news_can_exclude_cves_without_hiding_untagged(monkeypatch) -> None:
    monkeypatch.setattr(function_app, "_store", lambda: _FakeStore())
    req = func.HttpRequest(
        method="GET",
        url="https://example.com/api/news",
        params={"exclude_topics": "cve"},
        body=b"",
    )

    response = function_app.api_news(req)
    payload = json.loads(response.get_body())

    assert response.status_code == 200
    assert payload["count"] == 1
    assert payload["items"][0]["title"] == "Windows admins discuss April servicing rollout"
