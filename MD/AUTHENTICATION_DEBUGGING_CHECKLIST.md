# MS365 Auth Error - Step-by-Step Action Checklist

## Quick Reference: The Error Means One of These

The Azure error **"The provided authorization grant... is invalid, expired, revoked, does not match the redirection URI..."** typically means:

- ❌ Redirect URI mismatch (MOST LIKELY)
- ❌ Authorization code expired (<10 minutes)
- ❌ Client ID/Secret mismatch
- ❌ Token sent to wrong endpoint
- ❌ PKCE verification failed

---

## Immediate Actions (Start Here)

### 1. Stop Everything and Restart with Fresh Logs

```bash
# Kill running processes
pkill -f "python main.py" || true
pkill -f "expo start" || true
pkill -f "uvicorn" || true
sleep 2

# Clear old logs
rm -f /tmp/backend.log /tmp/frontend.log

# Start backend with logging to file
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
source venv/bin/activate
cd backend
nohup python3 main.py > /tmp/backend.log 2>&1 &
echo "Backend started. PID: $!"
sleep 3

# In another terminal, start frontend
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
npm start -- --port 8081 2>&1 | tee /tmp/frontend.log
```

### 2. Open Browser Developer Console
- Press **F12** to open Chrome DevTools
- Go to **Console** tab
- Go to **Application** → **Storage** to see environment vars

### 3. Attempt Login and Collect Logs

1. Click "Login with Microsoft"
2. Complete Microsoft login
3. **IMMEDIATELY** collect logs:

```bash
# In terminal 1 - Get backend logs
echo "=== BACKEND LOGS (Last 50 lines) ===" && tail -50 /tmp/backend.log
echo "" && echo "=== FULL BACKEND LOG ===" && cat /tmp/backend.log

# In terminal 2 - Screenshot frontend console
# Keep DevTools open and watch for error messages
```

---

## Checklist: Verify Configuration

### ✅ Step 1: Confirm Azure AD App Registration Config

**Where to check:** https://portal.azure.com → Azure AD → App Registrations → Your App

```
□ App name: [should be "Awana Points Logger" or similar]
□ Client ID visible: [should match AZURE_CLIENT_ID in backend/.env]
□ Tenant ID visible: [should match AZURE_TENANT_ID]

□ Go to "Authentication" tab:
  □ Redirect URIs includes: http://localhost:8081/auth
  □ Supported account types: "Accounts in this organizational directory only"
  □ Advanced settings:
    □ Allow public client flows: ON (for mobile)
    □ ID tokens: CHECKED
    
□ Go to "API Permissions":
  □ "openid" scope: GRANTED
  □ "profile" scope: GRANTED  
  □ "offline_access" scope: GRANTED (for refresh tokens)
  □ "User.Read" scope: GRANTED
  
□ Go to "Certificates & secrets":
  □ Has valid client secret (not expired)
  □ Secret value matches AZURE_CLIENT_SECRET in backend/.env
```

**ACTION:** If any missing, you must:
1. Add the missing redirect URI to Azure AD
2. Verify all permissions are granted
3. Ensure client secret hasn't expired

---

### ✅ Step 2: Verify Backend Configuration

```bash
# Check backend/.env file directly
cat /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger/backend/.env

# Expected output (sanitized):
# AZURE_CLIENT_ID=6c117750-8af8-4e5f-a016-136c2430b940  ← Match Azure AD
# AZURE_CLIENT_SECRET=4y58Q~hUUJ-sirWrcd4OVpv... ← Not expired
# AZURE_TENANT_ID=afdc3b01-cd69-4af3-a783-9f13cce85492
# SHAREPOINT_SITE_ID=...
# SESSION_SECRET=...
# ENVIRONMENT=development
# ALLOWED_ORIGINS=http://localhost:8081,http://localhost:3000
```

```bash
# Verify backend sees correct config
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
source venv/bin/activate
python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv('backend/.env', override=True)

config_items = {
    'AZURE_CLIENT_ID': os.getenv('AZURE_CLIENT_ID', 'NOT SET'),
    'AZURE_CLIENT_SECRET': 'SET' if os.getenv('AZURE_CLIENT_SECRET') else 'NOT SET',
    'AZURE_TENANT_ID': os.getenv('AZURE_TENANT_ID', 'NOT SET'),
    'ENVIRONMENT': os.getenv('ENVIRONMENT', 'NOT SET'),
    'ALLOWED_ORIGINS': os.getenv('ALLOWED_ORIGINS', 'NOT SET'),
}

print("Backend Configuration:")
for key, value in config_items.items():
    if len(str(value)) > 50:
        print(f"  {key}: {str(value)[:50]}...")
    else:
        print(f"  {key}: {value}")
EOF
```

**ACTION:** Verify:
- [ ] CLIENT_ID is set (not "YOUR_CLIENT_ID")
- [ ] CLIENT_SECRET is set and not expired
- [ ] TENANT_ID is set
- [ ] ALLOWED_ORIGINS includes `http://localhost:8081`

---

### ✅ Step 3: Verify Frontend Configuration

```bash
# Check environment variables
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
echo "Frontend Environment Variables:"
echo "EXPO_PUBLIC_AZURE_CLIENT_ID: ${EXPO_PUBLIC_AZURE_CLIENT_ID:-NOT SET}"
echo "EXPO_PUBLIC_AZURE_TENANT_ID: ${EXPO_PUBLIC_AZURE_TENANT_ID:-NOT SET}"  
echo "EXPO_PUBLIC_API_BASE_URL: ${EXPO_PUBLIC_API_BASE_URL:-NOT SET}"

# Check appConfig.js for hardcoded values
grep -A 5 "azureClientId:" /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger/config/appConfig.js
grep -A 5 "azureTenantId:" /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger/config/appConfig.js
grep -A 5 "apiBaseUrl:" /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger/config/appConfig.js
```

**ACTION:** Verify:
- [ ] EXPO_PUBLIC_AZURE_CLIENT_ID matches backend AZURE_CLIENT_ID
- [ ] EXPO_PUBLIC_AZURE_TENANT_ID matches backend AZURE_TENANT_ID
- [ ] EXPO_PUBLIC_API_BASE_URL is `http://localhost:8000` for dev

---

### ✅ Step 4: Verify Redirect URI Match

**Critical:** All these must be IDENTICAL:

```
Azure AD Config:        http://localhost:8081/auth
Frontend (web):         http://localhost:8081/auth
Frontend (mobile):      appawanapointslogger://auth (generated from scheme)
```

**Check in appConfig.js:**
```javascript
export const appConfig = {
  redirectScheme: expoConfig.scheme || 'appawanapointslogger',  // ← Mobile
  redirectPath: 'auth',                                         // ← Must be 'auth'
};
```

**Check in LoginScreen.js:**
```javascript
const FIXED_WEB_REDIRECT_URI = 
  process.env.EXPO_PUBLIC_WEB_REDIRECT_URI || 'http://localhost:8081/auth';
```

**ACTION:** Verify:
- [ ] Mobile redirect: `appawanapointslogger://auth`
- [ ] Web redirect: `http://localhost:8081/auth`
- [ ] Both registered in Azure AD

---

## Debug with Detailed Logs

### ✅ Step 5: Follow the Auth Flow with Logs

Now that we've added detailed logging, here's what to look for:

#### **In Browser Console (F12):**

```
🔑 [LoginScreen] Starting auth code exchange
🔑 [LoginScreen] Parameters: {clientId: "6c11...", redirectUri: "http://localhost:8081/auth", ...}
🔑 [LoginScreen] Calling AuthSession.exchangeCodeAsync...
✅ [LoginScreen] Auth code exchanged successfully
✅ [LoginScreen] Token response keys: ["accessToken", "expiresIn", "idToken", ...]
✅ [LoginScreen] Access token length: 1234

🔐 [AuthService] Exchanging access token for session token
🔐 [AuthService] Token length: 1234
🔐 [AuthService] Backend URL: http://localhost:8000/auth/token
🔐 [AuthService] Response status: 200
✅ [AuthService] Token exchange successful
```

**IF YOU SEE ERROR AT THIS STEP:** Look for:
- ❌ `Response status: 401` → Token is invalid/expired
- ❌ `Response status: 400` → Malformed request
- ❌ `Response status: 500` → Backend crashed
- ❌ `Response status: 0` → Network error / CORS issue

#### **In Backend Logs (/tmp/backend.log):**

```
======================================================================
🔐 [AuthToken] POST /auth/token request received
======================================================================
🔐 [AuthToken] Token length: 1234
🔐 [AuthToken] Token first 50 chars: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
🔐 [AuthToken] Client ID in backend: 6c117750-8af8-4e5f...
🔐 [AuthToken] Tenant ID in backend: afdc3b01-cd69-4af3...

🔐 [Graph] Fetching user profile with Graph /me
🔐 [Graph] Token length: 1234
📊 [Graph] Response status: 200
✅ [Graph] Successfully fetched user: John Doe

✅ [AuthToken] User verified: John Doe
✅ [AuthToken] Session token created successfully
======================================================================
```

**IF YOU SEE ERROR AT THIS STEP:** Look for:
- `📊 [Graph] Response status: 401` → Token invalid/expired/wrong client
- `❌ [Graph] Status code: 403` → Permission/scope issue
- `❌ [Graph] Response body: {...error details...}` → Specific Azure error

---

### ✅ Step 6: If You See Graph 401 Error

The Azure error message will be in the backend log. Look for:

```
❌ [Graph] Graph API error!
❌ [Graph] Status code: 401
❌ [Graph] Response body: {"error":{"code":"Authorization_RequestDenied","message":"...SPECIFIC ERROR..."}}
```

**Common Azure Error Messages & Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| "invalid_client" | Client ID/Secret mismatch | Verify AZURE_CLIENT_ID and CLIENT_SECRET match Azure AD |
| "invalid_grant" | Token expired, revoked, or code already used | Check that authorization code hasn't expired (usually <10 min) |
| "invalid_scope" | Requesting scope not configured | Add "openid", "profile", "User.Read" to Azure AD API Permissions |
| "AADSTS65001: User..." | User didn't consent to scopes | Clear browser cache/cookies and try again |
| "Redirect URI mismatch" | Redirect URI not matching | Add exact redirect URI to Azure AD Authentication settings |

---

## Quick Test Commands

### Test Backend Health
```bash
curl -s http://localhost:8000/health | jq .
# Should return: {"status":"ok"} or similar
```

### Test Token Flow Manually
```bash
# If you have a valid MS365 token (from browser console):
TOKEN="eyJhbGci...YOUR_ACTUAL_TOKEN..."

curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d "{\"access_token\":\"$TOKEN\"}" \
  -v  # verbose for full headers and response
```

### Check if Ports Are Running
```bash
lsof -nP -iTCP:8000,8081 -sTCP:LISTEN
# Should show:
# - Python on 8000 (backend)
# - Node.js on 8081 (frontend)
```

---

## Common Issues & Quick Fixes

### Issue: "Redirect URI mismatch" in Azure error

**Quick Fix:**
1. Check backend log for exact redirectUri being sent
2. Go to Azure Portal → Authentication → Redirect URIs
3. Add that exact URI (including http:// or scheme://)
4. Save and wait 2 minutes for propagation

### Issue: "Invalid token" after 1-2 minutes of waiting

**Quick Fix:**
- Authorization codes expire in ~10 minutes
- Access tokens typically expire in ~1 hour
- Log in again immediately without delays between steps

### Issue: CORS errors in browser console

**Quick Fix:**
1. Backend must have:
   ```python
   CORS enabled for http://localhost:8081
   ```
2. Check backend output for: `"✒ Allowed CORS Origins: [...]"`

### Issue: Token works in one browser but not another

**Quick Fix:**
- Different browsers have different sessionStorage
- Clear browser storage: DevTools → Application → Clear site data
- Try in Incognito/Private window (fresh storage)

---

## Next Steps After Debugging

1. **Collect all logs** from browser console + backend logs
2. **Screenshot the error** in browser/backend
3. **Verify Azure AD config** matches docs
4. **If still failing:** Note the EXACT error message from:
   - Browser console
   - Backend logs (/tmp/backend.log)
   - Azure request ID (if shown)

---

## Need More Help?

1. Check [AUTHENTICATION_DEBUG_GUIDE.md](./AUTHENTICATION_DEBUG_GUIDE.md) for in-depth explanations
2. Review Azure AD documentation: https://docs.microsoft.com/en-us/graph/auth
3. Check Expo Auth Session docs: https://docs.expo.dev/versions/latest/sdk/auth-session/
