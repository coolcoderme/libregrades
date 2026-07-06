"""Append advanced URL patterns to portal/urls.py"""
from pathlib import Path

FEATURES = [
    ("interactive_rubric", "section"),
    ("peer_review", "section"),
    ("quizzes", "section"),
    ("question_bank", None),
    ("exit_tickets", "section"),
    ("grade_appeals", None),
    ("moderation", None),
    ("competency", None),
    ("voice_feedback", None),
    ("ai_feedback", None),
    ("mobile_apps", None),
    ("parent_digest", None),
    ("schedule_conflicts", None),
    ("course_registration", None),
    ("student_hall_pass", None),
    ("safety_tips", None),
    ("translate", None),
    ("conf_self_schedule", None),
    ("e_signatures", None),
    ("alumni_transcripts", None),
    ("visual_schedule", None),
    ("section_balance", None),
    ("sub_autofill", None),
    ("inventory", None),
    ("maintenance", None),
    ("events", None),
    ("facility_use", None),
    ("lockdown", None),
    ("weather_closure", None),
    ("nurse_visits", None),
    ("immunization", None),
    ("seclusion", None),
    ("title_ix", None),
    ("volunteer_clearance", None),
    ("coppa", None),
    ("leave", None),
    ("evaluations", None),
    ("staff_directory", None),
    ("union_rules", None),
    ("sub_ratings", None),
    ("executive", None),
    ("benchmarks", None),
    ("chronic_absence", None),
    ("retention", None),
    ("program_eval", None),
    ("nl_query", None),
    ("multi_tenant", None),
    ("plugins", None),
    ("graphql", None),
    ("collab_gradebook", "section"),
    ("backups", None),
    ("health", None),
    ("feature_flags", None),
    ("ab_tests", None),
    ("command_palette", None),
    ("grade_undo", None),
    ("print_views", None),
    ("seating", "section"),
    ("waitlist", "section"),
    ("term_archive", None),
]

lines = [
    "\n    # Advanced features wave 2 (11-70)\n",
    '    path("features/advanced/", advanced_views.advanced_features_index, name="advanced_features_index"),\n',
    '    path("api/command-palette/", advanced_views.command_palette_api, name="adv_command_palette_api"),\n',
    '    path("api/grade-undo/", advanced_views.grade_undo_api, name="adv_grade_undo_api"),\n',
]
for slug, param in FEATURES:
    name = f"adv_{slug}"
    if param == "section":
        lines.append(f'    path("adv/{slug}/<int:section_id>/", advanced_views.adv_{slug}, name="{name}"),\n')
    else:
        lines.append(f'    path("adv/{slug}/", advanced_views.adv_{slug}, name="{name}"),\n')

urls_path = Path(__file__).resolve().parent.parent / "apps" / "portal" / "urls.py"
text = urls_path.read_text(encoding="utf-8")
if "advanced_features_index" not in text:
    text = text.replace(
        'from . import extended_views, feature_views, views',
        'from . import advanced_views, extended_views, feature_views, views',
    )
    text = text.rstrip()
    if text.endswith("]"):
        text = text[:-1] + "".join(lines) + "]\n"
    urls_path.write_text(text, encoding="utf-8")
    print("Updated urls.py")
else:
    print("urls.py already has advanced routes")
