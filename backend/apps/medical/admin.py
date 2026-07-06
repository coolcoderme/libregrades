from django.contrib import admin

from .models import Allergy, Immunization, MedicalCondition, MedicalRecord, Medication


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "doctor_name", "doctor_phone", "insurance_provider")
    search_fields = ("user__username", "user__last_name", "user__email")
    list_filter = ("user__role",)


@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = ("user", "allergen", "severity")
    list_filter = ("severity", "user__role")


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "dosage", "frequency")
    list_filter = ("user__role",)


@admin.register(MedicalCondition)
class MedicalConditionAdmin(admin.ModelAdmin):
    list_display = ("user", "condition", "is_active")


@admin.register(Immunization)
class ImmunizationAdmin(admin.ModelAdmin):
    list_display = ("user", "vaccine", "date_administered", "dose_number")
