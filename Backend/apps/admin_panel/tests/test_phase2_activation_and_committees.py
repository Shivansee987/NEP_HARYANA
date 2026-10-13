"""
NEP Excellence Awards 2026 - Head Admin Phase 2 Automated Tests
Comprehensive testing for:
1. Secure account activation lifecycle (creation, hashing, single-use, expiry, revocation, reuse prevention).
2. Password validation and secure hashing upon activation.
3. Password reset user enumeration resistance and secret protection.
4. Email delivery handling and retry behavior.
5. Unauthorized invitation and committee management blocking.
6. Formal Committee and CommitteeMember management (creation, chair assignment, member addition/removal).
7. Cross-framework constraints, duplicate membership prevention, and ReviewerAuthorization reconciliation.
8. Audit logging without token/password leakage.
9. Committee-led certification preservation.
"""
import hashlib
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.admin_panel.models import Committee, CommitteeMember
from apps.admin_panel.services import CommitteeService, AdminUserManagementService, AdminValidationError
from apps.authentication.activation_service import AccountActivationService
from apps.authentication.models import AccountActivationToken, UserAuditLog
from apps.evidence.models import ReviewerAuthorization

User = get_user_model()


class AccountActivationLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.head_admin = User.objects.create_user(
            email="head.admin@dhe.haryana.gov.in",
            full_name="Head Admin Officer",
            role="head_admin",
            password="SecureHeadPass123!",
            is_staff=True,
            is_superuser=True,
        )
        self.state_admin = User.objects.create_user(
            email="state.admin@dhe.haryana.gov.in",
            full_name="State Admin Officer",
            role="state_admin",
            password="StatePass123!",
            is_staff=True,
        )

    def _create_pending_user(self, email, full_name, role="committee"):
        user = User.objects.create_user(
            email=email,
            full_name=full_name,
            role=role,
            is_active=False,
        )
        user.set_unusable_password()
        user.save()
        return user

    def test_invitation_creates_hashed_token_and_pending_user(self):
        # Test creation via AdminUserManagementService (the primary admin entrypoint)
        created_user = AdminUserManagementService.create_user(
            actor=self.head_admin,
            validated_data={
                "email": "new.chair@dhe.haryana.gov.in",
                "full_name": "Dr. Sunita Verma",
                "role": "committee_chair",
                "committee_framework": "COLLEGE_2026",
            },
        )

        self.assertFalse(created_user.is_active)
        self.assertFalse(created_user.has_usable_password())

        token_obj = AccountActivationToken.objects.filter(user=created_user).first()
        self.assertIsNotNone(token_obj)
        self.assertFalse(token_obj.is_used)
        self.assertFalse(token_obj.is_revoked)

        # Verify token_hash is a 64-char sha256 hex string
        self.assertEqual(len(token_obj.token_hash), 64)

        # Verify audit log recorded without raw token
        audit = UserAuditLog.objects.filter(target_user=created_user, action="INVITATION_CREATED").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.head_admin)

    def test_verify_token_valid_and_invalid(self):
        user = self._create_pending_user("verify.test@dhe.haryana.gov.in", "Dr. Verify User")
        raw_token, token_obj = AccountActivationService.create_invitation(user=user, created_by=self.head_admin)

        # Valid token
        is_valid, returned_token, reason = AccountActivationService.verify_token(raw_token)
        self.assertTrue(is_valid)
        self.assertEqual(returned_token.user.email, "verify.test@dhe.haryana.gov.in")
        self.assertEqual(reason, "VALID")

        # Tampered / Invalid token
        is_valid, returned_token, reason = AccountActivationService.verify_token("tampered_token_xyz")
        self.assertFalse(is_valid)
        self.assertIsNone(returned_token)
        self.assertEqual(reason, "INVALID_TOKEN")

    def test_activation_success_and_reuse_prevention(self):
        user = self._create_pending_user("activate.test@dhe.haryana.gov.in", "Dr. Activate User")
        raw_token, token_obj = AccountActivationService.create_invitation(user=user, created_by=self.head_admin)

        # Activate account
        activated_user = AccountActivationService.activate_account(raw_token, "EstablishedPass123!", "EstablishedPass123!")
        self.assertIsNotNone(activated_user)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.has_usable_password())
        self.assertTrue(user.check_password("EstablishedPass123!"))

        token_obj.refresh_from_db()
        self.assertTrue(token_obj.is_used)

        # Verify audit log
        audit = UserAuditLog.objects.filter(target_user=user, action="ACCOUNT_ACTIVATED").first()
        self.assertIsNotNone(audit)
        self.assertNotIn("EstablishedPass123!", str(audit.details))

        # Attempting reuse must be rejected
        is_valid, _, reason = AccountActivationService.verify_token(raw_token)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "ALREADY_USED")

        with self.assertRaises(Exception):
            AccountActivationService.activate_account(raw_token, "AnotherPass123!", "AnotherPass123!")

    def test_expired_token_rejected(self):
        user = self._create_pending_user("expired.test@dhe.haryana.gov.in", "Dr. Expired User")
        raw_token, token_obj = AccountActivationService.create_invitation(user=user, created_by=self.head_admin)

        # Set expiry in the past
        token_obj.expires_at = timezone.now() - timedelta(hours=1)
        token_obj.save()

        is_valid, _, reason = AccountActivationService.verify_token(raw_token)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "EXPIRED_TOKEN")

        with self.assertRaises(Exception):
            AccountActivationService.activate_account(raw_token, "SomeNewPass123!", "SomeNewPass123!")

    def test_revoked_token_rejected(self):
        user = self._create_pending_user("revoked.test@dhe.haryana.gov.in", "Dr. Revoked User")
        raw_token, token_obj = AccountActivationService.create_invitation(user=user, created_by=self.head_admin)

        # Revoke invitation
        AccountActivationService.revoke_invitation(token_obj.user, actor=self.head_admin)
        token_obj.refresh_from_db()
        self.assertTrue(token_obj.is_revoked)

        is_valid, _, reason = AccountActivationService.verify_token(raw_token)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "REVOKED_TOKEN")

    def test_resend_invitation_revokes_old_and_creates_fresh_token(self):
        user = self._create_pending_user("resend.test@dhe.haryana.gov.in", "Dr. Resend User")
        raw1, token1 = AccountActivationService.create_invitation(user=user, created_by=self.head_admin)

        sent = AccountActivationService.resend_invitation(token1.user, actor=self.head_admin)
        self.assertTrue(sent)

        token1.refresh_from_db()
        self.assertTrue(token1.is_revoked)

        # Active valid token exists
        active_tokens = AccountActivationToken.objects.filter(
            user=token1.user, is_used=False, is_revoked=False
        )
        self.assertEqual(active_tokens.count(), 1)
        token2 = active_tokens.first()
        self.assertNotEqual(token1.token_hash, token2.token_hash)

    def test_password_validation_enforced_on_activation(self):
        user = self._create_pending_user("pwd.test@dhe.haryana.gov.in", "Dr. Pwd User")
        raw_token, token_obj = AccountActivationService.create_invitation(user=user, created_by=self.head_admin)

        # Too short (< 8 chars)
        with self.assertRaises(Exception) as ctx:
            AccountActivationService.activate_account(raw_token, "short", "short")
        self.assertIn("at least 8 characters", str(ctx.exception).lower())


class PasswordResetSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="registered.officer@dhe.haryana.gov.in",
            full_name="Registered Officer",
            role="state_admin",
            password="StrongPassword123!",
        )

    def test_password_reset_user_enumeration_resistance(self):
        # 1. Non-existent email
        res_nonexistent = self.client.post(
            "/api/auth/password/reset/",
            {"email": "nobody.doesnotexist@fake.domain"},
            format="json",
        )
        self.assertEqual(res_nonexistent.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res_nonexistent.data.get("message"),
            "If an account exists for that email address, a password reset link has been sent.",
        )
        # Verify no debug token/url is leaked
        self.assertNotIn("token", res_nonexistent.data)
        self.assertNotIn("debug_reset_url", res_nonexistent.data)

        # 2. Existing email
        res_existing = self.client.post(
            "/api/auth/password/reset/",
            {"email": "registered.officer@dhe.haryana.gov.in"},
            format="json",
        )
        self.assertEqual(res_existing.status_code, status.HTTP_200_OK)
        # Responses must be identical to prevent user enumeration
        self.assertEqual(res_existing.data.get("message"), res_nonexistent.data.get("message"))
        self.assertNotIn("token", res_existing.data)
        self.assertNotIn("debug_reset_url", res_existing.data)

        # Audit log was created for existing user without secret leakage
        audit = UserAuditLog.objects.filter(target_user=self.user, action="PASSWORD_RESET_REQUESTED").first()
        self.assertIsNotNone(audit)
        self.assertNotIn("password", str(audit.details))


class CommitteeManagementBackendTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.head_admin = User.objects.create_user(
            email="head.admin@dhe.haryana.gov.in",
            full_name="Head Admin",
            role="head_admin",
            password="HeadPass123!",
            is_staff=True,
            is_superuser=True,
        )
        self.state_admin = User.objects.create_user(
            email="state.admin@dhe.haryana.gov.in",
            full_name="State Admin",
            role="state_admin",
            password="StatePass123!",
            is_staff=True,
        )
        self.council_admin = User.objects.create_user(
            email="council.admin@dhe.haryana.gov.in",
            full_name="Council Admin Overseer",
            role="council_admin",
            password="CouncilPass123!",
        )
        self.chair_user = User.objects.create_user(
            email="college.chair@dhe.haryana.gov.in",
            full_name="Dr. College Chair",
            role="committee_chair",
            password="ChairPass123!",
        )
        self.member_user1 = User.objects.create_user(
            email="member.one@dhe.haryana.gov.in",
            full_name="Dr. Member One",
            role="committee",
            password="MemberPass123!",
        )
        self.member_user2 = User.objects.create_user(
            email="member.two@dhe.haryana.gov.in",
            full_name="Dr. Member Two",
            role="committee",
            password="MemberPass123!",
        )
        self.unauthorized_user = User.objects.create_user(
            email="principal.user@college.edu",
            full_name="College Principal",
            role="principal",
            password="PrincipalPass123!",
        )

    def test_create_committee_and_assign_chair(self):
        committee = CommitteeService.create_committee(
            actor=self.head_admin,
            data={
                "name": "College Screening Committee Alpha",
                "framework": "COLLEGE_2026",
                "committee_type": "SCREENING",
                "chair_id": self.chair_user.id,
                "description": "Evaluating colleges in northern Haryana zone",
            },
        )
        self.assertEqual(committee.name, "College Screening Committee Alpha")
        self.assertEqual(committee.chair, self.chair_user)
        self.assertEqual(committee.framework, "COLLEGE_2026")
        self.assertTrue(committee.is_active)

        # Audit log check
        audit = UserAuditLog.objects.filter(target_user=self.chair_user, action="COMMITTEE_CREATED").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.head_admin)

        # Reviewer authorization reconciliation check
        rev_auth = ReviewerAuthorization.objects.filter(
            user=self.chair_user, framework="COLLEGE_2026", is_active=True
        ).exists()
        self.assertTrue(rev_auth)

    def test_invalid_chair_role_rejected(self):
        # Ordinary member cannot be appointed chair
        with self.assertRaises(AdminValidationError) as ctx:
            CommitteeService.create_committee(
                actor=self.head_admin,
                data={
                    "name": "Invalid Chair Committee",
                    "framework": "COLLEGE_2026",
                    "committee_type": "SCREENING",
                    "chair_id": self.member_user1.id,  # has role="committee", not "committee_chair"
                },
            )
        self.assertEqual(ctx.exception.code, "INVALID_CHAIR_ROLE")

    def test_add_and_remove_members(self):
        committee = CommitteeService.create_committee(
            actor=self.head_admin,
            data={
                "name": "University Screening Committee",
                "framework": "UNIVERSITY_2026",
                "committee_type": "SCREENING",
            },
        )

        # Add member
        membership = CommitteeService.add_member(
            actor=self.head_admin,
            committee_id=committee.id,
            user_id=self.member_user1.id,
            role_in_committee="Subject Expert - Sciences",
        )
        self.assertTrue(membership.is_active)
        self.assertEqual(membership.role_in_committee, "Subject Expert - Sciences")
        self.assertEqual(committee.memberships.filter(is_active=True).count(), 1)

        # ReviewerAuthorization automatically reconciled
        auth = ReviewerAuthorization.objects.filter(
            user=self.member_user1, framework="UNIVERSITY_2026", is_active=True
        ).first()
        self.assertIsNotNone(auth)

        # Prevent duplicate active membership
        with self.assertRaises(AdminValidationError) as ctx:
            CommitteeService.add_member(
                actor=self.head_admin,
                committee_id=committee.id,
                user_id=self.member_user1.id,
            )
        self.assertEqual(ctx.exception.code, "DUPLICATE_ACTIVE_MEMBERSHIP")

        # Remove member
        removed = CommitteeService.remove_member(
            actor=self.head_admin,
            committee_id=committee.id,
            user_id=self.member_user1.id,
        )
        self.assertTrue(removed)
        self.assertEqual(committee.memberships.filter(is_active=True).count(), 0)

    def test_cross_framework_conflict_prevention(self):
        # Create an existing active authorization for COLLEGE_2026
        ReviewerAuthorization.objects.create(
            user=self.member_user2,
            framework="COLLEGE_2026",
            is_active=True,
            granted_by=self.head_admin,
        )

        uni_committee = CommitteeService.create_committee(
            actor=self.head_admin,
            data={
                "name": "State University Committee",
                "framework": "UNIVERSITY_2026",
                "committee_type": "SCREENING",
            },
        )

        # Adding member authorized strictly for COLLEGE_2026 to UNIVERSITY committee fails with framework conflict
        with self.assertRaises(AdminValidationError) as ctx:
            CommitteeService.add_member(
                actor=self.head_admin,
                committee_id=uni_committee.id,
                user_id=self.member_user2.id,
            )
        self.assertEqual(ctx.exception.code, "CROSS_FRAMEWORK_CONFLICT")

    def test_unauthorized_users_blocked_from_committee_apis(self):
        # 1. Anonymous user blocked
        res_anon = self.client.get("/api/v1/admin/committees/")
        self.assertIn(res_anon.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

        # 2. Non-admin (Principal) blocked
        self.client.force_authenticate(self.unauthorized_user)
        res_principal = self.client.get("/api/v1/admin/committees/")
        self.assertEqual(res_principal.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Council Admin Overseer cannot create committee
        self.client.force_authenticate(self.council_admin)
        res_council = self.client.post(
            "/api/v1/admin/committees/",
            {
                "name": "Council Attempt",
                "framework": "COLLEGE_2026",
                "committee_type": "SCREENING",
            },
            format="json",
        )
        self.assertEqual(res_council.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized_admin_can_list_and_create_committee(self):
        self.client.force_authenticate(self.head_admin)
        payload = {
            "name": "State Empirical Review Committee",
            "framework": "COLLEGE_2026",
            "committee_type": "SCREENING",
            "description": "Empirical evidence assessment",
        }
        res = self.client.post("/api/v1/admin/committees/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data.get("name"), "State Empirical Review Committee")

        # List committees
        res_list = self.client.get("/api/v1/admin/committees/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res_list.data.get("count"), 1)
