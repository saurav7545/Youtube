from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health_view, name="yt-health"),
    path("info", views.info_view, name="yt-info"),
    path("download", views.download_view, name="yt-download"),
]
