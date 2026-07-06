from django.urls import path

from .api_views import StudentCreditsView, StudentTranscriptView

urlpatterns = [
    path("students/<int:student_id>/credits/", StudentCreditsView.as_view(), name="api-student-credits"),
    path(
        "students/<int:student_id>/transcript/",
        StudentTranscriptView.as_view(),
        name="api-student-transcript",
    ),
]
