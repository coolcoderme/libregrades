from django.db import models

from apps.accounts.models import User
from apps.core.models import TimeStampedModel
from apps.students.models import StudentProfile


class IncidentType(models.TextChoices):
    POSITIVE = "positive", "Positive"
    MINOR = "minor", "Minor Infraction"
    MAJOR = "major", "Major Infraction"
    SUSPENSION = "suspension", "Suspension"


class BehaviorIncident(TimeStampedModel):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="behavior_incidents"
    )
    incident_date = models.DateField()
    incident_type = models.CharField(max_length=32, choices=IncidentType.choices)
    description = models.TextField()
    location = models.CharField(max_length=128, blank=True)
    reported_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="reported_incidents"
    )
    consequence = models.TextField(blank=True)
    parent_visible = models.BooleanField(default=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-incident_date"]

    def __str__(self):
        return f"{self.student} — {self.incident_type} ({self.incident_date})"
