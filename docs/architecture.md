# PatchFlux Architecture Guide

This guide is the onboarding-oriented system overview for contributors. It complements the short project overview in [README.md](/F:/GitRepos/PatchFlux/README.md) and the non-negotiable compliance rules in [LEGAL.md](/F:/GitRepos/PatchFlux/LEGAL.md) and [AGENTS.md](/F:/GitRepos/PatchFlux/AGENTS.md).

## Project Goal

PatchFlux is an independent, third-party aggregator for Microsoft product changes, new features, and IT news. The product intentionally stores and renders only legally safe metadata and always links back to the original publisher.

The most important design rule is that PatchFlux must not become a substitute for the original article.

## Hard Legal Guardrails

- Only official APIs and standardized RSS/Atom feeds may be used. No HTML scraping.
- Only metadata may be stored for third-party content: title, publication date, source, author, canonical URL, product labels, topic labels, ingestion metadata.
- No article body, snippet, summary, description, or image fields may be introduced for third-party content.
- Publisher names are plain text only. No logos, wordmarks, or brand assets.
- Outbound article links must use `target="_blank" rel="noopener nofollow"`.

The schema whitelist that enforces this boundary lives in [apps/functions/models/news_item.py](/F:/GitRepos/PatchFlux/apps/functions/models/news_item.py:1).

## System Overview

PatchFlux currently consists of five main parts:

- `apps/web`: Next.js 15 static-export frontend with `next-intl` for German and English.
- `apps/functions`: Azure Functions app for ingestion, read APIs, feeds, and health reporting.
- Azure Table Storage: persistence for `NewsItems` and `SourceHealth`.
- `infra`: Bicep templates for Azure deployment.
- `.github/workflows`: separate CI/CD pipelines for web, functions, and infrastructure.

There is also a small browser extension in [browser-extension](/F:/GitRepos/PatchFlux/browser-extension) that consumes the live `hot` API directly from the Azure Function host.

## End-to-End Flow

```text
Official API / RSS / Atom / public JSON
        -> Azure Functions ingest timers or manual ingest endpoint
        -> adapter-specific fetch with Conditional GET and transparent User-Agent
        -> NewsItem validation and source-health tracking
        -> Azure Table Storage
        -> Azure Functions read endpoints
        -> Next.js frontend and browser extension
```

The product does not scrape article pages and does not persist article bodies.

## Backend Responsibilities

The main entry point is [apps/functions/function_app.py](/F:/GitRepos/PatchFlux/apps/functions/function_app.py:1).

### Ingest scheduling

- `ingest_timer_high`: every 30 minutes for `msrc` and `cisa-kev`
- `ingest_timer_mid`: every 3 hours for blogs and news feeds
- `ingest_timer_low`: daily at `05:00 UTC` for `m365-roadmap` and `azure-updates`
- `ingest_http`: manual ingest trigger protected by Function auth

### Public read endpoints

- `/api/news`
- `/api/sources`
- `/api/products`
- `/api/topics`
- `/api/hot`
- `/api/health`
- `/api/feed.xml`
- `/api/atom.xml`

### Source adapter model

Every source adapter implements the `SourceAdapter` interface in [apps/functions/sources/base.py](/F:/GitRepos/PatchFlux/apps/functions/sources/base.py:1).

Common rules:

- fetches must identify PatchFlux via `User-Agent`
- feeds should use `ETag` and `Last-Modified` when supported
- adapters must only emit `NewsItem` metadata
- malformed entries should be skipped, not crash the whole ingest run

Most RSS/Atom adapters reuse helpers from [apps/functions/sources/_rss.py](/F:/GitRepos/PatchFlux/apps/functions/sources/_rss.py:1).

## Storage Model

The storage wrapper lives in [apps/functions/storage/table_client.py](/F:/GitRepos/PatchFlux/apps/functions/storage/table_client.py:1).

### `NewsItems`

- `PartitionKey`: `YYYY-MM` derived from `PublishedAt`
- `RowKey`: inverted timestamp plus dedup hash prefix
- purpose: newest-first queries across month partitions

Each entity stores metadata only:

- title
- publication timestamp
- source id and name
- source tier
- author
- canonical URL
- products
- tags
- language
- ingestion timestamp
- dedup hash

### `SourceHealth`

- `PartitionKey`: `sources`
- `RowKey`: source id
- tracks last fetch attempt, last status, last error, conditional GET headers, and items written

This table powers `/api/sources` and contributes to `/api/health`.

## Frontend Responsibilities

The web app lives in [apps/web](/F:/GitRepos/PatchFlux/apps/web).

Current frontend responsibilities:

- locale-aware rendering via `next-intl`
- fetch and render public API data from `apps/web/lib/api.ts`
- split the feed into `news` and `community`
- apply filters for source, product, language, time range, deduplication, hot-only, and topics
- render a `hot` ticker
- expose footer links, legal pages, and feed links

Important frontend entry points:

- [apps/web/app/[locale]/page.tsx](/F:/GitRepos/PatchFlux/apps/web/app/[locale]/page.tsx:1)
- [apps/web/components/NewsList.tsx](/F:/GitRepos/PatchFlux/apps/web/components/NewsList.tsx:1)
- [apps/web/components/FilterBar.tsx](/F:/GitRepos/PatchFlux/apps/web/components/FilterBar.tsx:1)
- [apps/web/lib/api.ts](/F:/GitRepos/PatchFlux/apps/web/lib/api.ts:1)

## Infrastructure and Deployment

- Web deploy: [.github/workflows/web.yml](/F:/GitRepos/PatchFlux/.github/workflows/web.yml:1)
- Functions deploy: [.github/workflows/functions.yml](/F:/GitRepos/PatchFlux/.github/workflows/functions.yml:1)
- Infra deploy: [.github/workflows/infra.yml](/F:/GitRepos/PatchFlux/.github/workflows/infra.yml:1)
- Azure resource definitions: [infra/main.bicep](/F:/GitRepos/PatchFlux/infra/main.bicep:1)

The intended hosting model is:

- Azure Static Web Apps for the static frontend
- Azure Functions on Consumption for ingest and read APIs
- Azure Table Storage for persistence

## Public Surfaces

PatchFlux currently exposes three user-facing surfaces:

- the web frontend on `patchflux.de`
- the Function-hosted JSON and XML APIs
- the browser extension popup that reads `https://func-omlorsnews-prod.azurewebsites.net/api/hot`

Two API access paths matter operationally:

- expected public website path: `https://patchflux.de/api/...`
- direct live Function path: `https://func-omlorsnews-prod.azurewebsites.net/api/...`

## Critical Change Hotspots

These areas deserve extra care during reviews.

### 1. Metadata schema boundary

File: [apps/functions/models/news_item.py](/F:/GitRepos/PatchFlux/apps/functions/models/news_item.py:1)

Why it is critical:

- this is the schema whitelist that prevents accidental storage of protected third-party content
- adding body-like fields here would violate the core legal model

### 2. Ingest orchestration, health, and feed output

File: [apps/functions/function_app.py](/F:/GitRepos/PatchFlux/apps/functions/function_app.py:1)

Why it is critical:

- contains timer grouping and ingest execution
- defines public API wire behavior
- controls health interpretation and source staleness
- generates RSS and Atom outputs

### 3. Topic classification and frontend defaults

Files:

- [apps/functions/topics.py](/F:/GitRepos/PatchFlux/apps/functions/topics.py:1)
- [apps/web/components/FilterBar.tsx](/F:/GitRepos/PatchFlux/apps/web/components/FilterBar.tsx:1)

Why they are critical:

- topic classification is title-only and directly shapes visibility in the UI
- default topic selection currently hides CVEs and any items with no derived topic
- small changes here can dramatically change what users think was or was not ingested

### 4. API routing and frontend connectivity

Files:

- [apps/web/lib/api.ts](/F:/GitRepos/PatchFlux/apps/web/lib/api.ts:1)
- [apps/web/public/staticwebapp.config.json](/F:/GitRepos/PatchFlux/apps/web/public/staticwebapp.config.json:1)

Why they are critical:

- determine whether the frontend uses `/api` or the direct Function host
- affect feed links, CSP, and public runtime behavior
- routing mistakes can make the site look empty even when the backend works

### 5. Source adapters

Directory: [apps/functions/sources](/F:/GitRepos/PatchFlux/apps/functions/sources:1)

Why it is critical:

- every new source must stay within the legal acquisition policy
- adapters must remain feed/API based
- scraper-like logic must not be introduced casually

## Current Operating State (as of April 27, 2026)

The following observations were verified against the live deployment on April 27, 2026.

### Verified findings

- `https://patchflux.de/api/...` currently returns `Azure Static Web Apps - 404 Not Found` instead of serving the expected API path.
- The frontend is therefore effectively relying on `NEXT_PUBLIC_API_BASE_URL` and talking directly to `https://func-omlorsnews-prod.azurewebsites.net/api`.
- The impression that "only one article arrived since Saturday" is reproducible under the current default frontend filters.

### Why only one item is visible under defaults

- the default topic selection excludes `cve`
- many press and blog headlines currently receive no derived topic at all in `compute_topics(...)`
- under the default topic filter set, the live API returned exactly 1 visible item since Saturday, April 26, 2026 `00:00 UTC`
- the same live backend returned far more raw items when queried without that default topic restriction

This means the symptom is primarily a visibility and filtering problem, not proof of a complete ingest outage.

### Confirmed live ingest and operations issues

- `reddit-microsoft`: `HTTP 403`
- `reddit-sysadmin`: `HTTP 403`
- `msrc` and `cisa-kev` were reported stale by `/api/health`
- their `LastFetchAt` values were still on April 26, 2026 at around `09:00` local time, which strongly suggests the high-frequency ingest path stopped firing or stopped completing successfully

### What still appears healthy

There was no sign of a full backend shutdown. On April 27, 2026, the live source status still showed successful recent writes from:

- `azure-updates`
- `m365-roadmap`
- `heise`
- `borns-it`
- `ms-security-blog`
- `ms-tech-community`
- `windows-it-pro-blog`
- `bleeping-computer`

## Suggested Contributor Workflow

- read [LEGAL.md](/F:/GitRepos/PatchFlux/LEGAL.md) first
- read this architecture guide second
- inspect `function_app.py`, `news_item.py`, `topics.py`, and `apps/web/lib/api.ts` before changing user-facing behavior
- treat source additions, schema changes, and API-routing changes as high-risk work
- use [docs/backlog.md](/F:/GitRepos/PatchFlux/docs/backlog.md) as the starting point for follow-up product work
