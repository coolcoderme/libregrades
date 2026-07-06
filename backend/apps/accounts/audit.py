"""Audit logging for sensitive data access."""

from apps.accounts.models import AuditLog


def log_audit(user, action, model_name, object_id, details=None, request=None):
    ip = None
    if request:
        ip = request.META.get("REMOTE_ADDR")
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        details=details or {},
        ip_address=ip,
    )
