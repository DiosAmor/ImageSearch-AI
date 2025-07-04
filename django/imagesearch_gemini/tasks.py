import logging

from celery import shared_task

from .models import ImageEmbedding
from .utils.embeddings import get_image_embedding
from .utils.logger import log_embedding_generation

logger = logging.getLogger(__name__)


@shared_task
def generate_image_embedding_task(image_embedding_id):
    try:
        image_embedding = ImageEmbedding.objects.get(id=image_embedding_id)
        file_path = image_embedding.image_path  # Django storage 경로 그대로 사용
        # 임베딩 생성
        embedding_model, embedding = get_image_embedding(file_path)
        image_embedding.embedding = embedding
        image_embedding.embedding_model = embedding_model
        image_embedding.embedding_status = "done"
        image_embedding.save()
    except Exception as e:
        logger.error(f"임베딩 생성 실패: {e}")
        try:
            image_embedding = ImageEmbedding.objects.get(id=image_embedding_id)
            image_embedding.embedding_status = "failed"
            image_embedding.save()
        except Exception:
            pass


@shared_task
def retry_failed_embeddings() -> int:
    """실패한 임베딩들을 재시도하는 태스크입니다.

    Returns:
        재시도된 태스크 수

    """
    failed_images = ImageEmbedding.objects.filter(embedding_status="failed")
    retry_count = 0

    for image in failed_images:
        try:
            generate_image_embedding_task.delay(image.id)
            retry_count += 1
        except Exception as e:
            # 개별 실패는 로깅만 하고 계속 진행
            log_embedding_generation(image.id, "failed", f"Retry failed: {e}")

    return retry_count
