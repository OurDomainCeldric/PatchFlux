using './main.bicep'

param location = 'westeurope'
param projectPrefix = 'omlorsnews'
param env = 'prod'
param alertEmail = 'romlor86@gmail.com'
// Optional: set these to link the Static Web App to a GitHub repo for auto-deploy.
// param repositoryUrl = 'https://github.com/<owner>/PatchFlux'
// param repositoryBranch = 'main'
