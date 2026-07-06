from rest_framework import serializers

from apps.attendance.models import AttendanceRecord


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    section_name = serializers.CharField(source="section.course.code", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = (
            "id",
            "student",
            "student_name",
            "section",
            "section_name",
            "date",
            "code",
            "period_number",
            "notes",
        )


class AttendanceSubmitSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    date = serializers.DateField()
    code = serializers.CharField(max_length=2)
    period_number = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
