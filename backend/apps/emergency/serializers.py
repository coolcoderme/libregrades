from rest_framework import serializers

from apps.emergency.models import EmergencyContact


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = (
            "id",
            "name",
            "relationship",
            "phone_primary",
            "phone_secondary",
            "email",
            "priority",
            "is_authorized_pickup",
        )
