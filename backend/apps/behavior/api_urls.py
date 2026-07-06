from django.urls import path

from .api_views import StudentBehaviorView

urlpatterns = [
    path(
        "students/<int:student_id>/behavior/",
        StudentBehaviorView.as_view(),
        name="api-student-behavior",
    ),
]
