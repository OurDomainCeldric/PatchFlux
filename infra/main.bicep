// PatchFlux — core Azure infrastructure.
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

@description('Optional email address for operational alerts (availability, stale ingest). Leave empty to skip alert wiring.')
param alertEmail string = ''

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
          value: 'PatchFlux/1.0 (+https://github.com/OurDomainCeldric/PatchFlux)'
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

// ---------------------------------------------------------------------------
// Availability & alerting
// ---------------------------------------------------------------------------
// Classic Application Insights availability ping against /api/health from
// three European test locations. Runs every 5 minutes. Alerts only fire if
// `alertEmail` is provided (action group + alert rules are conditional).

var healthUrl = 'https://${functionApp.properties.defaultHostName}/api/health'
var availabilityTestName = 'avail-${nameSuffix}-health'

resource availabilityTest 'Microsoft.Insights/webtests@2022-06-15' = {
  name: availabilityTestName
  location: location
  tags: {
    'hidden-link:${appInsights.id}': 'Resource'
  }
  kind: 'ping'
  properties: {
    Name: availabilityTestName
    SyntheticMonitorId: availabilityTestName
    Description: 'PatchFlux /api/health availability'
    Enabled: true
    Frequency: 300
    Timeout: 30
    Kind: 'ping'
    RetryEnabled: true
    Locations: [
      { Id: 'emea-nl-ams-azr' }
      { Id: 'emea-se-sto-edge' }
      { Id: 'emea-gb-db3-azr' }
    ]
    Configuration: {
      WebTest: '<WebTest Name="${availabilityTestName}" Enabled="True" CssProjectStructure="" CssIteration="" Timeout="30" WorkItemIds="" xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010" Description="" CredentialUserName="" CredentialPassword="" PreAuthenticate="True" Proxy="default" StopOnError="False" RecordedResultFile="" ResultsLocale=""><Items><Request Method="GET" Version="1.1" Url="${healthUrl}" ThinkTime="0" Timeout="30" ParseDependentRequests="False" FollowRedirects="True" RecordResult="True" Cache="False" ResponseTimeGoal="0" Encoding="utf-8" ExpectedHttpStatusCode="200" ExpectedResponseUrl="" ReportingName="" IgnoreHttpStatusCode="False" /></Items></WebTest>'
    }
  }
}

var actionGroupName = 'ag-${nameSuffix}'

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = if (!empty(alertEmail)) {
  name: actionGroupName
  location: 'global'
  properties: {
    groupShortName: 'newsbot'
    enabled: true
    emailReceivers: [
      {
        name: 'ops'
        emailAddress: alertEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

resource availabilityAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = if (!empty(alertEmail)) {
  name: 'alert-${availabilityTestName}'
  location: 'global'
  properties: {
    description: '/api/health failed availability probe'
    severity: 2
    enabled: true
    scopes: [
      availabilityTest.id
      appInsights.id
    ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.WebtestLocationAvailabilityCriteria'
      webTestId: availabilityTest.id
      componentId: appInsights.id
      failedLocationCount: 2
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// No successful ingest in the last 24 h → alert.
resource staleIngestAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = if (!empty(alertEmail)) {
  name: 'alert-${nameSuffix}-stale-ingest'
  location: location
  properties: {
    description: 'No successful ingest in the last 24 hours'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT1H'
    windowSize: 'PT24H'
    scopes: [ logs.id ]
    criteria: {
      allOf: [
        {
          query: 'AppTraces | where Message contains "\\"event\\": \\"ingest.source\\"" | where Message contains "\\"status\\": \\"ok\\""'
          timeAggregation: 'Count'
          operator: 'LessThan'
          threshold: 1
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [ actionGroup.id ]
    }
  }
}

output availabilityTestName string = availabilityTest.name
output healthUrl string = healthUrl
