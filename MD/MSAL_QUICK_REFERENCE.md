# Auth Quick Reference

## Current Stack

Frontend:

- Expo Auth Session
- Expo Secure Store
- React Native / Expo

Backend:

- FastAPI
- MSAL Python
- PyJWT session signing

## Runtime Flow

```text
Frontend -> Azure authorize -> auth code -> backend exchange -> session JWT -> protected API calls
```

## Key Files

- `config/appConfig.js`
- `screens/LoginScreen.js`
- `services/authService.js`
- `services/apiClient.js`
- `backend/main.py`
- `backend/.env.example`

## Frontend Usage

### Check current session

```javascript
const isAuthenticated = await authService.isAuthenticated();
```

### Get the backend session token

```javascript
const token = await authService.getAccessToken();
```

### Log out

```javascript
await authService.logout();
```

## Backend Auth Contract

### Request

`POST /auth/token`

```json
{
  "code": "azure-auth-code",
  "redirect_uri": "appawanapointslogger://auth",
  "code_verifier": "pkce-code-verifier"
}
```

### Response

```json
{
  "access_token": "backend-session-jwt",
  "token_type": "Bearer",
  "expires_in": 28800,
  "user": {
    "oid": "user-object-id",
    "display_name": "User Name",
    "email": "user@example.com",
    "tenant_id": "tenant-id"
  }
}
```

## Important Rules

- do not put client secrets in frontend code
- do not use `EXPO_PUBLIC_*` for confidential values
- backend routes require the backend-issued session JWT
- SharePoint access still happens with the backend confidential client
- when the session expires, sign in again

## Required Env Values

Frontend:

```bash
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000
EXPO_PUBLIC_AZURE_CLIENT_ID=your-client-id
EXPO_PUBLIC_AZURE_TENANT_ID=your-tenant-id
EXPO_PUBLIC_AZURE_AUTH_SCOPES=openid profile offline_access User.Read
```

Backend:

```bash
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
SESSION_SECRET=replace-with-a-long-random-secret
SESSION_TTL_HOURS=8
```

## Failure Modes

- `401 Authentication required`: no backend session token was sent
- `401 Invalid or expired session token`: session expired or was tampered with
- `400 Authentication failed`: Azure code exchange failed
- `500 Server error`: backend SharePoint or Graph operation failed
