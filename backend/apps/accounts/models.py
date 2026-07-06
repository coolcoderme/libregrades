from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import District, School, TimeStampedModel


class UserRole(models.TextChoices):
    STUDENT = "student", "Student"
    PARENT = "parent", "Parent"
    TEACHER = "teacher", "Teacher"
    COUNSELOR = "counselor", "Counselor"
    SCHOOL_ADMIN = "school_admin", "School Admin"
    DISTRICT_ADMIN = "district_admin", "District Admin"


class User(AbstractUser):
    role = models.CharField(max_length=32, choices=UserRole.choices, default=UserRole.STUDENT)
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    school = models.ForeignKey(
        School, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    phone = models.CharField(max_length=32, blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    totp_secret = models.CharField(max_length=32, blank=True)
    totp_enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ["last_name", "first_name"]

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        if self.username:
            return self.username[:2].upper()
        return "?"

    @property
    def is_staff_role(self):
        return self.role in {
            UserRole.TEACHER,
            UserRole.COUNSELOR,
            UserRole.SCHOOL_ADMIN,
            UserRole.DISTRICT_ADMIN,
        }

    @property
    def is_admin_role(self):
        return self.role in {UserRole.SCHOOL_ADMIN, UserRole.DISTRICT_ADMIN}


class StaffProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    employee_id = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=128, blank=True)
    department = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.role})"


class ParentProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="parent_profile")
    students = models.ManyToManyField(
        "students.StudentProfile",
        related_name="parents",
        blank=True,
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class ParentStudentLink(TimeStampedModel):
    """Verification record when linking parent to student."""

    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name="link_requests")
    student = models.ForeignKey(
        "students.StudentProfile", on_delete=models.CASCADE, related_name="parent_links"
    )
    verification_code = models.CharField(max_length=16)
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["parent", "student"]]


class AuditLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=64)
    model_name = models.CharField(max_length=128)
    object_id = models.CharField(max_length=64)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class SubstitutePass(TimeStampedModel):
    """One-day substitute access code for section attendance (and read-only gradebook)."""

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="substitute_passes")
    access_code = models.CharField(max_length=12, unique=True)
    valid_date = models.DateField()
    expires_at = models.DateTimeField()
    sections = models.ManyToManyField("scheduling.Section", related_name="substitute_passes")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-valid_date"]

    def __str__(self):
        return f"Sub pass {self.access_code} ({self.valid_date})"
