"""Tests for the AI BudgetTracker.

These tests stub out Azure Table Storage with an in-memory fake so the
budget logic can be exercised without the Azurite emulator. They verify:

* A brand-new month starts at zero spend.
* ``can_spend`` refuses once projected next-call cost would breach the cap.
* ``record`` accumulates tokens + cost across calls.
* Storage errors degrade gracefully to a zeroed state (fail-open read).
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from ai.budget import BudgetTracker
from ai.pricing import cost_usd


class _FakeTable:
    """Minimal in-memory stand-in for ``azure.data.tables.TableClient``."""

    def __init__(self, store: dict[tuple[str, str], dict]) -> None:
        self._store = store

    def __enter__(self) -> _FakeTable:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def get_entity(self, *, partition_key: str, row_key: str) -> dict:
        key = (partition_key, row_key)
        if key not in self._store:
            raise KeyError(key)
        return dict(self._store[key])

    def upsert_entity(self, entity: dict, *, mode: object = None) -> None:  # noqa: ARG002
        key = (entity["PartitionKey"], entity["RowKey"])
        self._store[key] = dict(entity)


class _FakeServiceClient:
    def __init__(self, store: dict) -> None:
        self._store = store

    @classmethod
    def make(cls, store: dict):  # pragma: no cover - tiny factory
        def _factory(_conn: str) -> _FakeServiceClient:
            return cls(store)

        return _factory

    def create_table(self, name: str) -> None:  # noqa: ARG002 — idempotent no-op
        return None


def _fresh_tracker(max_usd: float = 5.0) -> tuple[BudgetTracker, dict]:
    store: dict = {}

    def _svc_factory(_conn: str) -> _FakeServiceClient:
        return _FakeServiceClient(store)

    def _tbl_factory(_conn: str, _name: str) -> _FakeTable:
        return _FakeTable(store)

    tracker = BudgetTracker(
        connection_string="UseDevelopmentStorage=true",
        table_name="AiBudget",
        max_monthly_usd=max_usd,
        model="gpt-4o-mini",
        reserve_per_call_usd=0.001,
    )
    # Monkey-patch the SDK factories used inside the tracker.
    patcher_svc = patch(
        "ai.budget.TableServiceClient.from_connection_string",
        side_effect=_svc_factory,
    )
    patcher_tbl = patch(
        "ai.budget.TableClient.from_connection_string",
        side_effect=_tbl_factory,
    )
    patcher_svc.start()
    patcher_tbl.start()
    return tracker, store


def test_fresh_month_starts_at_zero() -> None:
    tracker, _ = _fresh_tracker()
    state = tracker.read(now=datetime(2026, 4, 1, tzinfo=UTC))
    assert state.cost_usd == 0.0
    assert state.calls == 0
    assert state.remaining_usd == 5.0
    assert not state.exhausted


def test_record_accumulates_cost() -> None:
    tracker, _ = _fresh_tracker()
    now = datetime(2026, 4, 10, tzinfo=UTC)
    state_a = tracker.record(input_tokens=300, output_tokens=150, now=now)
    state_b = tracker.record(input_tokens=200, output_tokens=100, now=now)
    assert state_b.calls == 2
    assert state_b.input_tokens == 500
    assert state_b.output_tokens == 250
    # Cost must equal gpt-4o-mini pricing over the total tokens.
    expected = cost_usd("gpt-4o-mini", 500, 250)
    assert abs(state_b.cost_usd - expected) < 1e-9
    assert state_a.calls == 1


def test_can_spend_respects_hard_cap() -> None:
    tracker, _ = _fresh_tracker(max_usd=0.002)
    now = datetime(2026, 4, 10, tzinfo=UTC)
    # Reserve is 0.001 -> two calls fit, third does not.
    assert tracker.can_spend(now=now) is True
    tracker.record(input_tokens=10, output_tokens=5, now=now)
    assert tracker.can_spend(now=now) is True
    # Simulate spending up to the cap.
    tracker.record(input_tokens=1_000_000, output_tokens=1_000_000, now=now)
    assert tracker.can_spend(now=now) is False


def test_zero_budget_refuses_all_calls() -> None:
    tracker, _ = _fresh_tracker(max_usd=0.0)
    assert tracker.can_spend() is False


def test_monthly_partitioning() -> None:
    tracker, store = _fresh_tracker()
    tracker.record(
        input_tokens=100,
        output_tokens=50,
        now=datetime(2026, 4, 5, tzinfo=UTC),
    )
    tracker.record(
        input_tokens=200,
        output_tokens=100,
        now=datetime(2026, 5, 1, tzinfo=UTC),
    )
    # Two distinct monthly rows.
    keys = sorted(store.keys())
    assert keys == [("ai", "spend-2026-04"), ("ai", "spend-2026-05")]
    april = tracker.read(now=datetime(2026, 4, 20, tzinfo=UTC))
    may = tracker.read(now=datetime(2026, 5, 10, tzinfo=UTC))
    assert april.calls == 1
    assert may.calls == 1
