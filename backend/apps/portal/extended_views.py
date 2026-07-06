"""Portal views for extended features (excluding integrations)."""

from __future__ import annotations

import csv

from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import UserRole
from apps.accounts.permissions import accessible_students, get_parent_profile, user_can_edit_grades
from apps.extensions.calendar import ical_response
from apps.extensions.models import (
    AdminIPAllowlist,
    AssignmentSubmission,
    AssignmentTemplate,
    BellSchedule,
    BellScheduleVariant,
    CustomReportDefinition,
    DailyBulletinEntry,
    DataRetentionPolicy,
    DropoutRiskAssessment,
    FeedbackTicket,
    FerpaConsent,
    GradeRevisionLog,
    HallPass,
    InterventionPlan,
    LateWorkPolicy,
    LearningStandard,
    MasterScheduleDraft,
    MealEligibility,
    PBISPoint,
    PBISReward,
    PDRecord,
    PlagiarismCheckResult,
    PortfolioItem,
    ResourceBooking,
    ResourceRoom,
    RestorativeJusticeNote,
    Rubric,
    RubricCriterion,
    RubricScore,
    SandboxConfig,
    SchoolAttendanceSettings,
    StateReportTemplate,
    StudentBusAssignment,
    StudentGoal,
    StudentStandardScore,
    SubmissionAttachment,
    SubstitutePoolMember,
    TemplateAssignmentItem,
    TruancyCase,
    UserPortalPreferences,
    UserSessionRecord,
    WebhookEndpoint,
)
from apps.extensions.search import global_search
from apps.extensions.services import (
    apply_assignment_template,
    bulk_set_grade,
    cohort_analytics,
    compute_dropout_risk,
    department_calibration,
    district_overview,
    equity_dashboard,
    run_custom_report,
    teacher_load_report,
    weighted_grade_preview,
)
from apps.extensions.webhooks import decrypt_text, encrypt_text
from apps.grades.models import Assignment, Grade, GradeCategory
from apps.portal.views import _missing_for_student, _resolve_student
from apps.scheduling.models import Course, Section
from apps.students.models import StudentProfile


def _generic(request, title, **ctx):
    ctx["title"] = title
    return render(request, "portal/extended/generic.html", ctx)


def _school(request):
    return request.user.school or StudentProfile.objects.first().school


FEATURE_INDEX = [
    {
        "title": "Grading & assessment",
        "features": [
            {"num": 1, "label": "Rubrics", "url_name": "portal:teacher_sections"},
            {"num": 2, "label": "Standards grading", "url_name": "portal:ext_standards"},
            {"num": 3, "label": "Grade weighting preview", "url_name": "portal:teacher_sections"},
            {"num": 4, "label": "Bulk grade entry", "url_name": "portal:teacher_sections"},
            {"num": 5, "label": "Grade revision log", "url_name": "portal:ext_grade_history"},
            {"num": 6, "label": "Late work policies", "url_name": "portal:teacher_sections"},
            {"num": 7, "label": "Extra credit & drop rules", "url_name": "portal:teacher_sections"},
            {"num": 8, "label": "Assignment templates", "url_name": "portal:ext_templates"},
            {"num": 9, "label": "Scan-to-grade (OMR)", "url_name": "portal:teacher_sections"},
            {"num": 10, "label": "Plagiarism check", "url_name": "portal:ext_plagiarism"},
        ],
    },
    {
        "title": "Student & family",
        "features": [
            {"num": 11, "label": "Push event settings", "url_name": "portal:notification_preferences"},
            {"num": 12, "label": "Parent multi-child dashboard", "url_name": "portal:ext_parent_dashboard"},
            {"num": 13, "label": "Student goals", "url_name": "portal:ext_goals"},
            {"num": 14, "label": "Assignment submissions", "url_name": "portal:ext_submissions"},
            {"num": 15, "label": "Homework calendar (iCal)", "url_name": "portal:ext_ical"},
            {"num": 16, "label": "Language & locale", "url_name": "portal:ext_preferences"},
            {"num": 17, "label": "Accessibility mode", "url_name": "portal:ext_preferences"},
            {"num": 18, "label": "Student portfolio", "url_name": "portal:ext_portfolio"},
        ],
    },
    {
        "title": "Scheduling & operations",
        "features": [
            {"num": 19, "label": "Master schedule builder", "url_name": "portal:ext_master_schedule"},
            {"num": 20, "label": "Bell schedule variants", "url_name": "portal:ext_bell_schedules"},
            {"num": 21, "label": "Room booking", "url_name": "portal:ext_room_booking"},
            {"num": 22, "label": "Daily bulletin", "url_name": "portal:ext_bulletin"},
            {"num": 23, "label": "Bus transportation", "url_name": "portal:ext_bus"},
            {"num": 24, "label": "Meal eligibility", "url_name": "portal:ext_meals"},
        ],
    },
    {
        "title": "Attendance & behavior",
        "features": [
            {"num": 25, "label": "Attendance mode", "url_name": "portal:ext_attendance_mode"},
            {"num": 26, "label": "Truancy workflows", "url_name": "portal:ext_truancy"},
            {"num": 27, "label": "PBIS points", "url_name": "portal:ext_pbis"},
            {"num": 28, "label": "Restorative justice", "url_name": "portal:ext_restorative"},
            {"num": 29, "label": "Hall pass kiosk", "url_name": "portal:ext_hall_pass"},
        ],
    },
    {
        "title": "Staff & HR",
        "features": [
            {"num": 30, "label": "PD tracker", "url_name": "portal:ext_pd"},
            {"num": 31, "label": "Substitute pool", "url_name": "portal:ext_sub_pool"},
            {"num": 32, "label": "Teacher load report", "url_name": "portal:ext_teacher_load"},
            {"num": 33, "label": "Grade calibration", "url_name": "portal:ext_calibration"},
        ],
    },
    {
        "title": "Admin & compliance",
        "features": [
            {"num": 34, "label": "Custom report builder", "url_name": "portal:ext_custom_reports"},
            {"num": 35, "label": "Data retention", "url_name": "portal:ext_retention"},
            {"num": 36, "label": "FERPA consent", "url_name": "portal:ext_ferpa"},
            {"num": 37, "label": "State reporting", "url_name": "portal:ext_state_reports"},
            {"num": 38, "label": "Sandbox server", "url_name": "portal:ext_sandbox"},
            {"num": 39, "label": "API webhooks", "url_name": "portal:ext_webhooks"},
        ],
    },
    {
        "title": "Analytics & intervention",
        "features": [
            {"num": 45, "label": "Dropout risk", "url_name": "portal:ext_dropout_risk"},
            {"num": 46, "label": "RTI / MTSS plans", "url_name": "portal:ext_interventions"},
            {"num": 47, "label": "Cohort analytics", "url_name": "portal:ext_cohort"},
            {"num": 48, "label": "Equity dashboard", "url_name": "portal:ext_equity"},
        ],
    },
    {
        "title": "Security & platform",
        "features": [
            {"num": 49, "label": "Session management", "url_name": "portal:ext_sessions"},
            {"num": 50, "label": "Admin IP allowlist", "url_name": "portal:ext_ip_allowlist"},
            {"num": 51, "label": "Encrypted fields", "url_name": "portal:ext_encryption_info"},
            {"num": 52, "label": "Offline mode (mobile)", "url_name": "portal:ext_offline_info"},
            {"num": 53, "label": "District multi-school view", "url_name": "portal:ext_district_view"},
        ],
    },
    {
        "title": "Quality of life",
        "features": [
            {"num": 54, "label": "Global search", "url_name": "portal:ext_search"},
            {"num": 55, "label": "Gradebook keyboard shortcuts", "url_name": "portal:ext_keyboard_help"},
            {"num": 56, "label": "Dark mode", "url_name": "portal:ext_preferences"},
            {"num": 57, "label": "Guided tours", "url_name": "portal:ext_tour"},
            {"num": 58, "label": "Feedback widget", "url_name": "portal:ext_feedback"},
        ],
    },
]


@login_required
def features_index(request):
    return render(
        request,
        "portal/extended/index.html",
        {"groups": FEATURE_INDEX, "page_title": "Features (wave 1)"},
    )


# ── 1 Rubrics ──
@login_required
@require_http_methods(["GET", "POST"])
def rubrics(request, section_id):
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    if request.method == "POST":
        rubric = Rubric.objects.create(
            section=section,
            name=request.POST.get("name", "Rubric"),
            max_points=request.POST.get("max_points") or 100,
        )
        for i in range(1, 4):
            title = request.POST.get(f"criterion_{i}")
            if title:
                RubricCriterion.objects.create(
                    rubric=rubric, title=title, max_points=10, sort_order=i
                )
        return redirect("portal:ext_rubrics", section_id=section.id)
    rubrics_qs = Rubric.objects.filter(section=section).prefetch_related("criteria")
    rows = []
    for r in rubrics_qs:
        rows.append([r.name, r.max_points, r.criteria.count()])
    return _generic(
        request,
        f"Rubrics — {section.course.code}",
        description="Define rubric criteria and score students per criterion.",
        columns=["Rubric", "Max pts", "Criteria"],
        rows=rows,
        form_fields=[
            {"name": "name", "label": "Rubric name", "required": True},
            {"name": "max_points", "label": "Max points", "type": "number"},
            {"name": "criterion_1", "label": "Criterion 1"},
            {"name": "criterion_2", "label": "Criterion 2"},
            {"name": "criterion_3", "label": "Criterion 3"},
        ],
        extra_html='<p><a href="/teacher/sections/">← Back to sections</a></p>',
    )


@login_required
@require_http_methods(["POST"])
def rubric_score(request, section_id, rubric_id):
    section = get_object_or_404(Section, pk=section_id)
    rubric = get_object_or_404(Rubric, pk=rubric_id, section=section)
    student = get_object_or_404(StudentProfile, pk=request.POST.get("student_id"))
    for c in rubric.criteria.all():
        pts = request.POST.get(f"criterion_{c.id}")
        if pts:
            RubricScore.objects.update_or_create(
                criterion=c, student=student, defaults={"points": pts}
            )
    return redirect("portal:ext_rubrics", section_id=section.id)


# ── 2 Standards ──
@login_required
@require_http_methods(["GET", "POST"])
def standards_grading(request):
    if not request.user.is_staff_role:
        return HttpResponseForbidden()
    school = _school(request)
    if request.method == "POST":
        LearningStandard.objects.create(
            school=school,
            code=request.POST.get("code", ""),
            title=request.POST.get("title", ""),
            subject_area=request.POST.get("subject_area", ""),
        )
        return redirect("portal:ext_standards")
    standards = LearningStandard.objects.filter(school=school)
    rows = [[s.code, s.title, s.subject_area] for s in standards]
    return _generic(
        request,
        "Standards-based grading",
        columns=["Code", "Title", "Subject"],
        rows=rows,
        form_fields=[
            {"name": "code", "label": "Standard code", "required": True},
            {"name": "title", "label": "Title", "required": True},
            {"name": "subject_area", "label": "Subject"},
        ],
    )


@login_required
@require_http_methods(["POST"])
def standard_score_update(request, student_id):
    student = get_object_or_404(StudentProfile, pk=student_id)
    standard = get_object_or_404(LearningStandard, pk=request.POST.get("standard_id"))
    StudentStandardScore.objects.update_or_create(
        student=student,
        standard=standard,
        defaults={"mastery_level": request.POST.get("mastery_level", "not_met")},
    )
    return redirect("portal:ext_standards")


# ── 3 Weighting preview ──
@login_required
def grade_weighting(request, section_id):
    section = get_object_or_404(Section, pk=section_id)
    student = StudentProfile.objects.filter(enrollments__section=section).first()
    preview = weighted_grade_preview(student, section) if student else {"breakdown": [], "percentage": None}
    rows = [[b["category"], f"{b['weight']}%", f"{b['average']:.1f}"] for b in preview["breakdown"]]
    return _generic(
        request,
        f"Grade weighting — {section.course.code}",
        description=f"Preview weighted grade: {preview['percentage']}%",
        columns=["Category", "Weight", "Average"],
        rows=rows,
    )


# ── 4 Bulk grade ──
@login_required
@require_http_methods(["GET", "POST"])
def bulk_grade_entry(request, section_id):
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    assignments = Assignment.objects.filter(section=section)
    result = None
    if request.method == "POST":
        assignment = get_object_or_404(Assignment, pk=request.POST.get("assignment_id"), section=section)
        result = bulk_set_grade(section, assignment, request.POST.get("points"))
    return _generic(
        request,
        f"Bulk grade entry — {section.course.code}",
        alert={"text": f"Updated {result} students."} if result else None,
        form_fields=[
            {
                "name": "assignment_id",
                "label": "Assignment",
                "type": "select",
                "required": True,
                "options": [{"value": a.id, "label": a.title} for a in assignments],
            },
            {"name": "points", "label": "Points for all", "type": "number", "required": True},
        ],
        submit_label="Apply to all students",
    )


# ── 5 Grade history ──
@login_required
def grade_history(request, section_id=None):
    if not request.user.is_staff_role:
        return HttpResponseForbidden()
    logs = GradeRevisionLog.objects.select_related("grade__assignment", "grade__student", "changed_by")[:200]
    if section_id:
        logs = logs.filter(grade__assignment__section_id=section_id)
    rows = []
    for log in logs:
        rows.append(
            [
                log.grade.student.full_name,
                log.grade.assignment.title,
                log.old_points,
                log.new_points,
                log.created_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )
    return _generic(
        request,
        "Grade revision log",
        columns=["Student", "Assignment", "Old", "New", "When"],
        rows=rows,
    )


# ── 6 Late policy ──
@login_required
@require_http_methods(["GET", "POST"])
def late_work_policy(request, section_id):
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    if request.method == "POST":
        LateWorkPolicy.objects.update_or_create(
            section=section,
            defaults={
                "deduction_per_day": request.POST.get("deduction_per_day") or 10,
                "max_deduction": request.POST.get("max_deduction") or 50,
                "grace_days": request.POST.get("grace_days") or 0,
            },
        )
        return redirect("portal:ext_late_policy", section_id=section.id)
    policy = LateWorkPolicy.objects.filter(section=section).first()
    return _generic(
        request,
        f"Late work policy — {section.course.code}",
        description=str(policy) if policy else "No policy set.",
        form_fields=[
            {"name": "deduction_per_day", "label": "% deduction/day", "type": "number", "value": "10"},
            {"name": "max_deduction", "label": "Max deduction %", "type": "number", "value": "50"},
            {"name": "grace_days", "label": "Grace days", "type": "number", "value": "0"},
        ],
    )


# ── 7 Drop rules / extra credit ──
@login_required
@require_http_methods(["GET", "POST"])
def drop_rules(request, section_id):
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    categories = GradeCategory.objects.filter(section=section)
    if request.method == "POST":
        cat = get_object_or_404(GradeCategory, pk=request.POST.get("category_id"), section=section)
        cat.drop_lowest = int(request.POST.get("drop_lowest") or 0)
        cat.save()
        return redirect("portal:ext_drop_rules", section_id=section.id)
    rows = [[c.name, c.weight, c.drop_lowest] for c in categories]
    return _generic(
        request,
        f"Drop lowest & extra credit — {section.course.code}",
        description="Mark assignments as extra credit when creating them. Set drop-lowest per category below.",
        columns=["Category", "Weight %", "Drop lowest N"],
        rows=rows,
        form_fields=[
            {
                "name": "category_id",
                "label": "Category",
                "type": "select",
                "options": [{"value": c.id, "label": c.name} for c in categories],
            },
            {"name": "drop_lowest", "label": "Drop lowest N scores", "type": "number"},
        ],
    )


# ── 8 Templates ──
@login_required
@require_http_methods(["GET", "POST"])
def assignment_templates(request):
    if not request.user.is_staff_role:
        return HttpResponseForbidden()
    school = _school(request)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            t = AssignmentTemplate.objects.create(
                school=school, name=request.POST.get("name", "Template"), created_by=request.user
            )
            TemplateAssignmentItem.objects.create(template=t, title="Sample assignment", days_offset=7)
        elif action == "apply":
            template = get_object_or_404(AssignmentTemplate, pk=request.POST.get("template_id"))
            section = get_object_or_404(Section, pk=request.POST.get("section_id"))
            n = apply_assignment_template(template, section)
            return _generic(request, "Templates applied", alert={"text": f"Created {n} assignments."})
        return redirect("portal:ext_templates")
    templates = AssignmentTemplate.objects.filter(school=school)
    sections = Section.objects.filter(term__is_current=True, course__school=school)
    rows = [[t.name, t.items.count()] for t in templates]
    return _generic(
        request,
        "Assignment templates",
        columns=["Template", "Items"],
        rows=rows,
        form_fields=[
            {"name": "action", "type": "hidden", "value": "create"},
            {"name": "name", "label": "New template name", "required": True},
        ],
    )


# ── 9 OMR ──
@login_required
@require_http_methods(["GET", "POST"])
def omr_scan(request, section_id):
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    from apps.extensions.models import OMRScanBatch

    if request.method == "POST" and request.FILES.get("scan"):
        assignment = get_object_or_404(Assignment, pk=request.POST.get("assignment_id"), section=section)
        OMRScanBatch.objects.create(
            section=section,
            assignment=assignment,
            uploaded_by=request.user,
            image=request.FILES["scan"],
            status="processing",
            results_json={"message": "OMR queued — manual review required"},
        )
        return redirect("portal:ext_omr", section_id=section.id)
    batches = OMRScanBatch.objects.filter(section=section)[:20]
    rows = [[b.assignment.title, b.status, b.created_at.date()] for b in batches]
    return _generic(
        request,
        f"Scan-to-grade (OMR) — {section.course.code}",
        columns=["Assignment", "Status", "Uploaded"],
        rows=rows,
        form_fields=[
            {
                "name": "assignment_id",
                "label": "Assignment",
                "type": "select",
                "options": [{"value": a.id, "label": a.title} for a in section.assignments.all()],
            },
            {"name": "scan", "label": "Scan image", "type": "file", "required": True},
        ],
    )


# ── 10 Plagiarism ──
@login_required
def plagiarism_checks(request):
    if not request.user.is_staff_role:
        return HttpResponseForbidden()
    checks = PlagiarismCheckResult.objects.select_related("submission__assignment", "submission__student")[:50]
    rows = [
        [c.submission.student.full_name, c.submission.assignment.title, c.similarity_score, c.status]
        for c in checks
    ]
    return _generic(
        request,
        "Plagiarism check queue",
        description="Hook for external similarity services. Submissions queue checks automatically.",
        columns=["Student", "Assignment", "Similarity %", "Status"],
        rows=rows,
    )


# ── 12 Parent multi-child ──
@login_required
def parent_multi_child_dashboard(request):
    if request.user.role != UserRole.PARENT:
        return HttpResponseForbidden()
    profile = get_parent_profile(request.user)
    if not profile:
        return HttpResponseForbidden()
    cards = []
    for child in profile.students.all():
        grades = Grade.objects.filter(student=child, points__isnull=False)[:10]
        avg = sum(float(g.points) for g in grades) / len(grades) if grades else None
        cards.append(
            {"id": child.id, "name": child.full_name, "missing": _missing_for_student(child), "avg": f"{avg:.1f}" if avg else None}
        )
    return render(request, "portal/extended/parent_multi_child.html", {"children_cards": cards})


# ── 13 Goals ──
@login_required
@require_http_methods(["GET", "POST"])
def student_goals(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    if request.method == "POST":
        StudentGoal.objects.create(
            student=student,
            title=request.POST.get("title", ""),
            target_value=request.POST.get("target_value", ""),
            due_date=request.POST.get("due_date") or None,
        )
        return redirect("portal:ext_goals")
    goals = StudentGoal.objects.filter(student=student)
    rows = [[g.title, g.target_value, g.current_value, g.due_date, "✓" if g.is_complete else "—"] for g in goals]
    return _generic(
        request,
        f"Goals — {student.full_name}",
        columns=["Goal", "Target", "Current", "Due", "Done"],
        rows=rows,
        form_fields=[
            {"name": "title", "label": "Goal", "required": True},
            {"name": "target_value", "label": "Target (e.g. B+)"},
            {"name": "due_date", "label": "Due date", "type": "date"},
        ],
    )


# ── 14 Submissions ──
@login_required
@require_http_methods(["GET", "POST"])
def assignment_submissions(request, assignment_id=None):
    student = _resolve_student(request)
    if request.user.role == UserRole.STUDENT and student and request.method == "POST":
        assignment = get_object_or_404(Assignment, pk=request.POST.get("assignment_id"), accepts_submissions=True)
        sub, _ = AssignmentSubmission.objects.get_or_create(assignment=assignment, student=student)
        if request.FILES.get("file"):
            SubmissionAttachment.objects.create(submission=sub, file=request.FILES["file"], filename=request.FILES["file"].name)
            PlagiarismCheckResult.objects.get_or_create(submission=sub, defaults={"status": "queued"})
        return redirect("portal:ext_submissions")
    rows = []
    if request.user.is_staff_role:
        subs = AssignmentSubmission.objects.select_related("assignment", "student")[:100]
        rows = [[s.student.full_name, s.assignment.title, s.submitted_at.date()] for s in subs]
    elif student:
        subs = AssignmentSubmission.objects.filter(student=student)
        rows = [[s.assignment.title, s.submitted_at.date()] for s in subs]
    fields = []
    if student:
        fields = [
            {"name": "assignment_id", "label": "Assignment ID", "required": True},
            {"name": "file", "label": "Upload file", "type": "file", "required": True},
        ]
    return _generic(
        request,
        "Assignment submissions",
        columns=["Student", "Assignment", "Submitted"] if request.user.is_staff_role else ["Assignment", "Submitted"],
        rows=rows,
        form_fields=fields or None,
    )


# ── 15 iCal ──
@login_required
def homework_ical(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    return ical_response(student)


# ── 16-17, 56 Preferences ──
@login_required
@require_http_methods(["GET", "POST"])
def portal_preferences(request):
    prefs, _ = UserPortalPreferences.objects.get_or_create(user=request.user)
    if request.method == "POST":
        prefs.theme = request.POST.get("theme", prefs.theme)
        prefs.locale = request.POST.get("locale", prefs.locale)
        prefs.accessibility_large_text = request.POST.get("accessibility_large_text") == "on"
        prefs.accessibility_high_contrast = request.POST.get("accessibility_high_contrast") == "on"
        prefs.keyboard_shortcuts_enabled = request.POST.get("keyboard_shortcuts_enabled") == "on"
        prefs.save()
        request.session["portal_theme"] = prefs.theme
        request.session["portal_locale"] = prefs.locale
        request.session["portal_a11y_large"] = prefs.accessibility_large_text
        request.session["portal_a11y_contrast"] = prefs.accessibility_high_contrast
        return redirect("portal:ext_preferences")
    return _generic(
        request,
        "Portal preferences",
        description="Theme, language, accessibility, and keyboard shortcuts.",
        form_fields=[
            {
                "name": "theme",
                "label": "Theme",
                "type": "select",
                "options": [{"value": "light", "label": "Light"}, {"value": "dark", "label": "Dark"}],
            },
            {
                "name": "locale",
                "label": "Language",
                "type": "select",
                "options": [{"value": "en", "label": "English"}, {"value": "es", "label": "Español"}],
            },
            {"name": "accessibility_large_text", "label": "Large text", "type": "checkbox", "checked": prefs.accessibility_large_text},
            {"name": "accessibility_high_contrast", "label": "High contrast", "type": "checkbox", "checked": prefs.accessibility_high_contrast},
            {"name": "keyboard_shortcuts_enabled", "label": "Keyboard shortcuts in gradebook", "type": "checkbox", "checked": prefs.keyboard_shortcuts_enabled},
        ],
    )


# ── 18 Portfolio ──
@login_required
@require_http_methods(["GET", "POST"])
def student_portfolio(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    if request.method == "POST":
        PortfolioItem.objects.create(
            student=student,
            title=request.POST.get("title", ""),
            description=request.POST.get("description", ""),
            course_code=request.POST.get("course_code", ""),
            artifact=request.FILES.get("artifact"),
        )
        return redirect("portal:ext_portfolio")
    items = PortfolioItem.objects.filter(student=student)
    rows = [[i.title, i.course_code, i.created_at.date()] for i in items]
    return _generic(
        request,
        f"Portfolio — {student.full_name}",
        columns=["Title", "Course", "Added"],
        rows=rows,
        form_fields=[
            {"name": "title", "label": "Title", "required": True},
            {"name": "course_code", "label": "Course"},
            {"name": "description", "label": "Description", "type": "textarea"},
            {"name": "artifact", "label": "File", "type": "file"},
        ],
    )


# ── 19 Master schedule ──
@login_required
@require_http_methods(["GET", "POST"])
def master_schedule(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    school = _school(request)
    term = school.terms.filter(is_current=True).first()
    if request.method == "POST" and term:
        MasterScheduleDraft.objects.create(
            school=school,
            term=term,
            name=request.POST.get("name", "Draft"),
            data={"sections": list(Section.objects.filter(term=term).values("id", "course__code", "section_number"))},
            created_by=request.user,
        )
        return redirect("portal:ext_master_schedule")
    drafts = MasterScheduleDraft.objects.filter(school=school)[:20]
    rows = [[d.name, d.term.name, d.created_at.date()] for d in drafts]
    return _generic(
        request,
        "Master schedule builder",
        description="Draft schedules stored as JSON. Drag-and-drop UI can extend this data model.",
        columns=["Draft", "Term", "Created"],
        rows=rows,
        form_fields=[{"name": "name", "label": "New draft name", "required": True}],
    )


# ── 20 Bell schedules ──
@login_required
@require_http_methods(["GET", "POST"])
def bell_schedules(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    school = _school(request)
    if request.method == "POST":
        BellSchedule.objects.create(school=school, name=request.POST.get("name", "Default"), is_default=True)
        return redirect("portal:ext_bell_schedules")
    schedules = BellSchedule.objects.filter(school=school)
    variants = BellScheduleVariant.objects.filter(school=school)
    rows = [[s.name, "Default" if s.is_default else "—"] for s in schedules]
    rows += [[f"Variant: {v.name}", v.schedule.name] for v in variants]
    return _generic(
        request,
        "Bell schedules & variants",
        columns=["Schedule", "Notes"],
        rows=rows,
        form_fields=[{"name": "name", "label": "Schedule name", "required": True}],
    )


# ── 21 Room booking ──
@login_required
@require_http_methods(["GET", "POST"])
def room_booking(request):
    if not request.user.is_staff_role:
        return HttpResponseForbidden()
    school = _school(request)
    if request.method == "POST":
        room = get_object_or_404(ResourceRoom, pk=request.POST.get("room_id"))
        from django.utils.dateparse import parse_datetime

        ResourceBooking.objects.create(
            room=room,
            booked_by=request.user,
            start_at=parse_datetime(request.POST.get("start_at")),
            end_at=parse_datetime(request.POST.get("end_at")),
            purpose=request.POST.get("purpose", ""),
        )
        return redirect("portal:ext_room_booking")
    rooms = ResourceRoom.objects.filter(school=school)
    if not rooms.exists():
        ResourceRoom.objects.create(school=school, name="Room 101")
        rooms = ResourceRoom.objects.filter(school=school)
    bookings = ResourceBooking.objects.filter(room__school=school).select_related("room")[:30]
    rows = [[b.room.name, b.start_at, b.end_at, b.purpose] for b in bookings]
    return _generic(
        request,
        "Room & resource booking",
        columns=["Room", "Start", "End", "Purpose"],
        rows=rows,
        form_fields=[
            {
                "name": "room_id",
                "label": "Room",
                "type": "select",
                "options": [{"value": r.id, "label": r.name} for r in rooms],
            },
            {"name": "start_at", "label": "Start", "type": "datetime-local", "required": True},
            {"name": "end_at", "label": "End", "type": "datetime-local", "required": True},
            {"name": "purpose", "label": "Purpose"},
        ],
    )


# ── 22 Bulletin ──
@login_required
@require_http_methods(["GET", "POST"])
def daily_bulletin(request):
    school = _school(request)
    today = timezone.localdate()
    if request.method == "POST" and request.user.is_staff_role:
        DailyBulletinEntry.objects.create(
            school=school,
            date=request.POST.get("date") or today,
            title=request.POST.get("title", ""),
            body=request.POST.get("body", ""),
            author=request.user,
        )
        return redirect("portal:ext_bulletin")
    entries = DailyBulletinEntry.objects.filter(school=school, date=today)
    rows = [[e.title, e.body[:80]] for e in entries]
    return _generic(
        request,
        f"Daily bulletin — {today}",
        columns=["Title", "Preview"],
        rows=rows,
        form_fields=[
            {"name": "title", "label": "Title", "required": True},
            {"name": "body", "label": "Body", "type": "textarea", "required": True},
        ]
        if request.user.is_staff_role
        else None,
    )


# ── 23 Bus ──
@login_required
@require_http_methods(["GET", "POST"])
def bus_transportation(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    from apps.extensions.models import BusRoute, BusStop

    school = _school(request)
    if request.method == "POST":
        route = BusRoute.objects.create(school=school, name=request.POST.get("name", "Route A"))
        BusStop.objects.create(route=route, name="Main & Oak", sort_order=1)
        return redirect("portal:ext_bus")
    routes = BusRoute.objects.filter(school=school).prefetch_related("stops")
    rows = [[r.name, r.stops.count(), StudentBusAssignment.objects.filter(route=r).count()] for r in routes]
    return _generic(
        request,
        "Bus transportation",
        columns=["Route", "Stops", "Students"],
        rows=rows,
        form_fields=[{"name": "name", "label": "Route name", "required": True}],
    )


# ── 24 Meals ──
@login_required
@require_http_methods(["GET", "POST"])
def meal_eligibility(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    if request.method == "POST":
        student = get_object_or_404(StudentProfile, pk=request.POST.get("student_id"))
        MealEligibility.objects.create(
            student=student,
            program=request.POST.get("program", "free"),
            effective_date=timezone.localdate(),
        )
        return redirect("portal:ext_meals")
    rows = [
        [m.student.full_name, m.program, m.effective_date]
        for m in MealEligibility.objects.select_related("student")[:100]
    ]
    return _generic(
        request,
        "Meal eligibility",
        description="FERPA-sensitive — admin access only.",
        columns=["Student", "Program", "Effective"],
        rows=rows,
        form_fields=[
            {"name": "student_id", "label": "Student ID", "required": True},
            {"name": "program", "label": "Program (free/reduced/paid)"},
        ],
    )


# ── 25 Attendance mode ──
@login_required
@require_http_methods(["GET", "POST"])
def attendance_mode(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    school = _school(request)
    settings_obj, _ = SchoolAttendanceSettings.objects.get_or_create(school=school)
    if request.method == "POST":
        settings_obj.mode = request.POST.get("mode", "period")
        settings_obj.save()
        return redirect("portal:ext_attendance_mode")
    return _generic(
        request,
        "Attendance mode",
        description=f"Current mode: {settings_obj.mode}",
        form_fields=[
            {
                "name": "mode",
                "label": "Mode",
                "type": "select",
                "options": [{"value": "daily", "label": "Daily"}, {"value": "period", "label": "Period"}],
            },
        ],
    )


# ── 26 Truancy ──
@login_required
def truancy_workflow(request):
    if request.user.role not in {UserRole.COUNSELOR, UserRole.SCHOOL_ADMIN, UserRole.DISTRICT_ADMIN}:
        return HttpResponseForbidden()
    from apps.attendance.models import AttendanceRecord
    from apps.extensions.models import TruancyLetter

    for student in accessible_students(request.user)[:50]:
        absences = AttendanceRecord.objects.filter(student=student, code="A").count()
        if absences >= 5:
            case, _ = TruancyCase.objects.get_or_create(student=student, defaults={"absence_count": absences})
            case.absence_count = absences
            case.save()
    cases = TruancyCase.objects.filter(status="open").select_related("student")[:50]
    rows = [[c.student.full_name, c.absence_count, c.letters.count()] for c in cases]
    return _generic(
        request,
        "Truancy workflow",
        columns=["Student", "Absences", "Letters sent"],
        rows=rows,
    )


# ── 27 PBIS ──
@login_required
@require_http_methods(["GET", "POST"])
def pbis_points(request):
    if not request.user.is_staff_role:
        return HttpResponseForbidden()
    school = _school(request)
    if request.method == "POST":
        student = get_object_or_404(StudentProfile, pk=request.POST.get("student_id"))
        PBISPoint.objects.create(
            student=student,
            points=int(request.POST.get("points") or 0),
            reason=request.POST.get("reason", ""),
            awarded_by=request.user,
        )
        return redirect("portal:ext_pbis")
    rewards = PBISReward.objects.filter(school=school)
    if not rewards.exists():
        PBISReward.objects.create(school=school, name="Spirit sticker", point_cost=5)
    points = PBISPoint.objects.select_related("student")[:50]
    rows = [[p.student.full_name, p.points, p.reason, p.created_at.date()] for p in points]
    return _generic(
        request,
        "PBIS points",
        columns=["Student", "Points", "Reason", "Date"],
        rows=rows,
        form_fields=[
            {"name": "student_id", "label": "Student profile ID", "required": True},
            {"name": "points", "label": "Points (+/-)", "type": "number", "required": True},
            {"name": "reason", "label": "Reason", "required": True},
        ],
    )


# ── 28 Restorative ──
@login_required
@require_http_methods(["GET", "POST"])
def restorative_justice(request):
    if not request.user.is_staff_role:
        return HttpResponseForbidden()
    from apps.behavior.models import BehaviorIncident

    if request.method == "POST":
        incident = get_object_or_404(BehaviorIncident, pk=request.POST.get("incident_id"))
        RestorativeJusticeNote.objects.create(
            incident=incident,
            meeting_date=request.POST.get("meeting_date") or timezone.localdate(),
            agreement=request.POST.get("agreement", ""),
        )
        return redirect("portal:ext_restorative")
    notes = RestorativeJusticeNote.objects.select_related("incident__student")[:50]
    rows = [[n.incident.student.full_name, n.meeting_date, n.agreement[:60]] for n in notes]
    return _generic(
        request,
        "Restorative justice notes",
        columns=["Student", "Meeting", "Agreement"],
        rows=rows,
        form_fields=[
            {"name": "incident_id", "label": "Incident ID", "required": True},
            {"name": "meeting_date", "label": "Meeting date", "type": "date"},
            {"name": "agreement", "label": "Agreement", "type": "textarea"},
        ],
    )


# ── 29 Hall pass ──
@login_required
@require_http_methods(["GET", "POST"])
def hall_pass_kiosk(request):
    if request.method == "POST":
        student = get_object_or_404(StudentProfile, pk=request.POST.get("student_id"))
        HallPass.objects.create(
            student=student,
            destination=request.POST.get("destination", "Office"),
            issued_by=request.user if request.user.is_authenticated else None,
        )
        return redirect("portal:ext_hall_pass")
    active = HallPass.objects.filter(returned_at__isnull=True).select_related("student")[:30]
    rows = [[p.student.full_name, p.destination, p.issued_at.strftime("%H:%M")] for p in active]
    return _generic(
        request,
        "Hall pass kiosk",
        columns=["Student", "Destination", "Issued"],
        rows=rows,
        form_fields=[
            {"name": "student_id", "label": "Student profile ID", "required": True},
            {"name": "destination", "label": "Destination", "required": True},
        ],
    )


# ── 30 PD ──
@login_required
@require_http_methods(["GET", "POST"])
def pd_tracker(request):
    if not request.user.is_staff_role:
        return HttpResponseForbidden()
    if request.method == "POST":
        PDRecord.objects.create(
            staff=request.user,
            title=request.POST.get("title", ""),
            hours=request.POST.get("hours") or 1,
            completed_date=request.POST.get("completed_date") or timezone.localdate(),
        )
        return redirect("portal:ext_pd")
    records = PDRecord.objects.filter(staff=request.user)
    total = sum(float(r.hours) for r in records)
    rows = [[r.title, r.hours, r.completed_date] for r in records]
    return _generic(
        request,
        "Professional development",
        description=f"Total hours: {total}",
        columns=["Title", "Hours", "Completed"],
        rows=rows,
        form_fields=[
            {"name": "title", "label": "Training title", "required": True},
            {"name": "hours", "label": "Hours", "type": "number"},
            {"name": "completed_date", "label": "Date", "type": "date"},
        ],
    )


# ── 31 Sub pool ──
@login_required
@require_http_methods(["GET", "POST"])
def substitute_pool(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    school = _school(request)
    if request.method == "POST":
        SubstitutePoolMember.objects.create(
            school=school,
            name=request.POST.get("name", ""),
            email=request.POST.get("email", ""),
            subjects=request.POST.get("subjects", ""),
        )
        return redirect("portal:ext_sub_pool")
    members = SubstitutePoolMember.objects.filter(school=school, is_available=True)
    rows = [[m.name, m.subjects, m.email] for m in members]
    return _generic(
        request,
        "Substitute pool",
        columns=["Name", "Subjects", "Email"],
        rows=rows,
        form_fields=[
            {"name": "name", "label": "Name", "required": True},
            {"name": "email", "label": "Email"},
            {"name": "subjects", "label": "Subjects"},
        ],
    )


# ── 32 Teacher load ──
@login_required
def teacher_load(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    rows = [[r["teacher"], r["sections"], r["students"]] for r in teacher_load_report(_school(request))]
    return _generic(request, "Teacher load report", columns=["Teacher", "Sections", "Student enrollments"], rows=rows)


# ── 33 Calibration ──
@login_required
@require_http_methods(["GET", "POST"])
def grade_calibration(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    school = _school(request)
    courses = Course.objects.filter(school=school)
    term = school.terms.filter(is_current=True).first()
    if request.method == "POST" and term:
        course = get_object_or_404(Course, pk=request.POST.get("course_id"))
        snap = department_calibration(course, term)
        return _generic(request, "Calibration snapshot", alert={"text": str(snap.section_averages)})
    return _generic(
        request,
        "Department grade calibration",
        form_fields=[
            {
                "name": "course_id",
                "label": "Course",
                "type": "select",
                "options": [{"value": c.id, "label": c.code} for c in courses],
            },
        ],
        submit_label="Capture snapshot",
    )


# ── 34 Custom reports ──
@login_required
@require_http_methods(["GET", "POST"])
def custom_reports(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    school = _school(request)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            CustomReportDefinition.objects.create(
                school=school,
                name=request.POST.get("name", "Report"),
                model_name=request.POST.get("model_name", "StudentProfile"),
                columns=request.POST.get("columns", "student_id,grade_level").split(","),
                created_by=request.user,
            )
        elif action == "run":
            defn = get_object_or_404(CustomReportDefinition, pk=request.POST.get("report_id"))
            csv_data = run_custom_report(defn)
            response = HttpResponse(csv_data, content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{defn.name}.csv"'
            return response
        return redirect("portal:ext_custom_reports")
    reports = CustomReportDefinition.objects.filter(school=school)
    rows = [[r.name, r.model_name] for r in reports]
    return _generic(
        request,
        "Custom report builder",
        columns=["Report", "Model"],
        rows=rows,
        form_fields=[
            {"name": "action", "type": "hidden", "value": "create"},
            {"name": "name", "label": "Report name", "required": True},
            {"name": "model_name", "label": "Model (e.g. StudentProfile)", "value": "StudentProfile"},
            {"name": "columns", "label": "Columns (comma-separated)", "value": "student_id,grade_level"},
        ],
    )


# ── 35 Retention ──
@login_required
@require_http_methods(["GET", "POST"])
def data_retention(request):
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    district = request.user.district
    if request.method == "POST":
        DataRetentionPolicy.objects.create(
            district=district,
            model_name=request.POST.get("model_name", "Grade"),
            retain_years=int(request.POST.get("retain_years") or 7),
        )
        return redirect("portal:ext_retention")
    policies = DataRetentionPolicy.objects.filter(district=district)
    rows = [[p.model_name, p.retain_years, "Yes" if p.archive_before_delete else "No"] for p in policies]
    return _generic(
        request,
        "Data retention policies",
        columns=["Model", "Retain (years)", "Archive first"],
        rows=rows,
        form_fields=[
            {"name": "model_name", "label": "Model", "required": True},
            {"name": "retain_years", "label": "Years", "type": "number", "value": "7"},
        ],
    )


# ── 36 FERPA ──
@login_required
@require_http_methods(["GET", "POST"])
def ferpa_consent(request, student_id=None):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    student = get_object_or_404(StudentProfile, pk=student_id) if student_id else None
    if request.method == "POST":
        student = get_object_or_404(StudentProfile, pk=request.POST.get("student_id"))
        notes = request.POST.get("notes", "")
        FerpaConsent.objects.create(
            student=student,
            consent_type=request.POST.get("consent_type", "directory"),
            granted=request.POST.get("granted") == "on",
            granted_by=request.user,
            notes_encrypted=encrypt_text(notes),
        )
        return redirect("portal:ext_ferpa")
    consents = FerpaConsent.objects.select_related("student")[:100]
    rows = [
        [c.student.full_name, c.consent_type, "Yes" if c.granted else "No", decrypt_text(c.notes_encrypted)[:40]]
        for c in consents
    ]
    return _generic(
        request,
        "FERPA consent tracking",
        columns=["Student", "Type", "Granted", "Notes"],
        rows=rows,
        form_fields=[
            {"name": "student_id", "label": "Student profile ID", "required": True},
            {"name": "consent_type", "label": "Type (directory/media/etc.)"},
            {"name": "notes", "label": "Notes (encrypted at rest)", "type": "textarea"},
        ],
    )


# ── 37 State reports ──
@login_required
@require_http_methods(["GET", "POST"])
def state_reports(request):
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    district = request.user.district
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            StateReportTemplate.objects.create(
                district=district,
                name=request.POST.get("name", "State export"),
                state_code=request.POST.get("state_code", "CA"),
            )
        elif action == "export":
            students = StudentProfile.objects.filter(school__district=district)[:500]
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="state_export.csv"'
            writer = csv.writer(response)
            writer.writerow(["student_id", "grade_level", "school_code"])
            for s in students:
                writer.writerow([s.student_id, s.grade_level, s.school.code])
            return response
        return redirect("portal:ext_state_reports")
    templates = StateReportTemplate.objects.filter(district=district)
    rows = [[t.name, t.state_code] for t in templates]
    return _generic(
        request,
        "State reporting exports",
        columns=["Template", "State"],
        rows=rows,
        form_fields=[{"name": "action", "type": "hidden", "value": "export"}, {"name": "name", "label": "Template name"}],
        submit_label="Export CSV now",
    )


# ── 38 Sandbox ──
@login_required
def sandbox_info(request):
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    district = request.user.district
    configs = SandboxConfig.objects.filter(district=district)
    rows = [[c.label, c.database_url_hint or "—", "Active" if c.is_active else "—"] for c in configs]
    return _generic(
        request,
        "Sandbox / staging server",
        description="Clone this install with a separate DATABASE_URL and SECRET_KEY. Never point sandbox at production DB.",
        columns=["Label", "DB hint", "Status"],
        rows=rows,
    )


# ── 39 Webhooks ──
@login_required
@require_http_methods(["GET", "POST"])
def webhooks_manage(request):
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    district = request.user.district
    if request.method == "POST":
        WebhookEndpoint.objects.create(
            district=district,
            url=request.POST.get("url", ""),
            secret=request.POST.get("secret", ""),
            events=["grade.posted", "attendance.absent"],
        )
        return redirect("portal:ext_webhooks")
    hooks = WebhookEndpoint.objects.filter(district=district)
    rows = [[h.url, ", ".join(h.events), "Active" if h.is_active else "Off"] for h in hooks]
    return _generic(
        request,
        "API webhooks",
        columns=["URL", "Events", "Status"],
        rows=rows,
        form_fields=[
            {"name": "url", "label": "Endpoint URL", "required": True},
            {"name": "secret", "label": "Signing secret"},
        ],
    )


# ── 45 Dropout risk ──
@login_required
@require_http_methods(["GET", "POST"])
def dropout_risk(request):
    if request.user.role not in {UserRole.COUNSELOR, UserRole.SCHOOL_ADMIN, UserRole.DISTRICT_ADMIN}:
        return HttpResponseForbidden()
    if request.method == "POST":
        for student in accessible_students(request.user)[:30]:
            compute_dropout_risk(student)
        return redirect("portal:ext_dropout_risk")
    assessments = DropoutRiskAssessment.objects.select_related("student").order_by("-risk_score")[:50]
    rows = [[a.student.full_name, a.risk_score, ", ".join(a.factors)] for a in assessments]
    return _generic(
        request,
        "Predictive dropout risk",
        columns=["Student", "Risk score", "Factors"],
        rows=rows,
        form_fields=[{"name": "run", "type": "hidden", "value": "1"}],
        submit_label="Recompute all",
    )


# ── 46 Interventions ──
@login_required
@require_http_methods(["GET", "POST"])
def intervention_plans(request, student_id=None):
    if not request.user.is_staff_role:
        return HttpResponseForbidden()
    if request.method == "POST":
        student = get_object_or_404(StudentProfile, pk=request.POST.get("student_id"))
        InterventionPlan.objects.create(
            student=student,
            tier=int(request.POST.get("tier") or 1),
            title=request.POST.get("title", "Intervention plan"),
            goals=request.POST.get("goals", ""),
            start_date=timezone.localdate(),
            lead=request.user,
        )
        return redirect("portal:ext_interventions")
    plans = InterventionPlan.objects.filter(is_active=True).select_related("student")[:50]
    rows = [[p.student.full_name, f"Tier {p.tier}", p.title, p.start_date] for p in plans]
    return _generic(
        request,
        "RTI / MTSS intervention plans",
        columns=["Student", "Tier", "Plan", "Started"],
        rows=rows,
        form_fields=[
            {"name": "student_id", "label": "Student profile ID", "required": True},
            {"name": "tier", "label": "Tier (1-3)", "type": "number"},
            {"name": "title", "label": "Plan title", "required": True},
            {"name": "goals", "label": "Goals", "type": "textarea"},
        ],
    )


# ── 47 Cohort ──
@login_required
@require_http_methods(["GET", "POST"])
def cohort_analytics_view(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    school = _school(request)
    if request.method == "POST":
        cohort_analytics(school, int(request.POST.get("grade_level") or 9))
        return redirect("portal:ext_cohort")
    from apps.extensions.models import CohortSnapshot

    snaps = CohortSnapshot.objects.filter(school=school)[:20]
    rows = [[s.cohort_label, s.metrics.get("student_count"), s.metrics.get("avg_points")] for s in snaps]
    return _generic(
        request,
        "Cohort analytics",
        columns=["Cohort", "Students", "Avg points"],
        rows=rows,
        form_fields=[{"name": "grade_level", "label": "Grade level", "type": "number", "value": "11"}],
        submit_label="Capture snapshot",
    )


# ── 48 Equity ──
@login_required
@require_http_methods(["GET", "POST"])
def equity_dashboard_view(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    if request.method == "POST":
        equity_dashboard(_school(request))
        return redirect("portal:ext_equity")
    from apps.extensions.models import EquityMetricsSnapshot

    snaps = EquityMetricsSnapshot.objects.filter(school=_school(request)).order_by("-captured_at")[:20]
    rows = [[s.subgroup, s.metrics.get("student_count"), s.metrics.get("avg_points")] for s in snaps]
    return _generic(request, "Equity dashboard", columns=["Subgroup", "Students", "Avg points"], rows=rows, submit_label="Refresh metrics")


# ── 49 Sessions ──
@login_required
@require_http_methods(["GET", "POST"])
def session_management(request):
    records = UserSessionRecord.objects.filter(user=request.user, is_active=True)
    if request.method == "POST" and request.POST.get("revoke"):
        key = request.POST.get("session_key")
        UserSessionRecord.objects.filter(user=request.user, session_key=key).update(is_active=False)
        Session.objects.filter(session_key=key).delete()
        return redirect("portal:ext_sessions")
    rows = [[r.ip_address, r.user_agent[:40], r.last_seen] for r in records]
    return _generic(
        request,
        "Active sessions",
        description="Revoke any session you do not recognize.",
        columns=["IP", "Device", "Last seen"],
        rows=rows,
    )


# ── 50 IP allowlist ──
@login_required
@require_http_methods(["GET", "POST"])
def ip_allowlist(request):
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    district = request.user.district
    if request.method == "POST":
        AdminIPAllowlist.objects.create(
            district=district, cidr=request.POST.get("cidr", ""), label=request.POST.get("label", "")
        )
        return redirect("portal:ext_ip_allowlist")
    rows = [[e.cidr, e.label] for e in AdminIPAllowlist.objects.filter(district=district)]
    return _generic(
        request,
        "Admin IP allowlist",
        columns=["CIDR", "Label"],
        rows=rows,
        form_fields=[
            {"name": "cidr", "label": "CIDR (e.g. 10.0.0.0/8)", "required": True},
            {"name": "label", "label": "Label"},
        ],
    )


# ── 51 Encryption info ──
@login_required
def encryption_info(request):
    from django.conf import settings

    enabled = bool(getattr(settings, "EXTENSIONS_ENCRYPTION_KEY", ""))
    return _generic(
        request,
        "Encrypted fields at rest",
        description="Set EXTENSIONS_ENCRYPTION_KEY in .env (Fernet key). FERPA notes use this when enabled.",
        alert={"type": "success" if enabled else "warning", "text": "Encryption active" if enabled else "Encryption not configured — notes stored as plain text"},
    )


# ── 52 Offline info ──
@login_required
def offline_info(request):
    return _generic(
        request,
        "Offline mode (Kivy app)",
        description="The mobile app caches grades, schedule, and missing work locally. Data syncs when connectivity returns.",
    )


# ── 53 District view ──
@login_required
def district_multi_school(request):
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    overview = district_overview(request.user.district)
    rows = [[s["name"], s["code"], s["students"]] for s in overview["schools"]]
    return _generic(
        request,
        f"District overview — {overview['school_count']} schools",
        description=f"{overview['student_count']} students, {overview['teacher_count']} teachers",
        columns=["School", "Code", "Students"],
        rows=rows,
    )


# ── 54 Search ──
@login_required
def search_global(request):
    query = request.GET.get("q", "")
    results = global_search(request.user, query) if query else {}
    return render(request, "portal/extended/search.html", {"query": query, "results": results})


# ── 55 Keyboard help ──
@login_required
def keyboard_help(request):
    return _generic(
        request,
        "Gradebook keyboard shortcuts",
        description="Arrow keys move between cells. Enter saves. Tab moves to next field. Enable in preferences.",
    )


# ── 57 Tour ──
@login_required
@require_http_methods(["GET", "POST"])
def guided_tour(request):
    prefs, _ = UserPortalPreferences.objects.get_or_create(user=request.user)
    if request.method == "POST":
        prefs.tour_completed = {"dashboard": True, "gradebook": True}
        prefs.save()
        return redirect("portal:dashboard")
    return _generic(
        request,
        "Guided tour",
        description="Walkthrough highlights: Dashboard → Grades → Due this week → Notifications.",
        form_fields=[{"name": "complete", "type": "hidden", "value": "1"}],
        submit_label="Mark tour complete",
    )


# ── 58 Feedback ──
@login_required
@require_http_methods(["GET", "POST"])
def feedback_submit(request):
    from apps.core.server_identity import get_server_identity

    if request.method == "POST":
        FeedbackTicket.objects.create(
            user=request.user,
            server_code=get_server_identity().code,
            role=request.user.role,
            message=request.POST.get("message", ""),
            page_url=request.POST.get("page_url", request.META.get("HTTP_REFERER", "")),
        )
        return redirect("portal:ext_feedback")
    return _generic(
        request,
        "Send feedback",
        form_fields=[
            {"name": "message", "label": "Message", "type": "textarea", "required": True},
            {"name": "page_url", "label": "Page URL"},
        ],
    )


@login_required
def feedback_api(request):
    """JSON endpoint for navbar feedback widget."""
    if request.method != "POST":
        return JsonResponse({"detail": "POST only"}, status=405)
    from apps.core.server_identity import get_server_identity

    FeedbackTicket.objects.create(
        user=request.user,
        server_code=get_server_identity().code,
        role=request.user.role,
        message=request.POST.get("message", ""),
        page_url=request.POST.get("page_url", ""),
    )
    return JsonResponse({"ok": True})
