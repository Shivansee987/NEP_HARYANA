"""
S-02 (security review 2026-10-21): user-supplied names must never become markup in the portal's own e-mails, and
public registration refuses names that carry markup or links.
"""
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.authentication.activation_service import AccountActivationService
from apps.authentication.email_otp_service import EmailOTPService
from apps.authentication.email_verification_service import EmailVerificationService
from apps.authentication.models import College, User

PAYLOAD = '<a href="https://evil.example/login">Click here</a>'


def _html_part(message):
    return next(content for content, mimetype in message.alternatives if mimetype == 'text/html')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailMarkupEscapingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="applicant@example.com", full_name=PAYLOAD, role="principal", password="x-Str0ng!Passw0rd",
            is_email_verified=False,
        )

    def _assert_escaped(self):
        html = _html_part(mail.outbox[-1])
        self.assertNotIn(PAYLOAD, html)
        self.assertNotIn('href="https://evil.example', html)
        self.assertIn('&lt;a href=', html)

    def test_otp_email_escapes_name(self):
        EmailOTPService._dispatch_email(user=self.user, raw_otp="123456", expires_minutes=10)
        self._assert_escaped()

    def test_verification_email_escapes_name(self):
        EmailVerificationService.send_verification_email(self.user, raw_token="tok", raw_otp="123456")
        self._assert_escaped()

    def test_activation_email_escapes_name(self):
        AccountActivationService.send_invitation_email(self.user, raw_token="tok")
        self._assert_escaped()

    def test_email_in_link_is_url_encoded(self):
        self.user.email = "a+b@example.com"
        self.user.save()
        EmailOTPService._dispatch_email(user=self.user, raw_otp="123456", expires_minutes=10)
        self.assertIn("otp?email=a%2Bb%40example.com", _html_part(mail.outbox[-1]))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RegistrationNameValidationTests(TestCase):
    def setUp(self):
        self.college = College.objects.create(name="Requested College")
        self.client = APIClient()

    def _signup(self, name, email):
        return self.client.post("/api/auth/signup/", {
            "fullName": name, "email": email, "password": "Str0ng!Passw0rd#2026",
            "collegeId": self.college.id, "role": "principal"}, format="json")

    def test_markup_and_links_are_refused(self):
        for i, name in enumerate([PAYLOAD, "Visit https://evil.example", "Dr <b>X</b>", "www.evil.example now"]):
            response = self._signup(name, f"bad{i}@example.com")
            self.assertEqual(response.status_code, 400, name)
            self.assertIn("fullName", response.json())
        self.assertEqual(len(mail.outbox), 0)

    def test_ordinary_names_are_accepted(self):
        for i, name in enumerate(["Dr. A. K. Sharma", "Anne-Marie O'Neil", "डॉ. राजेश कुमार"]):
            response = self._signup(name, f"ok{i}@example.com")
            self.assertIn(response.status_code, (200, 201), (name, response.content[:200]))
