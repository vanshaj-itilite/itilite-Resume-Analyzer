from django.urls import path
from .app import analyze_async, analysis_status

urlpatterns = [
    path("analysis/async", analyze_async),
    path("status/<str:task_id>/", analysis_status),
]
