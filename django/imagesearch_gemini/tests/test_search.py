"""검색 엔진 테스트입니다."""

from unittest.mock import Mock, patch

from django.test import TestCase

from ..utils.search import VectorSearchEngine


class SearchEngineTests(TestCase):
    """검색 엔진 테스트 클래스입니다."""

    @patch("imagesearch_gemini.utils.search.cache")
    @patch("imagesearch_gemini.utils.search.get_text_embedding")
    def test_get_cached_query_embedding_cache_hit(self, mock_get_embedding, mock_cache):
        """캐시 히트 테스트."""
        # Mock 설정
        cached_embedding = [0.1, 0.2, 0.3] * 469
        mock_cache.get.return_value = cached_embedding

        # 테스트 실행
        result = VectorSearchEngine._get_cached_query_embedding("test query")

        # 검증
        self.assertEqual(result, cached_embedding)
        mock_cache.get.assert_called_once_with("query_embedding:test query")
        mock_get_embedding.assert_not_called()

    @patch("imagesearch_gemini.utils.search.cache")
    @patch("imagesearch_gemini.utils.search.SearchQuery")
    @patch("imagesearch_gemini.utils.search.get_text_embedding")
    def test_get_cached_query_embedding_db_hit(
        self, mock_get_embedding, mock_search_query, mock_cache
    ):
        """데이터베이스 히트 테스트."""
        # Mock 설정
        mock_cache.get.return_value = None

        mock_query_obj = Mock()
        mock_query_obj.query_embedding = [0.1, 0.2, 0.3] * 469
        mock_search_query.objects.filter.return_value.first.return_value = (
            mock_query_obj
        )

        # 테스트 실행
        result = VectorSearchEngine._get_cached_query_embedding("test query")

        # 검증
        self.assertEqual(result, mock_query_obj.query_embedding)
        mock_cache.set.assert_called_once()
        mock_get_embedding.assert_not_called()

    @patch("imagesearch_gemini.utils.search.cache")
    @patch("imagesearch_gemini.utils.search.SearchQuery")
    @patch("imagesearch_gemini.utils.search.get_text_embedding")
    def test_get_cached_query_embedding_new_generation(
        self, mock_get_embedding, mock_search_query, mock_cache
    ):
        """새로운 임베딩 생성 테스트."""
        # Mock 설정
        mock_cache.get.return_value = None
        mock_search_query.objects.filter.return_value.first.return_value = None

        new_embedding = [0.1, 0.2, 0.3] * 469
        mock_get_embedding.return_value = ("multimodalembedding@001", new_embedding)

        # 테스트 실행
        result = VectorSearchEngine._get_cached_query_embedding("test query")

        # 검증
        self.assertEqual(result, new_embedding)
        mock_get_embedding.assert_called_once_with("test query")
        mock_cache.set.assert_called_once()

    def test_clear_query_cache(self):
        """검색어 캐시 삭제 테스트."""
        with patch("imagesearch_gemini.utils.search.cache") as mock_cache:
            VectorSearchEngine.clear_query_cache("test query")
            mock_cache.delete.assert_called_once_with("query_embedding:test query")
