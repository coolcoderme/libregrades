"""TOTP two-factor authentication for staff."""

import io
import secrets

import pyotp
import qrcode


def generate_totp_secret():
    return pyotp.random_base32()


def totp_uri(user, secret):
    return pyotp.TOTP(secret).provisioning_uri(name=user.email or user.username, issuer_name="LibreGrades")


def qr_code_base64(uri):
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    import base64

    return base64.b64encode(buf.getvalue()).decode("ascii")


def verify_totp(secret, token):
    if not secret or not token:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(str(token).strip(), valid_window=1)
