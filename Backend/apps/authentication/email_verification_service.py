import secrets
import hashlib
import logging
from datetime import timedelta
from typing import Optional, Tuple

from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import User, EmailVerificationToken, UserAuditLog

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when an email cannot be delivered through the configured email backend."""
    pass


class RateLimitExceededError(Exception):
    """Base exception for rate limit issues."""
    def __init__(self, message, retry_after=60):
        super().__init__(message)
        self.retry_after = retry_after


class VerificationCooldownError(RateLimitExceededError):
    """Raised when email resend request is in the cooldown window."""
    def __init__(self, message="Please wait before requesting another verification email.", retry_after=60):
        super().__init__(message, retry_after=retry_after)


class VerificationRateLimitError(RateLimitExceededError):
    """Raised when email resend requests exceed hourly limits."""
    def __init__(self, message="Too many verification requests. Please try again later.", retry_after=3600):
        super().__init__(message, retry_after=retry_after)


class EmailVerificationService:
    """
    Cryptographically secure email verification service.
    - Generates single-use, high-entropy (token_urlsafe 32-byte) tokens.
    - Stores only the SHA-256 hash of the token in the database.
    - Enforces expiry (default 24 hours), single use, resend cooldown, and rate limits.
    - Fails safely when email delivery is unavailable without creating inconsistent state.
    - Preserves separation between email verification and administrator institutional access approval.
    """

    COOLDOWN_SECONDS = 60
    MAX_SENDS_PER_HOUR = 5

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    @staticmethod
    def mask_email(email: str) -> str:
        """Masks an email for safe display, e.g. v***e@college.edu.in."""
        if not email or '@' not in email:
            return ""
        user_part, domain_part = email.split('@', 1)
        if len(user_part) <= 2:
            masked_user = user_part[0] + "***"
        else:
            masked_user = user_part[0] + "***" + user_part[-1]
        return f"{masked_user}@{domain_part}"

    @classmethod
    def create_verification_token(cls, user: User, validity_hours: Optional[int] = None) -> Tuple[str, EmailVerificationToken]:
        """
        Creates a single-use email verification token for the user.
        Any previous unconsumed tokens for this user are revoked.
        Returns the (raw_token, token_obj).
        """
        ttl_hours = validity_hours or getattr(settings, 'EMAIL_VERIFICATION_TTL_HOURS', 24)

        # Invalidate previous unconsumed tokens
        EmailVerificationToken.objects.filter(
            user=user,
            is_used=False,
            is_revoked=False
        ).update(is_revoked=True)

        raw_token = secrets.token_urlsafe(32)
        token_hash = cls._hash_token(raw_token)
        expires_at = timezone.now() + timedelta(hours=ttl_hours)

        token_obj = EmailVerificationToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at
        )

        UserAuditLog.objects.create(
            actor=user,
            target_user=user,
            action='EMAIL_VERIFICATION_SENT',
            details={
                'role': user.role,
                'validity_hours': ttl_hours,
                'expires_at': expires_at.isoformat(),
            }
        )

        return raw_token, token_obj

    @classmethod
    def send_verification_email(cls, user: User, raw_token: str) -> bool:
        """
        Sends the email verification link to the user's registered email address.
        Uses a trusted configured frontend/base URL from settings, never an untrusted host header.
        Fails safely if email delivery is unavailable.
        """
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
        verification_link = f"{frontend_url}/auth/verify-email/{raw_token}"

        subject = "Verify Your Email Address — HSHEC Haryana Excellence Awards 2026"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@haryana.gov.in')

        text_content = (
            f"Dear {user.full_name},\n\n"
            f"Thank you for registering on the Haryana State Higher Education Council (HSHEC) "
            f"NEP Excellence Awards 2026 Portal.\n\n"
            f"Please verify your email address by visiting the following link:\n"
            f"{verification_link}\n\n"
            f"This link is single-use and will expire in 24 hours.\n\n"
            f"Important Notice:\n"
            f"Verifying your email verifies your contact identity. Access to institution assessment data "
            f"remains subject to administrator approval in accordance with council governance rules.\n\n"
            f"If you did not register for this account, please ignore this email.\n\n"
            f"Regards,\nHaryana State Higher Education Council (HSHEC)\n"
            f"Government of Haryana"
        )

        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
            <div style="text-align: center; margin-bottom: 24px; border-bottom: 2px solid #600b0b; padding-bottom: 16px;">
                <h2 style="color: #600b0b; margin: 0; font-size: 20px;">Haryana State Higher Education Council</h2>
                <p style="color: #64748b; font-size: 13px; margin: 4px 0 0; font-weight: 600;">NEP EXCELLENCE AWARDS 2026</p>
            </div>
            <p style="font-size: 15px; color: #1e293b;">Dear <strong>{user.full_name}</strong>,</p>
            <p style="font-size: 14px; color: #334155; line-height: 1.6;">
                Thank you for initiating registration on the official HSHEC Haryana Excellence Awards Portal.
                To complete your applicant verification, please confirm your email address.
            </p>
            <div style="text-align: center; margin: 28px 0;">
                <a href="{verification_link}" style="background-color: #600b0b; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 14px; display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            <p style="font-size: 13px; color: #64748b; line-height: 1.5;">
                Or copy and paste this secure link into your browser:<br/>
                <a href="{verification_link}" style="color: #600b0b; word-break: break-all; font-size: 12px;">{verification_link}</a>
            </p>
            <div style="margin-top: 24px; padding: 12px 16px; background-color: #fffbeb; border: 1px solid #fef3c7; border-radius: 8px; font-size: 12px; color: #92400e; line-height: 1.5;">
                <strong>Governance Notice:</strong> Email verification establishes your identity. Institutional assessment access remains subject to State DHE Administrator approval.
            </div>
            <p style="font-size: 11px; color: #94a3b8; margin-top: 24px; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 12px;">
                This link will expire in 24 hours. If you did not create an account, no further action is required.
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
            logger.error(f"Failed to send verification email to {user.email}: {e}")
            UserAuditLog.objects.create(
                actor=None,
                target_user=user,
                action='NOTIFICATION_FAILED',
                details={'channel': 'EMAIL_VERIFICATION', 'error': str(e)}
            )
            return False

    @classmethod
    def verify_token(cls, raw_token: str) -> Tuple[bool, Optional[EmailVerificationToken], str]:
        """
        Validates token status without consuming it.
        Returns (is_valid, token_obj, reason).
        Reasons: VALID, INVALID_TOKEN, ALREADY_USED, REVOKED_TOKEN, EXPIRED_TOKEN.
        """
        if not raw_token or not isinstance(raw_token, str) or len(raw_token.strip()) < 16:
            return False, None, "INVALID_TOKEN"

        token_hash = cls._hash_token(raw_token.strip())
        token_obj = EmailVerificationToken.objects.filter(token_hash=token_hash).select_related('user').first()

        if not token_obj:
            return False, None, "INVALID_TOKEN"

        if token_obj.is_used:
            return False, token_obj, "ALREADY_USED"

        if token_obj.is_revoked:
            return False, token_obj, "REVOKED_TOKEN"

        if timezone.now() >= token_obj.expires_at:
            return False, token_obj, "EXPIRED_TOKEN"

        return True, token_obj, "VALID"

    @classmethod
    def confirm_email_verification(cls, raw_token: str) -> User:
        """
        Validates and consumes the verification token, marking user.is_email_verified = True.
        Enforces single use and records the audit log.
        Does NOT alter user.institution_status or grant institutional access.
        """
        from django.db import transaction

        is_valid, token_obj, reason = cls.verify_token(raw_token)
        if not is_valid:
            error_map = {
                "EXPIRED_TOKEN": "This verification link has expired. Please request a new verification link.",
                "ALREADY_USED": "This verification link has already been used.",
                "REVOKED_TOKEN": "This verification link has been superseded by a newer link. Please check your inbox.",
                "INVALID_TOKEN": "The verification link is invalid or malformed.",
            }
            err_dict = {
                "detail": error_map.get(reason, "Invalid or expired verification link."),
                "code": reason,
                "reason": reason,
            }
            if reason == "ALREADY_USED" and token_obj:
                user = getattr(token_obj, 'user', None)
                if user and getattr(user, 'is_email_verified', False):
                    err_dict["account_already_verified"] = True
                    err_dict["already_verified"] = True
                    err_dict["email"] = cls.mask_email(user.email)
            raise DRFValidationError(err_dict)

        with transaction.atomic():
            # Lock the token row to prevent race conditions / double consumption
            token = EmailVerificationToken.objects.select_for_update().get(pk=token_obj.pk)
            if token.is_used:
                err_dict = {
                    "detail": "This verification link has already been used.",
                    "code": "ALREADY_USED",
                    "reason": "ALREADY_USED",
                }
                if getattr(token.user, 'is_email_verified', False):
                    err_dict["account_already_verified"] = True
                    err_dict["already_verified"] = True
                    err_dict["email"] = cls.mask_email(token.user.email)
                raise DRFValidationError(err_dict)
            token.is_used = True
            token.used_at = timezone.now()
            token.save(update_fields=['is_used', 'used_at'])

            user = token.user
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])

            UserAuditLog.objects.create(
                actor=user,
                target_user=user,
                action='EMAIL_VERIFIED',
                details={
                    'institution_status': user.institution_status,
                    'role': user.role,
                }
            )

        return user

    @classmethod
    def request_resend_verification(cls, email: str) -> bool:
        """
        Handles requests to resend a verification link.
        - Enforces cooldown and rate limits.
        - Safe against account enumeration: returns generic success whether email exists or not.
        - Fails safely if email delivery fails for a known unverified user.
        """
        norm_email = (email or '').strip().lower()
        if not norm_email or '@' not in norm_email:
            raise DRFValidationError({'email': 'A valid email address is required.'})

        email_hash = hashlib.sha256(norm_email.encode('utf-8')).hexdigest()[:16]
        cooldown_key = f"email_verify_cooldown_{email_hash}"
        rate_key = f"email_verify_rate_{email_hash}"

        if cache.get(cooldown_key):
            raise VerificationCooldownError(
                "A verification link was recently requested for this email. Please wait 60 seconds before requesting another.",
                retry_after=60
            )

        hourly_count = cache.get(rate_key, 0)
        if hourly_count >= cls.MAX_SENDS_PER_HOUR:
            raise VerificationRateLimitError(
                "Too many verification requests for this address. Please check your spam folder or try again later.",
                retry_after=3600
            )

        user = User.objects.filter(email__iexact=norm_email).first()

        # Anti-enumeration timing defense: set cooldown and increment regardless of existence
        cache.set(cooldown_key, True, cls.COOLDOWN_SECONDS)
        cache.set(rate_key, hourly_count + 1, 3600)

        if user and not user.is_email_verified:
            raw_token, _ = cls.create_verification_token(user)
            delivered = cls.send_verification_email(user, raw_token)
            if not delivered:
                # Clear cooldown so retry is possible after delivery failure
                cache.delete(cooldown_key)
                raise EmailDeliveryError(
                    "Verification email delivery failed. Please check your mail service or try again later."
                )
            UserAuditLog.objects.create(
                actor=user,
                target_user=user,
                action='EMAIL_VERIFICATION_RESENT',
                details={'email': norm_email}
            )

        return True
