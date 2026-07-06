from rest_framework import serializers

from apps.behavior.models import BehaviorIncident


class BehaviorIncidentSerializer(serializers.ModelSerializer):
    reported_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BehaviorIncident
        fields = (
            "id",
            "incident_date",
            "incident_type",
            "description",
            "location",
            "reported_by",
            "reported_by_name",
            "consequence",
            "parent_visible",
            "resolved",
        )
        read_only_fields = ("reported_by", "reported_by_name")

    def get_reported_by_name(self, obj):
        if obj.reported_by:
            return obj.reported_by.get_full_name() or obj.reported_by.username
        return ""
