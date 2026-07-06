from django.apps import AppConfig


class ExtensionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.extensions"
    verbose_name = "Extended features"

    def ready(self):
        from . import signals  # noqa: F401
