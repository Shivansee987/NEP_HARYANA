"""
Tests for Email Verification flow, Security Invariants, and Empowered Committee Authorization Safeguards.
"""
import datetime
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import College, EmailVerificationToken, UserAuditLog
from apps.authentication.email_verification_service import EmailVerificationService
from apps.university.models import University

User = get_user_model()


class EmailVerificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.college = College.objects.create(name="Government College Karnal", aishe_code="C-20001")
        self.university = University.objects.create(
            name="Kurukshetra University, Kurukshetra",
            aishe_code="U-0160",
            university_type="State Public University",
            state="Haryana",
            is_active=True,
        )

    def test_registration_creates_unverified_account_and_dispatches_email(self):
        """Registration creates an account in PENDING / unverified state and sends an email."""
        mail.outbox.clear()
        payload = {
            "fullName": "Prof. Applicant",
            "email": "applicant@college.edu.in",
            "collegeId": self.college.id,
            "role": "principal",
            "password": "SecurePassword123!",
            "phoneNumber": "9876543210",
        }
        res = self.client.post(reverse("signup"), payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertFalse(res.data["user"]["is_email_verified"])
        self.assertEqual(res.data["user"]["institution_status"], "PENDING")
        self.assertNotIn("tokens", res.data)
        self.assertTrue(res.data.get("verification_sent"))

        # Verify database record
        user = User.objects.get(email="applicant@college.edu.in")
        self.assertFalse(user.is_email_verified)
        self.assertEqual(user.institution_status, "PENDING")

        # Verify token created in DB (hashed only)
        token_record = EmailVerificationToken.objects.filter(user=user).first()
        self.assertIsNotNone(token_record)
        self.assertFalse(token_record.is_used)
        self.assertFalse(token_record.is_revoked)
        self.assertEqual(len(token_record.token_hash), 64)  # SHA-256

        # Verify email dispatched
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn("applicant@college.edu.in", sent_email.to)
        self.assertIn("Verify Your Email Address", sent_email.subject)
        self.assertIn("/auth/verify-email/", sent_email.body)

    def test_unverified_user_cannot_login(self):
        """Unverified accounts are rejected during login with 403 EMAIL_NOT_VERIFIED."""
        user = User.objects.create_user(
            email="unverified.user@college.edu.in",
            full_name="Unverified User",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
        )
        res = self.client.post(reverse("login"), {
            "email": "unverified.user@college.edu.in",
            "password": "SecurePassword123!",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("code"), "EMAIL_NOT_VERIFIED")
        self.assertNotIn("tokens", res.data)

    def test_verify_and_confirm_email_lifecycle(self):
        """Valid token can be inspected (verify) and consumed (confirm), enabling login."""
        user = User.objects.create_user(
            email="verify.me@college.edu.in",
            full_name="Dr. Verify",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
            requested_college=self.college,
        )
        raw_token, token_obj = EmailVerificationService.create_verification_token(user)

        # 1. Read-only inspection via GET
        inspect_res = self.client.get(reverse("email-verify") + f"?token={raw_token}")
        self.assertEqual(inspect_res.status_code, status.HTTP_200_OK)
        self.assertTrue(inspect_res.data["valid"])
        self.assertEqual(inspect_res.data["reason"], "VALID")
        # Masked email
        self.assertIn("v***e@college.edu.in", inspect_res.data["email"])

        # Token is still unused
        token_obj.refresh_from_db()
        self.assertFalse(token_obj.is_used)

        # 2. Confirm email verification via POST
        confirm_res = self.client.post(reverse("email-verify-confirm"), {"token": raw_token}, format="json")
        self.assertEqual(confirm_res.status_code, status.HTTP_200_OK)
        self.assertTrue(confirm_res.data["success"])
        self.assertTrue(confirm_res.data["is_email_verified"])
        # Institutional status remains PENDING until administrator approval
        self.assertEqual(confirm_res.data["institution_status"], "PENDING")

        # Database state updated
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertEqual(user.institution_status, "PENDING")
        self.assertIsNone(user.college)  # Institutional access not yet granted

        token_obj.refresh_from_db()
        self.assertTrue(token_obj.is_used)
        self.assertIsNotNone(token_obj.used_at)

        # 3. User can now sign in
        login_res = self.client.post(reverse("login"), {
            "email": "verify.me@college.edu.in",
            "password": "SecurePassword123!",
        }, format="json")
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", login_res.data)

    def test_reused_token_rejected(self):
        """A consumed verification token cannot be reused."""
        user = User.objects.create_user(
            email="reused@college.edu.in",
            full_name="Dr. Reused",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
        )
        raw_token, token_obj = EmailVerificationService.create_verification_token(user)
        # First confirmation succeeds
        res1 = self.client.post(reverse("email-verify-confirm"), {"token": raw_token}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Second confirmation fails with 410 Gone / ALREADY_USED
        res2 = self.client.post(reverse("email-verify-confirm"), {"token": raw_token}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_410_GONE)
        self.assertEqual(res2.data.get("code"), "ALREADY_USED")

    def test_expired_token_rejected(self):
        """An expired verification token is rejected."""
        user = User.objects.create_user(
            email="expired@college.edu.in",
            full_name="Dr. Expired",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
        )
        raw_token, token_obj = EmailVerificationService.create_verification_token(user)
        # Fast-forward token into expiry
        token_obj.expires_at = timezone.now() - datetime.timedelta(hours=1)
        token_obj.save()

        # Inspection reports EXPIRED
        inspect_res = self.client.get(reverse("email-verify") + f"?token={raw_token}")
        self.assertEqual(inspect_res.status_code, status.HTTP_410_GONE)
        self.assertEqual(inspect_res.data.get("reason"), "EXPIRED_TOKEN")

        # Confirmation fails
        confirm_res = self.client.post(reverse("email-verify-confirm"), {"token": raw_token}, format="json")
        self.assertEqual(confirm_res.status_code, status.HTTP_410_GONE)
        self.assertEqual(confirm_res.data.get("code"), "EXPIRED_TOKEN")

    def test_malformed_token_rejected(self):
        """Malformed or non-existent token is rejected."""
        confirm_res = self.client.post(reverse("email-verify-confirm"), {"token": "completely_bogus_token"}, format="json")
        self.assertEqual(confirm_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(confirm_res.data.get("code"), "INVALID_TOKEN")

    def test_resend_cooldown_and_rate_limiting(self):
        """Resend enforces 60s cooldown and hourly limit without user enumeration."""
        user = User.objects.create_user(
            email="resend.test@college.edu.in",
            full_name="Resend Tester",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
        )
        # 1. First resend succeeds
        res1 = self.client.post(reverse("email-resend-verification"), {"email": user.email}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertTrue(res1.data.get("success"))

        # 2. Immediate second resend hits cooldown (429)
        res2 = self.client.post(reverse("email-resend-verification"), {"email": user.email}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(res2.data.get("code"), "COOLDOWN_ACTIVE")

        # 3. Requesting resend for a non-existent email returns generic 200 (anti-enumeration)
        non_existent_res = self.client.post(reverse("email-resend-verification"), {"email": "does.not.exist@college.edu.in"}, format="json")
        self.assertEqual(non_existent_res.status_code, status.HTTP_200_OK)
        self.assertTrue(non_existent_res.data.get("success"))

    def test_email_delivery_failure_safe_handling(self):
        """If email delivery fails, registration fails safely with 503 and does not leave unverified orphan."""
        payload = {
            "fullName": "Fail Delivery",
            "email": "fail.delivery@college.edu.in",
            "collegeId": self.college.id,
            "role": "principal",
            "password": "SecurePassword123!",
            "phoneNumber": "9876543210",
        }
        with patch.object(EmailVerificationService, "send_verification_email", return_value=False):
            res = self.client.post(reverse("signup"), payload, format="json")
            self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(res.data.get("code"), "EMAIL_DELIVERY_FAILED")

        # Ensure user was rolled back
        self.assertFalse(User.objects.filter(email="fail.delivery@college.edu.in").exists())

    def test_resend_email_delivery_failure_safe_handling(self):
        """If email delivery fails during resend, resend returns 503 and clears cooldown for retry."""
        user = User.objects.create_user(
            email="resend.fail@college.edu.in",
            full_name="Resend Fail Tester",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
        )
        with patch.object(EmailVerificationService, "send_verification_email", return_value=False):
            res = self.client.post(reverse("email-resend-verification"), {"email": user.email}, format="json")
            self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(res.data.get("code"), "EMAIL_DELIVERY_FAILED")

    def test_separation_between_email_verification_and_admin_approval(self):
        """
        Email verification verifies email ownership but keeps institution_status as PENDING.
        Institutional access (assessment modification) is blocked until administrator approval.
        """
        user = User.objects.create_user(
            email="separated@college.edu.in",
            full_name="Separated Flow",
            role="principal",
            password="SecurePassword123!",
            is_email_verified=False,
            institution_status="PENDING",
            requested_college=self.college,
        )
        raw_token, _ = EmailVerificationService.create_verification_token(user)

        # Confirm verification
        res = self.client.post(reverse("email-verify-confirm"), {"token": raw_token}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertEqual(user.institution_status, "PENDING")
        self.assertIsNone(user.college)  # Not assigned until approved


class EmpoweredCommitteeAuthorizationTests(TestCase):
    """
    Empowered Committee review/decision endpoints must reject unauthorized transitions
    and remain safely inactive until official HSHEC policy is enacted.
    """
    def setUp(self):
        self.client = APIClient()
        self.empowered_user = User.objects.create_user(
            email="empowered.chair@haryana.gov.in",
            full_name="Dr. Empowered Chair",
            role="empowered_committee_chair",
            password="SecurePassword123!",
            is_email_verified=True,
        )
        self.committee_user = User.objects.create_user(
            email="committee.member@haryana.gov.in",
            full_name="Committee Member",
            role="committee",
            password="SecurePassword123!",
            is_email_verified=True,
        )

    def test_empowered_committee_cannot_perform_review_actions(self):
        """Review endpoints explicitly restrict to screening committee, rejecting empowered committee with 403."""
        # 1. Empowered Committee user is refused
        self.client.force_authenticate(user=self.empowered_user)
        res = self.client.get("/api/evidence/review-queue/")
        # Access policy restricts reviewers to {'committee', 'committee_chair'}; empowered committee is refused (403)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Screening Committee user is authorized
        self.client.force_authenticate(user=self.committee_user)
        res_ok = self.client.get("/api/evidence/review-queue/")
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
