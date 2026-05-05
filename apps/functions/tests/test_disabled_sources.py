from __future__ import annotations

from function_app import DISABLED_SOURCE_IDS, _all_adapters, _is_enabled_source_id


def test_disabled_sources_are_not_enabled() -> None:
    assert "reddit-microsoft" in DISABLED_SOURCE_IDS
    assert "reddit-sysadmin" in DISABLED_SOURCE_IDS
    assert not _is_enabled_source_id("reddit-microsoft")
    assert not _is_enabled_source_id("reddit-sysadmin")


def test_disabled_sources_are_excluded_from_active_adapters() -> None:
    active_ids = {adapter.source_id for adapter in _all_adapters()}
    assert "reddit-microsoft" not in active_ids
    assert "reddit-sysadmin" not in active_ids
    assert "msrc" in active_ids
