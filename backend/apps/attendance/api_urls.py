from django.urls import path

from .api_views import SectionAttendanceView, StudentAttendanceView

urlpatterns = [
    path(
        "students/<int:student_id>/attendance/",
        StudentAttendanceView.as_view(),
        name="api-student-attendance",
    ),
    path(
        "sections/<int:section_id>/attendance/",
        SectionAttendanceView.as_view(),
        name="api-section-attendance",
    ),
]
