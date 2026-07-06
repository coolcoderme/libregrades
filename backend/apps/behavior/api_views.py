from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.accounts.permissions import user_can_view_student
from apps.behavior.models import BehaviorIncident
from apps.behavior.serializers import BehaviorIncidentSerializer
from apps.students.models import StudentProfile


class StudentBehaviorView(APIView):
    def get(self, request, student_id):
        try:
            student = StudentProfile.objects.get(pk=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFound()
        if not user_can_view_student(request.user, student):
            raise PermissionDenied()
        qs = BehaviorIncident.objects.filter(student=student)
        if request.user.role in (UserRole.STUDENT, UserRole.PARENT):
            qs = qs.filter(parent_visible=True)
        return Response(BehaviorIncidentSerializer(qs, many=True).data)

    def post(self, request, student_id):
        if request.user.role not in {
            UserRole.TEACHER,
            UserRole.COUNSELOR,
            UserRole.SCHOOL_ADMIN,
            UserRole.DISTRICT_ADMIN,
        }:
            raise PermissionDenied()
        try:
            student = StudentProfile.objects.get(pk=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFound()
        serializer = BehaviorIncidentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incident = serializer.save(student=student, reported_by=request.user)
        from apps.notifications.tasks import notify_behavior

        notify_behavior.delay(incident.id)
        return Response(BehaviorIncidentSerializer(incident).data, status=status.HTTP_201_CREATED)
