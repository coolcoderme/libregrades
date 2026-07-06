"""Grade visibility and posting window helpers."""

from django.utils import timezone

from apps.grades.models import GradePostingWindow


def posting_window_open(term):
    if not term:
        return True
    now = timezone.now()
    windows = GradePostingWindow.objects.filter(term=term)
    if not windows.exists():
        return True
    return windows.filter(opens_at__lte=now, closes_at__gte=now).exists()


def grades_visible_to_student(queryset):
    return queryset.filter(is_posted=True)


def can_publish_grades(user, section):
    if user.role in ("district_admin", "school_admin"):
        return True
    return posting_window_open(section.term)
