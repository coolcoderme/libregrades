from django.urls import path

from .api_views import (
    LinkParentStudentView,
    LoginView,
    MeView,
    NotificationPreferenceView,
    ParentChildrenView,
    RefreshView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/refresh/", RefreshView.as_view(), name="api-refresh"),
    path("auth/me/", MeView.as_view(), name="api-me"),
    path("parents/children/", ParentChildrenView.as_view(), name="api-parent-children"),
    path("parents/link/", LinkParentStudentView.as_view(), name="api-parent-link"),
    path("notifications/preferences/", NotificationPreferenceView.as_view(), name="api-notif-prefs"),
]
