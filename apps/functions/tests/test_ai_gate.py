"""Tests for the AIRelevanceGate using a fake Azure OpenAI client."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

from ai.budget import BudgetTracker
from ai.gate import AIRelevanceGate, GateRunStats
from models.news_item import NewsItem


class _FakeBudget(BudgetTracker):
    """BudgetTracker subclass that skips storage entirely."""

    def __init__(self, *, max_monthly_usd: float = 5.0, reserve: float = 0.001) -> None:
        super().__init__(
            connection_string="",
            table_name="",
            max_monthly_usd=max_monthly_usd,
            model="gpt-4o-mini",
            reserve_per_call_usd=reserve,
        )
        self._cost = 0.0
        self._calls = 0

    def ensure_table(self) -> None:  # noqa: D401
        return None

    def can_spend(self, *, now: datetime | None = None) -> bool:  # noqa: ARG002
        return self._cost + self._reserve_per_call_usd <= self._max_monthly_usd

    def record(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        now: datetime | None = None,  # noqa: ARG002
    ):
        from ai.budget import BudgetState
        from ai.pricing import cost_usd

        self._cost += cost_usd("gpt-4o-mini", input_tokens, output_tokens)
        self._calls += 1
        return BudgetState(
            year_month="2026-04",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._cost,
            calls=self._calls,
            max_monthly_usd=self._max_monthly_usd,
        )

    def read(self, *, now: datetime | None = None):  # noqa: ARG002
        from ai.budget import BudgetState

        return BudgetState(
            year_month="2026-04",
            input_tokens=0,
            output_tokens=0,
            cost_usd=self._cost,
            calls=self._calls,
            max_monthly_usd=self._max_monthly_usd,
        )


class _FakeClient:
    """Fake Azure OpenAI chat client whose replies are scripted per-index."""

    def __init__(self, replies: list[object]) -> None:
        self._replies = list(replies)
        self.calls: list[dict] = []

        fake_self = self

        class _Completions:
            def create(_cls, **kwargs):  # noqa: N805
                fake_self.calls.append(kwargs)
                reply = fake_self._replies.pop(0)
                if isinstance(reply, Exception):
                    raise reply
                return reply

        self.chat = SimpleNamespace(completions=_Completions())


def _mk_response(payload: dict, *, prompt_tokens: int = 120, completion_tokens: int = 40):
    msg = SimpleNamespace(content=json.dumps(payload))
    choice = SimpleNamespace(message=msg)
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
    return SimpleNamespace(choices=[choice], usage=usage)


def _mk_item(title: str, *, products: tuple[str, ...] = ()) -> NewsItem:
    return NewsItem(
        title=title,
        published_at=datetime(2026, 4, 20, tzinfo=UTC),
        source_id="heise",
        source_name="heise online",
        canonical_url="https://example.com/a",
        products=products,
        tags=(),
        language="de",
    )


def _gate(client: _FakeClient, *, max_calls: int = 100, budget: _FakeBudget | None = None):
    budget = budget or _FakeBudget()
    return AIRelevanceGate(
        client=client,
        deployment="patchflux-gate",
        model="gpt-4o-mini",
        budget=budget,
        max_calls_per_run=max_calls,
        max_output_tokens=150,
    )


def test_gate_keeps_relevant_and_enriches_products() -> None:
    client = _FakeClient(
        [_mk_response({"relevant": True, "products": ["azure"], "tags": ["security"]})]
    )
    gate = _gate(client)
    stats = GateRunStats()
    kept = gate.process(
        [_mk_item("Azure security bulletin")], source_id="heise", stats=stats
    )
    assert len(kept) == 1
    assert "azure" in kept[0].products
    assert "security" in kept[0].tags
    assert stats.kept == 1
    assert stats.rejected == 0
    assert stats.calls == 1


def test_gate_drops_irrelevant_items() -> None:
    client = _FakeClient([_mk_response({"relevant": False, "products": [], "tags": []})])
    gate = _gate(client)
    stats = GateRunStats()
    kept = gate.process(
        [_mk_item("Apple unveils new iPhone color")], source_id="heise", stats=stats
    )
    assert kept == []
    assert stats.rejected == 1
    assert stats.kept == 0


def test_gate_respects_monthly_budget_cap() -> None:
    # Budget is exhausted from the start; no calls may be issued and all
    # items pass through untouched (fail-open).
    tight_budget = _FakeBudget(max_monthly_usd=0.0)
    client = _FakeClient([])  # must never be called
    gate = _gate(client, budget=tight_budget)
    stats = GateRunStats()
    items = [_mk_item("Unrelated gadget news"), _mk_item("Windows 11 build 26xxx")]
    kept = gate.process(items, source_id="heise", stats=stats)
    assert kept == items
    assert stats.calls == 0
    assert stats.bypassed == len(items)
    assert client.calls == []


def test_gate_respects_per_run_call_cap() -> None:
    client = _FakeClient(
        [_mk_response({"relevant": True, "products": [], "tags": []})]
    )
    gate = _gate(client, max_calls=1)
    stats = GateRunStats()
    items = [_mk_item("Azure one"), _mk_item("Azure two"), _mk_item("Azure three")]
    kept = gate.process(items, source_id="heise", stats=stats)
    # Exactly one real call; the remaining items bypass the gate.
    assert stats.calls == 1
    assert stats.bypassed == 2
    assert len(kept) == 3


def test_gate_disables_after_transient_error() -> None:
    # First call raises, subsequent items bypass (fail-open) and no further
    # calls are issued, so we don't burn budget on a broken deployment.
    client = _FakeClient([RuntimeError("boom")])
    gate = _gate(client)
    stats = GateRunStats()
    kept = gate.process(
        [_mk_item("Azure one"), _mk_item("Azure two")],
        source_id="heise",
        stats=stats,
    )
    assert len(kept) == 2
    assert stats.errors == 1
    assert stats.bypassed == 1
    assert len(client.calls) == 1


def test_gate_bypasses_on_malformed_reply() -> None:
    bad = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )
    client = _FakeClient([bad])
    gate = _gate(client)
    stats = GateRunStats()
    kept = gate.process([_mk_item("Azure one")], source_id="heise", stats=stats)
    # Fail-open: item is kept, counted as bypassed, tokens still accounted for.
    assert len(kept) == 1
    assert stats.bypassed == 1
    assert stats.input_tokens == 10
    assert stats.output_tokens == 5


def test_gate_bypasses_high_frequency_security_sources_without_calls() -> None:
    client = _FakeClient([])  # must never be called
    gate = _gate(client)
    stats = GateRunStats()
    items = [_mk_item("CVE-2026-12345"), _mk_item("CVE-2026-12346")]
    kept = gate.process(items, source_id="msrc", stats=stats)
    assert kept == items
    assert stats.calls == 0
    assert stats.bypassed == 2
    assert stats.per_source["msrc"]["bypassed"] == 2
    assert client.calls == []
