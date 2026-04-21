"""Azure Functions v2 entry point.

Triggers
--------
- ``ingest_timer``     : Timer-Trigger, runs daily 05:00 UTC, aggregates sources.
- ``ingest_http``      : HTTP-Trigger (admin), manually triggers an aggregation run.
- ``api_news``         : HTTP-Trigger, returns recent news items as JSON.
- ``api_sources``      : HTTP-Trigger, returns source-health metadata.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime

import azure.functions as func

from config import get_settings
from sources.azure_updates import AzureUpdatesAdapter
from sources.base import SourceAdapter
from sources.borns_it import BornsITAdapter
from sources.heise import HeiseAdapter
from sources.m365_roadmap import M365RoadmapAdapter
from sources.msrc import MSRCAdapter
from sources.tech_community import TechCommunityAdapter
from sources.windows_blog import WindowsBlogAdapter, WindowsITProBlogAdapter
from storage.table_client import NewsStore

log = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Pause between source fetches to avoid hammering publishers.
INTER_SOURCE_DELAY_SECONDS = 1.0


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


def _adapters() -> list[SourceAdapter]:
    return [
        M365RoadmapAdapter(),
        AzureUpdatesAdapter(),
        MSRCAdapter(),
        TechCommunityAdapter(),
        WindowsBlogAdapter(),
        WindowsITProBlogAdapter(),
        HeiseAdapter(),
        BornsITAdapter(),
    ]


def _run_ingest() -> dict:
    settings = get_settings()
    store = _store()
    store.ensure_tables()

    totals: dict[str, int] = {}
    adapters = _adapters()
    for index, adapter in enumerate(adapters):
        if index > 0:
            time.sleep(INTER_SOURCE_DELAY_SECONDS)

        previous = store.get_source_health(adapter.source_id) or {}
        etag = previous.get("ETag") or None
        last_modified = previous.get("LastModified") or None

        log.info("Fetching %s", adapter.source_id)
        try:
            result = adapter.fetch(
                user_agent=settings.user_agent,
                etag=etag,
                last_modified=last_modified,
            )
        except Exception as exc:  # noqa: BLE001 — never let one bad source kill the run
            log.exception("Adapter %s crashed", adapter.source_id)
            store.record_source_health(
                source_id=adapter.source_id,
                status="error",
                error=str(exc),
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
        )
        totals[adapter.source_id] = written
        log.info(
            "Source %s status=%s written=%d", adapter.source_id, result.status, written
        )

    return {"written": totals}


@app.function_name(name="ingest_timer")
@app.schedule(
    schedule="0 0 5 * * *",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def ingest_timer(timer: func.TimerRequest) -> None:
    log.info("ingest_timer fired (past_due=%s)", timer.past_due)
    result = _run_ingest()
    log.info("ingest_timer done: %s", result)


@app.function_name(name="ingest_http")
@app.route(route="ingest", methods=["POST", "GET"])
def ingest_http(req: func.HttpRequest) -> func.HttpResponse:
    log.info("ingest_http triggered")
    result = _run_ingest()
    return func.HttpResponse(
        json.dumps(result),
        status_code=200,
        mimetype="application/json",
    )


def _parse_int(value: str | None, default: int, *, minimum: int, maximum: int) -> int:
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))


def _serialize_entity(ent: dict) -> dict:
    def iso(value: object) -> object:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    return {
        "id": ent.get("RowKey"),
        "title": ent.get("Title"),
        "publishedAt": iso(ent.get("PublishedAt")),
        "sourceId": ent.get("SourceId"),
        "sourceName": ent.get("SourceName"),
        "author": ent.get("Author") or None,
        "url": ent.get("CanonicalUrl"),
        "products": [p for p in (ent.get("Products") or "").split(",") if p],
        "tags": [t for t in (ent.get("Tags") or "").split(",") if t],
        "language": ent.get("Language") or "en",
    }


@app.function_name(name="api_news")
@app.route(route="news", methods=["GET"])
def api_news(req: func.HttpRequest) -> func.HttpResponse:
    store = _store()

    limit = _parse_int(req.params.get("limit"), default=50, minimum=1, maximum=200)
    source_id = req.params.get("source") or None
    product = req.params.get("product") or None

    items = list(store.query_recent(limit=limit, source_id=source_id, product=product))
    payload = {
        "items": [_serialize_entity(e) for e in items],
        "count": len(items),
    }
    return func.HttpResponse(
        json.dumps(payload),
        status_code=200,
        mimetype="application/json",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.function_name(name="api_sources")
@app.route(route="sources", methods=["GET"])
def api_sources(req: func.HttpRequest) -> func.HttpResponse:
    store = _store()
    sources = []
    for ent in store.list_source_health():
        last_fetch = ent.get("LastFetchAt")
        if isinstance(last_fetch, datetime):
            last_fetch = last_fetch.isoformat()
        sources.append(
            {
                "sourceId": ent.get("RowKey"),
                "lastFetchAt": last_fetch,
                "lastStatus": ent.get("LastStatus"),
                "lastError": ent.get("LastError") or None,
            }
        )
    return func.HttpResponse(
        json.dumps({"sources": sources}),
        status_code=200,
        mimetype="application/json",
    )
