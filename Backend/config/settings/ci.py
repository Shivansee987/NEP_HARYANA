"""
Settings for the automated test run in CI (and for local full-suite runs).

Development settings plus: a fast password hasher (the default PBKDF2 makes the ~850-test suite take ~40 minutes),
and in-memory e-mail and SMS backends so no message can leave the machine.
"""
from .development import *  # noqa: F401,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
SMS_BACKEND = "apps.authentication.sms.LocmemSMSBackend"
