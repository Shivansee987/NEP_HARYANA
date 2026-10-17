"""Password-reset link delivery shared by self-service recovery and Head-Admin-initiated resets.

Links use Django's default token generator: single-use (the token is bound to the current password hash and
last login), expiring after settings.PASSWORD_RESET_TIMEOUT, and never stored or returned by the API.
"""
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


def build_reset_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
    return f"{frontend_url}/auth/reset-password/{uid}/{token}"


def send_password_reset_email(user) -> bool:
    """Sends the reset link. Returns True only when the mail backend accepted the message."""
    reset_url = build_reset_url(user)
    context = {'user': user, 'reset_url': reset_url}
    try:
        html_content = render_to_string('authentication/password_reset_email.html', context)
        text_content = render_to_string('authentication/password_reset_email.txt', context)
    except Exception:
        html_content = f"<p>Reset link: <a href='{reset_url}'>{reset_url}</a></p>"
        text_content = f"Reset your password at: {reset_url}"
    try:
        msg = EmailMultiAlternatives(
            subject="Reset Your Password - HSHEC NEP Portal",
            body=text_content,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@haryana.gov.in'),
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True
    except Exception as exc:
        logger.error("Failed to send password reset email to user %s: %s", user.pk, type(exc).__name__)
        return False
