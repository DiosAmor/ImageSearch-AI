import os
import tempfile

from imagesearch_gemini.utils.validators import validate_upload_data

from django.core.exceptions import ValidationError
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
