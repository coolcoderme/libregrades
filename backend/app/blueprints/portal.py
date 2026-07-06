import os
from datetime import date

from flask import Blueprint, abort, current_app, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import (
    Assignment,
    AttendanceRecord,
    BehaviorIncident,
    CreditEarned,
    EmergencyContact,
    Enrollment,
    Grade,
    MedicalRecord,
    NotificationPreference,
    ParentProfile,
    Section,
    StudentProfile,
    Term,
    User,
)
from ..permissions import (
    MEDICAL_FULL,
    MEDICAL_LIMITED,
    MEDICAL_NONE,
    accessible_students,
    get_parent_profile,
    get_staff_medical_access,
    get_student_medical_access,
    get_student_profile,
    user_can_edit_grades,
    user_can_view_emergency_contacts,
    user_can_view_student,
)
from ..services import build_credit_summary, generate_transcript_pdf
from ..task_queue import queue_task
from ..tasks.notifications import notify_attendance, notify_behavior, notify_grade_posted
from ..uploads import save_profile_picture

portal_bp = Blueprint("portal", __name__)


def _resolve_student(student_id=None):
    if student_id:
        student = db.session.get(StudentProfile, student_id)
        if not student or not user_can_view_student(current_user, student):
            return None
        return student
    if current_user.role == "student":
        return get_student_profile(current_user)
    if current_user.role == "parent":
        child_id = request.args.get("child")
        profile = get_parent_profile(current_user)
        if profile and child_id:
            for s in profile.students:
                if str(s.id) == str(child_id):
                    return s
        if profile and profile.students:
            return profile.students[0]
    return None


def _missing_for_student(student):
    today = date.today()
    section_ids = [
        e.section_id
        for e in Enrollment.query.filter_by(student_id=student.id, is_active=True).all()
    ]
    if not section_ids:
        return 0
    assignments = Assignment.query.filter(
        Assignment.section_id.in_(section_ids),
        Assignment.is_published.is_(True),
        Assignment.due_date < today,
    ).all()
    count = 0
    for a in assignments:
        g = Grade.query.filter_by(assignment_id=a.id, student_id=student.id).first()
        if g is None or (g.points is None and not g.is_excused):
            count += 1
    return count


@portal_bp.route("/")
@login_required
def dashboard():
    student = _resolve_student()
    ctx = {"student": student, "role": current_user.role}
    if current_user.role == "teacher":
        ctx["sections"] = (
            Section.query.filter_by(teacher_id=current_user.id)
            .join(Term, Section.term_id == Term.id)
            .filter(Term.is_current.is_(True))
            .options(joinedload(Section.course), joinedload(Section.period))
            .all()
        )
    elif current_user.role == "parent":
        profile = get_parent_profile(current_user)
        ctx["children"] = profile.students if profile else []
    if student:
        ctx["missing_count"] = _missing_for_student(student)
        ctx["recent_grades"] = (
            Grade.query.filter_by(student_id=student.id)
            .order_by(Grade.updated_at.desc())
            .limit(5)
            .all()
        )
        ctx["credit_summary"] = build_credit_summary(student)
    return render_template("portal/dashboard.html", **ctx)


@portal_bp.route("/settings/profile/", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        if first_name:
            current_user.first_name = first_name
        if last_name:
            current_user.last_name = last_name
        file = request.files.get("profile_picture")
        if file and file.filename:
            try:
                current_user.profile_picture = save_profile_picture(current_user, file)
            except ValueError as exc:
                return render_template("portal/profile.html", error=str(exc))
        db.session.commit()
        return redirect(url_for("portal.profile"))
    return render_template("portal/profile.html")


@portal_bp.route("/grades/")
@portal_bp.route("/grades/<int:student_id>/")
@login_required
def grades(student_id=None):
    student = _resolve_student(student_id)
    if not student:
        abort(403)
    grades_list = (
        Grade.query.filter_by(student_id=student.id)
        .options(joinedload(Grade.assignment).joinedload(Assignment.section).joinedload(Section.course))
        .all()
    )
    return render_template("portal/grades.html", student=student, grades=grades_list)


@portal_bp.route("/missing/")
@portal_bp.route("/missing/<int:student_id>/")
@login_required
def missing(student_id=None):
    student = _resolve_student(student_id)
    if not student:
        abort(403)
    today = date.today()
    section_ids = [
        e.section_id
        for e in Enrollment.query.filter_by(student_id=student.id, is_active=True).all()
    ]
    assignments = (
        Assignment.query.filter(
            Assignment.section_id.in_(section_ids),
            Assignment.is_published.is_(True),
            Assignment.due_date < today,
        )
        .options(joinedload(Assignment.section).joinedload(Section.course))
        .all()
        if section_ids
        else []
    )
    missing_list = []
    for a in assignments:
        g = Grade.query.filter_by(assignment_id=a.id, student_id=student.id).first()
        if g is None or (g.points is None and not g.is_excused):
            missing_list.append(a)
    return render_template("portal/missing.html", student=student, missing=missing_list)


@portal_bp.route("/schedule/")
@portal_bp.route("/schedule/<int:student_id>/")
@login_required
def schedule(student_id=None):
    student = _resolve_student(student_id)
    if not student:
        abort(403)
    enrollments = (
        Enrollment.query.filter_by(student_id=student.id, is_active=True)
        .options(
            joinedload(Enrollment.section).joinedload(Section.course),
            joinedload(Enrollment.section).joinedload(Section.teacher),
            joinedload(Enrollment.section).joinedload(Section.period),
        )
        .all()
    )
    return render_template("portal/schedule.html", student=student, enrollments=enrollments)


@portal_bp.route("/credits/")
@portal_bp.route("/credits/<int:student_id>/")
@login_required
def credits(student_id=None):
    student = _resolve_student(student_id)
    if not student:
        abort(403)
    credits_list = (
        CreditEarned.query.filter_by(student_id=student.id)
        .options(joinedload(CreditEarned.course))
        .all()
    )
    summary = build_credit_summary(student)
    return render_template(
        "portal/credits.html", student=student, credits=credits_list, summary=summary
    )


@portal_bp.route("/medical/")
@portal_bp.route("/medical/<int:student_id>/")
@login_required
def medical(student_id=None):
    access = None
    student = None
    if student_id:
        student = db.session.get(StudentProfile, student_id)
        if not student:
            abort(404)
        subject_user = student.user
        access = get_student_medical_access(current_user, student)
        if access == MEDICAL_NONE:
            abort(403)
    elif current_user.role in ("student", "parent"):
        student = _resolve_student()
        if not student:
            abort(403)
        subject_user = student.user
        access = get_student_medical_access(current_user, student)
        if access == MEDICAL_NONE:
            abort(403)
    else:
        subject_user = current_user
        access = get_staff_medical_access(current_user, subject_user)
        if subject_user.student_profile:
            access = get_student_medical_access(current_user, subject_user.student_profile)
        if access == MEDICAL_NONE:
            abort(403)

    record = MedicalRecord.query.filter_by(user_id=subject_user.id).first()
    if not record:
        record = MedicalRecord(user_id=subject_user.id)
        db.session.add(record)
        db.session.commit()

    subject_name = student.full_name if student else subject_user.display_name
    show_immunizations = access == MEDICAL_FULL
    return render_template(
        "portal/medical.html",
        student=student,
        subject_name=subject_name,
        record=record,
        access_level=access,
        show_immunizations=show_immunizations,
        show_sensitive=show_immunizations,
        is_limited_view=access == MEDICAL_LIMITED,
        allergies=subject_user.allergies,
        medications=subject_user.medications,
        conditions=subject_user.medical_conditions,
        immunizations=subject_user.immunizations if show_immunizations else [],
    )


@portal_bp.route("/emergency/")
@portal_bp.route("/emergency/<int:student_id>/")
@login_required
def emergency(student_id=None):
    if student_id:
        student = db.session.get(StudentProfile, student_id)
        if not student or not user_can_view_emergency_contacts(current_user, student):
            abort(403)
    else:
        student = _resolve_student()
        if not student or not user_can_view_emergency_contacts(current_user, student):
            abort(403)
    contacts = EmergencyContact.query.filter_by(student_id=student.id).order_by(
        EmergencyContact.priority, EmergencyContact.name
    ).all()
    return render_template("portal/emergency.html", student=student, contacts=contacts)


@portal_bp.route("/behavior/")
@portal_bp.route("/behavior/<int:student_id>/")
@login_required
def behavior(student_id=None):
    student = _resolve_student(student_id)
    if not student:
        abort(403)
    qs = BehaviorIncident.query.filter_by(student_id=student.id)
    if current_user.role in ("student", "parent"):
        qs = qs.filter_by(parent_visible=True)
    incidents = qs.order_by(BehaviorIncident.incident_date.desc()).all()
    return render_template("portal/behavior.html", student=student, incidents=incidents)


@portal_bp.route("/attendance/")
@portal_bp.route("/attendance/<int:student_id>/")
@login_required
def attendance(student_id=None):
    student = _resolve_student(student_id)
    if not student:
        abort(403)
    records = (
        AttendanceRecord.query.filter_by(student_id=student.id)
        .options(joinedload(AttendanceRecord.section))
        .order_by(AttendanceRecord.date.desc())
        .all()
    )
    return render_template("portal/attendance.html", student=student, records=records)


@portal_bp.route("/teacher/sections/")
@login_required
def teacher_sections():
    if current_user.role not in {"teacher", "school_admin", "district_admin"}:
        abort(403)
    qs = (
        Section.query.join(Term, Section.term_id == Term.id)
        .filter(Term.is_current.is_(True))
        .options(joinedload(Section.course))
    )
    if current_user.role == "teacher":
        qs = qs.filter(Section.teacher_id == current_user.id)
    return render_template("portal/teacher_sections.html", sections=qs.all())


@portal_bp.route("/teacher/gradebook/<int:section_id>/")
@login_required
def gradebook(section_id):
    section = db.session.get(Section, section_id)
    if not section or not user_can_edit_grades(current_user, section):
        abort(403)
    students = (
        StudentProfile.query.join(Enrollment)
        .filter(Enrollment.section_id == section_id, Enrollment.is_active.is_(True))
        .distinct()
        .all()
    )
    assignments = Assignment.query.filter_by(section_id=section_id).order_by(Assignment.due_date).all()
    grades = Grade.query.join(Assignment).filter(Assignment.section_id == section_id).all()
    grade_map = {(g.student_id, g.assignment_id): g for g in grades}
    rows = []
    for student in students:
        row_grades = []
        for assignment in assignments:
            g = grade_map.get((student.id, assignment.id))
            row_grades.append({"assignment": assignment, "grade": g})
        rows.append({"student": student, "grades": row_grades})
    return render_template(
        "portal/gradebook.html",
        section=section,
        assignments=assignments,
        rows=rows,
    )


@portal_bp.route("/teacher/gradebook/<int:section_id>/update/", methods=["POST"])
@login_required
def gradebook_update(section_id):
    section = db.session.get(Section, section_id)
    if not section or not user_can_edit_grades(current_user, section):
        abort(403)
    student_id = request.form.get("student_id")
    assignment_id = request.form.get("assignment_id")
    points = request.form.get("points")
    student = db.session.get(StudentProfile, student_id)
    assignment = Assignment.query.filter_by(id=assignment_id, section_id=section_id).first()
    if not student or not assignment:
        abort(404)
    grade = Grade.query.filter_by(assignment_id=assignment.id, student_id=student.id).first()
    if not grade:
        grade = Grade(assignment_id=assignment.id, student_id=student.id)
        db.session.add(grade)
    grade.points = None if points in ("", None) else points
    db.session.commit()
    queue_task(notify_grade_posted, grade.id)
    if request.headers.get("HX-Request"):
        return render_template(
            "portal/partials/grade_cell.html",
            grade=grade,
            assignment=assignment,
            section=section,
        )
    return redirect(url_for("portal.gradebook", section_id=section_id))


@portal_bp.route("/teacher/attendance/<int:section_id>/")
@login_required
def section_attendance(section_id):
    section = db.session.get(Section, section_id)
    if not section or not user_can_edit_grades(current_user, section):
        abort(403)
    students = (
        StudentProfile.query.join(Enrollment)
        .filter(Enrollment.section_id == section_id, Enrollment.is_active.is_(True))
        .distinct()
        .all()
    )
    date_str = request.args.get("date", date.today().isoformat())
    records = {
        r.student_id: r
        for r in AttendanceRecord.query.filter_by(section_id=section_id, date=date.fromisoformat(date_str)).all()
    }
    student_rows = [(s, records.get(s.id)) for s in students]
    return render_template(
        "portal/section_attendance.html",
        section=section,
        student_rows=student_rows,
        date=date_str,
    )


@portal_bp.route("/teacher/attendance/<int:section_id>/submit/", methods=["POST"])
@login_required
def section_attendance_submit(section_id):
    section = db.session.get(Section, section_id)
    if not section or not user_can_edit_grades(current_user, section):
        abort(403)
    student = db.session.get(StudentProfile, request.form.get("student_id"))
    if not student:
        abort(404)
    record = AttendanceRecord.query.filter_by(
        student_id=student.id,
        section_id=section_id,
        date=date.fromisoformat(request.form.get("date")),
    ).first()
    if not record:
        record = AttendanceRecord(
            student_id=student.id,
            section_id=section_id,
            date=date.fromisoformat(request.form.get("date")),
        )
        db.session.add(record)
    record.code = request.form.get("code", "P")
    record.recorded_by_id = current_user.id
    db.session.commit()
    if record.code in ("A", "T"):
        queue_task(notify_attendance, record.id)
    return redirect(url_for("portal.section_attendance", section_id=section_id))


@portal_bp.route("/behavior/log/<int:student_id>/", methods=["GET", "POST"])
@login_required
def behavior_log(student_id):
    student = db.session.get(StudentProfile, student_id)
    if not student or current_user.role not in {"teacher", "counselor", "school_admin", "district_admin"}:
        abort(403)
    if request.method == "POST":
        incident = BehaviorIncident(
            student_id=student.id,
            incident_date=date.fromisoformat(request.form.get("incident_date") or date.today().isoformat()),
            incident_type=request.form.get("incident_type", "minor"),
            description=request.form.get("description", ""),
            location=request.form.get("location", ""),
            reported_by_id=current_user.id,
            consequence=request.form.get("consequence", ""),
            parent_visible=request.form.get("parent_visible") == "on",
        )
        db.session.add(incident)
        db.session.commit()
        queue_task(notify_behavior, incident.id)
        return redirect(url_for("portal.behavior", student_id=student.id))
    return render_template("portal/behavior_log.html", student=student)


@portal_bp.route("/staff/students/")
@login_required
def admin_students():
    if not current_user.is_admin_role and current_user.role != "counselor":
        abort(403)
    q = request.args.get("q", "")
    students_q = accessible_students(current_user)
    if q:
        students_q = students_q.join(User).filter(
            db.or_(
                StudentProfile.student_id.ilike(f"%{q}%"),
                User.last_name.ilike(f"%{q}%"),
            )
        )
    return render_template("portal/admin_students.html", students=students_q.all(), q=q)


@portal_bp.route("/settings/notifications/", methods=["GET", "POST"])
@login_required
def notification_preferences():
    prefs = NotificationPreference.query.filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.session.add(prefs)
        db.session.commit()
    if request.method == "POST":
        prefs.email_grades = request.form.get("email_grades") == "on"
        prefs.email_missing = request.form.get("email_missing") == "on"
        prefs.email_attendance = request.form.get("email_attendance") == "on"
        prefs.email_behavior = request.form.get("email_behavior") == "on"
        prefs.email_digest = request.form.get("email_digest") == "on"
        db.session.commit()
        return redirect(url_for("portal.notification_preferences"))
    return render_template("portal/notification_preferences.html", prefs=prefs)


@portal_bp.route("/transcript/<int:student_id>/")
@login_required
def transcript(student_id):
    student = db.session.get(StudentProfile, student_id)
    if not student or not user_can_view_student(current_user, student):
        abort(403)
    from flask import Response

    pdf = generate_transcript_pdf(student)
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="transcript_{student.student_id}.pdf"'},
    )


@portal_bp.route("/parent/link/", methods=["GET", "POST"])
@login_required
def link_child():
    if current_user.role != "parent":
        abort(403)
    message = ""
    if request.method == "POST":
        sid = request.form.get("student_id")
        code = request.form.get("verification_code")
        student = StudentProfile.query.filter_by(student_id=sid).first()
        if not student:
            message = "Student not found."
        elif code != student.student_id[-4:]:
            message = "Invalid verification code."
        else:
            profile = ParentProfile.query.filter_by(user_id=current_user.id).first()
            if not profile:
                profile = ParentProfile(user_id=current_user.id)
                db.session.add(profile)
                db.session.flush()
            if student not in profile.students:
                profile.students.append(student)
            db.session.commit()
            message = f"Linked to {student.full_name}."
    return render_template("portal/link_child.html", message=message)


media_bp = Blueprint("media", __name__)


@media_bp.route("/media/<path:filename>")
@login_required
def serve(filename):
    folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(folder, filename)
