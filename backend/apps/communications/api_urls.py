from django.urls import path

from . import api_views

urlpatterns = [
    path("announcements/", api_views.AnnouncementListView.as_view(), name="api-announcements"),
    path("messages/", api_views.MessageListView.as_view(), name="api-messages"),
]
