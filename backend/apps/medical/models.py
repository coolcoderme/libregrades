from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class MedicalRecord(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="medical_record",
    )
    doctor_name = models.CharField(max_length=255, blank=True)
    doctor_phone = models.CharField(max_length=32, blank=True)
    insurance_provider = models.CharField(max_length=255, blank=True)
    insurance_policy = models.CharField(max_length=128, blank=True)
    nurse_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Medical record — {self.user.get_full_name() or self.user.username}"


class Allergy(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="allergies"
    )
    allergen = models.CharField(max_length=255)
    severity = models.CharField(max_length=64, blank=True)
    reaction = models.TextField(blank=True)

    def __str__(self):
        return f"{self.allergen} ({self.user.username})"


class Medication(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="medications"
    )
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=128, blank=True)
    frequency = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)


class MedicalCondition(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="medical_conditions"
    )
    condition = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)


class Immunization(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="immunizations"
    )
    vaccine = models.CharField(max_length=255)
    date_administered = models.DateField(null=True, blank=True)
    dose_number = models.PositiveSmallIntegerField(default=1)
