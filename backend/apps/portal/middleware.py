"""Portal middleware for 2FA and substitute sessions."""

from django.shortcuts import redirect
from django.urls import reverse


class StaffTwoFactorMiddleware:
    EXEMPT_PREFIXES = (
        "/login/",
        "/logout/",
        "/static/",
        "/media/",
        "/health/",
        "/api/",
        "/settings/2fa/",
        "/substitute/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and user.is_staff_role and user.totp_enabled:
            if not request.session.get("2fa_verified"):
                path = request.path
                if not any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
                    return redirect(f"{reverse('portal:totp_verify')}?next={path}")
        return self.get_response(request)
