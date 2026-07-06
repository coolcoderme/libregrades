"""Wave 3 feature models (74 features — integrations + deep product)."""

from decimal import Decimal

from django.db import models

from apps.accounts.models import User
from apps.core.models import District, School, Term, TimeStampedModel
from apps.grades.models import Assignment, Grade
from apps.scheduling.models import Course, Section
from apps.students.models import StudentProfile


# ── Integrations (1-10) ─────────────────────────────────────────────────────


class IntegrationConnector(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="integrations")
    provider = models.CharField(max_length=64)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)


class LDAPConfig(TimeStampedModel):
    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="ldap_config")
    server_uri = models.CharField(max_length=255)
    bind_dn = models.CharField(max_length=255, blank=True)
    user_search_base = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)


class SMSConfig(TimeStampedModel):
    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="sms_config")
    provider = models.CharField(max_length=32, default="twilio")
    from_number = models.CharField(max_length=32, blank=True)
    api_key_hint = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=False)


class SSOProviderConfig(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="sso_providers")
    provider = models.CharField(max_length=32)
    client_id = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)


class PaymentConfig(TimeStampedModel):
    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="payment_config")
    provider = models.CharField(max_length=32, default="stripe")
    public_key_hint = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=False)


class CloudStorageLink(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cloud_links")
    provider = models.CharField(max_length=32)
    file_id = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255, blank=True)


class MigrationJob(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="migration_jobs")
    source_system = models.CharField(max_length=64)
    status = models.CharField(max_length=32, default="pending")
    log = models.TextField(blank=True)


class ChatBotConfig(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="chatbots")
    platform = models.CharField(max_length=32)
    webhook_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=False)


class SyncJob(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="sync_jobs")
    job_type = models.CharField(max_length=64, default="nightly")
    status = models.CharField(max_length=32, default="pending")
    records_processed = models.PositiveIntegerField(default=0)


# ── Deepen scaffolds (11-20) ──────────────────────────────────────────────────


class QuizPlayerSession(TimeStampedModel):
    quiz = models.ForeignKey("extensions.Quiz", on_delete=models.CASCADE, related_name="player_sessions")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="quiz_sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    answers = models.JSONField(default=dict, blank=True)


class SavedNLReport(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_nl_reports")
    name = models.CharField(max_length=128)
    query_text = models.TextField()
    result_snapshot = models.JSONField(default=dict, blank=True)


class PluginSDKModule(TimeStampedModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=128)
    hook_points = models.JSONField(default=list, blank=True)
    documentation = models.TextField(blank=True)


class NativeAppBuild(TimeStampedModel):
    platform = models.CharField(max_length=16)
    version = models.CharField(max_length=32)
    build_number = models.PositiveIntegerField(default=1)
    release_notes = models.TextField(blank=True)


class CourseRegistrationWizardState(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="registration_wizard")
    step = models.PositiveSmallIntegerField(default=1)
    selections = models.JSONField(default=dict, blank=True)


# ── AI & automation (21-28) ─────────────────────────────────────────────────


class AIMissingNudge(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="ai_nudges")
    message = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


class AIReportNarrative(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="ai_narratives")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="ai_narratives")
    narrative = models.TextField()
    accepted = models.BooleanField(default=False)


class AIAccommodationHint(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="ai_accommodation_hints")
    suggestion = models.TextField()
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.5"))
    reviewed = models.BooleanField(default=False)


class SmartSubMatch(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="sub_matches")
    date = models.DateField()
    substitute_name = models.CharField(max_length=128)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))


class GradeAnomaly(TimeStampedModel):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="anomalies")
    reason = models.CharField(max_length=255)
    severity = models.CharField(max_length=16, default="medium")
    resolved = models.BooleanField(default=False)


class HelpChatLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    question = models.TextField()
    answer = models.TextField(blank=True)


class OCRHandwritingJob(TimeStampedModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="ocr_jobs")
    image = models.ImageField(upload_to="ocr/handwriting/", blank=True, null=True)
    extracted_text = models.TextField(blank=True)
    status = models.CharField(max_length=32, default="pending")


class ProjectGroup(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="project_groups")
    name = models.CharField(max_length=128)
    member_ids = models.JSONField(default=list, blank=True)


# ── Communication (29-35) ─────────────────────────────────────────────────────


class ClassFeedPost(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="feed_posts")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    media_url = models.URLField(blank=True)


class VideoAnnouncement(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="video_announcements")
    title = models.CharField(max_length=255)
    video_url = models.URLField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class LiveTranslation(TimeStampedModel):
    source_model = models.CharField(max_length=64)
    source_id = models.CharField(max_length=64)
    source_locale = models.CharField(max_length=8, default="en")
    target_locale = models.CharField(max_length=8)
    translated_text = models.TextField()


class EmergencyBroadcast(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="emergency_broadcasts")
    message = models.TextField()
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    recipient_count = models.PositiveIntegerField(default=0)
    channels = models.JSONField(default=list, blank=True)


class OfficeHoursSlot(TimeStampedModel):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="office_hours")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL, null=True, blank=True)


class NewsletterCampaign(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="newsletters")
    subject = models.CharField(max_length=255)
    body_html = models.TextField(blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)


class AlumniProfile(TimeStampedModel):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name="alumni_profile")
    graduation_year = models.CharField(max_length=16)
    current_email = models.EmailField(blank=True)
    opt_in_updates = models.BooleanField(default=True)


# ── Assessment (36-42) ────────────────────────────────────────────────────────


class CommonAssessment(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="common_assessments")
    title = models.CharField(max_length=255)
    course_code = models.CharField(max_length=32)
    admin_date = models.DateField(null=True, blank=True)


class GrowthMeasure(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="growth_measures")
    subject = models.CharField(max_length=64)
    prior_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    current_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    sgp = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)


class PortfolioDefenseSlot(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="defense_slots")
    scheduled_at = models.DateTimeField()
    panel_notes = models.TextField(blank=True)


class SkillBadge(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="skill_badges")
    skill_name = models.CharField(max_length=128)
    level = models.CharField(max_length=32, default="bronze")
    awarded_at = models.DateField()


class CurriculumMapUnit(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="curriculum_units")
    course_code = models.CharField(max_length=32)
    unit_title = models.CharField(max_length=255)
    standards = models.JSONField(default=list, blank=True)
    week_start = models.PositiveSmallIntegerField(default=1)


class ItemAnalysisReport(TimeStampedModel):
    quiz = models.ForeignKey("extensions.Quiz", on_delete=models.CASCADE, related_name="item_analyses")
    question_id = models.PositiveIntegerField()
    miss_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))


class ScantronScan(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="scantron_scans")
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="scantron_scans")
    image = models.ImageField(upload_to="scantron/", blank=True, null=True)
    parsed_answers = models.JSONField(default=dict, blank=True)


# ── Operations (43-49) ────────────────────────────────────────────────────────


class CafeteriaTransaction(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="cafeteria_tx")
    amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    meal_type = models.CharField(max_length=32, default="lunch")


class VisitorLog(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="visitor_logs")
    name = models.CharField(max_length=128)
    purpose = models.CharField(max_length=255, blank=True)
    check_in = models.DateTimeField(auto_now_add=True)
    check_out = models.DateTimeField(null=True, blank=True)


class KeycardAccessLog(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="keycard_logs")
    user_name = models.CharField(max_length=128)
    door = models.CharField(max_length=64)
    accessed_at = models.DateTimeField(auto_now_add=True)


class ParkingPermit(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="parking_permits")
    plate_number = models.CharField(max_length=16)
    permit_number = models.CharField(max_length=32)
    expires_at = models.DateField(null=True, blank=True)


class AthleticsEligibility(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="athletics_eligibility")
    sport = models.CharField(max_length=64)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    is_eligible = models.BooleanField(default=True)
    checked_at = models.DateField()


class LibraryCheckout(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="library_checkouts")
    title = models.CharField(max_length=255)
    due_date = models.DateField()
    returned_at = models.DateField(null=True, blank=True)


class AfterSchoolEnrollment(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="afterschool_enrollments")
    program_name = models.CharField(max_length=128)
    day_of_week = models.CharField(max_length=16, blank=True)
    authorized_pickup = models.TextField(blank=True)


# ── Finance (50-54) ─────────────────────────────────────────────────────────


class PurchaseRequest(TimeStampedModel):
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="purchase_requests")
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=32, default="pending")


class GrantRecord(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="grants")
    name = models.CharField(max_length=255)
    grant_type = models.CharField(max_length=64, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    deadline = models.DateField(null=True, blank=True)


class TimeClockEntry(TimeStampedModel):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name="time_clock_entries")
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(null=True, blank=True)


class VendorContract(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="vendor_contracts")
    vendor_name = models.CharField(max_length=255)
    expires_at = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)


class WorkersCompIncident(TimeStampedModel):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workers_comp_incidents")
    incident_date = models.DateField()
    description = models.TextField()
    status = models.CharField(max_length=32, default="open")


# ── Compliance (55-60) ──────────────────────────────────────────────────────


class McKinneyVentoRecord(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="mckinney_vento")
    liaison = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    housing_status = models.CharField(max_length=64, blank=True)
    transportation_notes = models.TextField(blank=True)


class Plan504(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="plans_504")
    effective_date = models.DateField()
    review_date = models.DateField(null=True, blank=True)
    accommodations = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)


class IEPPlan(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="iep_plans")
    effective_date = models.DateField()
    goals = models.TextField(blank=True)
    services = models.TextField(blank=True)
    next_meeting = models.DateField(null=True, blank=True)


class DisciplineHearing(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="discipline_hearings")
    hearing_date = models.DateField()
    hearing_type = models.CharField(max_length=64, blank=True)
    outcome = models.TextField(blank=True)


class PrivacyRequest(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="privacy_requests")
    request_type = models.CharField(max_length=32)
    status = models.CharField(max_length=32, default="pending")
    completed_at = models.DateTimeField(null=True, blank=True)


class BoardPacket(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="board_packets")
    meeting_date = models.DateField()
    title = models.CharField(max_length=255)
    content_html = models.TextField(blank=True)


# ── Platform (61-68) ────────────────────────────────────────────────────────


class RegionConfig(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="regions")
    region_code = models.CharField(max_length=16)
    data_residency = models.CharField(max_length=32, default="us")


class CacheConfig(TimeStampedModel):
    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="cache_config")
    redis_url_hint = models.CharField(max_length=255, blank=True)
    read_replica_hint = models.CharField(max_length=255, blank=True)
    enabled = models.BooleanField(default=False)


class ImmutableAuditEntry(TimeStampedModel):
    payload_hash = models.CharField(max_length=64)
    previous_hash = models.CharField(max_length=64, blank=True)
    event_type = models.CharField(max_length=64)
    data = models.JSONField(default=dict, blank=True)


class SandboxCloneJob(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="clone_jobs")
    status = models.CharField(max_length=32, default="pending")
    target_db_hint = models.CharField(max_length=255, blank=True)


class StatusPageConfig(TimeStampedModel):
    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="status_page")
    public_url = models.URLField(blank=True)
    is_public = models.BooleanField(default=False)


class CustomRole(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="custom_roles")
    name = models.CharField(max_length=128)
    permissions = models.JSONField(default=dict, blank=True)


class WhiteLabelTheme(TimeStampedModel):
    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="white_label")
    logo_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=7, default="#0d6efd")
    custom_domain = models.CharField(max_length=255, blank=True)


# ── Quality of life (69-74) ───────────────────────────────────────────────────


class BulkActionLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bulk_actions")
    action = models.CharField(max_length=64)
    target_count = models.PositiveIntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)


class UserFavorite(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    label = models.CharField(max_length=128)
    url_path = models.CharField(max_length=255)


class SplitViewPreference(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="split_view_pref")
    show_student_panel = models.BooleanField(default=True)


class PWAInstallConfig(TimeStampedModel):
    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="pwa_config")
    manifest_name = models.CharField(max_length=128, default="LibreGrades")
    theme_color = models.CharField(max_length=7, default="#0d6efd")
    offline_enabled = models.BooleanField(default=True)


class AccessibilityAuditRun(TimeStampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="a11y_audits")
    page_path = models.CharField(max_length=255)
    issues_found = models.PositiveSmallIntegerField(default=0)
    report = models.JSONField(default=dict, blank=True)


class OnboardingChecklist(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="onboarding_checklists")
    role = models.CharField(max_length=32)
    steps_completed = models.JSONField(default=dict, blank=True)
    is_complete = models.BooleanField(default=False)
