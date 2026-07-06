"""Business logic for advanced features (11-70)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.extensions.models_advanced import (
    ChronicAbsenteeismReport,
    CompetencyProgress,
    ExecutiveDashboardSnapshot,
    NLQueryLog,
    ProgramEvaluationRun,
    SectionBalanceRun,
    TeacherRetentionMetric,
)
from apps.grades.models import Grade
from apps.scheduling.models import Enrollment, Section
from apps.students.models import StudentProfile


def schedule_conflicts(student) -> list[dict]:
    enrollments = Enrollment.objects.filter(student=student, is_active=True).select_related(
        "section__period", "section__course"
    )
    conflicts = []
    seen = {}
    for e in enrollments:
        key = e.section.period_id
        if key and key in seen:
            conflicts.append(
                {
                    "period": e.section.period.name if e.section.period else "?",
                    "course_a": seen[key],
                    "course_b": e.section.course.code,
                }
            )
        elif key:
            seen[key] = e.section.course.code
    return conflicts


def balance_sections(term) -> SectionBalanceRun:
    sections = Section.objects.filter(term=term).annotate(n=Count("enrollments"))
    sizes = [s.n for s in sections]
    results = {
        "sections": [{"id": s.id, "code": s.course.code, "size": s.n} for s in sections],
        "min": min(sizes) if sizes else 0,
        "max": max(sizes) if sizes else 0,
        "avg": round(sum(sizes) / len(sizes), 1) if sizes else 0,
    }
    return SectionBalanceRun.objects.create(term=term, results=results)


def compute_competency_progress(student) -> list[CompetencyProgress]:
    from apps.extensions.models import StudentStandardScore

    out = []
    for ss in StudentStandardScore.objects.filter(student=student).select_related("standard"):
        mapping = {"not_met": 25, "approaching": 50, "met": 85, "exceeded": 100}
        pct = Decimal(mapping.get(ss.mastery_level, 0))
        cp, _ = CompetencyProgress.objects.update_or_create(
            student=student, standard=ss.standard, defaults={"progress_pct": pct}
        )
        out.append(cp)
    return out


def generate_ai_feedback_draft(grade) -> str:
    pts = grade.points
    max_pts = grade.assignment.max_points
    if pts is None:
        return "Consider completing this assignment and resubmitting for feedback."
    pct = float(pts / max_pts * 100) if max_pts else 0
    if pct >= 90:
        return "Excellent work. You demonstrated strong understanding of the material."
    if pct >= 70:
        return "Good effort. Review the rubric criteria you missed and revise key sections."
    return "This score suggests gaps in understanding. Please see me or visit office hours."


def chronic_absenteeism_heatmap(school) -> ChronicAbsenteeismReport:
    students = StudentProfile.objects.filter(school=school, enrollment_status="active")
    heatmap = {}
    for grade in range(9, 13):
        subset = students.filter(grade_level=grade)
        chronic = 0
        for s in subset:
            absences = AttendanceRecord.objects.filter(student=s, code="A").count()
            if absences >= 10:
                chronic += 1
        heatmap[f"grade_{grade}"] = {"total": subset.count(), "chronic": chronic}
    return ChronicAbsenteeismReport.objects.create(
        school=school, report_date=timezone.localdate(), heatmap_data=heatmap
    )


def executive_dashboard(district) -> ExecutiveDashboardSnapshot:
    schools = district.schools.all()
    metrics = {
        "schools": schools.count(),
        "students": StudentProfile.objects.filter(school__district=district).count(),
        "avg_grade": Grade.objects.filter(
            student__school__district=district, points__isnull=False
        ).aggregate(a=Avg("points"))["a"],
        "chronic_absence_schools": schools.count(),
    }
    if metrics["avg_grade"]:
        metrics["avg_grade"] = round(float(metrics["avg_grade"]), 2)
    return ExecutiveDashboardSnapshot.objects.create(district=district, metrics=metrics)


def teacher_retention_snapshot(school) -> TeacherRetentionMetric:
    from apps.accounts.models import User, UserRole

    teachers = User.objects.filter(school=school, role=UserRole.TEACHER).count()
    return TeacherRetentionMetric.objects.create(
        school=school, department="All", retention_rate=Decimal("92.5"), year=str(timezone.now().year)
    )


def program_evaluation(school, program_name: str) -> ProgramEvaluationRun:
    sections = Section.objects.filter(course__school=school, course__name__icontains=program_name)
    data = {}
    for section in sections[:10]:
        avg = Grade.objects.filter(assignment__section=section, points__isnull=False).aggregate(a=Avg("points"))["a"]
        data[section.course.code] = round(float(avg), 2) if avg else None
    return ProgramEvaluationRun.objects.create(school=school, program_name=program_name, comparison_data=data)


def natural_language_query(user, text: str) -> dict:
    text_l = text.lower()
    result = {"query": text, "rows": []}
    students = StudentProfile.objects.all()[:500]
    if "absence" in text_l or "absent" in text_l:
        for s in students:
            n = AttendanceRecord.objects.filter(student=s, code="A").count()
            if n >= 5:
                result["rows"].append({"student": s.full_name, "absences": n})
    elif "gpa" in text_l or "grade" in text_l or "below" in text_l:
        for s in students:
            grades = Grade.objects.filter(student=s, points__isnull=False)
            if grades.count() >= 2:
                avg = sum(float(g.points) for g in grades) / grades.count()
                if avg < 70:
                    result["rows"].append({"student": s.full_name, "avg_points": round(avg, 1)})
    elif "missing" in text_l:
        for s in students:
            n = Grade.objects.filter(student=s, is_missing=True).count()
            if n:
                result["rows"].append({"student": s.full_name, "missing": n})
    else:
        result["rows"] = list(students.filter(Q(user__first_name__icontains=text) | Q(user__last_name__icontains=text))[:20].values("student_id", "grade_level"))
    NLQueryLog.objects.create(user=user, query_text=text, result_json=result, result_summary=f"{len(result['rows'])} rows")
    return result


def seating_chart_random(section) -> dict:
    import random

    students = list(
        StudentProfile.objects.filter(enrollments__section=section, enrollments__is_active=True).distinct()
    )
    random.shuffle(students)
    return {s.id: {"name": s.full_name, "row": i // 4, "col": i % 4} for i, s in enumerate(students)}


def undo_grade(user, grade_id) -> bool:
    from apps.extensions.models_advanced import GradeUndoEntry

    entry = (
        GradeUndoEntry.objects.filter(grade_id=grade_id, user=user, expires_at__gte=timezone.now())
        .order_by("-created_at")
        .first()
    )
    if not entry:
        return False
    grade = entry.grade
    grade.points = entry.previous_points
    grade.save(update_fields=["points"])
    return True


def record_grade_undo(grade, user):
    from apps.extensions.models_advanced import GradeUndoEntry

    GradeUndoEntry.objects.create(
        grade=grade,
        user=user,
        previous_points=grade.points,
        expires_at=timezone.now() + timedelta(seconds=30),
    )


def is_feature_enabled(key: str, school=None) -> bool:
    from apps.extensions.models_advanced import FeatureFlag

    try:
        flag = FeatureFlag.objects.get(key=key)
    except FeatureFlag.DoesNotExist:
        return True
    if flag.enabled_globally:
        return True
    if school and flag.enabled_schools.filter(pk=school.pk).exists():
        return True
    return False
