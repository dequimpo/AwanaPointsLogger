# Awana Points Logger

A React Native and FastAPI application for logging Awana points with Microsoft 365 and SharePoint.

## What This Repo Contains

- Expo frontend in the repository root
- FastAPI backend in `backend/`
- setup and migration scripts for the SharePoint-backed data model
- documentation in `MD/`

## Security First

This repository is prepared for GitHub publishing.

- Real credentials are not stored in tracked env files.
- Example env files are provided for local setup.
- Generated artifacts and local environments are ignored via `.gitignore`.
- A basic publication policy is documented in `SECURITY.md`.

If credentials were ever used in this workspace before this cleanup, rotate them before publishing.

## Quick Start

### 1. Install frontend dependencies

```bash
npm install
```

### 2. Install backend dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create local env files from templates

```bash
cp .env.development.example .env.development
cp backend/.env.example backend/.env
```

Fill in the copied files with your own values.

### 4. Run the backend

```bash
cd backend
source venv/bin/activate
python main.py
```

### 5. Run the frontend

```bash
npm start
```

## Environment Files

Tracked templates:

- `.env.development.example`
- `.env.production.example`
- `backend/.env.example`

Local files you create should stay untracked:

- `.env.development`
- `.env.production`
- `backend/.env`

## Repository Layout

```text
AwanaPointsLogger/
├── backend/
├── config/
├── screens/
├── services/
├── MD/
├── App.js
├── app.json
├── package.json
├── .gitignore
├── SECURITY.md
└── README.md
```

## Documentation

- `MD/SETUP_GUIDE.md`
- `MD/IMPLEMENTATION_GUIDE.md`
- `MD/INTEGRATION_SUMMARY.md`
- `MD/PRODUCTION_DEPLOYMENT_GUIDE.md`
- `MD/AZURE_AD_SETUP.md`
- `MD/MSAL_QUICK_REFERENCE.md`

## Authentication Note

Frontend code must not contain confidential client secrets.

For production auth:

- keep Azure secrets on the backend or in your deployment secret manager
- use backend-assisted token exchange for confidential flows
- avoid putting secrets in `EXPO_PUBLIC_*` variables

## Before Publishing To GitHub

Run this checklist:

1. Confirm no local `.env` files are staged.
2. Confirm no generated output such as `dist/`, `node_modules/`, or virtual environments is staged.
3. Confirm no screenshots, logs, or docs contain tenant IDs, client IDs, or secrets you do not want public.
4. Rotate any credential that was previously stored in this workspace.
5. Review `SECURITY.md`.

## License

Add the license your organization wants before making the repository public.
