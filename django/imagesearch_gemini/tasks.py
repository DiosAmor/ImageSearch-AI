from celery import shared_task

from django.db import transaction

from .models import ImageEmbedding
from .utils.embeddings import generate_embedding_vector
from .utils.logger import log_embedding_generation


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_image_embedding(self, image_embedding_id: int) -> None:
    """이미지 임베딩을 비동기적으로 생성하는 Celery 태스크입니다.

    Args:
        image_embedding_id: ImageEmbedding 모델의 ID

    Raises:
        ImageEmbedding.DoesNotExist: 이미지를 찾을 수 없는 경우
        Exception: 임베딩 생성 실패 시 재시도

    """
    try:
        with transaction.atomic():
            # 이미지 조회 및 상태 업데이트
            image = ImageEmbedding.objects.select_for_update().get(
                id=image_embedding_id
            )

            # 이미 처리 중이거나 완료된 경우 스킵
            if image.embedding_status in ["processing", "done"]:
                return

            # 상태를 processing으로 변경
            image.embedding_status = "processing"
            image.embedding_error = None
            image.save(update_fields=["embedding_status", "embedding_error"])

            log_embedding_generation(image_embedding_id, "processing")

        # 임베딩 생성 (트랜잭션 외부에서 실행)
        embedding = generate_embedding_vector(image.image_path)

        with transaction.atomic():
            # 결과 저장
            image = ImageEmbedding.objects.select_for_update().get(
                id=image_embedding_id
            )

            if embedding is not None:
                image.embedding = embedding
                image.embedding_status = "done"
                image.embedding_error = None
                log_embedding_generation(image_embedding_id, "done")
            else:
                image.embedding_status = "failed"
                image.embedding_error = "임베딩 생성에 실패했습니다."
                log_embedding_generation(
                    image_embedding_id, "failed", "No embedding generated"
                )

            image.save(
                update_fields=["embedding", "embedding_status", "embedding_error"]
            )

    except ImageEmbedding.DoesNotExist:
        log_embedding_generation(image_embedding_id, "failed", "Image not found")
        raise
    except Exception as exc:
        # 오류 상태로 업데이트
        try:
            with transaction.atomic():
                image = ImageEmbedding.objects.select_for_update().get(
                    id=image_embedding_id
                )
                image.embedding_status = "failed"
                image.embedding_error = str(exc)
                image.save(update_fields=["embedding_status", "embedding_error"])
        except ImageEmbedding.DoesNotExist:
            pass

        log_embedding_generation(image_embedding_id, "failed", str(exc))

        # 재시도 로직
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise


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
            generate_image_embedding.delay(image.id)
            retry_count += 1
        except Exception as e:
            # 개별 실패는 로깅만 하고 계속 진행
            log_embedding_generation(image.id, "failed", f"Retry failed: {e}")

    return retry_count
