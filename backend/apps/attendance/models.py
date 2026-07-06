from django.db import models

from apps.core.models import TimeStampedModel
from apps.scheduling.models import Section
from apps.students.models import StudentProfile


class AttendanceCode(models.TextChoices):
    PRESENT = "P", "Present"
    ABSENT = "A", "Absent"
    TARDY = "T", "Tardy"
    EXCUSED = "E", "Excused"


class AttendanceRecord(TimeStampedModel):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="attendance_records"
    )
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="attendance_records", null=True, blank=True
    )
    date = models.DateField()
    code = models.CharField(max_length=2, choices=AttendanceCode.choices, default=AttendanceCode.PRESENT)
    period_number = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-date"]
        unique_together = [["student", "date", "section", "period_number"]]

    def __str__(self):
        return f"{self.student} — {self.date}: {self.code}"
