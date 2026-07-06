from django.urls import path

from .api_views import StudentEmergencyContactsView

urlpatterns = [
    path(
        "students/<int:student_id>/emergency-contacts/",
        StudentEmergencyContactsView.as_view(),
        name="api-student-emergency",
    ),
]
