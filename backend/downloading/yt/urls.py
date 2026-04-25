from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health_view, name="yt-health"),
    path("info", views.info_view, name="yt-info"),
    path("local-job", views.local_job_view, name="yt-local-job"),
    path("download", views.download_view, name="yt-download"),
]
