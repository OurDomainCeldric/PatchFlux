# PatchFlux Backlog

This backlog captures the next recommended work for PatchFlux based on the current product shape and the verified live operating state on April 27, 2026.

Each entry includes the problem, the expected value, and a suggested implementation direction. Priorities are rough and should be revisited as production evidence changes.

## P0 Betriebsstabilitaet

### P0: Repair public API routing

Problem:
The public domain path `https://patchflux.de/api/...` currently returns `404`, which breaks the expected hosting model and makes footer feed links unreliable.

Value:
Restores a consistent public surface and reduces confusion between website health and backend health.

Suggested implementation:
Audit Static Web Apps routing and linked-backend expectations, then either restore `/api/*` proxying on the public domain or intentionally standardize all public API references on the direct Function host until proxying exists.

### P0: Stabilize high-frequency ingest for `msrc` and `cisa-kev`

Problem:
`/api/health` marked `msrc` and `cisa-kev` as stale on April 27, 2026, with `LastFetchAt` still stuck on April 26, 2026.

Value:
Prevents security-sensitive feeds from silently lagging behind while lower-frequency sources continue to update.

Suggested implementation:
Inspect Azure timer execution, Function logs, and host configuration for `ingest_timer_high`, then add a clear signal that distinguishes timer-not-firing from source-not-modified behavior.

### P0: Resolve or disable Reddit sources cleanly

Problem:
`reddit-microsoft` and `reddit-sysadmin` currently fail with `HTTP 403` in the Azure runtime and are temporarily disabled in production.

Value:
Avoids permanent false alarms in source health and prevents noisy operational status for sources that are no longer practically ingestible.

Suggested implementation:
Decide whether to replace these sources with supported alternatives, adjust request strategy if allowed by the source, or explicitly disable them and remove them from default health expectations.

### P0: Normalize public outbound links and feed targets

Problem:
Some public links still depend on broken `/api/*` paths or use `rel` values that do not match the repository guardrails.

Value:
Brings the public UI back into compliance and avoids broken links in footer, feed access, and extension-adjacent surfaces.

Suggested implementation:
Review web footer, feed links, browser extension links, and any direct article links for working targets and consistent `target="_blank" rel="noopener nofollow"` handling where required.

## P1 Relevanz und UX

### P1: Revisit default topic filter behavior

Problem:
The default topic selection excludes `cve` and also hides items that receive no derived topic, which makes the feed look much smaller than the raw ingest actually is.

Value:
Aligns user perception with real ingest volume and reduces false alarms like "only one article arrived."

Suggested implementation:
Choose a safer default behavior, such as including CVEs by default, treating unclassified items as visible by default, or showing an explicit filter explanation on first load.

### P1: Improve `compute_topics()` coverage for common press/blog headlines

Problem:
Many relevant items from Heise, Borns IT, and BleepingComputer currently end up with no topic.

Value:
Improves filtering quality, topic counts, and overall discoverability without relaxing the legal model.

Suggested implementation:
Expand title-only topic patterns using real headline samples from current sources and add focused tests for the missed categories.

### P1: Explain active defaults when filters hide content

Problem:
Users can easily interpret filtered views as ingest failures because the UI does not clearly explain that defaults are narrowing the result set.

Value:
Reduces confusion and support overhead while keeping filtering power.

Suggested implementation:
Add a lightweight visible hint, empty-state explanation, or result-summary note when default topic filtering excludes recent content.

### P1: Improve `/api/health` semantics

Problem:
Current health reporting groups together different operational states such as `error`, `not_modified`, stale data, and timer inactivity.

Value:
Makes operator diagnosis faster and reduces guesswork during incidents.

Suggested implementation:
Refine the health model so it can distinguish source fetch failure, no new content, stale success, and scheduler-level issues.

## P1 Observability

### P1: Document an ingest diagnosis runbook

Problem:
Live investigation currently depends on tribal knowledge across source health, timers, routing, and frontend filtering.

Value:
Shortens incident triage and makes maintenance more contributor-friendly.

Suggested implementation:
Add a runbook that lists the minimum checks for `/api/health`, `/api/sources`, raw `/api/news`, timer status, and known routing pitfalls.

### P1: Track last successful fetch separately from last attempt

Problem:
`SourceHealth` currently centers on the last fetch attempt, which makes it harder to tell whether a stale source is repeatedly failing or simply not scheduled.

Value:
Improves health interpretation and supports better operational UI later.

Suggested implementation:
Extend `SourceHealth` with explicit success timestamps and, if needed, last-success status metadata while preserving backward compatibility.

### P1: Expand smoke checks beyond `/api/health`

Problem:
A health endpoint alone does not guarantee that feed export, filtered news queries, and hot-item surfaces work.

Value:
Catches user-visible failures earlier, especially routing and serialization regressions.

Suggested implementation:
Add availability or smoke checks for `/api/news`, `/api/hot`, and `/api/feed.xml`, ideally from the same environment users hit publicly.

## P2 Produktweiterentwicklung

### P2: Add an operator-facing source health view

Problem:
Source health is available via API but not yet surfaced in a purpose-built operator experience.

Value:
Makes failures, stale sources, and run volume visible without manual API inspection.

Suggested implementation:
Create an admin or operator screen that summarizes source status, last fetch, last success, and items written.

### P2: Improve product and topic aggregation quality

Problem:
Current product and topic derivation are useful but still shallow for some headlines and source types.

Value:
Strengthens filtering, summary views, and future digest-style features without storing prohibited content.

Suggested implementation:
Expand title-only classification rules and validate them with representative samples from existing sources.

### P2: Document the browser extension explicitly

Problem:
The browser extension exists in the repo but is not treated as a first-class documented surface.

Value:
Helps contributors understand why it points directly at the Function host and how it should evolve alongside the web app.

Suggested implementation:
Add a short extension section to the architecture and contributor docs, including current API dependency and compliance expectations for outbound links.

### P2: Expand contributor onboarding with local smoke checks

Problem:
Local setup instructions are present, but there is no concise checklist for validating the end-to-end stack after startup.

Value:
Makes onboarding smoother and reduces uncertainty for first-time contributors.

Suggested implementation:
Add a short checklist covering local Functions startup, a sample `/api/news` request, web rendering, and source-health inspection.
