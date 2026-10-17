"""
Mobile OTP challenges.

- Codes come from `secrets`, are never stored or logged, and are kept only as an HMAC bound to the phone
  number and purpose.
- Each challenge expires (OTP_TTL_MINUTES), allows OTP_MAX_ATTEMPTS guesses, and is single use.
- Sends are limited by a resend cooldown and an hourly cap per number.
- A successful verification returns a single-use verification token (stored hashed) that the follow-up
  operation must present together with the same phone number and purpose within
  PHONE_VERIFICATION_TTL_MINUTES. Nothing is "verified" unless this backend check succeeded.
"""
import datetime
import hashlib
import hmac
import secrets

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import OTPVerification
from .sms import SMSDeliveryError, send_sms

REGISTRATION = "REGISTRATION"


class OTPError(Exception):
    def __init__(self, message, status=400, code="OTP_INVALID"):
        super().__init__(message)
        self.message, self.status, self.code = message, status, code


def _hmac(*parts):
    return hmac.new(settings.SECRET_KEY.encode(), ":".join(parts).encode(), hashlib.sha256).hexdigest()


def _token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def send_otp(phone, purpose=REGISTRATION):
    cooldown_key = f"otp_cooldown_{purpose}_{phone}"
    if cache.get(cooldown_key):
        raise OTPError("An OTP was recently sent to this number. Please wait before requesting another.", 429, "OTP_COOLDOWN")
    hour_ago = timezone.now() - datetime.timedelta(hours=1)
    if OTPVerification.objects.filter(phone_number=phone, purpose=purpose, created_at__gte=hour_ago).count() >= settings.OTP_MAX_SENDS_PER_HOUR:
        raise OTPError("Too many OTP requests for this number. Please try again later.", 429, "OTP_RATE_LIMITED")

    code = f"{secrets.randbelow(1_000_000):06d}"
    now = timezone.now()
    with transaction.atomic():
        # Only the newest challenge for a number/purpose can be answered.
        OTPVerification.objects.filter(phone_number=phone, purpose=purpose, is_verified=False, expires_at__gt=now).update(expires_at=now)
        challenge = OTPVerification.objects.create(
            phone_number=phone, purpose=purpose, otp_hash=_hmac(purpose, phone, code),
            expires_at=now + datetime.timedelta(minutes=settings.OTP_TTL_MINUTES))
    try:
        send_sms(phone, f"{code} is your HSHEC NEP Awards verification code. It expires in "
                        f"{settings.OTP_TTL_MINUTES} minutes. Do not share it.")
    except SMSDeliveryError:
        challenge.delete()
        raise OTPError("The verification SMS could not be sent. Please try again later.", 503, "SMS_UNAVAILABLE")
    cache.set(cooldown_key, True, settings.OTP_RESEND_COOLDOWN_SECONDS)
    return challenge


def verify_otp(phone, code, purpose=REGISTRATION):
    """Returns a single-use verification token on success; raises OTPError otherwise."""
    code = str(code or "").strip()
    now = timezone.now()
    challenge = (OTPVerification.objects
                 .filter(phone_number=phone, purpose=purpose, is_verified=False, expires_at__gt=now)
                 .order_by("-created_at").first())
    if challenge is None:
        raise OTPError("Invalid or expired OTP code. Please request a new OTP.")
    if challenge.attempt_count >= settings.OTP_MAX_ATTEMPTS:
        raise OTPError("Too many incorrect attempts. Please request a new OTP.", 429, "OTP_ATTEMPTS_EXCEEDED")

    OTPVerification.objects.filter(pk=challenge.pk).update(attempt_count=F("attempt_count") + 1)
    if not (len(code) == 6 and code.isdigit() and hmac.compare_digest(challenge.otp_hash, _hmac(purpose, phone, code))):
        challenge.refresh_from_db(fields=["attempt_count"])
        if challenge.attempt_count >= settings.OTP_MAX_ATTEMPTS:
            raise OTPError("Too many incorrect attempts. Please request a new OTP.", 429, "OTP_ATTEMPTS_EXCEEDED")
        raise OTPError("Invalid or expired OTP code. Please enter the correct OTP.")

    token = secrets.token_urlsafe(32)
    updated = OTPVerification.objects.filter(pk=challenge.pk, is_verified=False).update(
        is_verified=True, verified_at=now, verification_token_hash=_token_hash(token))
    if not updated:  # lost a race with a concurrent verification of the same challenge
        raise OTPError("Invalid or expired OTP code. Please request a new OTP.")
    return token


def _verified_challenge(phone, token, purpose):
    if not phone or not token:
        return None
    fresh_after = timezone.now() - datetime.timedelta(minutes=settings.PHONE_VERIFICATION_TTL_MINUTES)
    return OTPVerification.objects.filter(
        phone_number=phone, purpose=purpose, is_verified=True, consumed_at__isnull=True,
        verified_at__gte=fresh_after, verification_token_hash=_token_hash(str(token))).first()


def phone_verification_is_valid(phone, token, purpose=REGISTRATION):
    return _verified_challenge(phone, token, purpose) is not None


def consume_phone_verification(phone, token, purpose=REGISTRATION):
    """Atomically marks the verification as used. Returns False if it was already used or is invalid."""
    challenge = _verified_challenge(phone, token, purpose)
    if challenge is None:
        return False
    return OTPVerification.objects.filter(pk=challenge.pk, consumed_at__isnull=True).update(consumed_at=timezone.now()) == 1
