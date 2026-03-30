import Constants from 'expo-constants';

const expoConfig = Constants.expoConfig ?? {};
const extra = expoConfig.extra ?? {};

const authScopes = (
  process.env.EXPO_PUBLIC_AZURE_AUTH_SCOPES ||
  extra.azureAuthScopes ||
  'openid profile offline_access User.Read'
)
  .split(/[\s,]+/)
  .map((scope) => scope.trim())
  .filter(Boolean);

export const appConfig = {
  apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || extra.apiBaseUrl || 'http://localhost:8000',
  azureClientId: process.env.EXPO_PUBLIC_AZURE_CLIENT_ID || extra.azureClientId || '',
  azureTenantId: process.env.EXPO_PUBLIC_AZURE_TENANT_ID || extra.azureTenantId || '',
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
