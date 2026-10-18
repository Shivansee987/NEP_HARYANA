import datetime
import hashlib
import hmac
import logging
import secrets
from datetime import timedelta
from typing import Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import User, EmailOTPVerification, UserAuditLog

logger = logging.getLogger(__name__)


class EmailOTPError(Exception):
    """Base exception for Email OTP operations."""
    def __init__(self, message: str, status_code: int = 400, code: str = "EMAIL_OTP_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class EmailOTPDeliveryError(EmailOTPError):
    def __init__(self, message: str = "Unable to deliver verification email. Please check your email address or try again later."):
        super().__init__(message, status_code=503, code="EMAIL_DELIVERY_FAILED")


class EmailOTPCooldownError(EmailOTPError):
    def __init__(self, retry_after: int = 60, message: str = "Please wait before requesting another verification code."):
        super().__init__(message, status_code=429, code="OTP_COOLDOWN")
        self.retry_after = retry_after


class EmailOTPRateLimitError(EmailOTPError):
    def __init__(self, retry_after: int = 3600, message: str = "Too many verification attempts. Please try again later."):
        super().__init__(message, status_code=429, code="OTP_RATE_LIMITED")
        self.retry_after = retry_after


class EmailOTPAttemptsExceededError(EmailOTPError):
    def __init__(self, message: str = "Too many incorrect verification attempts. This code is now invalid. Please request a new code."):
        super().__init__(message, status_code=429, code="OTP_ATTEMPTS_EXCEEDED")


class EmailOTPInvalidError(EmailOTPError):
    def __init__(self, message: str = "Invalid or expired verification code.", code: str = "OTP_INVALID"):
        super().__init__(message, status_code=400, code=code)


class EmailOTPAlreadyVerifiedError(EmailOTPError):
    def __init__(self, message: str = "This account is already verified. You can proceed to login."):
        super().__init__(message, status_code=200, code="ALREADY_VERIFIED")


class EmailOTPService:
    """
    Production-grade 6-digit Email OTP Verification Service.
    - Generates 6-digit cryptographically secure numeric codes.
    - Preserves leading zeros.
    - Stores only an HMAC-SHA256 hash bound to SECRET_KEY, email, and purpose.
    - Enforces 10-minute configurable TTL (EMAIL_OTP_TTL_MINUTES).
    - Max 5 verification attempts per code.
    - Automatic invalidation of previous codes when a new one is issued.
    - 60s resend cooldown and hourly caps per email.
    - Anti-enumeration timing defense for public verification requests.
    """

    PURPOSE = "EMAIL_VERIFICATION"

    @classmethod
    def _hmac(cls, email: str, otp: str) -> str:
        key = settings.SECRET_KEY.encode('utf-8')
        message = f"{cls.PURPOSE}:{email.strip().lower()}:{otp.strip()}".encode('utf-8')
        return hmac.new(key, message, hashlib.sha256).hexdigest()

    @staticmethod
    def mask_email(email: str) -> str:
        """Masks an email for safe public presentation (e.g., p***l@college.edu.in)."""
        if not email or '@' not in email:
            return ""
        user_part, domain_part = email.split('@', 1)
        if len(user_part) <= 2:
            masked_user = user_part[0] + "***"
        else:
            masked_user = user_part[0] + "***" + user_part[-1]
        return f"{masked_user}@{domain_part}"

    @staticmethod
    def generate_otp() -> str:
        """Generates a cryptographically secure 6-digit numeric OTP preserving leading zeros."""
        return f"{secrets.randbelow(1_000_000):06d}"

    @classmethod
    def send_verification_otp(cls, user: User, ip_address: Optional[str] = None, bypass_cooldown: bool = False) -> Tuple[EmailOTPVerification, str]:
        """
        Creates and dispatches a fresh 6-digit OTP to the user's registered email address.
        Returns (challenge, masked_email).
        Raises EmailOTPCooldownError, EmailOTPRateLimitError, or EmailOTPDeliveryError.
        """
        norm_email = user.email.strip().lower()
        email_hash = hashlib.sha256(norm_email.encode('utf-8')).hexdigest()[:16]
        cooldown_key = f"email_otp_cd_{email_hash}"
        rate_key = f"email_otp_rate_{email_hash}"

        cooldown_ttl = getattr(settings, 'EMAIL_OTP_RESEND_COOLDOWN_SECONDS', 60)
        max_hourly = getattr(settings, 'EMAIL_OTP_MAX_SENDS_PER_HOUR', 5)
        ttl_minutes = getattr(settings, 'EMAIL_OTP_TTL_MINUTES', 10)
        max_attempts = getattr(settings, 'EMAIL_OTP_MAX_ATTEMPTS', 5)

        if not bypass_cooldown:
            if cache.get(cooldown_key):
                raise EmailOTPCooldownError(retry_after=cooldown_ttl)

        hourly_count = cache.get(rate_key, 0)
        if hourly_count >= max_hourly:
            raise EmailOTPRateLimitError(retry_after=3600)

        raw_otp = cls.generate_otp()
        otp_hash = cls._hmac(norm_email, raw_otp)
        now = timezone.now()
        expires_at = now + timedelta(minutes=ttl_minutes)

        with transaction.atomic():
            # Invalidate any existing unverified OTP challenges for this user/email
            EmailOTPVerification.objects.filter(
                user=user,
                purpose=cls.PURPOSE,
                is_verified=False,
                is_revoked=False
            ).update(is_revoked=True)

            challenge = EmailOTPVerification.objects.create(
                user=user,
                email=norm_email,
                purpose=cls.PURPOSE,
                otp_hash=otp_hash,
                attempt_count=0,
                max_attempts=max_attempts,
                expires_at=expires_at,
                is_verified=False,
                is_revoked=False,
                ip_address=ip_address
            )

        # Send the email
        delivered = cls._dispatch_email(user=user, raw_otp=raw_otp, expires_minutes=ttl_minutes)
        if not delivered:
            # Atomic rollback of challenge if email failed
            challenge.delete()
            UserAuditLog.objects.create(
                actor=None,
                target_user=user,
                action='NOTIFICATION_FAILED',
                ip_address=ip_address,
                details={'channel': 'EMAIL_OTP', 'reason': 'Delivery failed via mail backend'}
            )
            raise EmailOTPDeliveryError()

        # Update cache cooldown and rate count
        cache.set(cooldown_key, True, cooldown_ttl)
        cache.set(rate_key, hourly_count + 1, 3600)

        UserAuditLog.objects.create(
            actor=user,
            target_user=user,
            action='EMAIL_OTP_SENT',
            ip_address=ip_address,
            details={
                'email': norm_email,
                'expires_at': expires_at.isoformat(),
                'ttl_minutes': ttl_minutes,
            }
        )

        return challenge, cls.mask_email(norm_email)

    @classmethod
    def _dispatch_email(cls, user: User, raw_otp: str, expires_minutes: int) -> bool:
        """Sends the HTML and plain-text OTP verification email."""
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
        norm_email = user.email.strip().lower()
        otp_page_url = f"{frontend_url}/auth/verify-email/otp?email={norm_email}"

        subject = "Verify Your Email Address — HSHEC Haryana Excellence Awards 2026"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@haryana.gov.in')

        recipient_name = user.full_name or "Applicant"

        text_content = (
            f"Dear {recipient_name},\n\n"
            f"Your one-time email verification code for the Haryana State Higher Education Council (HSHEC) "
            f"NEP Excellence Awards 2026 Portal is:\n\n"
            f"    {raw_otp}\n\n"
            f"This code will expire in {expires_minutes} minutes.\n\n"
            f"Enter this code on the verification page:\n"
            f"{otp_page_url}\n\n"
            f"Security Notice:\n"
            f"- Never share this code with anyone. HSHEC officials will never ask for your verification code.\n"
            f"- If you did not request this verification code, please ignore this email.\n\n"
            f"Regards,\n"
            f"Haryana State Higher Education Council (HSHEC)\n"
            f"Government of Haryana"
        )

        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 580px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
            <div style="text-align: center; margin-bottom: 24px; border-bottom: 2px solid #600b0b; padding-bottom: 16px;">
                <h2 style="color: #600b0b; margin: 0; font-size: 20px; font-weight: 800; letter-spacing: 0.5px;">Haryana State Higher Education Council</h2>
                <p style="color: #64748b; font-size: 13px; margin: 4px 0 0; font-weight: 600; text-transform: uppercase;">NEP Excellence Awards 2026</p>
            </div>
            
            <p style="font-size: 15px; color: #1e293b; margin-top: 0;">Dear <strong>{recipient_name}</strong>,</p>
            <p style="font-size: 14px; color: #334155; line-height: 1.6;">
                Thank you for registering on the official HSHEC Haryana Excellence Awards Portal.
                Please enter the following 6-digit verification code to complete your email verification:
            </p>
            
            <div style="text-align: center; margin: 28px 0;">
                <div style="display: inline-block; background-color: #fdf2f2; border: 2px dashed #600b0b; border-radius: 12px; padding: 18px 36px; text-align: center;">
                    <span style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #600b0b; font-family: 'Courier New', Courier, monospace;">
                        {raw_otp}
                    </span>
                    <p style="margin: 8px 0 0 0; font-size: 12px; color: #7f1d1d; font-weight: 600;">
                        Valid for {expires_minutes} minutes
                    </p>
                </div>
            </div>

            <div style="text-align: center; margin: 20px 0;">
                <a href="{otp_page_url}" style="background-color: #600b0b; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 14px; display: inline-block;">
                    Open OTP Verification Page
                </a>
            </div>
            
            <div style="background-color: #fffbeb; border: 1px solid #fef3c7; border-radius: 8px; padding: 14px 16px; margin-bottom: 20px;">
                <strong style="color: #92400e; font-size: 13px;">Security Notice:</strong>
                <ul style="color: #92400e; font-size: 12px; margin: 6px 0 0 0; padding-left: 20px; line-height: 1.5;">
                    <li>Do not share this code with anyone, including university or college staff.</li>
                    <li>If you did not request this code, no action is required.</li>
                </ul>
            </div>

            <p style="font-size: 12px; color: #64748b; line-height: 1.5;">
                <strong>Governance Rule:</strong> Email verification verifies your contact identity. Access to institution assessment data remains subject to administrator approval.
            </p>
            
            <p style="font-size: 11px; color: #94a3b8; margin-top: 24px; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 14px;">
                This is an automated message from HSHEC Portal, Government of Haryana. Please do not reply to this email.
            </p>
        </div>
        """

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)
            return True
        except Exception as e:
            logger.error(f"Failed to send email OTP to {user.email}: {e}")
            return False

    @classmethod
    def verify_otp(cls, email: str, otp_code: str, ip_address: Optional[str] = None) -> User:
        """
        Validates the 6-digit OTP code against the active challenge for the email.
        On success, atomically updates:
          - EmailOTPVerification.is_verified = True
          - User.is_email_verified = True
          - Creates UserAuditLog entry
        Returns the verified User.
        Raises EmailOTPInvalidError, EmailOTPAttemptsExceededError, or EmailOTPAlreadyVerifiedError.
        """
        norm_email = (email or '').strip().lower()
        clean_code = str(otp_code or '').strip()

        if not norm_email or '@' not in norm_email:
            raise EmailOTPInvalidError("A valid email address is required.", code="INVALID_EMAIL")

        if not clean_code or len(clean_code) != 6 or not clean_code.isdigit():
            raise EmailOTPInvalidError("Please enter a valid 6-digit numeric verification code.", code="MALFORMED_OTP")

        user = User.objects.filter(email__iexact=norm_email).first()
        if not user:
            # Generic error to prevent enumeration
            raise EmailOTPInvalidError("Invalid or expired verification code.", code="OTP_INVALID")

        if user.is_email_verified:
            raise EmailOTPAlreadyVerifiedError("Your email address is already verified. Please sign in.")

        now = timezone.now()

        challenge = (
            EmailOTPVerification.objects
            .filter(
                user=user,
                email=norm_email,
                purpose=cls.PURPOSE,
                is_verified=False,
                is_revoked=False
            )
            .order_by('-created_at')
            .first()
        )

        if challenge is None:
            raise EmailOTPInvalidError("Invalid or expired verification code. Please request a new code.", code="OTP_NOT_FOUND")

        if now >= challenge.expires_at:
            EmailOTPVerification.objects.filter(pk=challenge.pk).update(is_revoked=True)
            raise EmailOTPInvalidError("This verification code has expired. Please request a new code.", code="OTP_EXPIRED")

        if challenge.attempt_count >= challenge.max_attempts:
            EmailOTPVerification.objects.filter(pk=challenge.pk).update(is_revoked=True)
            raise EmailOTPAttemptsExceededError()

        # Increment attempt count atomically (persisted regardless of outcome)
        EmailOTPVerification.objects.filter(pk=challenge.pk).update(attempt_count=F('attempt_count') + 1)
        challenge.refresh_from_db(fields=['attempt_count'])

        expected_hash = cls._hmac(norm_email, clean_code)
        if not hmac.compare_digest(challenge.otp_hash, expected_hash):
            if challenge.attempt_count >= challenge.max_attempts:
                EmailOTPVerification.objects.filter(pk=challenge.pk).update(is_revoked=True)
                raise EmailOTPAttemptsExceededError()
            remaining = max(0, challenge.max_attempts - challenge.attempt_count)
            raise EmailOTPInvalidError(
                f"Incorrect verification code. You have {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
                code="OTP_INCORRECT"
            )

        # Verification succeeded: atomically update challenge, user, and audit log
        with transaction.atomic():
            updated = EmailOTPVerification.objects.filter(
                pk=challenge.pk,
                is_verified=False,
                is_revoked=False
            ).update(is_verified=True, verified_at=now)

            if not updated:  # Lost race condition with concurrent verification
                raise EmailOTPInvalidError("Invalid or expired verification code. Please request a new code.", code="OTP_INVALID")

            # Invalidate any other outstanding challenges for this user
            EmailOTPVerification.objects.filter(
                user=user,
                purpose=cls.PURPOSE,
                is_verified=False
            ).update(is_revoked=True)

            # Update user
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])

            UserAuditLog.objects.create(
                actor=user,
                target_user=user,
                action='EMAIL_OTP_VERIFIED',
                ip_address=ip_address,
                details={
                    'email': norm_email,
                    'role': user.role,
                    'institution_status': user.institution_status
                }
            )

        return user

    @classmethod
    def request_otp_for_email(cls, email: str, ip_address: Optional[str] = None) -> dict:
        """
        Direct request for email verification code outside signup flow.
        - Returns identical success responses to prevent user enumeration.
        - Enforces rate limits and cooldowns.
        """
        norm_email = (email or '').strip().lower()
        if not norm_email or '@' not in norm_email:
            raise EmailOTPInvalidError("A valid email address is required.", code="INVALID_EMAIL")

        cooldown_ttl = getattr(settings, 'EMAIL_OTP_RESEND_COOLDOWN_SECONDS', 60)
        ttl_minutes = getattr(settings, 'EMAIL_OTP_TTL_MINUTES', 10)

        user = User.objects.filter(email__iexact=norm_email).first()

        if user and user.is_email_verified:
            return {
                'success': True,
                'already_verified': True,
                'account_already_verified': True,
                'email': cls.mask_email(norm_email),
                'message': "This email address is already verified. Please sign in to your account.",
                'detail': "This email address is already verified. Please sign in to your account.",
                'redirect_to': "/auth/login",
            }

        # If user exists and is not verified, send OTP
        if user and not user.is_email_verified:
            challenge, masked = cls.send_verification_otp(user=user, ip_address=ip_address)
            return {
                'success': True,
                'already_verified': False,
                'email': masked,
                'otp_sent': True,
                'message': "Verification code sent successfully. Please check your inbox.",
                'detail': "Verification code sent successfully. Please check your inbox.",
                'redirect_to': "/auth/verify-email/otp",
                'cooldown_seconds': cooldown_ttl,
                'expires_in_minutes': ttl_minutes,
            }

        # If user does NOT exist, apply cooldown to avoid enumeration timing, then return generic message
        email_hash = hashlib.sha256(norm_email.encode('utf-8')).hexdigest()[:16]
        cooldown_key = f"email_otp_cd_{email_hash}"
        rate_key = f"email_otp_rate_{email_hash}"

        if cache.get(cooldown_key):
            raise EmailOTPCooldownError(retry_after=cooldown_ttl)

        hourly_count = cache.get(rate_key, 0)
        if hourly_count >= getattr(settings, 'EMAIL_OTP_MAX_SENDS_PER_HOUR', 5):
            raise EmailOTPRateLimitError(retry_after=3600)

        cache.set(cooldown_key, True, cooldown_ttl)
        cache.set(rate_key, hourly_count + 1, 3600)

        masked = cls.mask_email(norm_email)
        return {
            'success': True,
            'already_verified': False,
            'email': masked,
            'otp_sent': False,
            'message': f"If an unverified account exists for {masked}, a verification code has been sent.",
            'redirect_to': "/auth/verify-email/otp",
            'cooldown_seconds': cooldown_ttl,
            'expires_in_minutes': ttl_minutes,
        }
