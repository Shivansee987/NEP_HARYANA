import secrets
import hashlib
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import User, AccountActivationToken, UserAuditLog, RefreshToken

logger = logging.getLogger(__name__)


class InvitationNotAllowedError(Exception):
    """Activation invitations are only for accounts that have never set a password."""


def is_pending_activation(user) -> bool:
    return not user.has_usable_password()


class AccountActivationService:
    """
    Secure Account Activation Lifecycle Service.
    Enforces cryptographic single-use expiring token storage, password validation,
    generic error protection, and audit logging.
    """

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    @classmethod
    def create_invitation(cls, user: User, created_by: User = None, validity_hours: int = 48):
        """
        Generates a cryptographically secure, single-use, expiring activation token.
        Stores only the SHA-256 hash. The raw token is returned once for email delivery.
        Refused for accounts that already have a password: an invitation must never be a way to overwrite an
        existing (active or deactivated) account's credentials. Those use the password-reset flow instead.
        """
        if not is_pending_activation(user):
            raise InvitationNotAllowedError(
                "This account has already been activated. Use a password reset link instead of an invitation."
            )
        # Revoke any outstanding unconsumed tokens for this user
        AccountActivationToken.objects.filter(
            user=user,
            is_used=False,
            is_revoked=False
        ).update(is_revoked=True)

        raw_token = secrets.token_urlsafe(32)
        token_hash = cls._hash_token(raw_token)
        expires_at = timezone.now() + timedelta(hours=validity_hours)

        token_obj = AccountActivationToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
            created_by=created_by,
        )

        UserAuditLog.objects.create(
            actor=created_by,
            target_user=user,
            action='INVITATION_CREATED',
            details={
                'role': user.role,
                'validity_hours': validity_hours,
                'expires_at': expires_at.isoformat(),
            }
        )

        return raw_token, token_obj

    @classmethod
    def send_invitation_email(cls, user: User, raw_token: str) -> bool:
        """
        Dispatches activation invitation email with secure activation link.
        Never logs or exposes the raw token.
        """
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
        activation_link = f"{frontend_url}/auth/activate/{raw_token}"

        subject = "Account Activation — HSHEC Haryana Excellence Awards Portal"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@haryana.gov.in')

        text_content = (
            f"Dear {user.full_name},\n\n"
            f"An administrative account has been provisioned for you on the NEP Haryana Excellence Awards Portal.\n"
            f"Role: {user.get_role_display()}\n\n"
            f"Please activate your account and establish your security password by visiting the following link:\n"
            f"{activation_link}\n\n"
            f"This activation link is single-use and will expire in 48 hours.\n"
            f"If you did not request or expect this account, please contact the HSHEC platform administrator.\n\n"
            f"Regards,\nHaryana State Higher Education Council (HSHEC)"
        )

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h2 style="color: #600b0b; margin: 0;">HSHEC Haryana Excellence Awards</h2>
                <p style="color: #64748b; font-size: 14px; margin: 4px 0 0;">Official Administrative Account Activation</p>
            </div>
            <p>Dear <strong>{escape(user.full_name)}</strong>,</p>
            <p>An official administrative profile has been provisioned for you on the portal:</p>
            <div style="background-color: #f8fafc; padding: 12px 16px; border-radius: 8px; margin: 16px 0; border: 1px solid #e2e8f0;">
                <p style="margin: 4px 0;"><strong>Email:</strong> {escape(user.email)}</p>
                <p style="margin: 4px 0;"><strong>Role:</strong> {user.get_role_display()}</p>
            </div>
            <p>Please click the button below to establish your password and activate your account:</p>
            <div style="text-align: center; margin: 28px 0;">
                <a href="{activation_link}" style="background-color: #600b0b; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                    Activate Account & Set Password
                </a>
            </div>
            <p style="font-size: 12px; color: #64748b; line-height: 1.5;">
                This link is single-use and will expire in 48 hours.<br/>
                If the button above does not work, copy and paste this URL into your browser:<br/>
                <span style="word-break: break-all; color: #600b0b;">{activation_link}</span>
            </p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
            <p style="font-size: 11px; color: #94a3b8; text-align: center; margin: 0;">
                Haryana State Higher Education Council &bull; Directorate of Higher Education, Haryana
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
            msg.send()
            return True
        except Exception as e:
            logger.error("Failed to deliver activation email to user %s: %s", user.pk, type(e).__name__)
            return False

    @classmethod
    def verify_token(cls, raw_token: str):
        """
        Validates token existence, expiry, and single-use state.
        Returns (is_valid, token_obj, reason_code).
        """
        if not raw_token or not isinstance(raw_token, str):
            return False, None, "INVALID_TOKEN"

        token_hash = cls._hash_token(raw_token.strip())
        token_obj = AccountActivationToken.objects.filter(token_hash=token_hash).first()

        if not token_obj:
            return False, None, "INVALID_TOKEN"

        if token_obj.is_revoked:
            return False, token_obj, "REVOKED_TOKEN"

        if token_obj.is_used:
            return False, token_obj, "ALREADY_USED"

        if timezone.now() >= token_obj.expires_at:
            return False, token_obj, "EXPIRED_TOKEN"

        return True, token_obj, "VALID"

    @classmethod
    def activate_account(cls, raw_token: str, password: str, confirm_password: str):
        """
        Sets user password, validates strength, marks token used, and activates account.
        """
        if not password or not confirm_password:
            raise DRFValidationError({"detail": "Password and confirmation password are required."})

        if password != confirm_password:
            raise DRFValidationError({"detail": "Passwords do not match."})

        is_valid, token_obj, reason = cls.verify_token(raw_token)
        if not is_valid:
            error_messages = {
                "EXPIRED_TOKEN": "This activation link has expired. Please contact your administrator for a new invitation.",
                "ALREADY_USED": "This activation link has already been used. Please sign in with your password.",
                "REVOKED_TOKEN": "This activation link has been revoked. Please request a new invitation.",
                "INVALID_TOKEN": "Invalid activation link.",
            }
            raise DRFValidationError({"detail": error_messages.get(reason, "Invalid or expired activation link.")})

        user = token_obj.user
        if not is_pending_activation(user):
            # Already activated (or deactivated after activation): an old or re-issued invitation must not reset
            # the password or re-enable the account.
            token_obj.is_revoked = True
            token_obj.save(update_fields=['is_revoked'])
            raise DRFValidationError({"detail": "This account has already been activated. Please sign in or use 'Forgot password'."})

        # Validate password using Django's configured password validators
        try:
            validate_password(password, user)
        except ValidationError as e:
            raise DRFValidationError({"detail": e.messages[0]})

        # Activate user, mark email verified, and set password
        user.set_password(password)
        user.is_active = True
        user.is_email_verified = True
        user.save()

        # Mark token consumed
        token_obj.is_used = True
        token_obj.used_at = timezone.now()
        token_obj.save()

        # Invalidate any other tokens for this user
        AccountActivationToken.objects.filter(
            user=user,
            is_used=False
        ).exclude(pk=token_obj.pk).update(is_revoked=True)

        # End any stale sessions
        user.revoke_sessions()

        # Log audit trail
        UserAuditLog.objects.create(
            actor=user,
            target_user=user,
            action='ACCOUNT_ACTIVATED',
            details={
                'method': 'SECURE_INVITATION_TOKEN',
                'role': user.role,
            }
        )

        return user

    @classmethod
    def resend_invitation(cls, user: User, actor: User = None):
        """
        Generates a fresh token, revoking existing pending tokens, and resends email.
        """
        raw_token, token_obj = cls.create_invitation(user, created_by=actor)
        email_sent = cls.send_invitation_email(user, raw_token)

        UserAuditLog.objects.create(
            actor=actor,
            target_user=user,
            action='INVITATION_RESENT',
            details={
                'email_sent': email_sent,
                'role': user.role,
            }
        )

        return email_sent

    @classmethod
    def revoke_invitation(cls, user: User, actor: User = None):
        """
        Revokes all pending activation tokens for a user.
        """
        count = AccountActivationToken.objects.filter(
            user=user,
            is_used=False,
            is_revoked=False
        ).update(is_revoked=True)

        UserAuditLog.objects.create(
            actor=actor,
            target_user=user,
            action='INVITATION_REVOKED',
            details={'revoked_count': count}
        )

        return True
