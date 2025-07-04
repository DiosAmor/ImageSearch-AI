"""임베딩 기능 테스트입니다."""

import os
import tempfile
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from ..utils.embeddings import get_image_embedding, get_text_embedding


class EmbeddingTests(TestCase):
    """임베딩 기능 테스트 클래스입니다."""

    def setUp(self):
        """테스트 설정."""
        # 테스트용 이미지 파일 생성
        self.test_image_content = b"fake image content"
        self.test_image = SimpleUploadedFile(
            "test.jpg", self.test_image_content, content_type="image/jpeg"
        )

    @patch("imagesearch_gemini.utils.embeddings._setup_google_credentials")
    @patch("imagesearch_gemini.utils.embeddings._initialize_vertex_ai")
    @patch("imagesearch_gemini.utils.embeddings.Image")
    @patch("imagesearch_gemini.utils.embeddings.log_api_usage")
    def test_get_image_embedding_success(
        self, mock_log, mock_image, mock_init, mock_setup
    ):
        """이미지 임베딩 생성 성공 테스트."""
        # Mock 설정
        mock_model = Mock()
        mock_init.return_value = mock_model

        mock_image_instance = Mock()
        mock_image.load_from_file.return_value = mock_image_instance

        mock_embeddings = Mock()
        mock_embeddings.image_embedding = [0.1, 0.2, 0.3] * 469  # 1408차원 벡터
        mock_model.get_embeddings.return_value = mock_embeddings

        # 테스트 실행
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(self.test_image_content)
            temp_file_path = temp_file.name

        try:
            model_name, embedding = get_image_embedding(temp_file_path)

            # 검증
            self.assertEqual(model_name, "multimodalembedding@001")
            self.assertIsNotNone(embedding)
            self.assertEqual(len(embedding), 1408)
            mock_setup.assert_called_once()
            mock_init.assert_called_once()
            mock_log.assert_called_with("Gemini Image Embedding", True)

        finally:
            os.unlink(temp_file_path)

    @patch("imagesearch_gemini.utils.embeddings._setup_google_credentials")
    @patch("imagesearch_gemini.utils.embeddings._initialize_vertex_ai")
    @patch("imagesearch_gemini.utils.embeddings.log_api_usage")
    def test_get_image_embedding_file_not_found(self, mock_log, mock_init, mock_setup):
        """이미지 파일이 존재하지 않는 경우 테스트."""
        # 테스트 실행
        with self.assertRaises(FileNotFoundError):
            get_image_embedding("nonexistent_file.jpg")

        mock_log.assert_called_with(
            "Gemini Image Embedding",
            False,
            "이미지 파일을 찾을 수 없습니다: nonexistent_file.jpg",
        )

    @patch("imagesearch_gemini.utils.embeddings._setup_google_credentials")
    @patch("imagesearch_gemini.utils.embeddings._initialize_vertex_ai")
    @patch("imagesearch_gemini.utils.embeddings.log_api_usage")
    def test_get_text_embedding_success(self, mock_log, mock_init, mock_setup):
        """텍스트 임베딩 생성 성공 테스트."""
        # Mock 설정
        mock_model = Mock()
        mock_init.return_value = mock_model

        mock_embeddings = Mock()
        mock_embeddings.text_embedding = [0.1, 0.2, 0.3] * 469  # 1408차원 벡터
        mock_model.get_embeddings.return_value = mock_embeddings

        # 테스트 실행
        model_name, embedding = get_text_embedding("test query")

        # 검증
        self.assertEqual(model_name, "multimodalembedding@001")
        self.assertIsNotNone(embedding)
        self.assertEqual(len(embedding), 1408)
        mock_log.assert_called_with("Gemini Text Embedding", True)

    def test_get_text_embedding_empty_text(self):
        """빈 텍스트 입력 테스트."""
        with self.assertRaises(ValueError):
            get_text_embedding("")

        with self.assertRaises(ValueError):
            get_text_embedding("   ")
