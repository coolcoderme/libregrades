from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import user_can_view_student
from apps.credits.models import CreditEarned, GraduationRequirement
from apps.credits.serializers import CreditEarnedSerializer, CreditSummarySerializer
from apps.credits.services import build_credit_summary
from apps.students.models import StudentProfile


class StudentCreditsView(APIView):
    def get(self, request, student_id):
        try:
            student = StudentProfile.objects.get(pk=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFound()
        if not user_can_view_student(request.user, student):
            raise PermissionDenied()
        credits = CreditEarned.objects.filter(student=student).select_related("course")
        summary = build_credit_summary(student)
        return Response(
            {
                "credits": CreditEarnedSerializer(credits, many=True).data,
                "summary": CreditSummarySerializer(summary).data,
            }
        )


class StudentTranscriptView(APIView):
    def get(self, request, student_id):
        try:
            student = StudentProfile.objects.get(pk=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFound()
        if not user_can_view_student(request.user, student):
            raise PermissionDenied()
        from apps.credits.services import generate_transcript_pdf
        from django.http import HttpResponse

        pdf = generate_transcript_pdf(student)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="transcript_{student.student_id}.pdf"'
        return response
