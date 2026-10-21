"""
S-11 (security review 2026-10-21): the attempt limit must hold even when concurrent guesses read the challenge before
any of them has recorded its attempt. The race is reproduced by handing the verifier a stale copy of the challenge
(attempt_count 0) while the database already shows the limit reached; the correct code must still be refused.
"""
from unittest.mock import patch

from django.conf import settings
from django.db.models.query import QuerySet
from django.test import TestCase, override_settings

from apps.authentication import otp_service
from apps.authentication.email_otp_service import EmailOTPAttemptsExceededError, EmailOTPService
from apps.authentication.models import EmailOTPVerification, OTPVerification, User

_original_first = QuerySet.first


def _stale_first_for(model):
    def first(queryset):
        obj = _original_first(queryset)
        if queryset.model is model and obj is not None:
            model.objects.filter(pk=obj.pk).update(attempt_count=obj.max_attempts if hasattr(obj, 'max_attempts')
                                                   else settings.OTP_MAX_ATTEMPTS)
        return obj  # attempt_count still reads as it was when loaded
    return first


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailOTPAttemptLimitTests(TestCase):
    def test_correct_code_refused_once_limit_reached_concurrently(self):
        user = User.objects.create_user(email="otp@example.com", full_name="Otp User", role="principal",
                                        password="x-Str0ng!Passw0rd", is_email_verified=False)
        with patch.object(EmailOTPService, 'generate_otp', return_value="246810"):
            EmailOTPService.send_verification_otp(user)
        with patch.object(QuerySet, 'first', _stale_first_for(EmailOTPVerification)):
            with self.assertRaises(EmailOTPAttemptsExceededError):
                EmailOTPService.verify_otp(email="otp@example.com", otp_code="246810")
        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)


class SMSOTPAttemptLimitTests(TestCase):
    def test_correct_code_refused_once_limit_reached_concurrently(self):
        with patch.object(otp_service.secrets, 'randbelow', return_value=135791):
            otp_service.send_otp("9876543210")
        with patch.object(QuerySet, 'first', _stale_first_for(OTPVerification)):
            with self.assertRaises(otp_service.OTPError) as ctx:
                otp_service.verify_otp("9876543210", "135791")
        self.assertEqual(ctx.exception.code, "OTP_ATTEMPTS_EXCEEDED")
        self.assertFalse(OTPVerification.objects.filter(is_verified=True).exists())
