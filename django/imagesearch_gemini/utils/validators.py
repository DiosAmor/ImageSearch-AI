import os
import re
from datetime import datetime
from typing import List, Tuple

from django.core.files.uploadedfile import UploadedFile


class FileValidator:
    """파일 업로드 검증을 위한 클래스입니다."""

    # 허용된 이미지 확장자
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

    # 파일 크기 제한 (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    @classmethod
    def validate_image_file(cls, file: UploadedFile) -> Tuple[bool, str]:
        """이미지 파일을 검증합니다.

        Args:
            file: 업로드된 파일

        Returns:
            (is_valid, error_message)

        """
        # 파일 크기 검증
        if file.size > cls.MAX_FILE_SIZE:
            return (
                False,
                f"파일 크기가 너무 큽니다. 최대 {cls.MAX_FILE_SIZE // (1024 * 1024)}MB까지 허용됩니다.",
            )

        # 파일 확장자 검증
        _, ext = os.path.splitext(file.name.lower())
        if ext not in cls.ALLOWED_EXTENSIONS:
            return (
                False,
                f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(cls.ALLOWED_EXTENSIONS)}",
            )

        # 파일명 보안 검증 (디렉토리 트래버설 방지)
        if ".." in file.name or "/" in file.name or "\\" in file.name:
            return False, "잘못된 파일명입니다."

        return True, ""


class TextValidator:
    """텍스트 입력 검증을 위한 클래스입니다."""

    @staticmethod
    def validate_search_query(query: str) -> Tuple[bool, str]:
        """검색어를 검증합니다 (영어만 허용).

        Args:
            query: 검색어

        Returns:
            (is_valid, error_message)

        """
        if not query or not query.strip():
            return False, "검색어를 입력해주세요."

        # 영어 단어만 허용 (알파벳, 숫자, 공백, 쉼표)
        if not re.fullmatch(r"[A-Za-z0-9 ,]+", query.strip()):
            return (
                False,
                "검색어는 영어 단어(알파벳, 숫자, 공백, 쉼표)만 입력 가능합니다.",
            )

        return True, ""

    @staticmethod
    def validate_tags(tags: str) -> Tuple[bool, str]:
        """태그를 검증합니다.

        Args:
            tags: 태그 문자열 (쉼표로 구분)

        Returns:
            (is_valid, error_message)

        """
        if not tags:
            return True, ""

        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # 태그 길이 및 특수문자 검증
        for tag in tag_list:
            if len(tag) > 50:
                return False, f"태그 '{tag}'가 너무 깁니다. 최대 50자까지 허용됩니다."

            # 특수문자 제한 (한글, 영문, 숫자, 공백만 허용)
            if not re.fullmatch(r"[가-힣A-Za-z0-9\s]+", tag):
                return (
                    False,
                    f"태그 '{tag}'에 허용되지 않는 특수문자가 포함되어 있습니다.",
                )

        return True, ""


class DateValidator:
    """날짜 입력 검증을 위한 클래스입니다."""

    @staticmethod
    def validate_date_range(date_from: str, date_to: str) -> Tuple[bool, str]:
        """날짜 범위를 검증합니다.

        Args:
            date_from: 시작 날짜 (YYYY-MM-DD)
            date_to: 종료 날짜 (YYYY-MM-DD)

        Returns:
            (is_valid, error_message)

        """
        if not date_from or not date_to:
            return True, ""

        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            to_date = datetime.strptime(date_to, "%Y-%m-%d")

            if from_date > to_date:
                return False, "시작 날짜가 종료 날짜보다 늦을 수 없습니다."

            # 과거 100년 이내로 제한
            current_year = datetime.now().year
            if from_date.year < current_year - 100 or to_date.year > current_year:
                return False, "날짜 범위가 유효하지 않습니다."

        except ValueError:
            return False, "날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)"

        return True, ""


def validate_upload_data(
    files: List[UploadedFile],
    date_taken: str = None,
    location: str = None,
    tags: str = None,
) -> Tuple[bool, List[str]]:
    """업로드 데이터를 종합적으로 검증합니다.

    Args:
        files: 업로드된 파일들
        date_taken: 촬영 날짜
        location: 촬영 장소
        tags: 태그

    Returns:
        (is_valid, error_messages)

    """
    errors = []

    # 파일 검증
    if not files:
        errors.append("업로드할 파일을 선택해주세요.")
    else:
        for file in files:
            is_valid, error = FileValidator.validate_image_file(file)
            if not is_valid:
                errors.append(f"{file.name}: {error}")

    # 태그 검증
    if tags:
        is_valid, error = TextValidator.validate_tags(tags)
        if not is_valid:
            errors.append(error)

    # 위치 검증
    if location and len(location.strip()) > 255:
        errors.append("촬영 장소가 너무 깁니다. 최대 255자까지 허용됩니다.")

    return len(errors) == 0, errors
