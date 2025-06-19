import os
import json
import jwt
from msal import ConfidentialClientApplication
from django.conf import settings
from .utils import save_token, get_token
import requests

CONFIG_FILE = os.path.join(
    settings.BASE_DIR, "oauth/credentials/onedrive-auth-client.json"
)

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)
CLIENT_ID = config["client_id"]
CLIENT_SECRET = config["client_secret"]
TENANT_ID = config.get("tenant_id", "common")
SCOPES = config.get("scopes", ["Files.Read"])
REDIRECT_URI = config.get(
    "redirect_uri", "http://localhost:8000/oauth/onedrive-redirect/"
)

# tenant는 onedrive 못 보게 함. 수정할 것.
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"


def build_onedrive_auth_url():
    app = ConfidentialClientApplication(
        CLIENT_ID, client_credential=CLIENT_SECRET, authority=AUTHORITY
    )
    auth_url = app.get_authorization_request_url(
        scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    return auth_url


def get_onedrive_token_from_code(auth_code):
    app = ConfidentialClientApplication(
        CLIENT_ID, client_credential=CLIENT_SECRET, authority=AUTHORITY
    )
    result = app.acquire_token_by_authorization_code(
        code=auth_code, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )

    # 토큰 DB 저장
    user_email = None
    if "id_token_claims" in result:
        user_email = result["id_token_claims"].get("preferred_username")
    elif "id_token" in result:
        id_claims = jwt.decode(result["id_token"], options={"verify_signature": False})
        user_email = id_claims.get("preferred_username")

    if user_email:
        save_token(
            user_email,
            "onedrive",
            {
                "access_token": result.get("access_token"),
                "refresh_token": result.get("refresh_token"),
                "expires_in": result.get("expires_in"),
            },
        )
    return result


def list_images_in_onedrive(user_email, top=20):
    """
    인증된 사용자의 OneDrive에서 이미지 파일 목록을 가져온다.
    인증이 안 되어 있으면 인증 URL을 반환하는 Exception을 발생시킨다.
    반환: [{'id': ..., 'name': ..., 'webUrl': ...}, ...]
    """
    access_token = get_token(user_email, "onedrive")
    if not access_token:
        auth_url = build_onedrive_auth_url()
        # 올바른 OneDrive 인증 URL을 안내
        raise Exception(
            f"OneDrive 인증이 필요합니다. <a href='{auth_url}' target='_blank'>OneDrive 인증하기</a>"
        )
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    url = f"https://graph.microsoft.com/v1.0/me/drive/root/children?$top={top}&$filter=startswith(file/mimeType,'image/')"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        items = response.json().get("value", [])
        return items
    else:
        raise Exception(f"OneDrive 목록 조회 실패: {response.text}")
