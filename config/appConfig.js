import Constants from 'expo-constants';

const expoConfig = Constants.expoConfig ?? {};
const extra = expoConfig.extra ?? {};

// Non-secret production fallbacks to protect web builds if EXPO_PUBLIC_* values
// are missing or if a stale cached bundle omits compile-time env injection.
const DEFAULT_API_BASE_URL = 'https://awanapointslogger.onrender.com';
const DEFAULT_AZURE_CLIENT_ID = '6c117750-8af8-4e5f-a016-136c2430b940';
const DEFAULT_AZURE_TENANT_ID = 'afdc3b01-cd69-4af3-a783-9f13cce85492';

const authScopes = (
  process.env.EXPO_PUBLIC_AZURE_AUTH_SCOPES ||
  extra.azureAuthScopes ||
  'openid profile offline_access User.Read Sites.Read.All Files.Read.All'
)
  .split(/[\s,]+/)
  .map((scope) => scope.trim())
  .filter(Boolean);

export const appConfig = {
  apiBaseUrl:
    process.env.EXPO_PUBLIC_API_BASE_URL ||
    extra.apiBaseUrl ||
    DEFAULT_API_BASE_URL,
  azureClientId:
    process.env.EXPO_PUBLIC_AZURE_CLIENT_ID ||
    extra.azureClientId ||
    DEFAULT_AZURE_CLIENT_ID,
  azureTenantId:
    process.env.EXPO_PUBLIC_AZURE_TENANT_ID ||
    extra.azureTenantId ||
    DEFAULT_AZURE_TENANT_ID,
  environment: process.env.EXPO_PUBLIC_ENVIRONMENT || 'development',
  redirectScheme: expoConfig.scheme || 'appawanapointslogger',
  redirectPath: 'auth',
  authScopes,
};

export const azureAuthority = appConfig.azureTenantId
  ? `https://login.microsoftonline.com/${appConfig.azureTenantId}`
  : 'https://login.microsoftonline.com/common';

export const azureDiscovery = {
  authorizationEndpoint: `${azureAuthority}/oauth2/v2.0/authorize`,
  tokenEndpoint: `${azureAuthority}/oauth2/v2.0/token`,
};

export function hasRequiredAuthConfig() {
  return Boolean(appConfig.azureClientId && appConfig.azureTenantId && appConfig.apiBaseUrl);
}
