"""SQLAlchemy models for LibreGrades (Flask)."""

from datetime import date, datetime, timezone
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

parent_students = db.Table(
    "parent_students",
    db.Column("parent_id", db.Integer, db.ForeignKey("parent_profiles.id"), primary_key=True),
    db.Column("student_id", db.Integer, db.ForeignKey("student_profiles.id"), primary_key=True),
)


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)


class District(db.Model, TimestampMixin):
    __tablename__ = "districts"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(32), unique=True, nullable=False)
    address = db.Column(db.Text, default="")
    phone = db.Column(db.String(32), default="")
    schools = db.relationship("School", back_populates="district")
    users = db.relationship("User", back_populates="district")


class School(db.Model, TimestampMixin):
    __tablename__ = "schools"
    id = db.Column(db.Integer, primary_key=True)
    district_id = db.Column(db.Integer, db.ForeignKey("districts.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(32), nullable=False)
    address = db.Column(db.Text, default="")
    phone = db.Column(db.String(32), default="")
    district = db.relationship("District", back_populates="schools")
    users = db.relationship("User", back_populates="school")
    students = db.relationship("StudentProfile", back_populates="school")
    terms = db.relationship("Term", back_populates="school")
    periods = db.relationship("Period", back_populates="school")
    courses = db.relationship("Course", back_populates="school")

    __table_args__ = (db.UniqueConstraint("district_id", "code"),)


class AcademicYear(db.Model, TimestampMixin):
    __tablename__ = "academic_years"
    id = db.Column(db.Integer, primary_key=True)
    district_id = db.Column(db.Integer, db.ForeignKey("districts.id"), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False)


class Term(db.Model, TimestampMixin):
    __tablename__ = "terms"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=True)
    name = db.Column(db.String(64), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False)
    school = db.relationship("School", back_populates="terms")
    sections = db.relationship("Section", back_populates="term")


class User(UserMixin, db.Model, TimestampMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), default="")
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(150), default="")
    last_name = db.Column(db.String(150), default="")
    role = db.Column(db.String(32), default="student")
    district_id = db.Column(db.Integer, db.ForeignKey("districts.id"), nullable=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=True)
    phone = db.Column(db.String(32), default="")
    profile_picture = db.Column(db.String(512), nullable=True)

    district = db.relationship("District", back_populates="users")
    school = db.relationship("School", back_populates="users")
    staff_profile = db.relationship("StaffProfile", back_populates="user", uselist=False)
    parent_profile = db.relationship("ParentProfile", back_populates="user", uselist=False)
    student_profile = db.relationship("StudentProfile", back_populates="user", uselist=False)
    medical_record = db.relationship("MedicalRecord", back_populates="user", uselist=False)
    allergies = db.relationship("Allergy", back_populates="user")
    medications = db.relationship("Medication", back_populates="user")
    medical_conditions = db.relationship("MedicalCondition", back_populates="user")
    immunizations = db.relationship("Immunization", back_populates="user")
    notifications = db.relationship("Notification", back_populates="user")
    notification_preferences = db.relationship(
        "NotificationPreference", back_populates="user", uselist=False
    )
    sections_taught = db.relationship("Section", back_populates="teacher")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        if self.username:
            return self.username[:2].upper()
        return "?"

    @property
    def is_staff_role(self):
        return self.role in {"teacher", "counselor", "school_admin", "district_admin"}

    @property
    def is_admin_role(self):
        return self.role in {"school_admin", "district_admin"}


class StaffProfile(db.Model, TimestampMixin):
    __tablename__ = "staff_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    employee_id = db.Column(db.String(64), default="")
    title = db.Column(db.String(128), default="")
    department = db.Column(db.String(128), default="")
    user = db.relationship("User", back_populates="staff_profile")


class ParentProfile(db.Model, TimestampMixin):
    __tablename__ = "parent_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    user = db.relationship("User", back_populates="parent_profile")
    students = db.relationship("StudentProfile", secondary=parent_students, back_populates="parents")


class StudentProfile(db.Model, TimestampMixin):
    __tablename__ = "student_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    student_id = db.Column(db.String(64), nullable=False)
    grade_level = db.Column(db.Integer, default=9)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(32), default="")
    address = db.Column(db.Text, default="")
    enrollment_status = db.Column(db.String(32), default="active")
    photo = db.Column(db.String(512), nullable=True)

    user = db.relationship("User", back_populates="student_profile")
    school = db.relationship("School", back_populates="students")
    parents = db.relationship("ParentProfile", secondary=parent_students, back_populates="students")
    enrollments = db.relationship("Enrollment", back_populates="student")
    grades = db.relationship("Grade", back_populates="student")
    attendance_records = db.relationship("AttendanceRecord", back_populates="student")
    behavior_incidents = db.relationship("BehaviorIncident", back_populates="student")
    emergency_contacts = db.relationship("EmergencyContact", back_populates="student")
    credits_earned = db.relationship("CreditEarned", back_populates="student")

    __table_args__ = (db.UniqueConstraint("school_id", "student_id"),)

    @property
    def full_name(self):
        return self.user.display_name if self.user else self.student_id


class Period(db.Model, TimestampMixin):
    __tablename__ = "periods"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    period_number = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    school = db.relationship("School", back_populates="periods")
    sections = db.relationship("Section", back_populates="period")

    __table_args__ = (db.UniqueConstraint("school_id", "period_number"),)


class Course(db.Model, TimestampMixin):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    code = db.Column(db.String(32), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    credit_value = db.Column(db.Numeric(4, 2), default=Decimal("5.0"))
    is_honors = db.Column(db.Boolean, default=False)
    school = db.relationship("School", back_populates="courses")
    sections = db.relationship("Section", back_populates="course")

    __table_args__ = (db.UniqueConstraint("school_id", "code"),)


class Section(db.Model, TimestampMixin):
    __tablename__ = "sections"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey("terms.id"), nullable=False)
    section_number = db.Column(db.String(16), default="1")
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    period_id = db.Column(db.Integer, db.ForeignKey("periods.id"), nullable=True)
    room = db.Column(db.String(32), default="")
    max_students = db.Column(db.Integer, default=35)

    course = db.relationship("Course", back_populates="sections")
    term = db.relationship("Term", back_populates="sections")
    teacher = db.relationship("User", back_populates="sections_taught")
    period = db.relationship("Period", back_populates="sections")
    enrollments = db.relationship("Enrollment", back_populates="section")
    assignments = db.relationship("Assignment", back_populates="section")
    grade_categories = db.relationship("GradeCategory", back_populates="section")
    attendance_records = db.relationship("AttendanceRecord", back_populates="section")

    __table_args__ = (db.UniqueConstraint("course_id", "term_id", "section_number"),)


class Enrollment(db.Model, TimestampMixin):
    __tablename__ = "enrollments"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    enrolled_at = db.Column(db.Date, default=date.today)
    is_active = db.Column(db.Boolean, default=True)
    student = db.relationship("StudentProfile", back_populates="enrollments")
    section = db.relationship("Section", back_populates="enrollments")

    __table_args__ = (db.UniqueConstraint("student_id", "section_id"),)


class GradeCategory(db.Model, TimestampMixin):
    __tablename__ = "grade_categories"
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    weight = db.Column(db.Numeric(5, 2), default=Decimal("100.00"))
    drop_lowest = db.Column(db.Integer, default=0)
    section = db.relationship("Section", back_populates="grade_categories")
    assignments = db.relationship("Assignment", back_populates="category")


class Assignment(db.Model, TimestampMixin):
    __tablename__ = "assignments"
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("grade_categories.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    due_date = db.Column(db.Date, nullable=True)
    max_points = db.Column(db.Numeric(8, 2), default=Decimal("100"))
    is_published = db.Column(db.Boolean, default=True)
    section = db.relationship("Section", back_populates="assignments")
    category = db.relationship("GradeCategory", back_populates="assignments")
    grades = db.relationship("Grade", back_populates="assignment")

    @property
    def is_past_due(self):
        if not self.due_date:
            return False
        return self.due_date < date.today()


class Grade(db.Model, TimestampMixin):
    __tablename__ = "grades"
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    points = db.Column(db.Numeric(8, 2), nullable=True)
    letter_grade = db.Column(db.String(4), default="")
    comment = db.Column(db.Text, default="")
    is_excused = db.Column(db.Boolean, default=False)
    is_missing = db.Column(db.Boolean, default=False)
    assignment = db.relationship("Assignment", back_populates="grades")
    student = db.relationship("StudentProfile", back_populates="grades")

    __table_args__ = (db.UniqueConstraint("assignment_id", "student_id"),)

    @property
    def percentage(self):
        if self.points is None or not self.assignment.max_points:
            return None
        return float(self.points / self.assignment.max_points * 100)


class MedicalRecord(db.Model, TimestampMixin):
    __tablename__ = "medical_records"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    doctor_name = db.Column(db.String(255), default="")
    doctor_phone = db.Column(db.String(32), default="")
    insurance_provider = db.Column(db.String(255), default="")
    insurance_policy = db.Column(db.String(128), default="")
    nurse_notes = db.Column(db.Text, default="")
    user = db.relationship("User", back_populates="medical_record")


class Allergy(db.Model, TimestampMixin):
    __tablename__ = "allergies"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    allergen = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.String(64), default="")
    reaction = db.Column(db.Text, default="")
    user = db.relationship("User", back_populates="allergies")


class Medication(db.Model, TimestampMixin):
    __tablename__ = "medications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    dosage = db.Column(db.String(128), default="")
    frequency = db.Column(db.String(128), default="")
    notes = db.Column(db.Text, default="")
    user = db.relationship("User", back_populates="medications")


class MedicalCondition(db.Model, TimestampMixin):
    __tablename__ = "medical_conditions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    condition = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    is_active = db.Column(db.Boolean, default=True)
    user = db.relationship("User", back_populates="medical_conditions")


class Immunization(db.Model, TimestampMixin):
    __tablename__ = "immunizations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    vaccine = db.Column(db.String(255), nullable=False)
    date_administered = db.Column(db.Date, nullable=True)
    dose_number = db.Column(db.Integer, default=1)
    user = db.relationship("User", back_populates="immunizations")


class EmergencyContact(db.Model, TimestampMixin):
    __tablename__ = "emergency_contacts"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    relationship = db.Column(db.String(64), nullable=False)
    phone_primary = db.Column(db.String(32), nullable=False)
    phone_secondary = db.Column(db.String(32), default="")
    email = db.Column(db.String(254), default="")
    priority = db.Column(db.Integer, default=1)
    is_authorized_pickup = db.Column(db.Boolean, default=False)
    student = db.relationship("StudentProfile", back_populates="emergency_contacts")


class AttendanceRecord(db.Model, TimestampMixin):
    __tablename__ = "attendance_records"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=True)
    date = db.Column(db.Date, nullable=False)
    code = db.Column(db.String(2), default="P")
    period_number = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, default="")
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    student = db.relationship("StudentProfile", back_populates="attendance_records")
    section = db.relationship("Section", back_populates="attendance_records")


class BehaviorIncident(db.Model, TimestampMixin):
    __tablename__ = "behavior_incidents"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    incident_date = db.Column(db.Date, nullable=False)
    incident_type = db.Column(db.String(32), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(128), default="")
    reported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    consequence = db.Column(db.Text, default="")
    parent_visible = db.Column(db.Boolean, default=True)
    resolved = db.Column(db.Boolean, default=False)
    student = db.relationship("StudentProfile", back_populates="behavior_incidents")


class Notification(db.Model, TimestampMixin):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notification_type = db.Column(db.String(32), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    metadata_json = db.Column(db.JSON, default=dict)
    user = db.relationship("User", back_populates="notifications")


class NotificationPreference(db.Model, TimestampMixin):
    __tablename__ = "notification_preferences"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    email_grades = db.Column(db.Boolean, default=True)
    email_missing = db.Column(db.Boolean, default=True)
    email_attendance = db.Column(db.Boolean, default=True)
    email_behavior = db.Column(db.Boolean, default=True)
    email_digest = db.Column(db.Boolean, default=True)
    user = db.relationship("User", back_populates="notification_preferences")


class GraduationRequirement(db.Model, TimestampMixin):
    __tablename__ = "graduation_requirements"
    id = db.Column(db.Integer, primary_key=True)
    district_id = db.Column(db.Integer, db.ForeignKey("districts.id"), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    subject_area = db.Column(db.String(128), nullable=False)
    credits_required = db.Column(db.Numeric(5, 2), nullable=False)
    total_credits_required = db.Column(db.Numeric(6, 2), default=Decimal("220"))


class CreditEarned(db.Model, TimestampMixin):
    __tablename__ = "credits_earned"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    term_name = db.Column(db.String(64), nullable=False)
    school_year = db.Column(db.String(32), nullable=False)
    credits = db.Column(db.Numeric(4, 2), nullable=False)
    letter_grade = db.Column(db.String(4), default="")
    gpa_points = db.Column(db.Numeric(3, 2), nullable=True)
    student = db.relationship("StudentProfile", back_populates="credits_earned")
    course = db.relationship("Course")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
