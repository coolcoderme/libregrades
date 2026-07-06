from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import user_can_edit_grades, user_can_view_student
from apps.grades.models import Assignment, Grade, GradeCategory
from apps.grades.serializers import AssignmentSerializer, GradeEntrySerializer, GradeSerializer
from apps.scheduling.models import Enrollment, Section
from apps.students.models import StudentProfile
from django.utils import timezone


class StudentGradesView(APIView):
    def get(self, request, student_id):
        try:
            student = StudentProfile.objects.get(pk=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFound()
        if not user_can_view_student(request.user, student):
            raise PermissionDenied()
        grades = Grade.objects.filter(student=student).select_related(
            "assignment__section__course", "assignment__category"
        )
        return Response(GradeSerializer(grades, many=True).data)


class StudentMissingAssignmentsView(APIView):
    def get(self, request, student_id):
        try:
            student = StudentProfile.objects.get(pk=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFound()
        if not user_can_view_student(request.user, student):
            raise PermissionDenied()
        today = timezone.localdate()
        enrollments = Enrollment.objects.filter(student=student, is_active=True).values_list(
            "section_id", flat=True
        )
        assignments = Assignment.objects.filter(
            section_id__in=enrollments, is_published=True, due_date__lt=today
        ).select_related("section__course", "category")
        missing = []
        for assignment in assignments:
            grade = Grade.objects.filter(assignment=assignment, student=student).first()
            if grade is None or (grade.points is None and not grade.is_excused):
                missing.append(
                    {
                        "assignment_id": assignment.id,
                        "title": assignment.title,
                        "course_code": assignment.section.course.code,
                        "course_name": assignment.section.course.name,
                        "due_date": assignment.due_date,
                        "max_points": assignment.max_points,
                        "section_id": assignment.section_id,
                    }
                )
        return Response(missing)


class SectionGradebookView(APIView):
    def get(self, request, section_id):
        try:
            section = Section.objects.select_related("course").get(pk=section_id)
        except Section.DoesNotExist:
            raise NotFound()
        if not user_can_edit_grades(request.user, section):
            raise PermissionDenied()
        students = StudentProfile.objects.filter(
            enrollments__section=section, enrollments__is_active=True
        ).distinct()
        assignments = Assignment.objects.filter(section=section).order_by("due_date")
        categories = GradeCategory.objects.filter(section=section)
        grades = Grade.objects.filter(assignment__section=section)
        grade_map = {(g.student_id, g.assignment_id): g for g in grades}
        rows = []
        for student in students:
            row = {"student_id": student.id, "student_name": student.full_name, "grades": []}
            for assignment in assignments:
                g = grade_map.get((student.id, assignment.id))
                row["grades"].append(
                    {
                        "assignment_id": assignment.id,
                        "points": float(g.points) if g and g.points is not None else None,
                        "is_missing": g.is_missing if g else assignment.is_past_due,
                        "is_excused": g.is_excused if g else False,
                        "grade_id": g.id if g else None,
                    }
                )
            rows.append(row)
        return Response(
            {
                "section": section.id,
                "course": section.course.code,
                "assignments": AssignmentSerializer(assignments, many=True).data,
                "categories": [{"id": c.id, "name": c.name, "weight": float(c.weight)} for c in categories],
                "rows": rows,
            }
        )

    def post(self, request, section_id):
        try:
            section = Section.objects.get(pk=section_id)
        except Section.DoesNotExist:
            raise NotFound()
        if not user_can_edit_grades(request.user, section):
            raise PermissionDenied()
        serializer = GradeEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            student = StudentProfile.objects.get(pk=data["student_id"])
            assignment = Assignment.objects.get(pk=data["assignment_id"], section=section)
        except (StudentProfile.DoesNotExist, Assignment.DoesNotExist):
            return Response({"detail": "Invalid student or assignment."}, status=400)
        grade, _ = Grade.objects.get_or_create(assignment=assignment, student=student)
        if "points" in data:
            grade.points = data["points"]
        grade.comment = data.get("comment", grade.comment)
        grade.is_excused = data.get("is_excused", grade.is_excused)
        grade.save()
        from apps.notifications.tasks import notify_grade_posted

        notify_grade_posted.delay(grade.id)
        return Response(GradeSerializer(grade).data, status=status.HTTP_200_OK)
