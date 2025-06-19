from .models import OAuthToken
from django.utils import timezone
import datetime


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
    token = OAuthToken.objects.filter(user_email=user_email, provider=provider).first()
    if token and token.expires_at and token.expires_at > timezone.now():
        return token.access_token
    return None
