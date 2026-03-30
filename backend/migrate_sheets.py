"""
Migration Script: Converts single PointsLogSheet to normalized Students + PointsLog sheets
Run this ONCE to create the new structure and migrate existing data
    python migrate_sheets.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import httpx
import msal
from datetime import datetime

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Configuration
config = {
    "client_id": os.getenv("AZURE_CLIENT_ID"),
    "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
    "tenant_id": os.getenv("AZURE_TENANT_ID"),
    "site_id": os.getenv("SHAREPOINT_SITE_ID"),
    "drive_id": os.getenv("SHAREPOINT_DRIVE_ID"),
    "file_id": os.getenv("SHAREPOINT_FILE_ID"),
}

AUTHORITY = f"https://login.microsoftonline.com/{config['tenant_id']}"
SCOPE = ["https://graph.microsoft.com/.default"]


def get_msal_app():
    """Initialize MSAL application"""
    return msal.ConfidentialClientApplication(
        config["client_id"],
        authority=AUTHORITY,
        client_credential=config["client_secret"],
    )


def get_access_token():
    """Get access token from Azure AD"""
    app = get_msal_app()
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception("Failed to acquire access token")


def excel_serial_to_date_string(serial):
    """Convert Excel date serial number to M/D/YYYY string"""
    if isinstance(serial, str):
        return serial
    from datetime import datetime, timezone, timedelta
    unix_days = serial - 25569
    d = datetime(1970, 1, 1) + timedelta(days=unix_days)
    return f"{d.month}/{d.day}/{d.year}"


async def fetch_existing_sheet(access_token: str):
    """Fetch all data from existing PointsLogSheet"""
    print("📥 Fetching existing PointsLogSheet data...")
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = (
            f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
            f"/items/{config['file_id']}/workbook/worksheets('PointsLogSheet')/range(address='A1:L10000')"
        )
        
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch sheet: {response.text}")
        
        data = response.json()
        rows = data.get("values", [])
        print(f"✅ Retrieved {len(rows)} rows")
        return rows


async def create_students_sheet(access_token: str, students_data: list):
    """Create new Students sheet with StudentID, Name, Class"""
    print("📝 Creating Students sheet...")
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Create new worksheet named "Students"
        sheet_name = "Students"
        create_url = (
            f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
            f"/items/{config['file_id']}/workbook/worksheets/add"
        )
        
        sheet_response = await client.post(
            create_url,
            json={"name": sheet_name},
            headers=headers,
        )
        
        if sheet_response.status_code != 201:
            if "already exists" in sheet_response.text:
                print(f"   ⚠️ {sheet_name} sheet already exists, will overwrite...")
            else:
                print(f"   Error: {sheet_response.text}")
        
        # Add headers
        headers_data = [["StudentID", "Name", "Class"]]
        headers_url = (
            f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
            f"/items/{config['file_id']}/workbook/worksheets('{sheet_name}')/range(address='A1:C1')"
        )
        
        header_response = await client.patch(
            headers_url,
            json={"values": headers_data},
            headers=headers,
        )
        if header_response.status_code != 200:
            print(f"   Error writing headers: {header_response.text}")
        
        # Add student data
        if students_data:
            students_range = f"A2:C{len(students_data) + 1}"
            data_url = (
                f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                f"/items/{config['file_id']}/workbook/worksheets('{sheet_name}')/range(address='{students_range}')"
            )
            
            data_response = await client.patch(
                data_url,
                json={"values": students_data},
                headers=headers,
            )
            if data_response.status_code == 200:
                print(f"✅ Created {len(students_data)} student records")
            else:
                print(f"   Error writing data: {data_response.text}")


async def create_pointslog_sheet(access_token: str, points_data: list):
    """Create new PointsLog sheet with StudentID and points columns"""
    print("📝 Creating PointsLog sheet...")
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        sheet_name = "PointsLog"
        
        # Create new worksheet
        create_url = (
            f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
            f"/items/{config['file_id']}/workbook/worksheets/add"
        )
        
        sheet_response = await client.post(
            create_url,
            json={"name": sheet_name},
            headers=headers,
        )
        
        if sheet_response.status_code != 201:
            if "already exists" in sheet_response.text:
                print(f"   ⚠️ {sheet_name} sheet already exists, will overwrite...")
            else:
                print(f"   Error: {sheet_response.text}")
        
        # Add headers
        headers_data = [[
            "Date", "StudentID", "Class",
            "Attendance", "Bible", "BookAnswered", "MemoryVerse", "Participation",
            "Bonus1_BAF1", "Bonus2_BAF2", "Bonus3_Participation", "TotalPoints"
        ]]
        
        headers_url = (
            f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
            f"/items/{config['file_id']}/workbook/worksheets('{sheet_name}')/range(address='A1:L1')"
        )
        
        header_response = await client.patch(
            headers_url,
            json={"values": headers_data},
            headers=headers,
        )
        if header_response.status_code != 200:
            print(f"   Error writing headers: {header_response.text}")
        
        # Add points data
        if points_data:
            points_range = f"A2:L{len(points_data) + 1}"
            data_url = (
                f"https://graph.microsoft.com/v1.0/drives/{config['drive_id']}"
                f"/items/{config['file_id']}/workbook/worksheets('{sheet_name}')/range(address='{points_range}')"
            )
            
            data_response = await client.patch(
                data_url,
                json={"values": points_data},
                headers=headers,
            )
            if data_response.status_code == 200:
                print(f"✅ Migrated {len(points_data)} point records")
            else:
                print(f"   Error writing data: {data_response.text}")


async def migrate():
    """Main migration process"""
    print("\n🚀 Starting Awana Points Logger Migration\n")
    
    try:
        # Validate config
        if not all([config["client_id"], config["client_secret"], config["tenant_id"]]):
            print("❌ Missing Azure credentials in .env file")
            return False
        
        # Get access token
        print("🔐 Authenticating with Azure AD...")
        access_token = get_access_token()
        print("✅ Authentication successful\n")
        
        # Fetch existing data
        rows = await fetch_existing_sheet(access_token)
        
        # Skip header row
        data_rows = rows[1:] if len(rows) > 1 else []
        
        if not data_rows:
            print("⚠️ No data found in existing sheet. Creating empty normalized sheets...")
            await create_students_sheet(access_token, [])
            await create_pointslog_sheet(access_token, [])
            print("\n✅ Migration complete!")
            return True
        
        # Extract unique students while preserving order
        students_dict = {}
        student_id_counter = 1
        
        for row in data_rows:
            if len(row) >= 3:
                student_name = str(row[2]).strip()
                student_class = str(row[1]).strip() if row[1] else "Journey_Boys"
                
                # Create unique key
                key = (student_name, student_class)
                if key not in students_dict:
                    students_dict[key] = student_id_counter
                    student_id_counter += 1
        
        # Create students list for Students sheet
        students_data = [
            [student_id, name, cls]
            for (name, cls), student_id in sorted(students_dict.items(), key=lambda x: x[1])
        ]
        
        print(f"\n📊 Found {len(students_data)} unique students across all dates and classes\n")
        
        # Create Points Log data with StudentID references
        points_data = []
        for row in data_rows:
            if len(row) >= 12:
                date_val = excel_serial_to_date_string(row[0])
                class_val = str(row[1]).strip() if row[1] else "Journey_Boys"
                student_name = str(row[2]).strip()
                
                # Get the StudentID for this student
                key = (student_name, class_val)
                student_id = students_dict.get(key, 0)
                
                # Extract points
                attendance = 1 if row[3] else 0
                bible = 1 if row[4] else 0
                book_answered = 1 if row[5] else 0
                memory_verse = 1 if row[6] else 0
                participation = 1 if row[7] else 0
                bonus1 = 1 if row[8] else 0
                bonus2 = 1 if row[9] else 0
                bonus3 = 1 if row[10] else 0
                total_points = int(row[11]) if row[11] else 0
                
                points_data.append([
                    date_val, student_id, class_val,
                    attendance, bible, book_answered, memory_verse, participation,
                    bonus1, bonus2, bonus3, total_points
                ])
        
        print(f"📊 Migrating {len(points_data)} point records\n")
        
        # Create sheets and migrate data
        await create_students_sheet(access_token, students_data)
        await create_pointslog_sheet(access_token, points_data)
        
        print("\n✅ Migration complete!")
        print(f"   • Created 'Students' sheet with {len(students_data)} records")
        print(f"   • Created 'PointsLog' sheet with {len(points_data)} records")
        print(f"   • Original 'PointsLogSheet' remains unchanged (archive)")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(migrate())
    sys.exit(0 if success else 1)
