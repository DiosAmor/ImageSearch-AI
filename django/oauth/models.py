from django.db import models


class OAuthToken(models.Model):
    user_email = models.CharField(max_length=255)
    provider = models.CharField(max_length=30)  # 예: 'google', 'onedrive'

    # user_email + provider 조합이 유일하도록 unique_together 설정
    class Meta:
        unique_together = ("user_email", "provider")

    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.provider} - {self.user_email}"
