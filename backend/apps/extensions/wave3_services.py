"""Services for wave 3 features."""

from __future__ import annotations

import hashlib
import json

from django.db.models import Avg
from django.utils import timezone

from apps.grades.models import Grade
from apps.students.models import StudentProfile


def help_chatbot_answer(question: str) -> str:
    q = question.lower()
    if "link" in q and "child" in q:
        return "Go to Parent → Link Child and enter the verification code from your school."
    if "grade" in q:
        return "Grades appear after teachers post them. Check Notifications for updates."
    if "password" in q:
        return "Contact your school admin to reset your password."
    return "Browse Features in the navbar or press Ctrl+K for quick navigation."


def ai_missing_nudge_text(student) -> str:
    missing = Grade.objects.filter(student=student, is_missing=True).count()
    if missing:
        return f"You have {missing} missing assignment(s). Log in to LibreGrades to see details."
    return "You're caught up — great work!"


def ai_report_narrative(student, term) -> str:
    grades = Grade.objects.filter(student=student, points__isnull=False).select_related("assignment")[:20]
    if not grades:
        return f"{student.full_name} is progressing through {term.name}. No graded work yet."
    avg = sum(float(g.points) for g in grades) / len(grades)
    return (
        f"{student.full_name} demonstrates {'strong' if avg >= 85 else 'steady' if avg >= 70 else 'developing'} "
        f"performance this term with an average around {avg:.0f} points on recent assignments."
    )


def detect_grade_anomalies(section):
    from apps.extensions.models_wave3 import GradeAnomaly

    created = []
    for grade in Grade.objects.filter(assignment__section=section, points__isnull=False):
        avg = Grade.objects.filter(assignment=grade.assignment, points__isnull=False).aggregate(a=Avg("points"))["a"]
        if avg and float(grade.points) > float(avg) * 1.5:
            obj, _ = GradeAnomaly.objects.get_or_create(
                grade=grade, defaults={"reason": "Score unusually high vs class average", "severity": "medium"}
            )
            created.append(obj)
    return created


def athletics_eligibility_check(student) -> dict:
    grades = Grade.objects.filter(student=student, points__isnull=False)
    gpa = sum(float(g.points) for g in grades) / grades.count() if grades.count() else 0
    from apps.attendance.models import AttendanceRecord

    absences = AttendanceRecord.objects.filter(student=student, code="A").count()
    eligible = gpa >= 2.0 and absences < 15
    return {"gpa": round(gpa, 2), "absences": absences, "is_eligible": eligible}


def item_analysis_for_quiz(quiz):
    from apps.extensions.models_advanced import QuizQuestion, QuizAttempt
    from apps.extensions.models_wave3 import ItemAnalysisReport

    reports = []
    for q in QuizQuestion.objects.filter(quiz=quiz):
        attempts = QuizAttempt.objects.filter(quiz=quiz)
        total = attempts.count() or 1
        miss = sum(1 for a in attempts if str(q.id) not in (a.answers or {}))
        rate = round(miss / total * 100, 1)
        reports.append(ItemAnalysisReport.objects.create(quiz=quiz, question_id=q.id, miss_rate=rate))
    return reports


def append_immutable_audit(event_type: str, data: dict):
    from apps.extensions.models_wave3 import ImmutableAuditEntry

    last = ImmutableAuditEntry.objects.order_by("-id").first()
    prev = last.payload_hash if last else ""
    payload = json.dumps({"event": event_type, "data": data, "prev": prev}, sort_keys=True)
    h = hashlib.sha256(payload.encode()).hexdigest()
    return ImmutableAuditEntry.objects.create(
        event_type=event_type, data=data, previous_hash=prev, payload_hash=h
    )


def auto_project_groups(section, size=4):
    import random
    from apps.extensions.models_wave3 import ProjectGroup

    students = list(
        StudentProfile.objects.filter(enrollments__section=section, enrollments__is_active=True).distinct()
    )
    random.shuffle(students)
    groups = []
    for i in range(0, len(students), size):
        chunk = students[i : i + size]
        g = ProjectGroup.objects.create(
            section=section, name=f"Group {len(groups) + 1}", member_ids=[s.id for s in chunk]
        )
        groups.append(g)
    return groups


def board_packet_generate(district, meeting_date):
    from apps.core.models import School
    from apps.extensions.models_wave3 import BoardPacket

    schools = School.objects.filter(district=district)
    html = f"<h1>Board packet — {meeting_date}</h1><ul>"
    for s in schools:
        n = StudentProfile.objects.filter(school=s).count()
        html += f"<li>{s.name}: {n} students</li>"
    html += "</ul>"
    return BoardPacket.objects.create(
        district=district, meeting_date=meeting_date, title=f"Board meeting {meeting_date}", content_html=html
    )
