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
        "community",
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


def test_changes_consuming_minutes() -> None:
    assert "changes" in compute_topics(
        "GitHub Copilot code review will start consuming GitHub Actions minutes on June 1, 2026"
    )


def test_compliance_flex_routing() -> None:
    topics = compute_topics("Microsoft enables Flex Routing for Copilot in EU")
    assert "compliance" in topics


def test_compliance_dsgvo() -> None:
    assert "compliance" in compute_topics("DSGVO-konforme Konfiguration für Exchange")


def test_outage_incident() -> None:
    assert "outage" in compute_topics("Azure outage affecting EU regions")


def test_outage_sign_in_failures() -> None:
    assert "outage" in compute_topics(
        "Microsoft says Outlook.com outage is causing sign-in failures"
    )


def test_security_flaw_and_patches() -> None:
    topics = compute_topics(
        "Microsoft releases emergency patches for critical ASP.NET flaw"
    )
    assert "security" in topics
    assert "cve" not in topics


def test_boring_title_has_no_topics() -> None:
    assert compute_topics("Weekly wrap: community events in May") == ()


def test_cisa_advisories_source_is_security() -> None:
    topics = compute_topics("ICS Advisory: Widget HMI", source_id="cisa-advisories")
    assert "security" in topics


def test_cisa_kev_source_is_cve_only() -> None:
    # KEV source auto-tags as cve; the cve/security mutual exclusion still
    # applies, so security must not be present.
    topics = compute_topics("Windows Kernel EoP Vulnerability", source_id="cisa-kev")
    assert "cve" in topics
    assert "security" not in topics


def test_ms_security_blog_source_is_security() -> None:
    topics = compute_topics("Threat intel report on XYZ actor", source_id="ms-security-blog")
    assert "security" in topics


def test_github_blog_source_is_new_features_and_changes() -> None:
    topics = compute_topics("Dependabot now supports npm workspaces", source_id="github-blog")
    assert "new-features" in topics
    assert "changes" in topics
