import time
from typing import List, Optional, Tuple

from django.db.models import QuerySet

from ..models import ImageEmbedding, SearchQuery
from .embeddings import get_text_embedding
from .logger import log_search_performance


class VectorSearchEngine:
    """벡터 검색 엔진 클래스입니다."""

    # 검색 결과 제한
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 50

    @classmethod
    def search_images(
        cls,
        query_text: Optional[str] = None,
        tags: Optional[str] = None,
        location: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> Tuple[QuerySet, Optional[str]]:
        """이미지를 검색합니다.

        Args:
            query_text: 검색어 (영어만 지원)
            tags: 태그 필터 (쉼표로 구분)
            location: 위치 필터
            date_from: 시작 날짜 (YYYY-MM-DD)
            date_to: 종료 날짜 (YYYY-MM-DD)
            limit: 결과 제한 수

        Returns:
            (검색 결과 QuerySet, 오류 메시지)

        """
        start_time = time.time()

        # 기본 쿼리셋
        qs = ImageEmbedding.objects.filter(embedding_status="done")

        # 필터 적용
        qs = cls._apply_filters(qs, tags, location, date_from, date_to)

        # 벡터 검색 적용
        if query_text:
            qs, error = cls._apply_vector_search(qs, query_text, limit)
            if error:
                return qs, error
        else:
            # 텍스트 검색이 없는 경우 최신 순으로 제한
            qs = qs.order_by("-created_at")[:limit]

        # 성능 로깅
        duration = time.time() - start_time
        log_search_performance(query_text or "no_query", duration, len(qs))

        return qs, None

    @classmethod
    def _apply_filters(
        cls,
        qs: QuerySet,
        tags: Optional[str],
        location: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
    ) -> QuerySet:
        """필터를 적용합니다."""
        # 태그 필터
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            for tag in tag_list:
                qs = qs.filter(tags__name__icontains=tag)

        # 위치 필터
        if location:
            qs = qs.filter(location_user__icontains=location)

        # 날짜 필터
        if date_from:
            qs = qs.filter(date_taken_exif__date__gte=date_from)
        if date_to:
            qs = qs.filter(date_taken_exif__date__lte=date_to)

        return qs

    @classmethod
    def _apply_vector_search(
        cls, qs: QuerySet, query_text: str, limit: int
    ) -> Tuple[QuerySet, Optional[str]]:
        """벡터 검색을 적용합니다."""
        # 검색어 임베딩 가져오기
        query_embedding = cls._get_query_embedding(query_text)
        if query_embedding is None:
            return qs, "검색어 임베딩 생성에 실패했습니다."

        # 벡터 유사도 검색
        vec_str = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
        qs = qs.extra(
            select={"l2": f"embedding <-> '{vec_str}'::vector"}, order_by=["l2"]
        )[:limit]

        return qs, None

    @classmethod
    def _get_query_embedding(cls, query_text: str) -> Optional[List[float]]:
        """검색어 임베딩을 가져오거나 새로 생성합니다."""
        # 데이터베이스에서 확인
        search_query = SearchQuery.objects.filter(query_text=query_text).first()
        if search_query and search_query.query_embedding is not None:
            return search_query.query_embedding

        # 새로 생성
        try:
            embedding_model, embedding = get_text_embedding(query_text)
            if embedding is not None:
                # 데이터베이스에 저장
                SearchQuery.objects.create(
                    query_text=query_text,
                    query_embedding=embedding,
                    query_embedding_model=embedding_model,
                )
                return embedding
        except Exception:
            # 로깅은 get_text_embedding에서 처리됨
            pass

        return None

    @classmethod
    def get_similar_images(cls, image_id: int, limit: int = DEFAULT_LIMIT) -> QuerySet:
        """특정 이미지와 유사한 이미지들을 찾습니다.

        Args:
            image_id: 기준 이미지 ID
            limit: 결과 제한 수

        Returns:
            유사한 이미지들의 QuerySet

        """
        try:
            # 기준 이미지 조회
            base_image = ImageEmbedding.objects.get(
                id=image_id, embedding_status="done"
            )

            if base_image.embedding is None:
                return ImageEmbedding.objects.none()

            # 유사도 검색
            vec_str = "[" + ",".join(str(float(x)) for x in base_image.embedding) + "]"
            similar_images = (
                ImageEmbedding.objects.filter(embedding_status="done")
                .exclude(
                    id=image_id  # 자기 자신 제외
                )
                .extra(
                    select={"l2": f"embedding <-> '{vec_str}'::vector"}, order_by=["l2"]
                )[:limit]
            )

            return similar_images

        except ImageEmbedding.DoesNotExist:
            return ImageEmbedding.objects.none()
