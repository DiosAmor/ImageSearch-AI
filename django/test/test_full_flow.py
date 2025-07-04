"""전체 이미지 검색 플로우 통합 테스트입니다."""

from unittest.mock import patch

from imagesearch_gemini.models import ImageEmbedding

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse


class FullFlowIntegrationTests(TestCase):
    """전체 플로우 통합 테스트 클래스입니다."""

    def setUp(self):
        """테스트 설정."""
        self.client = Client()
        self.test_image_content = b"fake image content"
        self.test_image = SimpleUploadedFile(
            "test.jpg", self.test_image_content, content_type="image/jpeg"
        )

    @patch("imagesearch_gemini.utils.embeddings.get_image_embedding")
    @patch("imagesearch_gemini.utils.embeddings.get_text_embedding")
    def test_full_image_search_flow(self, mock_text_embedding, mock_image_embedding):
        """이미지 업로드 → 임베딩 생성 → 검색 전체 플로우 테스트."""
        # Mock 설정
        mock_image_embedding.return_value = (
            "multimodalembedding@001",
            [0.1, 0.2, 0.3] * 469,
        )
        mock_text_embedding.return_value = (
            "multimodalembedding@001",
            [0.1, 0.2, 0.3] * 469,
        )

        # 1. 이미지 업로드
        upload_data = {
            "upload_type": "single",
            "date_taken": "2023-01-01",
            "location": "Seoul",
            "tags": "nature, landscape",
        }
        files = {"image": self.test_image}

        response = self.client.post(reverse("image_select"), upload_data, files=files)
        self.assertEqual(response.status_code, 200)
        self.assertIn("이미지 및 정보 저장 완료", response.content.decode())

        # 2. 임베딩 생성 확인
        image = ImageEmbedding.objects.first()
        self.assertIsNotNone(image)
        self.assertEqual(image.embedding_status, "pending")

        # 3. 임베딩 처리 (Celery 태스크 시뮬레이션)
        from imagesearch_gemini.tasks import generate_image_embedding

        generate_image_embedding(image.id)

        # 4. 임베딩 완료 확인
        image.refresh_from_db()
        self.assertEqual(image.embedding_status, "done")

        # 5. 이미지 검색
        search_data = {
            "query_text": "nature landscape",
            "tags": "nature",
            "location": "Seoul",
        }

        response = self.client.get(reverse("image_search"), search_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("test.jpg", response.content.decode())

    def test_cloud_drive_integration(self):
        """클라우드 드라이브 연동 테스트."""
        # Google Drive 연동 테스트
        with patch(
            "imagesearch_gemini.storage.google_drive.list_folders_and_images_in_google_drive"
        ) as mock_google:
            mock_google.return_value = ([], [], "내 드라이브", {})

            response = self.client.get(
                reverse("cloud_image_list"),
                {"cloud": "google", "cloud_email": "test@example.com"},
            )
            self.assertEqual(response.status_code, 200)

        # OneDrive 연동 테스트
        with patch(
            "imagesearch_gemini.storage.onedrive.list_folders_and_images_in_onedrive"
        ) as mock_onedrive:
            mock_onedrive.return_value = ([], [], "내 드라이브", {})

            response = self.client.get(
                reverse("cloud_image_list"),
                {"cloud": "onedrive", "cloud_email": "test@example.com"},
            )
            self.assertEqual(response.status_code, 200)

    def test_embedding_status_management(self):
        """임베딩 상태 관리 테스트."""
        # 이미지 생성
        image = ImageEmbedding.objects.create(
            image_path="test.jpg",
            embedding_status="failed",
            embedding_error="Test error",
        )

        # 상태 목록 확인
        response = self.client.get(reverse("embedding_status_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("test.jpg", response.content.decode())

        # 재시도 기능 테스트
        with patch("imagesearch_gemini.tasks.generate_image_embedding") as mock_retry:
            response = self.client.post(
                reverse("retry_failed_embedding", args=[image.id])
            )
            self.assertEqual(response.status_code, 200)
            mock_retry.delay.assert_called_once_with(image.id)

    def test_similar_images_feature(self):
        """유사 이미지 기능 테스트."""
        # 테스트 이미지 생성
        image = ImageEmbedding.objects.create(
            image_path="test.jpg",
            embedding_status="done",
            embedding=[0.1, 0.2, 0.3] * 469,
        )

        # 유사 이미지 검색
        response = self.client.get(reverse("similar_images", args=[image.id]))
        self.assertEqual(response.status_code, 200)

    def test_error_handling(self):
        """오류 처리 테스트."""
        # 잘못된 파일 형식 업로드
        invalid_file = SimpleUploadedFile(
            "test.txt", b"invalid content", content_type="text/plain"
        )

        upload_data = {"upload_type": "single"}
        files = {"image": invalid_file}

        response = self.client.post(reverse("image_select"), upload_data, files=files)
        self.assertEqual(response.status_code, 200)
        self.assertIn("지원하지 않는 파일 형식", response.content.decode())

        # 잘못된 검색어
        search_data = {"query_text": "테스트@검색어"}
        response = self.client.get(reverse("image_search"), search_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("영어 단어만 입력 가능합니다", response.content.decode())
