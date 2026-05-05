"""Azure Table Storage access for NewsItems and SourceHealth.

Partitioning strategy
---------------------
- NewsItems.PartitionKey  = ``YYYY-MM`` of PublishedAt (even distribution, good time queries)
- NewsItems.RowKey        = ``{inverted_ts}_{dedup_hash[:8]}``
  where ``inverted_ts = 9999999999 - int(published_at.timestamp())`` so that
  natural RowKey order returns newest-first.
- SourceHealth.PartitionKey = ``"sources"``
- SourceHealth.RowKey       = source_id
"""
from __future__ import annotations

import base64
import binascii
import json
import logging
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.data.tables import TableClient, TableServiceClient, UpdateMode

from models.news_item import NewsItem
from topics import compute_topics

_INVERTED_TS_BASE = 9_999_999_999

log = logging.getLogger(__name__)


def _partition_key(published_at: datetime) -> str:
    dt = published_at.astimezone(UTC)
    return f"{dt.year:04d}-{dt.month:02d}"


def _row_key(published_at: datetime, dedup_hash: str) -> str:
    ts = int(published_at.astimezone(UTC).timestamp())
    inverted = _INVERTED_TS_BASE - ts
    return f"{inverted:010d}_{dedup_hash[:8]}"


def news_item_to_entity(item: NewsItem) -> dict:
    return {
        "PartitionKey": _partition_key(item.published_at),
        "RowKey": _row_key(item.published_at, item.dedup_hash),
        "DedupHash": item.dedup_hash,
        "Title": item.title,
        "PublishedAt": item.published_at,
        "SourceId": item.source_id,
        "SourceName": item.source_name,
        "SourceTier": item.source_tier,
        "Author": item.author or "",
        "CanonicalUrl": str(item.canonical_url),
        "Products": ",".join(item.products),
        "Tags": ",".join(item.tags),
        "Language": item.language,
        "IngestedAt": datetime.now(UTC),
    }


def encode_cursor(*, year: int, month: int, last_row_key: str) -> str:
    """Encode a pagination cursor as URL-safe base64 JSON."""
    payload = json.dumps({"y": year, "m": month, "rk": last_row_key}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).rstrip(b"=").decode("ascii")


def decode_cursor(cursor: str) -> tuple[int, int, str] | None:
    """Decode a pagination cursor. Returns (year, month, last_row_key) or None if invalid."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        return int(data["y"]), int(data["m"]), str(data["rk"])
    except (ValueError, KeyError, TypeError, binascii.Error, json.JSONDecodeError):
        return None


def _prev_month(month: int, year: int) -> tuple[int, int]:
    """Return (month, year) for the previous calendar month."""
    month -= 1
    if month == 0:
        month = 12
        year -= 1
    return month, year


@dataclass
class QueryPage:
    """A single page of news items with an optional next-page cursor."""

    items: list[dict]
    next_cursor: str | None


@dataclass
class NewsStore:
    """Thin wrapper over Azure Table Storage for news items + source health."""

    connection_string: str
    news_table: str = "NewsItems"
    source_health_table: str = "SourceHealth"
    visit_counter_table: str = "VisitCounters"
    comment_user_table: str = "CommentUsers"
    comment_table: str = "Comments"
    comment_moderation_table: str = "CommentModeration"
    comment_rate_limit_table: str = "CommentRateLimits"

    def _service(self) -> TableServiceClient:
        return TableServiceClient.from_connection_string(self.connection_string)

    def ensure_tables(self) -> None:
        svc = self._service()
        for name in (
            self.news_table,
            self.source_health_table,
            self.visit_counter_table,
            self.comment_user_table,
            self.comment_table,
            self.comment_moderation_table,
            self.comment_rate_limit_table,
        ):
            try:
                svc.create_table(name)
                log.info("Created table %s", name)
            except ResourceExistsError:
                pass

    def _news_client(self) -> TableClient:
        return TableClient.from_connection_string(self.connection_string, self.news_table)

    def _health_client(self) -> TableClient:
        return TableClient.from_connection_string(self.connection_string, self.source_health_table)

    def _visit_client(self) -> TableClient:
        return TableClient.from_connection_string(self.connection_string, self.visit_counter_table)

    def _comment_user_client(self) -> TableClient:
        return TableClient.from_connection_string(self.connection_string, self.comment_user_table)

    def _comment_client(self) -> TableClient:
        return TableClient.from_connection_string(self.connection_string, self.comment_table)

    def _comment_moderation_client(self) -> TableClient:
        return TableClient.from_connection_string(
            self.connection_string, self.comment_moderation_table
        )

    def _comment_rate_limit_client(self) -> TableClient:
        return TableClient.from_connection_string(
            self.connection_string, self.comment_rate_limit_table
        )

    # ---- NewsItems ------------------------------------------------------

    def upsert_many(self, items: Iterable[NewsItem]) -> int:
        """Upsert a batch of items. Returns number of items written."""
        count = 0
        with self._news_client() as client:
            for item in items:
                entity = news_item_to_entity(item)
                client.upsert_entity(entity, mode=UpdateMode.MERGE)
                count += 1
        return count

    def query_page(
        self,
        *,
        limit: int = 50,
        source_id: str | None = None,
        product: str | None = None,
        language: str | None = None,
        since: datetime | None = None,
        search: str | None = None,
        deduped: bool = False,
        months_back: int = 36,
        cursor: str | None = None,
    ) -> QueryPage:
        """Return one page of news items with filters and cursor pagination.

        Walks month partitions (``YYYY-MM``) from the current month backwards so
        results come out newest-first globally. Supports:

        * ``source_id``  – exact match on SourceId (OData filter).
        * ``product``    – case-insensitive substring match on Products CSV.
        * ``language``   – exact match on Language.
        * ``since``      – include only items with PublishedAt >= since.
        * ``search``     – case-insensitive substring match on Title.
        * ``deduped``    – collapse duplicates by DedupHash (first wins).
        * ``cursor``     – opaque token from a previous page; resume right after it.
        """
        now = datetime.now(UTC)
        start_year, start_month = now.year, now.month
        skip_row_key: str | None = None

        if cursor:
            decoded = decode_cursor(cursor)
            if decoded is not None:
                start_year, start_month, skip_row_key = decoded

        seen_hashes: set[str] = set()
        items: list[dict] = []
        search_low = search.lower() if search else None

        year, month = start_year, start_month

        with self._news_client() as client:
            for step in range(months_back):
                partition = f"{year:04d}-{month:02d}"

                filters = [f"PartitionKey eq '{partition}'"]
                params: dict[str, object] = {}
                if source_id:
                    filters.append("SourceId eq @sid")
                    params["sid"] = source_id
                if language:
                    filters.append("Language eq @lng")
                    params["lng"] = language
                # Only apply the RowKey skip on the first partition we examine.
                if step == 0 and skip_row_key:
                    filters.append("RowKey gt @rk")
                    params["rk"] = skip_row_key

                query = " and ".join(filters)

                try:
                    entities = client.query_entities(
                        query_filter=query,
                        parameters=params or None,
                    )
                except Exception:  # noqa: BLE001 — logged, skip month
                    log.exception("Query failed for partition %s", partition)
                    month, year = _prev_month(month, year)
                    continue

                for ent in entities:
                    if product and product.lower() not in (ent.get("Products") or "").lower():
                        continue
                    if search_low and search_low not in (ent.get("Title") or "").lower():
                        continue
                    if since is not None:
                        pub = ent.get("PublishedAt")
                        if isinstance(pub, datetime) and pub.astimezone(UTC) < since:
                            continue
                    if deduped:
                        h = ent.get("DedupHash")
                        if h:
                            if h in seen_hashes:
                                continue
                            seen_hashes.add(h)

                    items.append(ent)
                    if len(items) >= limit:
                        return QueryPage(
                            items=items,
                            next_cursor=encode_cursor(
                                year=year, month=month, last_row_key=str(ent.get("RowKey"))
                            ),
                        )

                month, year = _prev_month(month, year)

        return QueryPage(items=items, next_cursor=None)

    # Backward-compatible iterator API used by tests and older callers.
    def query_recent(
        self,
        *,
        limit: int = 50,
        source_id: str | None = None,
        product: str | None = None,
        months_back: int = 36,
    ) -> Iterator[dict]:
        page = self.query_page(
            limit=limit,
            source_id=source_id,
            product=product,
            months_back=months_back,
        )
        yield from page.items

    def product_counts(
        self,
        *,
        months_back: int = 3,
        limit_per_month: int = 2000,
    ) -> dict[str, int]:
        """Return product_id -> occurrence count over the last *months_back* months.

        Bounded scan: at most ``months_back * limit_per_month`` entities are examined.
        Used to drive the frontend filter dropdown.
        """
        counts: dict[str, int] = {}
        now = datetime.now(UTC)
        year, month = now.year, now.month
        with self._news_client() as client:
            for _ in range(months_back):
                partition = f"{year:04d}-{month:02d}"
                scanned = 0
                try:
                    entities = client.query_entities(
                        query_filter=f"PartitionKey eq '{partition}'",
                    )
                    for ent in entities:
                        for product in (ent.get("Products") or "").split(","):
                            p = product.strip()
                            if p:
                                counts[p] = counts.get(p, 0) + 1
                        scanned += 1
                        if scanned >= limit_per_month:
                            break
                except Exception:  # noqa: BLE001
                    log.exception("product_counts query failed for %s", partition)
                month, year = _prev_month(month, year)
        return counts

    def topic_counts(
        self,
        *,
        days: int = 14,
        limit_per_month: int = 2000,
    ) -> dict[str, int]:
        """Return topic_id -> occurrence count over the last *days* days.

        Topic tags are stored as a comma-separated string in the ``Tags``
        entity field by ``news_item_to_entity``. Bounded scan like
        ``product_counts``: walks at most 2 month partitions for windows <=
        31 days to keep the tally cheap. Used by ``/api/topics``.
        """
        counts: dict[str, int] = {}
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=max(1, days))
        year, month = now.year, now.month
        # For <=31-day windows we only ever need the current + previous month.
        months_to_scan = 1 if days <= 7 else 2 if days <= 31 else 3
        with self._news_client() as client:
            for _ in range(months_to_scan):
                partition = f"{year:04d}-{month:02d}"
                scanned = 0
                try:
                    entities = client.query_entities(
                        query_filter=f"PartitionKey eq '{partition}'",
                    )
                    for ent in entities:
                        published = ent.get("PublishedAt")
                        if isinstance(published, datetime) and published < cutoff:
                            continue
                        entity_topics: set[str] = set()
                        for tag in (ent.get("Tags") or "").split(","):
                            t = tag.strip().lower()
                            if t:
                                entity_topics.add(t)
                        # Also compute topics on the fly from title + source_id,
                        # since adapters typically don't populate ``item.tags``
                        # (topics are derived at response time in /api/news).
                        title = str(ent.get("Title") or "")
                        source_id = str(ent.get("SourceId") or "")
                        if title:
                            entity_topics.update(compute_topics(title, source_id))
                        for topic in entity_topics:
                            counts[topic] = counts.get(topic, 0) + 1
                        scanned += 1
                        if scanned >= limit_per_month:
                            break
                except Exception:  # noqa: BLE001
                    log.exception("topic_counts query failed for %s", partition)
                month, year = _prev_month(month, year)
        return counts

    # ---- SourceHealth ---------------------------------------------------

    def record_source_health(
        self,
        *,
        source_id: str,
        status: str,
        error: str | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
        items_last_run: int | None = None,
    ) -> None:
        now = datetime.now(UTC)
        entity: dict[str, object] = {
            "PartitionKey": "sources",
            "RowKey": source_id,
            "LastAttemptAt": now,
            "LastStatus": status,
            "LastError": (error or "")[:500],
            "ETag": etag or "",
            "LastModified": last_modified or "",
        }
        if status != "error":
            entity["LastFetchAt"] = now
        if status in {"ok", "not_modified"}:
            entity["LastSuccessAt"] = now
        if items_last_run is not None:
            entity["ItemsLastRun"] = int(items_last_run)
        with self._health_client() as client:
            client.upsert_entity(entity, mode=UpdateMode.MERGE)

    def get_source_health(self, source_id: str) -> dict | None:
        with self._health_client() as client:
            try:
                return client.get_entity(partition_key="sources", row_key=source_id)
            except Exception:  # noqa: BLE001
                return None

    def list_source_health(self) -> Iterator[dict]:
        with self._health_client() as client:
            yield from client.query_entities("PartitionKey eq 'sources'")

    # ---- VisitCounters --------------------------------------------------

    def _counter_key(self, day_key: str | None = None) -> str:
        return "total" if day_key is None else f"day:{day_key}"

    def _read_counter(self, row_key: str) -> int:
        with self._visit_client() as client:
            try:
                entity = client.get_entity(partition_key="visits", row_key=row_key)
            except ResourceNotFoundError:
                return 0
        return int(entity.get("Count") or 0)

    def get_visit_counts(self, *, day_key: str) -> dict[str, int]:
        return {
            "today": self._read_counter(self._counter_key(day_key)),
            "allTime": self._read_counter(self._counter_key()),
        }

    def _increment_counter(self, row_key: str) -> int:
        with self._visit_client() as client:
            try:
                entity = client.get_entity(partition_key="visits", row_key=row_key)
                count = int(entity.get("Count") or 0) + 1
            except ResourceNotFoundError:
                count = 1
            client.upsert_entity(
                {
                    "PartitionKey": "visits",
                    "RowKey": row_key,
                    "Count": count,
                    "UpdatedAt": datetime.now(UTC),
                },
                mode=UpdateMode.MERGE,
            )
        return count

    def record_visit(self, *, day_key: str) -> dict[str, int]:
        return {
            "today": self._increment_counter(self._counter_key(day_key)),
            "allTime": self._increment_counter(self._counter_key()),
        }

    # ---- Comments -------------------------------------------------------

    def get_comment_user(self, user_id: str) -> dict | None:
        with self._comment_user_client() as client:
            try:
                return client.get_entity(partition_key="users", row_key=user_id)
            except ResourceNotFoundError:
                return None

    def upsert_comment_user(
        self,
        *,
        user_id: str,
        display_name: str,
        secret_hash: str,
    ) -> dict:
        now = datetime.now(UTC)
        existing = self.get_comment_user(user_id)
        entity: dict[str, object] = {
            "PartitionKey": "users",
            "RowKey": user_id,
            "DisplayName": display_name,
            "SecretHash": secret_hash,
            "LastSeenAt": now,
        }
        if existing is None:
            entity.update(
                {
                    "CreatedAt": now,
                    "Status": "active",
                    "CommentCount": 0,
                    "ModerationNote": "",
                }
            )
        with self._comment_user_client() as client:
            client.upsert_entity(entity, mode=UpdateMode.MERGE)
            return client.get_entity(partition_key="users", row_key=user_id)

    def increment_comment_user_count(self, *, user_id: str) -> None:
        with self._comment_user_client() as client:
            try:
                entity = client.get_entity(partition_key="users", row_key=user_id)
            except ResourceNotFoundError:
                return
            entity["CommentCount"] = int(entity.get("CommentCount") or 0) + 1
            entity["LastSeenAt"] = datetime.now(UTC)
            client.upsert_entity(entity, mode=UpdateMode.MERGE)

    def update_comment_user_status(
        self,
        *,
        user_id: str,
        status: str,
        note: str = "",
    ) -> None:
        with self._comment_user_client() as client:
            try:
                entity = client.get_entity(partition_key="users", row_key=user_id)
            except ResourceNotFoundError:
                return
            entity["Status"] = status
            entity["ModerationNote"] = note[:500]
            entity["ModeratedAt"] = datetime.now(UTC)
            client.upsert_entity(entity, mode=UpdateMode.MERGE)

    def get_comment_rate_limit(self, *, user_id: str, day_key: str) -> dict | None:
        with self._comment_rate_limit_client() as client:
            try:
                return client.get_entity(partition_key=f"day:{day_key}", row_key=user_id)
            except ResourceNotFoundError:
                return None

    def record_comment_rate_limit(self, *, user_id: str, day_key: str) -> dict:
        now = datetime.now(UTC)
        with self._comment_rate_limit_client() as client:
            try:
                entity = client.get_entity(partition_key=f"day:{day_key}", row_key=user_id)
                entity["Count"] = int(entity.get("Count") or 0) + 1
            except ResourceNotFoundError:
                entity = {
                    "PartitionKey": f"day:{day_key}",
                    "RowKey": user_id,
                    "Count": 1,
                    "CreatedAt": now,
                }
            entity["LastCommentAt"] = now
            client.upsert_entity(entity, mode=UpdateMode.MERGE)
            return entity

    def add_comment(
        self,
        *,
        news_item_id: str,
        user_id: str,
        display_name: str,
        body: str,
        status: str,
    ) -> dict:
        now = datetime.now(UTC)
        comment_id = uuid.uuid4().hex
        row_key = f"{_INVERTED_TS_BASE - int(now.timestamp()):010d}_{comment_id}"
        entity: dict[str, object] = {
            "PartitionKey": f"article:{news_item_id}",
            "RowKey": row_key,
            "CommentId": comment_id,
            "NewsItemId": news_item_id,
            "UserId": user_id,
            "DisplayName": display_name,
            "Body": body,
            "Status": status,
            "CreatedAt": now,
            "UpdatedAt": now,
            "ReportCount": 0,
            "ModerationReason": "",
        }
        with self._comment_client() as client:
            client.create_entity(entity)
        if status != "visible":
            self._upsert_comment_moderation_index(entity)
        self.increment_comment_user_count(user_id=user_id)
        return entity

    def list_visible_comments(self, *, news_item_id: str, limit: int = 50) -> list[dict]:
        comments: list[dict] = []
        with self._comment_client() as client:
            entities = client.query_entities(
                query_filter="PartitionKey eq @pk and Status eq @status",
                parameters={"pk": f"article:{news_item_id}", "status": "visible"},
            )
            for ent in entities:
                comments.append(ent)
                if len(comments) >= limit:
                    break
        return comments

    def visible_comment_counts(self, *, news_item_ids: Iterable[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        with self._comment_client() as client:
            for news_item_id in news_item_ids:
                count = 0
                entities = client.query_entities(
                    query_filter="PartitionKey eq @pk and Status eq @status",
                    parameters={"pk": f"article:{news_item_id}", "status": "visible"},
                    select=["RowKey"],
                )
                for _ in entities:
                    count += 1
                counts[news_item_id] = count
        return counts

    def list_moderation_comments(self, *, status: str, limit: int = 100) -> list[dict]:
        comments: list[dict] = []
        with self._comment_moderation_client() as index_client:
            pointers = index_client.query_entities(
                query_filter="PartitionKey eq @pk",
                parameters={"pk": f"status:{status}"},
            )
            for pointer in pointers:
                partition_key = str(pointer.get("CommentPartitionKey") or "")
                row_key = str(pointer.get("CommentRowKey") or "")
                if not partition_key or not row_key:
                    continue
                try:
                    with self._comment_client() as comment_client:
                        comments.append(
                            comment_client.get_entity(
                                partition_key=partition_key,
                                row_key=row_key,
                            )
                        )
                except ResourceNotFoundError:
                    pass
                if len(comments) >= limit:
                    break
        return comments

    def moderate_comment(
        self,
        *,
        comment_partition_key: str,
        comment_row_key: str,
        action: str,
        reason: str,
    ) -> dict | None:
        status_by_action = {
            "approve": "visible",
            "hide": "hidden",
            "flag": "flagged",
            "reject": "rejected",
        }
        next_status = status_by_action.get(action)
        if next_status is None:
            return None
        with self._comment_client() as client:
            try:
                entity = client.get_entity(
                    partition_key=comment_partition_key,
                    row_key=comment_row_key,
                )
            except ResourceNotFoundError:
                return None
            previous_status = str(entity.get("Status") or "")
            entity["Status"] = next_status
            entity["UpdatedAt"] = datetime.now(UTC)
            entity["ModeratedAt"] = datetime.now(UTC)
            entity["ModerationReason"] = reason[:500]
            client.upsert_entity(entity, mode=UpdateMode.MERGE)
        self._delete_comment_moderation_index(
            status=previous_status,
            comment_partition_key=comment_partition_key,
            comment_row_key=comment_row_key,
        )
        if next_status != "visible":
            self._upsert_comment_moderation_index(entity)
        return entity

    def _comment_index_row_key(self, ent: dict) -> str:
        return f"{ent.get('RowKey')}_{ent.get('CommentId')}"

    def _upsert_comment_moderation_index(self, ent: dict) -> None:
        status = str(ent.get("Status") or "pending")
        with self._comment_moderation_client() as client:
            client.upsert_entity(
                {
                    "PartitionKey": f"status:{status}",
                    "RowKey": self._comment_index_row_key(ent),
                    "CommentPartitionKey": ent.get("PartitionKey"),
                    "CommentRowKey": ent.get("RowKey"),
                    "NewsItemId": ent.get("NewsItemId"),
                    "CreatedAt": ent.get("CreatedAt"),
                    "UpdatedAt": datetime.now(UTC),
                },
                mode=UpdateMode.MERGE,
            )

    def _delete_comment_moderation_index(
        self,
        *,
        status: str,
        comment_partition_key: str,
        comment_row_key: str,
    ) -> None:
        if not status or status == "visible":
            return
        prefix = f"{comment_row_key}_"
        with self._comment_moderation_client() as client:
            entities = client.query_entities(
                query_filter="PartitionKey eq @pk",
                parameters={"pk": f"status:{status}"},
            )
            for ent in entities:
                if (
                    str(ent.get("CommentPartitionKey") or "") == comment_partition_key
                    and str(ent.get("RowKey") or "").startswith(prefix)
                ):
                    client.delete_entity(
                        partition_key=str(ent.get("PartitionKey")),
                        row_key=str(ent.get("RowKey")),
                    )
