from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import user_can_edit_grades, user_can_view_student
from apps.attendance.models import AttendanceCode, AttendanceRecord
from apps.attendance.serializers import AttendanceRecordSerializer, AttendanceSubmitSerializer
from apps.scheduling.models import Section
from apps.students.models import StudentProfile


class StudentAttendanceView(APIView):
    def get(self, request, student_id):
        try:
            student = StudentProfile.objects.get(pk=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFound()
        if not user_can_view_student(request.user, student):
            raise PermissionDenied()
        records = AttendanceRecord.objects.filter(student=student).select_related("section")
        return Response(AttendanceRecordSerializer(records, many=True).data)


class SectionAttendanceView(APIView):
    def get(self, request, section_id):
        try:
            section = Section.objects.get(pk=section_id)
        except Section.DoesNotExist:
            raise NotFound()
        if not user_can_edit_grades(request.user, section):
            raise PermissionDenied()
        date = request.query_params.get("date")
        qs = AttendanceRecord.objects.filter(section=section)
        if date:
            qs = qs.filter(date=date)
        return Response(AttendanceRecordSerializer(qs, many=True).data)

    def post(self, request, section_id):
        try:
            section = Section.objects.get(pk=section_id)
        except Section.DoesNotExist:
            raise NotFound()
        if not user_can_edit_grades(request.user, section):
            raise PermissionDenied()
        serializer = AttendanceSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            student = StudentProfile.objects.get(pk=data["student_id"])
        except StudentProfile.DoesNotExist:
            return Response({"detail": "Student not found."}, status=400)
        record, _ = AttendanceRecord.objects.update_or_create(
            student=student,
            section=section,
            date=data["date"],
            period_number=data.get("period_number"),
            defaults={
                "code": data["code"],
                "notes": data.get("notes", ""),
                "recorded_by": request.user,
            },
        )
        from apps.notifications.tasks import notify_attendance

        if data["code"] in (AttendanceCode.ABSENT, AttendanceCode.TARDY):
            notify_attendance.delay(record.id)
        return Response(AttendanceRecordSerializer(record).data, status=status.HTTP_200_OK)
