"""Substitute teacher session helpers."""

import secrets
from datetime import datetime, timedelta

from django.utils import timezone

from apps.accounts.models import SubstitutePass


def generate_substitute_code():
    return secrets.token_hex(4).upper()[:8]


def create_substitute_pass(teacher, sections, valid_date):
    expires = timezone.make_aware(
        datetime.combine(valid_date, datetime.max.time().replace(microsecond=0))
    )
    for _ in range(10):
        code = generate_substitute_code()
        if not SubstitutePass.objects.filter(access_code=code).exists():
            p = SubstitutePass.objects.create(
                created_by=teacher,
                access_code=code,
                valid_date=valid_date,
                expires_at=expires,
            )
            p.sections.set(sections)
            return p
    raise RuntimeError("Could not generate substitute code")


def validate_substitute_code(code):
    today = timezone.localdate()
    now = timezone.now()
    try:
        p = SubstitutePass.objects.prefetch_related("sections").get(
            access_code=code.upper(), is_active=True, valid_date=today
        )
    except SubstitutePass.DoesNotExist:
        return None
    if p.expires_at < now:
        return None
    return p
