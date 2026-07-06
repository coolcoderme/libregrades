from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import ParentProfile, UserRole
from apps.behavior.models import BehaviorIncident, IncidentType
from apps.core.models import AcademicYear, District, School, Term
from apps.credits.models import CreditEarned, GraduationRequirement
from apps.emergency.models import EmergencyContact
from apps.grades.models import Assignment, Grade, GradeCategory
from apps.medical.models import Allergy, Immunization, MedicalCondition, MedicalRecord, Medication
from apps.scheduling.models import Course, Enrollment, Period, Section
from apps.students.models import StudentProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo district with sample users, courses, and grades"

    def handle(self, *args, **options):
        district, _ = District.objects.get_or_create(
            code="DEMO", defaults={"name": "Demo Unified School District"}
        )
        school, _ = School.objects.get_or_create(
            district=district, code="HS01", defaults={"name": "Demo High School"}
        )
        year, _ = AcademicYear.objects.get_or_create(
            district=district,
            name="2025-2026",
            defaults={
                "start_date": date(2025, 8, 15),
                "end_date": date(2026, 6, 15),
                "is_current": True,
            },
        )
        term, _ = Term.objects.get_or_create(
            school=school,
            name="Fall 2025",
            defaults={
                "academic_year": year,
                "start_date": date(2025, 8, 15),
                "end_date": date(2025, 12, 20),
                "is_current": True,
            },
        )

        GraduationRequirement.objects.get_or_create(
            district=district,
            subject_area="Total",
            defaults={"name": "Standard Diploma", "credits_required": Decimal("220"), "total_credits_required": Decimal("220")},
        )

        for n in range(1, 7):
            Period.objects.get_or_create(school=school, period_number=n, defaults={"name": f"Period {n}"})

        teacher, _ = User.objects.get_or_create(
            username="teacher1",
            defaults={
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "teacher1@demo.org",
                "role": UserRole.TEACHER,
                "district": district,
                "school": school,
            },
        )
        teacher.set_password("demo1234")
        teacher.save()

        student_user, _ = User.objects.get_or_create(
            username="student1",
            defaults={
                "first_name": "Alex",
                "last_name": "Johnson",
                "email": "student1@demo.org",
                "role": UserRole.STUDENT,
                "district": district,
                "school": school,
            },
        )
        student_user.set_password("demo1234")
        student_user.save()

        student, _ = StudentProfile.objects.get_or_create(
            user=student_user,
            defaults={"school": school, "student_id": "S1001234", "grade_level": 11},
        )

        parent_user, _ = User.objects.get_or_create(
            username="parent1",
            defaults={
                "first_name": "Maria",
                "last_name": "Johnson",
                "email": "parent1@demo.org",
                "role": UserRole.PARENT,
                "district": district,
            },
        )
        parent_user.set_password("demo1234")
        parent_user.save()
        parent_profile, _ = ParentProfile.objects.get_or_create(user=parent_user)
        parent_profile.students.add(student)

        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "first_name": "District",
                "last_name": "Admin",
                "email": "admin@demo.org",
                "role": UserRole.DISTRICT_ADMIN,
                "district": district,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.set_password("demo1234")
        admin.save()

        MedicalRecord.objects.get_or_create(
            user=student_user,
            defaults={
                "doctor_name": "Dr. Rivera",
                "doctor_phone": "555-0200",
            },
        )
        Allergy.objects.get_or_create(
            user=student_user, allergen="Peanuts", defaults={"severity": "Severe"}
        )
        Medication.objects.get_or_create(
            user=student_user,
            name="Albuterol",
            defaults={"dosage": "2 puffs", "frequency": "As needed"},
        )
        Immunization.objects.get_or_create(
            user=student_user,
            vaccine="Tdap",
            defaults={"dose_number": 1, "date_administered": date(2024, 9, 1)},
        )

        MedicalRecord.objects.get_or_create(
            user=teacher,
            defaults={
                "doctor_name": "Dr. Chen",
                "doctor_phone": "555-0301",
                "insurance_provider": "Blue Cross",
            },
        )
        Allergy.objects.get_or_create(
            user=teacher, allergen="Latex", defaults={"severity": "Mild", "reaction": "Skin rash"}
        )
        MedicalCondition.objects.get_or_create(
            user=teacher,
            condition="Asthma",
            defaults={"description": "Exercise-induced", "is_active": True},
        )

        MedicalRecord.objects.get_or_create(
            user=admin,
            defaults={
                "doctor_name": "Dr. Patel",
                "doctor_phone": "555-0400",
                "insurance_provider": "Kaiser",
            },
        )
        Medication.objects.get_or_create(
            user=admin,
            name="Lisinopril",
            defaults={"dosage": "10mg", "frequency": "Daily"},
        )
        EmergencyContact.objects.get_or_create(
            student=student,
            name="Maria Johnson",
            defaults={
                "relationship": "Mother",
                "phone_primary": "555-0100",
                "priority": 1,
                "is_authorized_pickup": True,
            },
        )

        courses_data = [
            ("ENG11", "English 11", Decimal("5")),
            ("MATH11", "Algebra II", Decimal("5")),
            ("SCI11", "Chemistry", Decimal("5")),
        ]
        period = Period.objects.filter(school=school, period_number=1).first()
        for code, name, credits in courses_data:
            course, _ = Course.objects.get_or_create(
                school=school, code=code, defaults={"name": name, "credit_value": credits}
            )
            section, _ = Section.objects.get_or_create(
                course=course,
                term=term,
                section_number="1",
                defaults={"teacher": teacher, "period": period, "room": "101"},
            )
            Enrollment.objects.get_or_create(student=student, section=section)
            cat, _ = GradeCategory.objects.get_or_create(
                section=section, name="Coursework", defaults={"weight": Decimal("100")}
            )
            a1, _ = Assignment.objects.get_or_create(
                section=section,
                title=f"{code} Essay 1",
                defaults={
                    "category": cat,
                    "due_date": date.today() - timedelta(days=14),
                    "max_points": Decimal("100"),
                },
            )
            a2, _ = Assignment.objects.get_or_create(
                section=section,
                title=f"{code} Quiz 1",
                defaults={
                    "category": cat,
                    "due_date": date.today() - timedelta(days=3),
                    "max_points": Decimal("50"),
                },
            )
            Grade.objects.get_or_create(
                assignment=a1, student=student, defaults={"points": Decimal("88")}
            )
            Grade.objects.get_or_create(assignment=a2, student=student, defaults={"is_missing": True})

            CreditEarned.objects.get_or_create(
                student=student,
                course=course,
                term_name="Spring 2025",
                school_year="2024-2025",
                defaults={"credits": credits, "letter_grade": "B+", "gpa_points": Decimal("3.3")},
            )

        BehaviorIncident.objects.get_or_create(
            student=student,
            incident_date=date.today() - timedelta(days=30),
            incident_type=IncidentType.POSITIVE,
            defaults={
                "description": "Helped organize library event",
                "reported_by": teacher,
                "parent_visible": True,
            },
        )

        from apps.communications.models import Announcement, AnnouncementScope
        from apps.students.models import StudentAccommodation
        from django.utils import timezone as tz

        Announcement.objects.get_or_create(
            title="Welcome to LibreGrades Demo",
            author=teacher,
            defaults={
                "body": "This is a sample district announcement. Check Due This Week for upcoming assignments.",
                "scope": AnnouncementScope.SCHOOL,
                "school": school,
            },
        )
        StudentAccommodation.objects.get_or_create(
            student=student,
            title="Extended time on tests",
            defaults={
                "accommodation_type": "504",
                "description": "1.5x time on assessments; prefer front-row seating.",
            },
        )
        for g in Grade.objects.filter(student=student, points__isnull=False):
            g.is_posted = True
            g.posted_at = tz.now()
            g.save(update_fields=["is_posted", "posted_at"])

        from apps.extensions.models import (
            DailyBulletinEntry,
            LearningStandard,
            PBISReward,
            ResourceRoom,
            StudentGoal,
        )

        LearningStandard.objects.get_or_create(
            school=school, code="ELA.11.1",
            defaults={"title": "Analyze theme development", "subject_area": "English"},
        )
        DailyBulletinEntry.objects.get_or_create(
            school=school, date=date.today(), title="Welcome",
            defaults={"body": "Check the Features menu for new tools.", "author": teacher},
        )
        ResourceRoom.objects.get_or_create(school=school, name="Computer Lab")
        PBISReward.objects.get_or_create(school=school, name="Homework pass", defaults={"point_cost": 10})
        StudentGoal.objects.get_or_create(
            student=student, title="Raise Algebra grade to B",
            defaults={"target_value": "B", "current_value": "C+"},
        )

        from apps.extensions.models_advanced import FeatureFlag, MobileAppRelease, QuestionBankItem

        FeatureFlag.objects.get_or_create(key="adv_quizzes", defaults={"name": "Quiz engine", "enabled_globally": True})
        MobileAppRelease.objects.get_or_create(platform="kivy", version="1.0.0", defaults={"release_notes": "Desktop client"})
        QuestionBankItem.objects.get_or_create(
            school=school, prompt="What is the theme of chapter 3?",
            defaults={"subject": "English", "question_type": "short"},
        )

        from apps.extensions import models_wave3 as w3m

        w3m.IntegrationConnector.objects.get_or_create(
            district=district, provider="google_classroom",
            defaults={"config": {"sync_rosters": True}, "is_active": False},
        )
        w3m.LDAPConfig.objects.get_or_create(
            district=district,
            defaults={"server_uri": "ldap://demo.local", "is_active": False},
        )
        w3m.PWAInstallConfig.objects.get_or_create(
            district=district,
            defaults={"manifest_name": "LibreGrades Demo", "offline_enabled": True},
        )
        w3m.OnboardingChecklist.objects.get_or_create(
            user=teacher, role="teacher",
            defaults={"steps_completed": {"profile": True, "sections": True}},
        )
        w3m.HelpChatLog.objects.get_or_create(
            user=parent_user, question="How do I link my child?",
            defaults={"answer": "Go to Parent → Link Child and enter the verification code."},
        )
        for key in ["w3_help_chat", "w3_google_classroom", "w3_emergency", "w3_pwa"]:
            FeatureFlag.objects.get_or_create(key=key, defaults={"name": key, "enabled_globally": True})

        from apps.extensions import models_wave4 as w4m

        w4m.ClassroomSyncJob.objects.get_or_create(
            district=district, defaults={"status": "completed", "rosters_synced": 10, "grades_pushed": 5}
        )
        w4m.InAppChangelog.objects.get_or_create(
            version="4.0.0", title="Wave 4 features",
            defaults={"body": "95 production-depth features are now available under Features → Wave 4.", "published_at": date.today()},
        )
        w4m.NavbarFavoritePin.objects.get_or_create(
            user=teacher, url_path="/teacher/sections/", defaults={"label": "Sections", "sort_order": 1}
        )
        w4m.EarlyWarningIndex.objects.get_or_create(
            student=student, defaults={"score": 12, "tier": "low", "factors": {"missing": 1, "absences": 0}}
        )
        for key in ["w4_classroom_sync", "w4_what_if", "w4_ewi", "w4_posting_preview"]:
            FeatureFlag.objects.get_or_create(key=key, defaults={"name": key, "enabled_globally": True})

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("Accounts (password: demo1234):")
        self.stdout.write("  admin / teacher1 / student1 / parent1")
