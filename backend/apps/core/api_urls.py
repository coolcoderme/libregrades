from django.urls import path

from .api_views import ServerInfoView

urlpatterns = [
    path("server/", ServerInfoView.as_view(), name="api-server-info"),
]
