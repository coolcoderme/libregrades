"""Convert Flask/Jinja portal templates back to Django template syntax."""
from pathlib import Path
import re

PORTAL = Path(__file__).resolve().parent.parent / "templates" / "portal"

REPLACEMENTS = [
    (r'\{\{\s*url_for\(\'portal\.dashboard\'\)\s*\}\}', "{% url 'portal:dashboard' %}"),
    (r'\{\{\s*url_for\(\'portal\.profile\'\)\s*\}\}', "{% url 'portal:profile' %}"),
    (r'\{\{\s*url_for\(\'portal\.medical\'\)\s*\}\}', "{% url 'portal:medical' %}"),
    (r'\{\{\s*url_for\(\'portal\.grades\'\)\s*\}\}', "{% url 'portal:grades' %}"),
    (r'\{\{\s*url_for\(\'portal\.missing\'\)\s*\}\}', "{% url 'portal:missing' %}"),
    (r'\{\{\s*url_for\(\'portal\.schedule\'\)\s*\}\}', "{% url 'portal:schedule' %}"),
    (r'\{\{\s*url_for\(\'portal\.credits\'\)\s*\}\}', "{% url 'portal:credits' %}"),
    (r'\{\{\s*url_for\(\'portal\.attendance\'\)\s*\}\}', "{% url 'portal:attendance' %}"),
    (r'\{\{\s*url_for\(\'portal\.behavior\'\)\s*\}\}', "{% url 'portal:behavior' %}"),
    (r'\{\{\s*url_for\(\'portal\.emergency\'\)\s*\}\}', "{% url 'portal:emergency' %}"),
    (r'\{\{\s*url_for\(\'portal\.teacher_sections\'\)\s*\}\}', "{% url 'portal:teacher_sections' %}"),
    (r'\{\{\s*url_for\(\'portal\.admin_students\'\)\s*\}\}', "{% url 'portal:admin_students' %}"),
    (r'\{\{\s*url_for\(\'portal\.link_child\'\)\s*\}\}', "{% url 'portal:link_child' %}"),
    (r'\{\{\s*url_for\(\'portal\.notification_preferences\'\)\s*\}\}', "{% url 'portal:notification_preferences' %}"),
    (r'\{\{\s*url_for\(\'auth\.logout\'\)\s*\}\}', "{% url 'portal:logout' %}"),
    (
        r'\{\{\s*url_for\(\'portal\.gradebook\',\s*section_id=section\.id\)\s*\}\}',
        "{% url 'portal:gradebook' section.id %}",
    ),
    (
        r'\{\{\s*url_for\(\'portal\.section_attendance\',\s*section_id=section\.id\)\s*\}\}',
        "{% url 'portal:section_attendance' section.id %}",
    ),
    (
        r'\{\{\s*url_for\(\'portal\.section_attendance_submit\',\s*section_id=section\.id\)\s*\}\}',
        "{% url 'portal:section_attendance_submit' section.id %}",
    ),
    (
        r'\{\{\s*url_for\(\'portal\.gradebook_update\',\s*section_id=section\.id\)\s*\}\}',
        "{% url 'portal:gradebook_update' section.id %}",
    ),
    (
        r'\{\{\s*url_for\(\'portal\.transcript\',\s*student_id=student\.id\)\s*\}\}',
        "{% url 'portal:transcript' student.id %}",
    ),
    (
        r'\{\{\s*url_for\(\'portal\.grades\',\s*student_id=s\.id\)\s*\}\}',
        "{% url 'portal:grades_student' s.id %}",
    ),
    (
        r'\{\{\s*url_for\(\'portal\.medical\',\s*student_id=s\.id\)\s*\}\}',
        "{% url 'portal:medical_student' s.id %}",
    ),
    (
        r'\{\{\s*url_for\(\'portal\.transcript\',\s*student_id=s\.id\)\s*\}\}',
        "{% url 'portal:transcript' s.id %}",
    ),
    (
        r'\{\{\s*url_for\(\'portal\.medical\',\s*student_id=row\.student\.id\)\s*\}\}',
        "{% url 'portal:medical_student' row.student.id %}",
    ),
    (
        r'\{\{\s*url_for\(\'portal\.emergency\',\s*student_id=row\.student\.id\)\s*\}\}',
        "{% url 'portal:emergency_student' row.student.id %}",
    ),
    (
        r'\{\{\s*url_for\(\'portal\.emergency\',\s*student_id=student\.id\)\s*\}\}',
        "{% url 'portal:emergency_student' student.id %}",
    ),
    (
        r'<input type="hidden" name="csrf_token" value="\{\{\s*csrf_token\(\)\s*\}\}">',
        "{% csrf_token %}",
    ),
    (r"current_user", "user"),
    (r"\{\%\s*else\s*\%\}", "{% empty %}"),
    (r"is not none", "!= None"),
    (r"\|default\('—'\)", '|default:"—"'),
    (r"\|default\('TBD'\)", '|default:"TBD"'),
    (r"\|default\('Daily'\)", '|default:"Daily"'),
    (r"\|round\|int", "|floatformat:0"),
    (r"\|round\(1\)", "|floatformat:1"),
    (r"\|truncate\(12,\s*True\)", "|truncatechars:12"),
    (r"e\.section\.teacher\.display_name if e\.section\.teacher else 'TBD'", "e.section.teacher.get_full_name|default:'TBD'"),
    (r"e\.section\.period\.name\|default\('—'\) if e\.section\.period else '—'", "e.section.period.name|default:'—'"),
    (r"r\.section\.course\.code if r\.section and r\.section\.course else 'Daily'", "r.section.course.code|default:'Daily'"),
    (r"\{\{\s*user\.display_name\s*\}\}", "{{ user.get_full_name|default:user.username }}"),
]

for path in PORTAL.rglob("*.html"):
    if path.name in {"base.html", "login.html", "profile.html"}:
        continue
    text = path.read_text(encoding="utf-8")
    original = text
    for pattern, repl in REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        print("updated", path.relative_to(PORTAL.parent))
