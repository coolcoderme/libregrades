from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required

from ..extensions import db
from ..models import NotificationPreference, ParentProfile, StudentProfile, User
from ..permissions import get_parent_profile

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "profile_picture": user.profile_picture,
        "display_name": user.display_name,
    }


def _student_payload(student):
    return {
        "id": student.id,
        "student_id": student.student_id,
        "grade_level": student.grade_level,
        "full_name": student.full_name,
        "school_id": student.school_id,
    }


@api_bp.route("/auth/login/", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"detail": "Invalid credentials."}), 401
    access = create_access_token(identity=str(user.id))
    refresh = create_refresh_token(identity=str(user.id))
    return jsonify({"access": access, "refresh": refresh})


@api_bp.route("/auth/refresh/", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access = create_access_token(identity=user_id)
    return jsonify({"access": access})


@api_bp.route("/auth/me/", methods=["GET"])
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"detail": "Not found."}), 404
    return jsonify(_user_payload(user))


@api_bp.route("/parents/children/", methods=["GET"])
@jwt_required()
def parent_children():
    user = db.session.get(User, int(get_jwt_identity()))
    if user.role != "parent":
        return jsonify({"detail": "Not a parent account."}), 403
    profile = get_parent_profile(user)
    if not profile:
        return jsonify([])
    return jsonify([_student_payload(s) for s in profile.students])


@api_bp.route("/parents/link/", methods=["POST"])
@jwt_required()
def parent_link():
    user = db.session.get(User, int(get_jwt_identity()))
    if user.role != "parent":
        return jsonify({"detail": "Parent account required."}), 403
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    code = data.get("verification_code")
    student = StudentProfile.query.filter_by(student_id=student_id).first()
    if not student:
        return jsonify({"detail": "Student not found."}), 404
    if code != student.student_id[-4:]:
        return jsonify({"detail": "Invalid verification code."}), 400
    profile = ParentProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = ParentProfile(user_id=user.id)
        db.session.add(profile)
        db.session.flush()
    if student not in profile.students:
        profile.students.append(student)
    db.session.commit()
    return jsonify({"detail": "Student linked.", "student_id": student.id})


@api_bp.route("/notifications/preferences/", methods=["GET", "PUT", "PATCH"])
@jwt_required()
def notification_preferences():
    user = db.session.get(User, int(get_jwt_identity()))
    prefs = NotificationPreference.query.filter_by(user_id=user.id).first()
    if not prefs:
        prefs = NotificationPreference(user_id=user.id)
        db.session.add(prefs)
        db.session.commit()
    if request.method == "GET":
        return jsonify(
            {
                "email_grades": prefs.email_grades,
                "email_missing": prefs.email_missing,
                "email_attendance": prefs.email_attendance,
                "email_behavior": prefs.email_behavior,
                "email_digest": prefs.email_digest,
            }
        )
    data = request.get_json(silent=True) or {}
    for field in ("email_grades", "email_missing", "email_attendance", "email_behavior", "email_digest"):
        if field in data:
            setattr(prefs, field, bool(data[field]))
    db.session.commit()
    return jsonify({"detail": "Updated."})
