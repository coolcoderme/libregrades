"""Extended feature models (features 1-39, 45-58 — excluding integrations)."""

from decimal import Decimal

from django.db import models

from apps.accounts.models import User
from apps.core.models import District, School, Term, TimeStampedModel
from apps.grades.models import Assignment, Grade, GradeCategory
from apps.scheduling.models import Course, Period, Section
from apps.students.models import StudentProfile


# ── Grading & assessment (1-10) ─────────────────────────────────────────────


class Rubric(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="rubrics")
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, null=True, blank=True, related_name="rubrics"
    )
    name = models.CharField(max_length=128)
    max_points = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("100"))

    def __str__(self):
        return self.name


class RubricCriterion(TimeStampedModel):
    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE, related_name="criteria")
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    max_points = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("10"))
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]


class RubricScore(TimeStampedModel):
    criterion = models.ForeignKey(RubricCriterion, on_delete=models.CASCADE, related_name="scores")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="rubric_scores")
    points = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = [["criterion", "student"]]


class LearningStandard(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="standards")
    code = models.CharField(max_length=32)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    subject_area = models.CharField(max_length=64, blank=True)

    class Meta:
        unique_together = [["school", "code"]]
        ordering = ["code"]


class AssignmentStandard(TimeStampedModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="standards")
    standard = models.ForeignKey(LearningStandard, on_delete=models.CASCADE, related_name="assignments")


class StudentStandardScore(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="standard_scores")
    standard = models.ForeignKey(LearningStandard, on_delete=models.CASCADE, related_name="student_scores")
    mastery_level = models.CharField(
        max_length=16,
        choices=[
            ("not_met", "Not met"),
            ("approaching", "Approaching"),
            ("met", "Met"),
            ("exceeded", "Exceeded"),
        ],
        default="not_met",
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [["student", "standard"]]


class GradeRevisionLog(TimeStampedModel):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="revisions")
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    old_points = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    new_points = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)


class LateWorkPolicy(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="late_policies")
    deduction_per_day = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10"))
    max_deduction = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("50"))
    grace_days = models.PositiveSmallIntegerField(default=0)


class AssignmentTemplate(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="assignment_templates")
    name = models.CharField(max_length=128)
    course_code = models.CharField(max_length=32, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class TemplateAssignmentItem(TimeStampedModel):
    template = models.ForeignKey(AssignmentTemplate, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=255)
    max_points = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("100"))
    category_name = models.CharField(max_length=128, default="Coursework")
    is_extra_credit = models.BooleanField(default=False)
    days_offset = models.IntegerField(default=7, help_text="Days from apply date for due date")


class OMRScanBatch(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="omr_batches")
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="omr_batches")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    image = models.ImageField(upload_to="omr/scans/", blank=True, null=True)
    status = models.CharField(max_length=32, default="pending")
    results_json = models.JSONField(default=dict, blank=True)


class PlagiarismCheckResult(TimeStampedModel):
    submission = models.ForeignKey(
        "AssignmentSubmission", on_delete=models.CASCADE, related_name="plagiarism_checks"
    )
    provider = models.CharField(max_length=64, default="internal")
    similarity_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    report_url = models.URLField(blank=True)
    status = models.CharField(max_length=32, default="queued")


# ── Student & family (11-18) ──────────────────────────────────────────────────


class StudentGoal(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="goals")
    title = models.CharField(max_length=255)
    target_value = models.CharField(max_length=64, blank=True)
    current_value = models.CharField(max_length=64, blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_complete = models.BooleanField(default=False)


class AssignmentSubmission(TimeStampedModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="submissions")
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade_override = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [["assignment", "student"]]


class SubmissionAttachment(TimeStampedModel):
    submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="submissions/%Y/%m/")
    filename = models.CharField(max_length=255, blank=True)


class PortfolioItem(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="portfolio_items")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    artifact = models.FileField(upload_to="portfolio/%Y/", blank=True, null=True)
    course_code = models.CharField(max_length=32, blank=True)
    is_public = models.BooleanField(default=False)


class UserPortalPreferences(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="portal_preferences")
    theme = models.CharField(max_length=16, default="light", choices=[("light", "Light"), ("dark", "Dark")])
    locale = models.CharField(max_length=8, default="en")
    accessibility_large_text = models.BooleanField(default=False)
    accessibility_high_contrast = models.BooleanField(default=False)
    keyboard_shortcuts_enabled = models.BooleanField(default=True)
    tour_completed = models.JSONField(default=dict, blank=True)


# ── Scheduling & operations (19-24) ───────────────────────────────────────────


class BellSchedule(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="bell_schedules")
    name = models.CharField(max_length=128)
    is_default = models.BooleanField(default=False)


class BellPeriod(TimeStampedModel):
    schedule = models.ForeignKey(BellSchedule, on_delete=models.CASCADE, related_name="periods")
    name = models.CharField(max_length=64)
    period_number = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()


class BellScheduleVariant(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="bell_variants")
    name = models.CharField(max_length=128)
    schedule = models.ForeignKey(BellSchedule, on_delete=models.CASCADE, related_name="variants")
    effective_dates = models.JSONField(default=list, blank=True)


class ResourceRoom(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="resource_rooms")
    name = models.CharField(max_length=128)
    capacity = models.PositiveSmallIntegerField(default=30)


class ResourceBooking(TimeStampedModel):
    room = models.ForeignKey(ResourceRoom, on_delete=models.CASCADE, related_name="bookings")
    booked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resource_bookings")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    purpose = models.CharField(max_length=255, blank=True)


class DailyBulletinEntry(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="bulletin_entries")
    date = models.DateField()
    title = models.CharField(max_length=255)
    body = models.TextField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class BusRoute(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="bus_routes")
    name = models.CharField(max_length=128)
    driver_name = models.CharField(max_length=128, blank=True)


class BusStop(TimeStampedModel):
    route = models.ForeignKey(BusRoute, on_delete=models.CASCADE, related_name="stops")
    name = models.CharField(max_length=128)
    pickup_time = models.TimeField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)


class StudentBusAssignment(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="bus_assignments")
    route = models.ForeignKey(BusRoute, on_delete=models.CASCADE, related_name="students")
    stop = models.ForeignKey(BusStop, on_delete=models.SET_NULL, null=True, blank=True)


class MealEligibility(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="meal_eligibility")
    program = models.CharField(max_length=32, default="free")
    effective_date = models.DateField()
    expires_date = models.DateField(null=True, blank=True)


class MasterScheduleDraft(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="schedule_drafts")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="schedule_drafts")
    name = models.CharField(max_length=128)
    data = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


# ── Attendance & behavior (25-29) ─────────────────────────────────────────────


class SchoolAttendanceSettings(TimeStampedModel):
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name="attendance_settings")
    mode = models.CharField(
        max_length=16,
        choices=[("daily", "Daily"), ("period", "Period")],
        default="period",
    )


class TruancyCase(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="truancy_cases")
    absence_count = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=32, default="open")
    counselor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class TruancyLetter(TimeStampedModel):
    case = models.ForeignKey(TruancyCase, on_delete=models.CASCADE, related_name="letters")
    sent_at = models.DateTimeField(auto_now_add=True)
    letter_type = models.CharField(max_length=64, default="warning")


class PBISPoint(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="pbis_points")
    points = models.IntegerField()
    reason = models.CharField(max_length=255)
    awarded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    category = models.CharField(max_length=64, blank=True)


class PBISReward(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="pbis_rewards")
    name = models.CharField(max_length=128)
    point_cost = models.PositiveSmallIntegerField(default=10)


class RestorativeJusticeNote(TimeStampedModel):
    incident = models.ForeignKey(
        "behavior.BehaviorIncident", on_delete=models.CASCADE, related_name="restorative_notes"
    )
    meeting_date = models.DateField()
    participants = models.TextField(blank=True)
    agreement = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)


class HallPass(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="hall_passes")
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    destination = models.CharField(max_length=128)
    issued_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)


# ── Staff & HR (30-33) ───────────────────────────────────────────────────────


class PDRecord(TimeStampedModel):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pd_records")
    title = models.CharField(max_length=255)
    hours = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1"))
    completed_date = models.DateField()
    certificate = models.FileField(upload_to="pd/", blank=True, null=True)


class SubstitutePoolMember(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="substitute_pool")
    name = models.CharField(max_length=128)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    subjects = models.CharField(max_length=255, blank=True)
    is_available = models.BooleanField(default=True)


class GradeCalibrationSnapshot(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="calibrations")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="calibrations")
    section_averages = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True)


# ── Admin, compliance & data (34-39) ──────────────────────────────────────────


class CustomReportDefinition(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="custom_reports")
    name = models.CharField(max_length=128)
    model_name = models.CharField(max_length=64)
    filters = models.JSONField(default=dict, blank=True)
    columns = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class DataRetentionPolicy(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="retention_policies")
    model_name = models.CharField(max_length=64)
    retain_years = models.PositiveSmallIntegerField(default=7)
    archive_before_delete = models.BooleanField(default=True)


class FerpaConsent(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="ferpa_consents")
    consent_type = models.CharField(max_length=64)
    granted = models.BooleanField(default=False)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes_encrypted = models.TextField(blank=True)


class StateReportTemplate(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="state_reports")
    name = models.CharField(max_length=128)
    state_code = models.CharField(max_length=8, default="CA")
    column_mapping = models.JSONField(default=dict, blank=True)


class SandboxConfig(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="sandbox_configs")
    label = models.CharField(max_length=128)
    database_url_hint = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)


class WebhookEndpoint(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="webhooks")
    url = models.URLField()
    secret = models.CharField(max_length=128, blank=True)
    events = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)


class WebhookDelivery(TimeStampedModel):
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries")
    event = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)


# ── Analytics & intervention (45-48) ─────────────────────────────────────────


class DropoutRiskAssessment(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="dropout_assessments")
    risk_score = models.DecimalField(max_digits=5, decimal_places=2)
    factors = models.JSONField(default=list, blank=True)


class InterventionPlan(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="intervention_plans")
    tier = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=255)
    goals = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    lead = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class InterventionMeeting(TimeStampedModel):
    plan = models.ForeignKey(InterventionPlan, on_delete=models.CASCADE, related_name="meetings")
    meeting_date = models.DateField()
    notes = models.TextField(blank=True)
    attendees = models.TextField(blank=True)


class CohortSnapshot(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="cohort_snapshots")
    cohort_label = models.CharField(max_length=64)
    metrics = models.JSONField(default=dict, blank=True)


class EquityMetricsSnapshot(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="equity_snapshots")
    subgroup = models.CharField(max_length=64)
    metrics = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True)


# ── Security & platform (49-53) ───────────────────────────────────────────────


class UserSessionRecord(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_records")
    session_key = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)


class AdminIPAllowlist(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="ip_allowlist")
    cidr = models.CharField(max_length=64)
    label = models.CharField(max_length=128, blank=True)


# ── Quality of life (58) ──────────────────────────────────────────────────────


class FeedbackTicket(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    server_code = models.CharField(max_length=6, blank=True)
    role = models.CharField(max_length=32, blank=True)
    message = models.TextField()
    page_url = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, default="open")


from .models_advanced import *  # noqa: F403, E402, F401
from .models_wave3 import *  # noqa: F403, E402, F401
from .models_wave4 import *  # noqa: F403, E402, F401
