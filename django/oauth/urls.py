from django.shortcuts import redirect
from django.urls import path

from . import views

urlpatterns = [
    path("", lambda request: redirect("cloud-drive-login/")),
    path("cloud-drive-login/", views.cloud_drive_login, name="cloud_drive_login"),
    path(
        "google-drive-redirect/",
        views.google_drive_redirect,
        name="google_drive_redirect",
    ),
    path("onedrive-redirect/", views.onedrive_redirect, name="onedrive_redirect"),
]
