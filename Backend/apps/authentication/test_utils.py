"""Helpers for tests that need a mobile number verified through the real OTP flow (in-memory SMS backend)."""
import re

from django.core.cache import cache

from . import sms


def last_sms_code(phone):
    """Returns the 6-digit code from the most recent SMS sent to `phone` by the in-memory backend."""
    for message in reversed(sms.outbox):
        if message["to"] == phone:
            return re.search(r"\b(\d{6})\b", message["message"]).group(1)
    raise AssertionError(f"No SMS was sent to {phone}")


def verify_phone(client, phone):
    """Runs send + verify through the public API and returns the single-use verification token."""
    cache.delete(f"otp_cooldown_REGISTRATION_{phone}")
    sent = client.post("/api/auth/otp/send/", {"phone_number": phone}, format="json")
    assert sent.status_code == 200, sent.data
    verified = client.post("/api/auth/otp/verify/", {"phone_number": phone, "otp": last_sms_code(phone)}, format="json")
    assert verified.status_code == 200, verified.data
    return verified.data["verification_token"]
