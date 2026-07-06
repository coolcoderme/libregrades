"""Append wave 3 URL patterns to portal/urls.py."""
from pathlib import Path

FEATURES = [
    ("google_classroom", None),
    ("canvas_lti", None),
    ("oneroster", None),
    ("ldap", None),
    ("sms", None),
    ("chat_bot", None),
    ("sso", None),
    ("payments", None),
    ("cloud_storage", None),
    ("migration", None),
    ("quiz_player", "section"),
    ("saved_nl", None),
    ("plugin_sdk", None),
    ("native_apps", None),
    ("reg_wizard", None),
    ("sync_jobs", None),
    ("api_explorer", None),
    ("integrations_hub", None),
    ("lti_launch", None),
    ("roster_delta", None),
    ("ai_nudge", None),
    ("ai_narrative", None),
    ("ai_accommodation", None),
    ("smart_sub", "section"),
    ("grade_anomaly", "section"),
    ("help_chat", None),
    ("ocr_handwriting", "section"),
    ("project_groups", "section"),
    ("class_feed", "section"),
    ("video_announce", None),
    ("live_translate", None),
    ("emergency", None),
    ("office_hours", None),
    ("newsletter", None),
    ("alumni", None),
    ("common_assess", None),
    ("growth", None),
    ("portfolio_defense", None),
    ("skill_badges", None),
    ("curriculum_map", None),
    ("item_analysis", "section"),
    ("scantron", "section"),
    ("cafeteria", None),
    ("visitors", None),
    ("keycard", None),
    ("parking", None),
    ("athletics", None),
    ("library", None),
    ("afterschool", None),
    ("purchase", None),
    ("grants", None),
    ("time_clock", None),
    ("vendors", None),
    ("workers_comp", None),
    ("mckinney_vento", None),
    ("plan_504", None),
    ("iep", None),
    ("discipline_hearing", None),
    ("privacy", None),
    ("board_packet", None),
    ("regions", None),
    ("cache", None),
    ("immutable_audit", None),
    ("sandbox_clone", None),
    ("status_page", None),
    ("custom_roles", None),
    ("white_label", None),
    ("pwa_manifest", None),
    ("bulk_actions", None),
    ("favorites", None),
    ("split_view", None),
    ("pwa", None),
    ("a11y_audit", None),
    ("onboarding", None),
]

lines = [
    "\n    # Wave 3 features (1-74)\n",
    '    path("features/wave3/", wave3_views.wave3_features_index, name="wave3_features_index"),\n',
    '    path("manifest.json", wave3_views.w3_manifest_json, name="w3_manifest_json"),\n',
]
for slug, param in FEATURES:
    name = f"w3_{slug}"
    if param == "section":
        lines.append(f'    path("w3/{slug}/<int:section_id>/", wave3_views.w3_{slug}, name="{name}"),\n')
    else:
        lines.append(f'    path("w3/{slug}/", wave3_views.w3_{slug}, name="{name}"),\n')

urls_path = Path(__file__).resolve().parent.parent / "apps" / "portal" / "urls.py"
text = urls_path.read_text(encoding="utf-8")
if "wave3_features_index" not in text:
    if "wave3_views" not in text:
        text = text.replace(
            "from . import advanced_views, extended_views, feature_views, views",
            "from . import advanced_views, extended_views, feature_views, views, wave3_views",
        )
    text = text.rstrip()
    if text.endswith("]"):
        text = text[:-1] + "".join(lines) + "]\n"
    urls_path.write_text(text, encoding="utf-8")
    print("Updated urls.py")
else:
    print("urls.py already has wave3 routes")
