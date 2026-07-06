from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib import admin

from apps.medical.models import Allergy, Immunization, MedicalCondition, Medication

from .models import AuditLog, ParentProfile, ParentStudentLink, StaffProfile, User


class AllergyInline(admin.TabularInline):
    model = Allergy
    extra = 0


class MedicationInline(admin.TabularInline):
    model = Medication
    extra = 0


class MedicalConditionInline(admin.TabularInline):
    model = MedicalCondition
    extra = 0


class ImmunizationInline(admin.TabularInline):
    model = Immunization
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "school", "is_active")
    list_filter = ("role", "school", "district")
    inlines = [AllergyInline, MedicationInline, MedicalConditionInline, ImmunizationInline]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("LibreGrades", {"fields": ("role", "district", "school", "phone")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("LibreGrades", {"fields": ("role", "district", "school", "phone")}),
    )


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "employee_id", "title")


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)
    filter_horizontal = ("students",)


@admin.register(ParentStudentLink)
class ParentStudentLinkAdmin(admin.ModelAdmin):
    list_display = ("parent", "student", "verified")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "model_name", "object_id")
    readonly_fields = ("created_at", "updated_at")
