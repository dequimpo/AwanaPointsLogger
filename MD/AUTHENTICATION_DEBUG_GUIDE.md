# MS365 Authentication Debug Guide

## Error Analysis
**Error Message:** "The provided authorization grant (e.g., authorization code, resource owner credentials) or refresh token is invalid, expired, revoked, does not match the redirection URI used in the authorization request, or was issued to another client."

This error from Azure AD typically indicates ONE of these issues:

1. **Redirect URI Mismatch** (MOST COMMON)
2. **Authorization Code Expired**
3. **Client ID Mismatch**
4. **Malformed Access Token**
5. **Token Revoked or Invalid**

---

## Systematic Debug Steps

### STEP 1: Verify Redirect URI Configuration
**WHERE THE ISSUE LIKELY IS!**

The redirect URI must match EXACTLY between:
- Azure AD App Registration
- Frontend code
- Backend expectations

**Check these:**

#### A. Azure Portal Settings
1. Go to Azure AD → App Registrations → Your App
2. Click "Authentication"
3. Check "Redirect URIs" - it should include:
   ```
   http://localhost:8081/auth
   ```
4. Verify for both Web and Mobile platforms

#### B. Frontend Code (appConfig.js)
```javascript
redirectScheme: expoConfig.scheme || 'appawanapointslogger',
redirectPath: 'auth',
```
This builds: `appawanapointslogger://auth` for mobile or `http://localhost:8081/auth` for web

#### C. LoginScreen.js
```javascript
const FIXED_WEB_REDIRECT_URI = 
  process.env.EXPO_PUBLIC_WEB_REDIRECT_URI || 'http://localhost:8081/auth';

const redirectUri = Platform.OS === 'web'
  ? FIXED_WEB_REDIRECT_URI
  : AuthSession.makeRedirectUri({...});
```

**ACTION:** 
- [ ] Verify `http://localhost:8081/auth` is in Azure AD App Registration
- [ ] Check if port 8081 is correct for your dev environment
- [ ] If using production URL, add that to Azure AD config

---

### STEP 2: Verify Authorization Code Exchange

The frontend exchanges the auth code for a token using PKCE. Check this flow:

```javascript
// LoginScreen.js - finishLogin()
const tokenResponse = await AuthSession.exchangeCodeAsync(
  {
    clientId: appConfig.azureClientId,
    code,
    redirectUri,           // ← Must match Azure AD config
    codeVerifier,          // ← PKCE verification
  },
  azureDiscovery
);
```

**DEBUGGING:** Add logging
```javascript
console.log('exchangeCodeAsync parameters:', {
  clientId: appConfig.azureClientId,
  redirectUri,
  codeVerifier: codeVerifier ? 'present' : 'MISSING',
  code: code ? 'present' : 'MISSING',
});
```

**ACTION:**
- [ ] Check browser console for the exchangeCodeAsync parameters
- [ ] Verify clientId matches Azure AD
- [ ] Verify redirectUri is correct

---

### STEP 3: Verify Token is Valid Before Sending to Backend

After successfully exchanging the code for a token, the frontend sends that token to your backend. But sometimes the token is:
- Already expired
- Malformed
- For wrong scope

**DEBUG:** In authService.js, add:
```javascript
async authenticate({ accessToken }) {
  console.log('🔐 Sending access token to backend');
  console.log('Access token first 50 chars:', accessToken?.substring(0, 50));
  console.log('Access token length:', accessToken?.length);
  
  try {
    const response = await fetch(`${API_BASE_URL}/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        access_token: accessToken,
      }),
    });

    const data = await response.json();
    
    if (!response.ok) {
      console.error('❌ Backend auth failed:', data);
      throw new Error(data.detail || 'Authentication failed');
    }
    // ... rest of code
  }
}
```

**ACTION:**
- [ ] Check frontend console logs
- [ ] Verify the token is a valid JWT (should have 3 dot-separated parts)
- [ ] Check token length (should be 1000+ characters)

---

### STEP 4: Verify Backend Configuration

Backend configuration in `backend/main.py`:

```python
config = {
    "client_id": os.getenv("AZURE_CLIENT_ID", "YOUR_CLIENT_ID"),
    "client_secret": os.getenv("AZURE_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
    "tenant_id": os.getenv("AZURE_TENANT_ID", "YOUR_TENANT_ID"),
    ...
}
```

**MISMATCH ISSUES:**
1. Backend client_id ≠ Frontend client_id
2. Backend client_secret is wrong/expired
3. Backend tenant_id is wrong

**CHECK:**
```bash
# Run this in terminal to see what backend is using:
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
source venv/bin/activate
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('backend/.env', override=True)
print('Backend Config:')
print('  CLIENT_ID:', os.getenv('AZURE_CLIENT_ID', 'NOT SET')[:20] + '...')
print('  CLIENT_SECRET: set' if os.getenv('AZURE_CLIENT_SECRET') else 'NOT SET')
print('  TENANT_ID:', os.getenv('AZURE_TENANT_ID', 'NOT SET'))
print('  API_BASE_URL should match frontend:', os.getenv('ALLOWED_ORIGINS'))
"
```

**ACTION:** Verify backend/.env has correct values

---

### STEP 5: Check Token Verification Flow

Backend fetches Graph /me endpoint with the access token:

```python
async def fetch_signed_in_user(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me?$select=id,displayName,userPrincipalName,mail",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if response.status_code != 200:
        return {}  # ← This hides the actual error!

    return response.json()
```

**PROBLEM:** When Graph returns 401, it just returns empty dict, which then causes the confusing error.

**FIX:** Add detailed error logging

```python
async def fetch_signed_in_user(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me?$select=id,displayName,userPrincipalName,mail",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    
    print(f"📊 Graph /me response status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Graph API error: {response.text}")
        print(f"⚠️  Headers sent: {response.request.headers}")
        return {}

    return response.json()
```

---

## Quick Verification Checklist

### Redirect URI
- [ ] Azure AD config includes `http://localhost:8081/auth`
- [ ] Frontend appConfig uses same redirectUri
- [ ] LoginScreen FIXED_WEB_REDIRECT_URI matches

### Environment Variables
- [ ] `/backend/.env` has correct AZURE_CLIENT_ID
- [ ] `/backend/.env` has correct AZURE_CLIENT_SECRET  
- [ ] `/backend/.env` has correct AZURE_TENANT_ID
- [ ] Frontend has EXPO_PUBLIC_AZURE_CLIENT_ID set
- [ ] Frontend has EXPO_PUBLIC_AZURE_TENANT_ID set

### Token Flow
- [ ] Frontend successfully exchanges code for token (check browser console)
- [ ] Token is sent as `access_token` in JSON body to `/auth/token`
- [ ] Backend receives token and calls Graph /me
- [ ] Graph endpoint returns user data

### CORS & Headers
- [ ] `ALLOWED_ORIGINS` in backend includes frontend URL
- [ ] Frontend sends `Content-Type: application/json`
- [ ] Backend accepts requests from frontend

---

## Testing Commands

### 1. Test Backend Is Running
```bash
curl -X GET http://localhost:8000/health 2>&1 | jq .
```

### 2. Test With Valid Token (if you have one)
```bash
# Set these from your actual values
TOKEN="eyJhbGci..." # Your actual access token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d "{\"access_token\":\"$TOKEN\"}" 2>&1 | jq .
```

### 3. Check Backend Logs
```bash
# If running via nohup:
tail -50 /tmp/backend.log

# If running in terminal, check the terminal output for:
# - 📊 Graph /me response status
# - ❌ Graph API error messages
```

---

## Most Likely Culprits (in order)

1. **Redirect URI Mismatch** - Azure AD config doesn't match frontend ← CHECK THIS FIRST
2. **Client ID/Secret Mismatch** - Backend using wrong credentials  
3. **Authorization Code Expired** - Too much time between auth request and token exchange
4. **PKCE State Lost** - sessionStorage codeVerifier not available on web
5. **Token Already Revoked** - User cancelled or error in first exchange

---

## Next Steps

1. Add detailed logging from this guide
2. Run through checklist items
3. Check browser console (F12) for frontend errors
4. Check backend logs: `tail -50 /tmp/backend.log`
5. Verify Azure AD App Registration matches all configs
6. Test the token exchange manually with cURL if possible

Would you like me to apply the debug logging code to your files?
