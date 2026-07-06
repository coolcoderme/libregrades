from django.urls import path

from .api_views import MyMedicalView, StudentMedicalView

urlpatterns = [
    path("auth/me/medical/", MyMedicalView.as_view(), name="api-my-medical"),
    path("students/<int:student_id>/medical/", StudentMedicalView.as_view(), name="api-student-medical"),
]
