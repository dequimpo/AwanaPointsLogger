# Azure Redirect URI Registration - Quick Fix

## The Problem

Your token exchange is failing with **HTTP 400** because Azure can't find `http://localhost:8081/auth` in your app registration's allowed redirect URIs.

**Error Context:**
- Error: "does not match the redirection URI used in the authorization request"
- Endpoint: `https://login.microsoftonline.com/afdc3b01-cd69-4af3-a783-9f13cce85492/oauth2/v2.0/token`
- Status: 400 Bad Request

## What We've Done

✅ Added `EXPO_PUBLIC_WEB_REDIRECT_URI=http://localhost:8081/auth` to `.env.development`

## What You Need to Do - Register in Azure AD

### Step 1: Open Azure Portal
1. Go to [Azure Portal](https://portal.azure.com)
2. Sign in with your Azure account
3. Search for **"Azure Active Directory"** or navigate from the sidebar

### Step 2: Find Your App Registration
1. Click **"App registrations"** in the left menu
2. Search for your app by **Client ID**: `6c117750-8af8-4e5f-a016-136c2430b940`
3. Click to open the app details

### Step 3: Add the Redirect URI
1. In the left menu, click **"Authentication"**
2. Under **"Platform configurations"**, look for **"Web"** section
3. If no "Web" section exists, click **"Add a platform"** → Select **"Web"**
4. Under **"Redirect URIs"**, click **"Add URI"**
5. Enter: `http://localhost:8081/auth`
6. ✅ **Click "Save"** at the bottom

### Step 4: Verify Other Scopes (Optional but Recommended)

In the left menu, click **"API permissions"** and verify:
- ✅ `openid` (should be included by default)
- ✅ `profile` (should be included by default)
- ✅ `offline_access` (for token refresh)
- ✅ `User.Read` (Microsoft Graph)

If any are missing, click **"Add a permission"** → **"Microsoft Graph"** → **"Delegated permissions"** → Check the box → **"Add permissions"**

## Verification

After registering the redirect URI, verify it's saved by checking the Authentication page shows:

```
Platform configurations
├── Web
│   └── Redirect URIs
│       └── http://localhost:8081/auth ✅
```

## Restart App & Test

After saving in Azure AD:

```bash
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
pkill -f "expo start" || true
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
npm start -- --port 8081
```

Then:
1. Open `http://localhost:8081` in your browser
2. Open **F12 Developer Console** (Console tab)
3. Click **"Login with Microsoft"**
4. Complete the Microsoft login
5. Check logs - you should now see `✅ Auth code exchanged successfully` instead of the 400 error

## Azure AD Configuration Context

Your app is registered with:
- **Client ID**: `6c117750-8af8-4e5f-a016-136c2430b940`
- **Tenant ID**: `afdc3b01-cd69-4af3-a783-9f13cce85492`
- **Application Name**: Awana Points Logger (verify in portal)

## Why This Matters

Azure AD uses redirect URIs for security:
1. **Authorization Request**: Your app sends user to Azure with `redirect_uri=http://localhost:8081/auth`
2. **Azure Callback**: Azure redirects user back to that exact URI with authorization code
3. **Token Exchange**: Your app exchanges code for token, must prove ownership by sending the SAME `redirect_uri`
4. **Security Validation**: Azure verifies `redirect_uri` is registered and matches exactly

If they don't match, you get: `HTTP 400 - "does not match the redirection URI"`

## Production Considerations

For production deployment, you'll need to:
1. Register your production domain: `https://yourdomain.example/auth`
2. Use HTTPS (not HTTP)
3. Keep both development and production URIs registered (can have multiple)
4. Update `.env.production` with the correct production URI

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| 400 Bad Request | Redirect URI not registered | Register in Azure AD |
| Redirect to wrong page | Typo in redirect_uri | Check spelling exactly |
| HTTPS needed | Using HTTP in production | Use HTTPS in production URIs |
| Code expired | Took too long to exchange | Exchange within 10 minutes of auth code |

## Files Modified

- ✅ `.env.development` - Added `EXPO_PUBLIC_WEB_REDIRECT_URI`
- `screens/LoginScreen.js` - Enhanced logging (already done)
- `backend/.env` - Already configured

## Next Steps

1. Register the redirect URI in Azure AD (this is the critical step)
2. Restart the frontend app
3. Test login - it should work!
4. Proceed to production setup when ready
