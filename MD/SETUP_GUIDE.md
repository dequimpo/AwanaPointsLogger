# Awana Points Logger - Setup Guide

A full-stack mobile app for logging Awana points using Microsoft 365 SharePoint as a database.

## Project Structure

```
awana-points-logger/
├── backend/
│   ├── main.py                 # FastAPI backend with MS Graph integration
│   ├── requirements.txt         # Python dependencies
│   └── .env                     # Environment variables (create this)
├── frontend/
│   ├── App.js                  # React Native app
│   └── package.json            # Node dependencies
└── README.md
```

---

## Backend Setup (FastAPI)

### 1. Prerequisites
- Python 3.9+
- Microsoft 365 subscription with SharePoint access
- Azure AD app registration

### 2. Azure AD Setup
1. Go to [Azure Portal](https://portal.azure.com)
2. Create a new **App Registration**:
   - Name: `Awana Points Logger`
   - Supported account types: Select based on your organization
3. Copy these values:
   - **Client ID** `<your_client_id>`
   - **Tenant ID** `<your_tenant_id>`
4. Create a **Client Secret**:
   - Go to Certificates & secrets
   - Add new client secret
   - Copy the value
5. Set **API Permissions**: done
   - Add: `Files.ReadWrite.All` and `Sites.ReadWrite.All`
   - Grant admin consent

### 3. SharePoint Setup
1. Create a SharePoint site or use existing
2. Upload an Excel file named `PointsLogSheet.xlsx` with columns:
   - A: Date
   - B: Class
   - C: Student Name
   - D: Attendance
   - E: Bible
   - F: BookAnswered
   - G: MemoryVerse
   - H: Participation
   - I: Bonus1-BAF-1
   - J: Bonus2-BAF-2
   - K: Bonus3-Participation
   - L: Total Points
3. Get the **Site ID** and **Drive ID**:
   ```bash
   # Use Microsoft Graph Explorer to get these IDs
   # GET /sites/{hostname}:{site-path}
   # GET /drives
   ```
Site "id": <your_site_id>
** Modify Permission consent Files.Read.All and Sites.Read.All
Drive "id": <your_drive_id>

### 4. Install Python Dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Create `.env` File
```
AZURE_CLIENT_ID=<your_client_id>
AZURE_CLIENT_SECRET=<your_client_secret>
AZURE_TENANT_ID=<your_tenant_id>
SHAREPOINT_SITE_ID=<your_site_id>
SHAREPOINT_DRIVE_ID=<your_drive_id>
SHAREPOINT_FILE_ID=<your_file_id>
```

### 6. Run Backend
```bash
python main.py
# Server runs on http://localhost:8000
```

### 7. Test API
```bash
# Health check
curl http://localhost:8000/health

# Get API docs
# Visit http://localhost:8000/docs in your browser
```

---

## Frontend Setup (React Native/Expo)

### 1. Prerequisites
- Node.js 16+
- Expo CLI: `npm install -g expo-cli`
- iOS Simulator (macOS) or Android Emulator

### 2. Install Dependencies
```bash
cd frontend
npm install
```

### 3. Configure Backend URL
Edit `App.js` and update:
```javascript
const API_BASE_URL = 'http://your-backend-ip:8000';
const ACCESS_TOKEN = 'your-access-token';
```

### 4. Run App
```bash
npm start

# For iOS
npm run ios

# For Android
npm run android

# For Web
npm run web
```

---

## Authentication Flow

### Option 1: Server-Side Auth (Recommended)
1. Frontend uses MSAL Web library to authenticate
2. User receives authorization code
3. Send code to backend `/auth/token` endpoint
4. Backend exchanges for access token
5. Frontend uses token for subsequent API calls

### Option 2: Direct Token Access
1. Store access token securely on device after login
2. Pass token in `Authorization` header for all requests

---

## Excel Data Schema

| Column | Field | Type | Notes |
|--------|-------|------|-------|
| A | Date | YYYY-MM-DD | Sunday date |
| B | Class | Text | Boys or Girls |
| C | Student Name | Text | Full name |
| D | Attendance | 0/1 | 10 points |
| E | Bible | 0/1 | 10 points |
| F | BookAnswered | 0/1 | 10 points |
| G | MemoryVerse | 0/1 | 10 points |
| H | Participation | 0/1 | 10 points |
| I | Bonus1-BAF-1 | 0/1 | 10 points |
| J | Bonus2-BAF-2 | 0/1 | 10 points |
| K | Bonus3-Participation | 0/1 | 10 points |
| L | Total Points | Formula | SUM(D:K)*10 |

---

## API Endpoints

### `POST /auth/token`
Exchange authorization code for access token.
```json
{
  "code": "auth_code_from_msal",
  "redirect_uri": "your_redirect_uri"
}
```

### `GET /sheets/PointsLogSheet`
Fetch all data from the Excel sheet.
- **Headers**: `Authorization: Bearer {access_token}`
- **Returns**: Headers and data rows

### `PATCH /sheets/PointsLogSheet/update`
Update a specific student row.
```json
{
  "date": "2024-03-24",
  "class_name": "Boys",
  "student_name": "John Doe",
  "attendance": 1,
  "bible": 1,
  "participation": 0
}
```

### `GET /sheets/classes`
Get available class options.

### `GET /health`
Health check endpoint.

---

## Frontend Features

### Screen 1: Date & Class Selection
- Date picker (rounds to nearest Sunday)
- Toggle between Boys/Girls classes
- Continue button to proceed to logging

### Screen 2: Student Logging List
- Displays filtered students by date and class
- 8 toggle switches per student:
  - Attendance, Bible, Book Answered, Memory Verse
  - Participation, Bonus 1, Bonus 2, Bonus 3
- Real-time sync to backend on toggle change
- Total points display
- Loading indicators during sync

---

## Helpful Tips

### Testing Backend
Use [Insomnia](https://insomnia.rest) or [Postman](https://www.postman.com/):
1. Get access token from `/auth/token`
2. Copy token to header: `Authorization: Bearer token`
3. Test GET `/sheets/PointsLogSheet`
4. Test PATCH with student update

### Debugging
- Backend logs: Check console output from `python main.py`
- Frontend logs: Open Expo DevTools (press 'i' in terminal)
- Network: Use React Native debugger to inspect network requests

### Production Deployment
**Backend:**
- Deploy to Azure App Service, Heroku, or DigitalOcean
- Use environment variables for secrets
- Enable HTTPS
- Configure CORS properly

**Frontend:**
- Build: `eas build --platform all`
- Submit to App Store/Google Play
- Use secure storage for tokens (react-native-secure-store)

---

## Troubleshooting

### Backend Issues
- **401 Unauthorized**: Check Client ID, Secret, Tenant ID
- **404 File not found**: Verify Site ID, Drive ID, File ID
- **CORS errors**: Check frontend URL in CORS middleware

### Frontend Issues
- **Can't reach backend**: Verify API_BASE_URL and network connectivity
- **Toggles not syncing**: Check network tab for failed requests
- **Token expired**: Implement token refresh logic

### Excel Issues
- **Formulas overwritten**: Ensure Total Points column uses formula, not values
- **Empty cells**: Null values in Excel show as empty; update to 0 if needed

---

## Security Checklist
- [ ] Store secrets in environment variables only
- [ ] Use HTTPS in production
- [ ] Implement token refresh on frontend
- [ ] Add request validation on backend
- [ ] Enable row-level security in SharePoint
- [ ] Use role-based access control
- [ ] Audit log changes to Excel file
- [ ] Secure stored tokens on mobile device

---

## Support & Resources
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Microsoft Graph](https://graph.microsoft.com/en-us/)
- [React Native Docs](https://reactnative.dev/)
- [Expo Docs](https://docs.expo.dev/)

---

**Happy Logging!**
