import os
import sys

os.environ["ENVIRONMENT"] = "development"
os.environ.setdefault("AZURE_TENANT_ID", "11111111-1111-1111-1111-111111111111")
os.environ.setdefault("AZURE_CLIENT_ID", "22222222-2222-2222-2222-222222222222")
os.environ.setdefault("AZURE_CLIENT_SECRET", "test-secret")
os.environ.setdefault("SHAREPOINT_DRIVE_ID", "drive-id")
os.environ.setdefault("SHAREPOINT_FILE_ID", "file-id")
os.environ.setdefault("SESSION_SECRET", "test-session-secret-at-least-32-bytes-long")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
