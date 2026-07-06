from rest_framework import serializers

from apps.communications.models import Announcement, DirectMessage


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True)

    class Meta:
        model = Announcement
        fields = ("id", "title", "body", "scope", "author_name", "created_at")


class DirectMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.display_name", read_only=True)

    class Meta:
        model = DirectMessage
        fields = ("id", "subject", "body", "sender_name", "is_read", "created_at")
