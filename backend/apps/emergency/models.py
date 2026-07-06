from django.db import models

from apps.core.models import TimeStampedModel
from apps.students.models import StudentProfile


class EmergencyContact(TimeStampedModel):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="emergency_contacts"
    )
    name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=64)
    phone_primary = models.CharField(max_length=32)
    phone_secondary = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    priority = models.PositiveSmallIntegerField(default=1)
    is_authorized_pickup = models.BooleanField(default=False)

    class Meta:
        ordering = ["priority", "name"]

    def __str__(self):
        return f"{self.name} ({self.relationship})"
