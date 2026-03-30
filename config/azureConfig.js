/**
 * Azure AD Configuration
 * Shared Azure auth configuration for frontend sign-in.
 */

import { appConfig, azureAuthority, azureDiscovery } from './appConfig';

export const msalConfig = {
  auth: {
    clientId: appConfig.azureClientId,
    authority: azureAuthority,
    redirectUri: `${appConfig.redirectScheme}://${appConfig.redirectPath}`,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
};

export const loginRequest = {
  scopes: appConfig.authScopes,
};

export const graphConfig = {
  graphMeEndpoint: 'https://graph.microsoft.com/v1.0/me',
  discovery: azureDiscovery,
};

export const apiConfig = {
  apiBaseUrl: appConfig.apiBaseUrl,
  authTokenEndpoint: `${appConfig.apiBaseUrl}/auth/token`,
};

// Production security settings
export const productionConfig = {
  enforceHttps: true,
  requireStrongTokens: true,
  tokenRefreshThresholdMinutes: 5,
  maxTokenAgeHours: 24,
};
