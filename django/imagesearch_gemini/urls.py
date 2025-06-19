from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path("", lambda request: redirect("search/")),
    path("upload/", views.image_upload, name="image_upload"),
    path("search/", views.image_search, name="image_search"),
    path("cloud-image-list/", views.cloud_image_list, name="cloud_image_list"),
]
