"""Seed demo district data for LibreGrades Flask backend."""

from datetime import date, timedelta
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    Allergy,
    Assignment,
    BehaviorIncident,
    Course,
    CreditEarned,
    District,
    EmergencyContact,
    Enrollment,
    Grade,
    GradeCategory,
    GraduationRequirement,
    Immunization,
    MedicalCondition,
    MedicalRecord,
    Medication,
    ParentProfile,
    Period,
    School,
    Section,
    StudentProfile,
    Term,
    User,
    AcademicYear,
)


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        district = District.query.filter_by(code="DEMO").first()
        if not district:
            district = District(name="Demo Unified School District", code="DEMO")
            db.session.add(district)
            db.session.flush()

        school = School.query.filter_by(district_id=district.id, code="HS01").first()
        if not school:
            school = School(district_id=district.id, name="Demo High School", code="HS01")
            db.session.add(school)
            db.session.flush()

        year = AcademicYear.query.filter_by(district_id=district.id, name="2025-2026").first()
        if not year:
            year = AcademicYear(
                district_id=district.id,
                name="2025-2026",
                start_date=date(2025, 8, 15),
                end_date=date(2026, 6, 15),
                is_current=True,
            )
            db.session.add(year)
            db.session.flush()

        term = Term.query.filter_by(school_id=school.id, name="Fall 2025").first()
        if not term:
            term = Term(
                school_id=school.id,
                academic_year_id=year.id,
                name="Fall 2025",
                start_date=date(2025, 8, 15),
                end_date=date(2025, 12, 20),
                is_current=True,
            )
            db.session.add(term)
            db.session.flush()

        if not GraduationRequirement.query.filter_by(district_id=district.id).first():
            db.session.add(
                GraduationRequirement(
                    district_id=district.id,
                    subject_area="Total",
                    name="Standard Diploma",
                    credits_required=Decimal("220"),
                    total_credits_required=Decimal("220"),
                )
            )

        for n in range(1, 7):
            if not Period.query.filter_by(school_id=school.id, period_number=n).first():
                db.session.add(Period(school_id=school.id, period_number=n, name=f"Period {n}"))

        def ensure_user(username, **kwargs):
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username, **kwargs)
                user.set_password("demo1234")
                db.session.add(user)
                db.session.flush()
            return user

        teacher = ensure_user(
            "teacher1",
            first_name="Jane",
            last_name="Smith",
            email="teacher1@demo.org",
            role="teacher",
            district_id=district.id,
            school_id=school.id,
        )
        student_user = ensure_user(
            "student1",
            first_name="Alex",
            last_name="Johnson",
            email="student1@demo.org",
            role="student",
            district_id=district.id,
            school_id=school.id,
        )
        parent_user = ensure_user(
            "parent1",
            first_name="Maria",
            last_name="Johnson",
            email="parent1@demo.org",
            role="parent",
            district_id=district.id,
        )
        admin = ensure_user(
            "admin",
            first_name="District",
            last_name="Admin",
            email="admin@demo.org",
            role="district_admin",
            district_id=district.id,
        )

        student = StudentProfile.query.filter_by(user_id=student_user.id).first()
        if not student:
            student = StudentProfile(
                user_id=student_user.id,
                school_id=school.id,
                student_id="S1001234",
                grade_level=11,
            )
            db.session.add(student)
            db.session.flush()

        parent_profile = ParentProfile.query.filter_by(user_id=parent_user.id).first()
        if not parent_profile:
            parent_profile = ParentProfile(user_id=parent_user.id)
            db.session.add(parent_profile)
            db.session.flush()
        if student not in parent_profile.students:
            parent_profile.students.append(student)

        if not MedicalRecord.query.filter_by(user_id=student_user.id).first():
            db.session.add(
                MedicalRecord(user_id=student_user.id, doctor_name="Dr. Rivera", doctor_phone="555-0200")
            )
        if not Allergy.query.filter_by(user_id=student_user.id, allergen="Peanuts").first():
            db.session.add(Allergy(user_id=student_user.id, allergen="Peanuts", severity="Severe"))
        if not Medication.query.filter_by(user_id=student_user.id, name="Albuterol").first():
            db.session.add(
                Medication(user_id=student_user.id, name="Albuterol", dosage="2 puffs", frequency="As needed")
            )
        if not Immunization.query.filter_by(user_id=student_user.id, vaccine="Tdap").first():
            db.session.add(
                Immunization(
                    user_id=student_user.id,
                    vaccine="Tdap",
                    dose_number=1,
                    date_administered=date(2024, 9, 1),
                )
            )

        if not MedicalRecord.query.filter_by(user_id=teacher.id).first():
            db.session.add(
                MedicalRecord(
                    user_id=teacher.id,
                    doctor_name="Dr. Chen",
                    doctor_phone="555-0301",
                    insurance_provider="Blue Cross",
                )
            )
        if not Allergy.query.filter_by(user_id=teacher.id, allergen="Latex").first():
            db.session.add(
                Allergy(user_id=teacher.id, allergen="Latex", severity="Mild", reaction="Skin rash")
            )
        if not MedicalCondition.query.filter_by(user_id=teacher.id, condition="Asthma").first():
            db.session.add(
                MedicalCondition(
                    user_id=teacher.id,
                    condition="Asthma",
                    description="Exercise-induced",
                    is_active=True,
                )
            )

        if not EmergencyContact.query.filter_by(student_id=student.id, name="Maria Johnson").first():
            db.session.add(
                EmergencyContact(
                    student_id=student.id,
                    name="Maria Johnson",
                    relationship="Mother",
                    phone_primary="555-0100",
                    priority=1,
                    is_authorized_pickup=True,
                )
            )

        period = Period.query.filter_by(school_id=school.id, period_number=1).first()
        courses_data = [
            ("ENG11", "English 11", Decimal("5")),
            ("MATH11", "Algebra II", Decimal("5")),
            ("SCI11", "Chemistry", Decimal("5")),
        ]
        for code, name, credits in courses_data:
            course = Course.query.filter_by(school_id=school.id, code=code).first()
            if not course:
                course = Course(school_id=school.id, code=code, name=name, credit_value=credits)
                db.session.add(course)
                db.session.flush()

            section = Section.query.filter_by(course_id=course.id, term_id=term.id, section_number="1").first()
            if not section:
                section = Section(
                    course_id=course.id,
                    term_id=term.id,
                    section_number="1",
                    teacher_id=teacher.id,
                    period_id=period.id if period else None,
                    room="101",
                )
                db.session.add(section)
                db.session.flush()

            if not Enrollment.query.filter_by(student_id=student.id, section_id=section.id).first():
                db.session.add(Enrollment(student_id=student.id, section_id=section.id))

            cat = GradeCategory.query.filter_by(section_id=section.id, name="Coursework").first()
            if not cat:
                cat = GradeCategory(section_id=section.id, name="Coursework", weight=Decimal("100"))
                db.session.add(cat)
                db.session.flush()

            a1 = Assignment.query.filter_by(section_id=section.id, title=f"{code} Essay 1").first()
            if not a1:
                a1 = Assignment(
                    section_id=section.id,
                    category_id=cat.id,
                    title=f"{code} Essay 1",
                    due_date=date.today() - timedelta(days=14),
                    max_points=Decimal("100"),
                )
                db.session.add(a1)
                db.session.flush()
                db.session.add(
                    Grade(assignment_id=a1.id, student_id=student.id, points=Decimal("88"))
                )

            a2 = Assignment.query.filter_by(section_id=section.id, title=f"{code} Quiz 1").first()
            if not a2:
                a2 = Assignment(
                    section_id=section.id,
                    category_id=cat.id,
                    title=f"{code} Quiz 1",
                    due_date=date.today() - timedelta(days=3),
                    max_points=Decimal("50"),
                )
                db.session.add(a2)
                db.session.flush()
                db.session.add(
                    Grade(assignment_id=a2.id, student_id=student.id, is_missing=True)
                )

            if not CreditEarned.query.filter_by(
                student_id=student.id, course_id=course.id, term_name="Spring 2025"
            ).first():
                db.session.add(
                    CreditEarned(
                        student_id=student.id,
                        course_id=course.id,
                        term_name="Spring 2025",
                        school_year="2024-2025",
                        credits=credits,
                        letter_grade="B+",
                        gpa_points=Decimal("3.3"),
                    )
                )

        if not BehaviorIncident.query.filter_by(student_id=student.id).first():
            db.session.add(
                BehaviorIncident(
                    student_id=student.id,
                    incident_date=date.today() - timedelta(days=30),
                    incident_type="positive",
                    description="Helped organize library event",
                    reported_by_id=teacher.id,
                    parent_visible=True,
                )
            )

        db.session.commit()
        print("Demo data seeded successfully.")
        print("Accounts (password: demo1234):")
        print("  admin / teacher1 / student1 / parent1")


if __name__ == "__main__":
    seed()
