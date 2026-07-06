import os
import secrets

from django.conf import settings
from django.db import IntegrityError, transaction

from .models import ServerIdentity


def _generate_code():
    return f"{secrets.randbelow(900000) + 100000:06d}"


def get_server_identity():
    """Return the singleton ServerIdentity for this installation."""
    identity = ServerIdentity.objects.first()
    if identity:
        return identity
    return ensure_server_identity()


def ensure_server_identity():
    """Create the server identity record if it does not exist."""
    existing = ServerIdentity.objects.first()
    if existing:
        return existing

    env_code = os.environ.get("SERVER_CODE", "").strip()
    if env_code and len(env_code) == 6 and env_code.isdigit():
        code = env_code
    else:
        code = _generate_code()

    for _ in range(20):
        try:
            with transaction.atomic():
                if ServerIdentity.objects.exists():
                    return ServerIdentity.objects.first()
                return ServerIdentity.objects.create(code=code)
        except IntegrityError:
            if env_code:
                raise
            code = _generate_code()

    raise RuntimeError("Could not generate a unique server code.")


def server_info_payload():
    identity = get_server_identity()
    return {
        "server_code": identity.code,
        "district_name": settings.DISTRICT_NAME,
    }
