"""Advanced portal views (wave 2: features 11-70, no integrations)."""

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


ADVANCED_INDEX = [
    {"title": "Grading depth (11-20)", "features": [
        {"num": 11, "label": "Interactive rubric grader", "url_name": "portal:teacher_sections"},
        {"num": 12, "label": "Peer review", "url_name": "portal:teacher_sections"},
        {"num": 13, "label": "Quiz engine", "url_name": "portal:teacher_sections"},
        {"num": 14, "label": "Question bank", "url_name": "portal:adv_question_bank"},
        {"num": 15, "label": "Exit tickets", "url_name": "portal:teacher_sections"},
        {"num": 16, "label": "Grade appeals", "url_name": "portal:adv_grade_appeals"},
        {"num": 17, "label": "Grade moderation queue", "url_name": "portal:adv_moderation"},
        {"num": 18, "label": "Competency progress", "url_name": "portal:adv_competency"},
        {"num": 19, "label": "Voice feedback", "url_name": "portal:adv_voice_feedback"},
        {"num": 20, "label": "AI feedback drafts", "url_name": "portal:adv_ai_feedback"},
    ]},
    {"title": "Student & family (21-30)", "features": [
        {"num": 21, "label": "Mobile app releases", "url_name": "portal:adv_mobile_apps"},
        {"num": 22, "label": "Weekly parent digest", "url_name": "portal:adv_parent_digest"},
        {"num": 23, "label": "Schedule conflict checker", "url_name": "portal:adv_schedule_conflicts"},
        {"num": 24, "label": "Course registration", "url_name": "portal:adv_course_registration"},
        {"num": 25, "label": "Student hall pass requests", "url_name": "portal:adv_student_hall_pass"},
        {"num": 26, "label": "Safety tip line", "url_name": "portal:adv_safety_tips"},
        {"num": 27, "label": "Multilingual translate cache", "url_name": "portal:adv_translate"},
        {"num": 28, "label": "Conference self-scheduling", "url_name": "portal:adv_conf_self_schedule"},
        {"num": 29, "label": "Document e-signatures", "url_name": "portal:adv_e_signatures"},
        {"num": 30, "label": "Alumni transcript requests", "url_name": "portal:adv_alumni_transcripts"},
    ]},
    {"title": "Scheduling & ops (31-39)", "features": [
        {"num": 31, "label": "Visual schedule builder", "url_name": "portal:adv_visual_schedule"},
        {"num": 32, "label": "Section balancing", "url_name": "portal:adv_section_balance"},
        {"num": 33, "label": "Substitute auto-fill", "url_name": "portal:adv_sub_autofill"},
        {"num": 34, "label": "Inventory tracking", "url_name": "portal:adv_inventory"},
        {"num": 35, "label": "Maintenance tickets", "url_name": "portal:adv_maintenance"},
        {"num": 36, "label": "Events & RSVPs", "url_name": "portal:adv_events"},
        {"num": 37, "label": "Facility use requests", "url_name": "portal:adv_facility_use"},
        {"num": 38, "label": "Lockdown drills", "url_name": "portal:adv_lockdown"},
        {"num": 39, "label": "Weather closure mode", "url_name": "portal:adv_weather_closure"},
    ]},
    {"title": "Health & compliance (40-45)", "features": [
        {"num": 40, "label": "Nurse visit log", "url_name": "portal:adv_nurse_visits"},
        {"num": 41, "label": "Immunization compliance", "url_name": "portal:adv_immunization"},
        {"num": 42, "label": "Seclusion & restraint", "url_name": "portal:adv_seclusion"},
        {"num": 43, "label": "Title IX tracking", "url_name": "portal:adv_title_ix"},
        {"num": 44, "label": "Volunteer clearances", "url_name": "portal:adv_volunteer_clearance"},
        {"num": 45, "label": "COPPA consent", "url_name": "portal:adv_coppa"},
    ]},
    {"title": "Staff & HR (46-50)", "features": [
        {"num": 46, "label": "Staff leave", "url_name": "portal:adv_leave"},
        {"num": 47, "label": "Staff evaluations", "url_name": "portal:adv_evaluations"},
        {"num": 48, "label": "Staff directory", "url_name": "portal:adv_staff_directory"},
        {"num": 49, "label": "Union contract rules", "url_name": "portal:adv_union_rules"},
        {"num": 50, "label": "Substitute ratings", "url_name": "portal:adv_sub_ratings"},
    ]},
    {"title": "Analytics (51-56)", "features": [
        {"num": 51, "label": "Executive dashboard", "url_name": "portal:adv_executive"},
        {"num": 52, "label": "State benchmarks", "url_name": "portal:adv_benchmarks"},
        {"num": 53, "label": "Chronic absenteeism heatmap", "url_name": "portal:adv_chronic_absence"},
        {"num": 54, "label": "Teacher retention", "url_name": "portal:adv_retention"},
        {"num": 55, "label": "Program evaluation", "url_name": "portal:adv_program_eval"},
        {"num": 56, "label": "Natural language queries", "url_name": "portal:adv_nl_query"},
    ]},
    {"title": "Platform (57-64, 66, 69-70)", "features": [
        {"num": 57, "label": "Multi-tenant mode", "url_name": "portal:adv_multi_tenant"},
        {"num": 58, "label": "Plugin marketplace", "url_name": "portal:adv_plugins"},
        {"num": 59, "label": "GraphQL API", "url_name": "portal:adv_graphql"},
        {"num": 60, "label": "Realtime gradebook collab", "url_name": "portal:teacher_sections"},
        {"num": 61, "label": "Automated backups", "url_name": "portal:adv_backups"},
        {"num": 62, "label": "System health dashboard", "url_name": "portal:adv_health"},
        {"num": 63, "label": "Feature flags", "url_name": "portal:adv_feature_flags"},
        {"num": 64, "label": "A/B testing", "url_name": "portal:adv_ab_tests"},
        {"num": 66, "label": "Grade undo", "url_name": "portal:adv_grade_undo"},
        {"num": 69, "label": "Section waitlist", "url_name": "portal:teacher_sections"},
        {"num": 70, "label": "Term archives", "url_name": "portal:adv_term_archive"},
    ]},
    {"title": "Quality of life (65-68)", "features": [
        {"num": 65, "label": "Command palette", "url_name": "portal:adv_command_palette"},
        {"num": 67, "label": "Print-optimized views", "url_name": "portal:adv_print_views"},
        {"num": 68, "label": "Seating charts", "url_name": "portal:teacher_sections"},
    ]},
]


@login_required
def advanced_features_index(request):
    return render(request, "portal/extended/index.html", {
        "groups": ADVANCED_INDEX,
        "page_title": "Advanced features (11–70)",
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



@login_required
def adv_interactive_rubric(request, section_id):
    if not is_feature_enabled("adv_interactive_rubric", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_advanced import RubricGridScore
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

@login_required
def adv_peer_review(request, section_id):
    if not is_feature_enabled("adv_peer_review", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(ma, 'PeerReviewAssignment')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields['section'] = section
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_peer_review', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Peer review', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_quizzes(request, section_id):
    if not is_feature_enabled("adv_quizzes", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(ma, 'Quiz')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields['section'] = section
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_quizzes', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Quiz engine', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_question_bank(request):
    if not is_feature_enabled("adv_question_bank", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'QuestionBankItem')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_question_bank')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Question bank', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_exit_tickets(request, section_id):
    if not is_feature_enabled("adv_exit_tickets", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(ma, 'ExitTicket')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields['section'] = section
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_exit_tickets', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Exit tickets', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_grade_appeals(request):
    if not is_feature_enabled("adv_grade_appeals", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'GradeAppeal')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_grade_appeals')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Grade appeals', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_moderation(request):
    if not is_feature_enabled("adv_moderation", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'GradeModerationItem')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_moderation')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Grade moderation queue', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def adv_competency(request):
    if not is_feature_enabled("adv_competency", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SafetyTip')
    if request.method == 'POST':
        student = _resolve_student(request)
        if student: compute_competency_progress(student)
        return redirect('portal:adv_competency')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Competency progress', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_voice_feedback(request):
    if not is_feature_enabled("adv_voice_feedback", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'VoiceFeedback')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_voice_feedback')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Voice feedback', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def adv_ai_feedback(request):
    if not is_feature_enabled("adv_ai_feedback", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SafetyTip')
    if request.method == 'POST':
        from apps.grades.models import Grade
        from apps.extensions.models_advanced import AIFeedbackDraft
        g = Grade.objects.filter(pk=request.POST.get('grade_id')).first()
        if g: AIFeedbackDraft.objects.create(grade=g, draft_text=generate_ai_feedback_draft(g))
        return redirect('portal:adv_ai_feedback')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'AI feedback drafts', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_mobile_apps(request):
    if not is_feature_enabled("adv_mobile_apps", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'MobileAppRelease')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_mobile_apps')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Mobile app releases', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_parent_digest(request):
    if not is_feature_enabled("adv_parent_digest", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_advanced import ParentDigestPreference
    pref, _ = ParentDigestPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        pref.enabled = request.POST.get("enabled") == "on"
        pref.save()
        return redirect("portal:adv_parent_digest")
    return _generic(request, "Weekly parent email digest", description=f"Digest {'enabled' if pref.enabled else 'disabled'}. Runs via Celery every week.",
        form_fields=[{"name": "enabled", "label": "Enable weekly digest", "type": "checkbox", "checked": pref.enabled}])

@login_required
@require_http_methods(['GET', 'POST'])
def adv_schedule_conflicts(request):
    if not is_feature_enabled("adv_schedule_conflicts", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    student = _resolve_student(request)
    if not student:
        return HttpResponseForbidden()
    conflicts = schedule_conflicts(student)
    rows = [[c["period"], c["course_a"], c["course_b"]] for c in conflicts]
    return _generic(request, f"Schedule conflicts — {student.full_name}", columns=["Period", "Course A", "Course B"], rows=rows)

@login_required
def adv_course_registration(request):
    if not is_feature_enabled("adv_course_registration", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'CourseRegistrationRequest')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_course_registration')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Course registration', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_student_hall_pass(request):
    if not is_feature_enabled("adv_student_hall_pass", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'StudentHallPassRequest')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_student_hall_pass')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Student hall pass requests', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_safety_tips(request):
    if not is_feature_enabled("adv_safety_tips", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SafetyTip')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_safety_tips')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Safety tip line', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_translate(request):
    if not is_feature_enabled("adv_translate", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'TranslatedContent')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_translate')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Multilingual translate cache', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_conf_self_schedule(request):
    if not is_feature_enabled("adv_conf_self_schedule", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'ConferenceSelfScheduleSlot')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_conf_self_schedule')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Conference self-scheduling', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_e_signatures(request):
    if not is_feature_enabled("adv_e_signatures", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'DocumentSignatureRequest')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_e_signatures')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Document e-signatures', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_alumni_transcripts(request):
    if not is_feature_enabled("adv_alumni_transcripts", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'AlumniTranscriptRequest')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_alumni_transcripts')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Alumni transcript requests', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def adv_visual_schedule(request):
    if not is_feature_enabled("adv_visual_schedule", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'VisualScheduleGrid')
    if request.method == 'POST':
        term = _school(request).terms.filter(is_current=True).first()
        if term: ma.VisualScheduleGrid.objects.create(school=_school(request), term=term, grid_data={'cells': []})
        return redirect('portal:adv_visual_schedule')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Visual schedule builder', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def adv_section_balance(request):
    if not is_feature_enabled("adv_section_balance", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SafetyTip')
    if request.method == 'POST':
        term = _school(request).terms.filter(is_current=True).first()
        if term: balance_sections(term)
        return redirect('portal:adv_section_balance')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Section balancing', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_sub_autofill(request):
    if not is_feature_enabled("adv_sub_autofill", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SubstituteAutoAssignment')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_sub_autofill')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Substitute auto-fill', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_inventory(request):
    if not is_feature_enabled("adv_inventory", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'AssetItem')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_inventory')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Inventory tracking', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_maintenance(request):
    if not is_feature_enabled("adv_maintenance", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'MaintenanceTicket')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_maintenance')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Maintenance tickets', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_events(request):
    if not is_feature_enabled("adv_events", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SchoolEvent')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_events')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Events & RSVPs', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_facility_use(request):
    if not is_feature_enabled("adv_facility_use", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'FacilityUseRequest')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_facility_use')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Facility use requests', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_lockdown(request):
    if not is_feature_enabled("adv_lockdown", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'LockdownDrill')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_lockdown')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Lockdown drills', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_weather_closure(request):
    if not is_feature_enabled("adv_weather_closure", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'WeatherClosureMode')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_weather_closure')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Weather closure mode', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_nurse_visits(request):
    if not is_feature_enabled("adv_nurse_visits", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'NurseVisit')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_nurse_visits')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Nurse visit log', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_immunization(request):
    if not is_feature_enabled("adv_immunization", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'ImmunizationComplianceFlag')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_immunization')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Immunization compliance', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_seclusion(request):
    if not is_feature_enabled("adv_seclusion", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SeclusionRestraintIncident')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_seclusion')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Seclusion & restraint', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_title_ix(request):
    if not is_feature_enabled("adv_title_ix", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'TitleIXCase')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_title_ix')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Title IX tracking', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_volunteer_clearance(request):
    if not is_feature_enabled("adv_volunteer_clearance", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'VolunteerClearance')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_volunteer_clearance')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Volunteer clearances', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_coppa(request):
    if not is_feature_enabled("adv_coppa", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'COPPAConsentRecord')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_coppa')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'COPPA consent', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_leave(request):
    if not is_feature_enabled("adv_leave", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'StaffLeaveRequest')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        pass  # use specific fields in production
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_leave')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Staff leave', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_evaluations(request):
    if not is_feature_enabled("adv_evaluations", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'StaffEvaluation')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        pass  # use specific fields in production
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_evaluations')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Staff evaluations', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_staff_directory(request):
    if not is_feature_enabled("adv_staff_directory", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'StaffDirectoryEntry')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        pass  # use specific fields in production
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_staff_directory')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Staff directory', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_union_rules(request):
    if not is_feature_enabled("adv_union_rules", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'UnionContractRule')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_union_rules')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Union contract rules', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_sub_ratings(request):
    if not is_feature_enabled("adv_sub_ratings", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SubstituteRating')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        pass  # use specific fields in production
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_sub_ratings')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Substitute ratings', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def adv_executive(request):
    if not is_feature_enabled("adv_executive", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    snap = executive_dashboard(request.user.district) if request.method == "POST" else None
    from apps.extensions.models_advanced import ExecutiveDashboardSnapshot
    latest = ExecutiveDashboardSnapshot.objects.filter(district=request.user.district).first()
    rows = [[k, v] for k, v in (latest.metrics.items() if latest else [])]
    return _generic(request, "Executive dashboard", rows=rows, columns=["Metric", "Value"], submit_label="Refresh snapshot")

@login_required
def adv_benchmarks(request):
    if not is_feature_enabled("adv_benchmarks", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'StateBenchmark')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_benchmarks')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'State benchmarks', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def adv_chronic_absence(request):
    if not is_feature_enabled("adv_chronic_absence", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SafetyTip')
    if request.method == 'POST':
        chronic_absenteeism_heatmap(_school(request))
        return redirect('portal:adv_chronic_absence')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Chronic absenteeism heatmap', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_retention(request):
    if not is_feature_enabled("adv_retention", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'TeacherRetentionMetric')
    if request.method == 'POST':
        teacher_retention_snapshot(_school(request))
        return redirect('portal:adv_retention')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Teacher retention', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def adv_program_eval(request):
    if not is_feature_enabled("adv_program_eval", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SafetyTip')
    if request.method == 'POST':
        program_evaluation(_school(request), request.POST.get('program_name', 'AP'))
        return redirect('portal:adv_program_eval')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Program evaluation', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def adv_nl_query(request):
    if not is_feature_enabled("adv_nl_query", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    result = None
    if request.method == "POST":
        result = natural_language_query(request.user, request.POST.get("query", ""))
    rows = [[r.get("student", r)] if isinstance(r, dict) else [r] for r in (result or {}).get("rows", [])[:30]]
    return _generic(request, "Natural language queries", form_fields=[{"name": "query", "label": "Ask in plain English", "type": "textarea", "required": True}], rows=rows, columns=["Result"])

@login_required
def adv_multi_tenant(request):
    if not is_feature_enabled("adv_multi_tenant", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'TenantOrganization')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_multi_tenant')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Multi-tenant mode', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_plugins(request):
    if not is_feature_enabled("adv_plugins", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'PluginModule')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_plugins')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Plugin marketplace', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_graphql(request):
    if not is_feature_enabled("adv_graphql", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SafetyTip')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_graphql')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'GraphQL API', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_collab_gradebook(request, section_id):
    if not is_feature_enabled("adv_collab_gradebook", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(ma, 'GradebookCollaborationSession')
    if request.method == 'POST':
        ma.GradebookCollaborationSession.objects.update_or_create(section=section, defaults={'active_users': [request.user.id]})
        return redirect('portal:adv_collab_gradebook', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Realtime gradebook collab', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_backups(request):
    if not is_feature_enabled("adv_backups", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'BackupJob')
    if request.method == 'POST':
        from apps.extensions.tasks_advanced import run_scheduled_backup
        if request.user.district_id: run_scheduled_backup.delay(request.user.district_id)
        return redirect('portal:adv_backups')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Automated backups', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_health(request):
    if not is_feature_enabled("adv_health", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'SystemHealthMetric')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_health')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'System health dashboard', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_feature_flags(request):
    if not is_feature_enabled("adv_feature_flags", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_advanced import FeatureFlag
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    if request.method == "POST":
        FeatureFlag.objects.get_or_create(key=request.POST.get("key", "demo"), defaults={"name": request.POST.get("name", "Demo feature")})
        return redirect("portal:adv_feature_flags")
    rows = [[f.key, f.name, f.enabled_globally] for f in FeatureFlag.objects.all()]
    return _generic(request, "Feature flags", columns=["Key", "Name", "Global"], rows=rows, form_fields=[{"name": "key", "label": "Key"}, {"name": "name", "label": "Name"}])

@login_required
def adv_ab_tests(request):
    if not is_feature_enabled("adv_ab_tests", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'ABTestVariant')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if 'school' not in fields: fields['school'] = _school(request)
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_ab_tests')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'A/B testing', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_command_palette(request):
    if not is_feature_enabled("adv_command_palette", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    return _generic(request, "Command palette", description="Press Ctrl+K anywhere in the portal to open the command palette.")

@login_required
def adv_grade_undo(request):
    if not is_feature_enabled("adv_grade_undo", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    return _generic(request, "Grade undo", description="After saving a grade, press Ctrl+Z within 30 seconds or use the gradebook undo button.")

@login_required
def adv_print_views(request):
    if not is_feature_enabled("adv_print_views", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    student = _resolve_student(request)
    grades = []
    if student:
        from apps.grades.services import grades_visible_to_student
        from apps.grades.models import Grade
        grades = grades_visible_to_student(Grade.objects.filter(student=student).select_related("assignment__section__course")[:50])
    return render(request, "portal/advanced/print_grades.html", {"student": student, "grades": grades})

@login_required
@require_http_methods(['GET', 'POST'])
def adv_seating(request, section_id):
    if not is_feature_enabled("adv_seating", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_advanced import SeatingChart
    section = get_object_or_404(Section, pk=section_id)
    if request.method == "POST":
        layout = seating_chart_random(section)
        SeatingChart.objects.update_or_create(section=section, name="Default", defaults={"layout": layout})
        return redirect("portal:adv_seating", section_id=section_id)
    chart = SeatingChart.objects.filter(section=section).first()
    rows = [[sid, info.get("name"), info.get("row"), info.get("col")] for sid, info in (chart.layout.items() if chart else [])]
    return _generic(request, f"Seating chart — {section.course.code}", columns=["ID", "Student", "Row", "Col"], rows=rows, submit_label="Generate random layout")

@login_required
def adv_waitlist(request, section_id):
    if not is_feature_enabled("adv_waitlist", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(ma, 'SectionWaitlist')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields['section'] = section
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_waitlist', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Section waitlist', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def adv_term_archive(request):
    if not is_feature_enabled("adv_term_archive", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_advanced as ma
    Model = getattr(ma, 'TermArchive')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: v for k, v in fields.items() if hasattr(Model, k)})
        except Exception:
            Model.objects.create(**{k: fields[k] for k in list(fields)[:3] if hasattr(Model, k)})
        return redirect('portal:adv_term_archive')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Term archives', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])
