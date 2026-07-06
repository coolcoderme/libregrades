"""Advanced feature models (wave 2: features 11-70, excluding integrations)."""

from decimal import Decimal

from django.db import models

from apps.accounts.models import User
from apps.core.models import District, School, Term, TimeStampedModel
from apps.extensions.models import AssignmentSubmission, LearningStandard
from apps.grades.models import Assignment, Grade
from apps.scheduling.models import Course, Section
from apps.students.models import StudentProfile


# ── Grading depth (11-20) ───────────────────────────────────────────────────


class RubricGridScore(TimeStampedModel):
    rubric = models.ForeignKey("extensions.Rubric", on_delete=models.CASCADE, related_name="grid_scores")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="rubric_grid_scores")
    cell_scores = models.JSONField(default=dict, blank=True)


class PeerReviewAssignment(TimeStampedModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="peer_reviews")
    reviewer = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="peer_reviews_given")
    reviewee = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="peer_reviews_received")
    feedback = models.TextField(blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_anonymous = models.BooleanField(default=True)


class Quiz(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=255)
    max_points = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("100"))
    is_published = models.BooleanField(default=False)


class QuestionBankItem(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="question_bank")
    subject = models.CharField(max_length=64, blank=True)
    prompt = models.TextField()
    question_type = models.CharField(max_length=32, default="mcq")
    choices = models.JSONField(default=list, blank=True)
    correct_answer = models.TextField(blank=True)


class QuizQuestion(TimeStampedModel):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    bank_item = models.ForeignKey(QuestionBankItem, on_delete=models.SET_NULL, null=True, blank=True)
    prompt = models.TextField()
    points = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("1"))
    sort_order = models.PositiveSmallIntegerField(default=0)


class QuizAttempt(TimeStampedModel):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="quiz_attempts")
    answers = models.JSONField(default=dict, blank=True)
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)


class ExitTicket(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="exit_tickets")
    question = models.TextField()
    session_date = models.DateField()


class ExitTicketResponse(TimeStampedModel):
    ticket = models.ForeignKey(ExitTicket, on_delete=models.CASCADE, related_name="responses")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="exit_ticket_responses")
    answer = models.TextField()


class GradeAppeal(TimeStampedModel):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="appeals")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="grade_appeals")
    reason = models.TextField()
    status = models.CharField(max_length=32, default="pending")
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_notes = models.TextField(blank=True)


class GradeModerationItem(TimeStampedModel):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="moderation_items")
    flagged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, default="pending")
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderation_approvals"
    )


class CompetencyProgress(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="competency_progress")
    standard = models.ForeignKey(LearningStandard, on_delete=models.CASCADE, related_name="competency_progress")
    progress_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))


class VoiceFeedback(TimeStampedModel):
    submission = models.ForeignKey(
        AssignmentSubmission, on_delete=models.CASCADE, null=True, blank=True, related_name="voice_feedback"
    )
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, null=True, blank=True, related_name="voice_feedback")
    audio = models.FileField(upload_to="voice_feedback/%Y/")
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class AIFeedbackDraft(TimeStampedModel):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="ai_drafts")
    draft_text = models.TextField()
    accepted = models.BooleanField(default=False)


# ── Student & family (21-30) ────────────────────────────────────────────────


class MobileAppRelease(TimeStampedModel):
    platform = models.CharField(max_length=16, choices=[("ios", "iOS"), ("android", "Android"), ("kivy", "Desktop")])
    version = models.CharField(max_length=32)
    release_notes = models.TextField(blank=True)
    download_url = models.URLField(blank=True)


class ParentDigestPreference(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="digest_preference")
    enabled = models.BooleanField(default=True)
    include_grades = models.BooleanField(default=True)
    include_attendance = models.BooleanField(default=True)
    include_due_dates = models.BooleanField(default=True)
    day_of_week = models.PositiveSmallIntegerField(default=5)


class CourseRegistrationWindow(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="registration_windows")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="registration_windows")
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()


class CourseRegistrationRequest(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="course_requests")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="registration_requests")
    rank = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=32, default="pending")


class StudentHallPassRequest(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="hall_pass_requests")
    destination = models.CharField(max_length=128)
    status = models.CharField(max_length=32, default="pending")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class SafetyTip(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="safety_tips")
    message = models.TextField()
    is_anonymous = models.BooleanField(default=True)
    status = models.CharField(max_length=32, default="new")
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class TranslatedContent(TimeStampedModel):
    source_model = models.CharField(max_length=64)
    source_id = models.CharField(max_length=64)
    locale = models.CharField(max_length=8)
    translated_text = models.TextField()


class ConferenceSelfScheduleSlot(TimeStampedModel):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="self_schedule_slots")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    booked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class DocumentSignatureRequest(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="signature_requests")
    title = models.CharField(max_length=255)
    document = models.FileField(upload_to="signatures/docs/", blank=True, null=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class AlumniTranscriptRequest(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="alumni_transcript_requests")
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    delivery_email = models.EmailField(blank=True)
    status = models.CharField(max_length=32, default="pending")


# ── Scheduling & operations (31-39) ─────────────────────────────────────────


class VisualScheduleGrid(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="visual_schedules")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="visual_schedules")
    grid_data = models.JSONField(default=dict, blank=True)


class SectionBalanceRun(TimeStampedModel):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="balance_runs")
    results = models.JSONField(default=dict, blank=True)
    run_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class SubstituteAutoAssignment(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="sub_auto_assignments")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="sub_auto_assignments")
    substitute_name = models.CharField(max_length=128)
    date = models.DateField()
    notified = models.BooleanField(default=False)


class AssetItem(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="assets")
    asset_tag = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    category = models.CharField(max_length=64, default="device")


class AssetAssignment(TimeStampedModel):
    asset = models.ForeignKey(AssetItem, on_delete=models.CASCADE, related_name="assignments")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="asset_assignments")
    assigned_at = models.DateField()
    returned_at = models.DateField(null=True, blank=True)


class MaintenanceTicket(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="maintenance_tickets")
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    location = models.CharField(max_length=128)
    description = models.TextField()
    status = models.CharField(max_length=32, default="open")
    priority = models.CharField(max_length=16, default="normal")


class SchoolEvent(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=255)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    location = models.CharField(max_length=128, blank=True)


class EventRSVP(TimeStampedModel):
    event = models.ForeignKey(SchoolEvent, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="event_rsvps")
    attending = models.BooleanField(default=True)


class FacilityUseRequest(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="facility_requests")
    requester_name = models.CharField(max_length=128)
    facility = models.CharField(max_length=128)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=32, default="pending")


class LockdownDrill(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="lockdown_drills")
    drill_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    roster_verified = models.BooleanField(default=False)


class WeatherClosureMode(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="weather_closures")
    date = models.DateField()
    is_active = models.BooleanField(default=True)
    message = models.TextField(blank=True)
    remote_attendance_rules = models.JSONField(default=dict, blank=True)


# ── Health & compliance (40-45) ───────────────────────────────────────────────


class NurseVisit(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="nurse_visits")
    visit_date = models.DateField()
    reason = models.CharField(max_length=255)
    treatment = models.TextField(blank=True)
    sent_home = models.BooleanField(default=False)
    logged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class ImmunizationComplianceFlag(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="immunization_flags")
    vaccine = models.CharField(max_length=64)
    is_compliant = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)


class SeclusionRestraintIncident(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="seclusion_incidents")
    incident_date = models.DateField()
    incident_type = models.CharField(max_length=32)
    duration_minutes = models.PositiveSmallIntegerField(default=0)
    staff_involved = models.TextField(blank=True)
    debrief_notes = models.TextField(blank=True)


class TitleIXCase(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="title_ix_cases")
    case_number = models.CharField(max_length=32, unique=True)
    status = models.CharField(max_length=32, default="open")
    investigator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    summary = models.TextField(blank=True)
    restricted = models.BooleanField(default=True)


class VolunteerClearance(TimeStampedModel):
    name = models.CharField(max_length=128)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="volunteer_clearances")
    clearance_type = models.CharField(max_length=64, default="background")
    expires_at = models.DateField()
    is_cleared = models.BooleanField(default=True)


class COPPAConsentRecord(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="coppa_consents")
    tool_name = models.CharField(max_length=128)
    parent_consented = models.BooleanField(default=False)
    consented_at = models.DateTimeField(null=True, blank=True)


# ── Staff & HR (46-50) ────────────────────────────────────────────────────────


class StaffLeaveRequest(TimeStampedModel):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name="leave_requests")
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=32, default="sick")
    status = models.CharField(max_length=32, default="pending")
    sub_plan = models.TextField(blank=True)


class StaffEvaluation(TimeStampedModel):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name="evaluations")
    evaluator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="evaluations_given")
    cycle_year = models.CharField(max_length=16)
    overall_rating = models.CharField(max_length=32, blank=True)
    goals = models.TextField(blank=True)


class EvaluationObservation(TimeStampedModel):
    evaluation = models.ForeignKey(StaffEvaluation, on_delete=models.CASCADE, related_name="observations")
    observation_date = models.DateField()
    notes = models.TextField(blank=True)
    rating = models.CharField(max_length=32, blank=True)


class StaffDirectoryEntry(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="directory_entry")
    room = models.CharField(max_length=32, blank=True)
    extension = models.CharField(max_length=16, blank=True)
    reports_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="direct_reports")


class UnionContractRule(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="union_rules")
    name = models.CharField(max_length=128)
    max_periods = models.PositiveSmallIntegerField(default=5)
    min_prep_periods = models.PositiveSmallIntegerField(default=1)
    rules_json = models.JSONField(default=dict, blank=True)


class SubstituteRating(TimeStampedModel):
    substitute_name = models.CharField(max_length=128)
    rated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    rating = models.PositiveSmallIntegerField(default=3)
    comments = models.TextField(blank=True)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True)


# ── Analytics (51-56) ─────────────────────────────────────────────────────────


class ExecutiveDashboardSnapshot(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="executive_snapshots")
    metrics = models.JSONField(default=dict, blank=True)


class StateBenchmark(TimeStampedModel):
    state_code = models.CharField(max_length=8)
    subject = models.CharField(max_length=64)
    grade_level = models.PositiveSmallIntegerField()
    proficient_pct = models.DecimalField(max_digits=5, decimal_places=2)


class ChronicAbsenteeismReport(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="chronic_absence_reports")
    report_date = models.DateField()
    heatmap_data = models.JSONField(default=dict, blank=True)


class TeacherRetentionMetric(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="retention_metrics")
    department = models.CharField(max_length=128, blank=True)
    retention_rate = models.DecimalField(max_digits=5, decimal_places=2)
    year = models.CharField(max_length=16)


class ProgramEvaluationRun(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="program_evaluations")
    program_name = models.CharField(max_length=128)
    comparison_data = models.JSONField(default=dict, blank=True)


class NLQueryLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    query_text = models.TextField()
    result_summary = models.TextField(blank=True)
    result_json = models.JSONField(default=dict, blank=True)


# ── Platform (57-64, 66, 69-70) ───────────────────────────────────────────────


class TenantOrganization(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="tenant")
    is_active = models.BooleanField(default=True)


class PluginModule(TimeStampedModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=32, default="1.0.0")
    is_enabled = models.BooleanField(default=False)


class FeatureFlag(TimeStampedModel):
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=128)
    enabled_globally = models.BooleanField(default=False)
    enabled_schools = models.ManyToManyField(School, blank=True, related_name="feature_flags")


class ABTestVariant(TimeStampedModel):
    experiment_key = models.CharField(max_length=64)
    variant_key = models.CharField(max_length=64)
    description = models.CharField(max_length=255, blank=True)
    weight = models.PositiveSmallIntegerField(default=50)


class BackupJob(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="backup_jobs")
    status = models.CharField(max_length=32, default="pending")
    file_path = models.CharField(max_length=255, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class SystemHealthMetric(TimeStampedModel):
    metric_name = models.CharField(max_length=64)
    value = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=32, blank=True)


class GradeUndoEntry(TimeStampedModel):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="undo_entries")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    previous_points = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    expires_at = models.DateTimeField()


class SeatingChart(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="seating_charts")
    name = models.CharField(max_length=128, default="Default")
    layout = models.JSONField(default=dict, blank=True)


class SectionWaitlist(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="waitlist")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="waitlists")
    position = models.PositiveSmallIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)


class TermArchive(TimeStampedModel):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="archives")
    archived_at = models.DateTimeField(auto_now_add=True)
    snapshot_path = models.CharField(max_length=255, blank=True)
    is_readonly = models.BooleanField(default=True)


class GradebookCollaborationSession(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="collab_sessions")
    active_users = models.JSONField(default=list, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
