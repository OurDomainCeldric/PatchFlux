"""Priority scoring for news items.

The score is derived **only from the headline** (which we already store) and
from the source id. We never look at article bodies — those are not stored
per the legal guardrails in ``LEGAL.md``.

Levels
------
0  Normal
1  Notable — GA announcements, deprecations, pricing/licensing changes,
   outages, generic CVE references, retirements.
2  Hot — actively exploited vulnerabilities, critical CVSS, EU/DE-specific
   regulatory or residency topics (Data Boundary, sovereign cloud, DSGVO/GDPR,
   flex routing, BSI, EU AI Act).
"""
from __future__ import annotations

import re

# Level-2 ("hot") patterns: security criticality + EU/DE/compliance relevance.
_HOT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        # Security criticality
        r"zero[\s\-]?day",
        r"actively exploited",
        r"under (active )?attack",
        r"exploited in the wild",
        r"emergency (patch|update|release)",
        r"out[\s\-]of[\s\-]band",
        r"critical (vulnerability|flaw|bug|rce|remote code)",
        r"kritische? (schwachstelle|sicherheitsl[üu]cke)",
        r"cvss[:\s]*([9](\.\d+)?|10(\.0)?)\b",
        r"patch (now|immediately|asap)",
        # EU / Germany / regulatory relevance
        r"eu[\s\-]data[\s\-]boundary",
        r"data residency",
        r"sovereign cloud",
        r"sovereignty",
        r"eu region",
        r"\beu[\s\-]cloud\b",
        r"\bgermany\b",
        r"\bdeutschland\b",
        r"german regulator",
        r"\bdsgvo\b",
        r"\bgdpr\b",
        r"\bbsi\b",
        r"schrems",
        r"flex[\s\-]?routing",
        r"eu ai act",
        r"ai act",
    )
)

# Level-1 ("notable") patterns: major lifecycle / announcements.
_NOTABLE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"general availability",
        r"\bga\b",
        r"now (generally )?available",
        r"public preview",
        r"deprecat",
        r"retir(ed|ement|ing)",
        r"end of support",
        r"out of support",
        r"price (change|update|increase)",
        r"pricing (update|change)",
        r"license (change|update|model)",
        r"\boutage\b",
        r"\bbreach\b",
        r"\bleak\b",
        r"\bcve[\s\-]\d",
        r"patch tuesday",
        r"preview to ga",
    )
)

# Sources whose content is security-critical by definition; bump any match
# on a NOTABLE pattern (or a bare CVE) to HOT.
_SECURITY_SOURCES = frozenset({"msrc"})

# Sources whose every item is, by definition, actively exploited / critical.
# CISA KEV is the canonical example: inclusion in the catalog means active
# exploitation in the wild, which is exactly our "hot" criterion.
_ALWAYS_HOT_SOURCES = frozenset({"cisa-kev"})


def compute_priority(title: str, source_id: str = "") -> int:
    """Return 0 (normal), 1 (notable), or 2 (hot) for the given headline.

    The MSRC feed is entirely CVEs — marking every CVE as "hot" would drown
    out the genuinely critical items (zero-days, RCEs, CVSS 9+ advisories,
    EU-specific compliance topics). Therefore MSRC titles are only ever
    *notable* by default and must match an explicit hot pattern to be
    promoted to level 2.
    """
    if source_id in _ALWAYS_HOT_SOURCES:
        return 2
    if not title:
        return 0
    if any(p.search(title) for p in _HOT_PATTERNS):
        return 2
    if any(p.search(title) for p in _NOTABLE_PATTERNS):
        return 1
    if source_id in _SECURITY_SOURCES:
        return 1
    return 0
