"""
DQ03252026: FastAPI backend for Awana Points Logger
Handles Microsoft 365 SharePoint XLSX authentication and data sync
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx
import msal
import json
from datetime import datetime, date, timedelta
import os

app = FastAPI(title="Awana Points Logger API")

# CORS configuration for React Native frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration - Store these in environment variables or .env file
config = {
    "client_id": os.getenv("AZURE_CLIENT_ID", "YOUR_CLIENT_ID"),
    "client_secret": os.getenv("AZURE_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
    "tenant_id": os.getenv("AZURE_TENANT_ID", "YOUR_TENANT_ID"),
    "site_id": os.getenv("SHAREPOINT_SITE_ID", "YOUR_SITE_ID"),
    "drive_id": os.getenv("SHAREPOINT_DRIVE_ID", "YOUR_DRIVE_ID"),
    "file_id": os.getenv("SHAREPOINT_FILE_ID", "YOUR_FILE_ID"),
}

# Authority URL for MSAL
AUTHORITY = f"https://login.microsoftonline.com/{config['tenant_id']}"
SCOPE = ["https://graph.microsoft.com/.default"]


class TokenRequest(BaseModel):
    code: str
    redirect_uri: str


class StudentUpdate(BaseModel):
    date: str  # Format: "YYYY-MM-DD"
    class_name: str  # "Boys" or "Girls"
    student_name: str
    attendance: Optional[int] = None  # 1 or 0/null
    bible: Optional[int] = None
    book_answered: Optional[int] = None
    memory_verse: Optional[int] = None
    participation: Optional[int] = None
    bonus1_baf_1: Optional[int] = None
    bonus2_baf_2: Optional[int] = None
    bonus3_participation: Optional[int] = None
    total_points: Optional[int] = None


class BootstrapRequest(BaseModel):
    date: str  # Format: YYYY-MM-DD (internal)
    class_name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


def normalize_date_str(value) -> str:
    """Normalize date inputs (Excel serial, M/D/YYYY, ISO) into YYYY-MM-DD."""
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        # Excel serial (base date 1899-12-30)
        base_date = date(1899, 12, 30)
        return (base_date + timedelta(days=int(value))).strftime("%Y-%m-%d")

    text = str(value).strip()
    if not text:
        return ""

    # Accept both ISO and M/D/YYYY
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


async def fetch_students_roster(client: httpx.AsyncClient, headers: dict) -> list:
    """Read Students sheet as source of truth. Supports [Name,Class] or [StudentID,Name,Class]."""
    students_url = (
        f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
        f"/items/{config['file_id']}/workbook/worksheets/Students/usedRange(valuesOnly=true)"
    )

    response = await client.get(students_url, headers=headers)
    response.raise_for_status()
    rows = (response.json().get("values") or [])

    roster = []
    for row in rows:
        if not isinstance(row, list) or not row:
            continue

        # Skip header rows
        row_join = " ".join(str(c).strip().lower() for c in row[:3])
        if "name" in row_join and "class" in row_join:
            continue

        if len(row) >= 3:
            student_name = str(row[1]).strip()
            class_name = str(row[2]).strip()
        elif len(row) >= 2:
            student_name = str(row[0]).strip()
            class_name = str(row[1]).strip()
        else:
            continue

        if student_name and class_name:
            roster.append({"student_name": student_name, "class_name": class_name})

    return roster


async def fetch_pointslog_rows(client: httpx.AsyncClient, headers: dict) -> list:
    """Fetch existing PointsLog rows (Date, Class, StudentName + point columns)."""
    points_url = (
        f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
        f"/items/{config['file_id']}/workbook/worksheets/PointsLogSheet/usedRange(valuesOnly=true)"
    )
    response = await client.get(points_url, headers=headers)
    response.raise_for_status()
    return response.json().get("values", []) or []


def find_pointslog_row_index(rows: list, date_value: str, class_name: str, student_name: str) -> Optional[int]:
    """Return Excel row index (1-based), or None if not found."""
    normalized_target_date = normalize_date_str(date_value)
    for idx, row in enumerate(rows[1:], start=2):
        if len(row) < 3:
            continue
        row_date = normalize_date_str(row[0])
        row_class = str(row[1]).strip()
        row_student = str(row[2]).strip()
        if row_date == normalized_target_date and row_class == class_name and row_student == student_name:
            return idx
    return None


def get_msal_app():
    """Initialize MSAL application for server-side auth"""
    return msal.ConfidentialClientApplication(
        config["client_id"],
        authority=AUTHORITY,
        client_credential=config["client_secret"],
    )


async def get_access_token() -> str:
    """Get access token from Azure AD using client credentials"""
    app = get_msal_app()
    result = app.acquire_token_for_client(scopes=SCOPE) or {}

    if "access_token" in result:
        return result["access_token"]
    else:
        raise HTTPException(status_code=401, detail="Failed to acquire access token")


@app.post("/auth/token", response_model=AuthResponse)
async def authenticate_user(token_request: TokenRequest):
    """
    Exchange authorization code for access token
    Frontend sends the auth code from MSAL web auth library
    """
    app = get_msal_app()
    
    try:
        result = app.acquire_token_by_authorization_code(
            token_request.code,
            scopes=SCOPE,
            redirect_uri=token_request.redirect_uri,
        )
        
        if "access_token" in result:
            return AuthResponse(
                access_token=result["access_token"],
                token_type="Bearer",
                expires_in=result.get("expires_in", 3600),
            )
        else:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed: " + result.get("error_description", "Unknown error"),
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sheets/PointsLogSheet")
async def fetch_points_sheet(
    date_value: Optional[str] = None,
    class_name: Optional[str] = None,
    access_token: str = Depends(get_access_token),
):
    """
    Fetch all data from 'PointsLogSheet' Excel worksheet
    Returns rows filtered by date and class
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            rows = await fetch_pointslog_rows(client, headers)

            # Parse headers and data
            headers_row = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []

            normalized_filter_date = normalize_date_str(date_value) if date_value else None
            filtered_rows = []
            for row in data_rows:
                if len(row) < 3:
                    continue
                row_date = normalize_date_str(row[0])
                row_class = str(row[1]).strip()

                if normalized_filter_date and row_date != normalized_filter_date:
                    continue
                if class_name and row_class != class_name:
                    continue

                normalized_row = list(row)
                normalized_row[0] = row_date
                filtered_rows.append(normalized_row)
            
            return {
                "headers": headers_row,
                "data": filtered_rows,
                "timestamp": datetime.utcnow().isoformat(),
            }
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Graph API error: {str(e)}")


@app.post("/sheets/PointsLogSheet/bootstrap")
async def bootstrap_pointslog(
    request: BootstrapRequest,
    access_token: str = Depends(get_access_token),
):
    """Ensure PointsLog rows exist for all students in a class on the selected date."""
    try:
        normalized_date = normalize_date_str(request.date)

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            roster = await fetch_students_roster(client, headers)
            class_students = [
                s["student_name"]
                for s in roster
                if str(s.get("class_name", "")).strip() == request.class_name
            ]

            if not class_students:
                return {
                    "message": "No students found for this class",
                    "entries_created": 0,
                    "date": normalized_date,
                    "class_name": request.class_name,
                }

            rows = await fetch_pointslog_rows(client, headers)
            existing_keys = set()
            for row in rows[1:]:
                if len(row) < 3:
                    continue
                existing_keys.add(
                    (
                        normalize_date_str(row[0]),
                        str(row[1]).strip(),
                        str(row[2]).strip(),
                    )
                )

            new_rows = []
            for student_name in class_students:
                key = (normalized_date, request.class_name, student_name)
                if key not in existing_keys:
                    # A..L: Date, Class, StudentName, Att, Bible, BA, MV, Part, B1, B2, B3, Total
                    new_rows.append([
                        normalized_date,
                        request.class_name,
                        student_name,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                    ])

            if new_rows:
                start_row = len(rows) + 1 if rows else 2
                end_row = start_row + len(new_rows) - 1
                insert_url = (
                    f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                    f"/items/{config['file_id']}/workbook/worksheets/PointsLogSheet/range(address='A{start_row}:L{end_row}')"
                )

                insert_response = await client.patch(
                    insert_url,
                    json={"values": new_rows},
                    headers=headers,
                )
                insert_response.raise_for_status()

            return {
                "message": "Bootstrap complete",
                "entries_created": len(new_rows),
                "date": normalized_date,
                "class_name": request.class_name,
                "total_students": len(class_students),
            }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Graph API error: {str(e)}")


@app.patch("/sheets/PointsLogSheet/update")
async def update_student_row(
    update: StudentUpdate,
    access_token: str = Depends(get_access_token),
):
    """
    Update a specific student row in the Excel sheet
    Finds the row by date, class, and student name, then updates the specified columns
    """
    try:
        normalized_date = normalize_date_str(update.date)

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            rows = await fetch_pointslog_rows(client, headers)

            # Find existing row (normalized date compare)
            row_index = find_pointslog_row_index(rows, normalized_date, update.class_name, update.student_name)

            # Idempotent upsert: create missing row first
            if row_index is None:
                roster = await fetch_students_roster(client, headers)
                valid_student = any(
                    s["student_name"] == update.student_name and s["class_name"] == update.class_name
                    for s in roster
                )
                if not valid_student:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Student not found in Students roster: {update.student_name} ({update.class_name})",
                    )

                append_row = [
                    normalized_date,
                    update.class_name,
                    update.student_name,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    safe_int(update.total_points, 0),
                ]

                row_index = len(rows) + 1 if rows else 2
                append_url = (
                    f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                    f"/items/{config['file_id']}/workbook/worksheets/PointsLogSheet/range(address='A{row_index}:L{row_index}')"
                )
                append_response = await client.patch(
                    append_url,
                    json={"values": [append_row]},
                    headers=headers,
                )
                append_response.raise_for_status()

            # Build update ranges and values
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
            if update.total_points is not None:
                updates.append(("L", safe_int(update.total_points, 0)))
            
            # Apply updates
            for column, value in updates:
                cell_address = f"{column}{row_index}"
                update_url = (
                    f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                    f"/items/{config['file_id']}/workbook/worksheets/PointsLogSheet/range(address='{cell_address}')"
                )
                
                update_response = await client.patch(
                    update_url,
                    json={"values": [[value]]},
                    headers=headers,
                )
                update_response.raise_for_status()
            
            return {
                "success": True,
                "message": f"Updated {update.student_name} on {normalized_date}",
                "row_updated": row_index,
            }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Graph API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sheets/classes")
async def get_class_options():
    """Get available class options"""
    return {
        "classes": ["Boys", "Girls"],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "Awana Points Logger API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
