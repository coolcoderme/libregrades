"""At-risk student scoring for counselors."""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.behavior.models import BehaviorIncident
from apps.grades.models import Grade
from apps.students.models import StudentProfile


def at_risk_students(students_qs, *, missing_threshold=2, absence_threshold=3):
    today = timezone.localdate()
    week_ago = today - timedelta(days=7)
    results = []
    for student in students_qs.select_related("user", "school"):
        missing = Grade.objects.filter(student=student, is_missing=True).count()
        absences = AttendanceRecord.objects.filter(
            student=student, code="A", date__gte=week_ago
        ).count()
        major_behavior = BehaviorIncident.objects.filter(
            student=student, incident_type__in=("major", "suspension"), incident_date__gte=week_ago
        ).count()
        score = 0
        flags = []
        if missing >= missing_threshold:
            score += missing
            flags.append(f"{missing} missing")
        if absences >= absence_threshold:
            score += absences * 2
            flags.append(f"{absences} absences (7d)")
        if major_behavior:
            score += major_behavior * 5
            flags.append(f"{major_behavior} major incidents")
        if score > 0:
            results.append({"student": student, "score": score, "flags": flags})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
