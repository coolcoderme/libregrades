from django.db import models

from apps.core.models import District, TimeStampedModel
from apps.scheduling.models import Course
from apps.students.models import StudentProfile


class GraduationRequirement(TimeStampedModel):
    district = models.ForeignKey(
        District, on_delete=models.CASCADE, related_name="graduation_requirements"
    )
    name = models.CharField(max_length=128)
    subject_area = models.CharField(max_length=128)
    credits_required = models.DecimalField(max_digits=5, decimal_places=2)
    total_credits_required = models.DecimalField(max_digits=6, decimal_places=2, default=220)

    class Meta:
        ordering = ["subject_area"]

    def __str__(self):
        return f"{self.subject_area}: {self.credits_required} credits"


class CreditEarned(TimeStampedModel):
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="credits_earned"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="credits_awarded")
    term_name = models.CharField(max_length=64)
    school_year = models.CharField(max_length=32)
    credits = models.DecimalField(max_digits=4, decimal_places=2)
    letter_grade = models.CharField(max_length=4, blank=True)
    gpa_points = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-school_year", "course__code"]

    def __str__(self):
        return f"{self.student} — {self.course.code}: {self.credits} cr"
