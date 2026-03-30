# Migration Guide: Single Sheet to Normalized Schema

## Overview

This guide walks you through migrating your Awana Points Logger from a single `PointsLogSheet` to a normalized two-sheet structure:

- **Students Sheet**: Master list of all students (StudentID, Name, Class)
- **PointsLog Sheet**: All points records with StudentID references (no duplicate names)

## Why Migrate?

✅ **No more manual student re-creation** for new Sundays  
✅ **Cleaner data** with no duplicates  
✅ **Automatic row population** for new dates  
✅ **Better maintenance** when students join/leave  
✅ **Scalability** for large classes  

## Prerequisites

- Backend running with proper `.env` configuration
- Microsoft 365 credentials configured
- Existing PointsLogSheet with student data

## Migration Steps

### Step 1: Backup Your Data (Optional but Recommended)

Before running the migration, create a backup of your Excel file:

```bash
# Copy your Excel file to a backup location
# This preserves the original PointsLogSheet in SharePoint
```

### Step 2: Run the Migration Script

```bash
# Navigate to the backend directory
cd backend

# Activate the Python virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Run the migration script
python migrate_sheets.py
```

**What the script does:**

1. Reads all data from existing `PointsLogSheet`
2. Extracts unique students and creates a new `Students` sheet
3. Creates a new `PointsLog` sheet with StudentID references
4. Migrates all existing point records
5. Leaves the original `PointsLogSheet` intact for archival

**Sample Output:**

```
🚀 Starting Awana Points Logger Migration

🔐 Authenticating with Azure AD...
✅ Authentication successful

📥 Fetching existing PointsLogSheet data...
✅ Retrieved 245 rows

📊 Found 42 unique students across all dates and classes

📝 Creating Students sheet...
✅ Created 42 student records

📝 Creating PointsLog sheet...
✅ Migrated 245 point records

✅ Migration complete!
   • Created 'Students' sheet with 42 records
   • Created 'PointsLog' sheet with 245 records
   • Original 'PointsLogSheet' remains unchanged (archive)
```

### Step 3: Verify Migration

After the script completes, verify the new sheets in SharePoint:

1. Open your Excel file in SharePoint
2. Check for three sheets:
   - `PointsLogSheet` (original, archived)
   - `Students` (new: StudentID, Name, Class)
   - `PointsLog` (new: Date, StudentID, Class, Points...)

## New Functionality

### Auto-Populate Feature

When you select a new Sunday date in the app, the system can automatically create empty point entries for all students in that class.

**Via API:**

```bash
curl -X POST http://localhost:8000/sheets/PointsLog/auto-populate \
  -H "Content-Type: application/json" \
  -d '{
    "date": "3/30/2026",
    "class_name": "Boys"
  }'
```

**Response:**

```json
{
  "message": "Auto-populated 21 students",
  "entries_created": 21,
  "date": "3/30/2026",
  "class": "Boys"
}
```

### New API Endpoints

#### Get all Students

```bash
GET /sheets/Students
```

Returns all students with their IDs and class assignments.

#### Get PointsLog

```bash
GET /sheets/PointsLog
```

Returns all point records in normalized format (StudentID instead of names).

#### Auto-Populate New Date

```bash
POST /sheets/PointsLog/auto-populate
Body: {
  "date": "M/D/YYYY",
  "class_name": "Boys" or "Girls"
}
```

Creates empty point entries for all students of the given class on the given date.

#### Update Points (Works with both schemas!)

```bash
PATCH /sheets/PointsLogSheet/update
```

Same as before - automatically routes to the new normalized sheet.

## Frontend Integration

**Good news:** The frontend continues to work without any changes!

- Existing endpoints remain compatible
- The new `/sheets/PointsLogSheet` endpoint denormalizes data on-the-fly
- Student names are automatically retrieved from the Students sheet
- No frontend code modification required

## Troubleshooting

### "Students sheet not found. Run migration first."

**Solution:** The migration script hasn't been run yet. Run:

```bash
python backend/migrate_sheets.py
```

### "Migration failed: Failed to acquire access token"

**Check:**

1. Azure credentials in `.env` are correct
2. The account has permissions to the SharePoint site
3. Azure app registration has `Files.ReadWrite.All` permission

### "Network errors during migration"

**Solution:** May be a temporary network issue. Run again:

```bash
python backend/migrate_sheets.py
```

The script is idempotent (safe to run multiple times).

## Rolling Back

If you need to revert to the single-sheet structure:

1. Delete the `Students` sheet
2. Delete the `PointsLog` sheet
3. Continue using the archived `PointsLogSheet`

**However**, you'll need to update the backend code to read from `PointsLogSheet` instead of `PointsLog`.

## Adding New Students

After migration, add new students directly in the `Students` sheet:

1. Open Excel file in SharePoint
2. Go to `Students` sheet
3. Add a new row: `[NextID, StudentName, Class]`
4. New students automatically appear in the app for future dates

## Next Steps

1. ✅ Run migration script
2. ✅ Verify new sheets exist
3. ✅ Test logging points for an existing date
4. ✅ Test logging for a new date (should auto-populate)
5. ✅ Share your feedback!

---

**Need help?** Check the backend logs for detailed error messages:

```bash
# View backend logs while running
tail -f backend/main.py  # or check the terminal where backend is running
```
