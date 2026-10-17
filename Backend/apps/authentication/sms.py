"""
SMS delivery abstraction for mobile OTP.

settings.SMS_BACKEND names a class with `send(phone_number, message)`. It returns a provider message id and
raises SMSDeliveryError when the message was not accepted, so callers never report a delivery that did not
happen. Shipped backends:

- DisabledSMSBackend   default; always fails (no provider configured: fail closed)
- LocmemSMSBackend     tests; appends to `outbox` (like django.core.mail.outbox)
- ConsoleSMSBackend    local development only; prints the message to the runserver console

A production provider (MSG91, Gupshup, Twilio, ...) is added by subclassing BaseSMSBackend with the
provider's DLT-registered sender id and template; config.settings.production refuses the dev backends.
"""
import logging

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

outbox = []


class SMSDeliveryError(Exception):
    """The SMS was not accepted for delivery."""


class BaseSMSBackend:
    def send(self, phone_number: str, message: str) -> str:
        raise NotImplementedError


class DisabledSMSBackend(BaseSMSBackend):
    def send(self, phone_number, message):
        raise SMSDeliveryError("No SMS provider is configured (SMS_BACKEND).")


class LocmemSMSBackend(BaseSMSBackend):
    def send(self, phone_number, message):
        outbox.append({"to": phone_number, "message": message})
        return f"locmem-{len(outbox)}"


class ConsoleSMSBackend(BaseSMSBackend):
    def send(self, phone_number, message):
        if not settings.DEBUG:
            raise SMSDeliveryError("The console SMS backend is only available when DEBUG is enabled.")
        print(f"[DEV SMS to ******{phone_number[-4:]}] {message}", flush=True)
        return "console"


def send_sms(phone_number: str, message: str) -> str:
    backend = import_string(getattr(settings, "SMS_BACKEND", "apps.authentication.sms.DisabledSMSBackend"))()
    try:
        return backend.send(phone_number, message)
    except SMSDeliveryError:
        raise
    except Exception as exc:  # provider/network failure: never surface as success
        logger.error("SMS provider error for ******%s: %s", phone_number[-4:], type(exc).__name__)
        raise SMSDeliveryError("SMS provider error.") from exc
