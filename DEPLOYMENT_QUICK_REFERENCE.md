# Awana Points Logger - QUICK REFERENCE CARD

**For Developers & Operations Team**  
**Print & Post:** Post this near your desk or share with the team

---

## 🚀 DEPLOYMENT QUICK START

### Deploy Frontend (Automatic)
```bash
git push origin main  # Triggers GitHub Actions
# Deployed to: https://awanapointslogger.pages.dev
```

### Deploy Backend (Automatic)
```bash
cd backend && git add . && git push  # Triggers GitHub Actions
# Deployed to: https://awanapointslogger.onrender.com
```

### Manual Frontend Deploy
```bash
EXPO_PUBLIC_API_BASE_URL="https://awanapointslogger.onrender.com" \
EXPO_PUBLIC_AZURE_CLIENT_ID="6c117750-8af8-4e5f-a016-136c2430b940" \
EXPO_PUBLIC_AZURE_TENANT_ID="afdc3b01-cd69-4af3-a783-9f13cce85492" \
EXPO_PUBLIC_WEB_REDIRECT_URI="https://awanapointslogger.pages.dev/auth" \
npx expo export --platform web && \
npx wrangler pages deploy dist --project-name=awanapointslogger
```

---

## 📋 CRITICAL SERVICE URLs

| Service | URL | Status |
|---------|-----|--------|
| **Frontend** | https://awanapointslogger.pages.dev | Check: `curl -I` |
| **Backend API** | https://awanapointslogger.onrender.com | Check: `curl /health` |
| **GitHub Repo** | https://github.com/dequimpo/AwanaPointsLogger | — |
| **Render Dashboard** | https://dashboard.render.com | — |
| **Cloudflare Dashboard** | https://dash.cloudflare.com | — |
| **Entra ID** | https://portal.azure.com | — |

---

## 🔑 CRITICAL SECRETS REFERENCE

### GitHub Secrets (prod environment)
```
✓ CLOUDFLARE_ACCOUNT_ID = 4b07dbb385ac65cb9265321cc1e8d4fc
✓ CLOUDFLARE_API_TOKEN = [Use GitHub UI to view]
✓ RENDER_DEPLOY_HOOK_URL = [Use GitHub UI to view]
```

### GitHub Variables (prod environment)
```
✓ CLOUDFLARE_PAGES_PROJECT_NAME = awanapointslogger
✓ EXPO_PUBLIC_API_BASE_URL = https://awanapointslogger.onrender.com
✓ EXPO_PUBLIC_AZURE_CLIENT_ID = 6c117750-8af8-4e5f-a016-136c2430b940
✓ EXPO_PUBLIC_AZURE_TENANT_ID = afdc3b01-cd69-4af3-a783-9f13cce85492
✓ EXPO_PUBLIC_AZURE_AUTH_SCOPES = openid profile offline_access User.Read
✓ EXPO_PUBLIC_WEB_REDIRECT_URI = https://awanapointslogger.pages.dev/auth
```

### Render Environment Variables
```
✓ AZURE_CLIENT_ID = 6c117750-8af8-4e5f-a016-136c2430b940
✓ AZURE_CLIENT_SECRET = [In Render dashboard, from Entra ID]
✓ AZURE_TENANT_ID = afdc3b01-cd69-4af3-a783-9f13cce85492
✓ SHAREPOINT_SITE_ID = [From Microsoft Graph Explorer]
✓ SHAREPOINT_DRIVE_ID = [From Microsoft Graph Explorer]
✓ SHAREPOINT_FILE_ID = [From Microsoft Graph Explorer]
✓ SESSION_SECRET = openssl rand -base64 32
✓ ALLOWED_ORIGINS = https://awanapointslogger.pages.dev
✓ ENVIRONMENT = production
```

---

## 🛠️ TECH STACK

### Frontend
- React 18.2.0 | React Native 0.72.10 | Expo 49.0.0
- React Native Web 0.19.6 | React DOM 18.2.0
- Expo Auth Session 5.0.2 | Expo Secure Store 12.3.1
- Node.js 16+ | npm

### Backend
- FastAPI 0.104.1 | Uvicorn 0.24.0 | Python 3.9+
- MSAL 1.25.0 | PyJWT 2.10.1 | httpx 0.25.2
- Pydantic 2.5.0 | python-dotenv 1.0.0

### Infrastructure
- Cloudflare Pages (Frontend)
- Render (Backend)
- GitHub Actions (CI/CD)
- Microsoft Entra ID (OAuth)
- SharePoint Online (Data)

---

## ✅ HEALTH CHECKS

### Frontend Health
```bash
curl -I https://awanapointslogger.pages.dev
# Expected: HTTP 200
```

### Backend Health
```bash
curl https://awanapointslogger.onrender.com/health
# Expected: { "status": "healthy" }
```

### OAuth Health
```bash
curl https://login.microsoftonline.com/afdc3b01-cd69-4af3-a783-9f13cce85492/.well-known/openid-configuration
# Expected: HTTP 200 with configuration
```

---

## 🔧 COMMON MANAGEMENT TASKS

### View Deployment Status
```bash
gh run list --workflow="deploy-frontend-cloudflare.yml" --limit=5
gh run list --workflow="deploy-backend-render.yml" --limit=5
```

### View Recent Build Logs
```bash
gh run view <RUN_ID> --log
# Get RUN_ID from above commands
```

### Trigger Manual Deployment
```bash
# Frontend
gh workflow run deploy-frontend-cloudflare.yml --ref main

# Backend
gh workflow run deploy-backend-render.yml --ref main
```

### Check GitHub Secrets
```bash
# List secrets (values masked)
gh secret list --env prod

# View specific secret
gh secret get CLOUDFLARE_ACCOUNT_ID --env prod
```

### Check Render Logs
```bash
# 1. Go to https://dashboard.render.com/
# 2. Click 'awanapointslogger' service
# 3. Go to 'Logs' tab
# 4. Filter by recent deployments
```

### Get Share Point File IDs
```bash
# Use Microsoft Graph Explorer
# https://developer.microsoft.com/en-us/graph/graph-explorer

# Query: GET /sites/root/lists
# Query: GET /drives/root/children
# Query: GET /sites/{site-id}/drive/items/{item-id}
```

---

## 🚨 TROUBLESHOOTING QUICK GUIDE

### "App stuck on loading"
- Clear cache: Cmd+Shift+Delete
- Hard refresh: Cmd+Shift+R
- Check Network tab for failed requests

### "CORS error on API calls"
- Verify ALLOWED_ORIGINS in Render
- Check Authorization header is sent
- Curl test: `curl -H "Authorization: Bearer TOKEN" https://...`

### "OAuth 401 Unauthorized"
- Verify AZURE_CLIENT_SECRET in Render
- Check Entra ID app permissions
- Rotate client secret if needed

### "Render build failed"
- Check Render logs (Dashboard > Logs)
- Verify environment variables are set
- Run locally: `pip install -r requirements.txt && python main.py`

### "Frontend not updating after deploy"
- Clear browser cache completely
- Hard refresh: Cmd+Shift+R
- Check GitHub Actions workflow succeeded
- Verify dist/ was deployed to Pages

---

## 📞 EMERGENCY CONTACTS

**For Production Issues:**
- Uptime monitoring: [Configure monitoring service]
- Incident response: #awana-dev Slack channel
- On-call rotation: [Add contact info]

**For Azure/SharePoint Issues:**
- Email: support@microsoft.com
- Help: https://support.microsoft.com

**For Cloudflare Issues:**
- Dashboard: https://dash.cloudflare.com
- Status: https://www.cloudflarestatus.com

**For Render Issues:**
- Dashboard: https://dashboard.render.com
- Status: https://render-status.com

---

## 📅 MAINTENANCE SCHEDULE

- **Weekly:** Check GitHub Actions runs for failures
- **Monthly:** Review Render logs for errors
- **Quarterly:** Rotate secrets (CLIENT_SECRET, API_TOKEN)
- **Quarterly:** Update dependencies: `npm update && pip list --outdated`
- **Semi-annually:** Review CORS policies and security headers

---

**FULL DOCUMENTATION:** See `DEPLOYMENT.md` for complete deployment guide.
