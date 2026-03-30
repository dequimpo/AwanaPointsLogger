# Quick Reference: Normalized Schema Commands

## 🚀 Getting Started

### Run Migration (First Time Only)
```bash
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
./setup-normalizedschema.sh
```

Or manually:
```bash
cd backend
python3 migrate_sheets.py
```

---

## 🔧 Common Tasks

### Start Development Servers
```bash
./run-servers.sh
```
Access at:
- App: `http://localhost:8081`
- API Docs: `http://localhost:8000/docs`

### Add a New Student
1. Open Excel file in SharePoint
2. Go to `Students` sheet
3. Add row: `[NextID, Name, Class]`
4. Example: `[43, Sarah Wilson, Girls]`

### Remove a Student
1. Open Excel file in SharePoint
2. Go to `Students` sheet
3. Delete the student row

### Test a New Date
1. Start app
2. Select new Sunday (e.g., 3/30/2026)
3. Choose class (Boys or Girls)
4. If no students: Click "Auto-Populate"
5. Start logging points

---

## 📊 API Calls

### Fetch All Students
```bash
curl -X GET http://localhost:8000/sheets/Students \
  -H "Authorization: Bearer your-token"
```

### Fetch Points Log
```bash
curl -X GET http://localhost:8000/sheets/PointsLog \
  -H "Authorization: Bearer your-token"
```

### Auto-Populate New Date
```bash
curl -X POST http://localhost:8000/sheets/PointsLog/auto-populate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "date": "3/30/2026",
    "class_name": "Boys"
  }'
```

### Update Student Points
```bash
curl -X PATCH http://localhost:8000/sheets/PointsLogSheet/update \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "date": "3/23/2026",
    "class_name": "Boys",
    "student_name": "John Doe",
    "attendance": 1,
    "bible": 1,
    "book_answered": 0,
    "memory_verse": 1,
    "participation": 1,
    "bonus1_baf_1": 0,
    "bonus2_baf_2": 1,
    "bonus3_participation": 0,
    "total_points": 70
  }'
```

---

## 🐛 Troubleshooting

### Migration Issues
```bash
# Check Azure credentials
cat backend/.env

# Try migration again (safe to rerun)
python backend/migrate_sheets.py

# Check logs
tail -f backend/main.py  # if running
```

### Backend Won't Start
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Sheets Not Found
```bash
# Verify migration ran successfully
# Check SharePoint Excel file has 3 sheets:
# ✓ PointsLogSheet (original)
# ✓ Students (new)
# ✓ PointsLog (new)
```

### App Shows No Students
```bash
# This is normal for new dates!
# Option 1: Click "Auto-Populate" in app
# Option 2: Call API to auto-populate:
curl -X POST http://localhost:8000/sheets/PointsLog/auto-populate \
  -H "Content-Type: application/json" \
  -d '{"date": "3/30/2026", "class_name": "Boys"}'
```

---

## 📁 File Structure

```
AwanaPointsLogger/
├── backend/
│   ├── main.py              ← Updated with new endpoints
│   ├── migrate_sheets.py    ← Migration script
│   ├── requirements.txt
│   └── .env                 ← Credentials
├── App.js                   ← Frontend (no changes needed)
├── run-servers.sh           ← Start both servers
├── setup-normalizedschema.sh ← Automated setup
├── IMPLEMENTATION_GUIDE.md  ← Full documentation
├── MIGRATION_GUIDE.md       ← Migration details
├── FRONTEND_ENHANCEMENT.md  ← Optional UI upgrade
└── README.md
```

---

## 🎯 Workflow Examples

### Example 1: First Time Setup
```bash
# 1. Run migration
./setup-normalizedschema.sh

# 2. Verify in SharePoint (3 sheets now exist)

# 3. Start servers
./run-servers.sh

# 4. Test app with existing date
# Should show all students

# 5. Test with new date
# Should show option to auto-populate
```

### Example 2: Add New Student to Class
```bash
# 1. Stop servers (optional)
Ctrl+C

# 2. Open Excel in SharePoint
# 3. Go to Students sheet
# 4. Add: [43, NewStudent, Boys]
# 5. Save
# 6. Restart servers
./run-servers.sh

# 7. New student appears in app
# for all future dates
```

### Example 3: Log Points for New Sunday
```bash
# 1. Start app: ./run-servers.sh
# 2. Select Sunday: 3/30/2026
# 3. Select Class: Boys
# 4. Click: "Auto-Populate Boys Class"
# 5. App shows 21 students
# 6. Toggle points for each student
# 7. Done! All points synced to Excel
```

---

## 📞 Sheet Definitions

### Students Sheet
```
Column A: StudentID      (integer, starting at 1)
Column B: Name           (string, full name)
Column C: Class          (string, "Boys" or "Girls")
```

### PointsLog Sheet
```
Column A: Date           (string, format M/D/YYYY)
Column B: StudentID      (integer, reference to Students)
Column C: Class          (string, "Boys" or "Girls")
Column D: Attendance     (0 or 1)
Column E: Bible          (0 or 1)
Column F: BookAnswered   (0 or 1)
Column G: MemoryVerse    (0 or 1)
Column H: Participation  (0 or 1)
Column I: Bonus1_BAF1    (0 or 1)
Column J: Bonus2_BAF2    (0 or 1)
Column K: Bonus3_Participation (0 or 1)
Column L: TotalPoints    (integer, calculated total)
```

---

## 🔍 Verification Checklist

- [ ] Migration script runs without errors
- [ ] Excel file has 3 sheets: PointsLogSheet, Students, PointsLog
- [ ] Students sheet has all unique students
- [ ] PointsLog sheet has all migrated data
- [ ] Backend starts: `python main.py`
- [ ] Frontend loads: `http://localhost:8081`
- [ ] Existing date shows students
- [ ] New date shows auto-populate option
- [ ] Points can be updated and synced

---

## 🆘 Emergency Commands

### Restart Everything
```bash
# Kill all processes
pkill -f "python"
pkill -f "npm"

# Restart servers
cd /Users/deq/Documents/DBDNJ_Dev/AwanaPointsLogger
./run-servers.sh
```

### Reinstall Dependencies
```bash
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Check Server Status
```bash
# Check if ports are in use
lsof -i :8000  # Backend
lsof -i :8081  # Frontend

# Check running processes
ps aux | grep python
ps aux | grep npm
```

---

## 📚 Documentation Quick Links

- **Full Implementation Details**: `IMPLEMENTATION_GUIDE.md`
- **Migration Step-by-Step**: `MIGRATION_GUIDE.md`
- **Frontend UI Enhancement**: `FRONTEND_ENHANCEMENT.md`
- **Backend API Reference**: See "API Calls" section above
- **Troubleshooting Guide**: `MIGRATION_GUIDE.md` (Troubleshooting section)

---

## ⚡ Pro Tips

1. **Run migration once, then forget about it**
   - Script is idempotent (safe to rerun)
   - Data is never duplicated

2. **Auto-populate is more than a UI feature**
   - You can call it via API too
   - Useful for batch operations

3. **Excel is your database**
   - Can edit directly in SharePoint
   - Changes sync immediately to the app

4. **No frontend code needed**
   - Backward compatible
   - Works with or without UI enhancement

5. **Historical data preserved**
   - Original PointsLogSheet remains
   - Can compare old vs. new format

---

**For detailed instructions, see the full documentation files!** 📖
