"""Append wave 4 URL patterns to portal/urls.py."""
from pathlib import Path

FEATURES = [
    ("classroom_sync", None),
    ("oneroster_live", None),
    ("sms_live", None),
    ("stripe_fees", None),
    ("ldap_live", None),
    ("clever_sso", None),
    ("timed_quiz", "section"),
    ("item_dashboard", "section"),
    ("anomaly_workflow", None),
    ("audit_verify", None),
    ("board_pdf", None),
    ("iep504_goals", None),
    ("athletics_auto", None),
    ("emergency_delivery", None),
    ("offline_gradebook", None),
    ("standards_rc", None),
    ("what_if", None),
    ("assignment_version", None),
    ("anon_grading", "section"),
    ("calibration", None),
    ("rubric_bank", None),
    ("retake_policy", "section"),
    ("weight_presets", None),
    ("scantron_post", None),
    ("ocr_pipeline", None),
    ("portfolio_exhibit", None),
    ("badge_evidence", None),
    ("cross_section", None),
    ("missing_escalation", None),
    ("comment_templates", None),
    ("family_inbox", None),
    ("push_fcm", None),
    ("digest_live", None),
    ("wellness", None),
    ("homework_planner", None),
    ("conf_prep", None),
    ("i18n_portal", None),
    ("tts", None),
    ("student_questions", "section"),
    ("grad_checklist", None),
    ("course_wishlist", None),
    ("sibling_schedule", None),
    ("co_teacher", "section"),
    ("gradebook_presence", "section"),
    ("lesson_link", None),
    ("sub_lesson_pack", "section"),
    ("dept_distribution", None),
    ("intervention_grp", "section"),
    ("plc_meeting", None),
    ("sub_request", None),
    ("voice_feedback", None),
    ("mail_merge", "section"),
    ("assignment_copy", None),
    ("posting_preview", "section"),
    ("ewi", None),
    ("equity_gap", None),
    ("teacher_effect", None),
    ("enroll_forecast", None),
    ("budget_scenario", None),
    ("report_builder", None),
    ("scheduled_report", None),
    ("state_benchmark", None),
    ("climate_survey", None),
    ("route_heatmap", None),
    ("visitor_badge", None),
    ("cafeteria_alert", None),
    ("bus_gps", None),
    ("reunification", None),
    ("threat_assess", None),
    ("med_admin", None),
    ("maint_photos", None),
    ("keycard_alert", None),
    ("parking_violation", None),
    ("pickup_verify", None),
    ("api_keys", None),
    ("webhook_retry", None),
    ("preview_as", None),
    ("ferpa_export", None),
    ("role_builder", None),
    ("plugin_sandbox", None),
    ("graphql_schema", None),
    ("principal_dash", None),
    ("audit_diff", None),
    ("session_geo", None),
    ("security_score", None),
    ("navbar_pins", None),
    ("page_history", None),
    ("bulk_email", "section"),
    ("print_config", None),
    ("keyboard_help", None),
    ("dark_preview", None),
    ("dash_widgets", None),
    ("changelog", None),
    ("help_tooltips", None),
    ("staff_photos", None),
]

lines = [
    "\n    # Wave 4 features (1-95)\n",
    '    path("features/wave4/", wave4_views.wave4_features_index, name="wave4_features_index"),\n',
]
for slug, param in FEATURES:
    name = f"w4_{slug}"
    if param == "section":
        lines.append(f'    path("w4/{slug}/<int:section_id>/", wave4_views.w4_{slug}, name="{name}"),\n')
    else:
        lines.append(f'    path("w4/{slug}/", wave4_views.w4_{slug}, name="{name}"),\n')

urls_path = Path(__file__).resolve().parent.parent / "apps" / "portal" / "urls.py"
text = urls_path.read_text(encoding="utf-8")
if "wave4_features_index" not in text:
    if "wave4_views" not in text:
        text = text.replace(
            "from . import advanced_views, extended_views, feature_views, views, wave3_views",
            "from . import advanced_views, extended_views, feature_views, views, wave3_views, wave4_views",
        )
    text = text.rstrip()
    if text.endswith("]"):
        text = text[:-1] + "".join(lines) + "]\n"
    urls_path.write_text(text, encoding="utf-8")
    print("Updated urls.py")
else:
    print("urls.py already has wave4 routes")
