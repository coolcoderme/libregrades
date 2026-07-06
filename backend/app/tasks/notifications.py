from datetime import date

from sqlalchemy.orm import joinedload

from app.celery_app import celery
from app.email_util import send_mail
from app.extensions import db
from app.models import (
    Assignment,
    Enrollment,
    Grade,
    Notification,
    NotificationPreference,
    Section,
    StudentProfile,
    User,
)

ATTENDANCE_LABELS = {
    "P": "Present",
    "A": "Absent",
    "T": "Tardy",
    "E": "Excused",
}


def _should_email(user, pref_field):
    prefs = NotificationPreference.query.filter_by(user_id=user.id).first()
    if not prefs:
        return True
    return getattr(prefs, pref_field, True)


def _create_notification(user, ntype, title, message, metadata=None, email_pref=None):
    notif = Notification(
        user_id=user.id,
        notification_type=ntype,
        title=title,
        message=message,
        metadata_json=metadata or {},
    )
    db.session.add(notif)
    db.session.flush()
    if email_pref and _should_email(user, email_pref) and user.email:
        if send_mail(f"[LibreGrades] {title}", message, user.email):
            notif.email_sent = True
    db.session.commit()
    return notif


def _notify_student_and_parents(student, ntype, title, message, email_pref, metadata=None):
    if student.user and student.user.email:
        _create_notification(student.user, ntype, title, message, metadata, email_pref)
    for parent in student.parents:
        if parent.user and parent.user.email:
            _create_notification(
                parent.user,
                ntype,
                f"{student.full_name}: {title}",
                message,
                metadata,
                email_pref,
            )


@celery.task(name="app.tasks.notifications.notify_grade_posted")
def notify_grade_posted(grade_id):
    grade = (
        Grade.query.options(
            joinedload(Grade.student).joinedload(StudentProfile.user),
            joinedload(Grade.assignment)
            .joinedload(Assignment.section)
            .joinedload(Section.course),
        )
        .filter_by(id=grade_id)
        .first()
    )
    if not grade or not grade.assignment:
        return
    course = grade.assignment.section.course.code if grade.assignment.section else "Course"
    title = f"Grade posted for {course}"
    message = (
        f"A grade was posted for {grade.assignment.title} in {course}: "
        f"{grade.points}/{grade.assignment.max_points} points."
    )
    _notify_student_and_parents(
        grade.student,
        "grade_posted",
        title,
        message,
        "email_grades",
        {"grade_id": grade.id},
    )


@celery.task(name="app.tasks.notifications.notify_attendance")
def notify_attendance(record_id):
    from app.models import AttendanceRecord

    record = (
        AttendanceRecord.query.options(
            joinedload(AttendanceRecord.student).joinedload(StudentProfile.user)
        )
        .filter_by(id=record_id)
        .first()
    )
    if not record:
        return
    label = ATTENDANCE_LABELS.get(record.code, record.code)
    title = f"Attendance: {label}"
    message = f"Attendance recorded as {label} on {record.date}."
    _notify_student_and_parents(
        record.student,
        "attendance",
        title,
        message,
        "email_attendance",
        {"record_id": record.id},
    )


@celery.task(name="app.tasks.notifications.notify_behavior")
def notify_behavior(incident_id):
    from app.models import BehaviorIncident

    incident = (
        BehaviorIncident.query.options(
            joinedload(BehaviorIncident.student).joinedload(StudentProfile.user)
        )
        .filter_by(id=incident_id)
        .first()
    )
    if not incident or not incident.parent_visible:
        return
    title = f"Behavior incident: {incident.incident_type.replace('_', ' ').title()}"
    message = f"{incident.description}\nDate: {incident.incident_date}"
    _notify_student_and_parents(
        incident.student,
        "behavior",
        title,
        message,
        "email_behavior",
        {"incident_id": incident.id},
    )


@celery.task(name="app.tasks.notifications.check_missing_assignments")
def check_missing_assignments():
    today = date.today()
    assignments = (
        Assignment.query.options(
            joinedload(Assignment.section).joinedload(Section.course)
        )
        .filter(Assignment.is_published.is_(True), Assignment.due_date < today)
        .all()
    )
    for assignment in assignments:
        enrollments = Enrollment.query.filter_by(
            section_id=assignment.section_id, is_active=True
        ).all()
        for enrollment in enrollments:
            student = (
                StudentProfile.query.options(joinedload(StudentProfile.user))
                .filter_by(id=enrollment.student_id)
                .first()
            )
            if not student:
                continue
            grade = Grade.query.filter_by(
                assignment_id=assignment.id, student_id=student.id
            ).first()
            if grade is None or (grade.points is None and not grade.is_excused):
                if not grade:
                    grade = Grade(
                        assignment_id=assignment.id,
                        student_id=student.id,
                        is_missing=True,
                    )
                    db.session.add(grade)
                else:
                    grade.is_missing = True
                db.session.commit()
                course_code = (
                    assignment.section.course.code
                    if assignment.section and assignment.section.course
                    else "Course"
                )
                title = f"Missing: {assignment.title}"
                message = (
                    f"{assignment.title} in {course_code} "
                    f"was due {assignment.due_date} and is marked missing."
                )
                _notify_student_and_parents(
                    student,
                    "missing_assignment",
                    title,
                    message,
                    "email_missing",
                    {"assignment_id": assignment.id},
                )


@celery.task(name="app.tasks.notifications.send_weekly_digests")
def send_weekly_digests():
    parents = User.query.filter(User.role == "parent", User.email != "").all()
    for parent in parents:
        if not _should_email(parent, "email_digest"):
            continue
        profile = parent.parent_profile
        if not profile or not profile.students:
            continue
        lines = []
        for student in profile.students:
            missing_count = Grade.query.filter_by(student_id=student.id, is_missing=True).count()
            lines.append(f"  {student.full_name}: {missing_count} missing assignment(s)")
        if not lines:
            continue
        message = "Weekly LibreGrades digest:\n" + "\n".join(lines)
        _create_notification(
            parent,
            "digest",
            "Weekly digest",
            message,
            email_pref="email_digest",
        )
