"""Middleware for extended platform features."""

import ipaddress

from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone


class SessionTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = request.user
        if user.is_authenticated and request.session.session_key:
            from apps.extensions.models import UserSessionRecord

            UserSessionRecord.objects.update_or_create(
                user=user,
                session_key=request.session.session_key,
                defaults={
                    "ip_address": request.META.get("REMOTE_ADDR"),
                    "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:255],
                    "last_seen": timezone.now(),
                    "is_active": True,
                },
            )
        return response


class AdminIPAllowlistMiddleware:
    EXEMPT = ("/login/", "/logout/", "/static/", "/media/", "/health/", "/api/", "/substitute/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and user.is_admin_role and user.district_id:
            path = request.path
            if not any(path.startswith(p) for p in self.EXEMPT):
                from apps.extensions.models import AdminIPAllowlist

                rules = AdminIPAllowlist.objects.filter(district_id=user.district_id)
                if rules.exists():
                    ip = request.META.get("REMOTE_ADDR", "")
                    allowed = False
                    for rule in rules:
                        try:
                            if ipaddress.ip_address(ip) in ipaddress.ip_network(rule.cidr, strict=False):
                                allowed = True
                                break
                        except ValueError:
                            continue
                    if not allowed:
                        return HttpResponseForbidden("Admin access denied from this IP.")
        return self.get_response(request)


class PortalPreferencesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            from apps.extensions.models import UserPortalPreferences

            prefs = UserPortalPreferences.objects.filter(user=user).first()
            if prefs:
                request.session.setdefault("portal_theme", prefs.theme)
                request.session.setdefault("portal_locale", prefs.locale)
                request.session.setdefault("portal_a11y_large", prefs.accessibility_large_text)
                request.session.setdefault("portal_a11y_contrast", prefs.accessibility_high_contrast)
        return self.get_response(request)
