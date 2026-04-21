"""Tests for priority.compute_priority."""
from __future__ import annotations

import pytest

from priority import compute_priority


@pytest.mark.parametrize(
    "title",
    [
        "Critical RCE in Exchange — actively exploited in the wild",
        "CVSS 9.8 zero-day in Windows Defender",
        "Microsoft enables Flex Routing for Copilot in EU Data Boundary",
        "Neue kritische Sicherheitslücke in SharePoint",
        "EU AI Act: compliance impact on Azure OpenAI",
        "BSI warnt vor aktueller Lücke in Windows Server",
        "Sovereign cloud expansion reaches Germany",
        "Patch now: out-of-band fix for Outlook",
    ],
)
def test_hot_titles_score_2(title: str) -> None:
    assert compute_priority(title) == 2


@pytest.mark.parametrize(
    "title",
    [
        "Microsoft Teams custom apps now generally available",
        "Azure Functions v3 retirement in 2027",
        "Price update for Microsoft 365 business plans",
        "CVE-2026-12345 fixed in latest cumulative update",
    ],
)
def test_notable_titles_score_1(title: str) -> None:
    assert compute_priority(title) == 1


def test_msrc_cve_title_is_notable_not_hot() -> None:
    # CVE advisories without severity markers are notable (1), not hot.
    assert (
        compute_priority(
            "CVE-2026-12345 Windows UPnP Elevation of Privilege Vulnerability",
            source_id="msrc",
        )
        == 1
    )


def test_msrc_critical_title_is_hot() -> None:
    assert (
        compute_priority(
            "Critical RCE in Exchange actively exploited",
            source_id="msrc",
        )
        == 2
    )


def test_msrc_bare_title_is_at_least_notable() -> None:
    assert compute_priority("Advisory: component updated", source_id="msrc") >= 1


def test_boring_title_is_zero() -> None:
    assert compute_priority("Weekly wrap: Community events in May") == 0


def test_empty_title() -> None:
    assert compute_priority("") == 0


def test_kev_source_is_always_hot() -> None:
    # Every KEV entry is actively exploited by definition.
    assert compute_priority("KEV: Some vendor X advisory", source_id="cisa-kev") == 2


def test_kev_source_overrides_empty_title() -> None:
    assert compute_priority("", source_id="cisa-kev") == 2
