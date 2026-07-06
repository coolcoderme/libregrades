"""Report card PDF generation."""

from decimal import Decimal
from io import BytesIO

from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from apps.grades.models import Grade
from apps.grades.services import grades_visible_to_student


def generate_report_card_pdf(student, term):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - inch

    p.setFont("Helvetica-Bold", 16)
    p.drawString(inch, y, settings.DISTRICT_NAME)
    y -= 24
    p.setFont("Helvetica", 12)
    p.drawString(inch, y, f"Report Card — {term.name}")
    y -= 30
    p.drawString(inch, y, f"Student: {student.full_name}")
    y -= 18
    p.drawString(inch, y, f"Student ID: {student.student_id}")
    y -= 18
    p.drawString(inch, y, f"School: {student.school.name}")
    y -= 30

    p.setFont("Helvetica-Bold", 11)
    p.drawString(inch, y, "Course")
    p.drawString(3.5 * inch, y, "Assignments graded")
    p.drawString(5.0 * inch, y, "Average %")
    y -= 16
    p.setFont("Helvetica", 10)

    section_ids = student.enrollments.filter(section__term=term, is_active=True).values_list(
        "section_id", flat=True
    )
    grades = grades_visible_to_student(
        Grade.objects.filter(student=student, assignment__section_id__in=section_ids, points__isnull=False)
    ).select_related("assignment__section__course")

    by_course = {}
    for g in grades:
        code = g.assignment.section.course.code
        by_course.setdefault(code, {"name": g.assignment.section.course.name, "scores": []})
        if g.percentage is not None:
            by_course[code]["scores"].append(g.percentage)

    for code, data in sorted(by_course.items()):
        if y < inch:
            p.showPage()
            y = height - inch
        avg = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        p.drawString(inch, y, f"{code} — {data['name']}")
        p.drawString(3.5 * inch, y, str(len(data["scores"])))
        p.drawString(5.0 * inch, y, f"{avg:.1f}%")
        y -= 14

    y -= 10
    p.setFont("Helvetica-Oblique", 9)
    p.drawString(inch, y, "Comments appear on individual assignments in the portal.")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.getvalue()
