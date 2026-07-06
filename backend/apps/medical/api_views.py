from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import (
    MEDICAL_FULL,
    MEDICAL_NONE,
    get_staff_medical_access,
    get_student_medical_access,
    user_can_view_medical,
)
from apps.medical.models import MedicalRecord
from apps.medical.serializers import MedicalRecordSerializer
from apps.students.models import StudentProfile


def _medical_payload(subject_user, access_level):
    record, _ = MedicalRecord.objects.get_or_create(user=subject_user)
    data = MedicalRecordSerializer(record).data
    data["access_level"] = access_level
    data["allergies"] = list(subject_user.allergies.values())
    data["medications"] = list(subject_user.medications.values())
    data["medical_conditions"] = list(subject_user.medical_conditions.values())
    if access_level == MEDICAL_FULL:
        data["immunizations"] = list(subject_user.immunizations.values())
        data["insurance_provider"] = record.insurance_provider
        data["insurance_policy"] = record.insurance_policy
        data["nurse_notes"] = record.nurse_notes
    else:
        data["immunizations"] = []
        data["insurance_provider"] = ""
        data["insurance_policy"] = ""
        data["nurse_notes"] = ""
    return data


class MyMedicalView(APIView):
    def get(self, request):
        if not user_can_view_medical(request.user, target_user=request.user):
            raise PermissionDenied()
        from apps.accounts.audit import log_audit

        access = get_staff_medical_access(request.user, request.user)
        if hasattr(request.user, "student_profile"):
            access = get_student_medical_access(request.user, request.user.student_profile)
        log_audit(request.user, "view", "MedicalRecord", request.user.id, request=request)
        return Response(_medical_payload(request.user, access))


class StudentMedicalView(APIView):
    def get(self, request, student_id):
        try:
            student = StudentProfile.objects.get(pk=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFound()
        access = get_student_medical_access(request.user, student)
        if access == MEDICAL_NONE:
            raise PermissionDenied()
        from apps.accounts.audit import log_audit

        log_audit(request.user, "view", "MedicalRecord", student.user_id, request=request)
        return Response(_medical_payload(student.user, access))
