"""Shared permission helpers for LibreGrades."""

from sqlalchemy import select

from .extensions import db
from .models import Enrollment, ParentProfile, Section, StudentProfile, User

MEDICAL_NONE = "none"
MEDICAL_LIMITED = "limited"
MEDICAL_FULL = "full"


def get_student_profile(user):
    return user.student_profile if user else None


def get_parent_profile(user):
    return user.parent_profile if user else None


def _teacher_has_student(user, student):
    return db.session.scalar(
        select(
            db.exists().where(
                Enrollment.student_id == student.id,
                Enrollment.is_active.is_(True),
                Enrollment.section_id == Section.id,
                Section.teacher_id == user.id,
            )
        )
    )


def get_student_medical_access(user, student):
    if user.id == student.user_id:
        return MEDICAL_FULL
    if user.role == "district_admin":
        return MEDICAL_FULL
    if user.role == "counselor":
        return MEDICAL_FULL
    if user.role == "school_admin" and user.school_id == student.school_id:
        return MEDICAL_FULL
    if user.role == "student":
        profile = get_student_profile(user)
        return MEDICAL_FULL if profile and profile.id == student.id else MEDICAL_NONE
    if user.role == "parent":
        profile = get_parent_profile(user)
        return MEDICAL_FULL if profile and student in profile.students else MEDICAL_NONE
    if user.role == "teacher" and _teacher_has_student(user, student):
        return MEDICAL_LIMITED
    return MEDICAL_NONE


def get_staff_medical_access(user, target_user):
    if user.id == target_user.id:
        return MEDICAL_FULL
    if user.role == "district_admin":
        return MEDICAL_FULL
    if user.role in ("school_admin", "counselor"):
        return (
            MEDICAL_FULL
            if user.school_id and user.school_id == target_user.school_id
            else MEDICAL_NONE
        )
    return MEDICAL_NONE


def user_can_view_student(user, student):
    if user.role in ("district_admin", "counselor"):
        return True
    if user.role == "school_admin" and user.school_id == student.school_id:
        return True
    if user.role == "student":
        profile = get_student_profile(user)
        return profile and profile.id == student.id
    if user.role == "parent":
        profile = get_parent_profile(user)
        return profile and student in profile.students
    if user.role == "teacher":
        return _teacher_has_student(user, student)
    return False


def user_can_edit_grades(user, section):
    if user.role in ("district_admin", "school_admin"):
        return True
    if user.role == "teacher" and section.teacher_id == user.id:
        return True
    return False


def user_can_view_emergency_contacts(user, student):
    return get_student_medical_access(user, student) in (MEDICAL_LIMITED, MEDICAL_FULL)


def accessible_students(user):
    if user.role == "district_admin":
        return StudentProfile.query
    if user.role in ("school_admin", "counselor"):
        if user.school_id:
            return StudentProfile.query.filter_by(school_id=user.school_id)
        return StudentProfile.query.filter(db.false())
    if user.role == "student":
        profile = get_student_profile(user)
        if profile:
            return StudentProfile.query.filter_by(id=profile.id)
    if user.role == "parent":
        profile = get_parent_profile(user)
        if profile and profile.students:
            ids = [s.id for s in profile.students]
            return StudentProfile.query.filter(StudentProfile.id.in_(ids))
    if user.role == "teacher":
        ids = db.session.scalars(
            select(Enrollment.student_id)
            .join(Section, Enrollment.section_id == Section.id)
            .where(Section.teacher_id == user.id, Enrollment.is_active.is_(True))
        ).all()
        return (
            StudentProfile.query.filter(StudentProfile.id.in_(ids))
            if ids
            else StudentProfile.query.filter(db.false())
        )
    return StudentProfile.query.filter(db.false())
