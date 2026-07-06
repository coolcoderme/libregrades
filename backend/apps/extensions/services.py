"""Service helpers for extended features."""

from __future__ import annotations

import csv
import io
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.attendance.models import AttendanceRecord
from apps.behavior.models import BehaviorIncident
from apps.extensions.models import (
    CohortSnapshot,
    DropoutRiskAssessment,
    EquityMetricsSnapshot,
    GradeCalibrationSnapshot,
    LateWorkPolicy,
)
from apps.grades.models import Assignment, Grade, GradeCategory
from apps.scheduling.models import Enrollment, Section
from apps.students.at_risk import at_risk_students
from apps.students.models import StudentProfile


def apply_late_penalty(grade: Grade) -> Decimal | None:
    if grade.points is None:
        return None
    policy = LateWorkPolicy.objects.filter(section=grade.assignment.section).first()
    if not policy or not grade.assignment.due_date:
        return grade.points
    days_late = (timezone.localdate() - grade.assignment.due_date).days - policy.grace_days
    if days_late <= 0:
        return grade.points
    deduction = min(policy.max_deduction, policy.deduction_per_day * days_late)
    adjusted = grade.points * (1 - deduction / Decimal("100"))
    return max(Decimal("0"), adjusted).quantize(Decimal("0.01"))


def category_average(student, section, category: GradeCategory) -> float | None:
    grades = Grade.objects.filter(
        student=student,
        assignment__section=section,
        assignment__category=category,
        points__isnull=False,
    ).select_related("assignment")
    points = [float(g.points) for g in grades]
    if category.drop_lowest and len(points) > category.drop_lowest:
        points.sort()
        points = points[category.drop_lowest :]
    if not points:
        return None
    return sum(points) / len(points)


def weighted_grade_preview(student, section) -> dict:
    categories = GradeCategory.objects.filter(section=section)
    total_weight = sum(float(c.weight) for c in categories) or 100.0
    weighted = 0.0
    breakdown = []
    for cat in categories:
        avg = category_average(student, section, cat)
        if avg is None:
            continue
        pct = (float(cat.weight) / total_weight) * avg
        weighted += pct
        breakdown.append({"category": cat.name, "weight": float(cat.weight), "average": avg})
    return {"percentage": round(weighted, 2), "breakdown": breakdown}


def bulk_set_grade(section, assignment, points, student_ids=None):
    students = StudentProfile.objects.filter(enrollments__section=section, enrollments__is_active=True)
    if student_ids:
        students = students.filter(id__in=student_ids)
    count = 0
    for student in students.distinct():
        grade, _ = Grade.objects.get_or_create(assignment=assignment, student=student)
        grade.points = points
        grade.save()
        count += 1
    return count


def apply_assignment_template(template, section, start_date=None):
    from apps.extensions.models import TemplateAssignmentItem

    start = start_date or timezone.localdate()
    created = 0
    for item in TemplateAssignmentItem.objects.filter(template=template):
        cat, _ = GradeCategory.objects.get_or_create(
            section=section, name=item.category_name, defaults={"weight": Decimal("100")}
        )
        Assignment.objects.create(
            section=section,
            category=cat,
            title=item.title,
            max_points=item.max_points,
            due_date=start + timedelta(days=item.days_offset),
            is_extra_credit=item.is_extra_credit,
            accepts_submissions=True,
        )
        created += 1
    return created


def teacher_load_report(school):
    rows = []
    teachers = Section.objects.filter(course__school=school, term__is_current=True).values(
        "teacher_id", "teacher__first_name", "teacher__last_name"
    ).annotate(section_count=Count("id"))
    for t in teachers:
        if not t["teacher_id"]:
            continue
        enrollments = Enrollment.objects.filter(
            section__teacher_id=t["teacher_id"], section__term__is_current=True, is_active=True
        ).count()
        rows.append(
            {
                "teacher": f"{t['teacher__first_name']} {t['teacher__last_name']}".strip(),
                "sections": t["section_count"],
                "students": enrollments,
            }
        )
    return rows


def department_calibration(course, term):
    sections = Section.objects.filter(course=course, term=term)
    averages = {}
    for section in sections:
        grades = Grade.objects.filter(assignment__section=section, points__isnull=False)
        avg = grades.aggregate(a=Avg("points"))["a"]
        if avg is not None:
            averages[f"{section.section_number}"] = round(float(avg), 2)
    snap = GradeCalibrationSnapshot.objects.create(course=course, term=term, section_averages=averages)
    return snap


def compute_dropout_risk(student) -> DropoutRiskAssessment:
    missing = Grade.objects.filter(student=student, is_missing=True).count()
    absences = AttendanceRecord.objects.filter(student=student, code="A").count()
    major = BehaviorIncident.objects.filter(student=student, incident_type__in=("major", "suspension")).count()
    score = missing * 3 + absences * 2 + major * 10
    factors = []
    if missing:
        factors.append(f"{missing} missing assignments")
    if absences:
        factors.append(f"{absences} absences")
    if major:
        factors.append(f"{major} major incidents")
    return DropoutRiskAssessment.objects.create(
        student=student, risk_score=min(Decimal("100"), Decimal(score)), factors=factors
    )


def cohort_analytics(school, grade_level: int):
    students = StudentProfile.objects.filter(school=school, grade_level=grade_level, enrollment_status="active")
    avg_grade = Grade.objects.filter(student__in=students, points__isnull=False).aggregate(a=Avg("points"))["a"]
    metrics = {
        "student_count": students.count(),
        "avg_points": round(float(avg_grade), 2) if avg_grade else None,
        "at_risk": len(at_risk_students(students)),
    }
    return CohortSnapshot.objects.create(school=school, cohort_label=f"Grade {grade_level}", metrics=metrics)


def equity_dashboard(school):
    snapshots = []
    for subgroup, q in [
        ("all", Q()),
        ("grade_11", Q(grade_level=11)),
        ("grade_12", Q(grade_level=12)),
    ]:
        students = StudentProfile.objects.filter(school=school).filter(q)
        avg = Grade.objects.filter(student__in=students, points__isnull=False).aggregate(a=Avg("points"))["a"]
        metrics = {"student_count": students.count(), "avg_points": round(float(avg), 2) if avg else None}
        snapshots.append(
            EquityMetricsSnapshot.objects.create(school=school, subgroup=subgroup, metrics=metrics)
        )
    return snapshots


def run_custom_report(defn) -> str:
    from django.apps import apps

    model = apps.get_model(defn.model_name.split(".")[0], defn.model_name.split(".")[-1]) if "." in defn.model_name else None
    if model is None:
        try:
            model = apps.get_model("students", defn.model_name)
        except LookupError:
            model = apps.get_model("grades", defn.model_name)
    qs = model.objects.all()[:500]
    output = io.StringIO()
    cols = defn.columns or [f.name for f in model._meta.fields[:8]]
    writer = csv.DictWriter(output, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for obj in qs:
        row = {c: getattr(obj, c, "") for c in cols}
        writer.writerow(row)
    return output.getvalue()


def district_overview(district):
    schools = district.schools.all()
    return {
        "school_count": schools.count(),
        "student_count": StudentProfile.objects.filter(school__district=district).count(),
        "teacher_count": district.users.filter(role=UserRole.TEACHER).count(),
        "schools": [{"name": s.name, "code": s.code, "students": s.students.count()} for s in schools],
    }
