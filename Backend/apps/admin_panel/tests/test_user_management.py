"""
NEP Excellence Awards 2026 - Centralized User Management & Role Governance Tests (Phase 1)
Tests:
1. Secure Head Admin provisioning CLI command.
2. Prevention of public users assigning privileged roles.
3. Sub-Admin and Committee role assignment permissions (Head Admin only).
4. Unauthorized access to user-management endpoints (principal/nodal officer blocked).
5. Protection of the last active Head Admin (demotion, deactivation, and deletion blocked).
6. Account activation/deactivation and role update workflows.
7. Append-only UserAuditLog generation and immutability.
8. Committee-led certification boundary (Head Admin cannot directly certify or bypass committee).
"""
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import User, College, UserAuditLog
from apps.university.models import University


class HeadAdminProvisioningCommandTests(TestCase):
    def test_provision_head_admin_creates_new_user(self):
        out = StringIO()
        call_command(
            "provision_head_admin",
            email="head.admin@dhe.haryana.gov.in",
            name="State Head Admin",
            password="SecureHeadAdminPassword123!",
            stdout=out,
        )
        user = User.objects.get(email="head.admin@dhe.haryana.gov.in")
        self.assertEqual(user.role, "head_admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password("SecureHeadAdminPassword123!"))

        # Verify audit log was recorded
        audit = UserAuditLog.objects.filter(target_user=user, action="HEAD_ADMIN_PROVISIONED").first()
        self.assertIsNotNone(audit)
        self.assertIsNone(audit.actor)  # System provisioning

    def test_provision_head_admin_promotes_existing_user(self):
        existing = User.objects.create_user(
            email="promoted.admin@dhe.haryana.gov.in",
            full_name="Regular Admin",
            role="admin",
            password="OldPassword123!",
        )
        out = StringIO()
        call_command(
            "provision_head_admin",
            email="promoted.admin@dhe.haryana.gov.in",
            name="Promoted Head Admin",
            password="NewSecurePassword123!",
            stdout=out,
        )
        existing.refresh_from_db()
        self.assertEqual(existing.role, "head_admin")
        self.assertTrue(existing.is_superuser)
        self.assertTrue(existing.check_password("NewSecurePassword123!"))


class PublicRegistrationPrivilegeEscalationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.college = College.objects.create(name="Govt College Rohtak", aishe_code="C-20001")

    def test_public_registration_rejects_head_admin_role(self):
        payload = {
            "fullName": "Attacker Trying Head Admin",
            "email": "attacker.head@fake.com",
            "password": "Password123!",
            "role": "head_admin",
            "collegeId": self.college.id,
        }
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="attacker.head@fake.com").exists())

    def test_public_registration_rejects_sub_admin_role(self):
        payload = {
            "fullName": "Attacker Trying Sub Admin",
            "email": "attacker.sub@fake.com",
            "password": "Password123!",
            "role": "sub_admin",
            "collegeId": self.college.id,
        }
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_public_registration_rejects_committee_role(self):
        payload = {
            "fullName": "Attacker Trying Committee",
            "email": "attacker.comm@fake.com",
            "password": "Password123!",
            "role": "committee",
            "collegeId": self.college.id,
        }
        res = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class CentralizedUserManagementAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Head Admin
        self.head_admin = User.objects.create_user(
            email="head@haryana.gov.in",
            full_name="Chief Executive",
            role="head_admin",
            password="HeadAdminPass123!",
            is_staff=True,
            is_superuser=True,
        )

        # Sub Admin
        self.sub_admin = User.objects.create_user(
            email="sub@haryana.gov.in",
            full_name="Sub Admin Officer",
            role="sub_admin",
            password="SubAdminPass123!",
            is_staff=True,
        )

        # Institutional Users
        self.college = College.objects.create(name="Govt College Karnal", aishe_code="C-30001")
        self.principal = User.objects.create_user(
            email="principal.karnal@haryana.gov.in",
            full_name="Principal Karnal",
            role="principal",
            college=self.college,
            password="PrincipalPass123!",
        )

        self.university = University.objects.create(name="Kurukshetra University", aishe_code="U-0123")
        self.nodal_officer = User.objects.create_user(
            email="nodal.kuk@kuk.ac.in",
            full_name="Nodal Officer KUK",
            role="nodal_officer",
            university=self.university,
            password="NodalPass123!",
        )

    def test_unauthorized_institutional_users_denied_user_management(self):
        self.client.force_authenticate(user=self.principal)
        res = self.client.get("/api/v1/admin/users/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.nodal_officer)
        res = self.client.get("/api/v1/admin/users/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_head_admin_can_list_and_search_users(self):
        self.client.force_authenticate(user=self.head_admin)
        res = self.client.get("/api/v1/admin/users/?q=karnal")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["email"], "principal.karnal@haryana.gov.in")
        self.assertEqual(res.data["results"][0]["institution_type"], "COLLEGE")

    def test_head_admin_can_create_sub_admin(self):
        self.client.force_authenticate(user=self.head_admin)
        payload = {
            "email": "new.subadmin@dhe.haryana.gov.in",
            "full_name": "New Sub Administrator",
            "role": "sub_admin",
            "password": "SecurePassword123!",
        }
        res = self.client.post("/api/v1/admin/users/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["role"], "sub_admin")

        # Verify audit log
        audit = UserAuditLog.objects.filter(target_user__email="new.subadmin@dhe.haryana.gov.in", action="USER_CREATED").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.head_admin)

    def test_head_admin_can_create_committee_members(self):
        self.client.force_authenticate(user=self.head_admin)
        for role in ["committee", "committee_chair", "empowered_committee", "empowered_committee_chair"]:
            payload = {
                "email": f"officer.{role}@haryana.gov.in",
                "full_name": f"Officer {role}",
                "role": role,
                "password": "Password123!",
            }
            res = self.client.post("/api/v1/admin/users/", payload, format="json")
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
            self.assertEqual(res.data["role"], role)

    def test_sub_admin_cannot_create_privileged_roles(self):
        self.client.force_authenticate(user=self.sub_admin)
        payload = {
            "email": "rogue.chair@haryana.gov.in",
            "full_name": "Rogue Chair",
            "role": "committee_chair",
            "password": "Password123!",
        }
        res = self.client.post("/api/v1/admin/users/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["error"], "HEAD_ADMIN_REQUIRED")

    def test_sub_admin_cannot_change_roles(self):
        self.client.force_authenticate(user=self.sub_admin)
        res = self.client.patch(
            f"/api/v1/admin/users/{self.principal.id}/",
            {"role": "committee"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["error"], "HEAD_ADMIN_REQUIRED")

    def test_head_admin_can_change_role_and_generates_audit(self):
        self.client.force_authenticate(user=self.head_admin)
        res = self.client.patch(
            f"/api/v1/admin/users/{self.principal.id}/",
            {"role": "committee"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.principal.refresh_from_db()
        self.assertEqual(self.principal.role, "committee")

        # Verify audit log
        audit = UserAuditLog.objects.filter(target_user=self.principal, action="ROLE_CHANGED").latest("timestamp")
        self.assertEqual(audit.details["old_role"], "principal")
        self.assertEqual(audit.details["new_role"], "committee")
        self.assertEqual(audit.actor, self.head_admin)

    def test_head_admin_can_activate_and_deactivate_users(self):
        self.client.force_authenticate(user=self.head_admin)
        # Deactivate
        res = self.client.patch(
            f"/api/v1/admin/users/{self.principal.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.principal.refresh_from_db()
        self.assertFalse(self.principal.is_active)

        # Audit
        audit = UserAuditLog.objects.filter(target_user=self.principal, action="ACCOUNT_DEACTIVATED").first()
        self.assertIsNotNone(audit)

        # Reactivate
        res = self.client.patch(
            f"/api/v1/admin/users/{self.principal.id}/",
            {"is_active": True},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.principal.refresh_from_db()
        self.assertTrue(self.principal.is_active)


class LastHeadAdminProtectionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sole_head_admin = User.objects.create_user(
            email="sole.head@haryana.gov.in",
            full_name="Sole Head Administrator",
            role="head_admin",
            password="SolePassword123!",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

    def test_sole_head_admin_cannot_be_demoted(self):
        self.client.force_authenticate(user=self.sole_head_admin)
        res = self.client.patch(
            f"/api/v1/admin/users/{self.sole_head_admin.id}/",
            {"role": "sub_admin"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["error"], "LAST_HEAD_ADMIN_PROTECTED")
        self.sole_head_admin.refresh_from_db()
        self.assertEqual(self.sole_head_admin.role, "head_admin")

    def test_sole_head_admin_cannot_be_deactivated(self):
        self.client.force_authenticate(user=self.sole_head_admin)
        res = self.client.patch(
            f"/api/v1/admin/users/{self.sole_head_admin.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["error"], "LAST_HEAD_ADMIN_PROTECTED")
        self.sole_head_admin.refresh_from_db()
        self.assertTrue(self.sole_head_admin.is_active)

    def test_sole_head_admin_cannot_be_deleted(self):
        with self.assertRaises(PermissionError):
            self.sole_head_admin.delete()

    def test_demotion_allowed_when_another_active_head_admin_exists(self):
        # Create second head admin
        User.objects.create_user(
            email="second.head@haryana.gov.in",
            full_name="Second Head Administrator",
            role="head_admin",
            password="SecondPassword123!",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        self.client.force_authenticate(user=self.sole_head_admin)
        res = self.client.patch(
            f"/api/v1/admin/users/{self.sole_head_admin.id}/",
            {"role": "sub_admin"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.sole_head_admin.refresh_from_db()
        self.assertEqual(self.sole_head_admin.role, "sub_admin")


class UserAuditLogImmutabilityTests(TestCase):
    def test_user_audit_log_cannot_be_modified_or_deleted(self):
        user = User.objects.create_user(email="test.audit@example.com", full_name="Test User", role="principal")
        log = UserAuditLog.objects.create(
            actor=None,
            target_user=user,
            action="USER_CREATED",
            details={"note": "original"},
        )
        # Attempt edit
        log.details = {"note": "tampered"}
        with self.assertRaises(ValueError):
            log.save()

        # Attempt delete
        with self.assertRaises(ValueError):
            log.delete()


class HeadAdminCertificationWorkflowBoundaryTests(TestCase):
    """
    Mandatory Boundary: Certification remains committee-led.
    The Head Admin may manage users and committee membership but must NOT
    directly certify an institution or bypass the required approval workflow.
    """
    def setUp(self):
        self.client = APIClient()
        self.head_admin = User.objects.create_user(
            email="super.head@haryana.gov.in",
            full_name="Chief Administrator",
            role="head_admin",
            password="HeadAdminPass123!",
            is_staff=True,
            is_superuser=True,
        )

    def test_head_admin_cannot_directly_certify_assessment(self):
        self.client.force_authenticate(user=self.head_admin)
        # Call certification endpoint
        res = self.client.post(
            "/api/v1/admin/assessments/COLLEGE-TEST-001/certify/",
            {"comments": "Direct Head Admin certification attempt"},
            format="json",
        )
        # Must be strictly forbidden by IsControlPlaneCertificationAuthority
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Screening Committee Chair", str(res.data.get("detail", "")))


class FourAdminProfilesProvisioningTests(TestCase):
    """
    Tests covering the 4 core administrative profile types:
    1. State Admin (HSHEC State)
    2. Screening Committee Chair
    3. Screening Committee Member
    4. Council Admin Overseer
    """
    def setUp(self):
        self.client = APIClient()
        self.head_admin = User.objects.create_user(
            email="head.admin.p1@hshec.gov.in",
            full_name="State Head Administrator",
            role="head_admin",
            password="SecureHeadPass123!",
            is_staff=True,
            is_superuser=True,
        )
        self.state_admin = User.objects.create_user(
            email="state.admin.p1@hshec.gov.in",
            full_name="HSHEC State Admin",
            role="state_admin",
            password="StatePass123!",
            is_staff=True,
        )
        self.council_admin = User.objects.create_user(
            email="council.admin.p1@hshec.gov.in",
            full_name="Council Admin Overseer",
            role="council_admin",
            password="CouncilPass123!",
        )
        self.chair = User.objects.create_user(
            email="chair.p1@hshec.gov.in",
            full_name="Screening Committee Chair",
            role="committee_chair",
            password="ChairPass123!",
        )

    def test_provisioning_all_four_profiles_by_head_admin(self):
        self.client.force_authenticate(user=self.head_admin)
        profiles = [
            ("state_admin", "officer.state@hshec.gov.in", "State Admin Officer"),
            ("committee_chair", "chair.screening@hshec.gov.in", "Screening Committee Chair"),
            ("committee", "member.screening@hshec.gov.in", "Screening Committee Member"),
            ("council_admin", "overseer.council@hshec.gov.in", "Council Admin Overseer"),
        ]

        for role, email, name in profiles:
            payload = {
                "email": email,
                "full_name": name,
                "role": role,
                "password": "InitialSecurePassword123!",
                "committee_framework": "COLLEGE_2026" if "committee" in role else "",
            }
            res = self.client.post("/api/v1/admin/users/", payload, format="json")
            self.assertEqual(res.status_code, status.HTTP_201_CREATED, f"Failed for {role}: {res.data}")
            self.assertEqual(res.data["role"], role)
            self.assertEqual(res.data["email"], email)
            # Credential status is confirmed secure and no password leaked
            self.assertEqual(res.data.get("credential_status"), "PROVISIONED_SECURELY")
            self.assertNotIn("temporary_password", res.data)
            self.assertNotIn("password", res.data)

            # Verify audit trail
            created_user = User.objects.get(email=email)
            log = UserAuditLog.objects.filter(target_user=created_user, action="USER_CREATED").first()
            self.assertIsNotNone(log)
            self.assertEqual(log.actor, self.head_admin)
            self.assertEqual(log.details.get("role"), role)
            # Ensure no password in audit log details
            self.assertNotIn("password", str(log.details))

    def test_duplicate_email_rejected_on_provisioning(self):
        self.client.force_authenticate(user=self.head_admin)
        payload = {
            "email": "state.admin.p1@hshec.gov.in",  # already exists
            "full_name": "Duplicate State Admin",
            "role": "state_admin",
            "password": "Password123!",
        }
        res = self.client.post("/api/v1/admin/users/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_state_admin_and_council_admin_cannot_provision_privileged_profiles(self):
        # State Admin attempting to create Head Admin or another State Admin
        self.client.force_authenticate(user=self.state_admin)
        res = self.client.post(
            "/api/v1/admin/users/",
            {"email": "rogue.admin@test.gov", "full_name": "Rogue", "role": "state_admin"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("error"), "HEAD_ADMIN_REQUIRED")

        # Council Admin attempting to create any user
        self.client.force_authenticate(user=self.council_admin)
        res = self.client.post(
            "/api/v1/admin/users/",
            {"email": "rogue2.admin@test.gov", "full_name": "Rogue 2", "role": "committee"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class SecurePasswordResetEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.head_admin = User.objects.create_user(
            email="head.reset@hshec.gov.in",
            full_name="Head Admin",
            role="head_admin",
            password="OldPassword123!",
            is_staff=True,
            is_superuser=True,
        )
        self.target_user = User.objects.create_user(
            email="target.user@hshec.gov.in",
            full_name="Target Officer",
            role="state_admin",
            password="OldTargetPassword123!",
        )
        self.council_admin = User.objects.create_user(
            email="council.reset@hshec.gov.in",
            full_name="Council Admin",
            role="council_admin",
            password="CouncilPassword123!",
        )

    def test_head_admin_can_securely_reset_password(self):
        self.client.force_authenticate(user=self.head_admin)
        res = self.client.post(
            f"/api/v1/admin/users/{self.target_user.id}/reset-password/",
            {"password": "NewSecurePassword456!"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["credential_status"], "PROVISIONED_SECURELY")
        # Ensure password not echoed back
        self.assertNotIn("password", res.data)

        # Verify password actually changed
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.check_password("NewSecurePassword456!"))

        # Verify audit log
        audit = UserAuditLog.objects.filter(target_user=self.target_user, action="PASSWORD_RESET").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.head_admin)
        self.assertNotIn("password", str(audit.details))

    def test_non_head_admin_cannot_reset_password(self):
        self.client.force_authenticate(user=self.council_admin)
        res = self.client.post(
            f"/api/v1/admin/users/{self.target_user.id}/reset-password/",
            {"password": "AttemptedPassword123!"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Head Administrator", str(res.data.get("detail", "")))


class CommitteeFrameworkManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.head_admin = User.objects.create_user(
            email="head.comm@hshec.gov.in",
            full_name="Head Administrator",
            role="head_admin",
            password="Password123!",
            is_staff=True,
            is_superuser=True,
        )
        self.reviewer = User.objects.create_user(
            email="reviewer.fw@hshec.gov.in",
            full_name="Screening Reviewer",
            role="committee",
            password="ReviewerPass123!",
        )
        self.council_admin = User.objects.create_user(
            email="council.comm@hshec.gov.in",
            full_name="Council Admin",
            role="council_admin",
            password="CouncilPass123!",
        )

    def test_assign_and_remove_committee_authorization(self):
        from apps.evidence.models import ReviewerAuthorization

        self.client.force_authenticate(user=self.head_admin)
        # Assign framework COLLEGE_2026
        res = self.client.post(
            f"/api/v1/admin/users/{self.reviewer.id}/committee/",
            {"framework": "COLLEGE_2026", "action": "assign"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(
            ReviewerAuthorization.objects.filter(
                user=self.reviewer, framework="COLLEGE_2026", is_active=True
            ).exists()
        )

        # Verify audit log
        log = UserAuditLog.objects.filter(target_user=self.reviewer, action="COMMITTEE_ASSIGNED").first()
        self.assertIsNotNone(log)

        # Remove framework COLLEGE_2026
        res_remove = self.client.post(
            f"/api/v1/admin/users/{self.reviewer.id}/committee/",
            {"framework": "COLLEGE_2026", "action": "remove"},
            format="json",
        )
        self.assertEqual(res_remove.status_code, status.HTTP_200_OK)
        self.assertFalse(
            ReviewerAuthorization.objects.filter(
                user=self.reviewer, framework="COLLEGE_2026", is_active=True
            ).exists()
        )

        # Verify removal audit log
        log_rem = UserAuditLog.objects.filter(target_user=self.reviewer, action="COMMITTEE_REMOVED").first()
        self.assertIsNotNone(log_rem)

    def test_council_admin_cannot_manage_committee_authorizations(self):
        self.client.force_authenticate(user=self.council_admin)
        res = self.client.post(
            f"/api/v1/admin/users/{self.reviewer.id}/committee/",
            {"framework": "UNIVERSITY_2026", "action": "assign"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Council Admin Overseer is restricted", str(res.data.get("detail", "")))


class CouncilAdminBoundaryTests(TestCase):
    """
    Council Admin Overseer:
    - Can view users and control centre in read-only / operational mode.
    - Cannot assign reviewers to assessments.
    - Cannot certify assessments.
    - Cannot alter privileged roles.
    """
    def setUp(self):
        self.client = APIClient()
        self.council_admin = User.objects.create_user(
            email="council.overseer@hshec.gov.in",
            full_name="Council Overseer",
            role="council_admin",
            password="CouncilPass123!",
        )

    def test_council_admin_can_view_user_directory(self):
        self.client.force_authenticate(user=self.council_admin)
        res = self.client.get("/api/v1/admin/users/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)

    def test_council_admin_cannot_assign_reviewer_to_assessment(self):
        self.client.force_authenticate(user=self.council_admin)
        res = self.client.post(
            "/api/v1/admin/assessments/COLLEGE-TEST-001/assign/",
            {"reviewer_id": self.council_admin.id, "reason": "Attempting assignment"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Council Admin Overseer is restricted", str(res.data.get("detail", "")))

    def test_council_admin_cannot_certify_assessment(self):
        self.client.force_authenticate(user=self.council_admin)
        res = self.client.post(
            "/api/v1/admin/assessments/COLLEGE-TEST-001/certify/",
            {"comments": "Attempting certification"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Screening Committee Chair", str(res.data.get("detail", "")))


class UserDeletionTests(TestCase):
    """
    Tests for removing users under Head Administrator apex authority.
    """
    def setUp(self):
        self.client = APIClient()
        self.head_admin = User.objects.create_user(
            email="head.admin.del@hshec.gov.in",
            full_name="Apex Head Administrator",
            role="head_admin",
            password="SecurePass123!",
            is_staff=True,
            is_superuser=True,
        )
        self.state_admin = User.objects.create_user(
            email="state.admin.del@hshec.gov.in",
            full_name="State Admin Officer",
            role="state_admin",
            password="StatePass123!",
            is_staff=True,
        )
        self.target_user = User.objects.create_user(
            email="target.to.remove@hshec.gov.in",
            full_name="User To Remove",
            role="committee",
            password="MemberPass123!",
        )

    def test_head_admin_can_delete_user(self):
        self.client.force_authenticate(user=self.head_admin)
        res = self.client.delete(f"/api/v1/admin/users/{self.target_user.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("removed successfully", res.data["message"])
        self.assertFalse(User.objects.filter(id=self.target_user.id).exists())

    def test_non_head_admin_cannot_delete_user(self):
        self.client.force_authenticate(user=self.state_admin)
        res = self.client.delete(f"/api/v1/admin/users/{self.target_user.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(User.objects.filter(id=self.target_user.id).exists())

    def test_head_admin_cannot_delete_themselves(self):
        self.client.force_authenticate(user=self.head_admin)
        res = self.client.delete(f"/api/v1/admin/users/{self.head_admin.id}/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("error"), "CANNOT_DELETE_SELF")
        self.assertTrue(User.objects.filter(id=self.head_admin.id).exists())

    def test_cannot_delete_last_active_head_admin_by_another_superuser(self):
        # Create a second head admin who tries to delete the only OTHER active head admin
        other_superuser = User.objects.create_user(
            email="super.other@hshec.gov.in",
            full_name="Other Super Administrator",
            role="admin",
            is_superuser=True,
            password="SuperPass123!",
        )
        self.client.force_authenticate(user=other_superuser)
        res = self.client.delete(f"/api/v1/admin/users/{self.head_admin.id}/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("error"), "LAST_HEAD_ADMIN_PROTECTED")
        self.assertTrue(User.objects.filter(id=self.head_admin.id).exists())



