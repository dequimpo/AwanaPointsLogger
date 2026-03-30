# Production Readiness Issues - Authentication & Security

Based on the authentication error you're experiencing and preparing for production, here are critical issues to address:

---

## 🔴 CRITICAL ISSUES (Fix Before Production)

### 1. **Redirect URI Must Be HTTPS in Production**

**Current Setup:**
- Dev: `http://localhost:8081/auth` ✅ (OK for dev)
- Production: Must be HTTPS

**Action Required:**
```bash
# In Azure AD App Registration, add production redirect URI:
https://yourdomain.com/auth        # For web
https://yourdomain.com/auth/mobile # For mobile (if applicable)
```

**Code Impact:**
Update `config/appConfig.js`:
```javascript
export const appConfig = {
  apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || 
    (process.env.NODE_ENV === 'production' 
      ? 'https://api.yourdomain.com' 
      : 'http://localhost:8000'),
  // ... rest
};
```

---

### 2. **Client Secret Should NOT Be in Frontend**

**Current Status:** ✅ GOOD - Using backend-only secret exchange

**Keep It This Way:**
- Frontend exchanges auth code for token ✅ (correct)
- Frontend sends token to backend ✅ (correct)
- Backend verifies with Graph ✅ (correct)
- Backend creates session token ✅ (correct)

**Never do this:**
```javascript
// ❌ WRONG - Don't put client secret in frontend
const clientSecret = "4y58Q~hUUJ...";  // NEVER IN FRONTEND!
```

---

### 3. **Environment Variables Must Be Secure**

**Current Issues:**
- `SESSION_SECRET` is visible in git history
- `AZURE_CLIENT_SECRET` could be exposed

**Production Fixes:**

For **Backend:**
```bash
# Never commit .env file
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore

# Use environment-specific secrets:
# Development: .env.development (gitignored)
# Production: Set via Docker/Kubernetes/Environment
```

For **Frontend:**
```bash
# Don't expose sensitive values
# Only use public values prefixed with EXPO_PUBLIC_
# Development: .env.local (gitignored)
# Production: Set via build process
```

---

### 4. **CORS Must Be Restrictive in Production**

**Current Setup:**
```python
allowed_origins = [
    "http://localhost:8081",
    "http://localhost:3000",
    ...
]
```

**Production Fix:**
```python
# backend/main.py
allowed_origins = [
    "http://localhost:8081" if IS_PRODUCTION is False else None,
    "http://localhost:3000" if IS_PRODUCTION is False else None,
    "https://yourdomain.com" if IS_PRODUCTION else None,
]

# Remove None values
allowed_origins = [o for o in allowed_origins if o]

# Validate
if not allowed_origins and IS_PRODUCTION:
    raise RuntimeError("No CORS origins configured for production!")
```

---

## 🟡 HIGH PRIORITY (Fix For Production)

### 5. **Token Expiration & Refresh**

**Current Issues:**
- No token refresh implemented
- Session tokens expire after SESSION_TTL_HOURS
- No refresh token handling

**Production Fix:**
```python
# backend/main.py - Add refresh token support
class TokenRefreshRequest(BaseModel):
    refresh_token: str

@app.post("/auth/refresh")
async def refresh_token(request: TokenRefreshRequest):
    """Refresh an expired session token using refresh grant."""
    # Implement refresh logic
    pass
```

**Frontend:**
```javascript
// services/authService.js - Check if token needs refresh
async getAccessToken() {
  if (this.isTokenNearExpiry()) {
    await this.refreshToken();
  }
  return this.accessToken;
}

isTokenNearExpiry() {
  const threshold = 5 * 60 * 1000; // 5 min
  return this.tokenExpiresAt - Date.now() < threshold;
}
```

---

### 6. **Error Handling Must Be User-Friendly**

**Current Issues:**
```python
# Returns confusing error if token exchange fails
raise HTTPException(
    status_code=401,
    detail="Unable to verify identity: Graph /me call failed or returned no user",
)
```

**Production Fix:**
```python
# Map Azure errors to user-friendly messages
AZURE_ERROR_MESSAGES = {
    "invalid_grant": "Your login expired. Please sign in again.",
    "AADSTS65001": "Please accept the permission request to continue.",
    "invalid_client": "Configuration error. Please contact support.",
    "invalid_scope": "Permission denied. Please contact support.",
}

@app.post("/auth/token")
async def authenticate_user(token_request: TokenRequest):
    try:
        graph_user = await fetch_signed_in_user(token_request.access_token)
        if not graph_user or "id" not in graph_user:
            # Check if there's a specific Azure error
            raise HTTPException(
                status_code=401,
                detail="Unable to verify identity. Please sign in again.",
            )
        # ... rest
    except Exception as e:
        # Log full error for debugging
        logger.error(f"Auth error: {str(e)}")
        
        # Return safe error to client
        raise HTTPException(
            status_code=400,
            detail="Authentication failed. Please try again.",
        )
```

---

### 7. **Logging Must Not Expose Secrets**

**Current Issues:** (With debug logging added)
```python
print(f"🔱 Token first 50 chars: {access_token[:50]}...")
# ⚠️  Logs token content!
```

**Production Fix:**
```python
# Safely log tokens
def safe_token_string(token: str, show_chars: int = 20) -> str:
    """Return first N chars + hash for identification."""
    if not token:
        return "NONE"
    return f"{token[:show_chars]}...{hash(token) % 10000}"

# Usage:
print(f"Token: {safe_token_string(token)}")
# Output: Token: eyJhbGciOiJIUzI1NiI...7382
```

**Also:**
- Never log `AZURE_CLIENT_SECRET` or `SESSION_SECRET`
- Use structured logging (JSON format) in production
- Rotate and review logs regularly

---

### 8. **Status Codes and Headers Matter**

**Current Issues:**
```python
# Generic 400 for all auth failures
raise HTTPException(status_code=400, detail=str(e))
```

**Production Fix:**
```python
# Use correct status codes
# 400 = Bad request (malformed request)
# 401 = Unauthorized (invalid credentials)
# 403 = Forbidden (valid user, not allowed)
# 500 = Server error

@app.post("/auth/token")
async def authenticate_user(token_request: TokenRequest):
    try:
        # ... auth logic
        if not graph_user:
            return JSONResponse(
                status_code=401,  # Unauthorized
                content={"detail": "Invalid or expired token"},
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,  # Internal server error
            content={"detail": "An unexpected error occurred"},
        )
```

---

## 🟢 MEDIUM PRIORITY (Improvements)

### 9. **Rate Limiting on Auth Endpoints**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/token")
@limiter.limit("10/minute")  # Max 10 auth attempts per minute
async def authenticate_user(token_request: TokenRequest):
    # ... implementation
```

---

### 10. **Audit Logging**

```python
import logging

# Setup audit logger
audit_logger = logging.getLogger('audit')

@app.post("/auth/token")
async def authenticate_user(token_request: TokenRequest):
    try:
        # ... auth
        audit_logger.info(
            f"User login successful: {user.email}",
            extra={
                "event": "login_success",
                "user_id": user.oid,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except Exception as e:
        audit_logger.warning(
            f"Login failed: {str(e)}",
            extra={
                "event": "login_failure",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        raise
```

---

### 11. **HTTPS Everywhere**

**Production deployment must enforce HTTPS:**

```python
# backend/main.py

if IS_PRODUCTION:
    @app.middleware("http")
    async def https_redirect(request, call_next):
        if request.url.scheme == "http":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=url, status_code=307)
        return await call_next(request)
```

---

### 12. **Content Security Policy Headers**

```python
# Already added in current code - keep it!
response.headers["Content-Security-Policy"] = \
    "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"

# For production, make stricter:
if IS_PRODUCTION:
    response.headers["Content-Security-Policy"] = \
        "default-src 'self'; style-src 'self'; script-src 'self'; " \
        "connect-src 'self' https://graph.microsoft.com"
```

---

## 🔍 Checklist for Production Deployment

Before deploying to production:

- [ ] All redirect URIs are HTTPS
- [ ] Client secret is NEVER in frontend code
- [ ] Environment variables are injected securely (not in code)
- [ ] CORS whitelist is restrictive (specific domains only)
- [ ] Error messages don't expose sensitive info
- [ ] Token expiration is implemented
- [ ] Refresh token logic is implemented
- [ ] Logging doesn't expose secrets
- [ ] Rate limiting is enabled on auth endpoints
- [ ] Audit logging is enabled
- [ ] HTTPS is enforced
- [ ] Security headers are correct
- [ ] .env files are gitignored
- [ ] TLS certificate is valid
- [ ] API keys are rotated regularly
- [ ] Backend uses HTTPS to call Microsoft Graph
- [ ] No console.error() exposes sensitive data in production

---

## Deployment Checklist

### Environment Variables (Must be set, never in code)

**Backend (.env or secrets manager):**
```
AZURE_CLIENT_ID=<value>
AZURE_CLIENT_SECRET=<value>
AZURE_TENANT_ID=<value>
SESSION_SECRET=<60+ char random string>
ENVIRONMENT=production
ALLOWED_ORIGINS=https://yourdomain.com
```

**Frontend (build-time or runtime):**
```
EXPO_PUBLIC_AZURE_CLIENT_ID=<value>
EXPO_PUBLIC_AZURE_TENANT_ID=<value>
EXPO_PUBLIC_API_BASE_URL=https://api.yourdomain.com
```

---

## Current vs Production-Ready

| Item | Current | Production-Ready |
|------|---------|---|
| Redirect URI | http://localhost:8081 | https://yourdomain.com |
| Client Secret Location | Backend ✅ | Backend ✅ |
| CORS Configuration | Wide open | Specific domains only |
| Error Messages | Technical | User-friendly |
| Logging | Verbose debug logs | Structured, no secrets |
| Token Refresh | Not implemented | Implemented |
| Rate Limiting | No | Yes |
| Audit Logging | No | Yes |
| HTTPS | Dev only | Enforced |
| Security Headers | Basic | Comprehensive |

---

See [AUTHENTICATION_DEBUGGING_CHECKLIST.md](./AUTHENTICATION_DEBUGGING_CHECKLIST.md) for debugging the current auth error first. Then use this guide to prepare for production.
