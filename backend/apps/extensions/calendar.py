from datetime import datetime, timedelta

from django.http import HttpResponse
from django.utils import timezone

from apps.grades.models import Assignment
from apps.scheduling.models import Enrollment


def ical_feed_for_student(student) -> str:
    section_ids = Enrollment.objects.filter(student=student, is_active=True).values_list("section_id", flat=True)
    assignments = Assignment.objects.filter(
        section_id__in=section_ids, due_date__isnull=False, is_published=True
    ).select_related("section__course")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LibreGrades//Homework//EN",
        "CALSCALE:GREGORIAN",
    ]
    for a in assignments:
        if not a.due_date:
            continue
        dt = datetime.combine(a.due_date, datetime.min.time())
        dtend = dt + timedelta(hours=1)
        uid = f"assignment-{a.id}@libregrades"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{dtend.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{a.section.course.code} — {a.title}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def ical_response(student) -> HttpResponse:
    body = ical_feed_for_student(student)
    response = HttpResponse(body, content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="homework_{student.student_id}.ics"'
    return response
