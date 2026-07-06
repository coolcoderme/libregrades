from rest_framework import serializers

from apps.accounts.models import ParentProfile, User
from apps.notifications.models import NotificationPreference


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "school",
            "district",
            "phone",
        )
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            "email_grades",
            "email_missing",
            "email_attendance",
            "email_behavior",
            "email_digest",
        )


class ParentChildSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="student_profile.id")
    student_id = serializers.CharField(source="student_profile.student_id")
    full_name = serializers.CharField(source="student_profile.full_name")
    grade_level = serializers.IntegerField(source="student_profile.grade_level")

    class Meta:
        model = ParentProfile
        fields = ("id", "student_id", "full_name", "grade_level")
