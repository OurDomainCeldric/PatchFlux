from __future__ import annotations

from datetime import UTC, datetime, timedelta

from function_app import STALE_WINDOW, _classify_source_state


def test_disabled_source_is_classified_as_disabled() -> None:
    now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
    assert (
        _classify_source_state(
            source_id="reddit-microsoft",
            last_status=None,
            last_attempt_at=None,
            last_success_at=None,
            now=now,
        )
        == "disabled"
    )


def test_never_fetched_source_is_classified_as_never() -> None:
    now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
    assert (
        _classify_source_state(
            source_id="msrc",
            last_status=None,
            last_attempt_at=None,
            last_success_at=None,
            now=now,
        )
        == "never"
    )


def test_recent_error_is_classified_as_error() -> None:
    now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
    recent = now - timedelta(hours=1)
    assert (
        _classify_source_state(
            source_id="msrc",
            last_status="error",
            last_attempt_at=recent,
            last_success_at=recent,
            now=now,
        )
        == "error"
    )


def test_missing_recent_attempt_is_classified_as_timer_not_firing() -> None:
    now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
    old = now - STALE_WINDOW - timedelta(minutes=5)
    assert (
        _classify_source_state(
            source_id="msrc",
            last_status="ok",
            last_attempt_at=old,
            last_success_at=old,
            now=now,
        )
        == "timer_not_firing"
    )


def test_recent_attempt_with_old_success_is_classified_as_stale() -> None:
    now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
    assert (
        _classify_source_state(
            source_id="msrc",
            last_status="ok",
            last_attempt_at=now - timedelta(hours=1),
            last_success_at=now - STALE_WINDOW - timedelta(minutes=5),
            now=now,
        )
        == "stale"
    )


def test_not_modified_is_classified_separately() -> None:
    now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
    recent = now - timedelta(minutes=20)
    assert (
        _classify_source_state(
            source_id="github-blog",
            last_status="not_modified",
            last_attempt_at=recent,
            last_success_at=recent,
            now=now,
        )
        == "not_modified"
    )


def test_recent_success_is_classified_as_ok() -> None:
    now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
    recent = now - timedelta(minutes=20)
    assert (
        _classify_source_state(
            source_id="github-blog",
            last_status="ok",
            last_attempt_at=recent,
            last_success_at=recent,
            now=now,
        )
        == "ok"
    )
