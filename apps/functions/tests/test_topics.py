"""Tests for topics.compute_topics."""
from __future__ import annotations

from topics import ALL_TOPICS, compute_topics


def test_all_topics_is_stable() -> None:
    assert ALL_TOPICS == (
        "new-features",
        "changes",
        "cve",
        "security",
        "compliance",
        "outage",
    )


def test_cve_does_not_imply_security() -> None:
    topics = compute_topics("CVE-2026-12345 Windows EoP Vulnerability")
    assert "cve" in topics
    # CVE items are never also tagged security, even when the title contains
    # security keywords like "vulnerability".
    assert "security" not in topics


def test_bare_cve_is_not_security() -> None:
    topics = compute_topics("CVE-2026-00001")
    assert "cve" in topics
    assert "security" not in topics


def test_msrc_source_is_cve_only() -> None:
    topics = compute_topics("Advisory update", source_id="msrc")
    assert "cve" in topics
    assert "security" not in topics


def test_non_cve_security_still_tagged() -> None:
    # Non-CVE security news must still be tagged "security".
    topics = compute_topics("Ungepatchte Windows-Zero-Days under active attack")
    assert "security" in topics
    assert "cve" not in topics


def test_new_features_ga() -> None:
    assert "new-features" in compute_topics(
        "Microsoft Teams custom apps now generally available"
    )


def test_changes_deprecation() -> None:
    assert "changes" in compute_topics("Azure Functions v3 retirement in 2027")


def test_compliance_flex_routing() -> None:
    topics = compute_topics("Microsoft enables Flex Routing for Copilot in EU")
    assert "compliance" in topics


def test_compliance_dsgvo() -> None:
    assert "compliance" in compute_topics("DSGVO-konforme Konfiguration für Exchange")


def test_outage_incident() -> None:
    assert "outage" in compute_topics("Azure outage affecting EU regions")


def test_boring_title_has_no_topics() -> None:
    assert compute_topics("Weekly wrap: community events in May") == ()
