"""Generate apps/portal/advanced_views.py for features 11-70."""

from pathlib import Path

HEADER = '''"""Advanced portal views (wave 2: features 11-70, no integrations)."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import UserRole
from apps.accounts.permissions import accessible_students, user_can_edit_grades
from apps.extensions.advanced_services import (
    balance_sections,
    chronic_absenteeism_heatmap,
    compute_competency_progress,
    executive_dashboard,
    generate_ai_feedback_draft,
    is_feature_enabled,
    natural_language_query,
    program_evaluation,
    schedule_conflicts,
    seating_chart_random,
    teacher_retention_snapshot,
    undo_grade,
)
from apps.portal.extended_views import _generic, _school
from apps.portal.views import _resolve_student
from apps.scheduling.models import Section

'''

FEATURES = [
    (11, "interactive_rubric", "Interactive rubric grader", "adv_interactive_rubric", "section"),
    (12, "peer_review", "Peer review", "adv_peer_review", "section"),
    (13, "quizzes", "Quiz engine", "adv_quizzes", "section"),
    (14, "question_bank", "Question bank", "adv_question_bank", None),
    (15, "exit_tickets", "Exit tickets", "adv_exit_tickets", "section"),
    (16, "grade_appeals", "Grade appeals", "adv_grade_appeals", None),
    (17, "moderation", "Grade moderation queue", "adv_moderation", None),
    (18, "competency", "Competency progress", "adv_competency", None),
    (19, "voice_feedback", "Voice feedback", "adv_voice_feedback", None),
    (20, "ai_feedback", "AI feedback drafts", "adv_ai_feedback", None),
    (21, "mobile_apps", "Mobile app releases", "adv_mobile_apps", None),
    (22, "parent_digest", "Weekly parent digest", "adv_parent_digest", None),
    (23, "schedule_conflicts", "Schedule conflict checker", "adv_schedule_conflicts", None),
    (24, "course_registration", "Course registration", "adv_course_registration", None),
    (25, "student_hall_pass", "Student hall pass requests", "adv_student_hall_pass", None),
    (26, "safety_tips", "Safety tip line", "adv_safety_tips", None),
    (27, "translate", "Multilingual translate cache", "adv_translate", None),
    (28, "conf_self_schedule", "Conference self-scheduling", "adv_conf_self_schedule", None),
    (29, "e_signatures", "Document e-signatures", "adv_e_signatures", None),
    (30, "alumni_transcripts", "Alumni transcript requests", "adv_alumni_transcripts", None),
    (31, "visual_schedule", "Visual schedule builder", "adv_visual_schedule", None),
    (32, "section_balance", "Section balancing", "adv_section_balance", None),
    (33, "sub_autofill", "Substitute auto-fill", "adv_sub_autofill", None),
    (34, "inventory", "Inventory tracking", "adv_inventory", None),
    (35, "maintenance", "Maintenance tickets", "adv_maintenance", None),
    (36, "events", "Events & RSVPs", "adv_events", None),
    (37, "facility_use", "Facility use requests", "adv_facility_use", None),
    (38, "lockdown", "Lockdown drills", "adv_lockdown", None),
    (39, "weather_closure", "Weather closure mode", "adv_weather_closure", None),
    (40, "nurse_visits", "Nurse visit log", "adv_nurse_visits", None),
    (41, "immunization", "Immunization compliance", "adv_immunization", None),
    (42, "seclusion", "Seclusion & restraint", "adv_seclusion", None),
    (43, "title_ix", "Title IX tracking", "adv_title_ix", None),
    (44, "volunteer_clearance", "Volunteer clearances", "adv_volunteer_clearance", None),
    (45, "coppa", "COPPA consent", "adv_coppa", None),
    (46, "leave", "Staff leave", "adv_leave", None),
    (47, "evaluations", "Staff evaluations", "adv_evaluations", None),
    (48, "staff_directory", "Staff directory", "adv_staff_directory", None),
    (49, "union_rules", "Union contract rules", "adv_union_rules", None),
    (50, "sub_ratings", "Substitute ratings", "adv_sub_ratings", None),
    (51, "executive", "Executive dashboard", "adv_executive", None),
    (52, "benchmarks", "State benchmarks", "adv_benchmarks", None),
    (53, "chronic_absence", "Chronic absenteeism heatmap", "adv_chronic_absence", None),
    (54, "retention", "Teacher retention", "adv_retention", None),
    (55, "program_eval", "Program evaluation", "adv_program_eval", None),
    (56, "nl_query", "Natural language queries", "adv_nl_query", None),
    (57, "multi_tenant", "Multi-tenant mode", "adv_multi_tenant", None),
    (58, "plugins", "Plugin marketplace", "adv_plugins", None),
    (59, "graphql", "GraphQL API", "adv_graphql", None),
    (60, "collab_gradebook", "Realtime gradebook collab", "adv_collab_gradebook", "section"),
    (61, "backups", "Automated backups", "adv_backups", None),
    (62, "health", "System health dashboard", "adv_health", None),
    (63, "feature_flags", "Feature flags", "adv_feature_flags", None),
    (64, "ab_tests", "A/B testing", "adv_ab_tests", None),
    (65, "command_palette", "Command palette", "adv_command_palette", None),
    (66, "grade_undo", "Grade undo", "adv_grade_undo", None),
    (67, "print_views", "Print-optimized views", "adv_print_views", None),
    (68, "seating", "Seating charts", "adv_seating", "section"),
    (69, "waitlist", "Section waitlist", "adv_waitlist", "section"),
    (70, "term_archive", "Term archives", "adv_term_archive", None),
]

INDEX_GROUPS = [
    ("Grading depth (11-20)", list(range(11, 21))),
    ("Student & family (21-30)", list(range(21, 31))),
    ("Scheduling & ops (31-39)", list(range(31, 40))),
    ("Health & compliance (40-45)", list(range(40, 46))),
    ("Staff & HR (46-50)", list(range(46, 51))),
    ("Analytics (51-56)", list(range(51, 57))),
    ("Platform (57-64, 66, 69-70)", [57, 58, 59, 60, 61, 62, 63, 64, 66, 69, 70]),
    ("Quality of life (65-68)", [65, 67, 68]),
]

num_to_slug = {n: slug for n, slug, *_ in FEATURES}

body = [HEADER]

body.append(
    '''
ADVANCED_INDEX = [
'''
)
for title, nums in INDEX_GROUPS:
    body.append(f'    {{"title": "{title}", "features": [\n')
    for n in nums:
        slug = num_to_slug[n]
        label = next(t for num, s, t, *_ in FEATURES if num == n)
        body.append(f'        {{"num": {n}, "label": "{label}", "url_name": "portal:adv_{slug}"}},\n')
    body.append("    ]},\n")
body.append("]\n\n")

body.append("""
@login_required
def advanced_features_index(request):
    return render(request, "portal/extended/index.html", {
        "groups": ADVANCED_INDEX,
        "page_title": "Advanced features (11-70)",
    })


@login_required
def command_palette_api(request):
    items = []
    for group in ADVANCED_INDEX:
        for f in group["features"]:
            items.append({"label": f["label"], "num": f["num"]})
    return JsonResponse({"items": items})


@login_required
@require_http_methods(["POST"])
def grade_undo_api(request):
    gid = request.POST.get("grade_id")
    if undo_grade(request.user, gid):
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "detail": "No undo available"}, status=400)


@login_required
@require_http_methods(["GET", "POST"])
def graphql_explorer(request):
    if request.method == "POST":
        q = request.POST.get("query", "")
        if q.strip().startswith("{"):
            result = natural_language_query(request.user, q)
            return JsonResponse({"data": result})
        return JsonResponse({"data": {"message": "Use NL query text or POST to /adv/nl-query/"}})
    return _generic(request, "GraphQL / query explorer", description="POST a natural-language query below.", form_fields=[{"name": "query", "label": "Query", "type": "textarea", "required": True}])


""")

# Per-feature stub views with POST create where applicable
for num, slug, title, func, param in FEATURES:
    if func in ("command_palette_api", "grade_undo_api", "graphql_explorer", "advanced_features_index"):
        continue
    body.append(f"\n@login_required\n")
    if slug in ("nl_query", "schedule_conflicts", "competency", "ai_feedback", "section_balance", "chronic_absence", "executive", "program_eval", "seating", "visual_schedule"):
        body.append("@require_http_methods(['GET', 'POST'])\n")
    body.append(f"def adv_{slug}(request")
    if param == "section":
        body.append(f", section_id")
    body.append("):\n")
    body.append(f'    if not is_feature_enabled("adv_{slug}", _school(request)):\n')
    body.append('        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})\n')

    # Custom logic snippets
    if slug == "interactive_rubric":
        body.append("""    from apps.extensions.models_advanced import RubricGridScore
    from apps.extensions.models import Rubric
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    rubric = Rubric.objects.filter(section=section).first()
    if request.method == "POST" and rubric:
        student = get_object_or_404(accessible_students(request.user), pk=request.POST.get("student_id"))
        RubricGridScore.objects.update_or_create(rubric=rubric, student=student, defaults={"cell_scores": request.POST.dict()})
        return redirect("portal:adv_interactive_rubric", section_id=section_id)
    scores = RubricGridScore.objects.filter(rubric=rubric).select_related("student") if rubric else []
    rows = [[s.student.full_name, s.cell_scores] for s in scores]
    return _generic(request, f"Interactive rubric — {section.course.code}", columns=["Student", "Grid scores"], rows=rows,
        form_fields=[{"name": "student_id", "label": "Student profile ID"}, {"name": "c1", "label": "Criterion 1 score", "type": "number"}] if rubric else None)
""")
    elif slug == "schedule_conflicts":
        body.append("""    student = _resolve_student(request)
    if not student:
        return HttpResponseForbidden()
    conflicts = schedule_conflicts(student)
    rows = [[c["period"], c["course_a"], c["course_b"]] for c in conflicts]
    return _generic(request, f"Schedule conflicts — {student.full_name}", columns=["Period", "Course A", "Course B"], rows=rows)
""")
    elif slug == "nl_query":
        body.append("""    result = None
    if request.method == "POST":
        result = natural_language_query(request.user, request.POST.get("query", ""))
    rows = [[r.get("student", r)] if isinstance(r, dict) else [r] for r in (result or {}).get("rows", [])[:30]]
    return _generic(request, "Natural language queries", form_fields=[{"name": "query", "label": "Ask in plain English", "type": "textarea", "required": True}], rows=rows, columns=["Result"])
""")
    elif slug == "parent_digest":
        body.append("""    from apps.extensions.models_advanced import ParentDigestPreference
    pref, _ = ParentDigestPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        pref.enabled = request.POST.get("enabled") == "on"
        pref.save()
        return redirect("portal:adv_parent_digest")
    return _generic(request, "Weekly parent email digest", description=f"Digest {'enabled' if pref.enabled else 'disabled'}. Runs via Celery every week.",
        form_fields=[{"name": "enabled", "label": "Enable weekly digest", "type": "checkbox", "checked": pref.enabled}])
""")
    elif slug == "command_palette":
        body.append("""    return _generic(request, "Command palette", description="Press Ctrl+K anywhere in the portal to open the command palette.")
""")
    elif slug == "grade_undo":
        body.append("""    return _generic(request, "Grade undo", description="After saving a grade, press Ctrl+Z within 30 seconds or use the gradebook undo button.")
""")
    elif slug == "print_views":
        body.append("""    return render(request, "portal/advanced/print_grades.html", {"student": _resolve_student(request)})
""")
    elif slug == "seating":
        body.append("""    from apps.extensions.models_advanced import SeatingChart
    section = get_object_or_404(Section, pk=section_id)
    if request.method == "POST":
        layout = seating_chart_random(section)
        SeatingChart.objects.update_or_create(section=section, name="Default", defaults={"layout": layout})
        return redirect("portal:adv_seating", section_id=section_id)
    chart = SeatingChart.objects.filter(section=section).first()
    rows = [[sid, info.get("name"), info.get("row"), info.get("col")] for sid, info in (chart.layout.items() if chart else [])]
    return _generic(request, f"Seating chart — {section.course.code}", columns=["ID", "Student", "Row", "Col"], rows=rows, submit_label="Generate random layout")
""")
    elif slug == "executive":
        body.append("""    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    snap = executive_dashboard(request.user.district) if request.method == "POST" else None
    from apps.extensions.models_advanced import ExecutiveDashboardSnapshot
    latest = ExecutiveDashboardSnapshot.objects.filter(district=request.user.district).first()
    rows = [[k, v] for k, v in (latest.metrics.items() if latest else [])]
    return _generic(request, "Executive dashboard", rows=rows, columns=["Metric", "Value"], submit_label="Refresh snapshot")
""")
    elif slug == "feature_flags":
        body.append("""    from apps.extensions.models_advanced import FeatureFlag
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    if request.method == "POST":
        FeatureFlag.objects.get_or_create(key=request.POST.get("key", "demo"), defaults={"name": request.POST.get("name", "Demo feature")})
        return redirect("portal:adv_feature_flags")
    rows = [[f.key, f.name, f.enabled_globally] for f in FeatureFlag.objects.all()]
    return _generic(request, "Feature flags", columns=["Key", "Name", "Global"], rows=rows, form_fields=[{"name": "key", "label": "Key"}, {"name": "name", "label": "Name"}])
""")
    else:
        # Generic CRUD stub using model name inference
        model_map = {
            "peer_review": "PeerReviewAssignment",
            "quizzes": "Quiz",
            "question_bank": "QuestionBankItem",
            "exit_tickets": "ExitTicket",
            "grade_appeals": "GradeAppeal",
            "moderation": "GradeModerationItem",
            "voice_feedback": "VoiceFeedback",
            "mobile_apps": "MobileAppRelease",
            "course_registration": "CourseRegistrationRequest",
            "student_hall_pass": "StudentHallPassRequest",
            "safety_tips": "SafetyTip",
            "translate": "TranslatedContent",
            "conf_self_schedule": "ConferenceSelfScheduleSlot",
            "e_signatures": "DocumentSignatureRequest",
            "alumni_transcripts": "AlumniTranscriptRequest",
            "visual_schedule": "VisualScheduleGrid",
            "sub_autofill": "SubstituteAutoAssignment",
            "inventory": "AssetItem",
            "maintenance": "MaintenanceTicket",
            "events": "SchoolEvent",
            "facility_use": "FacilityUseRequest",
            "lockdown": "LockdownDrill",
            "weather_closure": "WeatherClosureMode",
            "nurse_visits": "NurseVisit",
            "immunization": "ImmunizationComplianceFlag",
            "seclusion": "SeclusionRestraintIncident",
            "title_ix": "TitleIXCase",
            "volunteer_clearance": "VolunteerClearance",
            "coppa": "COPPAConsentRecord",
            "leave": "StaffLeaveRequest",
            "evaluations": "StaffEvaluation",
            "staff_directory": "StaffDirectoryEntry",
            "union_rules": "UnionContractRule",
            "sub_ratings": "SubstituteRating",
            "benchmarks": "StateBenchmark",
            "retention": "TeacherRetentionMetric",
            "multi_tenant": "TenantOrganization",
            "plugins": "PluginModule",
            "collab_gradebook": "GradebookCollaborationSession",
            "backups": "BackupJob",
            "health": "SystemHealthMetric",
            "ab_tests": "ABTestVariant",
            "waitlist": "SectionWaitlist",
            "term_archive": "TermArchive",
        }
        model_name = model_map.get(slug, "SafetyTip")
        body.append(f"    from apps.extensions import models_advanced as ma\n")
        if param == "section":
            body.append("    section = get_object_or_404(Section, pk=section_id)\n")
        body.append(f"    Model = getattr(ma, '{model_name}')\n")
        body.append("    if request.method == 'POST':\n")
        if slug == "competency":
            body.append("        student = _resolve_student(request)\n        if student: compute_competency_progress(student)\n        return redirect('portal:adv_competency')\n")
        elif slug == "ai_feedback":
            body.append("        from apps.grades.models import Grade\n        from apps.extensions.models_advanced import AIFeedbackDraft\n        g = Grade.objects.filter(pk=request.POST.get('grade_id')).first()\n        if g: AIFeedbackDraft.objects.create(grade=g, draft_text=generate_ai_feedback_draft(g))\n        return redirect('portal:adv_ai_feedback')\n")
        elif slug == "section_balance":
            body.append("        term = _school(request).terms.filter(is_current=True).first()\n        if term: balance_sections(term)\n        return redirect('portal:adv_section_balance')\n")
        elif slug == "chronic_absence":
            body.append("        chronic_absenteeism_heatmap(_school(request))\n        return redirect('portal:adv_chronic_absence')\n")
        elif slug == "program_eval":
            body.append("        program_evaluation(_school(request), request.POST.get('program_name', 'AP'))\n        return redirect('portal:adv_program_eval')\n")
        elif slug == "visual_schedule":
            body.append("        term = _school(request).terms.filter(is_current=True).first()\n        if term: ma.VisualScheduleGrid.objects.create(school=_school(request), term=term, grid_data={'cells': []})\n        return redirect('portal:adv_visual_schedule')\n")
        elif slug == "retention":
            body.append("        teacher_retention_snapshot(_school(request))\n        return redirect('portal:adv_retention')\n")
        elif slug == "collab_gradebook":
            body.append("        ma.GradebookCollaborationSession.objects.update_or_create(section=section, defaults={'active_users': [request.user.id]})\n        return redirect('portal:adv_collab_gradebook', section_id=section_id)\n")
        elif slug == "backups":
            body.append("        from apps.extensions.tasks_advanced import run_scheduled_backup\n        if request.user.district_id: run_scheduled_backup.delay(request.user.district_id)\n        return redirect('portal:adv_backups')\n")
        else:
            body.append("        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}\n")
            if param == "section":
                body.append("        fields['section'] = section\n")
            if slug in ("question_bank", "inventory", "maintenance", "events", "safety_tips", "weather_closure", "title_ix", "volunteer_clearance", "union_rules", "multi_tenant", "plugins", "benchmarks", "health", "ab_tests"):
                body.append("        if 'school' not in fields: fields['school'] = _school(request)\n")
            if slug == "weather_closure":
                body.append("        fields['district'] = request.user.district\n")
            if slug in ("leave", "evaluations", "staff_directory", "sub_ratings", "nl_query"):
                body.append("        pass  # use specific fields in production\n")
            body.append("        try:\n            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})\n        except Exception:\n            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})\n")
            if param == "section":
                body.append(f"        return redirect('portal:adv_{slug}', section_id=section_id)\n")
            else:
                body.append(f"        return redirect('portal:adv_{slug}')\n")
        body.append(f"    qs = Model.objects.all()[:50]\n")
        if param == "section":
            body.append("    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs\n")
        body.append(f"    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]\n")
        body.append(f"    cols = [f.name for f in Model._meta.fields[:4]]\n")
        body.append(f"    return _generic(request, '{title}', columns=cols, rows=rows, form_fields=[{{'name': 'notes', 'label': 'Notes / primary field'}}])\n")

out = Path(__file__).resolve().parent.parent / "apps" / "portal" / "advanced_views.py"
out.write_text("".join(body), encoding="utf-8")
print(f"Wrote {out} ({len(body)} parts)")
