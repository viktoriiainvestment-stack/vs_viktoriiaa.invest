"""Google Drive upload: кожен проект отримує свою підпапку всередині
спільної папки "Ринок" (назва налаштовується), куди складається кожен
файл/нотатка, яку скидає інвестор.

Потребує сервісний акаунт Google (GOOGLE_SERVICE_ACCOUNT_JSON) і папку на
Google Диску, розшарену на його email з правами редактора
(GOOGLE_DRIVE_PARENT_FOLDER_ID) — див. investor_bot/README.md.
"""
import io
import json
import os

MARKET_FOLDER_NAME = os.environ.get("GOOGLE_DRIVE_MARKET_FOLDER_NAME", "Ринок")
PARENT_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_PARENT_FOLDER_ID", "")
SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

_service = None
_market_folder_id = None


def is_configured():
    return bool(SERVICE_ACCOUNT_JSON)


def _get_service():
    global _service
    if _service is not None:
        return _service
    if not SERVICE_ACCOUNT_JSON:
        return None
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive"]
    )
    _service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _service


def _find_folder(service, name, parent_id):
    parent_clause = f"'{parent_id}' in parents" if parent_id else "'root' in parents"
    query = (
        f"mimeType = 'application/vnd.google-apps.folder' and name = '{name}' "
        f"and {parent_clause} and trashed = false"
    )
    result = service.files().list(q=query, fields="files(id, webViewLink)", spaces="drive").execute()
    files = result.get("files", [])
    return files[0] if files else None


def _create_folder(service, name, parent_id):
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id] if parent_id else [],
    }
    folder = service.files().create(body=metadata, fields="id, webViewLink").execute()
    return folder


def _ensure_folder(name, parent_id):
    service = _get_service()
    if not service:
        return None
    existing = _find_folder(service, name, parent_id)
    if existing:
        return existing
    return _create_folder(service, name, parent_id)


def market_folder():
    """Спільна папка "Ринок" (кешується на час роботи процесу)."""
    global _market_folder_id
    if _market_folder_id:
        return _market_folder_id
    folder = _ensure_folder(MARKET_FOLDER_NAME, PARENT_FOLDER_ID)
    if not folder:
        return None
    _market_folder_id = folder
    return folder


def project_folder(project_name):
    """Підпапка проекту всередині "Ринок". Повертає {"id", "webViewLink"} або None."""
    market = market_folder()
    if not market:
        return None
    return _ensure_folder(project_name, market["id"])


def upload_bytes(folder_id, filename, data, mime_type="application/octet-stream"):
    """Завантажує файл у папку Drive. Повертає {"id", "webViewLink"} або None."""
    service = _get_service()
    if not service or not folder_id:
        return None
    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
    metadata = {"name": filename, "parents": [folder_id]}
    file = service.files().create(
        body=metadata, media_body=media, fields="id, webViewLink"
    ).execute()
    return file
