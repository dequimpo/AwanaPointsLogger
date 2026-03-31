# Backend API Documentation - Awana Points Logger

**Version:** 1.0.0  
**Framework:** FastAPI 0.104.1  
**Base URL (Production):** `https://awanapointslogger.onrender.com`  
**Base URL (Local):** `http://localhost:8000`

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Examples](#examples)

---

## API Overview

### Purpose

The backend API serves as the middleware between the React Native frontend and Microsoft SharePoint. It:

1. **Authenticates users** via Microsoft Entra ID OAuth
2. **Manages tokens** and session state
3. **Reads/writes** student points to SharePoint XLSX
4. **Syncs data** across mobile and web clients
5. **Provides health checks** for monitoring

### Architecture

```
┌─────────────────┐
│  React Native   │
│   Frontend      │
└────────┬────────┘
         │ HTTP/HTTPS
         │ JWT Bearer Token
         │
┌────────▼─────────────────┐
│   FastAPI Backend        │
│  (Render Container)      │
├──────────────────────────┤
│ • OAuth Token Validator  │
│ • SharePoint Adapter     │
│ • XLSX Parser/Writer     │
│ • Session Manager        │
└────────┬─────────────────┘
         │
         │ HTTPS
         │ App-only auth (MSAL)
         │
┌────────▼──────────────────┐
│  Microsoft Graph API      │
│  (SharePoint, OneDrive)   │
└────────┬──────────────────┘
         │
┌────────▼──────────────────┐
│  SharePoint Online        │
│  (XLSX Storage)           │
└───────────────────────────┘
```

### Request/Response Flow

```
1. Frontend sends:   POST /toggle
                     Authorization: Bearer <access_token>
                     { action, student, date, class }

2. Backend validates: JWT signature, exp, permissions

3. Backend reads:    GET /drive/items/.../workbook/tables/0/rows
                     Authorization: Bearer <app_token>
                     (Uses internal app auth)

4. Backend processes: Finds row, updates cells, recalculates

5. Backend writes:   PATCH /drive/items/.../workbook/tables/0/rows
                     Authorization: Bearer <app_token>

6. Frontend gets:    { newRow, updatedAt, syncStatus }
```

---

## Authentication

### OAuth 2.0 with PKCE

**Type:** Confidential Client (Backend) + Public Client (Frontend)

**Flow:**

```
Frontend:
1. Generates PKCE code_verifier & code_challenge
2. Redirects user to: https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize
   ?client_id={client_id}
   &scope=User.Read%20offline_access
   &response_type=code
   &redirect_uri=https://awanapointslogger.pages.dev/auth
   &code_challenge={code_challenge}
   
3. User signs in with Microsoft account

4. Entra ID redirects to: https://awanapointslogger.pages.dev/auth?code={auth_code}

5. Frontend calls backend: POST /auth/token
   { code, code_verifier }

Backend:
6. Validates auth code with Entra ID
7. Exchanges for access_token & refresh_token
8. Returns to frontend
9. Frontend stores tokens in SecureStore

Frontend uses: Bearer <access_token>
Example: Authorization: Bearer eyJhbGc...
```

### Token Types

#### 1. Frontend Access Token
- **Issued by:** Microsoft Entra ID
- **Used for:** Authenticate API requests from frontend
- **Scope:** `User.Read` (for user profile)
- **Expires:** 1 hour
- **Refresh:** Via refresh_token

#### 2. Backend Application Token
- **Issued by:** Microsoft Entra ID (client credentials)
- **Used for:** Backend to call Microsoft Graph API
- **Scope:** `https://graph.microsoft.com/.default` (all app permissions)
- **Type:** Client credentials flow (no user)
- **Cached:** In-memory, refetched before expiry

#### 3. Session Secret
- **Purpose:** Sign session cookies (if added)
- **Type:** HS256 JWT key
- **Format:** 32+ character random string

### Authorization

**Required:** Include `Authorization` header with all API requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Validation process:**

```
1. Extract token from Authorization: Bearer <token>
2. Decode JWT header: { alg, typ, kid }
3. Fetch public key from Entra ID using kid
4. Verify signature with public key
5. Check expiration: exp < now → reject
6. Validate claims:
   - aud (audience) = API resource ID
   - iss (issuer) = https://login.microsoftonline.com/{tenant_id}/v2.0
7. Extract user info from token claims
8. Allow request
```

---

## Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Authentication:** NOT required

**Purpose:** Monitoring, uptime checks

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2026-03-31T12:34:56Z",
  "version": "1.0.0",
  "environment": "production"
}
```

**Status Codes:**
- `200 OK` - All systems healthy
- `503 Service Unavailable` - Backend issues

---

### 2. Authentication - Token Exchange

**Endpoint:** `POST /auth/token`

**Authentication:** NOT required (client exchange)

**Purpose:** Exchange auth code for access token

**Request Body:**

```json
{
  "code": "M.R3_BAY...",
  "code_verifier": "thiswastherandomstringfrom_code_challenge"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "0.AVwA...",
  "scope": "User.Read profile openid",
  "id_token": "eyJhbGc..."
}
```

**Status Codes:**
- `200 OK` - Successfully exchanged
- `400 Bad Request` - Invalid code or verifier
- `401 Unauthorized` - Code expired
- `500 Internal Server Error` - Entra ID unavailable

**Flow:**

```
Frontend             Backend              Entra ID
   │                   │                     │
   ├─ POST /auth/token ─>
   │   code=XXX          │                    │
   │   code_verifier=YYY │                    │
   │                     ├─ POST /token ────>
   │                     │ code=XXX           │
   │                     │ client_id=ZZZ      │
   │                     │ client_secret=***  │
   │                     │ code_verifier=YYY  │
   │                     │<─────────────────┤
   │                     │  access_token    │
   │                     │  refresh_token   │
   │<─ 200 OK ──────────┤                    │
   │  { tokens }        │                    │
```

---

### 3. Points Toggle

**Endpoint:** `POST /toggle`

**Authentication:** REQUIRED (Bearer token)

**Purpose:** Toggle a student point checkbox (on/off)

**Request Body:**

```json
{
  "action": "toggle",
  "student_name": "John Doe",
  "date": "2026-03-23",
  "class": "Journey_Boys",
  "column": "Att"
}
```

**Column Names:**
- `Att` - Attendance (10 pts)
- `Bib` - Bible Brought (10 pts)
- `BA` - Book Answered (10 pts)
- `MV` - Memory Verse (10 pts)
- `Part` - Participation (10 pts)
- `B1` - Bonus BAF 1 (30 pts)
- `B2` - Bonus BAF 2 (20 pts)
- `B3` - Bonus Participation (20 pts)

**Response:**

```json
{
  "success": true,
  "student": "John Doe",
  "class": "Journey_Boys",
  "date": "2026-03-23",
  "updated_row": {
    "student_name": "John Doe",
    "Att": "☑",
    "Bib": "☐",
    "BA": "☑",
    "MV": "☐",
    "Part": "☑",
    "B1": "☐",
    "B2": "☐",
    "B3": "☑",
    "Pts": 50
  },
  "sync_time_ms": 234,
  "synchronized_at": "2026-03-31T12:34:56Z"
}
```

**Status Codes:**
- `200 OK` - Successfully toggled
- `400 Bad Request` - Invalid data (missing field, bad date)
- `401 Unauthorized` - Invalid token or expired
- `403 Forbidden` - User not authorized for this class
- `404 Not Found` - Student not found in class
- `500 Internal Server Error` - SharePoint API issue

**Flow:**

```
Frontend              Backend               SharePoint/Graph
   │                   │                        │
   ├─ POST /toggle ───>
   │  + token           │                        │
   │                    ├─ Validate JWT
   │                    │
   │                    ├─ Get app token
   │                    │                        │
   │                    ├─ GET /drive/items/... ─>
   │                    │  /tables/0/rows        │
   │                    │<─────────────────────┤
   │                    │  [ rows ]              │
   │                    │
   │                    ├─ Find row with student
   │                    ├─ Toggle column
   │                    ├─ Recalculate Pts
   │                    │
   │                    ├─ PATCH /drive/items.. ─>
   │                    │  /tables/0/rows        │
   │                    │  { updated cells }     │
   │                    │<─────────────────────┤
   │                    │  { success }           │
   │
   │<─ 200 OK ────────┤
   │ { updated_row } │
   │                  │
```

---

### 4. Get Leaderboard

**Endpoint:** `GET /leaderboard`

**Authentication:** REQUIRED (Bearer token)

**Query Parameters:**

```
?class=Journey_Boys        # Required
&date_from=2026-01-01      # Optional, default: start of season
&date_to=2026-12-31        # Optional, default: today
```

**Response:**

```json
{
  "class": "Journey_Boys",
  "date_range": {
    "from": "2026-01-01",
    "to": "2026-12-31"
  },
  "rankings": [
    {
      "rank": 1,
      "student_name": "John Doe",
      "total_points": 450,
      "sessions_attended": 12,
      "average_per_session": 37.5,
      "medal": "🥇"
    },
    {
      "rank": 2,
      "student_name": "Jane Smith",
      "total_points": 420,
      "sessions_attended": 11,
      "average_per_session": 38.2,
      "medal": "🥈"
    },
    {
      "rank": 3,
      "student_name": "Bob Johnson",
      "total_points": 380,
      "sessions_attended": 10,
      "average_per_session": 38.0,
      "medal": "🥉"
    },
    {
      "rank": 4,
      "student_name": "Alice Williams",
      "total_points": 350,
      "sessions_attended": 9,
      "average_per_session": 38.9,
      "medal": null
    }
  ],
  "total_students": 4,
  "total_sessions_recorded": 12,
  "retrieved_at": "2026-03-31T12:34:56Z"
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved
- `400 Bad Request` - Missing or invalid class parameter
- `401 Unauthorized` - Invalid token
- `404 Not Found` - Class not found
- `500 Internal Server Error` - SharePoint API issue

---

### 5. Get Student Data

**Endpoint:** `GET /student/{student_name}`

**Authentication:** REQUIRED (Bearer token)

**Path Parameters:**

```
student_name=John%20Doe    # URL encoded
```

**Query Parameters:**

```
?class=Journey_Boys        # Optional, defaults to all
&date_from=2026-01-01      # Optional
&date_to=2026-12-31        # Optional
```

**Response:**

```json
{
  "student": {
    "name": "John Doe",
    "class": "Journey_Boys",
    "sessions": [
      {
        "date": "2026-03-23",
        "attendance": true,
        "bible_brought": true,
        "book_answered": false,
        "memory_verse": true,
        "participation": false,
        "bonus_1": false,
        "bonus_2": false,
        "bonus_3": true,
        "session_points": 50
      },
      {
        "date": "2026-03-16",
        "attendance": true,
        "bible_brought": false,
        "book_answered": true,
        "memory_verse": true,
        "participation": true,
        "bonus_1": false,
        "bonus_2": false,
        "bonus_3": false,
        "session_points": 40
      }
    ],
    "totals": {
      "total_sessions": 2,
      "total_points": 90,
      "average_point_per_session": 45
    }
  }
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved
- `401 Unauthorized` - Invalid token
- `404 Not Found` - Student not found
- `500 Internal Server Error` - SharePoint API issue

---

### 6. Get All Students (for a class/date)

**Endpoint:** `GET /students`

**Authentication:** REQUIRED (Bearer token)

**Query Parameters:**

```
?class=Journey_Boys        # Required
&date=2026-03-23           # Optional, defaults to latest
```

**Response:**

```json
{
  "class": "Journey_Boys",
  "date": "2026-03-23",
  "students": [
    {
      "name": "John Doe",
      "attendance": true,
      "bible_brought": true,
      "book_answered": false,
      "memory_verse": true,
      "participation": false,
      "bonus_1": false,
      "bonus_2": false,
      "bonus_3": true,
      "session_points": 50
    },
    {
      "name": "Jane Smith",
      "attendance": true,
      "bible_brought": false,
      "book_answered": true,
      "memory_verse": true,
      "participation": true,
      "bonus_1": false,
      "bonus_2": false,
      "bonus_3": false,
      "session_points": 40
    }
  ],
  "total_students": 2,
  "retrieved_at": "2026-03-31T12:34:56Z"
}
```

---

## Data Models

### Request Models

#### ToggleRequest

```python
{
  "action": str,           # "toggle"
  "student_name": str,     # "John Doe"
  "date": str,             # "2026-03-23" (YYYY-MM-DD)
  "class": str,            # "Journey_Boys", "Journey_Girls", "Trek", "T&T", "Cubbies"
  "column": str            # "Att", "Bib", "BA", "MV", "Part", "B1", "B2", "B3"
}
```

#### TokenExchangeRequest

```python
{
  "code": str,             # From Entra ID /authorize redirect
  "code_verifier": str     # SHA256 hash of PKCE code_verifier
}
```

### Response Models

#### HealthResponse

```python
{
  "status": str,           # "healthy", "degraded", "unhealthy"
  "timestamp": str,        # ISO 8601 datetime
  "version": str,          # "1.0.0"
  "environment": str       # "production", "staging", "development"
}
```

#### StudentRow

```python
{
  "student_name": str,
  "Att": str,              # "☑" or "☐"
  "Bib": str,
  "BA": str,
  "MV": str,
  "Part": str,
  "B1": str,
  "B2": str,
  "B3": str,
  "Pts": int               # Calculated total
}
```

#### ToggleResponse

```python
{
  "success": bool,
  "student": str,
  "class": str,
  "date": str,
  "updated_row": StudentRow,
  "sync_time_ms": int,
  "synchronized_at": str   # ISO 8601
}
```

---

## Error Handling

### Error Response Format

**All errors return:**

```json
{
  "detail": "Error message"
}
```

**Extended error (with debugging):**

```json
{
  "detail": "Student not found",
  "error_code": "STUDENT_NOT_FOUND",
  "request_id": "req-12345",
  "timestamp": "2026-03-31T12:34:56Z"
}
```

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| `200` | OK | Request succeeded |
| `400` | Bad Request | Missing required field |
| `401` | Unauthorized | Token expired or invalid |
| `403` | Forbidden | User lacks permission |
| `404` | Not Found | Student/class not found |
| `500` | Internal Error | SharePoint API failure |
| `503` | Service Unavailable | Backend offline |

### Common Errors

#### Missing Authorization Header

```
Status: 401 Unauthorized
```

```json
{
  "detail": "Authorization header is required"
}
```

**Solution:** Include `Authorization: Bearer <token>`

#### Invalid Token Signature

```
Status: 401 Unauthorized
```

```json
{
  "detail": "Invalid token signature"
}
```

**Solution:** Ensure token hasn't been tampered with; re-authenticate if needed

#### Token Expired

```
Status: 401 Unauthorized
```

```json
{
  "detail": "Token has expired"
}
```

**Solution:** Call `POST /auth/token` with refresh_token to get new access_token

#### SharePoint Not Available

```
Status: 500 Internal Server Error
```

```json
{
  "detail": "SharePoint API returned: 503 Service Unavailable"
}
```

**Solution:** Check SharePoint status; retry after a delay

---

## Examples

### Example 1: Full Toggle Flow (cURL)

```bash
#!/bin/bash

# 1. Get access token from frontend (simulated)
ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 2. Toggle attendance for John Doe
curl -X POST "https://awanapointslogger.onrender.com/toggle" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "toggle",
    "student_name": "John Doe",
    "date": "2026-03-23",
    "class": "Journey_Boys",
    "column": "Att"
  }'

# Response:
# {
#   "success": true,
#   "student": "John Doe",
#   "class": "Journey_Boys",
#   "date": "2026-03-23",
#   "updated_row": {
#     "student_name": "John Doe",
#     "Att": "☑",
#     "Pts": 50
#   },
#   "synchronized_at": "2026-03-31T12:34:56Z"
# }
```

### Example 2: Get Leaderboard (cURL)

```bash
#!/bin/bash

ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET "https://awanapointslogger.onrender.com/leaderboard?class=Journey_Boys" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Response:
# {
#   "class": "Journey_Boys",
#   "rankings": [
#     {
#       "rank": 1,
#       "student_name": "John Doe",
#       "total_points": 450,
#       "medal": "🥇"
#     },
#     ...
#   ]
# }
```

### Example 3: Health Check (JavaScript)

```javascript
// Check backend availability
async function checkBackendHealth() {
  try {
    const response = await fetch('https://awanapointslogger.onrender.com/health');
    const data = await response.json();
    
    if (response.ok && data.status === 'healthy') {
      console.log('✅ Backend is healthy');
      return true;
    } else {
      console.warn('⚠️ Backend degraded:', data.status);
      return false;
    }
  } catch (error) {
    console.error('❌ Backend unreachable:', error);
    return false;
  }
}
```

### Example 4: Error Handling (JavaScript)

```javascript
async function togglePointsWithErrorHandling(action) {
  const token = await getAccessToken();
  
  try {
    const response = await fetch('https://awanapointslogger.onrender.com/toggle', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        action: 'toggle',
        student_name: 'John Doe',
        date: '2026-03-23',
        class: 'Journey_Boys',
        column: 'Att'
      })
    });
    
    if (response.status === 401) {
      // Token expired, refresh and retry
      await refreshToken();
      return togglePointsWithErrorHandling(action);
    }
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Toggle failed:', error.message);
    showErrorAlert(error.message);
  }
}
```

---

## Rate Limiting & Performance

### Current Limits (Subject to Change)

- No explicit rate limit per se, but SharePoint has:
  - 2000 requests per minute per app/user
  - Batch size limit of 100 rows per request

### Caching Strategy

**Currently:** No caching layer
**Recommended for future:**
- Cache leaderboard rankings for 5 minutes
- Cache student data for 1 minute
- Cache health check as-is (already fast)

### Performance Tips

```javascript
// ✅ GOOD: Batch multiple toggles
Promise.all([
  toggle(student1),
  toggle(student2),
  toggle(student3)
]).then(() => refreshLeaderboard());

// ❌ BAD: Sequential requests (3x slower)
await toggle(student1);
await toggle(student2);
await toggle(student3);
```

---

## Future Enhancements

- [ ] WebSocket support for real-time sync
- [ ] Batch toggle endpoint
- [ ] Export to PDF/CSV
- [ ] Historical data API
- [ ] Analytics/reporting endpoints
- [ ] Admin endpoints (manage classes, students)
- [ ] Role-based access control (RBAC)

---

**API Version:** 1.0.0  
**Last Updated:** March 31, 2026  
**Maintain this: Update on new endpoints or breaking changes**
