import os
import json
import jwt
from msal import ConfidentialClientApplication
from django.conf import settings
from .utils import save_token

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

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"


def build_auth_url():
    app = ConfidentialClientApplication(
        CLIENT_ID, client_credential=CLIENT_SECRET, authority=AUTHORITY
    )
    auth_url = app.get_authorization_request_url(
        scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    return auth_url


def get_token_from_code(auth_code):
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
