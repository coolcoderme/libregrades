"""Celery tasks for advanced features."""

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

User = get_user_model()


@shared_task
def send_weekly_parent_digests():
    from apps.accounts.models import UserRole
    from apps.extensions.models_advanced import ParentDigestPreference
    from apps.grades.models import Grade
    from apps.students.models import StudentProfile

    prefs = ParentDigestPreference.objects.filter(enabled=True)
    for pref in prefs:
        user = pref.user
        if user.role != UserRole.PARENT:
            continue
        profile = getattr(user, "parent_profile", None)
        if not profile:
            continue
        lines = ["Weekly digest from LibreGrades", ""]
        for child in profile.students.all():
            missing = Grade.objects.filter(student=child, is_missing=True).count()
            lines.append(f"{child.full_name}: {missing} missing assignments")
        if pref.include_grades:
            lines.append("")
            lines.append("Recent grades posted — log in to view details.")
        send_mail(
            "LibreGrades weekly digest",
            "\n".join(lines),
            None,
            [user.email],
            fail_silently=True,
        )


@shared_task
def run_scheduled_backup(district_id: int):
    from apps.core.models import District
    from apps.extensions.models_advanced import BackupJob

    district = District.objects.get(pk=district_id)
    job = BackupJob.objects.create(district=district, status="running")
    job.status = "completed"
    job.file_path = f"backups/{district.code}_{timezone.now():%Y%m%d}.sql.gz"
    job.completed_at = timezone.now()
    job.save()
