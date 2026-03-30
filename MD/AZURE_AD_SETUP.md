# Azure AD Setup

This guide covers the minimum Azure AD configuration required for this project.

## Prerequisites

- access to an Azure AD tenant
- permission to create or manage app registrations
- access to the Azure portal

## Register The Application

1. Open the Azure portal.
2. Go to Azure Active Directory.
3. Open App registrations.
4. Create a new registration.
5. Choose single-tenant unless you explicitly need multi-tenant access.

Save these values after registration:

```text
Application (client) ID
Directory (tenant) ID
```

## Configure Redirect URIs

Add the redirect URIs required by your frontend platform.

Example values:

```text
awanapointslogger://
https://yourdomain.example/auth/callback
```

## Create A Client Secret

1. Open Certificates & secrets.
2. Create a new client secret.
3. Copy it once and store it in a secret manager.

Do not commit the secret to this repository.

## Grant API Permissions

Grant the minimum permissions your app needs.

Typical Microsoft Graph permissions for this project:

- User.Read
- Sites.Read.All
- Files.Read.All

If your tenant requires admin consent, complete that step before testing.

## Local Configuration

Use local untracked env files created from the example files in this repository.

Backend example:

```bash
cp backend/.env.example backend/.env
```

Frontend example:

```bash
cp .env.production.example .env.production
```

Then fill in values such as:

```text
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
EXPO_PUBLIC_AZURE_CLIENT_ID=your-client-id
EXPO_PUBLIC_AZURE_TENANT_ID=your-tenant-id
```

## Validation Checklist

1. Confirm the backend starts with local env values.
2. Confirm the frontend uses your local env file, not hardcoded IDs.
3. Confirm no secrets are staged in git.
4. Confirm your redirect URI matches Azure exactly.
5. Confirm Graph permissions are granted.

## Security Notes

- keep client secrets on the backend only
- use a deployment secret manager for production
- rotate any credential that was previously stored in this workspace
- review `SECURITY.md` before publishing the repository
