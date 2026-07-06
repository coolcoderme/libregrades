import hashlib
import hmac
import json

import requests
from django.conf import settings


def encrypt_text(value: str) -> str:
    if not value:
        return ""
    try:
        from cryptography.fernet import Fernet
        import base64

        key = settings.EXTENSIONS_ENCRYPTION_KEY
        if not key:
            return value
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.encrypt(value.encode()).decode()
    except Exception:
        return value


def decrypt_text(value: str) -> str:
    if not value:
        return ""
    try:
        from cryptography.fernet import Fernet

        key = settings.EXTENSIONS_ENCRYPTION_KEY
        if not key:
            return value
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value


def dispatch_webhook(event: str, payload: dict):
    from apps.extensions.models import WebhookDelivery, WebhookEndpoint

    for endpoint in WebhookEndpoint.objects.filter(is_active=True):
        if endpoint.events and event not in endpoint.events:
            continue
        body = json.dumps({"event": event, "payload": payload})
        headers = {"Content-Type": "application/json"}
        if endpoint.secret:
            sig = hmac.new(endpoint.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-LibreGrades-Signature"] = sig
        success = False
        status_code = None
        try:
            r = requests.post(endpoint.url, data=body, headers=headers, timeout=10)
            status_code = r.status_code
            success = 200 <= r.status_code < 300
        except requests.RequestException:
            pass
        WebhookDelivery.objects.create(
            endpoint=endpoint,
            event=event,
            payload=payload,
            status_code=status_code,
            success=success,
        )
