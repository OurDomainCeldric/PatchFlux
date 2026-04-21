using './main.bicep'

param location = 'westeurope'
param projectPrefix = 'omlorsnews'
param env = 'prod'
param alertEmail = 'romlor86@gmail.com'

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
