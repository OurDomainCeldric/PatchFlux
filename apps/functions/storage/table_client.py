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

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

from azure.core.exceptions import ResourceExistsError
from azure.data.tables import TableClient, TableServiceClient, UpdateMode

from models.news_item import NewsItem

_INVERTED_TS_BASE = 9_999_999_999

log = logging.getLogger(__name__)


def _partition_key(published_at: datetime) -> str:
    dt = published_at.astimezone(timezone.utc)
    return f"{dt.year:04d}-{dt.month:02d}"


def _row_key(published_at: datetime, dedup_hash: str) -> str:
    ts = int(published_at.astimezone(timezone.utc).timestamp())
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
        "Author": item.author or "",
        "CanonicalUrl": str(item.canonical_url),
        "Products": ",".join(item.products),
        "Tags": ",".join(item.tags),
        "Language": item.language,
        "IngestedAt": datetime.now(timezone.utc),
    }


@dataclass
class NewsStore:
    """Thin wrapper over Azure Table Storage for news items + source health."""

    connection_string: str
    news_table: str = "NewsItems"
    source_health_table: str = "SourceHealth"

    def _service(self) -> TableServiceClient:
        return TableServiceClient.from_connection_string(self.connection_string)

    def ensure_tables(self) -> None:
        svc = self._service()
        for name in (self.news_table, self.source_health_table):
            try:
                svc.create_table(name)
                log.info("Created table %s", name)
            except ResourceExistsError:
                pass

    def _news_client(self) -> TableClient:
        return TableClient.from_connection_string(self.connection_string, self.news_table)

    def _health_client(self) -> TableClient:
        return TableClient.from_connection_string(self.connection_string, self.source_health_table)

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

    def query_recent(
        self,
        *,
        limit: int = 50,
        source_id: str | None = None,
        product: str | None = None,
        months_back: int = 36,
    ) -> Iterator[dict]:
        """Return up to *limit* most recent items, optionally filtered.

        Iterates month partitions (YYYY-MM) from the current month backwards
        so results come out newest-first globally. Within a partition, the
        inverted-timestamp RowKey already yields newest-first.
        """
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month

        with self._news_client() as client:
            yielded = 0
            for _ in range(months_back):
                partition = f"{year:04d}-{month:02d}"

                filters = [f"PartitionKey eq '{partition}'"]
                params: dict[str, object] = {}
                if source_id:
                    filters.append("SourceId eq @sid")
                    params["sid"] = source_id
                query = " and ".join(filters)

                entities = client.query_entities(
                    query_filter=query,
                    parameters=params or None,
                )
                for ent in entities:
                    if product and product.lower() not in (ent.get("Products") or "").lower():
                        continue
                    yield ent
                    yielded += 1
                    if yielded >= limit:
                        return

                # step one month back
                month -= 1
                if month == 0:
                    month = 12
                    year -= 1

    # ---- SourceHealth ---------------------------------------------------

    def record_source_health(
        self,
        *,
        source_id: str,
        status: str,
        error: str | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> None:
        entity = {
            "PartitionKey": "sources",
            "RowKey": source_id,
            "LastFetchAt": datetime.now(timezone.utc),
            "LastStatus": status,
            "LastError": error or "",
            "ETag": etag or "",
            "LastModified": last_modified or "",
        }
        with self._health_client() as client:
            client.upsert_entity(entity, mode=UpdateMode.MERGE)

    def get_source_health(self, source_id: str) -> dict | None:
        with self._health_client() as client:
            try:
                return client.get_entity(partition_key="sources", row_key=source_id)
            except Exception:
                return None

    def list_source_health(self) -> Iterator[dict]:
        with self._health_client() as client:
            yield from client.query_entities("PartitionKey eq 'sources'")
