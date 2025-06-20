from celery import shared_task

from .models import ImageEmbedding
from .utils.embeddings import generate_embedding_vector  # 임베딩 생성 함수(예시)


@shared_task
def generate_image_embedding(image_embedding_id):
    image = ImageEmbedding.objects.get(id=image_embedding_id)
    image.embedding_status = "processing"
    image.save(update_fields=["embedding_status"])
    try:
        embedding = generate_embedding_vector(image.image_path)
        image.embedding = embedding
        image.embedding_status = "done"
        image.embedding_error = None
    except Exception as e:
        image.embedding_status = "failed"
        image.embedding_error = str(e)
    image.save(update_fields=["embedding", "embedding_status", "embedding_error"])
