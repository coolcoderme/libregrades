from django.db import models

from apps.accounts.models import User
from apps.core.models import School, Term, TimeStampedModel
from apps.students.models import StudentProfile


class Period(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="periods")
    name = models.CharField(max_length=64)
    period_number = models.PositiveSmallIntegerField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ["period_number"]
        unique_together = [["school", "period_number"]]

    def __str__(self):
        return self.name


class Course(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="courses")
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    credit_value = models.DecimalField(max_digits=4, decimal_places=2, default=5.0)
    is_honors = models.BooleanField(default=False)

    class Meta:
        unique_together = [["school", "code"]]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Section(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="sections")
    section_number = models.CharField(max_length=16, default="1")
    teacher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sections_taught"
    )
    period = models.ForeignKey(
        Period, on_delete=models.SET_NULL, null=True, blank=True, related_name="sections"
    )
    room = models.CharField(max_length=32, blank=True)
    max_students = models.PositiveSmallIntegerField(default=35)

    class Meta:
        unique_together = [["course", "term", "section_number"]]
        ordering = ["course__code", "section_number"]

    def __str__(self):
        return f"{self.course.code}-{self.section_number} ({self.term.name})"


class Enrollment(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="enrollments")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [["student", "section"]]
        ordering = ["section__course__code"]

    def __str__(self):
        return f"{self.student} in {self.section}"
