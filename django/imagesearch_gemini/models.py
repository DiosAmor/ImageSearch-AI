from django.db import models
from pgvector.django import VectorField
from django.contrib.gis.db.models import PointField
from taggit.managers import TaggableManager
import os
from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver


# 예시 모델: 이미지 벡터 저장 및 EXIF 정보 포함
class ImageEmbedding(models.Model):
    image_path = models.CharField(max_length=1024)  # 이미지 경로(로컬, URL 등)
    embedding = VectorField(dimensions=1408)  # 1408차원 벡터
    embedding_model = models.CharField(
        max_length=128, null=True, blank=True
    )  # 임베딩 모델명

    gps = PointField(null=True, blank=True)  # PostGIS Point (경도, 위도)
    city_from_gps = models.CharField(
        max_length=128, null=True, blank=True
    )  # GPS로 추출한 도시명
    date_taken_exif = models.DateTimeField(
        null=True, blank=True
    )  # EXIF에서 추출한 촬영일시
    image_unique_id = models.CharField(
        max_length=128, null=True, blank=True
    )  # ImageUniqueID
    exif_json = models.JSONField(null=True, blank=True)  # 기타 EXIF 정보

    date_taken_user = models.DateField(
        null=True, blank=True
    )  # 사용자가 입력한 촬영일(날짜만)
    location_user = models.CharField(
        max_length=255, null=True, blank=True
    )  # 사용자가 입력한 장소
    tags = TaggableManager(blank=True)  # django-taggit 태그 필드

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # 수정일시

    @property
    def date_taken(self):
        """사용자 입력 촬영일이 있으면 우선, 없으면 EXIF 촬영일 반환"""
        return self.date_taken_user or self.date_taken_exif


@receiver(post_delete, sender=ImageEmbedding)
def delete_image_file(sender, instance, **kwargs):
    if instance.image_path and not (
        instance.image_path.startswith("http://")
        or instance.image_path.startswith("https://")
    ):
        file_path = os.path.join(
            settings.MEDIA_ROOT, instance.image_path.replace("\\", "/").lstrip("/")
        )
        print(f"Deleting file: {file_path}")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


class SearchQuery(models.Model):
    query_text = models.CharField(max_length=255)
    query_embedding = VectorField(
        dimensions=1408, null=True, blank=True
    )  # 검색어 임베딩 벡터
    query_embedding_model = models.CharField(
        max_length=128, null=True, blank=True
    )  # 임베딩 모델명
    searched_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.query_text} ({self.searched_at:%Y-%m-%d %H:%M:%S})"
