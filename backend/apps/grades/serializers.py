from rest_framework import serializers

from apps.grades.models import Assignment, Grade


class AssignmentSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_past_due = serializers.BooleanField(read_only=True)

    class Meta:
        model = Assignment
        fields = (
            "id",
            "title",
            "description",
            "due_date",
            "max_points",
            "category",
            "category_name",
            "is_published",
            "is_past_due",
        )


class GradeSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    course_code = serializers.CharField(source="assignment.section.course.code", read_only=True)
    section_id = serializers.IntegerField(source="assignment.section_id", read_only=True)
    due_date = serializers.DateField(source="assignment.due_date", read_only=True)
    max_points = serializers.DecimalField(
        source="assignment.max_points", max_digits=8, decimal_places=2, read_only=True
    )
    percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = Grade
        fields = (
            "id",
            "assignment",
            "assignment_title",
            "course_code",
            "section_id",
            "due_date",
            "max_points",
            "points",
            "letter_grade",
            "comment",
            "is_excused",
            "is_missing",
            "percentage",
        )


class GradeEntrySerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    assignment_id = serializers.IntegerField()
    points = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True, required=False)
    comment = serializers.CharField(required=False, allow_blank=True)
    is_excused = serializers.BooleanField(default=False)
