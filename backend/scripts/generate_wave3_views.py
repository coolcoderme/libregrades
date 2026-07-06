"""Generate apps/portal/wave3_views.py for wave 3 (74 features)."""

from pathlib import Path

HEADER = '''"""Wave 3 portal views (74 features — integrations + deep product)."""

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

'''

FEATURES = [
    (1, "google_classroom", "Google Classroom sync", "IntegrationConnector"),
    (2, "canvas_lti", "Canvas / Schoology LTI", "IntegrationConnector"),
    (3, "oneroster", "OneRoster sync", "SyncJob"),
    (4, "ldap", "LDAP / Active Directory", "LDAPConfig"),
    (5, "sms", "SMS alerts (Twilio)", "SMSConfig"),
    (6, "chat_bot", "Teams / Chat bot", "ChatBotConfig"),
    (7, "sso", "Clever / ClassLink SSO", "SSOProviderConfig"),
    (8, "payments", "Payment gateway (Stripe)", "PaymentConfig"),
    (9, "cloud_storage", "Cloud storage links", "CloudStorageLink"),
    (10, "migration", "SIS migration jobs", "MigrationJob"),
    (11, "quiz_player", "Quiz player sessions", "QuizPlayerSession", "section"),
    (12, "saved_nl", "Saved NL reports", "SavedNLReport"),
    (13, "plugin_sdk", "Plugin SDK modules", "PluginSDKModule"),
    (14, "native_apps", "Native app builds", "NativeAppBuild"),
    (15, "reg_wizard", "Course registration wizard", "CourseRegistrationWizardState"),
    (16, "sync_jobs", "Nightly sync jobs", "SyncJob"),
    (17, "api_explorer", "API explorer", None),
    (18, "integrations_hub", "Integration connectors", "IntegrationConnector"),
    (19, "lti_launch", "LTI deep link", "IntegrationConnector"),
    (20, "roster_delta", "Roster delta sync", "SyncJob"),
    (21, "ai_nudge", "AI missing-work nudges", "AIMissingNudge"),
    (22, "ai_narrative", "AI report card narratives", "AIReportNarrative"),
    (23, "ai_accommodation", "AI accommodation hints", "AIAccommodationHint"),
    (24, "smart_sub", "Smart substitute matching", "SmartSubMatch", "section"),
    (25, "grade_anomaly", "Grade anomaly detection", "GradeAnomaly", "section"),
    (26, "help_chat", "Help chatbot", "HelpChatLog"),
    (27, "ocr_handwriting", "OCR handwriting grading", "OCRHandwritingJob", "section"),
    (28, "project_groups", "Auto project groups", "ProjectGroup", "section"),
    (29, "class_feed", "Class social feed", "ClassFeedPost", "section"),
    (30, "video_announce", "Video announcements", "VideoAnnouncement"),
    (31, "live_translate", "Live translation cache", "LiveTranslation"),
    (32, "emergency", "Emergency broadcast", "EmergencyBroadcast"),
    (33, "office_hours", "Office hours booking", "OfficeHoursSlot"),
    (34, "newsletter", "Newsletter campaigns", "NewsletterCampaign"),
    (35, "alumni", "Alumni profiles", "AlumniProfile"),
    (36, "common_assess", "Common assessments", "CommonAssessment"),
    (37, "growth", "Student growth measures", "GrowthMeasure"),
    (38, "portfolio_defense", "Portfolio defense slots", "PortfolioDefenseSlot"),
    (39, "skill_badges", "Skill badges", "SkillBadge"),
    (40, "curriculum_map", "Curriculum mapping", "CurriculumMapUnit"),
    (41, "item_analysis", "Quiz item analysis", "ItemAnalysisReport", "section"),
    (42, "scantron", "Scantron scanning", "ScantronScan", "section"),
    (43, "cafeteria", "Cafeteria POS", "CafeteriaTransaction"),
    (44, "visitors", "Visitor management", "VisitorLog"),
    (45, "keycard", "Keycard access log", "KeycardAccessLog"),
    (46, "parking", "Parking permits", "ParkingPermit"),
    (47, "athletics", "Athletics eligibility", "AthleticsEligibility"),
    (48, "library", "Library checkouts", "LibraryCheckout"),
    (49, "afterschool", "After-school enrollment", "AfterSchoolEnrollment"),
    (50, "purchase", "Purchase requests", "PurchaseRequest"),
    (51, "grants", "Grant tracking", "GrantRecord"),
    (52, "time_clock", "Staff time clock", "TimeClockEntry"),
    (53, "vendors", "Vendor contracts", "VendorContract"),
    (54, "workers_comp", "Workers comp incidents", "WorkersCompIncident"),
    (55, "mckinney_vento", "McKinney-Vento records", "McKinneyVentoRecord"),
    (56, "plan_504", "504 plans", "Plan504"),
    (57, "iep", "IEP plans", "IEPPlan"),
    (58, "discipline_hearing", "Discipline hearings", "DisciplineHearing"),
    (59, "privacy", "Privacy requests (GDPR)", "PrivacyRequest"),
    (60, "board_packet", "Board meeting packets", "BoardPacket"),
    (61, "regions", "Multi-region config", "RegionConfig"),
    (62, "cache", "Redis / read replica", "CacheConfig"),
    (63, "immutable_audit", "Immutable audit chain", "ImmutableAuditEntry"),
    (64, "sandbox_clone", "Sandbox clone jobs", "SandboxCloneJob"),
    (65, "status_page", "Public status page", "StatusPageConfig"),
    (66, "custom_roles", "Custom RBAC roles", "CustomRole"),
    (67, "white_label", "White-label theming", "WhiteLabelTheme"),
    (68, "pwa_manifest", "PWA install config", "PWAInstallConfig"),
    (69, "bulk_actions", "Bulk action log", "BulkActionLog"),
    (70, "favorites", "User favorites", "UserFavorite"),
    (71, "split_view", "Split-view preferences", "SplitViewPreference"),
    (72, "pwa", "Progressive web app", None),
    (73, "a11y_audit", "Accessibility audits", "AccessibilityAuditRun"),
    (74, "onboarding", "Role onboarding checklist", "OnboardingChecklist"),
]

INDEX_GROUPS = [
    ("Integrations (1-10)", list(range(1, 11))),
    ("Deepen scaffolds (11-20)", list(range(11, 21))),
    ("AI & automation (21-28)", list(range(21, 29))),
    ("Communication (29-35)", list(range(29, 36))),
    ("Assessment (36-42)", list(range(36, 43))),
    ("Operations (43-49)", list(range(43, 50))),
    ("Finance (50-54)", list(range(50, 55))),
    ("Compliance (55-60)", list(range(55, 61))),
    ("Platform (61-68)", list(range(61, 69))),
    ("Quality of life (69-74)", list(range(69, 75))),
]

num_to = {n: (slug, title, model, *rest) for n, slug, title, model, *rest in FEATURES}
for n, slug, title, model in [(f[0], f[1], f[2], f[3]) for f in FEATURES]:
    pass

body = [HEADER]
body.append("WAVE3_INDEX = [\n")
for gtitle, nums in INDEX_GROUPS:
    body.append(f'    {{"title": "{gtitle}", "features": [\n')
    for n in nums:
        slug, title = num_to[n][0], num_to[n][1]
        body.append(f'        {{"num": {n}, "label": "{title}", "url_name": "portal:w3_{slug}"}},\n')
    body.append("    ]},\n")
body.append("]\n\n")

body.append("""
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


""")

DISTRICT_MODELS = {
    "IntegrationConnector", "SyncJob", "LDAPConfig", "SMSConfig", "ChatBotConfig",
    "SSOProviderConfig", "PaymentConfig", "MigrationJob", "EmergencyBroadcast",
    "NewsletterCampaign", "GrantRecord", "VendorContract", "BoardPacket",
    "RegionConfig", "CacheConfig", "SandboxCloneJob", "StatusPageConfig",
    "CustomRole", "WhiteLabelTheme", "PWAInstallConfig",
}
SCHOOL_MODELS = {
    "VideoAnnouncement", "CommonAssessment", "CurriculumMapUnit", "VisitorLog",
    "KeycardAccessLog", "AccessibilityAuditRun",
}
USER_MODELS = {"CloudStorageLink", "SavedNLReport", "PurchaseRequest", "PrivacyRequest", "BulkActionLog", "UserFavorite", "SplitViewPreference", "OnboardingChecklist", "HelpChatLog", "TimeClockEntry", "WorkersCompIncident", "OfficeHoursSlot"}

for item in FEATURES:
    n, slug, title = item[0], item[1], item[2]
    model = item[3]
    param = item[4] if len(item) > 4 else None

    body.append(f"\n@login_required\n")
    if slug in ("help_chat", "emergency", "athletics", "grade_anomaly", "ai_nudge", "ai_narrative", "project_groups", "item_analysis", "board_packet", "immutable_audit", "api_explorer", "pwa"):
        body.append("@require_http_methods(['GET', 'POST'])\n")
    body.append(f"def w3_{slug}(request")
    if param == "section":
        body.append(", section_id")
    body.append("):\n")

    if slug != "api_explorer" and slug != "pwa":
        body.append(f'    if not is_feature_enabled("w3_{slug}", _school(request)):\n')
        body.append('        return _generic(request, "Feature disabled", alert={"type": "warning", "text": "Enable in Feature flags."})\n')

    if slug == "api_explorer":
        body.append("    return redirect('/api/docs/')\n")
    elif slug == "pwa":
        body.append("""    cfg = None
    if request.user.district_id:
        from apps.extensions.models_wave3 import PWAInstallConfig
        cfg, _ = PWAInstallConfig.objects.get_or_create(district=request.user.district)
    return _generic(request, "Progressive web app", description="Install LibreGrades as an app. Service worker enabled for offline cache.",
        form_fields=[{"name": "manifest_name", "label": "App name", "value": cfg.manifest_name if cfg else "LibreGrades"},
        {"name": "offline_enabled", "label": "Offline mode", "type": "checkbox", "checked": cfg.offline_enabled if cfg else True}] if request.method == "GET" else None)
""")
    elif slug == "help_chat":
        body.append("""    from apps.extensions.models_wave3 import HelpChatLog
    answer = None
    if request.method == "POST":
        q = request.POST.get("question", "")
        answer = w3.help_chatbot_answer(q)
        HelpChatLog.objects.create(user=request.user, question=q, answer=answer)
    logs = HelpChatLog.objects.filter(user=request.user).order_by("-id")[:10]
    rows = [[l.question[:50], l.answer[:80]] for l in logs]
    return _generic(request, "Help chatbot", form_fields=[{"name": "question", "label": "Ask a question", "type": "textarea", "required": True}],
        rows=rows, columns=["Question", "Answer"], description=answer or "Ask about grades, linking children, or navigation.")
""")
    elif slug == "emergency":
        body.append("""    from apps.extensions.models_wave3 import EmergencyBroadcast
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
""")
    elif slug == "athletics":
        body.append("""    from apps.extensions.models_wave3 import AthleticsEligibility
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
""")
    elif slug == "grade_anomaly":
        body.append("""    from apps.extensions.models_wave3 import GradeAnomaly
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    if request.method == "POST":
        w3.detect_grade_anomalies(section)
        return redirect("portal:w3_grade_anomaly", section_id=section_id)
    anomalies = GradeAnomaly.objects.filter(grade__assignment__section=section)[:30]
    rows = [[a.grade.student.full_name, a.reason, a.severity] for a in anomalies]
    return _generic(request, f"Grade anomalies — {section.course.code}", rows=rows, columns=["Student", "Reason", "Severity"], submit_label="Scan for anomalies")
""")
    elif slug == "ai_nudge":
        body.append("""    from apps.extensions.models_wave3 import AIMissingNudge
    student = _resolve_student(request)
    if not student:
        return HttpResponseForbidden()
    if request.method == "POST":
        msg = w3.ai_missing_nudge_text(student)
        AIMissingNudge.objects.create(student=student, message=msg)
        return redirect("portal:w3_ai_nudge")
    rows = [[n.message[:80], n.sent_at or "draft"] for n in AIMissingNudge.objects.filter(student=student)[:20]]
    return _generic(request, "AI missing-work nudges", rows=rows, columns=["Message", "Status"], submit_label="Generate nudge")
""")
    elif slug == "ai_narrative":
        body.append("""    from apps.extensions.models_wave3 import AIReportNarrative
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
""")
    elif slug == "project_groups":
        body.append("""    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    if request.method == "POST":
        w3.auto_project_groups(section)
        return redirect("portal:w3_project_groups", section_id=section_id)
    from apps.extensions.models_wave3 import ProjectGroup
    rows = [[g.name, len(g.member_ids)] for g in ProjectGroup.objects.filter(section=section)]
    return _generic(request, f"Project groups — {section.course.code}", rows=rows, columns=["Group", "Members"], submit_label="Auto-assign groups")
""")
    elif slug == "item_analysis":
        body.append("""    from apps.extensions.models_advanced import Quiz
    from apps.extensions.models_wave3 import ItemAnalysisReport
    section = get_object_or_404(Section, pk=section_id)
    quiz = Quiz.objects.filter(section=section).first()
    if request.method == "POST" and quiz:
        w3.item_analysis_for_quiz(quiz)
        return redirect("portal:w3_item_analysis", section_id=section_id)
    rows = [[r.question_id, r.miss_rate] for r in ItemAnalysisReport.objects.filter(quiz=quiz)[:30]] if quiz else []
    return _generic(request, f"Item analysis — {section.course.code}", rows=rows, columns=["Question", "Miss %"], submit_label="Run analysis")
""")
    elif slug == "board_packet":
        body.append("""    from apps.extensions.models_wave3 import BoardPacket
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
""")
    elif slug == "immutable_audit":
        body.append("""    if request.user.role not in (UserRole.DISTRICT_ADMIN, UserRole.SCHOOL_ADMIN):
        return HttpResponseForbidden()
    from apps.extensions.models_wave3 import ImmutableAuditEntry
    if request.method == "POST":
        w3.append_immutable_audit(request.POST.get("event_type", "manual"), {"user": request.user.id, "note": request.POST.get("note", "")})
        return redirect("portal:w3_immutable_audit")
    rows = [[e.event_type, e.payload_hash[:16], e.created_at] for e in ImmutableAuditEntry.objects.all()[:30]]
    return _generic(request, "Immutable audit chain", rows=rows, columns=["Event", "Hash", "Time"],
        form_fields=[{"name": "event_type", "label": "Event type"}, {"name": "note", "label": "Note"}])
""")
    elif model:
        body.append("    from apps.extensions import models_wave3 as mw3\n")
        if param == "section":
            body.append("    section = get_object_or_404(Section, pk=section_id)\n")
        body.append(f"    Model = getattr(mw3, '{model}')\n")
        body.append("    if request.method == 'POST':\n")
        body.append("        fields = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken' and v}\n")
        if model in DISTRICT_MODELS:
            body.append("        if hasattr(Model, 'district') and request.user.district_id:\n            fields['district'] = request.user.district\n")
        if model in SCHOOL_MODELS:
            body.append("        fields.setdefault('school', _school(request))\n")
        if model in USER_MODELS:
            body.append("        if hasattr(Model, 'user'):\n            fields['user'] = request.user\n")
        if model == "IntegrationConnector":
            body.append(f"        fields.setdefault('provider', '{slug}')\n")
        if param == "section":
            body.append("        if hasattr(Model, 'section'):\n            fields['section'] = section\n")
        if model == "QuizPlayerSession":
            body.append("        from apps.extensions.models_advanced import Quiz\n        q = Quiz.objects.filter(section=section).first()\n        if q: fields['quiz'] = q\n        student = _resolve_student(request)\n        if student: fields['student'] = student\n")
        if model == "CourseRegistrationWizardState":
            body.append("        student = _resolve_student(request)\n        if student: fields['student'] = student\n")
        if model == "SmartSubMatch":
            body.append("        fields['date'] = timezone.now().date()\n")
        if model == "ClassFeedPost":
            body.append("        fields['author'] = request.user\n")
        if model == "SplitViewPreference":
            body.append("        SplitViewPreference.objects.update_or_create(user=request.user, defaults={'show_student_panel': request.POST.get('show_student_panel') == 'on'})\n")
            body.append(f"        return redirect('portal:w3_{slug}')\n")
        else:
            body.append("        try:\n            Model.objects.create(**{k: fields[k] for k in fields if hasattr(Model, k)})\n        except Exception:\n            pass\n")
            if param == "section":
                body.append(f"        return redirect('portal:w3_{slug}', section_id=section_id)\n")
            else:
                body.append(f"        return redirect('portal:w3_{slug}')\n")
        body.append("    qs = Model.objects.all()[:50]\n")
        if param == "section":
            body.append("    qs = Model.objects.filter(section=section)[:50] if hasattr(Model, 'section') else qs\n")
        elif model in DISTRICT_MODELS:
            body.append("    qs = Model.objects.filter(district=request.user.district)[:50] if request.user.district_id and hasattr(Model, 'district') else qs\n")
        elif model == "CloudStorageLink":
            body.append("    qs = Model.objects.filter(user=request.user)[:50]\n")
        body.append("    rows = [[str(getattr(o, f.name, ''))[:40] for f in Model._meta.fields[:4]] for o in qs]\n")
        body.append("    cols = [f.name for f in Model._meta.fields[:4]]\n")
        extra_form = ""
        if model == "SplitViewPreference":
            extra_form = "pref, _ = SplitViewPreference.objects.get_or_create(user=request.user)\n    "
            body.append(f"    {extra_form}return _generic(request, '{title}', columns=cols, rows=rows, form_fields=[{{'name': 'show_student_panel', 'label': 'Show student panel', 'type': 'checkbox', 'checked': pref.show_student_panel}}])\n")
        else:
            body.append(f"    return _generic(request, '{title}', columns=cols, rows=rows, form_fields=[{{'name': 'notes', 'label': 'Notes / primary field'}}])\n")

out = Path(__file__).resolve().parent.parent / "apps" / "portal" / "wave3_views.py"
out.write_text("".join(body), encoding="utf-8")
print(f"Wrote {out}")
