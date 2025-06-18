from django.db import models
from pgvector.django import VectorField


# 예시 모델: 이미지 벡터 저장
class ImageEmbedding(models.Model):
    image = models.ImageField(upload_to="images/")
    embedding = VectorField(dimensions=1408)  # 1408차원 벡터
    created_at = models.DateTimeField(auto_now_add=True)
