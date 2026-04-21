# Infrastructure — Azure (Bicep)

All Azure resources live in a single resource group and are defined in [main.bicep](main.bicep).

## Targets

- **Subscription:** `4d267595-24a9-46d3-aa30-580f3de0af1f`
- **Resource group:** `RG-NewsBot`
- **Region:** `westeurope`

## Resources deployed

| Resource | SKU / Tier | Purpose |
|---|---|---|
| Storage Account (`Standard_LRS`) | cheapest redundancy | Table Storage for `NewsItems` + `SourceHealth`, function host storage |
| Log Analytics Workspace | `PerGB2018`, 30-day retention | Backs Application Insights |
| Application Insights | workspace-based | Logs / failures / traces |
| App Service Plan | `Y1` (Consumption) | Hosts the Functions app |
| Function App (Linux, Python 3.11) | Consumption | `ingest` timer + `api` HTTP triggers |
| Static Web App | `Free` | Hosts the Next.js frontend and proxies `/api/*` to the Function App |
| Azure OpenAI account + `gpt-4o-mini` deployment (optional, `deployAiGate`) | `S0` / `GlobalStandard` | Relevance gate that classifies titles pre-ingest; spend is capped in code at `$aiMaxMonthlyUsd`/month (default **$5**). |

Expected cost on MVP load: **under 1 EUR/month** infra + **up to `aiMaxMonthlyUsd` USD/month** for AI (hard-capped by `BudgetTracker`).

## AI relevance gate — prerequisites

Azure OpenAI is an allow-listed service. Before enabling `deployAiGate = true`:

1. Check the subscription has Azure OpenAI access: `az cognitiveservices account list-kinds` — the output must include `OpenAI`. If not, request access at <https://aka.ms/oai/access>.
2. Confirm `gpt-4o-mini` is available in `aiLocation`: `az cognitiveservices model list --location westeurope --query "[?model.name=='gpt-4o-mini']" -o table`.

If either check fails, leave `deployAiGate = false` and ingestion continues with the keyword-only filter.


## First deployment

Run from the repo root in PowerShell:

```powershell
az login
az account set --subscription 4d267595-24a9-46d3-aa30-580f3de0af1f
az group create --name RG-NewsBot --location westeurope
az deployment group create `
  --resource-group RG-NewsBot `
  --template-file infra/main.bicep `
  --parameters infra/main.bicepparam
```

After deployment, capture the outputs — you'll need:

- `functionAppName` — for `az functionapp deployment` or the GitHub Action
- `staticSiteDefaultHostname` — your public URL
- Static Web App deployment token (see below)

## GitHub Actions setup

Create the following repo secrets:

| Secret | How to obtain |
|---|---|
| `AZURE_CREDENTIALS` | `az ad sp create-for-rbac --name "omlorsnews-ci" --role contributor --scopes /subscriptions/4d267595-24a9-46d3-aa30-580f3de0af1f/resourceGroups/RG-NewsBot --sdk-auth` |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | `az staticwebapp secrets list --name <staticSiteName> --query "properties.apiKey" -o tsv` |
| `AZURE_FUNCTIONAPP_NAME` | Output `functionAppName` from the deployment |
| `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` | `az functionapp deployment list-publishing-profiles --resource-group RG-NewsBot --name <functionAppName> --xml` |

## Manual ingest trigger (smoke test)

```powershell
$funcName = "<functionAppName>"
$key = az functionapp keys list --resource-group RG-NewsBot --name $funcName --query "functionKeys.default" -o tsv
Invoke-RestMethod -Method Post -Uri "https://$funcName.azurewebsites.net/api/admin/ingest?code=$key"
```
