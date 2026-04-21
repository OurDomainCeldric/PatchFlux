# PatchFlux

An **independent, third-party** aggregator for Microsoft product changes, new features, and IT news. This project is **not affiliated with, endorsed by, or connected to** Microsoft, Heise, Borns IT-Blog, or any other referenced publisher. All trademarks belong to their respective owners.

## What it does

- Pulls news **exclusively from official APIs and standardized RSS/Atom feeds** (no aggressive HTML scraping).
- Stores only **legally safe metadata**: headline, publication date, source name, author, canonical URL, product/tag labels.
- **No article bodies, snippets, or images** from third parties are stored or reproduced.
- Every item links back to the **original publisher** (`rel="noopener nofollow"`).

## Architecture (MVP)

```
RSS/Atom + M365 Roadmap API
        ▼  (1×/day, Conditional GET, clear User-Agent)
Azure Function "ingest" (Python, Timer-Trigger)
        ▼
Azure Table Storage  (metadata only)
        ▼
Azure Function "api" (HTTP-Trigger, JSON)
        ▼
Next.js Frontend on Azure Static Web Apps
```

- **Frontend:** Next.js 15 (App Router, Static Export) + TypeScript + Tailwind + shadcn/ui, i18n DE/EN via `next-intl`
- **Backend:** Azure Functions, Python 3.11 (v2 programming model)
- **Storage:** Azure Table Storage
- **Hosting:** Azure Static Web Apps (Free) + Azure Functions (Consumption)
- **Region:** `westeurope` — cheapest DSGVO-compliant EU region

## Monorepo layout

```
apps/
  web/        # Next.js frontend
  functions/  # Python Azure Functions (ingest + api)
infra/        # Bicep IaC
.github/workflows/  # CI/CD (GitHub Actions)
```

## Local development

Prerequisites: Node.js 20+, Python 3.11, Azure Functions Core Tools v4, Azurite (local Table Storage emulator).

```bash
# Frontend
cd apps/web
npm install
npm run dev

# Backend (Azure Functions)
cd apps/functions
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # (Windows PowerShell)
pip install -r requirements.txt
func start
```

## Deployment (Azure)

- **Subscription:** stored as the `AZURE_SUBSCRIPTION_ID` GitHub Actions secret; export `AZURE_SUBSCRIPTION_ID` locally for manual `az` runs.
- **Resource Group:** `RG-NewsBot`
- **Region:** `westeurope`

See [infra/README.md](infra/README.md) for Bicep deployment.

## Legal & Compliance

See [LEGAL.md](LEGAL.md) for the compliance design (EU copyright, ancillary copyright for press publishers, trademarks, ToS).

## License

[MIT](LICENSE)
