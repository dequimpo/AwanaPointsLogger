"""
DQ03252026: FastAPI backend for Awana Points Logger
Handles Microsoft 365 SharePoint XLSX authentication and data sync
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from typing import Optional
import httpx
import jwt
import msal
import json
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv
from jwt import PyJWTError

# Load environment variables from .env file - specify the path explicitly
import os.path
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    print(f"🔍 Loading backend environment from: {env_path}")
    load_dotenv(env_path, override=True)
else:
    print("ℹ️ No backend .env found; relying on environment variables")

app = FastAPI(title="Awana Points Logger API")

# Determine environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# CORS configuration - restrict to specific origins in production
allowed_origins = [
    "http://localhost:8081",      # Local development
    "http://localhost:3000",       # Alternative local dev
    "http://127.0.0.1:8081",
    "http://127.0.0.1:3000",
]

# Add production origins if configured
PRODUCTION_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
if PRODUCTION_ORIGINS and PRODUCTION_ORIGINS[0]:
    allowed_origins.extend([origin.strip() for origin in PRODUCTION_ORIGINS if origin.strip()])

# In production, never allow "*"
if IS_PRODUCTION and "*" in allowed_origins:
    allowed_origins.remove("*")

print(f"🔒 Environment: {ENVIRONMENT}")
print(f"📍 Allowed CORS Origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains" if IS_PRODUCTION else "max-age=86400"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # CORS headers (redundant with middleware but explicit)
    origin = request.headers.get("origin")
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    
    return response

# Configuration - Store these in environment variables or .env file
config = {
    "client_id": os.getenv("AZURE_CLIENT_ID", "YOUR_CLIENT_ID"),
    "client_secret": os.getenv("AZURE_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
    "tenant_id": os.getenv("AZURE_TENANT_ID", "YOUR_TENANT_ID"),
    "site_id": os.getenv("SHAREPOINT_SITE_ID", "YOUR_SITE_ID"),
    "drive_id": os.getenv("SHAREPOINT_DRIVE_ID", "YOUR_DRIVE_ID"),
    "file_id": os.getenv("SHAREPOINT_FILE_ID", "YOUR_FILE_ID"),
    "session_secret": os.getenv("SESSION_SECRET", "development-session-secret"),
}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Group access controls for app authorization.
# - ALLOWED_GROUP_ID: preferred, immutable Entra object ID for the group.
# - ALLOWED_GROUP_NAME: fallback display name match (default requested by user).
# - ENFORCE_GROUP_MEMBERSHIP: when true, non-members are denied at /auth/token.
# - FAIL_OPEN_ON_GROUP_CHECK_ERROR: when true, transient Graph permission/errors won't block sign-in.
ALLOWED_GROUP_ID = os.getenv("ALLOWED_GROUP_ID", "").strip()
ALLOWED_GROUP_NAME = os.getenv("ALLOWED_GROUP_NAME", "AwanaPointsLogger").strip()
ENFORCE_GROUP_MEMBERSHIP = _env_bool("ENFORCE_GROUP_MEMBERSHIP", True)
FAIL_OPEN_ON_GROUP_CHECK_ERROR = _env_bool("FAIL_OPEN_ON_GROUP_CHECK_ERROR", True)
ENFORCE_SHAREPOINT_ACCESS = _env_bool("ENFORCE_SHAREPOINT_ACCESS", True)

# Validate that environment variables are loaded
if config["tenant_id"] == "YOUR_TENANT_ID":
    print("❌ ERROR: AZURE_TENANT_ID not loaded from .env file!")
    print("   Make sure .env file exists in backend/ directory")
    print(f"   Looking for: {env_path}")
else:
    print("✅ Azure tenant configuration detected")

# Authority URL for MSAL
AUTHORITY = f"https://login.microsoftonline.com/{config['tenant_id']}"
GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "8"))
SESSION_AUDIENCE = "awana-points-logger-client"
SESSION_ISSUER = "awana-points-logger-api"
bearer_scheme = HTTPBearer(auto_error=False)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Ensure CORS headers are present on all unhandled 500 errors."""
    from fastapi.responses import JSONResponse
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers,
    )


if IS_PRODUCTION and config["session_secret"] == "development-session-secret":
    raise RuntimeError("SESSION_SECRET must be set in production")


class TokenRequest(BaseModel):
    access_token: str


class AuthUser(BaseModel):
    oid: Optional[str] = None
    display_name: str
    email: Optional[str] = None
    tenant_id: Optional[str] = None


class StudentUpdate(BaseModel):
    date: str  # Format: "M/D/YYYY"
    class_name: str  # "Journey_Boys", "Journey_Girls", "Trek", "T&T", or "Cubbies"
    student_name: str
    student_id: Optional[str] = None
    attendance: Optional[int] = None  # 1 or 0/null
    bible: Optional[int] = None
    book_answered: Optional[int] = None
    memory_verse: Optional[int] = None
    participation: Optional[int] = None
    bonus1_baf_1: Optional[int] = None
    bonus2_baf_2: Optional[int] = None
    bonus3_participation: Optional[int] = None
    total_points: Optional[int] = None


class AutoPopulateRequest(BaseModel):
    date: str  # Format: "M/D/YYYY"
    class_name: str  # "Journey_Boys", "Journey_Girls", "Trek", "T&T", or "Cubbies"


class BootstrapRequest(BaseModel):
    date: str  # Format: YYYY-MM-DD (internal)
    class_name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: AuthUser


def get_msal_app():
    """Initialize MSAL application for server-side auth"""
    return msal.ConfidentialClientApplication(
        config["client_id"],
        authority=AUTHORITY,
        client_credential=config["client_secret"],
    )


async def get_graph_access_token() -> str:
    """Get app access token for Microsoft Graph."""
    app = get_msal_app()
    result = app.acquire_token_for_client(scopes=GRAPH_SCOPE) or {}
    
    if "access_token" in result:
        return result["access_token"]
    else:
        raise HTTPException(status_code=401, detail="Failed to acquire access token")


def create_session_token(user: AuthUser) -> tuple[str, int]:
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    payload = {
        "sub": user.oid or user.email or user.display_name,
        "name": user.display_name,
        "email": user.email,
        "oid": user.oid,
        "tid": user.tenant_id,
        "iss": SESSION_ISSUER,
        "aud": SESSION_AUDIENCE,
        "iat": datetime.utcnow(),
        "exp": expires_at,
    }
    token = jwt.encode(payload, config["session_secret"], algorithm="HS256")
    return token, SESSION_TTL_HOURS * 3600


def require_authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            config["session_secret"],
            algorithms=["HS256"],
            audience=SESSION_AUDIENCE,
            issuer=SESSION_ISSUER,
        )
        return payload
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        ) from exc


def build_auth_user(result: dict) -> AuthUser:
    claims = result.get("id_token_claims") or {}
    if not claims and result.get("id_token"):
        try:
            claims = jwt.decode(
                result["id_token"],
                options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
            )
        except PyJWTError:
            claims = {}
    return AuthUser(
        oid=claims.get("oid"),
        display_name=claims.get("name") or claims.get("preferred_username") or "User",
        email=claims.get("preferred_username") or claims.get("email"),
        tenant_id=claims.get("tid"),
    )


async def fetch_signed_in_user(access_token: str) -> dict:
    print(f"🔐 [Graph] Fetching user profile with Graph /me")
    print(f"🔐 [Graph] Token length: {len(access_token) if access_token else 0}")
    print(f"🔐 [Graph] Token first 50 chars: {access_token[:50] if access_token else 'NONE'}...")
    print(f"🔐 [Graph] Token parts: {len(access_token.split('.')) if access_token else 0}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me?$select=id,displayName,userPrincipalName,mail",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            print(f"📊 [Graph] Response status: {response.status_code}")
            print(f"📊 [Graph] Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                print(f"❌ [Graph] Graph API error!")
                print(f"❌ [Graph] Status code: {response.status_code}")
                print(f"❌ [Graph] Response body: {response.text}")
                print(f"❌ [Graph] Request headers: Authorization: Bearer {access_token[:50]}...")
                return {}
            
            result = response.json()
            print(f"✅ [Graph] Successfully fetched user: {result.get('displayName')}")
            return result
            
        except Exception as e:
            print(f"❌ [Graph] Exception during Graph API call: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}


async def check_membership_by_group_id(access_token: str, group_id: str) -> bool:
    """Check if signed-in user is a member of specific group id via /me/checkMemberGroups."""
    if not group_id:
        return False

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://graph.microsoft.com/v1.0/me/checkMemberGroups",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"groupIds": [group_id]},
        )

        if response.status_code != 200:
            raise RuntimeError(f"checkMemberGroups failed ({response.status_code}): {response.text}")

        data = response.json() if response.content else {}
        matched_ids = data.get("value") or []
        return group_id in matched_ids


async def check_membership_by_group_name(access_token: str, group_name: str) -> bool:
    """Check user membership by scanning transitive groups for a display name match."""
    if not group_name:
        return False

    target = group_name.casefold()
    url = "https://graph.microsoft.com/v1.0/me/transitiveMemberOf/microsoft.graph.group?$select=id,displayName&$top=999"

    async with httpx.AsyncClient(timeout=30.0) as client:
        while url:
            response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
            if response.status_code != 200:
                raise RuntimeError(f"transitiveMemberOf failed ({response.status_code}): {response.text}")

            payload = response.json() if response.content else {}
            groups = payload.get("value") or []
            for grp in groups:
                name = str(grp.get("displayName") or "").strip()
                if name and name.casefold() == target:
                    return True

            url = payload.get("@odata.nextLink")

    return False


async def check_user_sharepoint_file_access(access_token: str) -> bool:
    """Return true when the signed-in user can read the configured SharePoint workbook."""
    if not config["drive_id"] or not config["file_id"]:
        raise RuntimeError("SHAREPOINT_DRIVE_ID and SHAREPOINT_FILE_ID must be configured")

    file_url = (
        f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
        f"/items/{config['file_id']}?$select=id,name,webUrl,parentReference"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(file_url, headers={"Authorization": f"Bearer {access_token}"})

    if response.status_code == 200:
        data = response.json() if response.content else {}
        print(f"✅ [AuthZ] SharePoint file access confirmed: {data.get('name')}")
        return True

    if response.status_code in {401, 403, 404}:
        print(f"❌ [AuthZ] SharePoint file access denied ({response.status_code}): {response.text}")
        return False

    raise RuntimeError(f"sharepoint_file_access_check_failed ({response.status_code}): {response.text}")


async def ensure_user_is_authorized(access_token: str, user: dict) -> None:
    """Authorize app usage using SharePoint access first, then optional group rules."""
    if ENFORCE_SHAREPOINT_ACCESS:
        try:
            if await check_user_sharepoint_file_access(access_token):
                return
            print("ℹ️ [AuthZ] SharePoint file access not confirmed; evaluating group fallback rules")
        except Exception as exc:
            if FAIL_OPEN_ON_GROUP_CHECK_ERROR:
                print(f"⚠️ [AuthZ] SharePoint access check errored; continuing to fallback auth checks: {exc}")
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unable to verify SharePoint access for this user.",
                ) from exc

    await ensure_user_group_access(access_token, user)


async def ensure_user_group_access(access_token: str, user: dict) -> None:
    """Authorize app usage based on configured group controls."""
    if not ENFORCE_GROUP_MEMBERSHIP:
        print("ℹ️ [AuthZ] Group enforcement disabled; allowing authenticated user")
        return

    checks_attempted = 0
    check_errors = []

    if ALLOWED_GROUP_ID:
        checks_attempted += 1
        try:
            if await check_membership_by_group_id(access_token, ALLOWED_GROUP_ID):
                print(f"✅ [AuthZ] User is member of allowed group ID {ALLOWED_GROUP_ID}")
                return
            print(f"❌ [AuthZ] User is not member of allowed group ID {ALLOWED_GROUP_ID}")
        except Exception as exc:
            check_errors.append(f"group_id_check_error={str(exc)}")

    if ALLOWED_GROUP_NAME:
        checks_attempted += 1
        try:
            if await check_membership_by_group_name(access_token, ALLOWED_GROUP_NAME):
                print(f"✅ [AuthZ] User is member of allowed group name '{ALLOWED_GROUP_NAME}'")
                return
            print(f"❌ [AuthZ] User is not member of allowed group name '{ALLOWED_GROUP_NAME}'")
        except Exception as exc:
            check_errors.append(f"group_name_check_error={str(exc)}")

    if check_errors and FAIL_OPEN_ON_GROUP_CHECK_ERROR:
        print("⚠️ [AuthZ] Group check errored; FAIL_OPEN enabled. Allowing sign-in.")
        for err in check_errors:
            print(f"⚠️ [AuthZ] {err}")
        return

    if checks_attempted == 0:
        print("⚠️ [AuthZ] No group configured; allowing authenticated user")
        return

    user_name = user.get("displayName") or user.get("userPrincipalName") or "User"
    target_group = ALLOWED_GROUP_NAME or ALLOWED_GROUP_ID
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied for {user_name}: membership in '{target_group}' is required.",
    )


    


def _is_students_header_row(row: list) -> bool:
    if not row or len(row) < 2:
        return False
    first = str(row[0]).strip().lower()
    second = str(row[1]).strip().lower()
    return first in {"studentid", "student id", "id"} and second == "name"


def _students_data_rows(rows: list) -> list:
    if rows and _is_students_header_row(rows[0]):
        return rows[1:]
    return rows


async def fetch_students_used_rows(client: httpx.AsyncClient, headers: dict) -> list:
    """Fetch only populated rows from Students sheet using workbook usedRange."""
    students_url = (
        f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
        f"/items/{config['file_id']}/workbook/worksheets('Students')/usedRange(valuesOnly=true)"
    )

    students_response = await client.get(students_url, headers=headers)
    if students_response.status_code == 404:
        raise HTTPException(status_code=404, detail="Students sheet not found")
    if students_response.status_code != 200:
        raise HTTPException(
            status_code=students_response.status_code,
            detail=f"Graph API error fetching Students: {students_response.text}",
        )

    students_data = students_response.json()
    rows = students_data.get("values") or []
    if not isinstance(rows, list):
        rows = []

    cleaned_rows = []
    for row in rows:
        if not isinstance(row, list):
            continue
        # Keep only Students columns and skip fully empty records.
        trimmed = row[:3]
        if not any(str(cell).strip() for cell in trimmed):
            continue
        while len(trimmed) < 3:
            trimmed.append("")
        cleaned_rows.append(trimmed)

    return cleaned_rows


async def fetch_pointslog_used_rows(client: httpx.AsyncClient, headers: dict) -> list:
    """Fetch only populated rows from PointsLog sheet using workbook usedRange."""
    pointslog_url = (
        f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
        f"/items/{config['file_id']}/workbook/worksheets('PointsLog')/usedRange(valuesOnly=true)"
    )

    response = await client.get(pointslog_url, headers=headers)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="PointsLog sheet not found")
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Graph API error fetching PointsLog: {response.text}",
        )

    data = response.json()
    rows = data.get("values") or []
    if not isinstance(rows, list):
        return []

    cleaned_rows = []
    for row in rows:
        if not isinstance(row, list):
            continue
        if not any(str(cell).strip() for cell in row):
            continue
        cleaned_rows.append(row)

    return cleaned_rows


def _normalize_sheet_date(value) -> str:
    """Normalize Excel/ISO/string dates to M/D/YYYY for reliable comparisons."""
    if value is None:
        return ""

    # Excel serial date support (e.g., 45678)
    if isinstance(value, (int, float)):
        dt = datetime.utcfromtimestamp((float(value) - 25569) * 86400)
        return f"{dt.month}/{dt.day}/{dt.year}"

    text = str(value).strip()
    if not text:
        return ""

    # If already in M/D/YYYY format, keep as-is after int normalization
    if "/" in text:
        parts = text.split("/")
        if len(parts) == 3:
            try:
                month = int(parts[0])
                day = int(parts[1])
                year = int(parts[2])
                return f"{month}/{day}/{year}"
            except ValueError:
                pass

    # Common ISO forms: YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss
    iso_text = text.split("T")[0]
    if "-" in iso_text:
        parts = iso_text.split("-")
        if len(parts) == 3:
            try:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                return f"{month}/{day}/{year}"
            except ValueError:
                pass

    return text


def normalize_date_str(value) -> str:
    """Normalize date inputs (Excel serial, M/D/YYYY, ISO) into YYYY-MM-DD."""
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        base_date = date(1899, 12, 30)
        return (base_date + timedelta(days=int(value))).strftime("%Y-%m-%d")

    text = str(value).strip()
    if not text:
        return ""

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text).strftime("%Y-%m-%d")
    except ValueError:
        return text


def safe_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def calculate_total_points_from_row_values(values: list) -> int:
    """Calculate TotalPoints using D:K values [Att, Bible, BA, MV, Part, B1, B2, B3]."""
    if not isinstance(values, list):
        return 0

    # Base fields: D-H are 10 points each when ON.
    att = safe_int(values[0] if len(values) > 0 else 0)
    bible = safe_int(values[1] if len(values) > 1 else 0)
    ba = safe_int(values[2] if len(values) > 2 else 0)
    mv = safe_int(values[3] if len(values) > 3 else 0)
    part = safe_int(values[4] if len(values) > 4 else 0)

    # Bonus fields: I=30, J=20, K=20 when ON.
    b1 = safe_int(values[5] if len(values) > 5 else 0)
    b2 = safe_int(values[6] if len(values) > 6 else 0)
    b3 = safe_int(values[7] if len(values) > 7 else 0)

    return ((att + bible + ba + mv + part) * 10) + (b1 * 30) + (b2 * 20) + (b3 * 20)


def apply_update_to_score_values(values: list, update: StudentUpdate) -> list:
    """Overlay an incoming checkbox update onto D:K score values."""
    score_values = list(values[:8]) if isinstance(values, list) else []
    while len(score_values) < 8:
        score_values.append(0)

    field_updates = {
        0: update.attendance,
        1: update.bible,
        2: update.book_answered,
        3: update.memory_verse,
        4: update.participation,
        5: update.bonus1_baf_1,
        6: update.bonus2_baf_2,
        7: update.bonus3_participation,
    }

    for idx, value in field_updates.items():
        if value is not None:
            score_values[idx] = safe_int(value, 0)

    return score_values


async def fetch_students_roster(client: httpx.AsyncClient, headers: dict) -> list:
    """Read Students sheet as source of truth: returns {student_id, student_name, class_name}."""
    students_rows = _students_data_rows(await fetch_students_used_rows(client, headers))

    roster = []
    for row in students_rows:
        if not isinstance(row, list) or len(row) < 3:
            continue
        student_id = str(row[0]).strip()
        student_name = str(row[1]).strip()
        class_name = str(row[2]).strip()
        if student_id and student_name and class_name:
            roster.append(
                {
                    "student_id": student_id,
                    "student_name": student_name,
                    "class_name": class_name,
                }
            )

    return roster


async def fetch_pointslog_rows(client: httpx.AsyncClient, headers: dict) -> list:
    """Fetch existing PointsLog rows from used range."""
    return await fetch_pointslog_used_rows(client, headers)


def find_pointslog_row_index(rows: list, date_value: str, student_id: str, class_name: str) -> Optional[int]:
    """Return Excel row index (1-based), or None if not found."""
    target_date = normalize_date_str(date_value)
    target_student_id = str(student_id).strip()
    target_class = str(class_name).strip()

    for idx, row in enumerate(rows[1:], start=2):
        if len(row) < 3:
            continue

        row_date = normalize_date_str(row[0])
        row_student_id = str(row[1]).strip()
        row_class = str(row[2]).strip()

        if row_date == target_date and row_student_id == target_student_id and row_class == target_class:
            return idx

    return None


@app.post("/auth/token", response_model=AuthResponse)
async def authenticate_user(token_request: TokenRequest):
    """
    Accept a browser-issued access token, verify identity via Graph, and issue a session.
    SPA platform tokens can only be redeemed from the browser, so the frontend
    exchanges the auth code itself and sends the resulting access_token here.
    """
    try:
        print("\n" + "="*70)
        print("🔐 [AuthToken] POST /auth/token request received")
        print("="*70)
        print(f"🔐 [AuthToken] Token length: {len(token_request.access_token) if token_request.access_token else 0}")
        print(f"🔐 [AuthToken] Token first 50 chars: {token_request.access_token[:50] if token_request.access_token else 'NONE'}...")
        print(f"🔐 [AuthToken] Token parts (should be 3): {len(token_request.access_token.split('.')) if token_request.access_token else 0}")
        print(f"🔐 [AuthToken] Client ID in backend: {config['client_id'][:20]}...")
        print(f"🔐 [AuthToken] Tenant ID in backend: {config['tenant_id']}")
        
        graph_user = await fetch_signed_in_user(token_request.access_token)
        
        if not graph_user or "id" not in graph_user:
            print(f"❌ [AuthToken] Graph verification failed!")
            print(f"❌ [AuthToken] graph_user: {graph_user}")
            raise HTTPException(
                status_code=401,
                detail="Unable to verify identity: Graph /me call failed or returned no user",
            )

        print(f"✅ [AuthToken] User verified: {graph_user.get('displayName')}")
        await ensure_user_is_authorized(token_request.access_token, graph_user)
        
        user = AuthUser(
            oid=graph_user.get("id"),
            display_name=graph_user.get("displayName") or "User",
            email=graph_user.get("userPrincipalName") or graph_user.get("mail"),
            tenant_id=None,
        )

        session_token, expires_in = create_session_token(user)
        print(f"✅ [AuthToken] Session token created successfully")
        print("="*70 + "\n")
        
        return AuthResponse(
            access_token=session_token,
            token_type="Bearer",
            expires_in=expires_in,
            user=user,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [AuthToken] Exception in /auth/token: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sheets/PointsLogSheet")
async def fetch_points_sheet(
    date_value: Optional[str] = None,
    class_name: Optional[str] = None,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Fetch all data from PointsLog (normalized) with student names denormalized
    Returns data in legacy format for backward compatibility
    Format: [Date, Class, StudentName, Att, Bible, BA, MV, Part, B1, B2, B3, Total]
    """
    try:
        print("📋 Fetching PointsLogSheet (with denormalized student names)...")
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Fetch normalized PointsLog from used range only
            pointslog_rows = []
            try:
                pointslog_rows = await fetch_pointslog_used_rows(client, headers)
            except HTTPException as e:
                if e.status_code != 404:
                    raise
                print("⚠️ PointsLog sheet not found. Trying legacy PointsLogSheet...")
                legacy_url = (
                    f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                    f"/items/{config['file_id']}/workbook/worksheets('PointsLogSheet')/range(address='A1:M1000')"
                )
                response = await client.get(legacy_url, headers=headers)
                
                if response.status_code != 200:
                    raise HTTPException(status_code=404, detail="No points sheet found. Run migration: python backend/migrate_sheets.py")
                
                # Return legacy format
                data = response.json()
                rows = data.get("values") or []
                return {
                    "headers": rows[0] if rows else [],
                    "data": rows[1:] if len(rows) > 1 else [],
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "legacy",
                }
            
            # Fetch only populated Students rows for name mapping
            students_rows = _students_data_rows(await fetch_students_used_rows(client, headers))

            # Build StudentID -> Name mapping
            id_to_name = {}
            for row in students_rows:
                if len(row) >= 2:
                    student_id = row[0]
                    name = str(row[1]).strip()
                    id_to_name[student_id] = name
            
            print(f"📚 StudentID -> Name mapping: {id_to_name}")
            
            print(f"✅ Retrieved {len(pointslog_rows)} populated rows from PointsLog sheet")

            headers_row = pointslog_rows[0] if pointslog_rows else []
            data_rows = pointslog_rows[1:] if len(pointslog_rows) > 1 else []
            
            normalized_filter_date = normalize_date_str(date_value) if date_value else None

            # Denormalize: Replace StudentID with StudentName in column C
            denormalized_rows = []
            for row in data_rows:
                if len(row) >= 12:
                    normalized_row_date = normalize_date_str(row[0])
                    row_class = str(row[2]).strip()

                    if normalized_filter_date and normalized_row_date != normalized_filter_date:
                        continue
                    if class_name and row_class != class_name:
                        continue

                    student_id = row[1]
                    student_name = id_to_name.get(student_id, f"Unknown({student_id})")
                    # Reorder to: [Date, Class, StudentName, Att, Bible, BA, MV, Part, B1, B2, B3, Total]
                    denormalized_row = [
                        normalized_row_date,  # Date (normalized)
                        row_class,  # Class
                        student_name,  # Student Name (denormalized)
                        row[3],  # Attendance
                        row[4],  # Bible
                        row[5],  # BookAnswered
                        row[6],  # MemoryVerse
                        row[7],  # Participation
                        row[8],  # Bonus1_BAF1
                        row[9],  # Bonus2_BAF2
                        row[10], # Bonus3_Participation
                        row[11], # TotalPoints
                    ]
                    denormalized_rows.append(denormalized_row)
            
            print(f"✅ Raw PointsLog rows count: {len(data_rows)}")
            if len(data_rows) > 0:
                print(f"📦 First raw row (normalized): {data_rows[0]}")
                print(f"   Length: {len(data_rows[0])}")
                for i, cell in enumerate(data_rows[0][:5]):
                    print(f"   [{i}]: {repr(cell)}")
            
            print(f"✅ Denormalized rows count: {len(denormalized_rows)}")
            if len(denormalized_rows) > 0:
                print(f"📦 First denormalized row: {denormalized_rows[0]}")
                for i, cell in enumerate(denormalized_rows[0][:5]):
                    print(f"   [{i}]: {repr(cell)}")
            
            # Return in legacy format
            legacy_headers = ["Date", "Class", "StudentName", "Attendance", "Bible", 
                            "BookAnswered", "MemoryVerse", "Participation", 
                            "Bonus1_BAF1", "Bonus2_BAF2", "Bonus3_Participation", "TotalPoints"]
            
            return {
                "headers": legacy_headers,
                "data": denormalized_rows,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "normalized",
            }
    except Exception as e:
        print(f"💥 Exception in fetch_points_sheet: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.patch("/sheets/PointsLogSheet/update")
async def update_student_row(
    update: StudentUpdate,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Update a specific student row (backward compatible endpoint)
    Automatically routes to normalized PointsLog update
    """
    return await update_student_pointslog(update, access_token)


@app.post("/sheets/PointsLogSheet/bootstrap")
async def bootstrap_pointslog_sheet(
    request: BootstrapRequest,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """Ensure PointsLog contains one row per class student for the selected date."""
    try:
        normalized_date = normalize_date_str(request.date)

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            roster = await fetch_students_roster(client, headers)
            class_students = [s for s in roster if s["class_name"] == request.class_name]

            if not class_students:
                return {
                    "message": "No students found for this class",
                    "entries_created": 0,
                    "date": normalized_date,
                    "class_name": request.class_name,
                    "total_students": 0,
                }

            pointslog_rows = await fetch_pointslog_rows(client, headers)

            existing_keys = set()
            for row in pointslog_rows[1:]:
                if len(row) < 3:
                    continue
                existing_keys.add(
                    (
                        normalize_date_str(row[0]),
                        str(row[1]).strip(),
                        str(row[2]).strip(),
                    )
                )

            new_entries = []
            for student in class_students:
                key = (normalized_date, student["student_id"], request.class_name)
                if key in existing_keys:
                    continue

                new_entries.append(
                    [
                        normalized_date,
                        student["student_id"],
                        request.class_name,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                    ]
                )

            if new_entries:
                start_row = max(2, len(pointslog_rows) + 1)
                end_row = start_row + len(new_entries) - 1
                insert_url = (
                    f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                    f"/items/{config['file_id']}/workbook/worksheets('PointsLog')/range(address='A{start_row}:L{end_row}')"
                )
                insert_response = await client.patch(
                    insert_url,
                    json={"values": new_entries},
                    headers=headers,
                )
                if insert_response.status_code != 200:
                    raise HTTPException(
                        status_code=insert_response.status_code,
                        detail=f"Failed to insert bootstrap rows: {insert_response.text}",
                    )

            return {
                "message": "Bootstrap complete",
                "entries_created": len(new_entries),
                "date": normalized_date,
                "class_name": request.class_name,
                "total_students": len(class_students),
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bootstrap failed: {str(e)}")


@app.get("/sheets/classes")
async def get_class_options(user_session: dict = Depends(require_authenticated_user)):
    """Get available class options"""
    return {
        "classes": ["Journey_Boys", "Journey_Girls", "Trek", "T&T", "Cubbies"],
    }


@app.get("/sheets/Students")
async def fetch_students_sheet(
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Fetch all students from normalized 'Students' sheet
    Returns: [ {id, name, class}, ... ]
    """
    try:
        print("📋 Fetching Students sheet...")
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            try:
                rows = await fetch_students_used_rows(client, headers)
            except HTTPException as e:
                if e.status_code != 404:
                    raise
                # Students sheet doesn't exist yet - return empty list
                print("⚠️ Students sheet not found. Run migration first: python backend/migrate_sheets.py")
                return {
                    "headers": ["StudentID", "Name", "Class"],
                    "data": [],
                    "timestamp": datetime.utcnow().isoformat(),
                }

            print(f"✅ Retrieved {len(rows)} populated rows from Students sheet")

            default_headers = ["StudentID", "Name", "Class"]
            if rows and _is_students_header_row(rows[0]):
                headers_row = rows[0]
                data_rows = rows[1:]
            else:
                headers_row = default_headers
                data_rows = rows
            
            return {
                "headers": headers_row,
                "data": data_rows,
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        print(f"💥 Exception in fetch_students_sheet: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/sheets/PointsLog")
async def fetch_pointslog_sheet(
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Fetch all data from normalized 'PointsLog' sheet
    Returns normalized structure: [ [date, studentID, class, att, bible, ...], ... ]
    """
    try:
        print("📋 Fetching PointsLog sheet (normalized)...")
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            url = (
                f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                f"/items/{config['file_id']}/workbook/worksheets('PointsLog')/range(address='A1:L10000')"
            )
            
            response = await client.get(url, headers=headers)
            
            if response.status_code == 404:
                # PointsLog sheet doesn't exist - return empty
                print("⚠️ PointsLog sheet not found. Run migration first: python backend/migrate_sheets.py")
                return {
                    "headers": ["Date", "StudentID", "Class", "Attendance", "Bible", "BookAnswered", 
                               "MemoryVerse", "Participation", "Bonus1_BAF1", "Bonus2_BAF2", 
                               "Bonus3_Participation", "TotalPoints"],
                    "data": [],
                    "timestamp": datetime.utcnow().isoformat(),
                }
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Graph API error: {response.text}")
            
            data = response.json()
            rows = data.get("values", [])
            
            print(f"✅ Retrieved {len(rows)} rows from PointsLog sheet")
            
            headers_row = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            
            return {
                "headers": headers_row,
                "data": data_rows,
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        print(f"💥 Exception in fetch_pointslog_sheet: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.post("/sheets/PointsLog/auto-populate")
async def auto_populate_new_date(
    request: AutoPopulateRequest,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Auto-populate PointsLog for a new date by creating empty entries for all students of the given class
    """
    try:
        print(f"🆕 Auto-populating PointsLog for {request.date} ({request.class_name})")
        normalized_date = normalize_date_str(request.date)
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # 1. Fetch populated students only
            students_rows = _students_data_rows(await fetch_students_used_rows(client, headers))
            if not isinstance(students_rows, list):
                students_rows = []
            
            # Filter students for the given class
            class_students = []
            for row in students_rows:
                if not isinstance(row, list):
                    continue
                if len(row) >= 3 and str(row[2]).strip() == request.class_name:
                    class_students.append([row[0], row[1], row[2]])  # [StudentID, Name, Class]
            
            if not class_students:
                print(f"⚠️ No students found for class: {request.class_name}")
                return {"message": "No students found for this class", "entries_created": 0}
            
            # 2. Create entries for each student
            new_entries = []
            for student in class_students:
                student_id = student[0]
                # [Date, StudentID, Class, Attendance, Bible, BookAnswered, MemoryVerse, 
                #  Participation, Bonus1_BAF1, Bonus2_BAF2, Bonus3_Participation, TotalPoints]
                new_entries.append([
                    normalized_date,  # Date
                    student_id,    # StudentID
                    request.class_name,  # Class
                    0, 0, 0, 0, 0, 0, 0, 0, 0  # All points default to 0
                ])
            
            # 3. Append entries to PointsLog sheet
            pointslog_url = (
                f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                f"/items/{config['file_id']}/workbook/worksheets('PointsLog')/range(address='A:L')"
            )
            
            # Get current row count
            count_response = await client.get(
                pointslog_url,
                headers=headers,
            )
            if count_response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to read PointsLog: {count_response.text}")

            count_data = count_response.json() if count_response.content else {}
            count_rows = (count_data.get("values") if isinstance(count_data, dict) else []) or []
            if not isinstance(count_rows, list):
                count_rows = []
            next_row = len(count_rows) + 1

            if not new_entries:
                return {
                    "message": "No entries to create",
                    "entries_created": 0,
                    "date": normalized_date,
                    "class": request.class_name,
                }
            
            # Write new entries
            range_address = f"A{next_row}:L{next_row + len(new_entries) - 1}"
            insert_url = (
                f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                f"/items/{config['file_id']}/workbook/worksheets('PointsLog')/range(address='{range_address}')"
            )
            
            insert_response = await client.patch(
                insert_url,
                json={"values": new_entries},
                headers=headers,
            )
            
            if insert_response.status_code == 200:
                print(f"✅ Created {len(new_entries)} entries for {normalized_date}")
                return {
                    "message": f"Auto-populated {len(new_entries)} students",
                    "entries_created": len(new_entries),
                    "date": normalized_date,
                    "class": request.class_name,
                }

            raise HTTPException(status_code=400, detail=f"Failed to insert entries: {insert_response.text}")
            
    except Exception as e:
        print(f"💥 Exception in auto_populate_new_date: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.patch("/sheets/PointsLog/update")
async def update_student_pointslog(
    update: StudentUpdate,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Update a specific student's points in PointsLog sheet
    Uses normalized structure with StudentID
    """
    try:
        print(f"✏️ Updating points for {update.student_name} on {update.date}")
        normalized_date = normalize_date_str(update.date)
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            
            # 1. Use provided student_id when available; otherwise fall back to roster lookup.
            student_id = str(update.student_id).strip() if update.student_id else None
            if not student_id:
                roster = await fetch_students_roster(client, headers)

                student_id = None
                for student in roster:
                    if student["student_name"] == update.student_name and student["class_name"] == update.class_name:
                        student_id = student["student_id"]
                        break
            
            if student_id is None:
                raise HTTPException(status_code=404, detail=f"Student {update.student_name} not found")
            
            # 2. Find existing row in PointsLog
            pointslog_rows = await fetch_pointslog_rows(client, headers)
            row_index = find_pointslog_row_index(pointslog_rows, normalized_date, student_id, update.class_name)
            existing_score_values = []
            
            # 2b. Upsert: if missing, append row with defaults first
            if row_index is None:
                append_row = [
                    normalized_date,
                    str(student_id),
                    update.class_name,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ]

                existing_score_values = append_row[3:11]

                row_index = max(2, len(pointslog_rows) + 1)
                append_url = (
                    f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                    f"/items/{config['file_id']}/workbook/worksheets('PointsLog')/range(address='A{row_index}:L{row_index}')"
                )
                append_response = await client.patch(
                    append_url,
                    json={"values": [append_row]},
                    headers=headers,
                )
                if append_response.status_code != 200:
                    raise HTTPException(
                        status_code=append_response.status_code,
                        detail=f"Failed to create missing PointsLog row: {append_response.text}",
                    )
            else:
                existing_row = pointslog_rows[row_index - 1] if len(pointslog_rows) >= row_index else []
                existing_score_values = existing_row[3:11] if isinstance(existing_row, list) else []
            
            # 3. Apply updates
            updates = []
            if update.attendance is not None:
                updates.append(("D", update.attendance))
            if update.bible is not None:
                updates.append(("E", update.bible))
            if update.book_answered is not None:
                updates.append(("F", update.book_answered))
            if update.memory_verse is not None:
                updates.append(("G", update.memory_verse))
            if update.participation is not None:
                updates.append(("H", update.participation))
            if update.bonus1_baf_1 is not None:
                updates.append(("I", update.bonus1_baf_1))
            if update.bonus2_baf_2 is not None:
                updates.append(("J", update.bonus2_baf_2))
            if update.bonus3_participation is not None:
                updates.append(("K", update.bonus3_participation))
            # Do not trust client total_points under concurrent toggles; server recalculates from D:K.
            
            # Apply all updates
            for column, value in updates:
                cell_address = f"{column}{row_index}"
                update_url = (
                    f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                    f"/items/{config['file_id']}/workbook/worksheets('PointsLog')/range(address='{cell_address}')"
                )
                
                update_response = await client.patch(
                    update_url,
                    json={"values": [[value]]},
                    headers=headers,
                )
                if update_response.status_code != 200:
                    print(f"❌ Error updating {cell_address}: {update_response.text}")
                    raise HTTPException(status_code=400, detail=f"Failed to update cell {cell_address}")

            # 4. Recalculate total points from the in-memory row snapshot with the new update applied.
            score_values = apply_update_to_score_values(existing_score_values, update)
            computed_total = calculate_total_points_from_row_values(score_values)

            total_cell_address = f"L{row_index}"
            total_update_url = (
                f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                f"/items/{config['file_id']}/workbook/worksheets('PointsLog')/range(address='{total_cell_address}')"
            )
            total_update_response = await client.patch(
                total_update_url,
                json={"values": [[computed_total]]},
                headers=headers,
            )
            if total_update_response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to update total points at {total_cell_address}")
            
            return {
                "success": True,
                "message": f"Updated {update.student_name} on {normalized_date}",
                "row_updated": row_index,
                "total_points": computed_total,
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 Exception in update_student_pointslog: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sheets/student-summary")
async def get_student_summary(
    class_filter: Optional[str] = None,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Get accumulated points per student grouped by Class then StudentID
    Optional: Filter by specific class_name (e.g., "Journey_Boys")
    Returns: { "Journey_Boys": [ {name, total_points}, ... ], "Journey_Girls": [ ... ], ... }
    Sorted by highest points first within each class
    """
    try:
        print(f"📊 Fetching student summary (class_filter: {class_filter})...")
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Fetch PointsLog sheet
            pointslog_url = (
                f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                f"/items/{config['file_id']}/workbook/worksheets('PointsLog')/range(address='A1:L10000')"
            )
            
            pointslog_response = await client.get(pointslog_url, headers=headers)
            
            if pointslog_response.status_code == 404:
                return {
                    "summary": {},
                    "total_students": 0,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            
            if pointslog_response.status_code != 200:
                raise HTTPException(status_code=pointslog_response.status_code, detail=f"Graph API error fetching PointsLog")
            
            # Fetch only populated Students rows for name mapping
            students_rows = _students_data_rows(await fetch_students_used_rows(client, headers))
            
            id_to_name = {}
            for row in students_rows:
                if len(row) >= 2:
                    student_id = row[0]
                    name = str(row[1]).strip()
                    id_to_name[student_id] = name
            
            # Process PointsLog data
            pointslog_data = pointslog_response.json()
            pointslog_rows = pointslog_data.get("values", [])
            
            # PointsLog structure: [Date, StudentID, Class, Att, Bible, BA, MV, Part, B1, B2, B3, TotalPoints]
            # Group by Class and StudentID, sum TotalPoints
            summary = {}  # {class_name: {student_name: total_points}}
            
            for row in pointslog_rows[1:]:  # Skip header
                if len(row) >= 12:
                    student_id = row[1]
                    class_name = row[2]
                    total_points = row[11]
                    
                    # Convert to int if possible
                    if total_points is None:
                        total_points = 0
                    else:
                        try:
                            total_points = int(total_points)
                        except (ValueError, TypeError):
                            total_points = 0
                    
                    # Apply class filter if provided
                    if class_filter and class_name != class_filter:
                        continue
                    
                    # Get student name
                    student_name = id_to_name.get(student_id, f"Unknown({student_id})")
                    
                    # Initialize class dict if not exists
                    if class_name not in summary:
                        summary[class_name] = {}
                    
                    # Sum points for this student
                    if student_name not in summary[class_name]:
                        summary[class_name][student_name] = 0
                    summary[class_name][student_name] += total_points
            
            # Convert to sorted list format and sort by points descending
            formatted_summary = {}
            for class_name in sorted(summary.keys()):
                students_list = [
                    {
                        "name": name,
                        "total_points": points
                    }
                    for name, points in summary[class_name].items()
                ]
                # Sort by points descending
                students_list.sort(key=lambda x: x["total_points"], reverse=True)
                formatted_summary[class_name] = students_list
            
            # Count total unique students
            total_students = sum(len(students) for students in formatted_summary.values())
            
            return {
                "summary": formatted_summary,
                "total_students": total_students,
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        print(f"💥 Exception in get_student_summary: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "Awana Points Logger API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
