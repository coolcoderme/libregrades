"""CSV roster import and export."""

import csv
import io
from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.accounts.models import User, UserRole
from apps.core.models import School
from apps.scheduling.models import Course, Enrollment, Section, Term
from apps.students.models import StudentProfile


def export_students_csv(students):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["student_id", "first_name", "last_name", "email", "grade_level", "school_code"])
    for s in students.select_related("user", "school"):
        w.writerow([
            s.student_id,
            s.user.first_name,
            s.user.last_name,
            s.user.email,
            s.grade_level,
            s.school.code,
        ])
    return buf.getvalue()


def export_grades_csv(student):
    from apps.grades.models import Grade
    from apps.grades.services import grades_visible_to_student

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["course", "assignment", "due_date", "points", "max_points", "comment", "posted"])
    for g in grades_visible_to_student(
        Grade.objects.filter(student=student).select_related("assignment__section__course")
    ):
        w.writerow([
            g.assignment.section.course.code,
            g.assignment.title,
            g.assignment.due_date,
            g.points,
            g.assignment.max_points,
            g.comment,
            g.is_posted,
        ])
    return buf.getvalue()


@transaction.atomic
def import_students_csv(file_obj, default_school):
    reader = csv.DictReader(io.TextIOWrapper(file_obj, encoding="utf-8-sig"))
    created = updated = 0
    errors = []
    for i, row in enumerate(reader, start=2):
        sid = (row.get("student_id") or "").strip()
        if not sid:
            errors.append(f"Row {i}: missing student_id")
            continue
        school_code = (row.get("school_code") or default_school.code).strip()
        school = School.objects.filter(code=school_code).first() or default_school
        username = (row.get("username") or sid).strip()
        user, was_created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": row.get("first_name", ""),
                "last_name": row.get("last_name", ""),
                "email": row.get("email", ""),
                "role": UserRole.STUDENT,
                "school": school,
            },
        )
        if was_created:
            user.set_password(row.get("password") or "changeme123")
            user.save()
            created += 1
        else:
            updated += 1
        StudentProfile.objects.update_or_create(
            user=user,
            defaults={
                "school": school,
                "student_id": sid,
                "grade_level": int(row.get("grade_level") or 9),
            },
        )
    return {"created": created, "updated": updated, "errors": errors}


@transaction.atomic
def import_enrollments_csv(file_obj):
    reader = csv.DictReader(io.TextIOWrapper(file_obj, encoding="utf-8-sig"))
    count = 0
    errors = []
    for i, row in enumerate(reader, start=2):
        sid = (row.get("student_id") or "").strip()
        course_code = (row.get("course_code") or "").strip()
        section_num = (row.get("section_number") or "1").strip()
        term_name = (row.get("term_name") or "").strip()
        try:
            student = StudentProfile.objects.get(student_id=sid)
            section = Section.objects.get(
                course__code=course_code,
                section_number=section_num,
                term__name=term_name,
                course__school=student.school,
            )
            Enrollment.objects.get_or_create(student=student, section=section)
            count += 1
        except (StudentProfile.DoesNotExist, Section.DoesNotExist) as exc:
            errors.append(f"Row {i}: {exc}")
    return {"enrolled": count, "errors": errors}
