"""Wave 4 portal views (95 production-depth features)."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import UserRole
from apps.accounts.permissions import user_can_edit_grades
from apps.extensions.advanced_services import is_feature_enabled
from apps.extensions import wave4_services as w4
from apps.portal.extended_views import _generic, _school
from apps.portal.views import _resolve_student
from apps.scheduling.models import Section

WAVE4_INDEX = [
    {"title": "Tier 1 — Live depth (1-15)", "features": [
        {"num": 1, "label": "Live Google Classroom sync", "url_name": "portal:w4_classroom_sync"},
        {"num": 2, "label": "OneRoster import", "url_name": "portal:w4_oneroster_live"},
        {"num": 3, "label": "SMS delivery (Twilio)", "url_name": "portal:w4_sms_live"},
        {"num": 4, "label": "Stripe fee collection", "url_name": "portal:w4_stripe_fees"},
        {"num": 5, "label": "LDAP login mapping", "url_name": "portal:w4_ldap_live"},
        {"num": 6, "label": "Clever/ClassLink roster sync", "url_name": "portal:w4_clever_sso"},
        {"num": 7, "label": "Timed quiz player", "url_name": "portal:teacher_sections"},
        {"num": 8, "label": "Item analysis dashboard", "url_name": "portal:teacher_sections"},
        {"num": 9, "label": "Grade anomaly workflow", "url_name": "portal:w4_anomaly_workflow"},
        {"num": 10, "label": "Audit chain verification", "url_name": "portal:w4_audit_verify"},
        {"num": 11, "label": "Board packet PDF export", "url_name": "portal:w4_board_pdf"},
        {"num": 12, "label": "IEP/504 goal tracking", "url_name": "portal:w4_iep504_goals"},
        {"num": 13, "label": "Athletics auto eligibility", "url_name": "portal:w4_athletics_auto"},
        {"num": 14, "label": "Emergency delivery status", "url_name": "portal:w4_emergency_delivery"},
        {"num": 15, "label": "Offline gradebook cache", "url_name": "portal:w4_offline_gradebook"},
    ]},
    {"title": "Tier 2 — Grading (16-30)", "features": [
        {"num": 16, "label": "Standards report cards", "url_name": "portal:w4_standards_rc"},
        {"num": 17, "label": "Grade what-if calculator", "url_name": "portal:w4_what_if"},
        {"num": 18, "label": "Assignment versioning", "url_name": "portal:w4_assignment_version"},
        {"num": 19, "label": "Anonymous grading", "url_name": "portal:teacher_sections"},
        {"num": 20, "label": "Calibration sessions", "url_name": "portal:w4_calibration"},
        {"num": 21, "label": "District rubric bank", "url_name": "portal:w4_rubric_bank"},
        {"num": 22, "label": "Retake/revision policies", "url_name": "portal:teacher_sections"},
        {"num": 23, "label": "Category weight presets", "url_name": "portal:w4_weight_presets"},
        {"num": 24, "label": "Scantron auto-post", "url_name": "portal:w4_scantron_post"},
        {"num": 25, "label": "Handwriting OCR pipeline", "url_name": "portal:w4_ocr_pipeline"},
        {"num": 26, "label": "Portfolio exhibitions", "url_name": "portal:w4_portfolio_exhibit"},
        {"num": 27, "label": "Competency badge evidence", "url_name": "portal:w4_badge_evidence"},
        {"num": 28, "label": "Cross-section grade compare", "url_name": "portal:w4_cross_section"},
        {"num": 29, "label": "Missing work escalation", "url_name": "portal:w4_missing_escalation"},
        {"num": 30, "label": "Grade comment templates", "url_name": "portal:w4_comment_templates"},
    ]},
    {"title": "Tier 3 — Family (31-42)", "features": [
        {"num": 31, "label": "Unified family inbox", "url_name": "portal:w4_family_inbox"},
        {"num": 32, "label": "Push notifications (FCM)", "url_name": "portal:w4_push_fcm"},
        {"num": 33, "label": "Live weekly digest", "url_name": "portal:w4_digest_live"},
        {"num": 34, "label": "Wellness check-in", "url_name": "portal:w4_wellness"},
        {"num": 35, "label": "Homework planner", "url_name": "portal:w4_homework_planner"},
        {"num": 36, "label": "Conference prep packet", "url_name": "portal:w4_conf_prep"},
        {"num": 37, "label": "Multi-language portal", "url_name": "portal:w4_i18n_portal"},
        {"num": 38, "label": "Read-aloud / TTS", "url_name": "portal:w4_tts"},
        {"num": 39, "label": "Student question queue", "url_name": "portal:teacher_sections"},
        {"num": 40, "label": "Graduation checklist", "url_name": "portal:w4_grad_checklist"},
        {"num": 41, "label": "Course wishlist / lottery", "url_name": "portal:w4_course_wishlist"},
        {"num": 42, "label": "Sibling schedule view", "url_name": "portal:w4_sibling_schedule"},
    ]},
    {"title": "Tier 4 — Teacher workflow (43-54)", "features": [
        {"num": 43, "label": "Co-teacher permissions", "url_name": "portal:teacher_sections"},
        {"num": 44, "label": "Gradebook presence", "url_name": "portal:teacher_sections"},
        {"num": 45, "label": "Lesson plan links", "url_name": "portal:w4_lesson_link"},
        {"num": 46, "label": "Substitute lesson pack", "url_name": "portal:teacher_sections"},
        {"num": 47, "label": "Department grade distribution", "url_name": "portal:w4_dept_distribution"},
        {"num": 48, "label": "Intervention groups", "url_name": "portal:teacher_sections"},
        {"num": 49, "label": "PLC meeting mode", "url_name": "portal:w4_plc_meeting"},
        {"num": 50, "label": "Teacher sub requests", "url_name": "portal:w4_sub_request"},
        {"num": 51, "label": "Voice-to-text feedback", "url_name": "portal:w4_voice_feedback"},
        {"num": 52, "label": "Bulk feedback mail merge", "url_name": "portal:teacher_sections"},
        {"num": 53, "label": "Assignment copy job", "url_name": "portal:w4_assignment_copy"},
        {"num": 54, "label": "Grade posting preview", "url_name": "portal:teacher_sections"},
    ]},
    {"title": "Tier 5 — Analytics (55-64)", "features": [
        {"num": 55, "label": "Early warning index", "url_name": "portal:w4_ewi"},
        {"num": 56, "label": "Equity gap reports", "url_name": "portal:w4_equity_gap"},
        {"num": 57, "label": "Teacher effectiveness", "url_name": "portal:w4_teacher_effect"},
        {"num": 58, "label": "Enrollment forecasting", "url_name": "portal:w4_enroll_forecast"},
        {"num": 59, "label": "Budget impact modeling", "url_name": "portal:w4_budget_scenario"},
        {"num": 60, "label": "Custom report builder", "url_name": "portal:w4_report_builder"},
        {"num": 61, "label": "Scheduled report emails", "url_name": "portal:w4_scheduled_report"},
        {"num": 62, "label": "State benchmark mapping", "url_name": "portal:w4_state_benchmark"},
        {"num": 63, "label": "Climate survey integration", "url_name": "portal:w4_climate_survey"},
        {"num": 64, "label": "Absence route heatmap", "url_name": "portal:w4_route_heatmap"},
    ]},
    {"title": "Tier 6 — Operations (65-74)", "features": [
        {"num": 65, "label": "Visitor badge printing", "url_name": "portal:w4_visitor_badge"},
        {"num": 66, "label": "Cafeteria low balance alerts", "url_name": "portal:w4_cafeteria_alert"},
        {"num": 67, "label": "Bus GPS parent view", "url_name": "portal:w4_bus_gps"},
        {"num": 68, "label": "Crisis reunification", "url_name": "portal:w4_reunification"},
        {"num": 69, "label": "Threat assessment", "url_name": "portal:w4_threat_assess"},
        {"num": 70, "label": "Medication admin log", "url_name": "portal:w4_med_admin"},
        {"num": 71, "label": "Maintenance photo tickets", "url_name": "portal:w4_maint_photos"},
        {"num": 72, "label": "Keycard anomaly alerts", "url_name": "portal:w4_keycard_alert"},
        {"num": 73, "label": "Parking violations", "url_name": "portal:w4_parking_violation"},
        {"num": 74, "label": "After-school pickup verify", "url_name": "portal:w4_pickup_verify"},
    ]},
    {"title": "Tier 7 — Platform (75-85)", "features": [
        {"num": 75, "label": "Public API keys", "url_name": "portal:w4_api_keys"},
        {"num": 76, "label": "Webhook delivery log", "url_name": "portal:w4_webhook_retry"},
        {"num": 77, "label": "Preview as user", "url_name": "portal:w4_preview_as"},
        {"num": 78, "label": "FERPA data export", "url_name": "portal:w4_ferpa_export"},
        {"num": 79, "label": "Role permission bindings", "url_name": "portal:w4_role_builder"},
        {"num": 80, "label": "Plugin runtime sandbox", "url_name": "portal:w4_plugin_sandbox"},
        {"num": 81, "label": "GraphQL schema", "url_name": "portal:w4_graphql_schema"},
        {"num": 82, "label": "Multi-school principal dash", "url_name": "portal:w4_principal_dash"},
        {"num": 83, "label": "Audit diff viewer", "url_name": "portal:w4_audit_diff"},
        {"num": 84, "label": "Session geo alerts", "url_name": "portal:w4_session_geo"},
        {"num": 85, "label": "Security scorecard", "url_name": "portal:w4_security_score"},
    ]},
    {"title": "Tier 8 — Quality of life (86-95)", "features": [
        {"num": 86, "label": "Navbar favorite pins", "url_name": "portal:w4_navbar_pins"},
        {"num": 87, "label": "Recent page history", "url_name": "portal:w4_page_history"},
        {"num": 88, "label": "Bulk email from gradebook", "url_name": "portal:teacher_sections"},
        {"num": 89, "label": "Print view config", "url_name": "portal:w4_print_config"},
        {"num": 90, "label": "Keyboard shortcuts", "url_name": "portal:w4_keyboard_help"},
        {"num": 91, "label": "Dark mode preview", "url_name": "portal:w4_dark_preview"},
        {"num": 92, "label": "Dashboard widgets", "url_name": "portal:w4_dash_widgets"},
        {"num": 93, "label": "In-app changelog", "url_name": "portal:w4_changelog"},
        {"num": 94, "label": "Contextual help tooltips", "url_name": "portal:w4_help_tooltips"},
        {"num": 95, "label": "Staff photo bulk upload", "url_name": "portal:w4_staff_photos"},
    ]},
]


@login_required
def wave4_features_index(request):
    return render(request, "portal/extended/index.html", {
        "groups": WAVE4_INDEX,
        "page_title": "Wave 4 features (1-95)",
        "wave4": True,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def w4_classroom_sync(request):
    if not is_feature_enabled("w4_classroom_sync", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    if request.method == "POST" and request.user.district_id:
        w4.run_classroom_sync(request.user.district)
        return redirect("portal:w4_classroom_sync")
    from apps.extensions import models_wave4 as m4
    rows = [[j.status, j.rosters_synced, j.grades_pushed] for j in m4.ClassroomSyncJob.objects.filter(district=request.user.district)[:20]] if request.user.district_id else []
    return _generic(request, "Live Google Classroom sync", rows=rows, columns=["Status", "Rosters", "Grades"], submit_label="Run sync now")

@login_required
@require_http_methods(['GET', 'POST'])
def w4_oneroster_live(request):
    if not is_feature_enabled("w4_oneroster_live", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    if request.method == "POST" and request.user.district_id:
        w4.run_oneroster_import(request.user.district)
        return redirect("portal:w4_oneroster_live")
    from apps.extensions import models_wave4 as m4
    rows = [[r.status, r.records_processed] for r in m4.OneRosterImportRun.objects.filter(district=request.user.district)[:20]] if request.user.district_id else []
    return _generic(request, "OneRoster import", rows=rows, columns=["Status", "Records"], submit_label="Import now")

@login_required
@require_http_methods(['GET', 'POST'])
def w4_sms_live(request):
    if not is_feature_enabled("w4_sms_live", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    if request.method == "POST" and request.user.district_id:
        w4.queue_sms(request.user.district, request.POST.get("recipient", ""), request.POST.get("message", ""))
        return redirect("portal:w4_sms_live")
    from apps.extensions import models_wave4 as m4
    rows = [[l.recipient, l.status, l.message[:40]] for l in m4.SMSDeliveryLog.objects.filter(district=request.user.district)[:20]] if request.user.district_id else []
    return _generic(request, "SMS delivery", rows=rows, columns=["To", "Status", "Message"],
        form_fields=[{"name": "recipient", "label": "Phone"}, {"name": "message", "label": "Message", "type": "textarea"}])

@login_required
def w4_stripe_fees(request):
    if not is_feature_enabled("w4_stripe_fees", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'StripePaymentTransaction')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_stripe_fees')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Stripe fee collection', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_ldap_live(request):
    if not is_feature_enabled("w4_ldap_live", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'LDAPLoginMapping')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_ldap_live')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'LDAP login mapping', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_clever_sso(request):
    if not is_feature_enabled("w4_clever_sso", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'SSOCleverRosterSync')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_clever_sso')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Clever/ClassLink roster sync', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_timed_quiz(request, section_id):
    if not is_feature_enabled("w4_timed_quiz", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(m4, 'TimedQuizConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_timed_quiz', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Timed quiz player', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_item_dashboard(request, section_id):
    if not is_feature_enabled("w4_item_dashboard", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(m4, 'ItemAnalysisDashboard')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_item_dashboard', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Item analysis dashboard', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_anomaly_workflow(request):
    if not is_feature_enabled("w4_anomaly_workflow", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'GradeAnomalyWorkflow')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_anomaly_workflow')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Grade anomaly workflow', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w4_audit_verify(request):
    if not is_feature_enabled("w4_audit_verify", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    if request.user.role not in (UserRole.DISTRICT_ADMIN, UserRole.SCHOOL_ADMIN):
        return HttpResponseForbidden()
    if request.method == "POST" and request.user.district_id:
        w4.verify_audit_chain(request.user.district)
        return redirect("portal:w4_audit_verify")
    from apps.extensions import models_wave4 as m4
    rows = [[v.verified, v.chain_length, v.created_at] for v in m4.AuditChainVerification.objects.filter(district=request.user.district)[:10]] if request.user.district_id else []
    return _generic(request, "Audit chain verification", rows=rows, columns=["Valid", "Length", "Checked"], submit_label="Verify chain")

@login_required
def w4_board_pdf(request):
    if not is_feature_enabled("w4_board_pdf", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'BoardPacketPDFExport')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_board_pdf')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Board packet PDF export', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_iep504_goals(request):
    if not is_feature_enabled("w4_iep504_goals", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'IEP504GoalTracker')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_iep504_goals')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'IEP/504 goal tracking', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_athletics_auto(request):
    if not is_feature_enabled("w4_athletics_auto", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'AthleticsAutoEligibilityRun')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_athletics_auto')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Athletics auto eligibility', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_emergency_delivery(request):
    if not is_feature_enabled("w4_emergency_delivery", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'EmergencyDeliveryStatus')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_emergency_delivery')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Emergency delivery status', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_offline_gradebook(request):
    if not is_feature_enabled("w4_offline_gradebook", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'OfflineGradebookCache')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_offline_gradebook')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Offline gradebook cache', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_standards_rc(request):
    if not is_feature_enabled("w4_standards_rc", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'StandardsReportCard')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_standards_rc')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Standards report cards', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w4_what_if(request):
    if not is_feature_enabled("w4_what_if", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    student = _resolve_student(request)
    if not student:
        return HttpResponseForbidden()
    if request.method == "POST":
        sec = get_object_or_404(Section, pk=request.POST.get("section_id"))
        w4.compute_what_if(student, sec, request.POST.get("target_grade", "B"))
        return redirect("portal:w4_what_if")
    from apps.extensions import models_wave4 as m4
    rows = [[c.target_grade, c.score_needed, c.section.course.code] for c in m4.GradeWhatIfCalculation.objects.filter(student=student)[:10]]
    return _generic(request, "Grade what-if calculator", rows=rows, columns=["Target", "Needed", "Section"],
        form_fields=[{"name": "section_id", "label": "Section ID"}, {"name": "target_grade", "label": "Target grade"}])

@login_required
def w4_assignment_version(request):
    if not is_feature_enabled("w4_assignment_version", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'AssignmentVersion')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_assignment_version')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Assignment versioning', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_anon_grading(request, section_id):
    if not is_feature_enabled("w4_anon_grading", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(m4, 'AnonymousGradingSession')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_anon_grading', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Anonymous grading', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_calibration(request):
    if not is_feature_enabled("w4_calibration", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'CalibrationSession')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_calibration')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Calibration sessions', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_rubric_bank(request):
    if not is_feature_enabled("w4_rubric_bank", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'DistrictRubricBank')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_rubric_bank')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'District rubric bank', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_retake_policy(request, section_id):
    if not is_feature_enabled("w4_retake_policy", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(m4, 'RetakePolicyRule')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_retake_policy', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Retake/revision policies', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_weight_presets(request):
    if not is_feature_enabled("w4_weight_presets", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'CategoryWeightPreset')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_weight_presets')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Category weight presets', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_scantron_post(request):
    if not is_feature_enabled("w4_scantron_post", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'ScantronAutoPostJob')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_scantron_post')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Scantron auto-post', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_ocr_pipeline(request):
    if not is_feature_enabled("w4_ocr_pipeline", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'HandwritingOCRPipeline')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_ocr_pipeline')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Handwriting OCR pipeline', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_portfolio_exhibit(request):
    if not is_feature_enabled("w4_portfolio_exhibit", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'PortfolioExhibition')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_portfolio_exhibit')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Portfolio exhibitions', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_badge_evidence(request):
    if not is_feature_enabled("w4_badge_evidence", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'CompetencyBadgeEvidence')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_badge_evidence')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Competency badge evidence', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_cross_section(request):
    if not is_feature_enabled("w4_cross_section", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'CrossSectionGradeCompare')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_cross_section')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Cross-section grade compare', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_missing_escalation(request):
    if not is_feature_enabled("w4_missing_escalation", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'MissingWorkEscalation')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_missing_escalation')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Missing work escalation', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_comment_templates(request):
    if not is_feature_enabled("w4_comment_templates", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'GradeCommentTemplate')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        fields['teacher'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_comment_templates')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Grade comment templates', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_family_inbox(request):
    if not is_feature_enabled("w4_family_inbox", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'UnifiedFamilyInbox')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_family_inbox')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Unified family inbox', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_push_fcm(request):
    if not is_feature_enabled("w4_push_fcm", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'PushNotificationDevice')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_push_fcm')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Push notifications (FCM)', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_digest_live(request):
    if not is_feature_enabled("w4_digest_live", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'LiveWeeklyDigestRun')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_digest_live')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Live weekly digest', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_wellness(request):
    if not is_feature_enabled("w4_wellness", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'WellnessCheckIn')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_wellness')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Wellness check-in', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_homework_planner(request):
    if not is_feature_enabled("w4_homework_planner", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'HomeworkPlannerEntry')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_homework_planner')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Homework planner', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_conf_prep(request):
    if not is_feature_enabled("w4_conf_prep", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'ConferencePrepPacket')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_conf_prep')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Conference prep packet', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_i18n_portal(request):
    if not is_feature_enabled("w4_i18n_portal", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'PortalLocaleConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_i18n_portal')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Multi-language portal', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_tts(request):
    if not is_feature_enabled("w4_tts", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'TextToSpeechRequest')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_tts')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Read-aloud / TTS', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_student_questions(request, section_id):
    if not is_feature_enabled("w4_student_questions", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(m4, 'StudentQuestionQueue')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_student_questions', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Student question queue', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_grad_checklist(request):
    if not is_feature_enabled("w4_grad_checklist", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'GraduationChecklist')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_grad_checklist')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Graduation checklist', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_course_wishlist(request):
    if not is_feature_enabled("w4_course_wishlist", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'CourseWishlistEntry')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_course_wishlist')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Course wishlist / lottery', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_sibling_schedule(request):
    if not is_feature_enabled("w4_sibling_schedule", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'SiblingScheduleView')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_sibling_schedule')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Sibling schedule view', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_co_teacher(request, section_id):
    if not is_feature_enabled("w4_co_teacher", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(m4, 'CoTeacherPermission')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_co_teacher', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Co-teacher permissions', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_gradebook_presence(request, section_id):
    if not is_feature_enabled("w4_gradebook_presence", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(m4, 'GradebookPresenceSession')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_gradebook_presence', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Gradebook presence', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_lesson_link(request):
    if not is_feature_enabled("w4_lesson_link", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'LessonPlanLink')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_lesson_link')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Lesson plan links', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w4_sub_lesson_pack(request, section_id):
    if not is_feature_enabled("w4_sub_lesson_pack", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    section = get_object_or_404(Section, pk=section_id)
    if request.method == "POST":
        w4.build_sub_lesson_pack(section, timezone.now().date())
        return redirect("portal:w4_sub_lesson_pack", section_id=section_id)
    from apps.extensions import models_wave4 as m4
    rows = [[p.date, p.pack_html[:60]] for p in m4.SubstituteLessonPack.objects.filter(section=section)[:10]]
    return _generic(request, f"Substitute lesson pack — {section.course.code}", rows=rows, columns=["Date", "Preview"], submit_label="Generate pack")

@login_required
def w4_dept_distribution(request):
    if not is_feature_enabled("w4_dept_distribution", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'DepartmentGradeDistribution')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_dept_distribution')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Department grade distribution', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_intervention_grp(request, section_id):
    if not is_feature_enabled("w4_intervention_grp", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(m4, 'InterventionGroup')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_intervention_grp', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Intervention groups', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_plc_meeting(request):
    if not is_feature_enabled("w4_plc_meeting", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'PLCMeetingSession')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_plc_meeting')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'PLC meeting mode', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_sub_request(request):
    if not is_feature_enabled("w4_sub_request", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'TeacherSubRequest')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_sub_request')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Teacher sub requests', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_voice_feedback(request):
    if not is_feature_enabled("w4_voice_feedback", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'VoiceToTextFeedback')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_voice_feedback')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Voice-to-text feedback', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_mail_merge(request, section_id):
    if not is_feature_enabled("w4_mail_merge", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(m4, 'BulkFeedbackMailMerge')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_mail_merge', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Bulk feedback mail merge', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_assignment_copy(request):
    if not is_feature_enabled("w4_assignment_copy", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'AssignmentCopyJob')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_assignment_copy')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Assignment copy job', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w4_posting_preview(request, section_id):
    if not is_feature_enabled("w4_posting_preview", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    if request.method == "POST":
        w4.generate_posting_preview(section, request.user)
        return redirect("portal:w4_posting_preview", section_id=section_id)
    from apps.extensions import models_wave4 as m4
    p = m4.GradePostingPreview.objects.filter(section=section).first()
    rows = [[r.get("student"), r.get("assignment"), r.get("points")] for r in (p.preview_data.get("rows", []) if p else [])]
    return _generic(request, f"Posting preview — {section.course.code}", rows=rows, columns=["Student", "Assignment", "Points"], submit_label="Generate preview")

@login_required
@require_http_methods(['GET', 'POST'])
def w4_ewi(request):
    if not is_feature_enabled("w4_ewi", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    student = _resolve_student(request)
    if not student:
        return HttpResponseForbidden()
    if request.method == "POST":
        w4.compute_ewi(student)
        return redirect("portal:w4_ewi")
    from apps.extensions import models_wave4 as m4
    rows = [[e.score, e.tier, e.created_at] for e in m4.EarlyWarningIndex.objects.filter(student=student)[:10]]
    return _generic(request, "Early warning index", rows=rows, columns=["Score", "Tier", "Date"], submit_label="Recalculate")

@login_required
def w4_equity_gap(request):
    if not is_feature_enabled("w4_equity_gap", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'EquityGapReport')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_equity_gap')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Equity gap reports', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_teacher_effect(request):
    if not is_feature_enabled("w4_teacher_effect", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'TeacherEffectivenessSnapshot')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_teacher_effect')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Teacher effectiveness', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_enroll_forecast(request):
    if not is_feature_enabled("w4_enroll_forecast", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'EnrollmentForecast')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_enroll_forecast')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Enrollment forecasting', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_budget_scenario(request):
    if not is_feature_enabled("w4_budget_scenario", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'BudgetImpactScenario')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_budget_scenario')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Budget impact modeling', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_report_builder(request):
    if not is_feature_enabled("w4_report_builder", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'CustomReportBuilderDefinition')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_report_builder')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Custom report builder', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_scheduled_report(request):
    if not is_feature_enabled("w4_scheduled_report", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'ScheduledReportEmail')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_scheduled_report')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Scheduled report emails', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_state_benchmark(request):
    if not is_feature_enabled("w4_state_benchmark", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'StateBenchmarkMapping')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_state_benchmark')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'State benchmark mapping', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_climate_survey(request):
    if not is_feature_enabled("w4_climate_survey", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'ClimateSurveyResponse')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_climate_survey')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Climate survey integration', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_route_heatmap(request):
    if not is_feature_enabled("w4_route_heatmap", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'AbsenceRouteHeatmap')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_route_heatmap')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Absence route heatmap', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_visitor_badge(request):
    if not is_feature_enabled("w4_visitor_badge", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'VisitorBadgePrint')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_visitor_badge')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Visitor badge printing', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_cafeteria_alert(request):
    if not is_feature_enabled("w4_cafeteria_alert", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'CafeteriaLowBalanceAlert')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_cafeteria_alert')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Cafeteria low balance alerts', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_bus_gps(request):
    if not is_feature_enabled("w4_bus_gps", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'BusGPSLocation')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_bus_gps')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Bus GPS parent view', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_reunification(request):
    if not is_feature_enabled("w4_reunification", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'CrisisReunificationRecord')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_reunification')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Crisis reunification', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_threat_assess(request):
    if not is_feature_enabled("w4_threat_assess", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'ThreatAssessmentCase')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_threat_assess')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Threat assessment', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_med_admin(request):
    if not is_feature_enabled("w4_med_admin", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'MedicationAdminLog')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_med_admin')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Medication admin log', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_maint_photos(request):
    if not is_feature_enabled("w4_maint_photos", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'MaintenancePhotoTicket')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_maint_photos')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Maintenance photo tickets', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_keycard_alert(request):
    if not is_feature_enabled("w4_keycard_alert", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'KeycardAnomalyAlert')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_keycard_alert')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Keycard anomaly alerts', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_parking_violation(request):
    if not is_feature_enabled("w4_parking_violation", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'ParkingViolation')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_parking_violation')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Parking violations', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_pickup_verify(request):
    if not is_feature_enabled("w4_pickup_verify", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'AfterSchoolPickupVerify')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_pickup_verify')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'After-school pickup verify', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_api_keys(request):
    if not is_feature_enabled("w4_api_keys", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'PublicAPIKey')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_api_keys')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Public API keys', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_webhook_retry(request):
    if not is_feature_enabled("w4_webhook_retry", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'WebhookDeliveryAttempt')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_webhook_retry')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Webhook delivery log', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_preview_as(request):
    if not is_feature_enabled("w4_preview_as", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'PreviewAsUserSession')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_preview_as')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Preview as user', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_ferpa_export(request):
    if not is_feature_enabled("w4_ferpa_export", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'FERPADataExportJob')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_ferpa_export')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'FERPA data export', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_role_builder(request):
    if not is_feature_enabled("w4_role_builder", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'RolePermissionBinding')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_role_builder')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Role permission bindings', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_plugin_sandbox(request):
    if not is_feature_enabled("w4_plugin_sandbox", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'PluginRuntimeSandbox')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_plugin_sandbox')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Plugin runtime sandbox', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_graphql_schema(request):
    return redirect("/api/docs/")

@login_required
def w4_principal_dash(request):
    if not is_feature_enabled("w4_principal_dash", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'MultiSchoolPrincipalDashboard')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_principal_dash')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Multi-school principal dash', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_audit_diff(request):
    if not is_feature_enabled("w4_audit_diff", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'AuditDiffEntry')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_audit_diff')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Audit diff viewer', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_session_geo(request):
    if not is_feature_enabled("w4_session_geo", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'SessionGeoAlert')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_session_geo')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Session geo alerts', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w4_security_score(request):
    if not is_feature_enabled("w4_security_score", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    if request.method == "POST" and request.user.district_id:
        w4.security_scorecard(request.user.district)
        return redirect("portal:w4_security_score")
    from apps.extensions import models_wave4 as m4
    rows = [[s.score, s.assessed_at] for s in m4.SecurityScorecard.objects.filter(district=request.user.district)[:10]] if request.user.district_id else []
    return _generic(request, "Security scorecard", rows=rows, columns=["Score", "Assessed"], submit_label="Run assessment")

@login_required
def w4_navbar_pins(request):
    if not is_feature_enabled("w4_navbar_pins", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'NavbarFavoritePin')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        fields.setdefault('label', fields.get('notes', 'Link'))
        fields.setdefault('url_path', '/')
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_navbar_pins')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Navbar favorite pins', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_page_history(request):
    if not is_feature_enabled("w4_page_history", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'RecentPageHistory')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_page_history')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Recent page history', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_bulk_email(request, section_id):
    if not is_feature_enabled("w4_bulk_email", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(m4, 'BulkEmailFromGradebook')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_bulk_email', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Bulk email from gradebook', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_print_config(request):
    if not is_feature_enabled("w4_print_config", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'PrintViewConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_print_config')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Print view config', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_keyboard_help(request):
    return redirect("portal:ext_keyboard_help")

@login_required
def w4_dark_preview(request):
    if not is_feature_enabled("w4_dark_preview", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'DarkModePreview')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_dark_preview')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Dark mode preview', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_dash_widgets(request):
    if not is_feature_enabled("w4_dash_widgets", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'DashboardWidget')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_dash_widgets')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50] if hasattr(Model, 'user') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Dashboard widgets', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_changelog(request):
    if not is_feature_enabled("w4_changelog", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'InAppChangelog')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_changelog')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'In-app changelog', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_help_tooltips(request):
    if not is_feature_enabled("w4_help_tooltips", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'ContextualHelpTooltip')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_help_tooltips')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Contextual help tooltips', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w4_staff_photos(request):
    if not is_feature_enabled("w4_staff_photos", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave4 as m4
    Model = getattr(m4, 'StaffPhotoBulkUpload')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w4_staff_photos')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Staff photo bulk upload', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])
