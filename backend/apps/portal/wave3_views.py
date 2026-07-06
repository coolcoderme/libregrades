"""Wave 3 portal views (74 features — integrations + deep product)."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import UserRole
from apps.accounts.permissions import accessible_students, user_can_edit_grades
from apps.extensions.advanced_services import is_feature_enabled
from apps.extensions import wave3_services as w3
from apps.portal.extended_views import _generic, _school
from apps.portal.views import _resolve_student
from apps.scheduling.models import Section

WAVE3_INDEX = [
    {"title": "Integrations (1-10)", "features": [
        {"num": 1, "label": "Google Classroom sync", "url_name": "portal:w3_google_classroom"},
        {"num": 2, "label": "Canvas / Schoology LTI", "url_name": "portal:w3_canvas_lti"},
        {"num": 3, "label": "OneRoster sync", "url_name": "portal:w3_oneroster"},
        {"num": 4, "label": "LDAP / Active Directory", "url_name": "portal:w3_ldap"},
        {"num": 5, "label": "SMS alerts (Twilio)", "url_name": "portal:w3_sms"},
        {"num": 6, "label": "Teams / Chat bot", "url_name": "portal:w3_chat_bot"},
        {"num": 7, "label": "Clever / ClassLink SSO", "url_name": "portal:w3_sso"},
        {"num": 8, "label": "Payment gateway (Stripe)", "url_name": "portal:w3_payments"},
        {"num": 9, "label": "Cloud storage links", "url_name": "portal:w3_cloud_storage"},
        {"num": 10, "label": "SIS migration jobs", "url_name": "portal:w3_migration"},
    ]},
    {"title": "Deepen scaffolds (11-20)", "features": [
        {"num": 11, "label": "Quiz player sessions", "url_name": "portal:teacher_sections"},
        {"num": 12, "label": "Saved NL reports", "url_name": "portal:w3_saved_nl"},
        {"num": 13, "label": "Plugin SDK modules", "url_name": "portal:w3_plugin_sdk"},
        {"num": 14, "label": "Native app builds", "url_name": "portal:w3_native_apps"},
        {"num": 15, "label": "Course registration wizard", "url_name": "portal:w3_reg_wizard"},
        {"num": 16, "label": "Nightly sync jobs", "url_name": "portal:w3_sync_jobs"},
        {"num": 17, "label": "API explorer", "url_name": "portal:w3_api_explorer"},
        {"num": 18, "label": "Integration connectors", "url_name": "portal:w3_integrations_hub"},
        {"num": 19, "label": "LTI deep link", "url_name": "portal:w3_lti_launch"},
        {"num": 20, "label": "Roster delta sync", "url_name": "portal:w3_roster_delta"},
    ]},
    {"title": "AI & automation (21-28)", "features": [
        {"num": 21, "label": "AI missing-work nudges", "url_name": "portal:w3_ai_nudge"},
        {"num": 22, "label": "AI report card narratives", "url_name": "portal:w3_ai_narrative"},
        {"num": 23, "label": "AI accommodation hints", "url_name": "portal:w3_ai_accommodation"},
        {"num": 24, "label": "Smart substitute matching", "url_name": "portal:teacher_sections"},
        {"num": 25, "label": "Grade anomaly detection", "url_name": "portal:teacher_sections"},
        {"num": 26, "label": "Help chatbot", "url_name": "portal:w3_help_chat"},
        {"num": 27, "label": "OCR handwriting grading", "url_name": "portal:teacher_sections"},
        {"num": 28, "label": "Auto project groups", "url_name": "portal:teacher_sections"},
    ]},
    {"title": "Communication (29-35)", "features": [
        {"num": 29, "label": "Class social feed", "url_name": "portal:teacher_sections"},
        {"num": 30, "label": "Video announcements", "url_name": "portal:w3_video_announce"},
        {"num": 31, "label": "Live translation cache", "url_name": "portal:w3_live_translate"},
        {"num": 32, "label": "Emergency broadcast", "url_name": "portal:w3_emergency"},
        {"num": 33, "label": "Office hours booking", "url_name": "portal:w3_office_hours"},
        {"num": 34, "label": "Newsletter campaigns", "url_name": "portal:w3_newsletter"},
        {"num": 35, "label": "Alumni profiles", "url_name": "portal:w3_alumni"},
    ]},
    {"title": "Assessment (36-42)", "features": [
        {"num": 36, "label": "Common assessments", "url_name": "portal:w3_common_assess"},
        {"num": 37, "label": "Student growth measures", "url_name": "portal:w3_growth"},
        {"num": 38, "label": "Portfolio defense slots", "url_name": "portal:w3_portfolio_defense"},
        {"num": 39, "label": "Skill badges", "url_name": "portal:w3_skill_badges"},
        {"num": 40, "label": "Curriculum mapping", "url_name": "portal:w3_curriculum_map"},
        {"num": 41, "label": "Quiz item analysis", "url_name": "portal:teacher_sections"},
        {"num": 42, "label": "Scantron scanning", "url_name": "portal:teacher_sections"},
    ]},
    {"title": "Operations (43-49)", "features": [
        {"num": 43, "label": "Cafeteria POS", "url_name": "portal:w3_cafeteria"},
        {"num": 44, "label": "Visitor management", "url_name": "portal:w3_visitors"},
        {"num": 45, "label": "Keycard access log", "url_name": "portal:w3_keycard"},
        {"num": 46, "label": "Parking permits", "url_name": "portal:w3_parking"},
        {"num": 47, "label": "Athletics eligibility", "url_name": "portal:w3_athletics"},
        {"num": 48, "label": "Library checkouts", "url_name": "portal:w3_library"},
        {"num": 49, "label": "After-school enrollment", "url_name": "portal:w3_afterschool"},
    ]},
    {"title": "Finance (50-54)", "features": [
        {"num": 50, "label": "Purchase requests", "url_name": "portal:w3_purchase"},
        {"num": 51, "label": "Grant tracking", "url_name": "portal:w3_grants"},
        {"num": 52, "label": "Staff time clock", "url_name": "portal:w3_time_clock"},
        {"num": 53, "label": "Vendor contracts", "url_name": "portal:w3_vendors"},
        {"num": 54, "label": "Workers comp incidents", "url_name": "portal:w3_workers_comp"},
    ]},
    {"title": "Compliance (55-60)", "features": [
        {"num": 55, "label": "McKinney-Vento records", "url_name": "portal:w3_mckinney_vento"},
        {"num": 56, "label": "504 plans", "url_name": "portal:w3_plan_504"},
        {"num": 57, "label": "IEP plans", "url_name": "portal:w3_iep"},
        {"num": 58, "label": "Discipline hearings", "url_name": "portal:w3_discipline_hearing"},
        {"num": 59, "label": "Privacy requests (GDPR)", "url_name": "portal:w3_privacy"},
        {"num": 60, "label": "Board meeting packets", "url_name": "portal:w3_board_packet"},
    ]},
    {"title": "Platform (61-68)", "features": [
        {"num": 61, "label": "Multi-region config", "url_name": "portal:w3_regions"},
        {"num": 62, "label": "Redis / read replica", "url_name": "portal:w3_cache"},
        {"num": 63, "label": "Immutable audit chain", "url_name": "portal:w3_immutable_audit"},
        {"num": 64, "label": "Sandbox clone jobs", "url_name": "portal:w3_sandbox_clone"},
        {"num": 65, "label": "Public status page", "url_name": "portal:w3_status_page"},
        {"num": 66, "label": "Custom RBAC roles", "url_name": "portal:w3_custom_roles"},
        {"num": 67, "label": "White-label theming", "url_name": "portal:w3_white_label"},
        {"num": 68, "label": "PWA install config", "url_name": "portal:w3_pwa_manifest"},
    ]},
    {"title": "Quality of life (69-74)", "features": [
        {"num": 69, "label": "Bulk action log", "url_name": "portal:w3_bulk_actions"},
        {"num": 70, "label": "User favorites", "url_name": "portal:w3_favorites"},
        {"num": 71, "label": "Split-view preferences", "url_name": "portal:w3_split_view"},
        {"num": 72, "label": "Progressive web app", "url_name": "portal:w3_pwa"},
        {"num": 73, "label": "Accessibility audits", "url_name": "portal:w3_a11y_audit"},
        {"num": 74, "label": "Role onboarding checklist", "url_name": "portal:w3_onboarding"},
    ]},
]


@login_required
def wave3_features_index(request):
    return render(request, "portal/extended/index.html", {
        "groups": WAVE3_INDEX,
        "page_title": "Wave 3 features (1-74)",
        "wave3": True,
    })


@login_required
def w3_manifest_json(request):
    cfg = getattr(request.user.district, "pwa_config", None) if request.user.district_id else None
    data = {
        "name": cfg.manifest_name if cfg else "LibreGrades",
        "short_name": "LibreGrades",
        "start_url": "/",
        "display": "standalone",
        "theme_color": cfg.theme_color if cfg else "#0d6efd",
        "background_color": "#ffffff",
    }
    return JsonResponse(data)



@login_required
def w3_google_classroom(request):
    if not is_feature_enabled("w3_google_classroom", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'IntegrationConnector')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        fields.setdefault('provider', 'google_classroom')
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_google_classroom')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Google Classroom sync', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_canvas_lti(request):
    if not is_feature_enabled("w3_canvas_lti", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'IntegrationConnector')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        fields.setdefault('provider', 'canvas_lti')
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_canvas_lti')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Canvas / Schoology LTI', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_oneroster(request):
    if not is_feature_enabled("w3_oneroster", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'SyncJob')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_oneroster')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'OneRoster sync', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_ldap(request):
    if not is_feature_enabled("w3_ldap", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'LDAPConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_ldap')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'LDAP / Active Directory', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_sms(request):
    if not is_feature_enabled("w3_sms", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'SMSConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_sms')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'SMS alerts (Twilio)', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_chat_bot(request):
    if not is_feature_enabled("w3_chat_bot", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'ChatBotConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_chat_bot')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Teams / Chat bot', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_sso(request):
    if not is_feature_enabled("w3_sso", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'SSOProviderConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_sso')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Clever / ClassLink SSO', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_payments(request):
    if not is_feature_enabled("w3_payments", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'PaymentConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_payments')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Payment gateway (Stripe)', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_cloud_storage(request):
    if not is_feature_enabled("w3_cloud_storage", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'CloudStorageLink')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_cloud_storage')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(user=request.user)[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Cloud storage links', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_migration(request):
    if not is_feature_enabled("w3_migration", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'MigrationJob')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_migration')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'SIS migration jobs', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_quiz_player(request, section_id):
    if not is_feature_enabled("w3_quiz_player", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(mw3, 'QuizPlayerSession')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        from apps.extensions.models_advanced import Quiz
        q = Quiz.objects.filter(section=section).first()
        if q: fields['quiz'] = q
        student = _resolve_student(request)
        if student: fields['student'] = student
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_quiz_player', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Quiz player sessions', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_saved_nl(request):
    if not is_feature_enabled("w3_saved_nl", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'SavedNLReport')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_saved_nl')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Saved NL reports', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_plugin_sdk(request):
    if not is_feature_enabled("w3_plugin_sdk", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'PluginSDKModule')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_plugin_sdk')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Plugin SDK modules', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_native_apps(request):
    if not is_feature_enabled("w3_native_apps", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'NativeAppBuild')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_native_apps')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Native app builds', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_reg_wizard(request):
    if not is_feature_enabled("w3_reg_wizard", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'CourseRegistrationWizardState')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        student = _resolve_student(request)
        if student: fields['student'] = student
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_reg_wizard')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Course registration wizard', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_sync_jobs(request):
    if not is_feature_enabled("w3_sync_jobs", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'SyncJob')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_sync_jobs')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Nightly sync jobs', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w3_api_explorer(request):
    return redirect('/api/docs/')

@login_required
def w3_integrations_hub(request):
    if not is_feature_enabled("w3_integrations_hub", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'IntegrationConnector')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        fields.setdefault('provider', 'integrations_hub')
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_integrations_hub')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Integration connectors', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_lti_launch(request):
    if not is_feature_enabled("w3_lti_launch", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'IntegrationConnector')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        fields.setdefault('provider', 'lti_launch')
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_lti_launch')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'LTI deep link', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_roster_delta(request):
    if not is_feature_enabled("w3_roster_delta", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'SyncJob')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_roster_delta')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Roster delta sync', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w3_ai_nudge(request):
    if not is_feature_enabled("w3_ai_nudge", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_wave3 import AIMissingNudge
    student = _resolve_student(request)
    if not student:
        return HttpResponseForbidden()
    if request.method == "POST":
        msg = w3.ai_missing_nudge_text(student)
        AIMissingNudge.objects.create(student=student, message=msg)
        return redirect("portal:w3_ai_nudge")
    rows = [[n.message[:80], n.sent_at or "draft"] for n in AIMissingNudge.objects.filter(student=student)[:20]]
    return _generic(request, "AI missing-work nudges", rows=rows, columns=["Message", "Status"], submit_label="Generate nudge")

@login_required
@require_http_methods(['GET', 'POST'])
def w3_ai_narrative(request):
    if not is_feature_enabled("w3_ai_narrative", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_wave3 import AIReportNarrative
    student = _resolve_student(request)
    if not student:
        return HttpResponseForbidden()
    term = _school(request).terms.filter(is_current=True).first()
    if request.method == "POST" and term:
        text = w3.ai_report_narrative(student, term)
        AIReportNarrative.objects.create(student=student, term=term, narrative=text)
        return redirect("portal:w3_ai_narrative")
    rows = [[n.term.name, n.narrative[:100], n.accepted] for n in AIReportNarrative.objects.filter(student=student)[:10]]
    return _generic(request, "AI report narratives", rows=rows, columns=["Term", "Narrative", "Accepted"], submit_label="Generate narrative")

@login_required
def w3_ai_accommodation(request):
    if not is_feature_enabled("w3_ai_accommodation", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'AIAccommodationHint')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_ai_accommodation')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'AI accommodation hints', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_smart_sub(request, section_id):
    if not is_feature_enabled("w3_smart_sub", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(mw3, 'SmartSubMatch')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        fields['date'] = timezone.now().date()
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_smart_sub', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Smart substitute matching', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w3_grade_anomaly(request, section_id):
    if not is_feature_enabled("w3_grade_anomaly", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_wave3 import GradeAnomaly
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    if request.method == "POST":
        w3.detect_grade_anomalies(section)
        return redirect("portal:w3_grade_anomaly", section_id=section_id)
    anomalies = GradeAnomaly.objects.filter(grade__assignment__section=section)[:30]
    rows = [[a.grade.student.full_name, a.reason, a.severity] for a in anomalies]
    return _generic(request, f"Grade anomalies — {section.course.code}", rows=rows, columns=["Student", "Reason", "Severity"], submit_label="Scan for anomalies")

@login_required
@require_http_methods(['GET', 'POST'])
def w3_help_chat(request):
    if not is_feature_enabled("w3_help_chat", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_wave3 import HelpChatLog
    answer = None
    if request.method == "POST":
        q = request.POST.get("question", "")
        answer = w3.help_chatbot_answer(q)
        HelpChatLog.objects.create(user=request.user, question=q, answer=answer)
    logs = HelpChatLog.objects.filter(user=request.user).order_by("-id")[:10]
    rows = [[l.question[:50], l.answer[:80]] for l in logs]
    return _generic(request, "Help chatbot", form_fields=[{"name": "question", "label": "Ask a question", "type": "textarea", "required": True}],
        rows=rows, columns=["Question", "Answer"], description=answer or "Ask about grades, linking children, or navigation.")

@login_required
def w3_ocr_handwriting(request, section_id):
    if not is_feature_enabled("w3_ocr_handwriting", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(mw3, 'OCRHandwritingJob')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_ocr_handwriting', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'OCR handwriting grading', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w3_project_groups(request, section_id):
    if not is_feature_enabled("w3_project_groups", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    if request.method == "POST":
        w3.auto_project_groups(section)
        return redirect("portal:w3_project_groups", section_id=section_id)
    from apps.extensions.models_wave3 import ProjectGroup
    rows = [[g.name, len(g.member_ids)] for g in ProjectGroup.objects.filter(section=section)]
    return _generic(request, f"Project groups — {section.course.code}", rows=rows, columns=["Group", "Members"], submit_label="Auto-assign groups")

@login_required
def w3_class_feed(request, section_id):
    if not is_feature_enabled("w3_class_feed", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(mw3, 'ClassFeedPost')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        fields['author'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_class_feed', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Class social feed', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_video_announce(request):
    if not is_feature_enabled("w3_video_announce", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'VideoAnnouncement')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_video_announce')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Video announcements', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_live_translate(request):
    if not is_feature_enabled("w3_live_translate", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'LiveTranslation')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_live_translate')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Live translation cache', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w3_emergency(request):
    if not is_feature_enabled("w3_emergency", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_wave3 import EmergencyBroadcast
    if request.user.role not in (UserRole.DISTRICT_ADMIN, UserRole.SCHOOL_ADMIN):
        return HttpResponseForbidden()
    if request.method == "POST" and request.user.district_id:
        msg = request.POST.get("message", "")
        EmergencyBroadcast.objects.create(district=request.user.district, message=msg, sent_by=request.user,
            recipient_count=0, channels=["email", "sms", "push"])
        return redirect("portal:w3_emergency")
    rows = [[b.message[:60], b.recipient_count, b.created_at] for b in EmergencyBroadcast.objects.filter(district=request.user.district)[:20]] if request.user.district_id else []
    return _generic(request, "Emergency broadcast", form_fields=[{"name": "message", "label": "Alert message", "type": "textarea", "required": True}],
        rows=rows, columns=["Message", "Recipients", "Sent"])

@login_required
def w3_office_hours(request):
    if not is_feature_enabled("w3_office_hours", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'OfficeHoursSlot')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_office_hours')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Office hours booking', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_newsletter(request):
    if not is_feature_enabled("w3_newsletter", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'NewsletterCampaign')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_newsletter')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Newsletter campaigns', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_alumni(request):
    if not is_feature_enabled("w3_alumni", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'AlumniProfile')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_alumni')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Alumni profiles', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_common_assess(request):
    if not is_feature_enabled("w3_common_assess", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'CommonAssessment')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_common_assess')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Common assessments', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_growth(request):
    if not is_feature_enabled("w3_growth", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'GrowthMeasure')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_growth')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Student growth measures', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_portfolio_defense(request):
    if not is_feature_enabled("w3_portfolio_defense", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'PortfolioDefenseSlot')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_portfolio_defense')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Portfolio defense slots', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_skill_badges(request):
    if not is_feature_enabled("w3_skill_badges", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'SkillBadge')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_skill_badges')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Skill badges', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_curriculum_map(request):
    if not is_feature_enabled("w3_curriculum_map", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'CurriculumMapUnit')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_curriculum_map')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Curriculum mapping', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w3_item_analysis(request, section_id):
    if not is_feature_enabled("w3_item_analysis", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_advanced import Quiz
    from apps.extensions.models_wave3 import ItemAnalysisReport
    section = get_object_or_404(Section, pk=section_id)
    quiz = Quiz.objects.filter(section=section).first()
    if request.method == "POST" and quiz:
        w3.item_analysis_for_quiz(quiz)
        return redirect("portal:w3_item_analysis", section_id=section_id)
    rows = [[r.question_id, r.miss_rate] for r in ItemAnalysisReport.objects.filter(quiz=quiz)[:30]] if quiz else []
    return _generic(request, f"Item analysis — {section.course.code}", rows=rows, columns=["Question", "Miss %"], submit_label="Run analysis")

@login_required
def w3_scantron(request, section_id):
    if not is_feature_enabled("w3_scantron", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    section = get_object_or_404(Section, pk=section_id)
    Model = getattr(mw3, 'ScantronScan')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'section'):
            fields['section'] = section
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_scantron', section_id=section_id)
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Scantron scanning', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_cafeteria(request):
    if not is_feature_enabled("w3_cafeteria", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'CafeteriaTransaction')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_cafeteria')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Cafeteria POS', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_visitors(request):
    if not is_feature_enabled("w3_visitors", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'VisitorLog')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_visitors')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Visitor management', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_keycard(request):
    if not is_feature_enabled("w3_keycard", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'KeycardAccessLog')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_keycard')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Keycard access log', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_parking(request):
    if not is_feature_enabled("w3_parking", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'ParkingPermit')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_parking')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Parking permits', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w3_athletics(request):
    if not is_feature_enabled("w3_athletics", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_wave3 import AthleticsEligibility
    student = _resolve_student(request)
    if not student:
        return HttpResponseForbidden()
    result = None
    if request.method == "POST":
        result = w3.athletics_eligibility_check(student)
        AthleticsEligibility.objects.create(student=student, sport=request.POST.get("sport", "General"),
            gpa=result["gpa"], is_eligible=result["is_eligible"], checked_at=timezone.now().date())
        return redirect("portal:w3_athletics")
    rows = [[e.sport, e.gpa, e.is_eligible, e.checked_at] for e in AthleticsEligibility.objects.filter(student=student)[:20]]
    return _generic(request, f"Athletics eligibility — {student.full_name}", rows=rows, columns=["Sport", "GPA", "Eligible", "Checked"],
        form_fields=[{"name": "sport", "label": "Sport"}], description=str(result) if result else "Check NCAA/eligibility rules.")

@login_required
def w3_library(request):
    if not is_feature_enabled("w3_library", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'LibraryCheckout')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_library')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Library checkouts', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_afterschool(request):
    if not is_feature_enabled("w3_afterschool", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'AfterSchoolEnrollment')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_afterschool')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'After-school enrollment', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_purchase(request):
    if not is_feature_enabled("w3_purchase", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'PurchaseRequest')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_purchase')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Purchase requests', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_grants(request):
    if not is_feature_enabled("w3_grants", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'GrantRecord')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_grants')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Grant tracking', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_time_clock(request):
    if not is_feature_enabled("w3_time_clock", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'TimeClockEntry')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_time_clock')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Staff time clock', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_vendors(request):
    if not is_feature_enabled("w3_vendors", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'VendorContract')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_vendors')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Vendor contracts', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_workers_comp(request):
    if not is_feature_enabled("w3_workers_comp", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'WorkersCompIncident')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_workers_comp')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Workers comp incidents', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_mckinney_vento(request):
    if not is_feature_enabled("w3_mckinney_vento", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'McKinneyVentoRecord')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_mckinney_vento')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'McKinney-Vento records', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_plan_504(request):
    if not is_feature_enabled("w3_plan_504", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'Plan504')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_plan_504')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, '504 plans', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_iep(request):
    if not is_feature_enabled("w3_iep", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'IEPPlan')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_iep')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'IEP plans', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_discipline_hearing(request):
    if not is_feature_enabled("w3_discipline_hearing", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'DisciplineHearing')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_discipline_hearing')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Discipline hearings', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_privacy(request):
    if not is_feature_enabled("w3_privacy", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'PrivacyRequest')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_privacy')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Privacy requests (GDPR)', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w3_board_packet(request):
    if not is_feature_enabled("w3_board_packet", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions.models_wave3 import BoardPacket
    if request.user.role != UserRole.DISTRICT_ADMIN:
        return HttpResponseForbidden()
    if request.method == "POST" and request.user.district_id:
        from datetime import date
        d = request.POST.get("meeting_date") or str(date.today())
        w3.board_packet_generate(request.user.district, d)
        return redirect("portal:w3_board_packet")
    rows = [[p.title, p.meeting_date] for p in BoardPacket.objects.filter(district=request.user.district)[:20]] if request.user.district_id else []
    return _generic(request, "Board meeting packets", rows=rows, columns=["Title", "Date"],
        form_fields=[{"name": "meeting_date", "label": "Meeting date", "type": "date"}], submit_label="Generate packet")

@login_required
def w3_regions(request):
    if not is_feature_enabled("w3_regions", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'RegionConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_regions')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Multi-region config', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_cache(request):
    if not is_feature_enabled("w3_cache", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'CacheConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_cache')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Redis / read replica', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
@require_http_methods(['GET', 'POST'])
def w3_immutable_audit(request):
    if not is_feature_enabled("w3_immutable_audit", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    if request.user.role not in (UserRole.DISTRICT_ADMIN, UserRole.SCHOOL_ADMIN):
        return HttpResponseForbidden()
    from apps.extensions.models_wave3 import ImmutableAuditEntry
    if request.method == "POST":
        w3.append_immutable_audit(request.POST.get("event_type", "manual"), {"user": request.user.id, "note": request.POST.get("note", "")})
        return redirect("portal:w3_immutable_audit")
    rows = [[e.event_type, e.payload_hash[:16], e.created_at] for e in ImmutableAuditEntry.objects.all()[:30]]
    return _generic(request, "Immutable audit chain", rows=rows, columns=["Event", "Hash", "Time"],
        form_fields=[{"name": "event_type", "label": "Event type"}, {"name": "note", "label": "Note"}])

@login_required
def w3_sandbox_clone(request):
    if not is_feature_enabled("w3_sandbox_clone", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'SandboxCloneJob')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_sandbox_clone')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Sandbox clone jobs', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_status_page(request):
    if not is_feature_enabled("w3_status_page", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'StatusPageConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_status_page')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Public status page', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_custom_roles(request):
    if not is_feature_enabled("w3_custom_roles", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'CustomRole')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_custom_roles')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Custom RBAC roles', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_white_label(request):
    if not is_feature_enabled("w3_white_label", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'WhiteLabelTheme')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_white_label')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'White-label theming', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_pwa_manifest(request):
    if not is_feature_enabled("w3_pwa_manifest", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'PWAInstallConfig')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'district') and request.user.district_id:
            fields['district'] = request.user.district
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_pwa_manifest')
    qs = Model.objects.all()[:50]
    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'PWA install config', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_bulk_actions(request):
    if not is_feature_enabled("w3_bulk_actions", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'BulkActionLog')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_bulk_actions')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Bulk action log', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_favorites(request):
    if not is_feature_enabled("w3_favorites", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'UserFavorite')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_favorites')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'User favorites', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_split_view(request):
    if not is_feature_enabled("w3_split_view", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'SplitViewPreference')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        Model.objects.update_or_create(user=request.user, defaults={'show_student_panel': request.POST.get('show_student_panel') == 'on'})
        return redirect('portal:w3_split_view')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    pref, _ = Model.objects.get_or_create(user=request.user)
    return _generic(request, 'Split-view preferences', columns=cols, rows=rows, form_fields=[{'name': 'show_student_panel', 'label': 'Show student panel', 'type': 'checkbox', 'checked': pref.show_student_panel}])

@login_required
@require_http_methods(['GET', 'POST'])
def w3_pwa(request):
    cfg = None
    if request.user.district_id:
        from apps.extensions.models_wave3 import PWAInstallConfig
        cfg, _ = PWAInstallConfig.objects.get_or_create(district=request.user.district)
    return _generic(request, "Progressive web app", description="Install LibreGrades as an app. Service worker enabled for offline cache.",
        form_fields=[{"name": "manifest_name", "label": "App name", "value": cfg.manifest_name if cfg else "LibreGrades"},
        {"name": "offline_enabled", "label": "Offline mode", "type": "checkbox", "checked": cfg.offline_enabled if cfg else True}] if request.method == "GET" else None)

@login_required
def w3_a11y_audit(request):
    if not is_feature_enabled("w3_a11y_audit", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'AccessibilityAuditRun')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        fields.setdefault('school', _school(request))
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_a11y_audit')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Accessibility audits', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])

@login_required
def w3_onboarding(request):
    if not is_feature_enabled("w3_onboarding", _school(request)):
        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})
    from apps.extensions import models_wave3 as mw3
    Model = getattr(mw3, 'OnboardingChecklist')
    if request.method == 'POST':
        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}
        if hasattr(Model, 'user'):
            fields['user'] = request.user
        try:
            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})
        except Exception:
            pass
        return redirect('portal:w3_onboarding')
    qs = Model.objects.all()[:50]
    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]
    cols = [f.name for f in Model._meta.fields[:4]]
    return _generic(request, 'Role onboarding checklist', columns=cols, rows=rows, form_fields=[{'name': 'notes', 'label': 'Notes / primary field'}])
