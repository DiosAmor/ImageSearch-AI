import os
import json
import jwt
import time
import requests
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from .utils import save_token, get_token
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

CONFIG_FILE = os.path.join(
    settings.BASE_DIR, "oauth/credentials/googledrive-auth-client.json"
)

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)
CLIENT_ID = config["client_id"]
CLIENT_SECRET = config["client_secret"]
SCOPES = config.get(
    "scopes",
    [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ],
)
REDIRECT_URI = config.get(
    "redirect_uri", "http://localhost:8000/oauth/google-drive-redirect/"
)


def build_google_auth_url():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(
        prompt="consent", access_type="offline", include_granted_scopes="true"
    )
    return auth_url


def get_google_token_from_code(code):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    # user_email 추출: id_token, _id_token, token_info 순서로 시도
    user_email = None
    if hasattr(creds, "id_token") and creds.id_token:
        try:
            idinfo = id_token.verify_oauth2_token(
                creds.id_token, requests.Request(), CLIENT_ID
            )
            user_email = idinfo.get("email")
        except Exception:
            pass
    if not user_email and hasattr(creds, "_id_token") and creds._id_token:
        try:
            id_token_bytes = (
                creds._id_token.encode()
                if isinstance(creds._id_token, str)
                else creds._id_token
            )
            idinfo = jwt.decode(id_token_bytes, options={"verify_signature": False})
            user_email = idinfo.get("email")
        except Exception:
            pass
    if not user_email and hasattr(creds, "token_info") and creds.token_info:
        user_email = creds.token_info.get("email")

    # 토큰 DB 저장
    if user_email:
        expires_in = None
        if hasattr(creds, "expiry") and creds.expiry:
            # creds.expiry는 datetime이므로, 현재 시간과의 차이(초)를 계산
            now_ts = time.time()
            expires_in = int(creds.expiry.timestamp() - now_ts)
        save_token(
            user_email,
            "google",
            {
                "access_token": creds.token,
                "refresh_token": getattr(creds, "refresh_token", None),
                "expires_in": expires_in,
            },
        )
    return creds


def list_images_in_google_drive(user_email, page_size=20):
    """
    인증된 사용자의 Google Drive에서 이미지 파일 목록을 가져온다.
    인증이 안 되어 있으면 인증 URL을 반환하는 Exception을 발생시킨다.
    반환: [{'id': ..., 'name': ..., 'webViewLink': ...}, ...]
    """
    access_token = get_token(user_email, "google")
    if not access_token:
        auth_url = build_google_auth_url()
        raise Exception(
            f"Google Drive 인증이 필요합니다. <a href='{auth_url}' target='_blank'>Google Drive 인증하기</a>"
        )
    creds = Credentials(token=access_token)
    service = build("drive", "v3", credentials=creds)
    results = (
        service.files()
        .list(
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink)",
            q="mimeType contains 'image/' and trashed = false",
        )
        .execute()
    )
    files = results.get("files", [])
    return files
