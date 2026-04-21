using './main.bicep'

param location = 'westeurope'
param projectPrefix = 'omlorsnews'
param env = 'prod'
param alertEmail = 'romlor86@gmail.com'

// Function App CORS allow-list. Keep this tight: the public custom domain(s),
// the SWA default hostname (fallback), and localhost for dev builds. The
// default in main.bicep intentionally omits the SWA hostname because it is
// environment-specific.
param functionAppAllowedOrigins = [
  'https://patchflux.de'
  'https://www.patchflux.de'
  'https://witty-ocean-00e235903.7.azurestaticapps.net'
  'http://localhost:3000'
]

// --- AI relevance gate ------------------------------------------------------
// Set to true to provision an Azure OpenAI account + gpt-4o-mini deployment.
// Spend is capped in code by BudgetTracker (default $5/month). Azure OpenAI
// access must be allow-listed on the subscription — see infra/README.md.
param deployAiGate = true
param aiMaxMonthlyUsd = 5
param aiLocation = 'westeurope'

// Optional: set these to link the Static Web App to a GitHub repo for auto-deploy.
// param repositoryUrl = 'https://github.com/<owner>/PatchFlux'
// param repositoryBranch = 'main'
