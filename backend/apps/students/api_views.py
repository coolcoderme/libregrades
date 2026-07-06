from rest_framework import generics
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.accounts.permissions import accessible_students, get_student_profile, user_can_view_student
from apps.students.models import StudentProfile
from apps.students.serializers import StudentProfileSerializer


class StudentMeView(generics.RetrieveAPIView):
    serializer_class = StudentProfileSerializer

    def get_object(self):
        profile = get_student_profile(self.request.user)
        if not profile:
            raise NotFound("No student profile.")
        return profile


class StudentDetailView(generics.RetrieveAPIView):
    serializer_class = StudentProfileSerializer
    queryset = StudentProfile.objects.select_related("user", "school")

    def get_object(self):
        obj = super().get_object()
        if not user_can_view_student(self.request.user, obj):
            raise PermissionDenied()
        return obj


class StudentListView(generics.ListAPIView):
    serializer_class = StudentProfileSerializer

    def get_queryset(self):
        return accessible_students(self.request.user).select_related("user", "school")
