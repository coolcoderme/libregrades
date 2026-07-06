from django.db import models

from apps.accounts.models import User
from apps.core.models import TimeStampedModel


class NotificationType(models.TextChoices):
    GRADE_POSTED = "grade_posted", "Grade Posted"
    MISSING_ASSIGNMENT = "missing_assignment", "Missing Assignment"
    ATTENDANCE = "attendance", "Attendance Alert"
    BEHAVIOR = "behavior", "Behavior Incident"
    DIGEST = "digest", "Weekly Digest"
    GENERAL = "general", "General"

    ANNOUNCEMENT = "announcement", "Announcement"
    MESSAGE = "message", "Direct Message"
    CONFERENCE = "conference", "Conference Reminder"


class Notification(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=32, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.title}"


class NotificationPreference(TimeStampedModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    email_grades = models.BooleanField(default=True)
    email_missing = models.BooleanField(default=True)
    email_attendance = models.BooleanField(default=True)
    email_behavior = models.BooleanField(default=True)
    email_digest = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"Preferences for {self.user.username}"


class DeviceToken(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=512)
    platform = models.CharField(max_length=32, default="unknown")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [["user", "token"]]

    def __str__(self):
        return f"{self.user.username} — {self.platform}"
