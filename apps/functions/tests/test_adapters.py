"""Adapter smoke tests: every registered adapter must declare valid metadata."""
from __future__ import annotations

import re

from sources.azure_updates import AzureUpdatesAdapter
from sources.bleeping_computer import BleepingComputerAdapter
from sources.borns_it import BornsITAdapter
from sources.cisa import CISAAdvisoriesAdapter
from sources.cisa_kev import CISAKEVAdapter
from sources.github_blog import GitHubBlogAdapter
from sources.heise import HeiseAdapter
from sources.krebs import KrebsAdapter
from sources.m365_roadmap import M365RoadmapAdapter
from sources.ms_security_blog import MSSecurityBlogAdapter
from sources.msrc import MSRCAdapter
from sources.tech_community import TechCommunityAdapter
from sources.windows_blog import WindowsBlogAdapter, WindowsITProBlogAdapter

ALL_ADAPTERS = [
    M365RoadmapAdapter,
    AzureUpdatesAdapter,
    MSRCAdapter,
    TechCommunityAdapter,
    WindowsBlogAdapter,
    WindowsITProBlogAdapter,
    MSSecurityBlogAdapter,
    GitHubBlogAdapter,
    CISAAdvisoriesAdapter,
    CISAKEVAdapter,
    BleepingComputerAdapter,
    KrebsAdapter,
    HeiseAdapter,
    BornsITAdapter,
]

SOURCE_ID_RE = re.compile(r"^[a-z0-9-]+$")


def test_unique_source_ids():
    ids = [cls.source_id for cls in ALL_ADAPTERS]
    assert len(ids) == len(set(ids)), "Duplicate source_ids in registered adapters"


def test_source_id_pattern():
    for cls in ALL_ADAPTERS:
        assert SOURCE_ID_RE.match(cls.source_id), f"{cls.__name__}: bad source_id"


def test_feed_urls_look_reasonable():
    for cls in ALL_ADAPTERS:
        url = cls.feed_url
        assert url.startswith("https://"), f"{cls.__name__}: non-https feed URL"
        assert " " not in url, f"{cls.__name__}: whitespace in feed URL"


def test_general_news_adapters_declare_microsoft_keyword_filter():
    """Adapters for general (non-Microsoft-first) feeds must filter by title
    keywords so PatchFlux stays Microsoft-scoped. See AGENTS.md."""
    from sources._rss import MICROSOFT_TITLE_KEYWORDS

    general_news = [
        HeiseAdapter,
        BornsITAdapter,
        BleepingComputerAdapter,
        KrebsAdapter,
        CISAAdvisoriesAdapter,
    ]
    for cls in general_news:
        kws = getattr(cls, "title_keywords", None)
        assert kws, f"{cls.__name__}: missing title_keywords"
        assert "microsoft" in kws, f"{cls.__name__}: no 'microsoft' keyword"
        # Every general-news adapter reuses the shared list (allows overrides,
        # but we expect full coverage today).
        assert set(MICROSOFT_TITLE_KEYWORDS).issubset(set(kws)), (
            f"{cls.__name__}: title_keywords missing shared Microsoft terms"
        )
