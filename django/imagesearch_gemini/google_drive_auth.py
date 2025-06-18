import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CREDENTIALS_FILE = os.path.join(
    os.path.dirname(__file__), "../../google-auth-client.json"
)
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "../../token.pickle")


def get_drive_service():
    """
    인증된 Google Drive API 서비스 객체를 반환합니다.
    최초 실행 시 인증 과정을 거치고, 이후에는 토큰을 재사용합니다.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)
    service = build("drive", "v3", credentials=creds)
    return service
