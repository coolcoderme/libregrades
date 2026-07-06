from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.scheduling.models import Section
from apps.students.models import StudentProfile


class GradeCategory(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="grade_categories")
    name = models.CharField(max_length=128)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("100.00"))
    drop_lowest = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name_plural = "grade categories"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.weight}%)"


class Assignment(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="assignments")
    category = models.ForeignKey(
        GradeCategory, on_delete=models.CASCADE, related_name="assignments"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    max_points = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("100"))
    is_published = models.BooleanField(default=True)
    is_extra_credit = models.BooleanField(default=False)
    accepts_submissions = models.BooleanField(default=False)

    class Meta:
        ordering = ["due_date", "title"]

    def __str__(self):
        return self.title

    @property
    def is_past_due(self):
        if not self.due_date:
            return False
        return self.due_date < timezone.localdate()


class Grade(TimeStampedModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="grades")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="grades")
    points = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    letter_grade = models.CharField(max_length=4, blank=True)
    comment = models.TextField(blank=True)
    is_excused = models.BooleanField(default=False)
    is_missing = models.BooleanField(default=False)
    is_posted = models.BooleanField(default=True, help_text="Visible to students/parents when True")
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["assignment", "student"]]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.student} — {self.assignment.title}: {self.points}"

    @property
    def percentage(self):
        if self.points is None or not self.assignment.max_points:
            return None
        return float(self.points / self.assignment.max_points * 100)

    def save(self, *args, **kwargs):
        if self.points is None and not self.is_excused and self.assignment.is_past_due:
            self.is_missing = True
        elif self.points is not None:
            self.is_missing = False
        super().save(*args, **kwargs)


class GradePostingWindow(TimeStampedModel):
    """When grades may be published to the student/parent portal."""

    term = models.ForeignKey("core.Term", on_delete=models.CASCADE, related_name="posting_windows")
    name = models.CharField(max_length=128)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()

    class Meta:
        ordering = ["-opens_at"]

    def __str__(self):
        return f"{self.name} ({self.term.name})"

    def is_open(self):
        now = timezone.now()
        return self.opens_at <= now <= self.closes_at
