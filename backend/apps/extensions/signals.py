from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.grades.models import Grade
from apps.notifications.models import Notification


@receiver(pre_save, sender=Grade)
def log_grade_revision(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Grade.objects.get(pk=instance.pk)
    except Grade.DoesNotExist:
        return
    if old.points != instance.points:
        from apps.extensions.models import GradeRevisionLog

        GradeRevisionLog.objects.create(
            grade=instance,
            old_points=old.points,
            new_points=instance.points,
            reason="auto",
        )


@receiver(pre_save, sender=Grade)
def track_grade_posted_change(sender, instance, **kwargs):
    instance._was_posted = False
    if instance.pk:
        try:
            instance._was_posted = Grade.objects.get(pk=instance.pk).is_posted
        except Grade.DoesNotExist:
            pass


@receiver(post_save, sender=Grade)
def grade_posted_notifications(sender, instance, **kwargs):
    if not instance.is_posted or getattr(instance, "_was_posted", False):
        return
    student = instance.student
    user = student.user
    Notification.objects.get_or_create(
        user=user,
        notification_type="grade_posted",
        title=f"Grade posted: {instance.assignment.title}",
        defaults={"message": f"{instance.points}/{instance.assignment.max_points}"},
    )
    from apps.extensions.webhooks import dispatch_webhook

    dispatch_webhook(
        "grade.posted",
        {
            "student_id": student.id,
            "assignment_id": instance.assignment_id,
            "points": str(instance.points) if instance.points is not None else None,
        },
    )
