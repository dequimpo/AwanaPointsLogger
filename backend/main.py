"""
DQ03252026: FastAPI backend for Awana Points Logger
Handles Microsoft 365 SharePoint XLSX authentication and data sync
"""

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, StringConstraints, field_validator
from typing import Annotated, Literal, Optional, get_args
import asyncio
import base64
import hashlib
import logging
import re
import threading
import time
import httpx
import jwt
import msal
import json
from datetime import datetime, date, timedelta, timezone
import os
from dotenv import load_dotenv
from jwt import PyJWTError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("awana_points_logger")

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

# Outbound HTTP timeout (seconds) for every httpx.AsyncClient.
HTTP_TIMEOUT = 30.0

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
# - FAIL_OPEN_ON_GROUP_CHECK_ERROR: development-only opt-in; when true, transient Graph
#   permission/errors won't block sign-in. Always forced off in production.
ALLOWED_GROUP_ID = os.getenv("ALLOWED_GROUP_ID", "").strip()
ALLOWED_GROUP_NAME = os.getenv("ALLOWED_GROUP_NAME", "AwanaPointsLogger").strip()
ENFORCE_GROUP_MEMBERSHIP = _env_bool("ENFORCE_GROUP_MEMBERSHIP", True)
_fail_open_requested = _env_bool("FAIL_OPEN_ON_GROUP_CHECK_ERROR", False)
FAIL_OPEN_ON_GROUP_CHECK_ERROR = _fail_open_requested and not IS_PRODUCTION
if IS_PRODUCTION and _fail_open_requested:
    print("⚠️ FAIL_OPEN_ON_GROUP_CHECK_ERROR is ignored in production; authorization errors deny sign-in")
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

# Entra ID access-token validation for /auth/token.
ENTRA_JWKS_URL = f"https://login.microsoftonline.com/{config['tenant_id']}/discovery/v2.0/keys"
JWKS_CACHE_TTL_SECONDS = 6 * 3600
JWKS_MIN_REFRESH_INTERVAL_SECONDS = 60
GRAPH_AUDIENCES = (
    "https://graph.microsoft.com",
    "https://graph.microsoft.com/",
    "00000003-0000-0000-c000-000000000000",
)
ENTRA_ALLOWED_AUDIENCES = [config["client_id"], f"api://{config['client_id']}", *GRAPH_AUDIENCES]
ENTRA_ALLOWED_ISSUERS = [
    f"https://login.microsoftonline.com/{config['tenant_id']}/v2.0",
    f"https://sts.windows.net/{config['tenant_id']}/",
]

# Rate limiting (in-memory; single Render instance).
AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "10/minute")
WRITE_RATE_LIMIT = os.getenv("WRITE_RATE_LIMIT", "120/minute")


def client_ip_key(request: Request) -> str:
    """Client IP for rate limiting. Uses the right-most X-Forwarded-For hop (set by the
    hosting proxy) because left-most entries are client-controlled."""
    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    if hops:
        return hops[-1]
    return get_remote_address(request)


def session_or_ip_key(request: Request) -> str:
    """Rate-limit authenticated writes per session user (leaders often share one church IP)."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        try:
            payload = decode_session_token(auth_header[7:].strip())
            if payload.get("sub"):
                return f"user:{payload['sub']}"
        except PyJWTError:
            pass
    return f"ip:{client_ip_key(request)}"


limiter = Limiter(key_func=client_ip_key)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Ensure CORS headers are present on all unhandled 500 errors."""
    logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
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

if IS_PRODUCTION and not ENFORCE_SHAREPOINT_ACCESS and not (
    ENFORCE_GROUP_MEMBERSHIP and (ALLOWED_GROUP_ID or ALLOWED_GROUP_NAME)
):
    print("❌ No SharePoint or group authorization check is configured; all sign-ins will be denied in production")


def log_graph_error(context: str, response: httpx.Response) -> None:
    """Log Graph failures server-side only; never forward Graph bodies to clients."""
    logger.warning("Graph error during %s (status=%s): %s", context, response.status_code, response.text[:2000])


ClassName = Literal["Journey_Boys", "Journey_Girls", "Trek", "T&T", "Cubbies"]
ALLOWED_CLASSES = list(get_args(ClassName))
PointFlag = Annotated[int, Field(ge=0, le=1)]
_DATE_PATTERN = re.compile(r"^(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/(\d{2}|\d{4}))$")
_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y")


def validate_date_input(value: str) -> str:
    """Accept YYYY-MM-DD (internal) or M/D/YYYY, rejecting anything that isn't a real date."""
    text = str(value).strip()
    if not _DATE_PATTERN.match(text):
        raise ValueError("date must be in YYYY-MM-DD or M/D/YYYY format")
    for fmt in _DATE_FORMATS:
        try:
            datetime.strptime(text, fmt)
            return text
        except ValueError:
            continue
    raise ValueError("date is not a valid calendar date")


class TokenRequest(BaseModel):
    access_token: str


class AuthUser(BaseModel):
    oid: Optional[str] = None
    display_name: str
    email: Optional[str] = None
    tenant_id: Optional[str] = None


class ClassDateRequest(BaseModel):
    date: str  # Format: YYYY-MM-DD (internal) or M/D/YYYY
    class_name: ClassName

    @field_validator("date")
    @classmethod
    def _validate_date(cls, value: str) -> str:
        return validate_date_input(value)


class StudentUpdate(ClassDateRequest):
    student_name: str
    student_id: Optional[str] = None
    attendance: Optional[PointFlag] = None  # 1 or 0/null
    bible: Optional[PointFlag] = None
    book_answered: Optional[PointFlag] = None
    memory_verse: Optional[PointFlag] = None
    participation: Optional[PointFlag] = None
    bonus1_baf_1: Optional[PointFlag] = None
    bonus2_baf_2: Optional[PointFlag] = None
    bonus3_participation: Optional[PointFlag] = None
    total_points: Optional[int] = None  # Ignored; server recalculates.


class NormalizedStudentUpdate(StudentUpdate):
    """Normalized PointsLog update: student_id is required (no name lookup)."""
    student_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AutoPopulateRequest(ClassDateRequest):
    pass


class BootstrapRequest(ClassDateRequest):
    pass


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: AuthUser


_msal_app: Optional[msal.ConfidentialClientApplication] = None
_msal_app_lock = threading.Lock()


def get_msal_app() -> msal.ConfidentialClientApplication:
    """Return the shared MSAL app so its in-memory token cache is reused across requests."""
    global _msal_app
    if _msal_app is None:
        with _msal_app_lock:
            if _msal_app is None:
                _msal_app = msal.ConfidentialClientApplication(
                    config["client_id"],
                    authority=AUTHORITY,
                    client_credential=config["client_secret"],
                )
    return _msal_app


async def get_graph_access_token() -> str:
    """Get app access token for Microsoft Graph (served from MSAL's cache when valid)."""
    result = get_msal_app().acquire_token_for_client(scopes=GRAPH_SCOPE) or {}

    if "access_token" in result:
        return result["access_token"]

    logger.error("Failed to acquire Graph app token: %s", result.get("error"))
    raise HTTPException(status_code=401, detail="Failed to acquire access token")


def create_session_token(user: AuthUser) -> tuple[str, int]:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(hours=SESSION_TTL_HOURS)
    payload = {
        "sub": user.oid or user.email or user.display_name,
        "name": user.display_name,
        "email": user.email,
        "oid": user.oid,
        "tid": user.tenant_id,
        "iss": SESSION_ISSUER,
        "aud": SESSION_AUDIENCE,
        "iat": issued_at,
        "exp": expires_at,
    }
    token = jwt.encode(payload, config["session_secret"], algorithm="HS256")
    return token, SESSION_TTL_HOURS * 3600


def decode_session_token(token: str) -> dict:
    return jwt.decode(
        token,
        config["session_secret"],
        algorithms=["HS256"],
        audience=SESSION_AUDIENCE,
        issuer=SESSION_ISSUER,
    )


def require_authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        return decode_session_token(credentials.credentials)
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        ) from exc


async def fetch_signed_in_user(access_token: str) -> dict:
    print("🔐 [Graph] Fetching user profile with Graph /me")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me?$select=id,displayName,userPrincipalName,mail",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            print(f"📊 [Graph] Response status: {response.status_code}")

            if response.status_code != 200:
                log_graph_error("Graph /me", response)
                return {}

            result = response.json()
            print("✅ [Graph] Successfully fetched signed-in user")
            return result

        except Exception:
            logger.exception("Exception during Graph /me call")
            return {}


class EntraKeyUnavailableError(Exception):
    """Raised when Entra signing keys cannot be retrieved."""


_jwks_cache: dict = {"keys": {}, "fetched_at": 0.0}
_jwks_lock = asyncio.Lock()


async def _refresh_entra_jwks() -> None:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.get(ENTRA_JWKS_URL)
    if response.status_code != 200:
        raise EntraKeyUnavailableError(f"JWKS fetch failed with status {response.status_code}")
    keys = (response.json() or {}).get("keys") or []
    _jwks_cache["keys"] = {key["kid"]: key for key in keys if isinstance(key, dict) and key.get("kid")}
    _jwks_cache["fetched_at"] = time.monotonic()


async def get_entra_signing_key(kid: Optional[str]):
    """Return the RSA public key for `kid`, refreshing the cached JWKS when stale or on key rollover."""
    if not kid:
        raise jwt.InvalidTokenError("Token header has no kid")

    async with _jwks_lock:
        age = time.monotonic() - _jwks_cache["fetched_at"]
        never_fetched = _jwks_cache["fetched_at"] == 0.0
        stale = never_fetched or age > JWKS_CACHE_TTL_SECONDS
        unknown_kid = kid not in _jwks_cache["keys"] and age > JWKS_MIN_REFRESH_INTERVAL_SECONDS
        if stale or unknown_kid:
            try:
                await _refresh_entra_jwks()
            except EntraKeyUnavailableError:
                raise
            except Exception as exc:
                raise EntraKeyUnavailableError("JWKS fetch failed") from exc

        jwk = _jwks_cache["keys"].get(kid)

    if not jwk:
        raise jwt.InvalidTokenError("Unknown token signing key")
    return jwt.PyJWK(jwk, algorithm="RS256").key


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _graph_nonce_signed_variant(token: str) -> Optional[str]:
    """Graph access tokens carry a `nonce` header whose SHA-256 hex digest (not the raw value)
    was signed. Return the token with the signed header form, or None if there is no nonce."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_json = _b64url_decode(parts[0]).decode("utf-8")
    nonce = json.loads(header_json).get("nonce")
    if not isinstance(nonce, str) or not nonce:
        return None
    hashed = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    signed_header_json = header_json.replace(json.dumps(nonce), json.dumps(hashed), 1)
    return ".".join([_b64url_encode(signed_header_json.encode("utf-8")), parts[1], parts[2]])


async def validate_entra_access_token(token: str) -> dict:
    """Verify an Entra access token's signature (tenant JWKS) and iss/aud/exp/tid claims."""
    header = jwt.get_unverified_header(token)
    if header.get("alg") != "RS256":
        raise jwt.InvalidTokenError("Unexpected token algorithm")

    signing_key = await get_entra_signing_key(header.get("kid"))

    candidates = []
    nonce_variant = _graph_nonce_signed_variant(token)
    if nonce_variant:
        candidates.append(nonce_variant)
    candidates.append(token)

    claims = None
    last_error: Optional[Exception] = None
    for candidate in candidates:
        try:
            claims = jwt.decode(
                candidate,
                signing_key,
                algorithms=["RS256"],
                audience=ENTRA_ALLOWED_AUDIENCES,
                issuer=ENTRA_ALLOWED_ISSUERS,
                leeway=60,
                options={"require": ["exp", "iss", "aud", "tid"]},
            )
            break
        except jwt.InvalidSignatureError as exc:
            last_error = exc
            continue

    if claims is None:
        raise last_error or jwt.InvalidSignatureError("Signature verification failed")

    if claims.get("tid") != config["tenant_id"]:
        raise jwt.InvalidTokenError("Token tenant does not match configured tenant")

    return claims


async def check_membership_by_group_id(access_token: str, group_id: str) -> bool:
    """Check if signed-in user is a member of specific group id via /me/checkMemberGroups."""
    if not group_id:
        return False

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
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

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
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

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
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
                logger.warning("SharePoint access check errored: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unable to verify SharePoint access for this user.",
                ) from exc

    await ensure_user_group_access(access_token, user)


def _deny_no_authorization_configured() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: unable to verify access for this user.",
    )


async def ensure_user_group_access(access_token: str, user: dict) -> None:
    """Authorize app usage based on configured group controls."""
    if not ENFORCE_GROUP_MEMBERSHIP:
        if IS_PRODUCTION:
            print("❌ [AuthZ] Group enforcement disabled and SharePoint access not confirmed; denying in production")
            _deny_no_authorization_configured()
        print("ℹ️ [AuthZ] Group enforcement disabled; allowing authenticated user (development)")
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

    for err in check_errors:
        logger.warning("[AuthZ] %s", err)

    if check_errors and FAIL_OPEN_ON_GROUP_CHECK_ERROR:
        print("⚠️ [AuthZ] Group check errored; FAIL_OPEN enabled (development). Allowing sign-in.")
        return

    if checks_attempted == 0:
        if IS_PRODUCTION:
            print("❌ [AuthZ] No group configured and SharePoint access not confirmed; denying in production")
            _deny_no_authorization_configured()
        print("⚠️ [AuthZ] No group configured; allowing authenticated user (development)")
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
        log_graph_error("fetch Students", students_response)
        raise HTTPException(
            status_code=students_response.status_code,
            detail="Graph API error fetching Students",
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
        log_graph_error("fetch PointsLog", response)
        raise HTTPException(
            status_code=response.status_code,
            detail="Graph API error fetching PointsLog",
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
        dt = datetime.fromtimestamp((float(value) - 25569) * 86400, tz=timezone.utc)
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
    score_values = [safe_int(v, 0) for v in values[:8]] if isinstance(values, list) else []
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
@limiter.limit(AUTH_RATE_LIMIT)
async def authenticate_user(request: Request, token_request: TokenRequest):
    """
    Accept a browser-issued access token, verify identity via Graph, and issue a session.
    SPA platform tokens can only be redeemed from the browser, so the frontend
    exchanges the auth code itself and sends the resulting access_token here.
    """
    try:
        print("🔐 [AuthToken] POST /auth/token request received")

        graph_user = await fetch_signed_in_user(token_request.access_token)

        if not graph_user or "id" not in graph_user:
            print("❌ [AuthToken] Graph verification failed")
            raise HTTPException(
                status_code=401,
                detail="Unable to verify identity: Graph /me call failed or returned no user",
            )

        try:
            claims = await validate_entra_access_token(token_request.access_token)
        except EntraKeyUnavailableError:
            logger.exception("Unable to load Entra signing keys")
            raise HTTPException(status_code=503, detail="Unable to validate access token right now")
        except PyJWTError as exc:
            logger.warning("Rejected access token: %s", exc)
            raise HTTPException(status_code=401, detail="Invalid access token")

        if claims.get("oid") and claims.get("oid") != graph_user.get("id"):
            logger.warning("Rejected access token: oid does not match Graph /me user")
            raise HTTPException(status_code=401, detail="Invalid access token")

        print("✅ [AuthToken] User verified")
        await ensure_user_is_authorized(token_request.access_token, graph_user)

        user = AuthUser(
            oid=graph_user.get("id"),
            display_name=graph_user.get("displayName") or "User",
            email=graph_user.get("userPrincipalName") or graph_user.get("mail"),
            tenant_id=None,
        )

        session_token, expires_in = create_session_token(user)
        print("✅ [AuthToken] Session token created successfully")

        return AuthResponse(
            access_token=session_token,
            token_type="Bearer",
            expires_in=expires_in,
            user=user,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Exception in /auth/token")
        raise HTTPException(status_code=400, detail="Authentication failed")


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
        
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "normalized",
            }
    except Exception:
        logger.exception("Exception in fetch_points_sheet")
        raise HTTPException(status_code=500, detail="Server error")




def pointslog_range_url(address: str) -> str:
    return (
        f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
        f"/items/{config['file_id']}/workbook/worksheets('PointsLog')/range(address='{address}')"
    )


async def ensure_pointslog_rows_for_class(
    client: httpx.AsyncClient, headers: dict, date_value: str, class_name: str
) -> dict:
    """Append a zeroed PointsLog row for every roster student in `class_name` that has no
    (date, student_id, class) row yet. Returns counts; never duplicates existing rows."""
    normalized_date = normalize_date_str(date_value)

    roster = await fetch_students_roster(client, headers)
    class_students = [s for s in roster if s["class_name"] == class_name]

    if not class_students:
        return {"date": normalized_date, "entries_created": 0, "total_students": 0}

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
        key = (normalized_date, student["student_id"], class_name)
        if key in existing_keys:
            continue
        # [Date, StudentID, Class, Att, Bible, BA, MV, Part, B1, B2, B3, TotalPoints]
        new_entries.append([normalized_date, student["student_id"], class_name, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    if new_entries:
        start_row = max(2, len(pointslog_rows) + 1)
        end_row = start_row + len(new_entries) - 1
        insert_response = await client.patch(
            pointslog_range_url(f"A{start_row}:L{end_row}"),
            json={"values": new_entries},
            headers=headers,
        )
        if insert_response.status_code != 200:
            log_graph_error("insert PointsLog rows", insert_response)
            raise HTTPException(
                status_code=insert_response.status_code,
                detail="Failed to insert PointsLog rows",
            )

    return {
        "date": normalized_date,
        "entries_created": len(new_entries),
        "total_students": len(class_students),
    }


async def apply_pointslog_update(update: StudentUpdate, access_token: str, allow_name_lookup: bool) -> dict:
    """Upsert one student's PointsLog row with a single Graph range write."""
    print(f"✏️ Updating points for {update.student_name} on {update.date}")
    normalized_date = normalize_date_str(update.date)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        student_id = str(update.student_id).strip() if update.student_id else None
        if not student_id and allow_name_lookup:
            roster = await fetch_students_roster(client, headers)
            for student in roster:
                if student["student_name"] == update.student_name and student["class_name"] == update.class_name:
                    student_id = student["student_id"]
                    break

        if not student_id:
            raise HTTPException(status_code=404, detail=f"Student {update.student_name} not found")

        pointslog_rows = await fetch_pointslog_rows(client, headers)
        row_index = find_pointslog_row_index(pointslog_rows, normalized_date, student_id, update.class_name)

        if row_index is None:
            existing_score_values = [0] * 8
        else:
            existing_row = pointslog_rows[row_index - 1] if len(pointslog_rows) >= row_index else []
            existing_score_values = existing_row[3:11] if isinstance(existing_row, list) else []

        # Do not trust client total_points; server recalculates from D:K.
        score_values = apply_update_to_score_values(existing_score_values, update)
        computed_total = calculate_total_points_from_row_values(score_values)

        if row_index is None:
            row_index = max(2, len(pointslog_rows) + 1)
            address = f"A{row_index}:L{row_index}"
            row_values = [normalized_date, student_id, update.class_name, *score_values, computed_total]
        else:
            address = f"D{row_index}:L{row_index}"
            row_values = [*score_values, computed_total]

        write_response = await client.patch(
            pointslog_range_url(address),
            json={"values": [row_values]},
            headers=headers,
        )
        if write_response.status_code != 200:
            log_graph_error(f"update PointsLog {address}", write_response)
            raise HTTPException(status_code=400, detail="Failed to update PointsLog row")

        return {
            "success": True,
            "message": f"Updated {update.student_name} on {normalized_date}",
            "row_updated": row_index,
            "total_points": computed_total,
        }


@app.patch("/sheets/PointsLogSheet/update")
@limiter.limit(WRITE_RATE_LIMIT, key_func=session_or_ip_key)
async def update_student_row(
    request: Request,
    update: StudentUpdate,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Update a specific student row (backward compatible endpoint)
    Routes to the normalized PointsLog update; falls back to a roster name lookup
    when student_id is not supplied.
    """
    try:
        return await apply_pointslog_update(update, access_token, allow_name_lookup=True)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Exception in update_student_row")
        raise HTTPException(status_code=500, detail="Server error")


@app.post("/sheets/PointsLogSheet/bootstrap")
@limiter.limit(WRITE_RATE_LIMIT, key_func=session_or_ip_key)
async def bootstrap_pointslog_sheet(
    request: Request,
    bootstrap_request: BootstrapRequest,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """Ensure PointsLog contains one row per class student for the selected date."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            result = await ensure_pointslog_rows_for_class(
                client, headers, bootstrap_request.date, bootstrap_request.class_name
            )

        return {
            "message": "Bootstrap complete" if result["total_students"] else "No students found for this class",
            "entries_created": result["entries_created"],
            "date": result["date"],
            "class_name": bootstrap_request.class_name,
            "total_students": result["total_students"],
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Exception in bootstrap_pointslog_sheet")
        raise HTTPException(status_code=500, detail="Bootstrap failed")


@app.get("/sheets/classes")
async def get_class_options(user_session: dict = Depends(require_authenticated_user)):
    """Get available class options"""
    return {
        "classes": list(ALLOWED_CLASSES),
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
        
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except Exception:
        logger.exception("Exception in fetch_students_sheet")
        raise HTTPException(status_code=500, detail="Server error")


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
        
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            
            if response.status_code != 200:
                log_graph_error("fetch PointsLog", response)
                raise HTTPException(status_code=response.status_code, detail="Graph API error")
            
            data = response.json()
            rows = data.get("values", [])
            
            print(f"✅ Retrieved {len(rows)} rows from PointsLog sheet")
            
            headers_row = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            
            return {
                "headers": headers_row,
                "data": data_rows,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except Exception:
        logger.exception("Exception in fetch_pointslog_sheet")
        raise HTTPException(status_code=500, detail="Server error")



@app.post("/sheets/PointsLog/auto-populate")
@limiter.limit(WRITE_RATE_LIMIT, key_func=session_or_ip_key)
async def auto_populate_new_date(
    request: Request,
    populate_request: AutoPopulateRequest,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Deprecated: use POST /sheets/PointsLogSheet/bootstrap.
    Delegates to the same dedupe-aware routine, so existing rows are never duplicated.
    """
    try:
        print(f"🆕 Auto-populating PointsLog for {populate_request.date} ({populate_request.class_name})")
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            result = await ensure_pointslog_rows_for_class(
                client, headers, populate_request.date, populate_request.class_name
            )

        if not result["total_students"]:
            message = "No students found for this class"
        elif not result["entries_created"]:
            message = "No entries to create"
        else:
            message = f"Auto-populated {result['entries_created']} students"

        return {
            "message": message,
            "entries_created": result["entries_created"],
            "date": result["date"],
            "class": populate_request.class_name,
        }
    except Exception:
        logger.exception("Exception in auto_populate_new_date")
        raise HTTPException(status_code=500, detail="Server error")


@app.patch("/sheets/PointsLog/update")
@limiter.limit(WRITE_RATE_LIMIT, key_func=session_or_ip_key)
async def update_student_pointslog(
    request: Request,
    update: NormalizedStudentUpdate,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Update a specific student's points in PointsLog sheet
    Uses normalized structure; student_id is required.
    """
    try:
        return await apply_pointslog_update(update, access_token, allow_name_lookup=False)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Exception in update_student_pointslog")
        raise HTTPException(status_code=500, detail="Server error")


@app.get("/sheets/student-summary")
async def get_student_summary(
    class_filter: Optional[str] = None,
    access_token: str = Depends(get_graph_access_token),
    user_session: dict = Depends(require_authenticated_user),
):
    """
    Get accumulated points per student grouped by Class then StudentID
    Optional: Filter by specific class_name (e.g., "Journey_Boys")
    Returns: { "Journey_Boys": [ {student_id, name, total_points}, ... ], ... }
    Sorted by highest points first within each class
    """
    try:
        print(f"📊 Fetching student summary (class_filter: {class_filter})...")

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            headers = {"Authorization": f"Bearer {access_token}"}

            pointslog_response = await client.get(pointslog_range_url("A1:L10000"), headers=headers)

            if pointslog_response.status_code == 404:
                return {
                    "summary": {},
                    "total_students": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            if pointslog_response.status_code != 200:
                log_graph_error("fetch PointsLog summary", pointslog_response)
                raise HTTPException(status_code=pointslog_response.status_code, detail="Graph API error fetching PointsLog")

            # Fetch only populated Students rows for display-name mapping
            students_rows = _students_data_rows(await fetch_students_used_rows(client, headers))

            id_to_name = {}
            for row in students_rows:
                if len(row) >= 2:
                    id_to_name[str(row[0]).strip()] = str(row[1]).strip()

            pointslog_data = pointslog_response.json()
            pointslog_rows = pointslog_data.get("values", [])

            # PointsLog structure: [Date, StudentID, Class, Att, Bible, BA, MV, Part, B1, B2, B3, TotalPoints]
            # Group by Class and StudentID, sum TotalPoints
            summary = {}  # {class_name: {student_id: total_points}}

            for row in pointslog_rows[1:]:  # Skip header
                if len(row) < 12:
                    continue
                student_id = str(row[1]).strip()
                class_name = row[2]
                if not student_id:
                    continue

                if class_filter and class_name != class_filter:
                    continue

                class_totals = summary.setdefault(class_name, {})
                class_totals[student_id] = class_totals.get(student_id, 0) + safe_int(row[11], 0)

            formatted_summary = {}
            for class_name in sorted(summary.keys()):
                students_list = [
                    {
                        "student_id": student_id,
                        "name": id_to_name.get(student_id, f"Unknown({student_id})"),
                        "total_points": points,
                    }
                    for student_id, points in summary[class_name].items()
                ]
                students_list.sort(key=lambda x: x["total_points"], reverse=True)
                formatted_summary[class_name] = students_list

            total_students = sum(len(students) for students in formatted_summary.values())

            return {
                "summary": formatted_summary,
                "total_students": total_students,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    except Exception:
        logger.exception("Exception in get_student_summary")
        raise HTTPException(status_code=500, detail="Server error")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "Awana Points Logger API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
