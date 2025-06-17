from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path("", lambda request: redirect("upload/")),
    path("upload/", views.image_upload, name="image_upload"),
    path("search/", views.image_search, name="image_search"),
]
