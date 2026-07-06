from django.urls import path

from .api_views import SectionDetailView, StudentScheduleView, TeacherSectionsView

urlpatterns = [
    path("students/<int:student_id>/schedule/", StudentScheduleView.as_view(), name="api-student-schedule"),
    path("sections/", TeacherSectionsView.as_view(), name="api-sections"),
    path("sections/<int:section_id>/", SectionDetailView.as_view(), name="api-section-detail"),
]
