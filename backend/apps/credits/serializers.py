from rest_framework import serializers

from apps.credits.models import CreditEarned, GraduationRequirement


class CreditEarnedSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)

    class Meta:
        model = CreditEarned
        fields = (
            "id",
            "course",
            "course_code",
            "course_name",
            "term_name",
            "school_year",
            "credits",
            "letter_grade",
            "gpa_points",
        )


class CreditSummarySerializer(serializers.Serializer):
    total_credits = serializers.DecimalField(max_digits=6, decimal_places=2)
    credits_required = serializers.DecimalField(max_digits=6, decimal_places=2)
    percent_complete = serializers.FloatField()
    by_subject = serializers.DictField(child=serializers.DecimalField(max_digits=5, decimal_places=2))
