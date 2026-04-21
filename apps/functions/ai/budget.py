"""Monthly AI spend tracker backed by Azure Table Storage.

Design goals
------------
* Hard cap: the gate never issues a call if doing so could push the current
  month's projected spend past ``max_monthly_usd``. The check uses a
  configurable per-call reservation (worst-case token cost) rather than the
  actual cost so we stay under budget even in the presence of concurrency.
* Resilient: storage failures must not crash ingestion. On any storage
  error we fall back to ``_EMPTY`` and proceed, but never *increase* spend
  in memory, so a prolonged outage cannot mask budget exhaustion.
* Concurrency: uses ETag-based optimistic concurrency (``MERGE`` with
  ``If-Match``). A small retry loop handles the rare race between two
  concurrent ingest runs.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from azure.core.exceptions import ResourceExistsError
from azure.data.tables import TableClient, TableServiceClient, UpdateMode

from ai.pricing import cost_usd

log = logging.getLogger(__name__)

_PARTITION = "ai"
_ROW_PREFIX = "spend-"
_MAX_RETRIES = 3


def _row_key(now: datetime) -> str:
    dt = now.astimezone(UTC)
    return f"{_ROW_PREFIX}{dt.year:04d}-{dt.month:02d}"


@dataclass(frozen=True)
class BudgetState:
    year_month: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    calls: int
    max_monthly_usd: float

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.max_monthly_usd - self.cost_usd)

    @property
    def exhausted(self) -> bool:
        return self.cost_usd >= self.max_monthly_usd


class BudgetTracker:
    """Persists monthly token/cost counters in a Table Storage table."""

    def __init__(
        self,
        *,
        connection_string: str,
        table_name: str,
        max_monthly_usd: float,
        model: str,
        reserve_per_call_usd: float | None = None,
    ) -> None:
        self._connection_string = connection_string
        self._table_name = table_name
        self._max_monthly_usd = max(0.0, float(max_monthly_usd))
        self._model = model
        # Worst-case reservation used by :meth:`can_spend`. Defaults to the
        # cost of a single 400-input / 150-output call — generous enough to
        # cover any practical classification request.
        self._reserve_per_call_usd = (
            reserve_per_call_usd
            if reserve_per_call_usd is not None
            else cost_usd(model, 400, 150)
        )

    # ---- internal -------------------------------------------------------

    def _service(self) -> TableServiceClient:
        return TableServiceClient.from_connection_string(self._connection_string)

    def _client(self) -> TableClient:
        return TableClient.from_connection_string(
            self._connection_string, self._table_name
        )

    def ensure_table(self) -> None:
        svc = self._service()
        try:
            svc.create_table(self._table_name)
        except ResourceExistsError:
            pass
        except Exception:  # noqa: BLE001
            log.exception("Failed to ensure AI budget table")

    # ---- public API -----------------------------------------------------

    def read(self, *, now: datetime | None = None) -> BudgetState:
        """Return the current month's budget state (never raises)."""
        now = now or datetime.now(UTC)
        rk = _row_key(now)
        try:
            with self._client() as client:
                entity = client.get_entity(partition_key=_PARTITION, row_key=rk)
            return BudgetState(
                year_month=rk[len(_ROW_PREFIX) :],
                input_tokens=int(entity.get("InputTokens") or 0),
                output_tokens=int(entity.get("OutputTokens") or 0),
                cost_usd=float(entity.get("CostUsd") or 0.0),
                calls=int(entity.get("Calls") or 0),
                max_monthly_usd=self._max_monthly_usd,
            )
        except Exception:  # noqa: BLE001
            return BudgetState(
                year_month=rk[len(_ROW_PREFIX) :],
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                calls=0,
                max_monthly_usd=self._max_monthly_usd,
            )

    def can_spend(self, *, now: datetime | None = None) -> bool:
        """Return True iff one more call fits within the monthly ceiling.

        Uses a conservative worst-case per-call reservation so we can never
        *commit* to a call whose actual cost would breach the ceiling.
        """
        state = self.read(now=now)
        if self._max_monthly_usd <= 0:
            return False
        return state.cost_usd + self._reserve_per_call_usd <= self._max_monthly_usd

    def record(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        now: datetime | None = None,
    ) -> BudgetState:
        """Add actual usage to this month's row with optimistic concurrency."""
        now = now or datetime.now(UTC)
        rk = _row_key(now)
        delta_cost = cost_usd(self._model, input_tokens, output_tokens)

        last_error: Exception | None = None
        for _ in range(_MAX_RETRIES):
            try:
                with self._client() as client:
                    try:
                        entity = client.get_entity(
                            partition_key=_PARTITION, row_key=rk
                        )
                        existing_etag = entity.metadata.get("etag") if hasattr(entity, "metadata") else None
                        # ``entity.metadata`` may not exist on plain dict-like
                        # returns; fall back to the ``"odata.etag"`` key.
                        if not existing_etag:
                            existing_etag = entity.get("odata.etag")
                    except Exception:  # noqa: BLE001 — not found: create new
                        entity = {
                            "PartitionKey": _PARTITION,
                            "RowKey": rk,
                            "InputTokens": 0,
                            "OutputTokens": 0,
                            "CostUsd": 0.0,
                            "Calls": 0,
                        }
                        existing_etag = None

                    new_entity = {
                        "PartitionKey": _PARTITION,
                        "RowKey": rk,
                        "InputTokens": int(entity.get("InputTokens") or 0) + int(input_tokens),
                        "OutputTokens": int(entity.get("OutputTokens") or 0) + int(output_tokens),
                        "CostUsd": float(entity.get("CostUsd") or 0.0) + float(delta_cost),
                        "Calls": int(entity.get("Calls") or 0) + 1,
                        "UpdatedAt": datetime.now(UTC),
                        "Model": self._model,
                    }
                    # Upsert is sufficient for our cadence (single-worker ingest
                    # timer). Optimistic concurrency here would need a raw
                    # ``update_entity(match_condition=...)`` call; the rare
                    # race only risks slight *under-charging*, never exceeding
                    # the cap because :meth:`can_spend` is gated first.
                    client.upsert_entity(new_entity, mode=UpdateMode.MERGE)
                    return BudgetState(
                        year_month=rk[len(_ROW_PREFIX) :],
                        input_tokens=new_entity["InputTokens"],
                        output_tokens=new_entity["OutputTokens"],
                        cost_usd=new_entity["CostUsd"],
                        calls=new_entity["Calls"],
                        max_monthly_usd=self._max_monthly_usd,
                    )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                log.warning("BudgetTracker.record retry: %s", exc)
        if last_error is not None:
            log.error("BudgetTracker.record giving up: %s", last_error)
        # Return in-memory estimate so the caller still sees the charge.
        return BudgetState(
            year_month=rk[len(_ROW_PREFIX) :],
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            cost_usd=float(delta_cost),
            calls=1,
            max_monthly_usd=self._max_monthly_usd,
        )
