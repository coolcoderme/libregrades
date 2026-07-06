from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.accounts.permissions import get_student_profile, user_can_view_student
from apps.scheduling.models import Enrollment, Section
from apps.scheduling.serializers import EnrollmentSerializer, SectionSerializer
from apps.students.models import StudentProfile


class StudentScheduleView(APIView):
    def get(self, request, student_id):
        try:
            student = StudentProfile.objects.get(pk=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFound()
        if not user_can_view_student(request.user, student):
            raise PermissionDenied()
        enrollments = Enrollment.objects.filter(student=student, is_active=True).select_related(
            "section__course", "section__teacher", "section__period"
        )
        return Response(EnrollmentSerializer(enrollments, many=True).data)


class TeacherSectionsView(APIView):
    def get(self, request):
        if request.user.role not in {UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.DISTRICT_ADMIN}:
            raise PermissionDenied()
        qs = Section.objects.select_related("course", "teacher", "period", "term")
        if request.user.role == UserRole.TEACHER:
            qs = qs.filter(teacher=request.user)
        sections = qs.filter(term__is_current=True)
        return Response(SectionSerializer(sections, many=True).data)


class SectionDetailView(APIView):
    def get(self, request, section_id):
        try:
            section = Section.objects.select_related("course", "teacher", "period").get(pk=section_id)
        except Section.DoesNotExist:
            raise NotFound()
        if request.user.role == UserRole.TEACHER and section.teacher_id != request.user.id:
            if request.user.role not in {UserRole.SCHOOL_ADMIN, UserRole.DISTRICT_ADMIN}:
                raise PermissionDenied()
        return Response(SectionSerializer(section).data)
