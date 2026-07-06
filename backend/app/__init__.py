import os
from datetime import datetime, timezone

from flask import Flask
from flask_login import current_user
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import csrf, db, jwt, login_manager, migrate


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object("app.config.Config")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401
    from .blueprints.api import api_bp
    from .blueprints.auth import auth_bp
    from .blueprints.portal import media_bp, portal_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(media_bp)
    csrf.exempt(api_bp)

    @app.route("/health/")
    def health():
        return {"status": "ok", "service": "libregrades", "framework": "flask"}

    @app.context_processor
    def inject_globals():
        ctx = {
            "district_name": app.config.get("DISTRICT_NAME", "LibreGrades District"),
            "notification_count": 0,
            "role": None,
        }
        if current_user.is_authenticated:
            ctx["role"] = current_user.role
            ctx["notification_count"] = sum(1 for n in current_user.notifications if not n.is_read)
        return ctx

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["PROFILE_UPLOAD_FOLDER"], exist_ok=True)

    return app


def utcnow():
    return datetime.now(timezone.utc)
