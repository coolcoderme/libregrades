from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import ParentProfile, User, UserRole
from apps.notifications.models import NotificationPreference
from apps.accounts.permissions import get_parent_profile, get_student_profile
from apps.accounts.serializers import NotificationPreferenceSerializer, UserSerializer
from apps.students.models import StudentProfile
from apps.students.serializers import StudentProfileSerializer


class LoginView(TokenObtainPairView):
    pass


class RefreshView(TokenRefreshView):
    pass


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ParentChildrenView(APIView):
    def get(self, request):
        if request.user.role != UserRole.PARENT:
            return Response({"detail": "Not a parent account."}, status=status.HTTP_403_FORBIDDEN)
        profile = get_parent_profile(request.user)
        if not profile:
            return Response([])
        children = profile.students.all()
        data = StudentProfileSerializer(children, many=True).data
        return Response(data)


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer

    def get_object(self):
        prefs, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        return prefs


class LinkParentStudentView(APIView):
    """Link parent to student using verification code (student ID suffix)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != UserRole.PARENT:
            return Response({"detail": "Parent account required."}, status=403)
        student_id = request.data.get("student_id")
        code = request.data.get("verification_code")
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            return Response({"detail": "Student not found."}, status=404)
        expected = student.student_id[-4:]
        if code != expected:
            return Response({"detail": "Invalid verification code."}, status=400)
        profile, _ = ParentProfile.objects.get_or_create(user=request.user)
        profile.students.add(student)
        return Response({"detail": "Student linked.", "student_id": student.id})
