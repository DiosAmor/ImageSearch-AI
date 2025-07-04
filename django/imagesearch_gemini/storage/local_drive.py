import os
import tempfile

from imagesearch_gemini.models import ImageEmbedding
from imagesearch_gemini.utils.validators import validate_upload_data

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile


def save_uploaded_image(
    uploaded_file: UploadedFile, date_taken_user=None, location_user=None, tags=None
) -> str:
    """업로드된 이미지 파일을 임시로 저장하고, 임시 파일 경로를 반환합니다.

    Args:
        uploaded_file: 업로드된 파일 객체
        date_taken_user: 사용자가 입력한 촬영일 (선택사항)
        location_user: 사용자가 입력한 장소 (선택사항)
        tags: 태그 문자열 (쉼표로 구분, 선택사항)

    Returns:
        str: 임시 파일 경로

    Raises:
        ValidationError: 파일 검증 실패 시

    """
    # 파일 및 메타데이터 검증
    is_valid, errors = validate_upload_data(
        [uploaded_file],
        date_taken=date_taken_user,
        location=location_user,
        tags=tags,
    )
    if not is_valid:
        raise ValidationError("; ".join(errors))

    # 임시 파일로 저장
    _, ext = os.path.splitext(uploaded_file.name)
    if not ext:
        ext = ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    return tmp_path


def get_image_info(image_embedding_id: int) -> dict:
    """ImageEmbedding 모델에서 이미지 정보를 반환합니다.

    Args:
        image_embedding_id: ImageEmbedding 객체의 ID

    Returns:
        dict: 이미지 정보

    """
    try:
        image_embedding = ImageEmbedding.objects.get(id=image_embedding_id)

        # 파일 존재 여부 확인
        if not default_storage.exists(image_embedding.image_path):
            raise FileNotFoundError(
                f"파일을 찾을 수 없습니다: {image_embedding.image_path}"
            )

        # 파일 크기
        file_size = default_storage.size(image_embedding.image_path)

        # 파일명 추출
        file_name = os.path.basename(image_embedding.image_path)

        # 파일 타입 추출
        _, ext = os.path.splitext(file_name)
        file_type = ext.upper().replace(".", "") if ext else "이미지"

        # URL 생성
        url = default_storage.url(image_embedding.image_path)

        return {
            "id": image_embedding.id,
            "file_path": image_embedding.image_path,
            "file_name": file_name,
            "file_size": file_size,
            "file_type": file_type,
            "upload_date": image_embedding.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "url": url,
            "storage_type": "local",
            "embedding_status": image_embedding.embedding_status,
            "date_taken": image_embedding.date_taken,
            "location_user": image_embedding.location_user,
            "tags": list(image_embedding.tags.names()),
            "gps": image_embedding.gps,
            "city_from_gps": image_embedding.city_from_gps,
        }

    except ImageEmbedding.DoesNotExist:
        raise ValidationError(f"이미지를 찾을 수 없습니다: ID {image_embedding_id}")
    except Exception as e:
        raise ValidationError(f"이미지 정보 조회 실패: {e!s}")


def delete_image(image_embedding_id: int) -> bool:
    """ImageEmbedding 모델에서 이미지를 삭제합니다 (파일도 함께 삭제).

    Args:
        image_embedding_id: ImageEmbedding 객체의 ID

    Returns:
        bool: 삭제 성공 여부

    """
    try:
        image_embedding = ImageEmbedding.objects.get(id=image_embedding_id)

        # 파일 삭제
        if default_storage.exists(image_embedding.image_path):
            default_storage.delete(image_embedding.image_path)

        # 모델 삭제 (post_delete 시그널이 파일 삭제를 처리)
        image_embedding.delete()
        return True

    except ImageEmbedding.DoesNotExist:
        return False
    except Exception:
        return False


def list_uploaded_images(limit: int = 20, embedding_status=None) -> list:
    """ImageEmbedding 모델에서 업로드된 이미지 목록을 반환합니다.

    Args:
        limit: 반환할 이미지 개수 제한
        embedding_status: 임베딩 상태 필터 (선택사항)

    Returns:
        list: 이미지 정보 리스트

    """
    try:
        # 쿼리셋 생성
        queryset = ImageEmbedding.objects.all().order_by("-created_at")

        # 임베딩 상태 필터 적용
        if embedding_status:
            queryset = queryset.filter(embedding_status=embedding_status)

        # 제한된 개수만큼 가져오기
        image_embeddings = queryset[:limit]

        images = []
        for image_embedding in image_embeddings:
            try:
                image_info = get_image_info(image_embedding.id)
                images.append(image_info)
            except Exception:
                # 개별 파일 오류는 무시하고 계속 진행
                continue

        return images

    except Exception as e:
        raise ValidationError(f"이미지 목록 조회 실패: {e!s}")


def get_storage_usage() -> dict:
    """저장소 사용량을 반환합니다.

    Returns:
        dict: 저장소 사용량 정보

    """
    try:
        # ImageEmbedding 모델에서 통계 계산
        total_files = ImageEmbedding.objects.count()
        total_size = 0

        # 각 파일의 크기 합계 계산
        for image_embedding in ImageEmbedding.objects.all():
            try:
                if default_storage.exists(image_embedding.image_path):
                    total_size += default_storage.size(image_embedding.image_path)
            except Exception:
                continue

        return {
            "total_files": total_files,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

    except Exception as e:
        raise ValidationError(f"저장소 사용량 조회 실패: {e!s}")


def get_images_by_status(embedding_status: str) -> list:
    """특정 임베딩 상태의 이미지들을 반환합니다.

    Args:
        embedding_status: 임베딩 상태 ('pending', 'processing', 'done', 'failed')

    Returns:
        list: 해당 상태의 이미지 정보 리스트

    """
    return list_uploaded_images(limit=100, embedding_status=embedding_status)


def get_images_with_embeddings() -> list:
    """임베딩이 완료된 이미지들을 반환합니다.

    Returns:
        list: 임베딩 완료된 이미지 정보 리스트

    """
    return get_images_by_status("done")


def get_failed_images() -> list:
    """임베딩 생성에 실패한 이미지들을 반환합니다.

    Returns:
        list: 임베딩 실패한 이미지 정보 리스트

    """
    return get_images_by_status("failed")
