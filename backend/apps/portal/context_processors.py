from django.conf import settings


def portal_context(request):
    from apps.core.server_identity import get_server_identity

    try:
        server_code = get_server_identity().code
    except Exception:
        server_code = "------"

    ctx = {
        "district_name": settings.DISTRICT_NAME,
        "server_code": server_code,
        "sso_google": bool(settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY),
        "sso_microsoft": bool(settings.SOCIAL_AUTH_MICROSOFT_GRAPH_KEY),
        "portal_theme": request.session.get("portal_theme", "light"),
        "portal_a11y_large": request.session.get("portal_a11y_large", False),
        "portal_a11y_contrast": request.session.get("portal_a11y_contrast", False),
    }
    if request.user.is_authenticated:
        ctx["notification_count"] = request.user.notifications.filter(is_read=False).count()
        ctx["role"] = request.user.role
    else:
        ctx["notification_count"] = 0
        ctx["role"] = None
    return ctx
