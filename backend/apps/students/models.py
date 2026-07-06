from django.db import models

from apps.accounts.models import User
from apps.core.models import School, TimeStampedModel


class EnrollmentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    GRADUATED = "graduated", "Graduated"
    TRANSFERRED = "transferred", "Transferred"


class StudentProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="students")
    student_id = models.CharField(max_length=64)
    grade_level = models.PositiveSmallIntegerField(default=9)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    enrollment_status = models.CharField(
        max_length=32, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE
    )
    photo = models.ImageField(upload_to="students/photos/", blank=True, null=True)

    class Meta:
        ordering = ["student_id"]
        unique_together = [["school", "student_id"]]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.student_id})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username


class AccommodationType(models.TextChoices):
    IEP = "iep", "IEP"
    PLAN_504 = "504", "504 Plan"
    OTHER = "other", "Other"


class StudentAccommodation(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="accommodations")
    accommodation_type = models.CharField(max_length=16, choices=AccommodationType.choices, default=AccommodationType.OTHER)
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.student.student_id}: {self.title}"
