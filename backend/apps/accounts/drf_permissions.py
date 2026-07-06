from rest_framework import permissions

from apps.accounts.models import UserRole
from apps.accounts.permissions import user_can_edit_grades, user_can_view_medical, user_can_view_student


class IsStaffRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff_role


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_role


class CanViewStudent(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        student = obj if hasattr(obj, "student_id") else getattr(obj, "student", obj)
        if hasattr(student, "student_profile"):
            student = student.student_profile
        return user_can_view_student(request.user, student)


class CanViewMedical(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        student = getattr(obj, "student", obj)
        return user_can_view_medical(request.user, student)


class CanEditMedical(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        from apps.accounts.permissions import user_can_edit_medical

        return user_can_edit_medical(request.user)


class CanEditGrades(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        section = getattr(obj, "section", obj)
        return user_can_edit_grades(request.user, section)


class IsTeacherOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in {
            UserRole.TEACHER,
            UserRole.SCHOOL_ADMIN,
            UserRole.DISTRICT_ADMIN,
        }
