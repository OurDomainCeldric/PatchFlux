"""Azure Functions v2 entry point.

HTTP routes
-----------
- ``GET  /api/news``       – filtered & paginated news feed
- ``GET  /api/sources``    – source-health status list
- ``GET  /api/products``   – distinct product IDs with occurrence counts
- ``GET|POST /api/comments`` – comments for one news item
- ``GET|POST /api/comments/*`` – Function-key protected moderation
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
import hmac
import json
import logging
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from xml.sax.saxutils import escape as xml_escape

import azure.functions as func

from ai.budget import BudgetTracker
from ai.gate import GateRunStats, build_gate
from config import get_settings
from priority import compute_priority
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
from sources.reddit_microsoft import RedditMicrosoftAdapter
from sources.reddit_sysadmin import RedditSysadminAdapter
from sources.tech_community import TechCommunityAdapter
from sources.windows_blog import WindowsBlogAdapter, WindowsITProBlogAdapter
from storage.table_client import NewsStore
from topics import compute_topics

log = logging.getLogger(__name__)

# ``/ingest`` uses a FUNCTION-level key; read endpoints are ANONYMOUS.
# Per-function auth is set on the decorators below so we keep the app default
# at ANONYMOUS for public read endpoints.
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

INTER_SOURCE_DELAY_SECONDS = 1.0
COMMENT_BODY_MAX_CHARS = 1000
COMMENT_DISPLAY_NAME_MAX_CHARS = 40
COMMENT_MIN_SECONDS_BETWEEN_POSTS = 60
COMMENT_MAX_PER_DAY = 20

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
    "reddit-sysadmin",
    "reddit-microsoft",
}
LOW_FREQ_SOURCES = {"m365-roadmap", "azure-updates"}
DISABLED_SOURCE_IDS = {"reddit-sysadmin", "reddit-microsoft"}

# If a source has not been fetched successfully within this window, /health
# reports it as stale.
STALE_WINDOW = timedelta(hours=26)
HEALTHY_SOURCE_STATUSES = {"ok", "not_modified"}

# Adapter error messages often embed absolute file paths, IP addresses,
# Python-package internals and line numbers; none of that is useful to the
# public. Strip aggressively before persisting or returning.
_ERROR_PATH_PATTERN = re.compile(
    r"(/[^\s'\"]*\.py[^\s'\"]*|[A-Za-z]:\\[^\s'\"]+|line\s+\d+|File\s+\"[^\"]+\")",
    re.IGNORECASE,
)
_COMMENT_URL_PATTERN = re.compile(
    r"(?i)(https?://|www\.|[a-z0-9][a-z0-9-]{1,62}\.(?:com|net|org|de|io|dev|app|info|biz|ru|cn|uk|eu)\b)"
)
_COMMENT_BLOCKED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bheil\s+hitler\b",
        r"\bwhite\s+power\b",
        r"\bkkk\b",
        r"\bnazi\s+(?:propaganda|salute|symbol)\b",
    )
]
_COMMENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,96}$")


def _safe_error_summary(exc: BaseException | str | None, *, limit: int = 120) -> str | None:
    """Return a short, path-free summary suitable for public display.

    - Keeps the exception class and a brief message.
    - Removes file paths, ``line NN`` markers and raw tracebacks.
    - Truncates to ``limit`` characters.
    """
    if exc is None:
        return None
    message = f"{type(exc).__name__}: {exc}" if isinstance(exc, BaseException) else str(exc)
    message = _ERROR_PATH_PATTERN.sub("", message)
    message = " ".join(message.split())
    if len(message) > limit:
        message = message[: limit - 1].rstrip() + "\u2026"
    return message or None


def _store() -> NewsStore:
    settings = get_settings()
    return NewsStore(
        connection_string=settings.table_connection,
        news_table=settings.news_table_name,
        source_health_table=settings.source_health_table_name,
        visit_counter_table=settings.visit_counter_table_name,
        comment_user_table=settings.comment_user_table_name,
        comment_table=settings.comment_table_name,
        comment_moderation_table=settings.comment_moderation_table_name,
        comment_rate_limit_table=settings.comment_rate_limit_table_name,
    )


def _is_enabled_source_id(source_id: str) -> bool:
    return source_id not in DISABLED_SOURCE_IDS


# Create tables on cold start so read-only endpoints don't 500 before the
# first ingest run. Safe & idempotent.
try:
    _store().ensure_tables()
except Exception:  # noqa: BLE001 — logged by Application Insights via logger
    log.exception("Failed to ensure tables during cold start")


def _configured_adapters() -> list[SourceAdapter]:
    adapters = [
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
        RedditSysadminAdapter(),
        RedditMicrosoftAdapter(),
    ]
    return adapters


def _all_adapters() -> list[SourceAdapter]:
    adapters = _configured_adapters()
    return [adapter for adapter in adapters if _is_enabled_source_id(adapter.source_id)]


def _adapters_matching(ids: Iterable[str]) -> list[SourceAdapter]:
    wanted = set(ids)
    return [a for a in _all_adapters() if a.source_id in wanted]


@dataclass(frozen=True)
class SourceHealthView:
    source_id: str
    source_name: str
    state: str
    last_status: str | None
    last_error: str | None
    last_attempt_at: str | None
    last_fetch_at: str | None
    last_success_at: str | None
    items_last_run: int


def _as_utc_datetime(value: object) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _classify_source_state(
    *,
    source_id: str,
    last_status: str | None,
    last_attempt_at: datetime | None,
    last_success_at: datetime | None,
    now: datetime,
) -> str:
    if not _is_enabled_source_id(source_id):
        return "disabled"
    if last_attempt_at is None and last_success_at is None:
        return "never"
    if last_attempt_at is None or (now - last_attempt_at) > STALE_WINDOW:
        return "timer_not_firing"
    if last_status == "error":
        return "error"
    if last_success_at is None or (now - last_success_at) > STALE_WINDOW:
        return "stale"
    if last_status == "not_modified":
        return "not_modified"
    return "ok"


def _source_catalog() -> dict[str, str]:
    return {adapter.source_id: adapter.source_name for adapter in _configured_adapters()}


def _list_source_health_views() -> list[SourceHealthView]:
    now = datetime.now(UTC)
    store = _store()
    catalog = _source_catalog()
    rows_by_id = {
        str(ent.get("RowKey") or ""): ent for ent in store.list_source_health() if ent.get("RowKey")
    }
    source_ids = sorted(set(catalog) | set(DISABLED_SOURCE_IDS) | set(rows_by_id))
    views: list[SourceHealthView] = []
    for source_id in source_ids:
        ent = rows_by_id.get(source_id, {})
        last_status = str(ent.get("LastStatus") or "") or None
        last_fetch_at = _as_utc_datetime(ent.get("LastFetchAt"))
        last_attempt_at = _as_utc_datetime(ent.get("LastAttemptAt")) or last_fetch_at
        last_success_at = _as_utc_datetime(ent.get("LastSuccessAt")) or last_fetch_at
        state = _classify_source_state(
            source_id=source_id,
            last_status=last_status,
            last_attempt_at=last_attempt_at,
            last_success_at=last_success_at,
            now=now,
        )
        views.append(
            SourceHealthView(
                source_id=source_id,
                source_name=catalog.get(source_id, source_id),
                state=state,
                last_status=last_status,
                last_error=_safe_error_summary(ent.get("LastError") or None),
                last_attempt_at=last_attempt_at.isoformat() if last_attempt_at else None,
                last_fetch_at=last_fetch_at.isoformat() if last_fetch_at else None,
                last_success_at=last_success_at.isoformat() if last_success_at else None,
                items_last_run=int(ent.get("ItemsLastRun") or 0),
            )
        )
    return views


def _run_ingest(source_ids: Iterable[str] | None = None) -> dict:
    """Run the ingest pipeline for the selected adapters (default: all)."""
    settings = get_settings()
    store = _store()
    store.ensure_tables()

    adapters = _all_adapters() if source_ids is None else _adapters_matching(source_ids)

    budget = BudgetTracker(
        connection_string=settings.table_connection,
        table_name=settings.ai_budget_table_name,
        max_monthly_usd=settings.ai_max_monthly_usd,
        model=settings.ai_model,
    )
    gate = build_gate(
        enabled=settings.ai_gate_enabled,
        endpoint=settings.ai_endpoint,
        api_key=settings.ai_api_key,
        deployment=settings.ai_deployment,
        model=settings.ai_model,
        api_version=settings.ai_api_version,
        budget=budget,
        max_calls_per_run=settings.ai_max_calls_per_run,
        max_output_tokens=settings.ai_max_output_tokens,
    )
    gate_stats = GateRunStats()

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
            # Full stack trace goes to App Insights only; the public
            # ``/api/sources`` endpoint must never expose file paths,
            # library internals or line numbers. Store a short category so
            # operators can still differentiate error classes in logs.
            log.exception("Adapter %s crashed", adapter.source_id)
            store.record_source_health(
                source_id=adapter.source_id,
                status="error",
                error=_safe_error_summary(exc),
                items_last_run=0,
            )
            totals[adapter.source_id] = 0
            continue

        written = 0
        if result.items:
            items_to_write = result.items
            if gate is not None:
                items_to_write = gate.process(
                    list(result.items),
                    source_id=adapter.source_id,
                    stats=gate_stats,
                )
            if items_to_write:
                written = store.upsert_many(items_to_write)

        store.record_source_health(
            source_id=adapter.source_id,
            status=result.status,
            error=_safe_error_summary(result.error),
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

    response: dict = {"written": totals}
    if gate is not None:
        response["ai_gate"] = gate_stats.to_dict()
        log.info(json.dumps({"event": "ingest.ai_gate", **gate_stats.to_dict()}))
    return response


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
    if source_param and not _is_enabled_source_id(source_param):
        return _json_response(
            {"error": "source_disabled", "sourceId": source_param},
            status_code=400,
        )
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
        return datetime.now(UTC) - timedelta(days=int(raw[:-1]))
    if raw.endswith("h") and raw[:-1].isdigit():
        return datetime.now(UTC) - timedelta(hours=int(raw[:-1]))
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _iso(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _visit_day_key(now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    return current.astimezone(UTC).date().isoformat()


def _comment_secret_hash(user_id: str, secret: str) -> str:
    # The browser-local secret is high entropy; hashing avoids storing it in clear text.
    return hashlib.sha256(f"{user_id}:{secret}".encode("utf-8")).hexdigest()


def _constant_time_equal(left: object, right: str) -> bool:
    return hmac.compare_digest(str(left or ""), right)


def _clean_comment_text(value: object, *, max_chars: int) -> str:
    text = str(value or "")
    text = " ".join(text.replace("\r", "\n").split())
    return text[:max_chars].strip()


def _comment_validation_error(display_name: str, body: str) -> str | None:
    if not display_name:
        return "display_name_required"
    if not body:
        return "body_required"
    if len(body) > COMMENT_BODY_MAX_CHARS:
        return "body_too_long"
    if _COMMENT_URL_PATTERN.search(body):
        return "links_not_allowed"
    if any(pattern.search(body) for pattern in _COMMENT_BLOCKED_PATTERNS):
        return "blocked_language"
    return None


def _request_json(req: func.HttpRequest) -> dict:
    try:
        data = req.get_json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _serialize_comment(ent: dict, *, admin: bool = False) -> dict:
    payload = {
        "id": ent.get("CommentId"),
        "newsItemId": ent.get("NewsItemId"),
        "displayName": ent.get("DisplayName"),
        "body": ent.get("Body"),
        "status": ent.get("Status"),
        "createdAt": _iso(ent.get("CreatedAt")),
        "updatedAt": _iso(ent.get("UpdatedAt")),
    }
    if admin:
        payload.update(
            {
                "userId": ent.get("UserId"),
                "commentPartitionKey": ent.get("PartitionKey"),
                "commentRowKey": ent.get("RowKey"),
                "moderationReason": ent.get("ModerationReason") or None,
                "reportCount": int(ent.get("ReportCount") or 0),
            }
        )
    return payload


def _serialize_entity(ent: dict) -> dict:
    title = ent.get("Title") or ""
    source_id = ent.get("SourceId") or ""
    return {
        "id": ent.get("RowKey"),
        "title": title,
        "publishedAt": _iso(ent.get("PublishedAt")),
        "sourceId": source_id,
        "sourceName": ent.get("SourceName"),
        "sourceTier": int(ent.get("SourceTier") or 2),
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
    # community=1 → Tier-3 only; community=0 → Tier 1+2 only; absent → all
    community_raw = req.params.get("community")
    community_filter: int | None = None  # None = no tier filter
    if community_raw is not None:
        community_filter = 3 if _parse_bool(community_raw) else 2  # 2 = max for news+blogs
    min_priority = _parse_int(
        req.params.get("min_priority"), default=0, minimum=0, maximum=2
    )
    if _parse_bool(req.params.get("hot")):
        min_priority = max(min_priority, 2)
    topics_param = (req.params.get("topics") or "").strip()
    topics_filter: set[str] = {
        t.strip().lower() for t in topics_param.split(",") if t.strip()
    }
    exclude_topics_param = (req.params.get("exclude_topics") or "").strip()
    exclude_topics_filter: set[str] = {
        t.strip().lower() for t in exclude_topics_param.split(",") if t.strip()
    }

    store = _store()
    start = time.monotonic()
    # When filtering by priority, topics, or tier we need to scan more raw rows
    # because all three filters are applied post-query.
    need_post_filter = (
        min_priority > 0
        or bool(topics_filter)
        or bool(exclude_topics_filter)
        or community_filter is not None
    )
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
    serialized = [i for i in serialized if _is_enabled_source_id(str(i["sourceId"]))]
    if community_filter is not None:
        if community_filter == 3:
            serialized = [i for i in serialized if i["sourceTier"] == 3]
        else:
            serialized = [i for i in serialized if i["sourceTier"] <= 2]
    if min_priority > 0:
        serialized = [i for i in serialized if i["priority"] >= min_priority]
    if exclude_topics_filter:
        serialized = [
            i
            for i in serialized
            if not exclude_topics_filter.intersection(str(topic).lower() for topic in i["topics"])
        ]
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
    sources = []
    for view in _list_source_health_views():
        record = {
            "sourceId": view.source_id,
            "sourceName": view.source_name,
            "state": view.state,
            "lastAttemptAt": view.last_attempt_at,
            "lastFetchAt": view.last_fetch_at,
            "lastSuccessAt": view.last_success_at,
            "lastStatus": view.last_status,
            "lastError": view.last_error,
        }
        if include_counts:
            record["itemsLastRun"] = view.items_last_run
        sources.append(record)
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

    since = datetime.now(UTC) - timedelta(days=days)
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
    storage_ok = True
    now = datetime.now(UTC)
    source_lists = {
        "disabled": [],
        "error": [],
        "never": [],
        "notModified": [],
        "ok": [],
        "stale": [],
        "timerNotFiring": [],
    }
    try:
        for view in _list_source_health_views():
            match view.state:
                case "disabled":
                    source_lists["disabled"].append(view.source_id)
                case "error":
                    source_lists["error"].append(view.source_id)
                case "never":
                    source_lists["never"].append(view.source_id)
                case "not_modified":
                    source_lists["notModified"].append(view.source_id)
                case "stale":
                    source_lists["stale"].append(view.source_id)
                case "timer_not_firing":
                    source_lists["timerNotFiring"].append(view.source_id)
                case _:
                    source_lists["ok"].append(view.source_id)
    except Exception:  # noqa: BLE001
        storage_ok = False
        log.exception("health check failed to enumerate SourceHealth")

    degraded_sources = sorted(
        source_lists["error"] + source_lists["never"] + source_lists["stale"] + source_lists["timerNotFiring"]
    )
    overall_ok = storage_ok and not degraded_sources

    body = {
        "status": "ok" if overall_ok else "degraded",
        "storage": storage_ok,
        "sourcesStale": degraded_sources,
        "sourceCounts": {key: len(value) for key, value in source_lists.items()},
        "sourcesByState": source_lists,
        "checkedAt": now.isoformat(),
    }
    status_code = 200 if storage_ok else 503
    return _json_response(body, status_code=status_code, cache_seconds=30)


@app.function_name(name="api_visits")
@app.route(route="visits", methods=["GET"])
def api_visits(req: func.HttpRequest) -> func.HttpResponse:
    day_key = _visit_day_key()
    counts = _store().get_visit_counts(day_key=day_key)
    return _json_response(
        {
            "today": counts["today"],
            "allTime": counts["allTime"],
            "dayKey": day_key,
            "timezone": "UTC",
        },
        cache_seconds=60,
    )


@app.function_name(name="api_visits_track")
@app.route(route="visits/track", methods=["POST"])
def api_visits_track(req: func.HttpRequest) -> func.HttpResponse:
    day_key = _visit_day_key()
    counts = _store().record_visit(day_key=day_key)
    return _json_response(
        {
            "today": counts["today"],
            "allTime": counts["allTime"],
            "dayKey": day_key,
            "timezone": "UTC",
        },
        cache_seconds=0,
        extra_headers={"Cache-Control": "no-store"},
    )


@app.function_name(name="api_comments")
@app.route(route="comments", methods=["GET", "POST"])
def api_comments(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "GET":
        news_item_id = (req.params.get("item") or "").strip()
        if not news_item_id:
            return _json_response({"error": "missing_item"}, status_code=400)
        comments = _store().list_visible_comments(news_item_id=news_item_id, limit=50)
        return _json_response(
            {
                "comments": [_serialize_comment(comment) for comment in comments],
                "count": len(comments),
            },
            cache_seconds=30,
        )

    data = _request_json(req)
    news_item_id = _clean_comment_text(data.get("newsItemId"), max_chars=160)
    user_id = _clean_comment_text(data.get("userId"), max_chars=96)
    user_secret = _clean_comment_text(data.get("userSecret"), max_chars=160)
    display_name = _clean_comment_text(
        data.get("displayName"), max_chars=COMMENT_DISPLAY_NAME_MAX_CHARS
    )
    body_raw = str(data.get("body") or "")
    body = _clean_comment_text(body_raw, max_chars=COMMENT_BODY_MAX_CHARS)

    if not news_item_id:
        return _json_response({"error": "missing_item"}, status_code=400)
    if not _COMMENT_ID_PATTERN.match(user_id) or not _COMMENT_ID_PATTERN.match(user_secret):
        return _json_response({"error": "invalid_user_identity"}, status_code=400)
    if len(body_raw) > COMMENT_BODY_MAX_CHARS:
        return _json_response({"error": "body_too_long"}, status_code=400)

    validation_error = _comment_validation_error(display_name, body)
    if validation_error:
        return _json_response({"error": validation_error}, status_code=400)

    store = _store()
    secret_hash = _comment_secret_hash(user_id, user_secret)
    user = store.get_comment_user(user_id)
    if user is not None and not _constant_time_equal(user.get("SecretHash"), secret_hash):
        return _json_response({"error": "invalid_user_identity"}, status_code=403)
    if user is not None and str(user.get("Status") or "active") in {"muted", "banned"}:
        return _json_response({"error": "user_not_allowed"}, status_code=403)

    day_key = _visit_day_key()
    rate = store.get_comment_rate_limit(user_id=user_id, day_key=day_key)
    if rate is not None:
        count = int(rate.get("Count") or 0)
        last_comment_at = _as_utc_datetime(rate.get("LastCommentAt"))
        if count >= COMMENT_MAX_PER_DAY:
            return _json_response({"error": "rate_limited_daily"}, status_code=429)
        if (
            last_comment_at is not None
            and datetime.now(UTC) - last_comment_at
            < timedelta(seconds=COMMENT_MIN_SECONDS_BETWEEN_POSTS)
        ):
            return _json_response({"error": "rate_limited_recent"}, status_code=429)

    store.upsert_comment_user(
        user_id=user_id,
        display_name=display_name,
        secret_hash=secret_hash,
    )
    store.record_comment_rate_limit(user_id=user_id, day_key=day_key)
    comment = store.add_comment(
        news_item_id=news_item_id,
        user_id=user_id,
        display_name=display_name,
        body=body,
        status="visible",
    )
    return _json_response(
        {
            "comment": _serialize_comment(comment),
            "status": "visible",
        },
        status_code=201,
        cache_seconds=0,
        extra_headers={"Cache-Control": "no-store"},
    )


@app.function_name(name="api_comment_counts")
@app.route(route="comments/counts", methods=["GET"])
def api_comment_counts(req: func.HttpRequest) -> func.HttpResponse:
    raw_items = (req.params.get("items") or "").strip()
    news_item_ids = [
        _clean_comment_text(item, max_chars=160)
        for item in raw_items.split(",")
        if item.strip()
    ][:100]
    if not news_item_ids:
        return _json_response({"counts": {}}, cache_seconds=30)
    counts = _store().visible_comment_counts(news_item_ids=news_item_ids)
    return _json_response({"counts": counts}, cache_seconds=30)


@app.function_name(name="api_comments_moderation")
@app.route(route="comments/moderation", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def api_comments_moderation(req: func.HttpRequest) -> func.HttpResponse:
    status = (req.params.get("status") or "pending").strip().lower()
    if status not in {"pending", "flagged", "hidden", "rejected"}:
        return _json_response({"error": "invalid_status"}, status_code=400)
    limit = _parse_int(req.params.get("limit"), default=50, minimum=1, maximum=200)
    comments = _store().list_moderation_comments(status=status, limit=limit)
    return _json_response(
        {
            "comments": [_serialize_comment(comment, admin=True) for comment in comments],
            "count": len(comments),
            "status": status,
        },
        cache_seconds=0,
        extra_headers={"Cache-Control": "no-store"},
    )


@app.function_name(name="api_comments_moderate")
@app.route(route="comments/moderate", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def api_comments_moderate(req: func.HttpRequest) -> func.HttpResponse:
    data = _request_json(req)
    action = _clean_comment_text(data.get("action"), max_chars=32).lower()
    reason = _clean_comment_text(data.get("reason"), max_chars=500)
    comment_partition_key = _clean_comment_text(data.get("commentPartitionKey"), max_chars=240)
    comment_row_key = _clean_comment_text(data.get("commentRowKey"), max_chars=240)
    if action not in {"approve", "hide", "flag", "reject", "ban_user"}:
        return _json_response({"error": "invalid_action"}, status_code=400)
    if not comment_partition_key or not comment_row_key:
        return _json_response({"error": "missing_comment"}, status_code=400)

    store = _store()
    moderation_action = "hide" if action == "ban_user" else action
    comment = store.moderate_comment(
        comment_partition_key=comment_partition_key,
        comment_row_key=comment_row_key,
        action=moderation_action,
        reason=reason,
    )
    if comment is None:
        return _json_response({"error": "comment_not_found"}, status_code=404)
    if action == "ban_user":
        store.update_comment_user_status(
            user_id=str(comment.get("UserId") or ""),
            status="banned",
            note=reason,
        )
    return _json_response(
        {
            "comment": _serialize_comment(comment, admin=True),
            "action": action,
        },
        cache_seconds=0,
        extra_headers={"Cache-Control": "no-store"},
    )


# ---- HTTP: RSS / Atom feeds -------------------------------------------------


def _feed_items(limit: int = 50) -> list[dict]:
    store = _store()
    page = store.query_page(limit=limit, deduped=True)
    return [
        item
        for item in (_serialize_entity(e) for e in page.items)
        if _is_enabled_source_id(str(item["sourceId"]))
    ]


def _rfc822(dt: datetime) -> str:
    # Azure Table timestamps come back aware; be defensive.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%a, %d %b %Y %H:%M:%S +0000")


@app.function_name(name="api_feed_rss")
@app.route(route="feed.xml", methods=["GET"])
def api_feed_rss(req: func.HttpRequest) -> func.HttpResponse:
    """RSS 2.0 feed – headline + URL + source + pubDate only. No description."""
    items = _feed_items(limit=50)
    now_str = _rfc822(datetime.now(UTC))

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        "<title>PatchFlux</title>",
        "<link>https://patchflux.de/</link>",
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
    now = datetime.now(UTC)

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        "<title>PatchFlux</title>",
        '<link href="https://patchflux.de/" rel="alternate"/>',
        f"<updated>{now.isoformat()}</updated>",
        "<id>urn:patchflux:main</id>",
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
