from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path("", lambda request: redirect("search/")),
    path("upload/", views.image_upload, name="image_upload"),
    path("search/", views.image_search, name="image_search"),
    path("google-drive-login/", views.google_drive_login, name="google_drive_login"),
]
