"""입력 검증 테스트입니다."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from ..utils.validators import (
    DateValidator,
    FileValidator,
    TextValidator,
    validate_upload_data,
)


class ValidatorTests(TestCase):
    """입력 검증 테스트 클래스입니다."""

    def test_file_validator_valid_image(self):
        """유효한 이미지 파일 검증 테스트."""
        valid_file = SimpleUploadedFile(
            "test.jpg", b"fake content", content_type="image/jpeg"
        )
        valid_file.size = 1024 * 1024  # 1MB

        is_valid, error = FileValidator.validate_image_file(valid_file)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_file_validator_invalid_extension(self):
        """잘못된 확장자 테스트."""
        invalid_file = SimpleUploadedFile(
            "test.txt", b"fake content", content_type="text/plain"
        )
        invalid_file.size = 1024

        is_valid, error = FileValidator.validate_image_file(invalid_file)
        self.assertFalse(is_valid)
        self.assertIn("지원하지 않는 파일 형식", error)

    def test_file_validator_too_large(self):
        """파일 크기 초과 테스트."""
        large_file = SimpleUploadedFile(
            "test.jpg", b"fake content", content_type="image/jpeg"
        )
        large_file.size = 20 * 1024 * 1024  # 20MB

        is_valid, error = FileValidator.validate_image_file(large_file)
        self.assertFalse(is_valid)
        self.assertIn("파일 크기가 너무 큽니다", error)

    def test_text_validator_valid_query(self):
        """유효한 검색어 테스트."""
        valid_queries = ["test", "test query", "test123", "test, query"]

        for query in valid_queries:
            is_valid, error = TextValidator.validate_search_query(query)
            self.assertTrue(is_valid, f"Query '{query}' should be valid")
            self.assertEqual(error, "")

    def test_text_validator_invalid_query(self):
        """잘못된 검색어 테스트."""
        invalid_queries = ["", "   ", "테스트", "test@query", "test!query"]

        for query in invalid_queries:
            is_valid, error = TextValidator.validate_search_query(query)
            self.assertFalse(is_valid, f"Query '{query}' should be invalid")
            self.assertNotEqual(error, "")

    def test_date_validator_valid_range(self):
        """유효한 날짜 범위 테스트."""
        is_valid, error = DateValidator.validate_date_range("2023-01-01", "2023-12-31")
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_date_validator_invalid_range(self):
        """잘못된 날짜 범위 테스트."""
        is_valid, error = DateValidator.validate_date_range("2023-12-31", "2023-01-01")
        self.assertFalse(is_valid)
        self.assertIn("시작 날짜가 종료 날짜보다 늦을 수 없습니다", error)

    def test_validate_upload_data_valid(self):
        """유효한 업로드 데이터 테스트."""
        valid_file = SimpleUploadedFile(
            "test.jpg", b"fake content", content_type="image/jpeg"
        )
        valid_file.size = 1024 * 1024

        is_valid, errors = validate_upload_data(
            files=[valid_file],
            date_taken="2023-01-01",
            location="Seoul",
            tags="nature, landscape",
        )

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_upload_data_invalid(self):
        """잘못된 업로드 데이터 테스트."""
        invalid_file = SimpleUploadedFile(
            "test.txt", b"fake content", content_type="text/plain"
        )
        invalid_file.size = 1024

        is_valid, errors = validate_upload_data(
            files=[invalid_file], tags="invalid@tag"
        )

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
