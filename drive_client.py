import io
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

SUPPORTED_MIME = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "application/vnd.google-apps.document": ".txt",
}

def get_drive_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)

def list_files(service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    results = []
    page_token = None
    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token
        ).execute()
        for f in response.get("files", []):
            if f["mimeType"] in SUPPORTED_MIME:
                results.append({
                    "id": f["id"],
                    "name": f["name"],
                    "mimeType": f["mimeType"],
                    "extension": SUPPORTED_MIME[f["mimeType"]],
                })
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return results

def download_file(service, file_info):
    buffer = io.BytesIO()
    if file_info["mimeType"] == "application/vnd.google-apps.document":
        request = service.files().export_media(fileId=file_info["id"], mimeType="text/plain")
    else:
        request = service.files().get_media(fileId=file_info["id"])
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()