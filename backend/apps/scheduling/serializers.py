from rest_framework import serializers

from apps.scheduling.models import Course, Enrollment, Period, Section


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = ("id", "name", "period_number", "start_time", "end_time")


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ("id", "code", "name", "description", "credit_value", "is_honors")


class SectionSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)
    teacher_name = serializers.SerializerMethodField()
    period_name = serializers.CharField(source="period.name", read_only=True)

    class Meta:
        model = Section
        fields = (
            "id",
            "course",
            "course_name",
            "course_code",
            "section_number",
            "teacher",
            "teacher_name",
            "period",
            "period_name",
            "room",
            "term",
        )

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.username
        return ""


class EnrollmentSerializer(serializers.ModelSerializer):
    section = SectionSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ("id", "section", "enrolled_at", "is_active")
