# Awana Points Logger - Complete Deployment Guide

**Version:** 1.0.0  
**Last Updated:** March 31, 2026  
**Maintained By:** DBDNJ Development Team  

---

## Table of Contents

1. [Quick Reference - Service URLs & Credentials](#quick-reference)
2. [Technology Stack](#technology-stack)
3. [Architecture Overview](#architecture-overview)
4. [Data Flow Diagram](#data-flow-diagram)
5. [Deployment Process](#deployment-process)
6. [Manual Deployment Steps](#manual-deployment-steps)
7. [Environment Variables & Secrets](#environment-variables--secrets)
8. [Secrets Management Scripts](#secrets-management-scripts)
9. [Troubleshooting](#troubleshooting)
10. [Team Developer Guide](#team-developer-guide)

---

## Quick Reference

### Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend (Web)** | `https://awanapointslogger.pages.dev` | React Native web app hosted on Cloudflare Pages |
| **Frontend (iOS)** | Expo Go or Published App | Native iOS app |
| **Backend API** | `https://awanapointslogger.onrender.com` | FastAPI server for data sync |
| **GitHub Repository** | `https://github.com/dequimpo/AwanaPointsLogger` | Source code management |
| **Cloudflare Dashboard** | `https://dash.cloudflare.com` | Pages & Worker deployment management |
| **Render Dashboard** | `https://dashboard.render.com` | Backend service management |
| **Entra ID (Azure AD)** | `https://portal.azure.com` | OAuth configuration & app registration |
| **SharePoint Online** | `https://account.sharepoint.com` | Data storage (XLSX file in Teams channel) |

### Required Secrets & Credentials

#### GitHub Repository Secrets (`prod` environment)

```
CLOUDFLARE_ACCOUNT_ID          → 4b07dbb385ac65cb9265321cc1e8d4fc
CLOUDFLARE_API_TOKEN           → [See Secrets Management Scripts]
RENDER_DEPLOY_HOOK_URL         → [See Secrets Management Scripts]
```

#### GitHub Repository Variables (`prod` environment)

```
CLOUDFLARE_PAGES_PROJECT_NAME  → awanapointslogger
EXPO_PUBLIC_API_BASE_URL       → https://awanapointslogger.onrender.com
EXPO_PUBLIC_AZURE_CLIENT_ID    → 6c117750-8af8-4e5f-a016-136c2430b940
EXPO_PUBLIC_AZURE_TENANT_ID    → afdc3b01-cd69-4af3-a783-9f13cce85492
EXPO_PUBLIC_AZURE_AUTH_SCOPES  → openid profile offline_access User.Read
EXPO_PUBLIC_WEB_REDIRECT_URI   → https://awanapointslogger.pages.dev/auth
```

#### Render Backend Environment Variables

```
AZURE_CLIENT_ID                → 6c117750-8af8-4e5f-a016-136c2430b940
AZURE_CLIENT_SECRET            → [See Secrets Management Scripts]
AZURE_TENANT_ID                → afdc3b01-cd69-4af3-a783-9f13cce85492
SHAREPOINT_SITE_ID             → [Site ID from SharePoint]
SHAREPOINT_DRIVE_ID            → [Drive ID from SharePoint]
SHAREPOINT_FILE_ID             → [File ID of XLSX in SharePoint]
SESSION_SECRET                 → [Random 32+ character secret]
ALLOWED_ORIGINS                → https://awanapointslogger.pages.dev
ENVIRONMENT                    → production
```

#### Entra ID App Registration

```
Client ID (App ID):            6c117750-8af8-4e5f-a016-136c2430b940
Tenant ID:                     afdc3b01-cd69-4af3-a783-9f13cce85492
Redirect URIs (SPA):           
  - https://awanapointslogger.pages.dev/auth
  - https://awanapointslogger.onrender.com/auth
  - exp://localhost:19000/+sitescope=https://login.microsoftonline.com/afdc3b01-cd69-4af3-a783-9f13cce85492/oauth2/v2.0/authorize
```

---

## Technology Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18.2.0 | Core UI framework |
| **React Native** | 0.72.10 | Native mobile platform |
| **Expo** | 49.0.0 | Managed React Native hosting (iOS builds, EAS) |
| **React Native Web** | 0.19.6 | Web platform support for Expo |
| **React DOM** | 18.2.0 | DOM rendering for web |
| **Expo Auth Session** | 5.0.2 | OAuth 2.0 with PKCE flow |
| **Expo Web Browser** | 12.3.2 | OAuth callback handling |
| **Expo Secure Store** | 12.3.1 | Secure token storage (native & web) |
| **Expo Vector Icons** | 13.0.0 | Icon system (custom SVG adapter) |
| **Date Time Picker** | 7.2.0 | Date/time selection UI |
| **Node.js** | ≥16.0.0 | Runtime environment |
| **npm** | Latest | Package manager |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.104.1 | REST API framework |
| **Uvicorn** | 0.24.0 | ASGI server |
| **httpx** | 0.25.2 | Async HTTP client for Microsoft Graph |
| **MSAL** | 1.25.0 | Microsoft Authentication Library |
| **PyJWT** | 2.10.1 | JWT token generation/validation |
| **Pydantic** | 2.5.0 | Data validation models |
| **Python** | 3.9+ | Backend runtime |
| **python-dotenv** | 1.0.0 | Environment variable management |

### Infrastructure & DevOps

| Service | Version/Plan | Purpose |
|---------|--------------|---------|
| **Cloudflare Pages** | Pro | Static frontend hosting |
| **Render.com** | Starter/Standard | Backend container hosting |
| **GitHub Actions** | Standard | CI/CD automation |
| **Microsoft Entra ID** | Free tier | OAuth provider |
| **SharePoint Online** | Microsoft 365 | Data persistence (XLSX) |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   DEPLOYMENT ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────┘

                          USERS
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   [BROWSER]          [iOS Safari]        [Expo Go/App]
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    INTERNET / HTTPS
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
  ┌─────▼──────────┐               ┌──────────▼─────────┐
  │ CLOUDFLARE     │               │  MICROSOFT ENTRA   │
  │ PAGES          │               │  ID (OAuth)        │
  │ ─────────────  │               │ ──────────────     │
  │ React Native   │─ Token Flow ──│ - Verify identity  │
  │ web (dist)     │               │ - Issue JWT        │
  │ awanapointslogger              │ - UserProfile      │
  │ .pages.dev     │               └────────────────────┘
  └─────┬──────────┘
        │
        │ (API calls + JWT token)
        │
  ┌─────▼──────────────────────┐
  │  RENDER BACKEND            │
  │  ──────────────────────    │
  │  https://awanapointslogger │
  │  .onrender.com             │
  │                            │
  │  ┌──────────────────────┐  │
  │  │ FastAPI App          │  │
  │  │ ─────────────────    │  │
  │  │ • Auth routes        │  │
  │  │ • Toggle endpoints   │  │
  │  │ • Data sync routes   │  │
  │  │ • Health check       │  │
  │  └────────────┬─────────┘  │
  │               │            │
  │  ┌────────────▼─────────┐  │
  │  │ Microsoft Graph API  │  │
  │  │ (SharePoint Adapter) │  │
  │  └────────────┬─────────┘  │
  └───────────────┼────────────┘
                  │
      ┌───────────▼───────────┐
      │   MICROSOFT 365       │
      │ ─────────────────     │
      │ SharePoint Online     │
      │ (XLSX in Teams)       │
      └───────────────────────┘
```

---

## Data Flow Diagram

### 1. Authentication Flow (OAuth 2.0 with PKCE)

```
┌──────────────────────────────────────────────────────────────┐
│                    OAUTH 2.0 PKCE FLOW                        │
└──────────────────────────────────────────────────────────────┘

[CLIENT]                      [AUTH SERVER]                [RESOURCE]
(App)                         (Entra ID)                   (Backend)
  │                                                            │
  ├─── (1) Generate PKCE ───────────────────────────────────►  │
  │      code_verifier                                          │
  │      code_challenge                                         │
  │                                                            │
  ├─── (2) Redirect to /authorize ────────────────────────►   │
  │      ?client_id=XXX                                        │
  │      ?scope=User.Read                                      │
  │      ?code_challenge=XXX                                   │
  │                                                            │
  │                     (USER SIGNS IN AT ENTRA ID)           │
  │                                                            │
  │◄─── (3) Redirect to /auth endpoint ────────────────────   │
  │      ?code=AUTH_CODE                                       │
  │      ?session_state=XXX                                    │
  │                                                            │
  ├─── (4) Exchange auth code for token ──────────────────►   │
  │      POST /token                                           │
  │      code=AUTH_CODE                                        │
  │      code_verifier=XXX                                     │
  │                                                            │
  │◄─── (5) Return access_token + refresh_token ────────────  │
  │      { access_token: "xxx", refresh_token: "yyy" }        │
  │                                                            │
  ├─── (6) Store tokens in SecureStore ─────────────────────► │
  │      (Native: SecureStore / Web: sessionStorage)           │
  │                                                            │
  └──────────────────────────────────────────────────────────┘
```

### 2. Data Sync Flow (Points Logging)

```
┌──────────────────────────────────────────────────────────────┐
│                     POINTS LOGGING FLOW                       │
└──────────────────────────────────────────────────────────────┘

[MOBILE/WEB]                 [RENDER BACKEND]            [SHAREPOINT]
(User Action)                (FastAPI)                   (XLSX)
  │                                 │                       │
  ├─ (1) User toggles ────────────► │                       │
  │    checkbox               POST /toggle                      │
  │    { action, date, class, student }                     │
  │                                 │                       │
  │                     ┌──────────┴───────────┐            │
  │                     │ Validate JWT token   │            │
  │                     │ Check permissions    │            │
  │                     │ Get SharePoint URL   │            │
  │                     └──────────┬───────────┘            │
  │                                 │                       │
  │                     ┌──────────┴───────────┐            │
  │                     │ Fetch Excel from     │            │
  │                     │ SharePoint Drive     │            │
  │                     └──────────┬───────────┘            │
  │                                 ├──────────────────────► 
  │                                 │GET /drive/items/ ...  
  │                                 │/workbook/tables       
  │                                 │                   ◄───●
  │                                 │(Return XLSX data)    │
  │                     ┌──────────┴───────────┐            │
  │                     │ Update row:           │            │
  │                     │ - Find student row    │            │
  │                     │ - Toggle column       │            │
  │                     │ - Calculate totals    │            │
  │                     │ - Reindex rankings    │            │
  │                     └──────────┬───────────┘            │
  │                                 │                       │
  │                                 ├──────────────────────►
  │                                 │PATCH /workbook/tables
  │                                 │/rows                  
  │                                 │{ new cell values }    
  │                                 │                   ◄───●
  │                                 │                 (Saved)
  │                                 │                       │
  │◄─────── (2) Return 200 OK ─────┤                       │
  │    { updatedRow, allData }      │                       │
  │                                 │                       │
  ├─ (3) Update local UI ─────────► │                       │
  │    Show checkmark              (UI updates immediately)  
  │    Show blue dot (syncing)      │                       │
  │                                 │                       │
  └──────────────────────────────────────────────────────────┘

  ║ Polling every 30-60 seconds for data refresh             ║
  ║ WebSocket could be added for real-time sync              ║
```

### 3. Deployment Workflow (CI/CD)

```
┌──────────────────────────────────────────────────────────────┐
│                    CI/CD DEPLOYMENT                           │
└──────────────────────────────────────────────────────────────┘

[DEVELOPER]
    │
    ├─ (1) git commit && git push origin main
    │       └──►  [GITHUB REPOSITORY]
    │
    ├─ (2) Workflow triggers automatically
    │       └──►  [GITHUB ACTIONS]
    │           ├─ For backend/ changes:
    │           │  deploy-backend-render.yml
    │           │  → Triggers Render deploy hook
    │           │
    │           └─ For frontend/ changes:
    │              deploy-frontend-cloudflare.yml
    │              → npm ci
    │              → npx expo export --platform web
    │              → wrangler pages deploy
    │
    ├─ (3) Frontend Build
    │       ├─ Load secrets & variables from GitHub
    │       ├─ Inject EXPO_PUBLIC_* env vars
    │       ├─ Build React Web artifacts to dist/
    │       └─ Deploy to Cloudflare Pages
    │           └──► https://awanapointslogger.pages.dev
    │
    ├─ (4) Backend Deploy (Manual Hook)
    │       ├─ Render receives webhook
    │       ├─ Pulls latest code from GitHub
    │       ├─ Rebuilds Docker image
    │       ├─ Deploys new container
    │       └──► https://awanapointslogger.onrender.com
    │
    ├─ (5) Health Checks
    │       ├─ GET /health
    │       └─ Verify services are responding
    │
    └─ (6) Done!
```

---

## Deployment Process

### Automatic Deployment (GitHub Actions)

The app uses **GitHub Actions** for continuous deployment on every push to `main` branch.

#### Frontend Deployment Trigger

**File:** `.github/workflows/deploy-frontend-cloudflare.yml`

Triggers when **any** of these change:
- `App.js` - Main app component
- `app.json` - Expo configuration
- `index.js` - Entry point
- `package.json` / `package-lock.json` - Dependencies
- `.env.production.example` - Example env vars
- `config/` - App configuration
- `screens/` - Screen components
- `services/` - API services
- `.github/workflows/deploy-frontend-cloudflare.yml` - Workflow itself

**Steps:**
1. Checkout code from main branch
2. Setup Node.js 20
3. Install dependencies with `npm ci`
4. Load EXPO_PUBLIC_* variables from GitHub `prod` environment
5. Build web artifacts: `npx expo export --platform web`
6. Deploy to Cloudflare Pages using Wrangler CLI
7. Live at `https://awanapointslogger.pages.dev`

#### Backend Deployment Trigger

**File:** `.github/workflows/deploy-backend-render.yml`

Triggers when **any** of these change:
- `backend/` directory
- `backend/Dockerfile`
- `.dockerignore`
- `.github/workflows/deploy-backend-render.yml` - Workflow itself

**Steps:**
1. Checkout code
2. Call Render deploy webhook via `RENDER_DEPLOY_HOOK_URL` secret
3. Render automatically:
   - Pulls latest code
   - Rebuilds Docker image
   - Redeploys to production
   - Runs health checks
4. Live at `https://awanapointslogger.onrender.com`

---

## Manual Deployment Steps

### Frontend - Deploy to Cloudflare Pages

#### Option 1: GitHub Actions (Recommended)

```bash
# Push to main branch (auto-triggers workflow)
git add .
git commit -m "chore: update frontend"
git push origin main

# Monitor deployment
gh run list --workflow="deploy-frontend-cloudflare.yml" --limit=1
gh run view <RUN_ID> --log
```

#### Option 2: Manual CLI Deploy

```bash
# Build web assets
npx expo export --platform web

# Deploy to Cloudflare Pages
npx wrangler pages deploy dist \
  --project-name=awanapointslogger \
  --account-id=4b07dbb385ac65cb9265321cc1e8d4fc

# Verify deployment
curl https://awanapointslogger.pages.dev/health
```

#### Environment Variables Required for Build

```bash
export EXPO_PUBLIC_API_BASE_URL=https://awanapointslogger.onrender.com
export EXPO_PUBLIC_AZURE_CLIENT_ID=6c117750-8af8-4e5f-a016-136c2430b940
export EXPO_PUBLIC_AZURE_TENANT_ID=afdc3b01-cd69-4af3-a783-9f13cce85492
export EXPO_PUBLIC_AZURE_AUTH_SCOPES="openid profile offline_access User.Read"
export EXPO_PUBLIC_WEB_REDIRECT_URI=https://awanapointslogger.pages.dev/auth
export EXPO_PUBLIC_ENVIRONMENT=production
```

### Backend - Deploy to Render

#### Option 1: GitHub Actions (Recommended)

```bash
# Push to main branch (auto-triggers workflow)
cd backend
git add .
git commit -m "fix: update API endpoints"
git push origin main

# Render webhook is automatically called
# Check Render dashboard for deployment status
```

#### Option 2: Manual Render Deploy Hook

```bash
# Trigger Render webhook (starts build & deploy)
curl -X POST "https://api.render.com/deploy/srv-<service_id>?key=<deploy_key>"

# Or use stored secret
curl -X POST "$RENDER_DEPLOY_HOOK_URL"
```

#### Render Environment Variables

Set these in **Render Dashboard** > **awanapointslogger** > **Environment**:

```
AZURE_CLIENT_ID=6c117750-8af8-4e5f-a016-136c2430b940
AZURE_CLIENT_SECRET=<See secrets script below>
AZURE_TENANT_ID=afdc3b01-cd69-4af3-a783-9f13cce85492
SHAREPOINT_SITE_ID=<From SharePoint>
SHAREPOINT_DRIVE_ID=<From SharePoint>
SHAREPOINT_FILE_ID=<From SharePoint>
SESSION_SECRET=<Random 32+ char string>
ALLOWED_ORIGINS=https://awanapointslogger.pages.dev
ENVIRONMENT=production
```

---

## Environment Variables & Secrets

### Frontend Build Variables

Injected during `npx expo export`:

| Variable | Source | Example |
|----------|--------|---------|
| `EXPO_PUBLIC_API_BASE_URL` | GitHub Variable (prod) | `https://awanapointslogger.onrender.com` |
| `EXPO_PUBLIC_AZURE_CLIENT_ID` | GitHub Variable (prod) | `6c117750-8af8-4e5f-a016-136c2430b940` |
| `EXPO_PUBLIC_AZURE_TENANT_ID` | GitHub Variable (prod) | `afdc3b01-cd69-4af3-a783-9f13cce85492` |
| `EXPO_PUBLIC_AZURE_AUTH_SCOPES` | GitHub Variable (prod) | `openid profile offline_access User.Read` |
| `EXPO_PUBLIC_WEB_REDIRECT_URI` | GitHub Variable (prod) | `https://awanapointslogger.pages.dev/auth` |
| `EXPO_PUBLIC_ENVIRONMENT` | Hardcoded in workflow | `production` |

### Backend Runtime Variables

Set in **Render Dashboard > Environment**:

| Variable | Type | Example |
|----------|------|---------|
| `AZURE_CLIENT_ID` | String | `6c117750-8af8-4e5f-a016-136c2430b940` |
| `AZURE_CLIENT_SECRET` | Secret | `[See Secrets Script]` |
| `AZURE_TENANT_ID` | String | `afdc3b01-cd69-4af3-a783-9f13cce85492` |
| `SHAREPOINT_SITE_ID` | String | `yourdomain.sharepoint.com:/sites/teamname` |
| `SHAREPOINT_DRIVE_ID` | String | `b!randomID` |
| `SHAREPOINT_FILE_ID` | String | `randomID` |
| `SESSION_SECRET` | Secret | `$(openssl rand -base64 32)` |
| `ALLOWED_ORIGINS` | String | `https://awanapointslogger.pages.dev` |
| `ENVIRONMENT` | String | `production` |

### GitHub Secrets (prod environment)

| Secret | Purpose | Location |
|--------|---------|----------|
| `CLOUDFLARE_ACCOUNT_ID` | Wrangler authentication | [Secrets Script] |
| `CLOUDFLARE_API_TOKEN` | Cloudflare Pages deploy | [Secrets Script] |
| `RENDER_DEPLOY_HOOK_URL` | Trigger backend deploy | [Secrets Script] |

---

## Secrets Management Scripts

### 1. Get Cloudflare Secrets

```bash
#!/bin/bash
# get-cloudflare-secrets.sh
# Retrieves Cloudflare credentials from GitHub Secrets

echo "=== Cloudflare Secrets for Documentation ==="
echo ""
echo "To retrieve from GitHub (CLI required):"
echo ""
echo "Account ID:"
gh secret get CLOUDFLARE_ACCOUNT_ID --env prod --repo dequimpo/AwanaPointsLogger

echo ""
echo "API Token (masked in output):"
echo "Use GitHub UI: https://github.com/dequimpo/AwanaPointsLogger/settings/secrets/actions"
echo "Or Cloudflare Dashboard: https://dash.cloudflare.com/profile/api-tokens"
echo ""
echo "⚠️  Never log the actual token to console - store securely!"
```

### 2. Get Render Deploy Hook

```bash
#!/bin/bash
# get-render-secrets.sh
# Retrieves Render deployment webhook URL

echo "=== Render Deploy Hook ==="
echo ""
echo "To retrieve from GitHub:"
gh secret get RENDER_DEPLOY_HOOK_URL --env prod --repo dequimpo/AwanaPointsLogger

echo ""
echo "To find in Render Dashboard:"
echo "1. https://dashboard.render.com/"
echo "2. Select 'awanapointslogger' service"
echo "3. Go to 'Settings' > 'Deploy Hook'"
echo "4. Copy the webhook URL"
echo ""
echo "To use:"
curl -X POST "<WEBHOOK_URL>"
```

### 3. Generate Backend Secrets

```bash
#!/bin/bash
# generate-backend-secrets.sh
# Generates fresh backend secrets

echo "=== Generate Backend Secrets ==="
echo ""

echo "1. SESSION_SECRET (store in Render environment):"
openssl rand -base64 32
echo ""

echo "2. AZURE_CLIENT_SECRET (from Entra ID app registration):"
echo "   - Go to: https://portal.azure.com"
echo "   - App registrations > Awana Points Logger"
echo "   - Certificates & secrets"
echo "   - Create new client secret"
echo "   - Copy and store in Render"
echo ""

echo "3. SharePoint IDs (from Microsoft Graph Explorer):"
echo "   - Go to: https://developer.microsoft.com/en-us/graph/graph-explorer"
echo "   - GET /sites/root/lists"
echo "   - GET /drives/root"
echo "   - Note down IDs"
```

### 4. Document All Secrets

```bash
#!/bin/bash
# document-deployment-secrets.sh
# Creates a secure documentation of deployment secrets

cat > DEPLOYMENT_SECRETS_INVENTORY.md << 'EOF'
# DEPLOYMENT SECRETS INVENTORY
**⚠️ SENSITIVE - Store securely**

## Frontend (GitHub Secrets - prod environment)

### CLOUDFLARE_ACCOUNT_ID
- Location: GitHub Secrets
- Value: 4b07dbb385ac65cb9265321cc1e8d4fc
- Used by: GitHub Actions (deploy-frontend-cloudflare.yml)
- Rotation: Not needed

### CLOUDFLARE_API_TOKEN
- Location: GitHub Secrets
- Original created: Cloudflare Dashboard > API Tokens
- Permissions: Edit Cloudflare Workers, Cloudflare Pages, Account Settings
- Scoped to: Account ID 4b07dbb385ac65cb9265321cc1e8d4fc
- Last rotated: [DATE]
- Rotation policy: Every 90 days

### RENDER_DEPLOY_HOOK_URL
- Location: GitHub Secrets
- URL Format: https://api.render.com/deploy/srv-xxxxxxx?key=xxxxxxx
- Original created: Render Dashboard > awanapointslogger > Settings > Deploy Hook
- Used by: GitHub Actions (deploy-backend-render.yml)
- Last rotated: [DATE]

## Backend (Render Environment)

### AZURE_CLIENT_SECRET
- Location: Render Environment Variables
- App: Entra ID - Awana Points Logger
- Created: Azure Portal > App registrations
- Type: Client secret
- Last rotated: [DATE]
- Rotation policy: Every 90 days

### SESSION_SECRET
- Location: Render Environment Variables
- Type: Random 32+ character string
- Generated: openssl rand -base64 32
- Last rotated: [DATE]
- Rotation policy: Quarterly

## Rotation Checklist

- [ ] CLOUDFLARE_API_TOKEN (Q3)
- [ ] AZURE_CLIENT_SECRET (Q2, Q4)
- [ ] SESSION_SECRET (Q1, Q3)
- [ ] Update this inventory after each rotation

EOF

echo "Created: DEPLOYMENT_SECRETS_INVENTORY.md"
echo "📌 Store this file securely and only share with authorized team members"
```

### 5. Quick Status Check

```bash
#!/bin/bash
# check-deployment-status.sh
# Verifies all services are running

echo "=== DEPLOYMENT STATUS CHECK ==="
echo ""

echo "1. Frontend (Cloudflare Pages)"
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://awanapointslogger.pages.dev")
if [ "$FRONTEND_STATUS" = "200" ]; then
  echo "✅ Frontend: ONLINE (HTTP $FRONTEND_STATUS)"
else
  echo "❌ Frontend: OFFLINE (HTTP $FRONTEND_STATUS)"
fi
echo ""

echo "2. Backend (Render)"
BACKEND_STATUS=$(curl -s "https://awanapointslogger.onrender.com/health" | jq -r '.status // "error"')
if [ "$BACKEND_STATUS" = "healthy" ]; then
  echo "✅ Backend: HEALTHY ($BACKEND_STATUS)"
elif [ "$BACKEND_STATUS" != "error" ]; then
  echo "⚠️  Backend: DEGRADED ($BACKEND_STATUS)"
else
  echo "❌ Backend: OFFLINE"
fi
echo ""

echo "3. OAuth Provider (Entra ID)"
OAUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://login.microsoftonline.com/afdc3b01-cd69-4af3-a783-9f13cce85492/.well-known/openid-configuration")
if [ "$OAUTH_STATUS" = "200" ]; then
  echo "✅ OAuth Provider: ONLINE (HTTP $OAUTH_STATUS)"
else
  echo "❌ OAuth Provider: OFFLINE (HTTP $OAUTH_STATUS)"
fi
echo ""

echo "4. Last Deployment"
gh run list --workflow="deploy-frontend-cloudflare.yml" --limit=1 --json status,updatedAt
```

---

## Troubleshooting

### Frontend Issues

#### Problem: "Loading assets..." spinner hangs indefinitely

**Symptoms:** Web app stuck on loading screen, console shows no errors

**Solution:**
- Font loading gate is skipped on web in `App.js`
- Check network tab in DevTools for failed requests
- Clear browser cache: Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)
- Hard refresh: Ctrl+F5 (Cmd+Shift+R on Mac)

#### Problem: "Missing Azure configuration" popup

**Symptoms:** Error after successful OAuth login

**Solution:**
- Verify `EXPO_PUBLIC_AZURE_CLIENT_ID` is set in build
- Verify `app.json` has fallback values in `extra` section
- Check that GitHub variables are set in `prod` environment
- Rebuild: `npx expo export --platform web && npx wrangler pages deploy dist`

#### Problem: OAuth redirect not working (on iOS Safari)

**Symptoms:** After Microsoft sign-in, app returns to login screen

**Solution:**
- iOS Safari drops the `useAuthRequest` response on full-page redirect
- Code includes fallback: reads auth code from URL query params
- Check that `EXPO_PUBLIC_WEB_REDIRECT_URI` matches Entra ID registration
- Verify Entra ID SPA redirect URI includes `https://awanapointslogger.pages.dev/auth`

### Backend Issues

#### Problem: "CORS error" on API calls

**Symptoms:** Browser console shows `No 'Access-Control-Allow-Origin'` header

**Solution:**
```bash
# Check Render environment variable
ALLOWED_ORIGINS=https://awanapointslogger.pages.dev

# Verify backend CORS is configured
curl -s https://awanapointslogger.onrender.com/health | jq .

# Check Security headers
curl -sI https://awanapointslogger.onrender.com/health | grep "Access-Control"
```

#### Problem: SharePoint API returns 401 Unauthorized

**Symptoms:** Backend logs show "Invalid token" or "Permission denied"

**Solution:**
- Check `AZURE_CLIENT_SECRET` is correct in Render
- Verify SharePoint IDs are correct: `SHAREPOINT_SITE_ID`, `SHAREPOINT_DRIVE_ID`, `SHAREPOINT_FILE_ID`
- Check Entra ID app permissions: Microsoft Graph API > Delegated permissions
- Rotate `AZURE_CLIENT_SECRET` if needed

#### Problem: Render service won't start ("Build Failed")

**Symptoms:** Deployment fails, container doesn't start

**Solution:**
```bash
# Check Render logs
# 1. Go to https://dashboard.render.com/
# 2. Select 'awanapointslogger'
# 3. View deployment logs
# 4. Common issues:
#    - Missing environment variables
#    - Python package conflicts (run: pip install -r requirements.txt)
#    - Port configuration (must listen on PORT env var, not hardcoded)
```

### Deployment Issues

#### Problem: GitHub Actions workflow fails

**Symptoms:** Red ✗ on commit in GitHub

**Solution:**
```bash
# View workflow log
gh run view <RUN_ID> --log

# Common causes:
# 1. Missing GitHub secrets/variables in 'prod' environment
# 2. Node.js dependency resolution (npm ci fails)
# 3. Build error in React/Expo code
# 4. Missing .env variables during build

# Debug locally
npm ci
EXPO_PUBLIC_API_BASE_URL="..." npx expo export --platform web
```

#### Problem: Can't connect to Cloudflare account

**Symptoms:** Wrangler error: "Unauthorized" or "Invalid credentials"

**Solution:**
```bash
# Check GitHub secret exists
gh secret list --env prod

# Verify Wrangler authentication
npx wrangler whoami

# Re-create API token if needed:
# 1. https://dash.cloudflare.com/profile/api-tokens
# 2. Create Custom Token
# 3. Permissions:
#    - Edit: Cloudflare Workers
#    - Edit: Cloudflare Pages
#    - Read: Account Settings
# 4. Scope to specific account
# 5. Update GitHub secret
```

---

## Team Developer Guide

### For New Developers

#### Step 1: Clone and Setup

```bash
# Clone repository
git clone https://github.com/dequimpo/AwanaPointsLogger.git
cd AwanaPointsLogger

# Setup local environment
cp .env.development.example .env.development
# Edit .env.development with local values

# Frontend
npm install
npm start

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

#### Step 2: Understand the Architecture

1. **Frontend** (`App.js`, `screens/`, `services/`)
   - React Native app with web support
   - Uses Expo for native builds
   - OAuth via Entra ID + PKCE
   - Local state management in `useState`

2. **Backend** (`backend/main.py`)
   - FastAPI REST API
   - Microsoft Graph integration
   - JWT token validation
   - SharePoint XLSX read/write

3. **Services**
   - `services/authService.js` - OAuth token management
   - `services/apiClient.js` - API request signing

#### Step 3: Making Changes

**For Frontend Changes:**

```bash
# Create feature branch
git checkout -b feature/new-icon-design

# Make changes in App.js, screens/, services/
# Test locally: npm start

# Commit with descriptive message
git commit -m "feat: redesign help screen icons"

# Push to trigger GitHub Actions
git push origin feature/new-icon-design

# Create Pull Request for code review
# Once merged to main, deployment auto-triggers
```

**For Backend Changes:**

```bash
# Create feature branch
git checkout -b feature/new-api-endpoint

# Make changes in backend/main.py
# Test locally: python backend/main.py

# Commit
git commit -m "feat: add leaderboard export endpoint"

# Push to trigger GitHub Actions
git push origin feature/new-api-endpoint

# PR review → merge → auto-deploy to Render
```

### Updating Dependencies

**Frontend:**

```bash
# Check updates
npm outdated

# Update specific package
npm install react@latest

# Update all
npm update

# Update lock file
npm install

# Commit
git add package.json package-lock.json
git commit -m "chore: update dependencies"
git push origin main  # Triggers deployment
```

**Backend:**

```bash
# Check updates
pip list --outdated

# Update package
pip install --upgrade fastapi

# Update requirements
pip freeze > backend/requirements.txt

# Commit
git add backend/requirements.txt
git commit -m "chore: update backend dependencies"
git push origin main  # Triggers deployment
```

### Adding New Environment Variables

**For Production:**

1. **Add to app.json** (frontend fallback):
   ```json
   "extra": {
     "myNewVar": "default-value"
   }
   ```

2. **Add to GitHub Variables** (prod environment):
   ```
   EXPO_PUBLIC_MY_NEW_VAR=value
   ```

3. **Add to Render Environment** (if backend needs it):
   - Render Dashboard > Environment Variables

4. **Update appConfig.js**:
   ```javascript
   myNewVar: process.env.EXPO_PUBLIC_MY_NEW_VAR || extra.myNewVar
   ```

5. **Test locally**:
   ```bash
   export EXPO_PUBLIC_MY_NEW_VAR=test-value
   npm start
   ```

### Deployment Checklist Before Release

```bash
#!/bin/bash
# deployment-checklist.sh

echo "=== DEPLOYMENT CHECKLIST ==="
echo ""

echo "[ ] Code reviewed and merged to main"
echo "[ ] All tests passing locally"
echo "[ ] Dependencies updated: npm install"
echo "[ ] No console errors or warnings"
echo "[ ] Environment variables set in GitHub (prod)"
echo "[ ] Render environment variables updated"
echo "[ ] Entra ID redirect URIs match frontend URL"
echo "[ ] SharePoint file IDs are correct"
echo ""

echo "[ ] Run pre-deployment checks:"
npm audit
npm run lint  # if configured
```

### Rolling Back a Deployment

**If frontend deployment has issues:**

```bash
# Option 1: Revert commit and push (auto-redeploy)
git revert HEAD
git push origin main

# Option 2: Roll back via Cloudflare Dashboard
# https://dash.cloudflare.com/ > Pages > awanapointslogger > Deployments
# Click "Rollback" on previous good deployment
```

**If backend deployment has issues:**

```bash
# Option 1: Revert commit and push (auto-redeploy)
git revert HEAD
git push origin main

# Option 2: Manually trigger previous build in Render
# https://dashboard.render.com/ > awanapointslogger
# Click on previous successful deployment
```

### Monitoring & Logs

**Frontend:**

```bash
# Check deployment status
gh run list --workflow="deploy-frontend-cloudflare.yml"

# View build logs
gh run view <RUN_ID> --log

# Check runtime errors
# DevTools Console (F12) in browser
curl https://awanapointslogger.pages.dev
```

**Backend:**

```bash
# Check deployment status
# https://dashboard.render.com/

# View application logs
# Render Dashboard > awanapointslogger > Logs

# Health check
curl https://awanapointslogger.onrender.com/health | jq .

# API response check
curl -H "Authorization: Bearer <token>" \
  https://awanapointslogger.onrender.com/api/leaderboard | jq .
```

---

## Contact & Support

- **Primary Maintainer:** DBDNJ Development Team
- **GitHub Issues:** https://github.com/dequimpo/AwanaPointsLogger/issues
- **Slack:** #awana-dev (internal)
- **Documentation:** See `/MD/` directory

---

**This deployment guide should be reviewed and updated quarterly to reflect infrastructure changes, security updates, and new features.**
