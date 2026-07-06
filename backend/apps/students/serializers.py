from rest_framework import serializers

from apps.students.models import StudentProfile


class StudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "student_id",
            "full_name",
            "username",
            "email",
            "school",
            "grade_level",
            "date_of_birth",
            "gender",
            "address",
            "enrollment_status",
        )
