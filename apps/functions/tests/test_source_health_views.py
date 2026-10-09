from __future__ import annotations

from datetime import UTC, datetime

import function_app


class _FakeStore:
    def list_source_health(self):  # noqa: ANN201
        now = datetime.now(UTC).replace(microsecond=0)
        yield {
            "RowKey": "msrc",
            "LastStatus": "not_modified",
            "LastFetchAt": now,
            "ItemsLastRun": 0,
        }


def test_legacy_last_fetch_is_used_as_last_attempt(monkeypatch) -> None:
    monkeypatch.setattr(function_app, "_store", lambda: _FakeStore())
    views = function_app._list_source_health_views()
    msrc = next(view for view in views if view.source_id == "msrc")
    assert msrc.state == "not_modified"
    assert msrc.last_attempt_at == msrc.last_success_at
