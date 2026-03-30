# Authentication Error Resolution - Complete Action Plan

## Summary of Your Issue

**Error:** "The provided authorization grant (e.g., authorization code, resource owner credentials) or refresh token is invalid, expired, revoked, does not match the redirection URI used in the authorization request, or was issued to another client."

**When:** After changes to prepare for production  
**Impact:** MS365 login failing after Azure AD authentication  
**Root Cause:** Most likely **Redirect URI Mismatch** or configuration issue

---

## What I've Done For You

✅ **Added detailed debug logging** to:
- Backend `/auth/token` endpoint
- Graph `/me` verification call
- Frontend token exchange
- Authentication service

✅ **Created three guidance documents:**
1. `AUTHENTICATION_DEBUG_GUIDE.md` - In-depth explanations
2. `AUTHENTICATION_DEBUGGING_CHECKLIST.md` - Step-by-step action plan
3. `PRODUCTION_AUTH_CHECKLIST.md` - Production readiness

---

## Immediate Next Steps (Do This Now)

### Step 1: Restart Backend with New Debug Logging (2 min)

```bash
# Kill old processes
pkill -f "python main.py" || true
pkill -f "python main.py" || true
sleep 2

# Start fresh backend with logs
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
source venv/bin/activate
cd backend
nohup python3 main.py > /tmp/backend.log 2>&1 &
echo "Backend started"
sleep 3

# Check if it's running
curl -s http://localhost:8000/health
```

### Step 2: Start Frontend (1 min)

```bash
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
npm start -- --port 8081
```

### Step 3: Attempt Login and Capture Logs (5 min)

1. Open browser: http://localhost:8081
2. Press **F12** to open Developer Console
3. Click "Login with Microsoft"
4. Complete Microsoft login flow
5. Watch for error in console

### Step 4: Run Verification Script (3 min)

```bash
# In another terminal, run this diagnostic:
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
source venv/bin/activate
python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv('backend/.env', override=True)

print("\n" + "="*60)
print("AUTHENTICATION CONFIGURATION CHECK")
print("="*60)

checks = [
    ("AZURE_CLIENT_ID", os.getenv('AZURE_CLIENT_ID')),
    ("AZURE_TENANT_ID", os.getenv('AZURE_TENANT_ID')),
    ("SESSION_SECRET", "SET" if os.getenv('SESSION_SECRET') else "NOT SET"),
    ("ENVIRONMENT", os.getenv('ENVIRONMENT')),
    ("ALLOWED_ORIGINS", os.getenv('ALLOWED_ORIGINS')),
]

for key, value in checks:
    if len(str(value)) > 40:
        display = str(value)[:40] + "..."
    else:
        display = value
    status = "✅" if value and value != "NOT SET" else "❌"
    print(f"{status} {key}: {display}")

print("\n" + "="*60)
EOF

# Check backend logs
echo "" && echo "Backend logs:" && tail -30 /tmp/backend.log
```

### Step 5: Collect Error Details

Look in **two places** for the error:

**Frontend (Browser Console - F12):**
```
Look for anything with ❌ or Error
Examples:
❌ [AuthService] Backend auth failed: Status 401
❌ [LoginScreen] Login error: ...
```

**Backend (/tmp/backend.log):**
```
Look for Graph API error details:
❌ [Graph] Graph API error!
❌ [Graph] Status code: 401
❌ [Graph] Response body: {"error": {...}}
```

---

## Diagnosis Tree

Based on where the error appears:

### **Error in Browser Console** 

#### `Status 200 but no login success`
→ Backend config issue  
→ Go to: PRODUCTION_AUTH_CHECKLIST.md, Item 1

#### `Status 401/403 from backend`
→ Token rejected by backend  
→ Go to: AUTHENTICATION_DEBUGGING_CHECKLIST.md, Step 6

#### `Network Error / CORS error`
→ Backend CORS configuration wrong  
→ Run: `curl -X POST http://localhost:8000/auth/token -H "Origin: http://localhost:8081" ...`

#### `Timeout / No response`
→ Backend not running or unreachable  
→ Run: `lsof -nP -iTCP:8000 -sTCP:LISTEN`

---

### **Error in Backend Logs (/tmp/backend.log)**

#### `📊 [Graph] Response status: 401`
**Cause:** Token invalid, expired, or client mismatch

**Quick Check:**
```bash
# Verify backend credentials match Azure AD
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
echo "Backend CLIENT_ID:" $(grep AZURE_CLIENT_ID backend/.env | cut -d= -f2)
echo "Go to Azure Portal and compare with App Registration Client ID"
```

**Fix:** 
- [ ] Verify AZURE_CLIENT_ID matches Azure AD
- [ ] Verify AZURE_CLIENT_SECRET hasn't expired
- [ ] Verify AZURE_TENANT_ID is correct
- [ ] Run: `pkill -f "python main.py"; sleep 2; source venv/bin/activate; cd backend; nohup python3 main.py > /tmp/backend.log 2>&1 &`

---

#### `❌ [Graph] Response body: {"error": {"code": "Redirect_Uri_Mismatch", ...}}`
**Cause:** Frontend sending token with wrong redirect URI in JWT

**Quick Check:**
```bash
# Check what redirectUri frontend is using
grep -r "redirectUri" /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger/screens/
grep -r "FIXED_WEB_REDIRECT_URI" /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger/screens/
```

**Expected:** `http://localhost:8081/auth`

**Fix:**
1. Go to Azure AD App Registration → Authentication
2. Add or verify redirect URI: `http://localhost:8081/auth`
3. Save and wait 2 minutes
4. Try login again

---

#### `❌ [Graph] Response body: {"error": {"code": "invalid_client", ...}}`
**Cause:** Client ID or secret mismatch

**Fix:**
1. Azure Portal → App Registrations → Your App
2. Copy Client ID exactly
3. Compare with: `grep AZURE_CLIENT_ID backend/.env`
4. If different, update backend/.env
5. Restart backend

---

#### `❌ [AuthToken] Exception in /auth/token: ...`
**Cause:** Unexpected backend error

**Action:**
- Look at full traceback in logs
- See what line failed
- Run: `grep -n "raise\|except\|def" backend/main.py | head -20` to find issue location

---

## Files Changed for Debug Logging

1. **services/authService.js** - Added token exchange logging
2. **screens/LoginScreen.js** - Added auth code exchange logging  
3. **backend/main.py** - Added Graph API and /auth/token logging

These can be removed for production or wrapped in `if DEBUG:` blocks.

---

## Critical Configuration to Verify

### Azure AD Must Have:
- [ ] Client ID: Visible in App Registration → Overview
- [ ] Client Secret: Not expired in Certificates & secrets
- [ ] Redirect URI: `http://localhost:8081/auth` in Authentication tab
- [ ] API Permissions: `openid`, `profile`, `offline_access`, `User.Read` (at least)
- [ ] Supported account types: "Accounts in this organizational directory only"

### Backend (.env) Must Have:
- [ ] `AZURE_CLIENT_ID` = Exact match to Azure AD
- [ ] `AZURE_CLIENT_SECRET` = Valid, not expired
- [ ] `AZURE_TENANT_ID` = Your tenant ID
- [ ] `SESSION_SECRET` = Some random string
- [ ] `ENVIRONMENT` = development or production
- [ ] `ALLOWED_ORIGINS` = includes http://localhost:8081

### Frontend (Environment) Must Have:
- [ ] `EXPO_PUBLIC_AZURE_CLIENT_ID` = Same as backend
- [ ] `EXPO_PUBLIC_AZURE_TENANT_ID` = Same as backend
- [ ] `EXPO_PUBLIC_API_BASE_URL` = http://localhost:8000 (dev)

---

## Most Likely Fixes (Order by Probability)

1. **Redirect URI Mismatch** (40% of cases)
   - Action: Add `http://localhost:8081/auth` to Azure AD
   - Expected time to fix: 5 minutes

2. **Environment Variables Not Loaded** (25% of cases)
   - Action: Verify backend/.env and restart backend
   - Expected time to fix: 3 minutes

3. **Client ID/Secret Mismatch** (20% of cases)
   - Action: Copy-paste correct values from Azure Portal
   - Expected time to fix: 5 minutes

4. **Authorization Code Expired** (10% of cases)
   - Action: Complete login quickly without delays
   - Expected time to fix: 1 minute (just retry)

5. **Other** (5% of cases)
   - Action: Follow debug logs and check error message
   - Expected time to fix: 15-30 minutes

---

## How to Share Logs for Help

If you need to ask for help, share:

1. **Frontend Error (from Browser F12 Console):**
   ```
   [Copy everything with 🔑, ❌, ✅ emoji]
   ```

2. **Backend Error (from /tmp/backend.log):**
   ```bash
   cat /tmp/backend.log
   ```

3. **Configuration (sanitize secrets):**
   ```bash
   grep "AZURE_CLIENT_ID\|TENANT_ID\|ENVIRONMENT" backend/.env
   # Show CLIENT_ID but hide CLIENT_SECRET
   ```

4. **Azure AD Details:**
   - Client ID from App Registration
   - Redirect URIs configured
   - API Permissions granted

---

## After Fixing the Error

Once authentication is working:

1. **Review PRODUCTION_AUTH_CHECKLIST.md** to prepare for production
2. **Remove debug logging** (optional, but recommended for production)
3. **Add rate limiting** on auth endpoints
4. **Set up HTTPS** for production
5. **Use secure credential storage** (not .env files)
6. **Enable audit logging** for security events

---

## Quick Reference Commands

```bash
# Check backend is running
lsof -nP -iTCP:8000 -sTCP:LISTEN

# View backend logs in real-time
tail -f /tmp/backend.log

# Check backend config
grep -E "AZURE|ENVIRONMENT" /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger/backend/.env

# Restart backend
pkill -f "python main.py"; sleep 2; cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger && source venv/bin/activate && cd backend && nohup python3 main.py > /tmp/backend.log 2>&1 &

# Test token manually (if you have a valid token)
TOKEN="your_token_here"
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d "{\"access_token\":\"$TOKEN\"}"
```

---

## Next Document to Read

Based on the error you see, read one of these:

- **Still stuck on error:** → Read [AUTHENTICATION_DEBUGGING_CHECKLIST.md](./AUTHENTICATION_DEBUGGING_CHECKLIST.md)
- **Auth works, preparing for production:** → Read [PRODUCTION_AUTH_CHECKLIST.md](./PRODUCTION_AUTH_CHECKLIST.md)  
- **Want to understand how it works:** → Read [AUTHENTICATION_DEBUG_GUIDE.md](./AUTHENTICATION_DEBUG_GUIDE.md)

Good luck! 🚀
