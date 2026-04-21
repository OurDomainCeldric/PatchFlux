"""Tests for the CISA KEV JSON adapter."""
from __future__ import annotations

import json

from sources.cisa_kev import CISAKEVAdapter, parse_kev_payload


def _sample_payload() -> bytes:
    payload = {
        "title": "CISA Catalog of Known Exploited Vulnerabilities",
        "catalogVersion": "2026.04.21",
        "dateReleased": "2026-04-21T12:00:00.000Z",
        "count": 2,
        "vulnerabilities": [
            {
                "cveID": "CVE-2026-11111",
                "vendorProject": "Microsoft",
                "product": "Windows",
                "vulnerabilityName": "Windows UPnP Elevation of Privilege",
                "dateAdded": "2026-04-20",
                "shortDescription": "This will be ignored by the adapter.",
                "requiredAction": "Apply updates.",
                "dueDate": "2026-05-11",
                "knownRansomwareCampaignUse": "Unknown",
            },
            {
                "cveID": "CVE-2026-22222",
                "vendorProject": "Fortinet",
                "product": "FortiOS",
                "vulnerabilityName": "Authentication bypass",
                "dateAdded": "2026-04-18",
            },
            # Malformed entry — missing dateAdded — must be skipped.
            {
                "cveID": "CVE-2026-33333",
                "vendorProject": "Acme",
                "product": "Thing",
            },
        ],
    }
    return json.dumps(payload).encode("utf-8")


def test_parse_kev_payload_happy_path() -> None:
    items = parse_kev_payload(_sample_payload())
    # The Fortinet entry is filtered out because PatchFlux is Microsoft-scoped.
    assert len(items) == 1
    titles = [i.title for i in items]
    assert all(t.startswith("KEV: ") for t in titles)
    assert any("CVE-2026-11111" in t for t in titles)
    assert not any("CVE-2026-22222" in t for t in titles)
    # All items link to the NVD detail page.
    for item in items:
        assert str(item.canonical_url).startswith("https://nvd.nist.gov/vuln/detail/CVE-")
        assert item.source_id == "cisa-kev"
        assert item.language == "en"


def test_parse_kev_payload_sorted_newest_first() -> None:
    payload = {
        "vulnerabilities": [
            {
                "cveID": "CVE-2026-A",
                "vendorProject": "Microsoft",
                "product": "Windows",
                "vulnerabilityName": "A",
                "dateAdded": "2026-04-20",
            },
            {
                "cveID": "CVE-2026-B",
                "vendorProject": "Microsoft",
                "product": "Exchange",
                "vulnerabilityName": "B",
                "dateAdded": "2026-04-18",
            },
        ]
    }
    items = parse_kev_payload(json.dumps(payload).encode("utf-8"))
    assert len(items) == 2
    assert items[0].published_at >= items[1].published_at


def test_parse_kev_payload_skips_malformed() -> None:
    items = parse_kev_payload(_sample_payload())
    assert all("CVE-2026-33333" not in i.title for i in items)


def test_parse_kev_payload_filters_non_microsoft_vendors() -> None:
    payload = {
        "vulnerabilities": [
            {
                "cveID": "CVE-2026-99999",
                "vendorProject": "Fortinet",
                "product": "FortiOS",
                "vulnerabilityName": "Authentication bypass",
                "dateAdded": "2026-04-18",
            },
            {
                "cveID": "CVE-2026-88888",
                "vendorProject": "Cisco",
                "product": "IOS XE",
                "vulnerabilityName": "Privilege escalation",
                "dateAdded": "2026-04-17",
            },
        ]
    }
    items = parse_kev_payload(json.dumps(payload).encode("utf-8"))
    assert items == []



def test_adapter_metadata_is_stable() -> None:
    assert CISAKEVAdapter.source_id == "cisa-kev"
    assert CISAKEVAdapter.source_name == "CISA KEV"
    assert CISAKEVAdapter.feed_url.startswith("https://www.cisa.gov/")
