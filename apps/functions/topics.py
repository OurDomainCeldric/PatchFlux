"""Topic classification for news items.

Each news item can belong to zero, one, or many topics. Classification uses
title keywords only — we never inspect article bodies, per the legal
guardrails in ``LEGAL.md``.

Available topics
----------------
- ``new-features``  Launches, GA, public preview, rollout, "now available".
- ``changes``       Deprecations, retirements, price/license changes, updates.
- ``cve``           Bare CVE advisories (``CVE-YYYY-NNNN`` in the title).
- ``security``      Vulnerabilities, exploits, zero-days, patches, attacks.
- ``compliance``    EU / DE regulatory, data residency, sovereignty, GDPR,
                    DSGVO, BSI, flex routing, EU AI Act.
- ``outage``        Incidents, disruptions, degradations, outages.
"""
from __future__ import annotations

import re

Topic = str

_TOPIC_PATTERNS: dict[Topic, tuple[re.Pattern[str], ...]] = {
    "new-features": tuple(
        re.compile(p, re.IGNORECASE)
        for p in (
            r"\bnow (generally )?available\b",
            r"general availability\b",
            r"\bga\b",
            r"public preview\b",
            r"private preview\b",
            r"\blaunch(?:ing|ed)?\b",
            r"\bannouncing\b",
            r"\bintroduc(?:ing|es)\b",
            r"\broll(?:ing)?[\s\-]?out\b",
            r"\brelease[d]?\b",
            r"\bneu(?:e|er|es)?\b",  # DE: "neu", "neue", …
            r"ab sofort verf",  # DE: "ab sofort verfügbar"
            r"\bverf[uü]gbar\b",
        )
    ),
    "changes": tuple(
        re.compile(p, re.IGNORECASE)
        for p in (
            r"\bdeprecat",
            r"\bretir(?:ed|ement|ing)\b",
            r"end of support\b",
            r"out of support\b",
            r"\bprice (change|update|increase)\b",
            r"\bpricing (update|change|model)\b",
            r"\blicense (change|update|model)\b",
            r"\blizenz",  # DE: Lizenz-*
            r"breaking change\b",
            r"\bsunset\b",
            r"end of life\b",
            r"\beol\b",
            r"\beingestellt\b",  # DE: discontinued
            r"\babgek[uü]ndigt\b",
            r"cumulative update\b",
            r"\bpatch tuesday\b",
        )
    ),
    "cve": (re.compile(r"\bcve[\s\-]\d{4}[\s\-]\d+\b", re.IGNORECASE),),
    "security": tuple(
        re.compile(p, re.IGNORECASE)
        for p in (
            r"\bvulnerabilit",
            r"\bschwachstelle",
            r"\bsicherheitsl[uü]cke",
            r"\bzero[\s\-]?day\b",
            r"\bactively exploited\b",
            r"\bexploited in the wild\b",
            r"\bunder (active )?attack\b",
            r"\bemergency (patch|update|release)\b",
            r"\bout[\s\-]of[\s\-]band\b",
            r"\battack",
            r"\bmalware\b",
            r"\bransomware\b",
            r"\bbreach\b",
            r"\bleak\b",
            r"\bphishing\b",
            r"\bbackdoor\b",
            r"\bpatch (now|immediately|asap)\b",
            r"\badvisory\b",
        )
    ),
    "compliance": tuple(
        re.compile(p, re.IGNORECASE)
        for p in (
            r"eu[\s\-]data[\s\-]boundary\b",
            r"\bdata residency\b",
            r"\bsovereign(?:ty|\s+cloud)\b",
            r"\beu[\s\-]cloud\b",
            r"\beu region\b",
            r"\bdeutschland\b",
            r"\bgermany\b",
            r"\bdsgvo\b",
            r"\bgdpr\b",
            r"\bbsi\b",
            r"\bschrems\b",
            r"\bflex[\s\-]?routing\b",
            r"\beu ai act\b",
            r"\bai act\b",
            r"\bcompliance\b",
            r"\bregulator",
            r"\bdatenschutz\b",
        )
    ),
    "outage": tuple(
        re.compile(p, re.IGNORECASE)
        for p in (
            r"\boutage\b",
            r"\bincident\b",
            r"\bservice disruption\b",
            r"\bdisruption\b",
            r"\bdegrad(ed|ation)\b",
            r"\bdown\s+for\b",
            r"\bstörung\b",
            r"\bausfall\b",
        )
    ),
}

# Sources whose entire output always belongs to these topics, irrespective of
# the headline wording.
_SOURCE_TOPICS: dict[str, tuple[Topic, ...]] = {
    "msrc": ("cve",),
    "m365-roadmap": ("new-features", "changes"),
    "azure-updates": ("new-features", "changes"),
    "cisa-advisories": ("security",),
    "cisa-kev": ("cve",),
    "ms-security-blog": ("security",),
    "github-blog": ("new-features", "changes"),
    "reddit-sysadmin": ("community",),
    "reddit-microsoft": ("community",),
}

ALL_TOPICS: tuple[Topic, ...] = (
    "new-features",
    "changes",
    "cve",
    "security",
    "compliance",
    "outage",
    "community",
)


def compute_topics(title: str, source_id: str = "") -> tuple[Topic, ...]:
    """Return a sorted, de-duplicated tuple of topic ids for the given item."""
    found: set[Topic] = set()
    if title:
        for topic, patterns in _TOPIC_PATTERNS.items():
            if any(p.search(title) for p in patterns):
                found.add(topic)
    for topic in _SOURCE_TOPICS.get(source_id, ()):
        found.add(topic)
    # CVEs are a separate bucket: items tagged ``cve`` are never also ``security``.
    # This keeps the "Security" filter focused on non-CVE security news
    # (zero-days, patches, malware, advisories).
    if "cve" in found:
        found.discard("security")
    return tuple(sorted(found))
