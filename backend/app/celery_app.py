from datetime import timedelta

from celery import Celery

celery = Celery("libregrades")


def init_celery(app):
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=app.config.get("CELERY_TIMEZONE", "UTC"),
        enable_utc=True,
        beat_schedule={
            "check-missing-assignments": {
                "task": "app.tasks.notifications.check_missing_assignments",
                "schedule": timedelta(hours=24),
            },
            "weekly-digest": {
                "task": "app.tasks.notifications.send_weekly_digests",
                "schedule": timedelta(days=7),
            },
        },
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    import app.tasks.notifications  # noqa: F401

    return celery
