# Deployment Summary

This summary matches the current implementation in the repository.

## Completed Work

- frontend auth now uses Expo Auth Session with PKCE
- backend exchanges the Azure authorization code
- backend issues a signed session JWT for API access
- protected API routes now require that backend session token
- backend still uses its confidential Microsoft Graph token for SharePoint access
- frontend and backend environment templates were updated
- deployment and auth guides were updated to reflect the real flow

## Main Files

- `screens/LoginScreen.js`
- `services/authService.js`
- `services/apiClient.js`
- `config/appConfig.js`
- `backend/main.py`
- `backend/.env.example`
- `MD/PRODUCTION_DEPLOYMENT_GUIDE.md`
- `MD/MSAL_QUICK_REFERENCE.md`

## Required Production Inputs

Frontend:

- `EXPO_PUBLIC_API_BASE_URL`
- `EXPO_PUBLIC_AZURE_CLIENT_ID`
- `EXPO_PUBLIC_AZURE_TENANT_ID`
- `EXPO_PUBLIC_AZURE_AUTH_SCOPES`

Backend:

- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TENANT_ID`
- `SHAREPOINT_SITE_ID`
- `SHAREPOINT_DRIVE_ID`
- `SHAREPOINT_FILE_ID`
- `SESSION_SECRET`
- `SESSION_TTL_HOURS`
- `ALLOWED_ORIGINS`

## Operational Notes

- do not store Azure client secrets in frontend code
- do not commit local `.env` files
- if a backend session expires, the user signs in again
- production startup fails if `SESSION_SECRET` is missing
