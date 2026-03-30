# Production Deployment Guide

This guide reflects the current production auth model used by the app.

## Authentication Model

Flow:

1. The Expo app starts Microsoft sign-in with Expo Auth Session.
2. Azure AD returns an authorization code.
3. The frontend sends that code and PKCE verifier to `POST /auth/token`.
4. The backend exchanges the code with Azure AD using its confidential client secret.
5. The backend issues its own signed session JWT.
6. The frontend stores that session token in secure storage and uses it for API requests.
7. The backend validates the session token and separately acquires an app token for Microsoft Graph.

This keeps confidential credentials off the client.

## Required Environment Variables

### Frontend

Create local files from the templates:

```bash
cp .env.development.example .env.development
cp .env.production.example .env.production
```

Required values:

```bash
EXPO_PUBLIC_API_BASE_URL=https://api.example.com
EXPO_PUBLIC_AZURE_CLIENT_ID=your-client-id
EXPO_PUBLIC_AZURE_TENANT_ID=your-tenant-id
EXPO_PUBLIC_AZURE_AUTH_SCOPES=openid profile offline_access User.Read
EXPO_PUBLIC_ENVIRONMENT=production
```

### Backend

Create a local backend env file:

```bash
cp backend/.env.example backend/.env
```

Required values:

```bash
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
SHAREPOINT_SITE_ID=your-sharepoint-site-id
SHAREPOINT_DRIVE_ID=your-sharepoint-drive-id
SHAREPOINT_FILE_ID=your-sharepoint-file-id
SESSION_SECRET=replace-with-a-long-random-secret
SESSION_TTL_HOURS=8
AZURE_AUTH_SCOPES=openid profile offline_access User.Read
ENVIRONMENT=production
ALLOWED_ORIGINS=https://app.example.com
```

## Azure AD Setup

Configure the Azure app registration with:

- a redirect URI matching the Expo redirect scheme
- delegated permissions for the scopes in `AZURE_AUTH_SCOPES`
- a client secret stored only on the backend

Typical redirect URIs:

```text
appawanapointslogger://auth
https://your-web-domain.example/auth
```

## Backend Deployment

Recommended command:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Production requirements:

- run behind HTTPS
- inject secrets through the hosting platform
- do not bake `.env` files into container images
- set a strong `SESSION_SECRET`
- restrict `ALLOWED_ORIGINS`

## Frontend Deployment

Build with EAS after production env values are configured.

```bash
eas build --platform ios
eas build --platform android
```

For web, ensure the deployed origin matches the configured Azure redirect URI and backend CORS origin.

## Security Checklist

- keep Azure client secrets on the backend only
- rotate any credentials previously stored in the workspace
- use a random `SESSION_SECRET`
- store frontend session tokens only in secure storage
- re-authenticate when the session expires instead of trying to refresh with a frontend secret
- verify no local `.env` files are committed

## Validation Checklist

1. Sign in succeeds on the target platform.
2. `POST /auth/token` returns a backend session token.
3. Protected API calls succeed with that token.
4. API calls fail with `401` after logout.
5. CORS allows only intended production origins.
6. Backend starts only when `SESSION_SECRET` is set in production.
