from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import user_can_view_emergency_contacts
from apps.emergency.models import EmergencyContact
from apps.emergency.serializers import EmergencyContactSerializer
from apps.students.models import StudentProfile


class StudentEmergencyContactsView(APIView):
    def get(self, request, student_id):
        try:
            student = StudentProfile.objects.get(pk=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFound()
        if not user_can_view_emergency_contacts(request.user, student):
            raise PermissionDenied()
        contacts = EmergencyContact.objects.filter(student=student)
        return Response(EmergencyContactSerializer(contacts, many=True).data)
