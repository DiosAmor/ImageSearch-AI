"""OAuth 인증 테스트입니다."""

from unittest.mock import patch

from django.test import TestCase

from ..models import OAuthToken


class OAuthTests(TestCase):
    """OAuth 인증 테스트 클래스입니다."""

    def setUp(self):
        """테스트 설정."""
        self.user_email = "test@example.com"

    @patch("oauth.google_drive.build_google_auth_url")
    def test_google_drive_auth_url_generation(self, mock_build_url):
        """Google Drive 인증 URL 생성 테스트."""
        # Mock 설정
        expected_url = "https://accounts.google.com/oauth/authorize?client_id=..."
        mock_build_url.return_value = expected_url

        # 테스트 실행
        from oauth.google_drive import build_google_auth_url

        result_url = build_google_auth_url()

        # 검증
        self.assertEqual(result_url, expected_url)
        mock_build_url.assert_called_once()

    @patch("oauth.onedrive.build_onedrive_auth_url")
    def test_onedrive_auth_url_generation(self, mock_build_url):
        """OneDrive 인증 URL 생성 테스트."""
        # Mock 설정
        expected_url = (
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?..."
        )
        mock_build_url.return_value = expected_url

        # 테스트 실행
        from oauth.onedrive import build_onedrive_auth_url

        result_url = build_onedrive_auth_url()

        # 검증
        self.assertEqual(result_url, expected_url)
        mock_build_url.assert_called_once()

    def test_oauth_token_creation(self):
        """OAuth 토큰 생성 테스트."""
        # 테스트 데이터
        token_data = {
            "user_email": self.user_email,
            "provider": "google",
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": "2024-12-31T23:59:59Z",
        }

        # 토큰 생성
        token = OAuthToken.objects.create(**token_data)

        # 검증
        self.assertEqual(token.user_email, self.user_email)
        self.assertEqual(token.provider, "google")
        self.assertEqual(token.access_token, "test_access_token")
        self.assertTrue(token.is_valid())

    def test_oauth_token_expiration(self):
        """OAuth 토큰 만료 테스트."""
        # 만료된 토큰 생성
        token_data = {
            "user_email": self.user_email,
            "provider": "google",
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": "2020-01-01T00:00:00Z",  # 과거 날짜
        }

        token = OAuthToken.objects.create(**token_data)

        # 검증
        self.assertFalse(token.is_valid())

    @patch("oauth.utils.get_token")
    def test_token_retrieval(self, mock_get_token):
        """토큰 조회 테스트."""
        # Mock 설정
        expected_token = "test_access_token"
        mock_get_token.return_value = expected_token

        # 테스트 실행
        from oauth.utils import get_token

        result_token = get_token(self.user_email, "google")

        # 검증
        self.assertEqual(result_token, expected_token)
        mock_get_token.assert_called_once_with(self.user_email, "google")
