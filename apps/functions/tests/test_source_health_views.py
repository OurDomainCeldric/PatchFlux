from __future__ import annotations

from datetime import UTC, datetime

import function_app


class _FakeStore:
    def list_source_health(self):  # noqa: ANN201
        yield {
            "RowKey": "msrc",
            "LastStatus": "not_modified",
            "LastFetchAt": datetime(2026, 4, 27, 21, 0, tzinfo=UTC),
            "ItemsLastRun": 0,
        }


def test_legacy_last_fetch_is_used_as_last_attempt(monkeypatch) -> None:
    monkeypatch.setattr(function_app, "_store", lambda: _FakeStore())
    views = function_app._list_source_health_views()
    msrc = next(view for view in views if view.source_id == "msrc")
    assert msrc.state == "not_modified"
    assert msrc.last_attempt_at == "2026-04-27T21:00:00+00:00"
