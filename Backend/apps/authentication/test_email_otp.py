"""
Tests for 6-Digit Email OTP Verification Flow, Security Invariants, Rate Limiting,
and Backward Compatibility.
"""
import datetime
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import College, EmailOTPVerification, EmailVerificationToken, UserAuditLog
from apps.authentication.email_otp_service import EmailOTPService, EmailOTPError
from apps.university.models import University

User = get_user_model()


class EmailOTPVerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        self.client = APIClient()
        self.college = College.objects.create(name="Government College Karnal", aishe_code="C-20001")
        self.university = University.objects.create(
            name="Kurukshetra University, Kurukshetra",
            aishe_code="U-0160",
            university_type="State Public University",
            state="Haryana",
            is_active=True,
        )

    def test_signup_automatically_triggers_otp_issuance_and_email(self):
        """1. Successful signup automatically triggers OTP issuance and email sending."""
        payload = {
            "fullName": "Dr. OTP Applicant",
            "email": "otp.applicant@college.edu.in",
            "collegeId": self.college.id,
            "role": "principal",
            "password": "SecurePassword123!",
            "phoneNumber": "9876543210",
        }
        res = self.client.post(reverse("signup"), payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data.get("verification_sent"))
        self.assertEqual(res.data.get("redirect_to"), "/auth/verify-email/otp")
        self.assertFalse(res.data["user"]["is_email_verified"])
        self.assertEqual(res.data["user"]["institution_status"], "PENDING")
        self.assertNotIn("tokens", res.data)

        # Check DB record
        user = User.objects.get(email="otp.applicant@college.edu.in")
        self.assertFalse(user.is_email_verified)

        # Check EmailOTPVerification challenge created
        challenge = EmailOTPVerification.objects.filter(user=user, is_verified=False).first()
        self.assertIsNotNone(challenge)
        self.assertEqual(len(challenge.otp_hash), 64)
        self.assertEqual(challenge.attempt_count, 0)

        # Check email was dispatched
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn("otp.applicant@college.edu.in", sent.to)
        self.assertIn("Verify Your Email Address", sent.subject)
        self.assertIn("/auth/verify-email/otp", sent.body)

    def test_valid_otp_verifies_account_and_redirects_to_login(self):
        """3 & 4. Valid 6-digit OTP verifies the account, logs audit entry, and does not return JWT tokens."""
        user = User.objects.create_user(
            email="valid.code@college.edu.in",
            full_name="Valid Code Tester",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
            requested_college=self.college,
        )

        with patch.object(EmailOTPService, "generate_otp", return_value="482910"):
            EmailOTPService.send_verification_otp(user)

        res = self.client.post(reverse("email-otp-verify"), {
            "email": "valid.code@college.edu.in",
            "otp": "482910"
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("success"))
        self.assertTrue(res.data.get("is_email_verified"))
        self.assertEqual(res.data.get("redirect_to"), "/auth/login")
        self.assertNotIn("tokens", res.data)

        # User is now verified in DB
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertEqual(user.institution_status, "PENDING")  # Institution approval unchanged

        # Audit log entry exists
        audit = UserAuditLog.objects.filter(target_user=user, action="EMAIL_OTP_VERIFIED").first()
        self.assertIsNotNone(audit)

    def test_leading_zero_otp_works_correctly(self):
        """6. Leading-zero OTPs (e.g., 007123) are preserved and verified correctly without truncation."""
        user = User.objects.create_user(
            email="leading.zero@college.edu.in",
            full_name="Agent 007",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
        )

        with patch.object(EmailOTPService, "generate_otp", return_value="007123"):
            EmailOTPService.send_verification_otp(user)

        res = self.client.post(reverse("email-otp-verify"), {
            "email": "leading.zero@college.edu.in",
            "otp": "007123"
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_incorrect_otp_increments_attempts_and_locks_on_limit(self):
        """5 & 10. Incorrect OTP increments attempt counter and rejects; 5 failures lock the code."""
        user = User.objects.create_user(
            email="incorrect.otp@college.edu.in",
            full_name="Mistake Prone",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
        )

        with patch.object(EmailOTPService, "generate_otp", return_value="654321"):
            EmailOTPService.send_verification_otp(user)

        # 4 incorrect attempts
        for i in range(4):
            res = self.client.post(reverse("email-otp-verify"), {
                "email": "incorrect.otp@college.edu.in",
                "otp": "111111"
            }, format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(res.data.get("code"), "OTP_INCORRECT")

        # 5th incorrect attempt exceeds max attempts
        res = self.client.post(reverse("email-otp-verify"), {
            "email": "incorrect.otp@college.edu.in",
            "otp": "111111"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(res.data.get("code"), "OTP_ATTEMPTS_EXCEEDED")

        # Code is revoked in DB
        challenge = EmailOTPVerification.objects.filter(user=user).first()
        self.assertTrue(challenge.is_revoked)

    def test_expired_otp_is_rejected(self):
        """5. Expired OTPs (> 10 mins) are rejected."""
        user = User.objects.create_user(
            email="expired.otp@college.edu.in",
            full_name="Late Arriver",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
        )

        with patch.object(EmailOTPService, "generate_otp", return_value="123456"):
            challenge, _ = EmailOTPService.send_verification_otp(user)

        # Fast-forward challenge expiration to past
        challenge.expires_at = timezone.now() - datetime.timedelta(minutes=1)
        challenge.save(update_fields=["expires_at"])

        res = self.client.post(reverse("email-otp-verify"), {
            "email": "expired.otp@college.edu.in",
            "otp": "123456"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "OTP_EXPIRED")

    def test_consumed_otp_cannot_be_reused(self):
        """7. Reused or consumed OTPs cannot verify an account again."""
        user = User.objects.create_user(
            email="reused.otp@college.edu.in",
            full_name="Reused Tester",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
        )

        with patch.object(EmailOTPService, "generate_otp", return_value="998877"):
            EmailOTPService.send_verification_otp(user)

        # First verification succeeds
        res1 = self.client.post(reverse("email-otp-verify"), {
            "email": "reused.otp@college.edu.in",
            "otp": "998877"
        }, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Second verification reports already verified
        res2 = self.client.post(reverse("email-otp-verify"), {
            "email": "reused.otp@college.edu.in",
            "otp": "998877"
        }, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data.get("already_verified"))

    def test_resend_invalidates_previous_otp_and_enforces_cooldown(self):
        """8, 9 & 10. Resending generates a new code, revokes old code, and enforces 60s cooldown."""
        user = User.objects.create_user(
            email="resend.otp@college.edu.in",
            full_name="Resend User",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
        )

        with patch.object(EmailOTPService, "generate_otp", return_value="112233"):
            EmailOTPService.send_verification_otp(user)

        # Immediate resend triggers 60s cooldown
        res_cooldown = self.client.post(reverse("email-otp-resend"), {
            "email": "resend.otp@college.edu.in"
        }, format="json")
        self.assertEqual(res_cooldown.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(res_cooldown.data.get("code"), "OTP_COOLDOWN")

        # Clear cooldown in cache
        cache.clear()

        # Resend succeeds with new code
        with patch.object(EmailOTPService, "generate_otp", return_value="445566"):
            res_resend = self.client.post(reverse("email-otp-resend"), {
                "email": "resend.otp@college.edu.in"
            }, format="json")
            self.assertEqual(res_resend.status_code, status.HTTP_200_OK)

        # Old code 112233 is now invalid
        res_old = self.client.post(reverse("email-otp-verify"), {
            "email": "resend.otp@college.edu.in",
            "otp": "112233"
        }, format="json")
        self.assertEqual(res_old.status_code, status.HTTP_400_BAD_REQUEST)

        # New code 445566 works
        res_new = self.client.post(reverse("email-otp-verify"), {
            "email": "resend.otp@college.edu.in",
            "otp": "445566"
        }, format="json")
        self.assertEqual(res_new.status_code, status.HTTP_200_OK)

    def test_direct_verification_request_without_signup(self):
        """14. Direct verification requests work for unverified users without creating new accounts."""
        user = User.objects.create_user(
            email="direct.req@college.edu.in",
            full_name="Direct Requester",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
        )
        initial_count = User.objects.count()

        res = self.client.post(reverse("email-otp-request"), {
            "email": "direct.req@college.edu.in"
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("success"))
        self.assertFalse(res.data.get("already_verified"))
        self.assertEqual(User.objects.count(), initial_count)

    def test_anti_enumeration_on_non_existent_email(self):
        """13 & 15. Non-existent email receives identical generic response without revealing account status."""
        initial_count = User.objects.count()
        res = self.client.post(reverse("email-otp-request"), {
            "email": "nonexistent.ghost@college.edu.in"
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("success"))
        self.assertFalse(res.data.get("already_verified"))
        # No account was created
        self.assertEqual(User.objects.count(), initial_count)

    def test_already_verified_account_direct_request(self):
        """15. Already-verified account receives clear already_verified response without sending an OTP."""
        mail.outbox.clear()
        User.objects.create_user(
            email="already.done@college.edu.in",
            full_name="Already Done",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=True,
            institution_status="VERIFIED",
        )

        res = self.client.post(reverse("email-otp-request"), {
            "email": "already.done@college.edu.in"
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("already_verified"))
        self.assertEqual(res.data.get("message"), "This email address is already verified. Please sign in to your account.")
        self.assertEqual(res.data.get("redirect_to"), "/auth/login")
        self.assertEqual(len(mail.outbox), 0)

    def test_already_verified_account_resend_request(self):
        """Already-verified account resend returns already_verified response without sending an OTP."""
        mail.outbox.clear()
        User.objects.create_user(
            email="already.resend@college.edu.in",
            full_name="Already Resend",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=True,
            institution_status="VERIFIED",
        )

        res = self.client.post(reverse("email-otp-resend"), {
            "email": "already.resend@college.edu.in"
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("already_verified"))
        self.assertEqual(res.data.get("message"), "This email address is already verified. Please sign in to your account.")
        self.assertEqual(res.data.get("redirect_to"), "/auth/login")
        self.assertEqual(len(mail.outbox), 0)

    def test_otp_is_never_leaked_in_responses(self):
        """16. OTPs and sensitive hashes are never exposed in any API response."""
        payload = {
            "fullName": "Leak Test",
            "email": "leak.test@college.edu.in",
            "collegeId": self.college.id,
            "role": "principal",
            "password": "SecurePassword123!",
        }
        res_signup = self.client.post(reverse("signup"), payload, format="json")
        response_str = str(res_signup.data)
        self.assertNotIn("otp_hash", response_str)
        self.assertNotIn("raw_otp", response_str)

        cache.clear()
        res_resend = self.client.post(reverse("email-otp-resend"), {"email": "leak.test@college.edu.in"}, format="json")
        resend_str = str(res_resend.data)
        self.assertNotIn("otp_hash", resend_str)
        self.assertNotIn("raw_otp", resend_str)

    def test_verified_user_can_login(self):
        """Verified user can successfully log in and receive auth tokens."""
        user = User.objects.create_user(
            email="login.ready@college.edu.in",
            full_name="Login Ready",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
            requested_college=self.college,
        )

        with patch.object(EmailOTPService, "generate_otp", return_value="771122"):
            EmailOTPService.send_verification_otp(user)

        # Verify
        self.client.post(reverse("email-otp-verify"), {
            "email": "login.ready@college.edu.in",
            "otp": "771122"
        }, format="json")

        # Login
        login_res = self.client.post(reverse("login"), {
            "email": "login.ready@college.edu.in",
            "password": "SecurePassword123!"
        }, format="json")

        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", login_res.data)
        self.assertIn("access", login_res.data["tokens"])
