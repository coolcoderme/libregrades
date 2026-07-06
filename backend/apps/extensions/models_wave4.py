"""Wave 4 models — 95 production-depth features (Tiers 1–8)."""

from decimal import Decimal

from django.db import models

from apps.accounts.models import User
from apps.core.models import District, School, Term, TimeStampedModel
from apps.grades.models import Assignment, Grade
from apps.scheduling.models import Section
from apps.students.models import StudentProfile


# ── Tier 1: Live integrations & depth (1-15) ────────────────────────────────


class ClassroomSyncJob(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="classroom_syncs")
    status = models.CharField(max_length=32, default="pending")
    rosters_synced = models.PositiveIntegerField(default=0)
    grades_pushed = models.PositiveIntegerField(default=0)
    log = models.TextField(blank=True)


class OneRosterImportRun(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="oneroster_imports")
    status = models.CharField(max_length=32, default="pending")
    records_processed = models.PositiveIntegerField(default=0)
    conflicts = models.JSONField(default=list, blank=True)


class SMSDeliveryLog(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="sms_deliveries")
    recipient = models.CharField(max_length=32)
    message = models.TextField()
    status = models.CharField(max_length=32, default="queued")
    provider_id = models.CharField(max_length=64, blank=True)


class StripePaymentTransaction(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="stripe_payments")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    purpose = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=32, default="pending")


class LDAPLoginMapping(TimeStampedModel):
    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="ldap_mapping")
    group_role_map = models.JSONField(default=dict, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)


class SSOCleverRosterSync(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="clever_syncs")
    provider = models.CharField(max_length=32, default="clever")
    status = models.CharField(max_length=32, default="pending")
    users_synced = models.PositiveIntegerField(default=0)


class TimedQuizConfig(TimeStampedModel):
    quiz = models.ForeignKey("extensions.Quiz", on_delete=models.CASCADE, related_name="timed_configs")
    time_limit_minutes = models.PositiveSmallIntegerField(default=30)
    randomize_questions = models.BooleanField(default=True)
    review_after_submit = models.BooleanField(default=True)


class ItemAnalysisDashboard(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="item_dashboards")
    quiz = models.ForeignKey("extensions.Quiz", on_delete=models.CASCADE, null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)


class GradeAnomalyWorkflow(TimeStampedModel):
    anomaly = models.ForeignKey("extensions.GradeAnomaly", on_delete=models.CASCADE, related_name="workflow")
    status = models.CharField(max_length=32, default="open")
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_notes = models.TextField(blank=True)


class AuditChainVerification(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="audit_verifications")
    verified = models.BooleanField(default=False)
    chain_length = models.PositiveIntegerField(default=0)
    report = models.JSONField(default=dict, blank=True)


class BoardPacketPDFExport(TimeStampedModel):
    packet = models.ForeignKey("extensions.BoardPacket", on_delete=models.CASCADE, related_name="pdf_exports")
    file_path = models.CharField(max_length=512, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)


class IEP504GoalTracker(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="iep504_goals")
    plan_type = models.CharField(max_length=8, default="504")
    goal_text = models.TextField()
    progress_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    linked_assignments = models.JSONField(default=list, blank=True)


class AthleticsAutoEligibilityRun(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="eligibility_runs")
    run_date = models.DateField()
    students_checked = models.PositiveIntegerField(default=0)
    ineligible_count = models.PositiveIntegerField(default=0)


class EmergencyDeliveryStatus(TimeStampedModel):
    broadcast = models.ForeignKey("extensions.EmergencyBroadcast", on_delete=models.CASCADE, related_name="deliveries")
    channel = models.CharField(max_length=32)
    sent = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)


class OfflineGradebookCache(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="offline_caches")
    payload = models.JSONField(default=dict, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)


# ── Tier 2: Grading & assessment (16-30) ────────────────────────────────────


class StandardsReportCard(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="standards_report_cards")
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    standards_scores = models.JSONField(default=dict, blank=True)
    published = models.BooleanField(default=False)


class GradeWhatIfCalculation(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="what_if_calcs")
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    target_grade = models.CharField(max_length=4, blank=True)
    score_needed = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    inputs = models.JSONField(default=dict, blank=True)


class AssignmentVersion(TimeStampedModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveSmallIntegerField(default=1)
    snapshot = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class AnonymousGradingSession(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="anon_grading_sessions")
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    alias_map = models.JSONField(default=dict, blank=True)


class CalibrationSession(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="calibration_sessions")
    title = models.CharField(max_length=255)
    sample_work = models.TextField(blank=True)
    scores = models.JSONField(default=list, blank=True)


class DistrictRubricBank(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="rubric_bank")
    name = models.CharField(max_length=255)
    criteria = models.JSONField(default=list, blank=True)
    subject = models.CharField(max_length=64, blank=True)


class RetakePolicyRule(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="retake_rules")
    max_retakes = models.PositiveSmallIntegerField(default=1)
    scoring_method = models.CharField(max_length=32, default="highest")


class CategoryWeightPreset(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="weight_presets")
    name = models.CharField(max_length=128)
    weights = models.JSONField(default=dict, blank=True)
    preset_type = models.CharField(max_length=32, default="summative")


class ScantronAutoPostJob(TimeStampedModel):
    scan = models.ForeignKey("extensions.ScantronScan", on_delete=models.CASCADE, related_name="auto_posts")
    grades_posted = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, default="pending")


class HandwritingOCRPipeline(TimeStampedModel):
    job = models.ForeignKey("extensions.OCRHandwritingJob", on_delete=models.CASCADE, related_name="pipeline_runs")
    engine = models.CharField(max_length=32, default="tesseract")
    confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)


class PortfolioExhibition(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="exhibitions")
    title = models.CharField(max_length=255)
    public_slug = models.SlugField(unique=True)
    approved = models.BooleanField(default=False)


class CompetencyBadgeEvidence(TimeStampedModel):
    badge = models.ForeignKey("extensions.SkillBadge", on_delete=models.CASCADE, related_name="evidence")
    submission = models.ForeignKey("extensions.AssignmentSubmission", on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)


class CrossSectionGradeCompare(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="cross_section_compares")
    assignment_title = models.CharField(max_length=255)
    section_stats = models.JSONField(default=dict, blank=True)


class MissingWorkEscalation(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="missing_escalations")
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    stage = models.PositiveSmallIntegerField(default=1)
    notified_at = models.DateTimeField(null=True, blank=True)


class GradeCommentTemplate(TimeStampedModel):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comment_templates")
    label = models.CharField(max_length=128)
    body = models.TextField()
    subject = models.CharField(max_length=64, blank=True)


# ── Tier 3: Student & family (31-42) ────────────────────────────────────────


class UnifiedFamilyInbox(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="family_inbox")
    thread_key = models.CharField(max_length=128)
    subject = models.CharField(max_length=255)
    preview = models.TextField(blank=True)
    unread = models.BooleanField(default=True)


class PushNotificationDevice(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="push_devices")
    platform = models.CharField(max_length=16)
    token = models.CharField(max_length=512)
    is_active = models.BooleanField(default=True)


class LiveWeeklyDigestRun(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="digest_runs")
    sent_at = models.DateTimeField(null=True, blank=True)
    children_summary = models.JSONField(default=dict, blank=True)


class WellnessCheckIn(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="wellness_checkins")
    mood_score = models.PositiveSmallIntegerField(default=3)
    notes = models.TextField(blank=True)
    flagged = models.BooleanField(default=False)


class HomeworkPlannerEntry(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="planner_entries")
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, null=True, blank=True)
    planned_date = models.DateField()
    estimated_minutes = models.PositiveSmallIntegerField(default=30)


class ConferencePrepPacket(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="conf_prep_packets")
    slot = models.ForeignKey("communications.ConferenceSlot", on_delete=models.SET_NULL, null=True, blank=True)
    pdf_generated = models.BooleanField(default=False)
    summary = models.JSONField(default=dict, blank=True)


class PortalLocaleConfig(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="locale_config")
    locale = models.CharField(max_length=8, default="en")
    rtl = models.BooleanField(default=False)


class TextToSpeechRequest(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tts_requests")
    source_text = models.TextField()
    audio_url = models.URLField(blank=True)


class StudentQuestionQueue(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="questions")
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    question = models.TextField()
    answered = models.BooleanField(default=False)
    answer = models.TextField(blank=True)


class GraduationChecklist(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="graduation_checklists")
    items = models.JSONField(default=dict, blank=True)
    percent_complete = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))


class CourseWishlistEntry(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="course_wishlist")
    course = models.ForeignKey("scheduling.Course", on_delete=models.CASCADE)
    priority = models.PositiveSmallIntegerField(default=1)
    lottery_rank = models.PositiveIntegerField(null=True, blank=True)


class SiblingScheduleView(TimeStampedModel):
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sibling_schedules")
    child_ids = models.JSONField(default=list, blank=True)
    merged_schedule = models.JSONField(default=dict, blank=True)


# ── Tier 4: Teacher workflow (43-54) ────────────────────────────────────────


class CoTeacherPermission(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="co_teacher_perms")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="co_teaching")
    can_edit = models.BooleanField(default=False)
    can_view = models.BooleanField(default=True)


class GradebookPresenceSession(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="presence_sessions")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    active_cell = models.CharField(max_length=64, blank=True)
    last_seen = models.DateTimeField(auto_now=True)


class LessonPlanLink(TimeStampedModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="lesson_links")
    plan_title = models.CharField(max_length=255)
    resources = models.JSONField(default=list, blank=True)
    standards = models.JSONField(default=list, blank=True)


class SubstituteLessonPack(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="sub_packs")
    date = models.DateField()
    pack_html = models.TextField(blank=True)
    generated_for = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class DepartmentGradeDistribution(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="dept_distributions")
    department = models.CharField(max_length=64)
    assignment_id = models.PositiveIntegerField(null=True, blank=True)
    histogram = models.JSONField(default=dict, blank=True)


class InterventionGroup(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="intervention_groups")
    standard_code = models.CharField(max_length=64, blank=True)
    student_ids = models.JSONField(default=list, blank=True)
    name = models.CharField(max_length=128)


class PLCMeetingSession(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="plc_sessions")
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    shared_data = models.JSONField(default=dict, blank=True)


class TeacherSubRequest(TimeStampedModel):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sub_requests")
    date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=32, default="pending")
    substitute = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sub_assignments")


class VoiceToTextFeedback(TimeStampedModel):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="voice_to_text_feedback")
    audio_url = models.URLField(blank=True)
    transcript = models.TextField(blank=True)


class BulkFeedbackMailMerge(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="mail_merges")
    template = models.TextField()
    sent_count = models.PositiveIntegerField(default=0)


class AssignmentCopyJob(TimeStampedModel):
    source_assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="copy_jobs")
    target_section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="copied_assignments")
    shift_dates_days = models.IntegerField(default=0)
    status = models.CharField(max_length=32, default="pending")


class GradePostingPreview(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="posting_previews")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    preview_data = models.JSONField(default=dict, blank=True)


# ── Tier 5: Analytics (55-64) ───────────────────────────────────────────────


class EarlyWarningIndex(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="ewi_scores")
    score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    factors = models.JSONField(default=dict, blank=True)
    tier = models.CharField(max_length=16, default="low")


class EquityGapReport(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="equity_gaps")
    metric = models.CharField(max_length=64)
    subgroup_data = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)


class TeacherEffectivenessSnapshot(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="teacher_effectiveness")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    growth_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    metrics = models.JSONField(default=dict, blank=True)


class EnrollmentForecast(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="enrollment_forecasts")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, null=True, blank=True)
    forecast = models.JSONField(default=dict, blank=True)


class BudgetImpactScenario(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="budget_scenarios")
    name = models.CharField(max_length=128)
    assumptions = models.JSONField(default=dict, blank=True)
    projected_fte = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)


class CustomReportBuilderDefinition(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wave4_custom_reports")
    name = models.CharField(max_length=128)
    definition = models.JSONField(default=dict, blank=True)


class ScheduledReportEmail(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scheduled_reports")
    report = models.ForeignKey(CustomReportBuilderDefinition, on_delete=models.CASCADE, null=True, blank=True)
    cron = models.CharField(max_length=64, default="0 8 * * 1")
    recipients = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)


class StateBenchmarkMapping(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="benchmark_mappings")
    state_code = models.CharField(max_length=8)
    cut_scores = models.JSONField(default=dict, blank=True)


class ClimateSurveyResponse(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="climate_surveys", null=True, blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="climate_responses")
    survey_name = models.CharField(max_length=128)
    responses = models.JSONField(default=dict, blank=True)


class AbsenceRouteHeatmap(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="route_heatmaps")
    route_name = models.CharField(max_length=128)
    absence_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    geo_data = models.JSONField(default=dict, blank=True)


# ── Tier 6: Operations & safety (65-74) ─────────────────────────────────────


class VisitorBadgePrint(TimeStampedModel):
    visit = models.ForeignKey("extensions.VisitorLog", on_delete=models.CASCADE, related_name="badges")
    qr_code = models.CharField(max_length=128, blank=True)
    printed_at = models.DateTimeField(null=True, blank=True)


class CafeteriaLowBalanceAlert(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="cafeteria_alerts")
    balance = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    alerted_at = models.DateTimeField(null=True, blank=True)


class BusGPSLocation(TimeStampedModel):
    route_name = models.CharField(max_length=128)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class CrisisReunificationRecord(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="reunifications")
    authorized_pickup = models.CharField(max_length=255)
    verified_at = models.DateTimeField(null=True, blank=True)
    incident_id = models.CharField(max_length=64, blank=True)


class ThreatAssessmentCase(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="threat_cases")
    student = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=32, default="open")
    timeline = models.JSONField(default=list, blank=True)


class MedicationAdminLog(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="med_admin_logs")
    medication = models.CharField(max_length=128)
    dose = models.CharField(max_length=64, blank=True)
    administered_at = models.DateTimeField()
    nurse = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class MaintenancePhotoTicket(TimeStampedModel):
    ticket = models.ForeignKey("extensions.MaintenanceTicket", on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="maintenance/", blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True)


class KeycardAnomalyAlert(TimeStampedModel):
    log = models.ForeignKey("extensions.KeycardAccessLog", on_delete=models.CASCADE, related_name="anomalies")
    reason = models.CharField(max_length=255)
    severity = models.CharField(max_length=16, default="medium")


class ParkingViolation(TimeStampedModel):
    permit = models.ForeignKey("extensions.ParkingPermit", on_delete=models.CASCADE, related_name="violations")
    violation_date = models.DateField()
    notes = models.TextField(blank=True)


class AfterSchoolPickupVerify(TimeStampedModel):
    enrollment = models.ForeignKey("extensions.AfterSchoolEnrollment", on_delete=models.CASCADE, related_name="pickups")
    verified_by = models.CharField(max_length=128)
    verified_at = models.DateTimeField(auto_now_add=True)


# ── Tier 7: Platform & security (75-85) ───────────────────────────────────


class PublicAPIKey(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=128)
    key_prefix = models.CharField(max_length=16)
    rate_limit = models.PositiveIntegerField(default=1000)
    is_active = models.BooleanField(default=True)


class WebhookDeliveryAttempt(TimeStampedModel):
    webhook = models.ForeignKey("extensions.WebhookEndpoint", on_delete=models.CASCADE, related_name="delivery_attempts")
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)


class PreviewAsUserSession(TimeStampedModel):
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name="preview_sessions")
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="previewed_as")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)


class FERPADataExportJob(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ferpa_exports")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=32, default="pending")
    file_path = models.CharField(max_length=512, blank=True)


class RolePermissionBinding(TimeStampedModel):
    role = models.ForeignKey("extensions.CustomRole", on_delete=models.CASCADE, related_name="bindings")
    permission_key = models.CharField(max_length=128)
    granted = models.BooleanField(default=True)


class PluginRuntimeSandbox(TimeStampedModel):
    plugin = models.ForeignKey("extensions.PluginModule", on_delete=models.CASCADE, related_name="sandbox_runs")
    hook = models.CharField(max_length=64)
    result = models.JSONField(default=dict, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)


class GraphQLSchemaConfig(TimeStampedModel):
    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="graphql_config")
    enabled = models.BooleanField(default=False)
    schema_version = models.CharField(max_length=16, default="1.0")


class MultiSchoolPrincipalDashboard(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="principal_dashboards")
    school_ids = models.JSONField(default=list, blank=True)
    widgets = models.JSONField(default=dict, blank=True)


class AuditDiffEntry(TimeStampedModel):
    audit_log = models.ForeignKey("accounts.AuditLog", on_delete=models.CASCADE, related_name="diffs")
    field_name = models.CharField(max_length=64)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)


class SessionGeoAlert(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="geo_alerts")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    location = models.CharField(max_length=128, blank=True)
    unusual = models.BooleanField(default=False)


class SecurityScorecard(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="security_scorecards")
    score = models.PositiveSmallIntegerField(default=0)
    checks = models.JSONField(default=dict, blank=True)
    assessed_at = models.DateTimeField(auto_now_add=True)


# ── Tier 8: Quality of life (86-95) ─────────────────────────────────────────


class NavbarFavoritePin(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="navbar_pins")
    label = models.CharField(max_length=64)
    url_path = models.CharField(max_length=255)
    sort_order = models.PositiveSmallIntegerField(default=0)


class RecentPageHistory(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="page_history")
    path = models.CharField(max_length=255)
    title = models.CharField(max_length=128, blank=True)


class BulkEmailFromGradebook(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="bulk_emails")
    subject = models.CharField(max_length=255)
    body = models.TextField()
    recipient_count = models.PositiveIntegerField(default=0)
    filter_missing = models.BooleanField(default=False)


class PrintViewConfig(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="print_config")
    compact = models.BooleanField(default=False)
    include_headers = models.BooleanField(default=True)


class KeyboardShortcutHelp(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="shortcut_help")
    dismissed = models.BooleanField(default=False)


class DarkModePreview(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dark_previews")
    preview_theme = models.CharField(max_length=16, default="dark")
    saved = models.BooleanField(default=False)


class DashboardWidget(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dashboard_widgets")
    widget_type = models.CharField(max_length=64)
    position = models.PositiveSmallIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)


class InAppChangelog(TimeStampedModel):
    version = models.CharField(max_length=32)
    title = models.CharField(max_length=255)
    body = models.TextField()
    published_at = models.DateField()


class ContextualHelpTooltip(TimeStampedModel):
    page_path = models.CharField(max_length=255)
    element_key = models.CharField(max_length=64)
    help_text = models.TextField()


class StaffPhotoBulkUpload(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="photo_uploads")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    photos_processed = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, default="pending")
