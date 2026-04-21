# Legal & Compliance Design

This document defines **non-negotiable legal guardrails** enforced in the code and architecture. Any change that weakens these guardrails requires explicit review.

## 1. Data acquisition

- **Official APIs and standardized RSS/Atom feeds only.** No aggressive HTML scraping.
- **Conditional GETs** (`If-None-Match`, `If-Modified-Since`) to minimize load on publishers.
- **Throttling:** at most one request per source per scheduled run, exponential backoff on errors.
- **Transparent User-Agent** identifying the bot and linking to the repository, e.g. `OmlorsNewsBot/1.0 (+https://github.com/<owner>/OmlorsNewsBot)`.
- `robots.txt` is respected.

## 2. Storage — what MAY be stored per item

- Original headline (short factual statement)
- Publication date (UTC)
- Source name & stable source id
- Author (if provided by the feed)
- Canonical URL (required — used as backlink)
- Product/tag labels derived locally from keyword matching on the title
- Ingestion timestamp and a deduplication hash

## 3. Storage — what MUST NOT be stored

- Article bodies, full text, or any substantial excerpt
- Feed `description` / `summary` / `content` fields from third-party publishers
- Images or media from third parties (no hotlinking either)
- Any data that could substitute reading the original article

These prohibitions are enforced at the schema level (Pydantic field whitelist in `apps/functions/models/news_item.py`).

## 4. Optional fact extraction (Phase 2, gated)

If AI-based fact extraction is introduced later:

- Article text is fetched **temporarily in memory only** and is **discarded immediately after extraction**.
- Only **neutral, factual bullet points** (e.g. "Patch KB12345 fixes issue X") are persisted.
- **Original wording is never reproduced.**
- This phase requires **explicit written approval** before activation.

## 5. Trademarks & branding

- The UI and metadata make clear that this is an **independent third-party tool**.
- **No logos, wordmarks, or brand assets** of Microsoft, Heise, Borns IT-Blog, or any other publisher are used.
- Source names appear as **plain text** only.

## 6. Outbound links

- All links to original articles use `target="_blank"` and `rel="noopener nofollow"`.
- Every item is displayed with a clearly visible **source name and link**.

## 7. Transparency

- A permanent **disclaimer** in the footer states the independent nature of the tool.
- Imprint/privacy policy placeholders must be finalized before public release (EU requirement).

## 8. Enforcement

- Schema-level field whitelist (Pydantic).
- Code review checklist blocks any PR introducing fields like `body`, `content`, `summary`, `description`, `snippet`, `image_url` on third-party content.
- CI grep check (planned) fails the build if such fields appear in the storage layer.
