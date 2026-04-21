// OmlorsNewsBot — core Azure infrastructure.
//
// Deploys:
//   * Storage Account (Standard_LRS)  — Table Storage for NewsItems & SourceHealth
//   * Log Analytics Workspace         — backs Application Insights
//   * Application Insights (workspace-based)
//   * Consumption Flex Plan (Linux)   — hosts the Python Functions app
//   * Function App (Python 3.11, v2)  — ingest + api
//   * Static Web App (Free)           — hosts the Next.js frontend
//
// Target scope : resourceGroup
// Target RG    : RG-NewsBot   (subscription 4d267595-24a9-46d3-aa30-580f3de0af1f)

targetScope = 'resourceGroup'

@description('Azure region for all resources. Keep aligned with RG location.')
param location string = resourceGroup().location

@description('Short project prefix used in resource names. Lowercase, 3-11 chars.')
@minLength(3)
@maxLength(11)
param projectPrefix string = 'omlorsnews'

@description('Environment discriminator (e.g. prod, dev).')
param env string = 'prod'

@description('GitHub repo URL for the Static Web App (leave empty to configure CI/CD manually).')
param repositoryUrl string = ''

@description('GitHub branch for the Static Web App.')
param repositoryBranch string = 'main'

var nameSuffix = toLower('${projectPrefix}-${env}')
// Storage accounts: 3-24 chars, lowercase, alphanumeric only
var storageAccountName = toLower(replace('${projectPrefix}${env}st', '-', ''))
var functionAppName = 'func-${nameSuffix}'
var hostingPlanName = 'plan-${nameSuffix}'
var appInsightsName = 'appi-${nameSuffix}'
var logAnalyticsName = 'log-${nameSuffix}'
var staticSiteName = 'swa-${nameSuffix}'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
  }
}

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
  }
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: hostingPlanName
  location: location
  kind: 'linux'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      http20Enabled: true
      cors: {
        allowedOrigins: [ '*' ]
        supportCredentials: false
      }
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storage.listKeys().keys[0].value}'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'AzureWebJobsFeatureFlags'
          value: 'EnableWorkerIndexing'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'NEWS_TABLE_CONNECTION'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storage.listKeys().keys[0].value}'
        }
        {
          name: 'NEWS_TABLE_NAME'
          value: 'NewsItems'
        }
        {
          name: 'SOURCE_HEALTH_TABLE_NAME'
          value: 'SourceHealth'
        }
        {
          name: 'USER_AGENT'
          value: 'OmlorsNewsBot/1.0 (+https://github.com/OmlorsNewsBot/OmlorsNewsBot)'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
      ]
    }
  }
}

resource staticSite 'Microsoft.Web/staticSites@2023-12-01' = {
  name: staticSiteName
  // Static Web Apps Free tier has limited regions; westeurope is supported.
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    repositoryUrl: empty(repositoryUrl) ? null : repositoryUrl
    branch: empty(repositoryUrl) ? null : repositoryBranch
    buildProperties: {
      appLocation: 'apps/web'
      outputLocation: 'out'
    }
  }
}

// NOTE: Static Web Apps "linked backends" (transparent /api/* proxy) require
// the Standard tier. To stay on the Free tier, the frontend talks to the
// Function App directly. CORS on the Function App is open ('*') because all
// endpoints are anonymous and read-only. Set the Next.js build-time env var
//   NEXT_PUBLIC_API_BASE_URL = https://<functionApp>.azurewebsites.net/api
// so the static export bakes the correct absolute URL.

output storageAccountName string = storage.name
output functionAppName string = functionApp.name
output functionAppHostName string = functionApp.properties.defaultHostName
output functionAppApiBaseUrl string = 'https://${functionApp.properties.defaultHostName}/api'
output staticSiteName string = staticSite.name
output staticSiteDefaultHostname string = staticSite.properties.defaultHostname
output appInsightsConnectionString string = appInsights.properties.ConnectionString
