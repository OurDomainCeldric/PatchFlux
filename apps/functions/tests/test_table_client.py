"""Pagination cursor + query filter tests for the storage layer."""
from __future__ import annotations

from datetime import datetime, timezone

from storage.table_client import (
    _row_key,
    decode_cursor,
    encode_cursor,
)


def test_cursor_round_trip():
    cursor = encode_cursor(year=2026, month=4, last_row_key="0123456789_abcdef12")
    assert decode_cursor(cursor) == (2026, 4, "0123456789_abcdef12")


def test_decode_cursor_rejects_garbage():
    assert decode_cursor("!!!not-valid!!!") is None
    assert decode_cursor("") is None


def test_row_key_is_monotonic_and_newer_first():
    older = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    newer = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
    rk_older = _row_key(older, "aabbccdd")
    rk_newer = _row_key(newer, "aabbccdd")
    # Newer item has SMALLER inverted timestamp, therefore smaller RowKey
    # (lexicographic / numeric equivalent since width is fixed).
    assert rk_newer < rk_older
