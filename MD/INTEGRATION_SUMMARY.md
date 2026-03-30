# Integration Summary

This file summarizes the current frontend and backend integration points.

## Frontend

- `App.js` controls screen flow and authenticated app state.
- `screens/LoginScreen.js` starts Microsoft sign-in with Expo Auth Session.
- `services/authService.js` exchanges the Azure auth code for a backend session token and stores it securely.
- `services/apiClient.js` attaches that session token to API requests.
- `config/appConfig.js` centralizes frontend environment values.

## Backend

- `backend/main.py` exchanges Azure authorization codes at `POST /auth/token`.
- The backend signs its own session JWT for the app.
- Protected routes validate that session JWT before handling requests.
- SharePoint access still uses the backend confidential client and Microsoft Graph.

## Main API Endpoints

- `GET /health`
- `POST /auth/token`
- `GET /sheets/classes`
- `GET /sheets/Students`
- `GET /sheets/PointsLog`
- `GET /sheets/PointsLogSheet`
- `PATCH /sheets/PointsLogSheet/update`
- `POST /sheets/PointsLogSheet/bootstrap`
- `POST /sheets/PointsLog/auto-populate`
- `GET /sheets/student-summary`

## Environment Inputs

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

## Security Model

- frontend never stores Azure client secrets
- frontend uses secure storage for the backend session token
- backend rejects missing or expired session tokens
- backend must have a strong `SESSION_SECRET` in production

## Deployment Notes

- use the example env files as templates only
- keep local `.env` files untracked
- configure Azure redirect URIs to match the Expo redirect scheme used by the app
- review `MD/PRODUCTION_DEPLOYMENT_GUIDE.md` for deployment steps
