from django.urls import path

from .api_views import (
    DeviceTokenRegisterView,
    NotificationListView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="api-notifications"),
    path("notifications/unread-count/", NotificationUnreadCountView.as_view(), name="api-notifications-unread"),
    path("notifications/register-device/", DeviceTokenRegisterView.as_view(), name="api-register-device"),
    path("notifications/<int:pk>/read/", NotificationMarkReadView.as_view(), name="api-notification-read"),
]
