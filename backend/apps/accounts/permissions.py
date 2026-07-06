"""Shared permission helpers for LibreGrades."""

from apps.accounts.models import UserRole

MEDICAL_NONE = "none"
MEDICAL_LIMITED = "limited"
MEDICAL_FULL = "full"


def get_student_profile(user):
    if hasattr(user, "student_profile"):
        return user.student_profile
    return None


def get_parent_profile(user):
    if hasattr(user, "parent_profile"):
        return user.parent_profile
    return None


def _teacher_has_student(user, student):
    from apps.scheduling.models import Enrollment

    return Enrollment.objects.filter(
        student=student, section__teacher=user, is_active=True
    ).exists()


def get_student_medical_access(user, student):
    """Return none, limited (teacher), or full (elevated) for a student record."""
    if user.id == student.user_id:
        return MEDICAL_FULL
    if user.role == UserRole.DISTRICT_ADMIN:
        return MEDICAL_FULL
    if user.role == UserRole.COUNSELOR:
        return MEDICAL_FULL
    if user.role == UserRole.SCHOOL_ADMIN and user.school_id == student.school_id:
        return MEDICAL_FULL
    if user.role == UserRole.STUDENT:
        profile = get_student_profile(user)
        return MEDICAL_FULL if profile and profile.id == student.id else MEDICAL_NONE
    if user.role == UserRole.PARENT:
        profile = get_parent_profile(user)
        return (
            MEDICAL_FULL
            if profile and profile.students.filter(id=student.id).exists()
            else MEDICAL_NONE
        )
    if user.role == UserRole.TEACHER and _teacher_has_student(user, student):
        return MEDICAL_LIMITED
    return MEDICAL_NONE


def get_staff_medical_access(user, target_user):
    """Access level for staff (non-student) medical records."""
    if user.id == target_user.id:
        return MEDICAL_FULL
    if user.role == UserRole.DISTRICT_ADMIN:
        return MEDICAL_FULL
    if user.role in (UserRole.SCHOOL_ADMIN, UserRole.COUNSELOR):
        return (
            MEDICAL_FULL
            if user.school_id and user.school_id == target_user.school_id
            else MEDICAL_NONE
        )
    return MEDICAL_NONE


def user_can_view_student(user, student):
    if user.role in (UserRole.DISTRICT_ADMIN, UserRole.COUNSELOR):
        return True
    if user.role == UserRole.SCHOOL_ADMIN and user.school_id == student.school_id:
        return True
    if user.role == UserRole.STUDENT:
        profile = get_student_profile(user)
        return profile and profile.id == student.id
    if user.role == UserRole.PARENT:
        profile = get_parent_profile(user)
        return profile and profile.students.filter(id=student.id).exists()
    if user.role == UserRole.TEACHER:
        return _teacher_has_student(user, student)
    return False


def user_can_edit_grades(user, section):
    if user.role in (UserRole.DISTRICT_ADMIN, UserRole.SCHOOL_ADMIN):
        return True
    if user.role == UserRole.TEACHER and section.teacher_id == user.id:
        return True
    return False


def user_can_access_section(request, section):
    user = request.user
    if user.is_authenticated and user_can_edit_grades(user, section):
        return True
    if request.session.get("substitute_pass_id"):
        return section.id in request.session.get("substitute_section_ids", [])
    return False


def user_can_view_medical(user, student=None, target_user=None):
    if student is not None:
        return get_student_medical_access(user, student) != MEDICAL_NONE
    if target_user is not None:
        if hasattr(target_user, "student_profile"):
            return (
                get_student_medical_access(user, target_user.student_profile) != MEDICAL_NONE
            )
        return get_staff_medical_access(user, target_user) != MEDICAL_NONE
    return False


def user_can_view_immunizations(user, student=None, target_user=None):
    if student is not None:
        return get_student_medical_access(user, student) == MEDICAL_FULL
    if target_user is not None:
        if hasattr(target_user, "student_profile"):
            return (
                get_student_medical_access(user, target_user.student_profile) == MEDICAL_FULL
            )
        return get_staff_medical_access(user, target_user) == MEDICAL_FULL
    return False


def user_can_view_emergency_contacts(user, student):
    """Teachers (own sections), students, parents, counselors, and admins."""
    return get_student_medical_access(user, student) in (MEDICAL_LIMITED, MEDICAL_FULL)


def user_can_edit_medical(user):
    return user.role in (
        UserRole.DISTRICT_ADMIN,
        UserRole.SCHOOL_ADMIN,
        UserRole.COUNSELOR,
    )


def accessible_students(user):
    from apps.students.models import StudentProfile

    if user.role == UserRole.DISTRICT_ADMIN:
        return StudentProfile.objects.all()
    if user.role in (UserRole.SCHOOL_ADMIN, UserRole.COUNSELOR):
        if user.school_id:
            return StudentProfile.objects.filter(school_id=user.school_id)
        return StudentProfile.objects.none()
    if user.role == UserRole.STUDENT:
        profile = get_student_profile(user)
        if profile:
            return StudentProfile.objects.filter(id=profile.id)
    if user.role == UserRole.PARENT:
        profile = get_parent_profile(user)
        if profile:
            return profile.students.all()
    if user.role == UserRole.TEACHER:
        from apps.scheduling.models import Enrollment

        ids = Enrollment.objects.filter(
            section__teacher=user, is_active=True
        ).values_list("student_id", flat=True)
        return StudentProfile.objects.filter(id__in=ids)
    return StudentProfile.objects.none()
