# AGENTS.md — Guidance for AI coding assistants (GitHub Copilot, etc.)

This repository has **strict legal guardrails**. Read this file before making changes.

## Project intent

**PatchFlux** is an **independent third-party aggregator** of Microsoft / IT news. It pulls metadata from official APIs and RSS/Atom feeds, stores only legally safe metadata, and links back to the original publisher. See [LEGAL.md](LEGAL.md).

## Monorepo layout

- `apps/web/` — Next.js 15 (App Router, Static Export), TypeScript, Tailwind, shadcn/ui, `next-intl` (DE/EN)
- `apps/functions/` — Azure Functions, Python 3.11, v2 programming model
- `infra/` — Bicep templates (target: RG `RG-NewsBot`, region `westeurope`; subscription ID is stored as the `AZURE_SUBSCRIPTION_ID` GitHub Actions secret)
- `.github/workflows/` — CI/CD

## Hard rules (do not violate)

1. **Never** add fields for article body/full text/snippet/description/summary/image on third-party content to any storage schema, API response, or UI component. See `apps/functions/models/news_item.py`.
2. **Never** render logos, wordmarks, or brand assets of Microsoft, Heise, Borns IT, or any publisher. Source names are plain text.
3. **Never** introduce HTML scraping. If a source has no API/RSS, bring it up for discussion — do not improvise.
4. **Always** set outbound links with `target="_blank" rel="noopener nofollow"`.
5. **Always** use Conditional GET (ETag / Last-Modified) in ingestion code and set a transparent `User-Agent`.

## Soft rules (preferences)

- Python: `ruff` + `black`, type hints, `pydantic` v2.
- TypeScript: strict mode, ESLint + Prettier, functional React components.
- Azure Functions: v2 programming model (`function_app.py`), no `function.json` files.
- Storage: partition by month (`YYYY-MM`), inverted timestamp in row key for newest-first queries.
- Tests: `pytest` for Python, Playwright or Vitest for web (later).

## Infrastructure defaults

- Subscription: stored as the `AZURE_SUBSCRIPTION_ID` GitHub Actions secret; for local `az` use `$env:AZURE_SUBSCRIPTION_ID`
- Resource group: `RG-NewsBot`
- Region: `westeurope`
- Stay on free / consumption tiers until told otherwise.

## When in doubt

Prefer asking over adding a feature that might affect legal compliance or cost. Flag anything that needs explicit approval (e.g. Azure OpenAI, Cosmos DB, SQL).
