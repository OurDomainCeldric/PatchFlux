"""Adapter smoke tests: every registered adapter must declare valid metadata."""
from __future__ import annotations

import re

from sources.azure_updates import AzureUpdatesAdapter
from sources.borns_it import BornsITAdapter
from sources.heise import HeiseAdapter
from sources.m365_roadmap import M365RoadmapAdapter
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
