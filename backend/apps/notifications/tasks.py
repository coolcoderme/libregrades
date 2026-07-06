from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.notifications.models import Notification, NotificationPreference, NotificationType


def _should_email(user, pref_field):
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    return getattr(prefs, pref_field, True)


def _create_notification(user, ntype, title, message, metadata=None, email_pref=None):
    notif = Notification.objects.create(
        user=user,
        notification_type=ntype,
        title=title,
        message=message,
        metadata=metadata or {},
    )
    if email_pref and _should_email(user, email_pref) and user.email:
        send_mail(
            subject=f"[LibreGrades] {title}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        notif.email_sent = True
        notif.save(update_fields=["email_sent"])
    return notif


def _notify_student_and_parents(student, ntype, title, message, email_pref, metadata=None):
    if student.user.email:
        _create_notification(student.user, ntype, title, message, metadata, email_pref)
    for parent in student.parents.all():
        if parent.user.email:
            _create_notification(
                parent.user,
                ntype,
                f"{student.full_name}: {title}",
                message,
                metadata,
                email_pref,
            )


@shared_task
def notify_grade_posted(grade_id):
    from apps.grades.models import Grade

    try:
        grade = Grade.objects.select_related(
            "student__user", "assignment__section__course"
        ).get(pk=grade_id)
    except Grade.DoesNotExist:
        return
    course = grade.assignment.section.course.code
    title = f"Grade posted for {course}"
    message = (
        f"A grade was posted for {grade.assignment.title} in {course}: "
        f"{grade.points}/{grade.assignment.max_points} points."
    )
    _notify_student_and_parents(
        grade.student,
        NotificationType.GRADE_POSTED,
        title,
        message,
        "email_grades",
        {"grade_id": grade.id},
    )


@shared_task
def notify_attendance(record_id):
    from apps.attendance.models import AttendanceRecord

    try:
        record = AttendanceRecord.objects.select_related("student__user").get(pk=record_id)
    except AttendanceRecord.DoesNotExist:
        return
    title = f"Attendance: {record.get_code_display()}"
    message = f"Attendance recorded as {record.get_code_display()} on {record.date}."
    _notify_student_and_parents(
        record.student,
        NotificationType.ATTENDANCE,
        title,
        message,
        "email_attendance",
        {"record_id": record.id},
    )


@shared_task
def notify_behavior(incident_id):
    from apps.behavior.models import BehaviorIncident

    try:
        incident = BehaviorIncident.objects.select_related("student__user").get(pk=incident_id)
    except BehaviorIncident.DoesNotExist:
        return
    if not incident.parent_visible:
        return
    title = f"Behavior incident: {incident.get_incident_type_display()}"
    message = f"{incident.description}\nDate: {incident.incident_date}"
    _notify_student_and_parents(
        incident.student,
        NotificationType.BEHAVIOR,
        title,
        message,
        "email_behavior",
        {"incident_id": incident.id},
    )


@shared_task
def check_missing_assignments():
    from apps.grades.models import Assignment, Grade
    from apps.scheduling.models import Enrollment

    today = timezone.localdate()
    assignments = Assignment.objects.filter(is_published=True, due_date__lt=today)
    for assignment in assignments.select_related("section__course"):
        enrollments = Enrollment.objects.filter(section=assignment.section, is_active=True)
        for enrollment in enrollments.select_related("student__user"):
            student = enrollment.student
            grade = Grade.objects.filter(assignment=assignment, student=student).first()
            if grade is None or (grade.points is None and not grade.is_excused):
                if not grade:
                    grade = Grade.objects.create(
                        assignment=assignment, student=student, is_missing=True
                    )
                else:
                    grade.is_missing = True
                    grade.save(update_fields=["is_missing"])
                title = f"Missing: {assignment.title}"
                message = (
                    f"{assignment.title} in {assignment.section.course.code} "
                    f"was due {assignment.due_date} and is marked missing."
                )
                _notify_student_and_parents(
                    student,
                    NotificationType.MISSING_ASSIGNMENT,
                    title,
                    message,
                    "email_missing",
                    {"assignment_id": assignment.id},
                )


@shared_task
def send_weekly_digests():
    from apps.accounts.models import User
    from apps.grades.models import Grade

    parents = User.objects.filter(role=UserRole.PARENT, email__gt="")
    for parent in parents:
        if not _should_email(parent, "email_digest"):
            continue
        profile = getattr(parent, "parent_profile", None)
        if not profile:
            continue
        lines = []
        for student in profile.students.all():
            missing_count = Grade.objects.filter(
                student=student, is_missing=True
            ).count()
            lines.append(f"  {student.full_name}: {missing_count} missing assignment(s)")
        if not lines:
            continue
        message = "Weekly LibreGrades digest:\n" + "\n".join(lines)
        _create_notification(
            parent,
            NotificationType.DIGEST,
            "Weekly digest",
            message,
            email_pref="email_digest",
        )
