from .models import OAuthToken
from django.utils import timezone
import datetime
import os
import json
import requests
from django.conf import settings


def save_token(user_email, provider, token_data):
    expires_in = token_data.get("expires_in")
    expires_at = (
        timezone.now() + datetime.timedelta(seconds=expires_in) if expires_in else None
    )
    OAuthToken.objects.update_or_create(
        user_email=user_email,
        provider=provider,
        defaults={
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": expires_at,
        },
    )


def get_token(user_email, provider):
    print(f"[get_token] user_email={user_email!r}, provider={provider!r}")
    tokens = OAuthToken.objects.all()
    print(f"[get_token] All tokens in DB: {[str(t) for t in tokens]}")
    token = OAuthToken.objects.filter(user_email=user_email, provider=provider).first()
    print(f"[get_token] Query result: {token}")
    if token:
        if token.expires_at and token.expires_at > timezone.now():
            return token.access_token
        # 만료된 경우 refresh 시도
        refresh_token = token.refresh_token
        if refresh_token:
            if provider == "google":
                new_token_data = refresh_google_access_token(refresh_token)
            elif provider == "onedrive":
                new_token_data = refresh_onedrive_access_token(refresh_token)
            else:
                return None
            if new_token_data and "access_token" in new_token_data:
                save_token(user_email, provider, new_token_data)
                return new_token_data["access_token"]
    return None


def refresh_google_access_token(refresh_token):
    CONFIG_FILE = os.path.join(
        settings.BASE_DIR, "oauth/credentials/googledrive-auth-client.json"
    )
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()
    return None


def refresh_onedrive_access_token(refresh_token):
    CONFIG_FILE = os.path.join(
        settings.BASE_DIR, "oauth/credentials/onedrive-auth-client.json"
    )
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    tenant_id = config.get("tenant_id", "common")
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": "https://graph.microsoft.com/.default offline_access",
    }
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()
    return None
