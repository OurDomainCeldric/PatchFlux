from __future__ import annotations

from datetime import UTC, datetime, timedelta

from function_app import (
    COMMENT_BODY_MAX_CHARS,
    _comment_secret_hash,
    _comment_validation_error,
    _clean_comment_text,
    _hot_score,
)


def test_comment_validation_accepts_plain_text() -> None:
    assert _comment_validation_error("Alice", "Useful context, no link here.") is None


def test_comment_validation_rejects_missing_fields() -> None:
    assert _comment_validation_error("", "hello") == "display_name_required"
    assert _comment_validation_error("Alice", "") == "body_required"


def test_comment_validation_rejects_url_like_text() -> None:
    assert _comment_validation_error("Alice", "see https://example.com") == "links_not_allowed"
    assert _comment_validation_error("Alice", "see www.example.com") == "links_not_allowed"
    assert _comment_validation_error("Alice", "see example.com") == "links_not_allowed"


def test_comment_validation_rejects_blocked_language() -> None:
    assert _comment_validation_error("Alice", "white power") == "blocked_language"


def test_clean_comment_text_normalizes_whitespace() -> None:
    assert _clean_comment_text("  hello\r\n  world  ", max_chars=100) == "hello world"


def test_comment_secret_hash_is_stable_and_user_scoped() -> None:
    first = _comment_secret_hash("user-a", "secret")
    assert first == _comment_secret_hash("user-a", "secret")
    assert first != _comment_secret_hash("user-b", "secret")


def test_body_limit_constant_is_not_too_large_for_table_storage() -> None:
    assert COMMENT_BODY_MAX_CHARS <= 1000


def test_hot_score_cools_older_items() -> None:
    now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    fresh = {"publishedAt": (now - timedelta(hours=1)).isoformat()}
    old = {"publishedAt": (now - timedelta(days=3)).isoformat()}
    assert _hot_score(fresh, 3, now=now) > _hot_score(old, 3, now=now)
