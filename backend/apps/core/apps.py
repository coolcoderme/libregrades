from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"

    def ready(self):
        from django.db.models.signals import post_migrate

        def _ensure_identity(sender, **kwargs):
            if sender.name != self.name:
                return
            try:
                from apps.core.server_identity import ensure_server_identity

                ensure_server_identity()
            except Exception:
                pass

        post_migrate.connect(_ensure_identity, dispatch_uid="core.ensure_server_identity")
