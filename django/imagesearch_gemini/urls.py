from django.shortcuts import redirect
from django.urls import path

from . import views

urlpatterns = [
    path("", lambda request: redirect("search/")),
    path("image-upload/", views.image_upload, name="image_upload"),
    path("search/", views.image_search, name="image_search"),
    path("cloud-image-list/", views.cloud_image_list, name="cloud_image_list"),
    path(
        "embedding-status/", views.embedding_status_list, name="embedding_status_list"
    ),
    path(
        "retry-embedding/<int:image_id>/",
        views.retry_failed_embedding,
        name="retry_failed_embedding",
    ),
    path("similar-images/<int:image_id>/", views.similar_images, name="similar_images"),
]
