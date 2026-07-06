from django.urls import path

from .api_views import SectionGradebookView, StudentGradesView, StudentMissingAssignmentsView

urlpatterns = [
    path("students/<int:student_id>/grades/", StudentGradesView.as_view(), name="api-student-grades"),
    path(
        "students/<int:student_id>/missing-assignments/",
        StudentMissingAssignmentsView.as_view(),
        name="api-student-missing",
    ),
    path("sections/<int:section_id>/gradebook/", SectionGradebookView.as_view(), name="api-section-gradebook"),
]
