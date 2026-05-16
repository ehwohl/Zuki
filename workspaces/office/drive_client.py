"""
drive_client.py — Google Drive API wrapper for OfficeSkill
───────────────────────────────────────────────────────────
Env vars:
  GOOGLE_CREDENTIALS_FILE  — path to OAuth2 client_secret JSON
                             (default: credentials.json in project root)

Token cache: memory/office_token.json  (gitignored)

Scopes:
  drive.readonly — list and read files for indexing
  drive.file     — upload files created by Zuki (own files only)

Log marker: [DRIVE]
"""

import os
from pathlib import Path

from core.logger import get_logger

log = get_logger("office.drive")

_ROOT       = Path(__file__).resolve().parent.parent.parent
_TOKEN_FILE = _ROOT / "memory" / "office_token.json"
_CREDS_FILE = Path(os.getenv("GOOGLE_CREDENTIALS_FILE", str(_ROOT / "credentials.json")))

_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]


def _get_creds():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise RuntimeError(
            "Google-Bibliotheken fehlen. Ausführen: "
            "pip install google-auth google-auth-oauthlib google-api-python-client"
        )

    creds = None
    if _TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not _CREDS_FILE.exists():
                raise FileNotFoundError(
                    f"Google-Zugangsdaten nicht gefunden: {_CREDS_FILE}\n"
                    "Download: Google Cloud Console → APIs & Dienste → Zugangsdaten → OAuth 2.0-Client-IDs"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDS_FILE), _SCOPES)
            creds = flow.run_local_server(port=0)

        _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_FILE.write_text(creds.to_json())
        log.info("[DRIVE] Token gespeichert → %s", _TOKEN_FILE)

    return creds


def build_service():
    """Return an authenticated Google Drive v3 service object."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        raise RuntimeError("Ausführen: pip install google-api-python-client")

    svc = build("drive", "v3", credentials=_get_creds())
    log.info("[DRIVE] Dienst verbunden")
    return svc


# ── File listing ──────────────────────────────────────────────────────────────

def list_all_files(service, folder_id: str | None = None) -> list[dict]:
    """
    List all non-trashed files in Drive.
    If folder_id is given, scoped to that folder subtree via Drive query.
    Returns list of dicts: id, name, mimeType, webViewLink, modifiedTime, parents.
    """
    q = "trashed = false and mimeType != 'application/vnd.google-apps.folder'"
    if folder_id:
        q = f"'{folder_id}' in parents and {q}"

    results: list[dict] = []
    page_token = None
    while True:
        resp = service.files().list(
            q         = q,
            pageSize  = 500,
            fields    = "nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime, parents)",
            pageToken = page_token,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    log.info("[DRIVE] list_all_files → %d Dateien", len(results))
    return results


def get_folder_map(service) -> dict[str, str]:
    """Returns {folder_id: folder_name} for all Drive folders."""
    folders: list[dict] = []
    page_token = None
    while True:
        resp = service.files().list(
            q         = "mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            pageSize  = 500,
            fields    = "nextPageToken, files(id, name, parents)",
            pageToken = page_token,
        ).execute()
        folders.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return {f["id"]: f["name"] for f in folders}


# ── Upload ────────────────────────────────────────────────────────────────────

def find_or_create_folder(service, name: str, parent_id: str = "root") -> str:
    """Find a folder by name under parent_id, or create it. Returns folder_id."""
    q = (
        f"name = '{name}' and "
        f"'{parent_id}' in parents and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"trashed = false"
    )
    resp  = service.files().list(q=q, fields="files(id)", pageSize=1).execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]

    folder = service.files().create(
        body   = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
        fields = "id",
    ).execute()
    log.info("[DRIVE] Ordner erstellt: '%s' (parent=%s)", name, parent_id)
    return folder["id"]


def upload_file(service, local_path: Path, folder_id: str, mime_type: str = "application/pdf") -> str:
    """
    Upload local_path into folder_id.
    Returns the web view link of the uploaded file.
    """
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        raise RuntimeError("Ausführen: pip install google-api-python-client")

    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
    file  = service.files().create(
        body       = {"name": local_path.name, "parents": [folder_id]},
        media_body = media,
        fields     = "id, webViewLink",
    ).execute()

    link = file.get("webViewLink", "")
    log.info("[DRIVE] Hochgeladen: %s → %s", local_path.name, link)
    return link
