from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import ParentProfile, UserRole
from apps.notifications.models import NotificationPreference
from apps.accounts.permissions import (
    MEDICAL_FULL,
    MEDICAL_LIMITED,
    MEDICAL_NONE,
    accessible_students,
    get_parent_profile,
    get_staff_medical_access,
    get_student_medical_access,
    get_student_profile,
    user_can_access_section,
    user_can_edit_grades,
    user_can_view_emergency_contacts,
    user_can_view_medical,
    user_can_view_student,
)
from apps.attendance.models import AttendanceRecord
from apps.behavior.models import BehaviorIncident
from apps.credits.services import build_credit_summary, generate_transcript_pdf
from apps.emergency.models import EmergencyContact
from apps.grades.models import Assignment, Grade, GradeCategory
from apps.medical.models import MedicalRecord
from apps.scheduling.models import Enrollment, Section
from apps.students.models import StudentProfile

from .forms import PortalAuthenticationForm


def _resolve_student(request, student_id=None):
    if student_id:
        student = get_object_or_404(StudentProfile, pk=student_id)
        if not user_can_view_student(request.user, student):
            return None
        return student
    if request.user.role == UserRole.STUDENT:
        return get_student_profile(request.user)
    if request.user.role == UserRole.PARENT:
        child_id = request.GET.get("child")
        profile = get_parent_profile(request.user)
        if profile and child_id:
            return profile.students.filter(pk=child_id).first()
        if profile:
            return profile.students.first()
    return None


class PortalLoginView(LoginView):
    template_name = "portal/login.html"
    authentication_form = PortalAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.get_user()
        self.request.session["2fa_verified"] = not user.totp_enabled
        return response


class PortalLogoutView(LogoutView):
    next_page = reverse_lazy("portal:login")


@login_required
def dashboard(request):
    student = _resolve_student(request)
    ctx = {"student": student, "role": request.user.role}
    if request.user.role == UserRole.TEACHER:
        ctx["sections"] = Section.objects.filter(
            teacher=request.user, term__is_current=True
        ).select_related("course")
    elif request.user.role == UserRole.PARENT:
        profile = get_parent_profile(request.user)
        ctx["children"] = profile.students.all() if profile else []
    if student:
        ctx["missing_count"] = _missing_for_student(student)
        ctx["recent_grades"] = Grade.objects.filter(student=student).order_by("-updated_at")[:5]
        ctx["credit_summary"] = build_credit_summary(student)
    return render(request, "portal/dashboard.html", ctx)


def _missing_for_student(student):
    today = timezone.localdate()
    section_ids = Enrollment.objects.filter(student=student, is_active=True).values_list(
        "section_id", flat=True
    )
    assignments = Assignment.objects.filter(
        section_id__in=section_ids, is_published=True, due_date__lt=today
    )
    count = 0
    for a in assignments:
        g = Grade.objects.filter(assignment=a, student=student).first()
        if g is None or (g.points is None and not g.is_excused):
            count += 1
    return count


@login_required
def student_grades(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    grades = Grade.objects.filter(student=student).select_related(
        "assignment__section__course"
    )
    if request.user.role in (UserRole.STUDENT, UserRole.PARENT):
        from apps.grades.services import grades_visible_to_student

        grades = grades_visible_to_student(grades)
    return render(request, "portal/grades.html", {"student": student, "grades": grades})


@login_required
def student_missing(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    today = timezone.localdate()
    section_ids = Enrollment.objects.filter(student=student, is_active=True).values_list(
        "section_id", flat=True
    )
    assignments = Assignment.objects.filter(
        section_id__in=section_ids, is_published=True, due_date__lt=today
    ).select_related("section__course")
    missing = []
    for a in assignments:
        g = Grade.objects.filter(assignment=a, student=student).first()
        if g is None or (g.points is None and not g.is_excused):
            missing.append(a)
    return render(request, "portal/missing.html", {"student": student, "missing": missing})


@login_required
def student_schedule(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    enrollments = Enrollment.objects.filter(student=student, is_active=True).select_related(
        "section__course", "section__teacher", "section__period"
    )
    return render(request, "portal/schedule.html", {"student": student, "enrollments": enrollments})


@login_required
def student_credits(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    from apps.credits.models import CreditEarned

    credits = CreditEarned.objects.filter(student=student).select_related("course")
    summary = build_credit_summary(student)
    return render(
        request,
        "portal/credits.html",
        {"student": student, "credits": credits, "summary": summary},
    )


@login_required
def student_medical(request, student_id=None):
    access = None
    if student_id:
        student = get_object_or_404(StudentProfile, pk=student_id)
        subject_user = student.user
        access = get_student_medical_access(request.user, student)
        if access == MEDICAL_NONE:
            return HttpResponseForbidden()
    elif request.user.role in (UserRole.STUDENT, UserRole.PARENT):
        student = _resolve_student(request)
        if not student:
            return HttpResponseForbidden()
        subject_user = student.user
        access = get_student_medical_access(request.user, student)
        if access == MEDICAL_NONE:
            return HttpResponseForbidden()
    else:
        student = None
        subject_user = request.user
        access = get_staff_medical_access(request.user, subject_user)
        if hasattr(subject_user, "student_profile"):
            access = get_student_medical_access(request.user, subject_user.student_profile)
        if access == MEDICAL_NONE:
            return HttpResponseForbidden()

    record, _ = MedicalRecord.objects.get_or_create(user=subject_user)
    from apps.accounts.audit import log_audit

    log_audit(
        request.user,
        "view",
        "MedicalRecord",
        subject_user.pk,
        {"student_id": student.pk if student else None},
        request,
    )
    subject_name = student.full_name if student else (subject_user.get_full_name() or subject_user.username)
    show_immunizations = access == MEDICAL_FULL
    show_sensitive = access == MEDICAL_FULL
    return render(
        request,
        "portal/medical.html",
        {
            "student": student,
            "subject_name": subject_name,
            "record": record,
            "access_level": access,
            "show_immunizations": show_immunizations,
            "show_sensitive": show_sensitive,
            "is_limited_view": access == MEDICAL_LIMITED,
            "allergies": subject_user.allergies.all(),
            "medications": subject_user.medications.all(),
            "conditions": subject_user.medical_conditions.all(),
            "immunizations": subject_user.immunizations.all() if show_immunizations else [],
        },
    )


@login_required
def student_emergency(request, student_id=None):
    if student_id:
        student = get_object_or_404(StudentProfile, pk=student_id)
        if not user_can_view_emergency_contacts(request.user, student):
            return HttpResponseForbidden()
    else:
        student = _resolve_student(request, student_id)
        if not student or not user_can_view_emergency_contacts(request.user, student):
            return HttpResponseForbidden()
    contacts = EmergencyContact.objects.filter(student=student)
    return render(request, "portal/emergency.html", {"student": student, "contacts": contacts})


@login_required
def student_behavior(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    qs = BehaviorIncident.objects.filter(student=student)
    if request.user.role in (UserRole.STUDENT, UserRole.PARENT):
        qs = qs.filter(parent_visible=True)
    return render(request, "portal/behavior.html", {"student": student, "incidents": qs})


@login_required
def student_attendance(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    records = AttendanceRecord.objects.filter(student=student).select_related("section")
    return render(request, "portal/attendance.html", {"student": student, "records": records})


@login_required
def teacher_sections(request):
    if request.user.role not in {UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.DISTRICT_ADMIN}:
        return HttpResponseForbidden()
    qs = Section.objects.filter(term__is_current=True).select_related("course")
    if request.user.role == UserRole.TEACHER:
        qs = qs.filter(teacher=request.user)
    return render(request, "portal/teacher_sections.html", {"sections": qs})


def gradebook(request, section_id):
    section = get_object_or_404(Section.objects.select_related("course", "term"), pk=section_id)
    if not user_can_access_section(request, section):
        return HttpResponseForbidden()
    students = StudentProfile.objects.filter(
        enrollments__section=section, enrollments__is_active=True
    ).distinct()
    assignments = Assignment.objects.filter(section=section).order_by("due_date")
    grades = Grade.objects.filter(assignment__section=section)
    grade_map = {(g.student_id, g.assignment_id): g for g in grades}
    rows = []
    for student in students:
        row_grades = []
        for assignment in assignments:
            g = grade_map.get((student.id, assignment.id))
            row_grades.append({"assignment": assignment, "grade": g})
        rows.append({"student": student, "grades": row_grades})
    from apps.grades.services import can_publish_grades, posting_window_open

    acc_map = {
        s.id: list(s.accommodations.filter(is_active=True))
        for s in students.prefetch_related("accommodations")
    }
    for row in rows:
        row["accommodations"] = acc_map.get(row["student"].id, [])
    return render(
        request,
        "portal/gradebook.html",
        {
            "section": section,
            "assignments": assignments,
            "rows": rows,
            "posting_open": posting_window_open(section.term),
            "can_publish": request.user.is_authenticated and can_publish_grades(request.user, section),
            "substitute_readonly": bool(request.session.get("substitute_pass_id")),
        },
    )


@login_required
@require_http_methods(["POST"])
def gradebook_update(request, section_id):
    if request.session.get("substitute_pass_id"):
        return HttpResponseForbidden("Substitutes have read-only gradebook access.")
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_edit_grades(request.user, section):
        return HttpResponseForbidden()
    student_id = request.POST.get("student_id")
    assignment_id = request.POST.get("assignment_id")
    points = request.POST.get("points")
    comment = request.POST.get("comment")
    publish = request.POST.get("publish") == "1"
    student = get_object_or_404(StudentProfile, pk=student_id)
    assignment = get_object_or_404(Assignment, pk=assignment_id, section=section)
    grade, _ = Grade.objects.get_or_create(assignment=assignment, student=student)
    if grade.pk:
        from apps.extensions.advanced_services import record_grade_undo

        record_grade_undo(grade, request.user)
    if points == "" or points is None:
        grade.points = None
    else:
        grade.points = points
    if comment is not None:
        grade.comment = comment
    from apps.grades.services import can_publish_grades

    if publish and can_publish_grades(request.user, section):
        grade.is_posted = True
        grade.posted_at = timezone.now()
    grade.save()
    from apps.notifications.tasks import notify_grade_posted

    if grade.is_posted:
        notify_grade_posted.delay(grade.id)
    if request.headers.get("HX-Request"):
        return render(
            request,
            "portal/partials/grade_cell.html",
            {"grade": grade, "assignment": assignment, "section": section},
        )
    return redirect("portal:gradebook", section_id=section_id)


def section_attendance(request, section_id):
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_access_section(request, section):
        return HttpResponseForbidden()
    students = StudentProfile.objects.filter(
        enrollments__section=section, enrollments__is_active=True
    ).distinct()
    date = request.GET.get("date", timezone.localdate().isoformat())
    records = {
        r.student_id: r
        for r in AttendanceRecord.objects.filter(section=section, date=date)
    }
    student_rows = [(s, records.get(s.id)) for s in students]
    return render(
        request,
        "portal/section_attendance.html",
        {"section": section, "student_rows": student_rows, "date": date},
    )


@require_http_methods(["POST"])
def section_attendance_submit(request, section_id):
    section = get_object_or_404(Section, pk=section_id)
    if not user_can_access_section(request, section):
        return HttpResponseForbidden()
    if request.session.get("substitute_pass_id") and not request.session.get("substitute_section_ids"):
        return HttpResponseForbidden()
    student = get_object_or_404(StudentProfile, pk=request.POST.get("student_id"))
    recorded_by = request.user if request.user.is_authenticated else None
    record, _ = AttendanceRecord.objects.update_or_create(
        student=student,
        section=section,
        date=request.POST.get("date"),
        defaults={
            "code": request.POST.get("code", "P"),
            "recorded_by": recorded_by,
        },
    )
    from apps.notifications.tasks import notify_attendance

    if record.code in ("A", "T"):
        notify_attendance.delay(record.id)
    return redirect("portal:section_attendance", section_id=section_id)


@login_required
def behavior_log(request, student_id):
    student = get_object_or_404(StudentProfile, pk=student_id)
    if request.user.role not in {
        UserRole.TEACHER,
        UserRole.COUNSELOR,
        UserRole.SCHOOL_ADMIN,
        UserRole.DISTRICT_ADMIN,
    }:
        return HttpResponseForbidden()
    if request.method == "POST":
        BehaviorIncident.objects.create(
            student=student,
            incident_date=request.POST.get("incident_date") or timezone.localdate(),
            incident_type=request.POST.get("incident_type", "minor"),
            description=request.POST.get("description", ""),
            location=request.POST.get("location", ""),
            reported_by=request.user,
            consequence=request.POST.get("consequence", ""),
            parent_visible=request.POST.get("parent_visible") == "on",
        )
        return redirect("portal:student_behavior", student_id=student.id)
    return render(request, "portal/behavior_log.html", {"student": student})


@login_required
def admin_students(request):
    if not request.user.is_admin_role and request.user.role != UserRole.COUNSELOR:
        return HttpResponseForbidden()
    q = request.GET.get("q", "")
    students = accessible_students(request.user)
    if q:
        students = students.filter(
            student_id__icontains=q
        ) | students.filter(user__last_name__icontains=q)
    return render(request, "portal/admin_students.html", {"students": students, "q": q})


@login_required
def notification_preferences(request):
    prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        prefs.email_grades = request.POST.get("email_grades") == "on"
        prefs.email_missing = request.POST.get("email_missing") == "on"
        prefs.email_attendance = request.POST.get("email_attendance") == "on"
        prefs.email_behavior = request.POST.get("email_behavior") == "on"
        prefs.email_digest = request.POST.get("email_digest") == "on"
        prefs.save()
        return redirect("portal:notification_preferences")
    return render(request, "portal/notification_preferences.html", {"prefs": prefs})


@login_required
def transcript_download(request, student_id):
    student = get_object_or_404(StudentProfile, pk=student_id)
    if not user_can_view_student(request.user, student):
        return HttpResponseForbidden()
    from django.http import HttpResponse

    pdf = generate_transcript_pdf(student)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="transcript_{student.student_id}.pdf"'
    return response


@login_required
def link_child(request):
    if request.user.role != UserRole.PARENT:
        return HttpResponseForbidden()
    message = ""
    if request.method == "POST":
        sid = request.POST.get("student_id")
        code = request.POST.get("verification_code")
        try:
            student = StudentProfile.objects.get(student_id=sid)
            if code == student.student_id[-4:]:
                profile, _ = ParentProfile.objects.get_or_create(user=request.user)
                profile.students.add(student)
                message = f"Linked to {student.full_name}."
            else:
                message = "Invalid verification code."
        except StudentProfile.DoesNotExist:
            message = "Student not found."
    return render(request, "portal/link_child.html", {"message": message})


ALLOWED_PROFILE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_PROFILE_BYTES = 5 * 1024 * 1024


@login_required
@require_http_methods(["GET", "POST"])
def profile_settings(request):
    error = None
    if request.method == "POST":
        user = request.user
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        pic = request.FILES.get("profile_picture")
        if pic:
            ext = pic.name.rsplit(".", 1)[-1].lower() if "." in pic.name else ""
            if ext not in ALLOWED_PROFILE_EXTENSIONS:
                error = "Invalid image type. Use PNG, JPG, GIF, or WebP."
            elif pic.size > MAX_PROFILE_BYTES:
                error = "Image is too large. Maximum size is 5 MB."
            else:
                if user.profile_picture:
                    user.profile_picture.delete(save=False)
                user.profile_picture = pic
        if not error:
            user.save()
            return redirect("portal:profile")
    return render(request, "portal/profile.html", {"error": error})
