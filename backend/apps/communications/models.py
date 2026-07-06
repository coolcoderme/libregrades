from django.db import models

from apps.accounts.models import User
from apps.core.models import School, TimeStampedModel
from apps.scheduling.models import Section
from apps.students.models import StudentProfile


class AnnouncementScope(models.TextChoices):
    DISTRICT = "district", "District-wide"
    SCHOOL = "school", "School-wide"
    SECTION = "section", "Class section"


class Announcement(TimeStampedModel):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=255)
    body = models.TextField()
    scope = models.CharField(max_length=16, choices=AnnouncementScope.choices, default=AnnouncementScope.SCHOOL)
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True, related_name="announcements")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True, related_name="announcements")
    is_published = models.BooleanField(default=True)
    publish_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class DirectMessage(TimeStampedModel):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, null=True, blank=True, related_name="messages"
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} ({self.sender.username} → {self.recipient.username})"


class ConferenceSlot(TimeStampedModel):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conference_slots")
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, null=True, blank=True, related_name="conference_slots"
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    location = models.CharField(max_length=128, blank=True)
    is_booked = models.BooleanField(default=False)
    booked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="booked_conferences"
    )
    student = models.ForeignKey(
        StudentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="conference_bookings"
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["start_at"]

    def __str__(self):
        return f"{self.teacher.get_full_name()} — {self.start_at}"
