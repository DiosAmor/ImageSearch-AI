"""검색 엔진 테스트입니다."""

from unittest.mock import Mock, patch

from django.test import TestCase

from ..utils.search import VectorSearchEngine


class SearchEngineTests(TestCase):
    """검색 엔진 테스트 클래스입니다."""

    @patch("imagesearch_gemini.utils.search.SearchQuery")
    @patch("imagesearch_gemini.utils.search.get_text_embedding")
    def test_get_query_embedding_db_hit(self, mock_get_embedding, mock_search_query):
        """데이터베이스 히트 테스트."""
        # Mock 설정
        mock_query_obj = Mock()
        mock_query_obj.query_embedding = [0.1, 0.2, 0.3] * 469
        mock_search_query.objects.filter.return_value.first.return_value = (
            mock_query_obj
        )

        # 테스트 실행
        result = VectorSearchEngine._get_query_embedding("test query")

        # 검증
        self.assertEqual(result, mock_query_obj.query_embedding)
        mock_get_embedding.assert_not_called()

    @patch("imagesearch_gemini.utils.search.SearchQuery")
    @patch("imagesearch_gemini.utils.search.get_text_embedding")
    def test_get_query_embedding_new_generation(
        self, mock_get_embedding, mock_search_query
    ):
        """새로운 임베딩 생성 테스트."""
        # Mock 설정
        mock_search_query.objects.filter.return_value.first.return_value = None

        new_embedding = [0.1, 0.2, 0.3] * 469
        mock_get_embedding.return_value = ("multimodalembedding@001", new_embedding)

        # 테스트 실행
        result = VectorSearchEngine._get_query_embedding("test query")

        # 검증
        self.assertEqual(result, new_embedding)
        mock_get_embedding.assert_called_once_with("test query")
        mock_search_query.objects.create.assert_called_once()

    @patch("imagesearch_gemini.utils.search.SearchQuery")
    @patch("imagesearch_gemini.utils.search.get_text_embedding")
    def test_get_query_embedding_error_handling(
        self, mock_get_embedding, mock_search_query
    ):
        """임베딩 생성 오류 처리 테스트."""
        # Mock 설정
        mock_search_query.objects.filter.return_value.first.return_value = None
        mock_get_embedding.side_effect = Exception("API Error")

        # 테스트 실행
        result = VectorSearchEngine._get_query_embedding("test query")

        # 검증
        self.assertIsNone(result)
        mock_get_embedding.assert_called_once_with("test query")
