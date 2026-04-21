"""Azure Functions v2 entry point.

HTTP routes
-----------
- ``GET  /api/news``       – filtered & paginated news feed
- ``GET  /api/sources``    – source-health status list
- ``GET  /api/products``   – distinct product IDs with occurrence counts
- ``GET  /api/feed.xml``   – RSS 2.0 export (headline + URL + source only)
- ``GET  /api/atom.xml``   – Atom 1.0 export (headline + URL + source only)
- ``GET  /api/health``     – lightweight liveness probe (status, storage,
  sourcesStale[]) — anonymous, suitable for availability tests.
- ``POST|GET /api/ingest`` – trigger ingest run (FUNCTION-level key required).
  Optional ``?source=<id>`` to run a single adapter.

Timer triggers
--------------
- ``ingest_timer_high``  – every 30 min: MSRC (security)
- ``ingest_timer_mid``   – every 3 h: Heise, Borns, Tech Community, Windows blogs
- ``ingest_timer_low``   – daily 05:00 UTC: M365 Roadmap, Azure Updates
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import traceback
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape as xml_escape

import azure.functions as func

from config import get_settings
from priority import compute_priority
from topics import compute_topics
from sources.azure_updates import AzureUpdatesAdapter
from sources.base import SourceAdapter
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
from storage.table_client import NewsStore

log = logging.getLogger(__name__)

# ``/ingest`` uses a FUNCTION-level key; read endpoints are ANONYMOUS.
# Per-function auth is set on the decorators below so we keep the app default
# at ANONYMOUS for public read endpoints.
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

INTER_SOURCE_DELAY_SECONDS = 1.0

# Grouping used by both the timer triggers and ``?source=<id>`` on /ingest.
HIGH_FREQ_SOURCES = {"msrc", "cisa-kev"}
MID_FREQ_SOURCES = {
    "heise",
    "borns-it",
    "ms-tech-community",
    "windows-blog",
    "windows-it-pro-blog",
    "ms-security-blog",
    "github-blog",
    "cisa-advisories",
    "bleeping-computer",
    "krebs",
}
LOW_FREQ_SOURCES = {"m365-roadmap", "azure-updates"}

# If a source has not been fetched successfully within this window, /health
# reports it as stale.
STALE_WINDOW = timedelta(hours=26)


def _store() -> NewsStore:
    settings = get_settings()
    return NewsStore(
        connection_string=settings.table_connection,
        news_table=settings.news_table_name,
        source_health_table=settings.source_health_table_name,
    )


# Create tables on cold start so read-only endpoints don't 500 before the
# first ingest run. Safe & idempotent.
try:
    _store().ensure_tables()
except Exception:  # noqa: BLE001 — logged by Application Insights via logger
    log.exception("Failed to ensure tables during cold start")


def _all_adapters() -> list[SourceAdapter]:
    return [
        M365RoadmapAdapter(),
        AzureUpdatesAdapter(),
        MSRCAdapter(),
        TechCommunityAdapter(),
        WindowsBlogAdapter(),
        WindowsITProBlogAdapter(),
        MSSecurityBlogAdapter(),
        GitHubBlogAdapter(),
        CISAAdvisoriesAdapter(),
        CISAKEVAdapter(),
        BleepingComputerAdapter(),
        KrebsAdapter(),
        HeiseAdapter(),
        BornsITAdapter(),
    ]


def _adapters_matching(ids: Iterable[str]) -> list[SourceAdapter]:
    wanted = set(ids)
    return [a for a in _all_adapters() if a.source_id in wanted]


def _run_ingest(source_ids: Iterable[str] | None = None) -> dict:
    """Run the ingest pipeline for the selected adapters (default: all)."""
    settings = get_settings()
    store = _store()
    store.ensure_tables()

    if source_ids is None:
        adapters = _all_adapters()
    else:
        adapters = _adapters_matching(source_ids)

    totals: dict[str, int] = {}

    for index, adapter in enumerate(adapters):
        if index > 0:
            time.sleep(INTER_SOURCE_DELAY_SECONDS)

        previous = store.get_source_health(adapter.source_id) or {}
        etag = previous.get("ETag") or None
        last_modified = previous.get("LastModified") or None

        log.info("Fetching %s", adapter.source_id)
        start = time.monotonic()
        try:
            result = adapter.fetch(
                user_agent=settings.user_agent,
                etag=etag,
                last_modified=last_modified,
            )
        except Exception as exc:  # noqa: BLE001 — never let one bad source kill the run
            log.exception("Adapter %s crashed", adapter.source_id)
            tb = traceback.format_exc(limit=3)[:500]
            store.record_source_health(
                source_id=adapter.source_id,
                status="error",
                error=f"{exc}\n{tb}",
                items_last_run=0,
            )
            totals[adapter.source_id] = 0
            continue

        written = 0
        if result.items:
            written = store.upsert_many(result.items)

        store.record_source_health(
            source_id=adapter.source_id,
            status=result.status,
            error=result.error,
            etag=result.etag,
            last_modified=result.last_modified,
            items_last_run=written,
        )
        totals[adapter.source_id] = written
        duration_ms = int((time.monotonic() - start) * 1000)
        log.info(
            json.dumps(
                {
                    "event": "ingest.source",
                    "source": adapter.source_id,
                    "status": result.status,
                    "written": written,
                    "duration_ms": duration_ms,
                }
            )
        )

    return {"written": totals}


# ---- Timer triggers ---------------------------------------------------------


@app.function_name(name="ingest_timer_high")
@app.schedule(schedule="0 */30 * * * *", arg_name="timer", run_on_startup=False, use_monitor=True)
def ingest_timer_high(timer: func.TimerRequest) -> None:
    """High-frequency fetch for security sources (MSRC) every 30 min."""
    log.info("ingest_timer_high fired (past_due=%s)", timer.past_due)
    result = _run_ingest(HIGH_FREQ_SOURCES)
    log.info("ingest_timer_high done: %s", result)


@app.function_name(name="ingest_timer_mid")
@app.schedule(schedule="0 15 */3 * * *", arg_name="timer", run_on_startup=False, use_monitor=True)
def ingest_timer_mid(timer: func.TimerRequest) -> None:
    """Medium-frequency fetch for blogs & news every 3 h (offset :15)."""
    log.info("ingest_timer_mid fired (past_due=%s)", timer.past_due)
    result = _run_ingest(MID_FREQ_SOURCES)
    log.info("ingest_timer_mid done: %s", result)


@app.function_name(name="ingest_timer_low")
@app.schedule(schedule="0 0 5 * * *", arg_name="timer", run_on_startup=False, use_monitor=True)
def ingest_timer_low(timer: func.TimerRequest) -> None:
    """Daily low-frequency fetch for roadmap & update feeds at 05:00 UTC."""
    log.info("ingest_timer_low fired (past_due=%s)", timer.past_due)
    result = _run_ingest(LOW_FREQ_SOURCES)
    log.info("ingest_timer_low done: %s", result)


# ---- HTTP: admin ingest (FUNCTION-level key) --------------------------------


@app.function_name(name="ingest_http")
@app.route(route="ingest", methods=["POST", "GET"], auth_level=func.AuthLevel.FUNCTION)
def ingest_http(req: func.HttpRequest) -> func.HttpResponse:
    """Manual ingest trigger. Protected by a Function key.

    Query parameters
    ----------------
    * ``source=<id>`` – optional; run only the named adapter.
    """
    source_param = req.params.get("source")
    requested = {source_param} if source_param else None
    log.info("ingest_http triggered source=%s", source_param or "<all>")
    result = _run_ingest(requested)
    return _json_response(result)


# ---- HTTP: public read endpoints --------------------------------------------


def _parse_int(value: str | None, default: int, *, minimum: int, maximum: int) -> int:
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    # Accept "7d", "24h", or an ISO 8601 date / datetime.
    if raw.endswith("d") and raw[:-1].isdigit():
        return datetime.now(timezone.utc) - timedelta(days=int(raw[:-1]))
    if raw.endswith("h") and raw[:-1].isdigit():
        return datetime.now(timezone.utc) - timedelta(hours=int(raw[:-1]))
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _iso(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _serialize_entity(ent: dict) -> dict:
    title = ent.get("Title") or ""
    source_id = ent.get("SourceId") or ""
    return {
        "id": ent.get("RowKey"),
        "title": title,
        "publishedAt": _iso(ent.get("PublishedAt")),
        "sourceId": source_id,
        "sourceName": ent.get("SourceName"),
        "author": ent.get("Author") or None,
        "url": ent.get("CanonicalUrl"),
        "products": [p for p in (ent.get("Products") or "").split(",") if p],
        "tags": [t for t in (ent.get("Tags") or "").split(",") if t],
        "language": ent.get("Language") or "en",
        "priority": compute_priority(title, source_id),
        "topics": list(compute_topics(title, source_id)),
    }


def _etag_for(payload: bytes) -> str:
    return '"' + hashlib.sha256(payload).hexdigest()[:24] + '"'


def _json_response(
    data: dict | list,
    *,
    status_code: int = 200,
    cache_seconds: int | None = None,
    extra_headers: dict[str, str] | None = None,
) -> func.HttpResponse:
    body = json.dumps(data).encode("utf-8")
    headers: dict[str, str] = {}
    if cache_seconds is not None:
        headers["Cache-Control"] = (
            f"public, max-age={cache_seconds}, "
            f"stale-while-revalidate={cache_seconds * 2}"
        )
        headers["ETag"] = _etag_for(body)
    if extra_headers:
        headers.update(extra_headers)
    return func.HttpResponse(
        body,
        status_code=status_code,
        mimetype="application/json",
        headers=headers,
    )


@app.function_name(name="api_news")
@app.route(route="news", methods=["GET"])
def api_news(req: func.HttpRequest) -> func.HttpResponse:
    limit = _parse_int(req.params.get("limit"), default=50, minimum=1, maximum=200)
    source_id = req.params.get("source") or None
    product = req.params.get("product") or None
    language = req.params.get("lang") or None
    if language not in (None, "de", "en"):
        language = None
    since = _parse_since(req.params.get("since"))
    search = (req.params.get("q") or "").strip() or None
    deduped = _parse_bool(req.params.get("deduped"))
    cursor = req.params.get("cursor") or None
    min_priority = _parse_int(
        req.params.get("min_priority"), default=0, minimum=0, maximum=2
    )
    if _parse_bool(req.params.get("hot")):
        min_priority = max(min_priority, 2)
    topics_param = (req.params.get("topics") or "").strip()
    topics_filter: set[str] = {
        t.strip().lower() for t in topics_param.split(",") if t.strip()
    }

    store = _store()
    start = time.monotonic()
    # When filtering by priority or topics we need to scan more raw rows
    # because both filters are applied post-query.
    need_post_filter = min_priority > 0 or bool(topics_filter)
    raw_limit = limit if not need_post_filter else min(limit * 10, 500)
    page = store.query_page(
        limit=raw_limit,
        source_id=source_id,
        product=product,
        language=language,
        since=since,
        search=search,
        deduped=deduped,
        cursor=cursor,
    )
    duration_ms = int((time.monotonic() - start) * 1000)

    serialized = [_serialize_entity(e) for e in page.items]
    if min_priority > 0:
        serialized = [i for i in serialized if i["priority"] >= min_priority]
    if topics_filter:
        serialized = [
            i for i in serialized if topics_filter.intersection(i["topics"])
        ]
    if len(serialized) > limit:
        serialized = serialized[:limit]

    payload = {
        "items": serialized,
        "count": len(serialized),
        "nextCursor": page.next_cursor,
    }

    log.info(
        json.dumps(
            {
                "event": "api.news",
                "source": source_id,
                "product": product,
                "lang": language,
                "q": bool(search),
                "deduped": deduped,
                "limit": limit,
                "count": len(page.items),
                "has_cursor": cursor is not None,
                "next_cursor": page.next_cursor is not None,
                "duration_ms": duration_ms,
            }
        )
    )

    return _json_response(payload, cache_seconds=300)


@app.function_name(name="api_sources")
@app.route(route="sources", methods=["GET"])
def api_sources(req: func.HttpRequest) -> func.HttpResponse:
    include_counts = _parse_bool(req.params.get("include_counts"))
    store = _store()
    sources = []
    for ent in store.list_source_health():
        last_fetch = ent.get("LastFetchAt")
        if isinstance(last_fetch, datetime):
            last_fetch = last_fetch.isoformat()
        record = {
            "sourceId": ent.get("RowKey"),
            "lastFetchAt": last_fetch,
            "lastStatus": ent.get("LastStatus"),
            "lastError": ent.get("LastError") or None,
        }
        if include_counts:
            record["itemsLastRun"] = int(ent.get("ItemsLastRun") or 0)
        sources.append(record)
    sources.sort(key=lambda r: r["sourceId"] or "")
    return _json_response({"sources": sources}, cache_seconds=60)


@app.function_name(name="api_products")
@app.route(route="products", methods=["GET"])
def api_products(req: func.HttpRequest) -> func.HttpResponse:
    months = _parse_int(req.params.get("months"), default=3, minimum=1, maximum=12)
    counts = _store().product_counts(months_back=months)
    products = [
        {"id": pid, "count": count}
        for pid, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return _json_response({"products": products}, cache_seconds=900)


@app.function_name(name="api_topics")
@app.route(route="topics", methods=["GET"])
def api_topics(req: func.HttpRequest) -> func.HttpResponse:
    """Return tag occurrence counts over a recent window (default 14 days).

    Powers the filter chip badges in the web UI. Cached for 5 minutes.
    """
    days = _parse_int(req.params.get("days"), default=14, minimum=1, maximum=90)
    counts = _store().topic_counts(days=days)
    topics = [
        {"id": tid, "count": count}
        for tid, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return _json_response({"topics": topics, "windowDays": days}, cache_seconds=300)


@app.function_name(name="api_hot")
@app.route(route="hot", methods=["GET"])
def api_hot(req: func.HttpRequest) -> func.HttpResponse:
    """Top "hot" headlines (priority>=2) from the last N days.

    Query parameters
    ----------------
    * ``limit`` (default 10, max 25)
    * ``days``  (default 7, max 30)
    * ``lang``  (optional: ``de`` | ``en``)
    """
    limit = _parse_int(req.params.get("limit"), default=10, minimum=1, maximum=25)
    days = _parse_int(req.params.get("days"), default=7, minimum=1, maximum=30)
    language = req.params.get("lang") or None
    if language not in (None, "de", "en"):
        language = None

    since = datetime.now(timezone.utc) - timedelta(days=days)
    store = _store()
    # Scan up to ~500 recent rows; priorities are computed post-query.
    page = store.query_page(
        limit=500,
        language=language,
        since=since,
        deduped=True,
    )
    serialized = [_serialize_entity(e) for e in page.items]
    hot = [i for i in serialized if i["priority"] >= 2][:limit]
    return _json_response(
        {"items": hot, "count": len(hot)},
        cache_seconds=300,
    )


@app.function_name(name="api_health")
@app.route(route="health", methods=["GET"])
def api_health(req: func.HttpRequest) -> func.HttpResponse:
    store = _store()
    stale: list[str] = []
    storage_ok = True
    now = datetime.now(timezone.utc)
    try:
        for ent in store.list_source_health():
            last_fetch = ent.get("LastFetchAt")
            status = ent.get("LastStatus") or ""
            if (
                not isinstance(last_fetch, datetime)
                or (now - last_fetch.astimezone(timezone.utc)) > STALE_WINDOW
                or status == "error"
            ):
                stale.append(str(ent.get("RowKey")))
    except Exception:  # noqa: BLE001
        storage_ok = False
        log.exception("health check failed to enumerate SourceHealth")

    body = {
        "status": "ok" if storage_ok else "degraded",
        "storage": storage_ok,
        "sourcesStale": sorted(stale),
        "checkedAt": now.isoformat(),
    }
    status_code = 200 if storage_ok else 503
    return _json_response(body, status_code=status_code, cache_seconds=30)


# ---- HTTP: RSS / Atom feeds -------------------------------------------------


def _feed_items(limit: int = 50) -> list[dict]:
    store = _store()
    page = store.query_page(limit=limit, deduped=True)
    return [_serialize_entity(e) for e in page.items]


def _rfc822(dt: datetime) -> str:
    # Azure Table timestamps come back aware; be defensive.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


@app.function_name(name="api_feed_rss")
@app.route(route="feed.xml", methods=["GET"])
def api_feed_rss(req: func.HttpRequest) -> func.HttpResponse:
    """RSS 2.0 feed – headline + URL + source + pubDate only. No description."""
    items = _feed_items(limit=50)
    now_str = _rfc822(datetime.now(timezone.utc))

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        "<title>OmlorsNewsBot</title>",
        "<link>https://omlorsnewsbot.example/</link>",
        "<description>Independent Microsoft &amp; IT news aggregator.</description>",
        "<language>en</language>",
        f"<lastBuildDate>{now_str}</lastBuildDate>",
    ]
    for item in items:
        pub = item.get("publishedAt") or ""
        try:
            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            pub_str = _rfc822(pub_dt)
        except (ValueError, TypeError):
            pub_str = now_str
        parts.extend(
            [
                "<item>",
                f"<title>{xml_escape(item.get('title') or '')}</title>",
                f"<link>{xml_escape(item.get('url') or '')}</link>",
                f"<guid isPermaLink=\"true\">{xml_escape(item.get('url') or '')}</guid>",
                f"<source>{xml_escape(item.get('sourceName') or '')}</source>",
                f"<pubDate>{pub_str}</pubDate>",
                "</item>",
            ]
        )
    parts.append("</channel></rss>")

    body = "".join(parts).encode("utf-8")
    return func.HttpResponse(
        body,
        status_code=200,
        mimetype="application/rss+xml",
        headers={
            "Cache-Control": "public, max-age=300, stale-while-revalidate=600",
            "ETag": _etag_for(body),
        },
    )


@app.function_name(name="api_feed_atom")
@app.route(route="atom.xml", methods=["GET"])
def api_feed_atom(req: func.HttpRequest) -> func.HttpResponse:
    """Atom 1.0 feed – headline + URL + source + pubDate only."""
    items = _feed_items(limit=50)
    now = datetime.now(timezone.utc)

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        "<title>OmlorsNewsBot</title>",
        '<link href="https://omlorsnewsbot.example/" rel="alternate"/>',
        f"<updated>{now.isoformat()}</updated>",
        "<id>urn:omlorsnewsbot:main</id>",
    ]
    for item in items:
        pub = item.get("publishedAt") or now.isoformat()
        parts.extend(
            [
                "<entry>",
                f"<title>{xml_escape(item.get('title') or '')}</title>",
                f'<link href="{xml_escape(item.get("url") or "")}" rel="alternate"/>',
                f"<id>{xml_escape(item.get('url') or '')}</id>",
                f"<updated>{xml_escape(pub)}</updated>",
                f"<source><title>{xml_escape(item.get('sourceName') or '')}</title></source>",
                "</entry>",
            ]
        )
    parts.append("</feed>")

    body = "".join(parts).encode("utf-8")
    return func.HttpResponse(
        body,
        status_code=200,
        mimetype="application/atom+xml",
        headers={
            "Cache-Control": "public, max-age=300, stale-while-revalidate=600",
            "ETag": _etag_for(body),
        },
    )
