from django.contrib import admin

from .models import OAuthToken


@admin.register(OAuthToken)
class OAuthTokenAdmin(admin.ModelAdmin):
    list_display = ("user_email", "provider", "expires_at", "created_at", "updated_at")
    search_fields = ("user_email", "provider")
    list_filter = ("provider",)
