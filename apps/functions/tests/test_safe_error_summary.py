"""Tests for the ``_safe_error_summary`` helper in ``function_app``.

This helper is the last line of defence against leaking file paths, stack
trace fragments or oversized error blobs through ``/api/sources``. Keep the
expectations tight.
"""
from __future__ import annotations

from function_app import _safe_error_summary


def test_returns_none_for_none() -> None:
    assert _safe_error_summary(None) is None


def test_empty_string_becomes_none() -> None:
    assert _safe_error_summary("") is None


def test_strips_absolute_posix_paths() -> None:
    raw = 'Traceback most recent: File "/home/site/wwwroot/sources/heise.py", line 42, in fetch'
    out = _safe_error_summary(raw)
    assert "/home/site" not in (out or "")
    assert ".py" not in (out or "")
    assert "line 42" not in (out or "")


def test_strips_windows_paths() -> None:
    raw = 'problem at C:\\Users\\x\\venv\\lib\\site-packages\\requests\\adapters.py line 512'
    out = _safe_error_summary(raw)
    assert "C:\\Users" not in (out or "")
    assert "adapters.py" not in (out or "")


def test_prefixes_exception_class_name_when_given_exception() -> None:
    exc = ValueError("boom")
    assert _safe_error_summary(exc) == "ValueError: boom"


def test_truncates_long_messages() -> None:
    out = _safe_error_summary("x" * 500, limit=40) or ""
    assert len(out) <= 40
    assert out.endswith("\u2026")
