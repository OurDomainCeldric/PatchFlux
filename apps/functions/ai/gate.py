"""Azure OpenAI relevance gate.

Given a freshly-fetched :class:`NewsItem`, the gate:

1. Decides whether the item is in-scope for PatchFlux (Microsoft / IT news).
2. Optionally enriches ``products`` / ``tags`` with structured labels.

Only *already-public* metadata is sent to the model — specifically title,
canonical URL, and source name. No article bodies, snippets, or descriptions.
See LEGAL.md.

Cost safety
-----------
Every call is gated by :class:`ai.budget.BudgetTracker`:

* Before the HTTP request we check :meth:`~BudgetTracker.can_spend`, which
  requires the *worst-case* projected next-call cost to fit within the
  configured monthly USD ceiling.
* After the response we record the *actual* tokens returned by Azure.
* Per-run call count is additionally capped by ``max_calls_per_run``.
* The first transient error disables the gate for the remainder of the run
  to avoid burning budget on repeated failures.

When the gate is disabled, mis-configured, or over budget, it simply passes
items through unchanged.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from models.news_item import NewsItem

from .budget import BudgetState, BudgetTracker
from .pricing import cost_usd

log = logging.getLogger(__name__)

# Some feeds are already deterministically in scope and high-volume enough
# that per-item LLM classification is pure latency and timeout risk.
_SOURCE_BYPASS_IDS = frozenset({"msrc", "cisa-kev"})


_SYSTEM_PROMPT = (
    "You are a strict relevance classifier for PatchFlux, a Microsoft-focused "
    "IT news aggregator. Given ONLY a news item's title, source name and URL, "
    "decide whether the item is in scope.\n\n"
    "In scope: Microsoft products and services (Windows, Windows Server, "
    "Azure, Microsoft 365, Office, Teams, Outlook, Exchange, SharePoint, "
    "OneDrive, Intune, Entra/Azure AD, Defender, Sentinel, Purview, "
    "Copilot, GitHub, .NET, Visual Studio, VS Code, PowerShell, Hyper-V, "
    "WSL, SQL Server, Power Platform, Dynamics 365, Fabric, Viva, Loop, "
    "Xbox, Edge) and CVEs/security advisories that affect those products.\n"
    "Out of scope: general Linux/Apple/Google news that does not mention a "
    "Microsoft product, unrelated consumer tech, politics, sports.\n\n"
    "Respond with STRICT JSON only, matching this schema:\n"
    "{\n"
    "  \"relevant\": boolean,\n"
    "  \"products\": string[],   // lowercase kebab-case IDs, e.g. \"azure\", "
    "\"windows-server\", \"microsoft-365\"\n"
    "  \"tags\": string[]        // lowercase short topic tags, e.g. \"security\", "
    "\"cve\", \"preview\"\n"
    "}\n"
    "No prose, no markdown, no code fences."
)


@dataclass(frozen=True)
class GateOutcome:
    """Result for a single item."""

    item: NewsItem | None           # None when the item was rejected
    decision: str                   # "kept", "rejected", "bypass", "error"
    reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd_delta: float = 0.0


@dataclass
class GateRunStats:
    """Aggregate stats for a single ingest run."""

    calls: int = 0
    kept: int = 0
    rejected: int = 0
    bypassed: int = 0
    errors: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    final_budget: BudgetState | None = None
    per_source: dict[str, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "kept": self.kept,
            "rejected": self.rejected,
            "bypassed": self.bypassed,
            "errors": self.errors,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "budget_cost_usd": (
                round(self.final_budget.cost_usd, 6)
                if self.final_budget is not None
                else None
            ),
            "budget_remaining_usd": (
                round(self.final_budget.remaining_usd, 6)
                if self.final_budget is not None
                else None
            ),
            "per_source": self.per_source,
        }


class AIRelevanceGate:
    """Classifies and enriches news items via Azure OpenAI, with a hard cost cap."""

    def __init__(
        self,
        *,
        client: Any,
        deployment: str,
        model: str,
        budget: BudgetTracker,
        max_calls_per_run: int = 100,
        max_output_tokens: int = 150,
    ) -> None:
        self._client = client
        self._deployment = deployment
        self._model = model
        self._budget = budget
        self._max_calls_per_run = max(0, int(max_calls_per_run))
        self._max_output_tokens = max(1, int(max_output_tokens))

    # ---- public API -----------------------------------------------------

    def process(
        self, items: list[NewsItem], *, source_id: str, stats: GateRunStats
    ) -> list[NewsItem]:
        """Classify a batch. Returns the kept subset (possibly enriched)."""
        if not items:
            return []
        if source_id in _SOURCE_BYPASS_IDS:
            stats.bypassed += len(items)
            for _ in items:
                self._bump(stats, source_id, "bypassed")
            if stats.final_budget is None:
                stats.final_budget = self._budget.read()
            return items

        kept: list[NewsItem] = []
        disabled_for_run = False

        for item in items:
            if disabled_for_run:
                kept.append(item)
                stats.bypassed += 1
                self._bump(stats, source_id, "bypassed")
                continue

            if stats.calls >= self._max_calls_per_run:
                log.warning(
                    "AI gate reached per-run cap (%d); passing remaining items through",
                    self._max_calls_per_run,
                )
                kept.append(item)
                stats.bypassed += 1
                self._bump(stats, source_id, "bypassed")
                continue

            if not self._budget.can_spend():
                log.warning("AI gate monthly budget exhausted; passing remaining items through")
                kept.append(item)
                stats.bypassed += 1
                self._bump(stats, source_id, "bypassed")
                disabled_for_run = True
                continue

            outcome = self._classify_one(item)
            stats.calls += 1
            stats.input_tokens += outcome.input_tokens
            stats.output_tokens += outcome.output_tokens
            stats.cost_usd += outcome.cost_usd_delta

            if outcome.decision == "kept" and outcome.item is not None:
                kept.append(outcome.item)
                stats.kept += 1
                self._bump(stats, source_id, "kept")
            elif outcome.decision == "rejected":
                stats.rejected += 1
                self._bump(stats, source_id, "rejected")
            elif outcome.decision == "error":
                # Keep the item (fail-open) but disable the gate for the rest of
                # the run so we don't burn the monthly budget on a broken feed
                # or a transient Azure OpenAI outage.
                kept.append(item)
                stats.errors += 1
                self._bump(stats, source_id, "error")
                disabled_for_run = True
            else:
                # "bypass" (unexpected reply, keep item)
                kept.append(item)
                stats.bypassed += 1
                self._bump(stats, source_id, "bypassed")

            if outcome.input_tokens or outcome.output_tokens:
                stats.final_budget = self._budget.record(
                    input_tokens=outcome.input_tokens,
                    output_tokens=outcome.output_tokens,
                )

        if stats.final_budget is None:
            stats.final_budget = self._budget.read()
        return kept

    # ---- internal -------------------------------------------------------

    @staticmethod
    def _bump(stats: GateRunStats, source_id: str, bucket: str) -> None:
        per = stats.per_source.setdefault(
            source_id,
            {"kept": 0, "rejected": 0, "bypassed": 0, "error": 0},
        )
        per[bucket] = per.get(bucket, 0) + 1

    def _user_message(self, item: NewsItem) -> str:
        return json.dumps(
            {
                "title": item.title,
                "source_name": item.source_name,
                "url": str(item.canonical_url),
                "language": item.language,
            },
            ensure_ascii=False,
        )

    def _classify_one(self, item: NewsItem) -> GateOutcome:
        try:
            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": self._user_message(item)},
                ],
                max_tokens=self._max_output_tokens,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("AI gate call failed for %s: %s", item.source_id, exc)
            return GateOutcome(item=item, decision="error", reason=str(exc))

        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
        delta_cost = cost_usd(self._model, input_tokens, output_tokens)

        try:
            choice = response.choices[0]
            raw = choice.message.content or "{}"
            payload = json.loads(raw)
        except (ValueError, AttributeError, IndexError, TypeError) as exc:
            log.warning("AI gate reply parse error: %s", exc)
            return GateOutcome(
                item=item,
                decision="bypass",
                reason="parse-error",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd_delta=delta_cost,
            )

        relevant = bool(payload.get("relevant", False))
        if not relevant:
            return GateOutcome(
                item=None,
                decision="rejected",
                reason="classifier",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd_delta=delta_cost,
            )

        products = _clean_tags(payload.get("products"))
        tags = _clean_tags(payload.get("tags"))

        merged_products = tuple(sorted(set(item.products) | set(products)))
        merged_tags = tuple(sorted(set(item.tags) | set(tags)))

        try:
            enriched = item.model_copy(
                update={"products": merged_products, "tags": merged_tags}
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("AI gate enrichment failed: %s", exc)
            enriched = item

        return GateOutcome(
            item=enriched,
            decision="kept",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd_delta=delta_cost,
        )


def _clean_tags(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, (list, tuple)):
        return ()
    cleaned: set[str] = set()
    for value in raw:
        if not isinstance(value, str):
            continue
        v = value.strip().lower()
        if not v or len(v) > 64:
            continue
        cleaned.add(v)
    return tuple(sorted(cleaned))


def build_gate(
    *,
    enabled: bool,
    endpoint: str,
    api_key: str,
    deployment: str,
    model: str,
    api_version: str,
    budget: BudgetTracker,
    max_calls_per_run: int,
    max_output_tokens: int,
) -> AIRelevanceGate | None:
    """Factory that returns ``None`` when the gate is disabled or not configured.

    The Azure OpenAI SDK is imported lazily so the module stays importable in
    environments where the ``openai`` package is not installed (tests, CI
    before opt-in, …).
    """
    if not enabled:
        return None
    if not (endpoint and api_key and deployment):
        log.info("AI gate enabled but Azure OpenAI settings are incomplete; disabled")
        return None
    try:
        from openai import AzureOpenAI  # type: ignore[import-not-found]
    except ImportError:
        log.warning("AI gate enabled but the 'openai' package is not installed")
        return None

    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
    )
    budget.ensure_table()
    return AIRelevanceGate(
        client=client,
        deployment=deployment,
        model=model,
        budget=budget,
        max_calls_per_run=max_calls_per_run,
        max_output_tokens=max_output_tokens,
    )
