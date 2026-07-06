"""Portal views for features 1–14."""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.audit import log_audit
from apps.accounts.models import AuditLog, SubstitutePass, User, UserRole
from apps.accounts.permissions import accessible_students, get_parent_profile, get_student_profile
from apps.accounts.substitute import create_substitute_pass, validate_substitute_code
from apps.accounts.totp import generate_totp_secret, qr_code_base64, totp_uri, verify_totp
from apps.attendance.models import AttendanceRecord
from apps.communications.models import Announcement, AnnouncementScope, ConferenceSlot, DirectMessage
from apps.core.models import Term
from apps.grades.models import Assignment, Grade, GradePostingWindow
from apps.grades.report_card import generate_report_card_pdf
from apps.grades.services import can_publish_grades, grades_visible_to_student, posting_window_open
from apps.notifications.models import Notification
from apps.scheduling.models import Enrollment, Section
from apps.students.at_risk import at_risk_students
from apps.students.csv_io import export_grades_csv, export_students_csv, import_enrollments_csv, import_students_csv
from apps.students.models import StudentAccommodation, StudentProfile

from .views import _missing_for_student, _resolve_student


def _week_assignments(student):
    today = timezone.localdate()
    end = today + timedelta(days=7)
    section_ids = Enrollment.objects.filter(student=student, is_active=True).values_list(
        "section_id", flat=True
    )
    return (
        Assignment.objects.filter(
            section_id__in=section_ids,
            is_published=True,
            due_date__gte=today,
            due_date__lte=end,
        )
        .select_related("section__course")
        .order_by("due_date")
    )


def _announcements_for(user):
    from django.db.models import Q

    qs = Announcement.objects.filter(is_published=True).select_related("author", "section", "school")
    if user.role == UserRole.DISTRICT_ADMIN:
        return qs.order_by("-created_at")[:50]
    filters = Q(scope=AnnouncementScope.DISTRICT)
    if user.school_id:
        filters |= Q(school_id=user.school_id)
    if user.role == UserRole.TEACHER:
        section_ids = Section.objects.filter(teacher=user, term__is_current=True).values_list("id", flat=True)
        filters |= Q(section_id__in=section_ids)
    return qs.filter(filters).order_by("-created_at")[:50]


@login_required
def announcements(request):
    items = _announcements_for(request.user)
    return render(request, "portal/announcements.html", {"announcements": items})


@login_required
@require_http_methods(["GET", "POST"])
def announcement_create(request):
    if request.user.role not in {
        UserRole.TEACHER,
        UserRole.SCHOOL_ADMIN,
        UserRole.DISTRICT_ADMIN,
        UserRole.COUNSELOR,
    }:
        return HttpResponseForbidden()
    sections = Section.objects.filter(term__is_current=True)
    if request.user.role == UserRole.TEACHER:
        sections = sections.filter(teacher=request.user)
    if request.method == "POST":
        scope = request.POST.get("scope", AnnouncementScope.SCHOOL)
        section_id = request.POST.get("section_id") or None
        Announcement.objects.create(
            author=request.user,
            title=request.POST.get("title", ""),
            body=request.POST.get("body", ""),
            scope=scope,
            school=request.user.school,
            section_id=section_id if section_id else None,
        )
        return redirect("portal:announcements")
    return render(request, "portal/announcement_form.html", {"sections": sections})


@login_required
def messages_inbox(request):
    msgs = DirectMessage.objects.filter(recipient=request.user).select_related("sender", "student")[:100]
    return render(request, "portal/messages.html", {"messages": msgs, "folder": "inbox"})


@login_required
@require_http_methods(["GET", "POST"])
def message_compose(request):
    if request.user.role not in {
        UserRole.TEACHER,
        UserRole.COUNSELOR,
        UserRole.SCHOOL_ADMIN,
        UserRole.DISTRICT_ADMIN,
        UserRole.PARENT,
    }:
        return HttpResponseForbidden()
    students = accessible_students(request.user)
    if request.method == "POST":
        student = get_object_or_404(StudentProfile, pk=request.POST.get("student_id"))
        if not students.filter(pk=student.pk).exists():
            return HttpResponseForbidden()
        recipient = student.user if request.user.role != UserRole.PARENT else None
        if request.user.role == UserRole.PARENT:
            section = student.enrollments.filter(is_active=True).select_related("section__teacher").first()
            recipient = section.section.teacher if section and section.section.teacher else None
        if not recipient:
            return render(request, "portal/message_compose.html", {"students": students, "error": "No recipient."})
        DirectMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            student=student,
            subject=request.POST.get("subject", ""),
            body=request.POST.get("body", ""),
        )
        Notification.objects.create(
            user=recipient,
            notification_type="message",
            title=f"Message from {request.user.display_name}",
            message=request.POST.get("subject", "New message"),
        )
        return redirect("portal:messages")
    return render(request, "portal/message_compose.html", {"students": students})


@login_required
def due_this_week(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    upcoming = list(_week_assignments(student))
    week_start = timezone.localdate()
    week_end = week_start + timedelta(days=7)
    attendance = AttendanceRecord.objects.filter(
        student=student, date__gte=week_start, date__lte=week_end
    ).select_related("section")
    recent = grades_visible_to_student(
        Grade.objects.filter(student=student).order_by("-updated_at")[:5]
    ).select_related("assignment__section__course")
    return render(
        request,
        "portal/due_this_week.html",
        {
            "student": student,
            "upcoming": upcoming,
            "attendance": attendance,
            "recent_grades": recent,
            "missing_count": _missing_for_student(student),
        },
    )


@login_required
def report_card(request, student_id=None):
    student = _resolve_student(request, student_id)
    if not student:
        return HttpResponseForbidden()
    term = Term.objects.filter(school=student.school, is_current=True).first()
    if not term:
        return HttpResponseForbidden("No current term.")
    pdf = generate_report_card_pdf(student, term)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="report_card_{student.student_id}.pdf"'
    return response


@login_required
@require_http_methods(["GET", "POST"])
def csv_tools(request):
    if not request.user.is_admin_role and request.user.role != UserRole.COUNSELOR:
        return HttpResponseForbidden()
    result = None
    school = request.user.school or StudentProfile.objects.first().school
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "import_students" and request.FILES.get("file"):
            result = import_students_csv(request.FILES["file"], school)
        elif action == "import_enrollments" and request.FILES.get("file"):
            result = import_enrollments_csv(request.FILES["file"])
        elif action == "export_students":
            data = export_students_csv(accessible_students(request.user))
            response = HttpResponse(data, content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="students.csv"'
            return response
    return render(request, "portal/csv_tools.html", {"result": result})


@login_required
@require_http_methods(["GET", "POST"])
def notification_center(request):
    notifs = Notification.objects.filter(user=request.user).order_by("-created_at")[:100]
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect("portal:notification_center")
    return render(request, "portal/notification_center.html", {"notifications": notifs})


@login_required
@require_http_methods(["GET", "POST"])
def totp_setup(request):
    if not request.user.is_staff_role:
        return HttpResponseForbidden()
    user = request.user
    qr_b64 = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "enable":
            secret = user.totp_secret or generate_totp_secret()
            token = request.POST.get("token", "")
            if verify_totp(secret, token):
                user.totp_secret = secret
                user.totp_enabled = True
                user.save(update_fields=["totp_secret", "totp_enabled"])
                request.session["2fa_verified"] = True
                return redirect("portal:dashboard")
        elif action == "disable" and verify_totp(user.totp_secret, request.POST.get("token", "")):
            user.totp_enabled = False
            user.totp_secret = ""
            user.save(update_fields=["totp_secret", "totp_enabled"])
            return redirect("portal:totp_setup")
    if not user.totp_secret:
        user.totp_secret = generate_totp_secret()
        user.save(update_fields=["totp_secret"])
    uri = totp_uri(user, user.totp_secret)
    qr_b64 = qr_code_base64(uri)
    return render(
        request,
        "portal/totp_setup.html",
        {"qr_b64": qr_b64, "secret": user.totp_secret, "enabled": user.totp_enabled},
    )


@login_required
@require_http_methods(["GET", "POST"])
def totp_verify(request):
    if not request.user.totp_enabled:
        return redirect("portal:dashboard")
    if request.method == "POST":
        if verify_totp(request.user.totp_secret, request.POST.get("token", "")):
            request.session["2fa_verified"] = True
            return redirect(request.GET.get("next") or "portal:dashboard")
    return render(request, "portal/totp_verify.html")


@login_required
def at_risk_dashboard(request):
    if request.user.role not in {UserRole.COUNSELOR, UserRole.SCHOOL_ADMIN, UserRole.DISTRICT_ADMIN}:
        return HttpResponseForbidden()
    rows = at_risk_students(accessible_students(request.user))
    return render(request, "portal/at_risk.html", {"rows": rows})


@login_required
def conference_slots(request):
    if request.user.role == UserRole.TEACHER:
        slots = ConferenceSlot.objects.filter(teacher=request.user).select_related("student", "section")
        return render(request, "portal/conference_manage.html", {"slots": slots})
    if request.user.role == UserRole.PARENT:
        profile = get_parent_profile(request.user)
        children = profile.students.all() if profile else []
        slots = ConferenceSlot.objects.filter(is_booked=False, start_at__gte=timezone.now()).select_related(
            "teacher", "section"
        )[:100]
        return render(request, "portal/conference_book.html", {"slots": slots, "children": children})
    return HttpResponseForbidden()


@login_required
@require_http_methods(["POST"])
def conference_create(request):
    if request.user.role != UserRole.TEACHER:
        return HttpResponseForbidden()
    from django.utils.dateparse import parse_datetime

    start = parse_datetime(request.POST.get("start_at"))
    end = parse_datetime(request.POST.get("end_at"))
    if start and end:
        ConferenceSlot.objects.create(
            teacher=request.user,
            section_id=request.POST.get("section_id") or None,
            start_at=start,
            end_at=end,
            location=request.POST.get("location", ""),
        )
    return redirect("portal:conferences")


@login_required
@require_http_methods(["POST"])
def conference_book(request, slot_id):
    if request.user.role != UserRole.PARENT:
        return HttpResponseForbidden()
    slot = get_object_or_404(ConferenceSlot, pk=slot_id, is_booked=False)
    student = get_object_or_404(StudentProfile, pk=request.POST.get("student_id"))
    profile = get_parent_profile(request.user)
    if not profile or student not in profile.students.all():
        return HttpResponseForbidden()
    slot.is_booked = True
    slot.booked_by = request.user
    slot.student = student
    slot.notes = request.POST.get("notes", "")
    slot.save()
    Notification.objects.create(
        user=slot.teacher,
        notification_type="conference",
        title="Conference booked",
        message=f"{student.full_name} — {slot.start_at}",
    )
    return redirect("portal:conferences")


@login_required
@require_http_methods(["GET", "POST"])
def substitute_manage(request):
    if request.user.role not in {UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.DISTRICT_ADMIN}:
        return HttpResponseForbidden()
    passes = SubstitutePass.objects.filter(created_by=request.user).prefetch_related("sections")[:20]
    new_pass = None
    if request.method == "POST":
        section_ids = request.POST.getlist("section_ids")
        valid_date = request.POST.get("valid_date") or timezone.localdate().isoformat()
        from datetime import date

        sections = Section.objects.filter(id__in=section_ids)
        if request.user.role == UserRole.TEACHER:
            sections = sections.filter(teacher=request.user)
        new_pass = create_substitute_pass(request.user, sections, date.fromisoformat(valid_date))
    sections = Section.objects.filter(term__is_current=True)
    if request.user.role == UserRole.TEACHER:
        sections = sections.filter(teacher=request.user)
    return render(
        request,
        "portal/substitute_manage.html",
        {
            "passes": passes,
            "sections": sections,
            "new_pass": new_pass,
            "today": timezone.localdate().isoformat(),
        },
    )


@require_http_methods(["GET", "POST"])
def substitute_login(request):
    if request.method == "POST":
        p = validate_substitute_code(request.POST.get("access_code", ""))
        if p:
            request.session["substitute_pass_id"] = p.id
            request.session["substitute_section_ids"] = list(p.sections.values_list("id", flat=True))
            return redirect("portal:substitute_dashboard")
    return render(request, "portal/substitute_login.html")


@require_http_methods(["GET"])
def substitute_dashboard(request):
    if not request.session.get("substitute_pass_id"):
        return redirect("portal:substitute_login")
    sid = request.session.get("substitute_pass_id")
    p = get_object_or_404(SubstitutePass, pk=sid, is_active=True)
    sections = p.sections.select_related("course")
    return render(request, "portal/substitute_dashboard.html", {"pass_obj": p, "sections": sections})


@login_required
def audit_log_view(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    logs = AuditLog.objects.select_related("user").all()[:200]
    if request.GET.get("model"):
        logs = logs.filter(model_name=request.GET["model"])
    return render(request, "portal/audit_log.html", {"logs": logs})


@login_required
@require_http_methods(["GET", "POST"])
def accommodations_manage(request, student_id):
    student = get_object_or_404(StudentProfile, pk=student_id)
    if request.user.role not in {
        UserRole.COUNSELOR,
        UserRole.SCHOOL_ADMIN,
        UserRole.DISTRICT_ADMIN,
    }:
        return HttpResponseForbidden()
    if request.method == "POST":
        StudentAccommodation.objects.create(
            student=student,
            accommodation_type=request.POST.get("accommodation_type", "other"),
            title=request.POST.get("title", ""),
            description=request.POST.get("description", ""),
        )
        return redirect("portal:accommodations", student_id=student.id)
    items = student.accommodations.filter(is_active=True)
    return render(request, "portal/accommodations.html", {"student": student, "accommodations": items})


@login_required
@require_http_methods(["GET", "POST"])
def posting_windows(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden()
    if request.method == "POST":
        from django.utils.dateparse import parse_datetime

        term = get_object_or_404(Term, pk=request.POST.get("term_id"))
        GradePostingWindow.objects.create(
            term=term,
            name=request.POST.get("name", "Posting window"),
            opens_at=parse_datetime(request.POST.get("opens_at")),
            closes_at=parse_datetime(request.POST.get("closes_at")),
        )
        return redirect("portal:posting_windows")
    windows = GradePostingWindow.objects.select_related("term").all()
    terms = Term.objects.filter(is_current=True)
    return render(request, "portal/posting_windows.html", {"windows": windows, "terms": terms})
