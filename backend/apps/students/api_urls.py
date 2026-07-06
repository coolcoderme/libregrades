from django.urls import path

from .api_views import StudentDetailView, StudentListView, StudentMeView

urlpatterns = [
    path("students/me/", StudentMeView.as_view(), name="api-student-me"),
    path("students/", StudentListView.as_view(), name="api-student-list"),
    path("students/<int:pk>/", StudentDetailView.as_view(), name="api-student-detail"),
]
