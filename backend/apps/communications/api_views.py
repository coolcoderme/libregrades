from rest_framework import generics

from apps.communications.models import Announcement, DirectMessage

from .serializers import AnnouncementSerializer, DirectMessageSerializer


class AnnouncementListView(generics.ListAPIView):
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        return Announcement.objects.filter(is_published=True).order_by("-created_at")[:50]


class MessageListView(generics.ListAPIView):
    serializer_class = DirectMessageSerializer

    def get_queryset(self):
        return DirectMessage.objects.filter(recipient=self.request.user).order_by("-created_at")[:50]
