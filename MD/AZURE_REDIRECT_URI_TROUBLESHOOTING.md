# Azure AD Redirect URI Troubleshooting Checklist

## Current Status
- ❌ Frontend getting 400 error: redirect URI mismatch
- Frontend is sending: `http://localhost:8081/auth`
- Azure is rejecting it as not matching

## Problem Diagnosis

The error "redirect URI mismatch" means Azure AD received the code with the redirect_uri you're sending, but it doesn't match what's registered in your app.

## 🔍 Verification Steps (DO THIS NOW)

### Step 1: Check Current Azure AD Configuration
1. Go to **[Azure Portal](https://portal.azure.com)**
2. Search for **"Azure Active Directory"**
3. Click **"App registrations"**
4. Find your app with Client ID: `6c117750-8af8-4e5f-a016-136c2430b940`
5. Click **"Authentication"** in left menu
6. **SCREENSHOT or WRITE DOWN exactly what you see:**

```
Platform configurations:

[ ] Web
    - Redirect URIs listed:
      ___________________________
      ___________________________
      
[ ] SPA
    - Redirect URIs listed:
      ___________________________
      ___________________________
      
[ ] Mobile
    (list any if present)
    - Redirect URIs listed:
      ___________________________
```

### Step 2: What You Should See
Your goal state should be:

```
Platform configurations:

✅ Web
    - Redirect URIs:
      http://localhost:8081/auth
      
❌ SPA (should NOT have http://localhost:8081/auth)
```

### Step 3: If you see SPA has the URI
1. Click on **SPA** section
2. Find `http://localhost:8081/auth` in the Redirect URIs
3. Click the **trash/delete icon** next to it
4. Click **Save**
5. Wait 30 seconds

### Step 4: If Web platform doesn't have the URI
1. Click on **Web** section (or **Add a platform** → **Web** if it doesn't exist)
2. Under "Redirect URIs", click **"Add URI"**
3. Paste: `http://localhost:8081/auth`
4. Click **Save**
5. Wait 30 seconds

### Step 5: Verify Save Completed
After clicking Save, you should see:
- ✅ No error message
- ✅ Green checkmarks or confirmation
- ✅ URI appears in the list

## 🔄 After Azure AD Changes

Once you've fixed Azure AD, run these commands:

```bash
# Restart frontend
pkill -f "expo start" || true
sleep 2
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
npm start -- --port 8081
```

Then:
1. Open `http://localhost:8081`
2. Open F12 Console
3. Click "Login with Microsoft" 
4. Complete login
5. Share console output

## 🚨 Common Mistakes

| Mistake | Fix |
|---------|-----|
| URI registered on both Web AND SPA | Remove from SPA, keep only on Web |
| Typo in URI (missing slash, extra char) | Copy-paste exactly: `http://localhost:8081/auth` |
| Forgot to click Save | Verify you see confirmation before closing |
| Using https instead of http for localhost | Use `http://` for development |
| Different port than 8081 | Make sure it's exactly 8081 |

## 📋 What to Report Back

After you fix Azure AD, tell me:
```
✅ Or ❌ Did Web platform now have http://localhost:8081/auth?
✅ Or ❌ Did you remove it from SPA platform?
✅ Or ❌ Did you click Save and see no error?
```

Then try logging in again and share the console logs.

## Still Getting 400?

If you STILL get 400 after fixing, the issue might be:
1. Azure AD hasn't refreshed (try closing browser, wait 1 min, try again)
2. Token endpoint receiving different redirect_uri than authorization endpoint
3. App registration cached - try refreshing Azure portal page (F5)
