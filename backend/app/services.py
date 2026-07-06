from decimal import Decimal
from io import BytesIO

from flask import current_app
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from .models import CreditEarned, GraduationRequirement


def build_credit_summary(student):
    credits = CreditEarned.query.filter_by(student_id=student.id).all()
    total = sum(c.credits for c in credits)
    district = student.school.district
    reqs = GraduationRequirement.query.filter_by(district_id=district.id).all()
    required = reqs[0].total_credits_required if reqs else Decimal("220")
    by_subject = {}
    for c in credits:
        area = c.course.name.split()[0] if c.course and c.course.name else "General"
        by_subject[area] = by_subject.get(area, Decimal("0")) + c.credits
    percent = float(total / required * 100) if required else 0
    return {
        "total_credits": total,
        "credits_required": required,
        "percent_complete": min(percent, 100.0),
        "by_subject": {k: v for k, v in by_subject.items()},
    }


def generate_transcript_pdf(student):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - inch

    district_name = current_app.config.get("DISTRICT_NAME", "LibreGrades District")
    p.setFont("Helvetica-Bold", 16)
    p.drawString(inch, y, district_name)
    y -= 24
    p.setFont("Helvetica", 12)
    p.drawString(inch, y, "Official Transcript")
    y -= 30
    p.drawString(inch, y, f"Student: {student.full_name}")
    y -= 18
    p.drawString(inch, y, f"Student ID: {student.student_id}")
    y -= 18
    p.drawString(inch, y, f"School: {student.school.name}")
    y -= 30

    p.setFont("Helvetica-Bold", 11)
    p.drawString(inch, y, "Course")
    p.drawString(3.5 * inch, y, "Term")
    p.drawString(4.5 * inch, y, "Credits")
    p.drawString(5.5 * inch, y, "Grade")
    y -= 16
    p.setFont("Helvetica", 10)

    credits = CreditEarned.query.filter_by(student_id=student.id).all()
    total = Decimal("0")
    for c in credits:
        if y < inch:
            p.showPage()
            y = height - inch
        p.drawString(inch, y, f"{c.course.code} — {c.course.name}")
        p.drawString(3.5 * inch, y, c.term_name)
        p.drawString(4.5 * inch, y, str(c.credits))
        p.drawString(5.5 * inch, y, c.letter_grade)
        total += c.credits
        y -= 14

    y -= 10
    p.setFont("Helvetica-Bold", 11)
    p.drawString(inch, y, f"Total Credits: {total}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.getvalue()
