"""
NEP Excellence Awards 2026 - Head Admin Control Centre Tests
Tests:
1. Successful summary response for an authorized Head Admin.
2. Least-privilege summary response for a Sub-Admin.
3. Access rejection for unauthenticated and institutional users.
4. Accurate governance staffing counts (Head Admin, Sub-Admin, Screening, Empowered).
5. Accurate assessment workflow stage and exception counts (unassigned, blocked, returned).
6. Safe handling of empty databases.
7. Global audit feed access, filtering, and pagination for Head Admin.
8. Denial of global audit feed to Sub-Admins and non-administrators.
9. Protection against leaking sensitive account information in audit trails.
10. Strict enforcement of committee-led certification boundary (Head Admin cannot certify).
"""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import User, College, UserAuditLog
from apps.university.models import University, UniversityAssessment
from apps.college.models import CollegeAssessment


class HeadAdminControlCentreSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Head Admin
        self.head_admin = User.objects.create_user(
            email="head.admin@dhe.haryana.gov.in",
            full_name="State Head Admin",
            role="head_admin",
            password="SecurePassword123!",
            is_staff=True,
            is_superuser=True,
        )

        # Sub Admin
        self.sub_admin = User.objects.create_user(
            email="sub.admin@dhe.haryana.gov.in",
            full_name="State Sub Admin",
            role="sub_admin",
            password="SecurePassword123!",
            is_staff=True,
        )

        # Committee Chair
        self.sc_chair = User.objects.create_user(
            email="sc.chair@dhe.haryana.gov.in",
            full_name="Screening Chair",
            role="committee_chair",
            password="SecurePassword123!",
        )

        # Committee Reviewer
        self.sc_reviewer = User.objects.create_user(
            email="sc.reviewer@dhe.haryana.gov.in",
            full_name="Screening Reviewer",
            role="committee",
            password="SecurePassword123!",
        )

        # Institutional Users
        self.college = College.objects.create(name="Govt College Karnal", aishe_code="C-30001")
        self.principal = User.objects.create_user(
            email="principal@gckarnal.ac.in",
            full_name="Principal Karnal",
            role="principal",
            college=self.college,
            password="SecurePassword123!",
        )

        self.university = University.objects.create(name="Kurukshetra University", aishe_code="U-0001")
        self.nodal = User.objects.create_user(
            email="nodal@kuk.ac.in",
            full_name="Nodal KUK",
            role="nodal_officer",
            university=self.university,
            password="SecurePassword123!",
        )

    def test_summary_success_for_head_admin(self):
        self.client.force_authenticate(user=self.head_admin)
        res = self.client.get("/api/v1/admin/control-centre/summary/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertIn("governance", data)
        self.assertIn("institutions", data)
        self.assertIn("operations", data)
        self.assertIn("warnings", data)
        self.assertIn("recent_privileged_actions", data)

        self.assertTrue(data["governance"]["is_full_governance"])
        self.assertIn("head_admins", data["governance"]["administrators"])
        self.assertIn("sub_admins", data["governance"]["administrators"])
        self.assertIn("screening_committee", data["governance"])
        self.assertIn("empowered_committee", data["governance"])

    def test_summary_least_privilege_for_sub_admin(self):
        self.client.force_authenticate(user=self.sub_admin)
        res = self.client.get("/api/v1/admin/control-centre/summary/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertFalse(data["governance"]["is_full_governance"])
        # Privileged user audit trail is restricted/empty for sub_admin
        self.assertEqual(data["recent_privileged_actions"], [])
        # Detailed admin internals omitted
        self.assertNotIn("head_admins", data["governance"]["administrators"])
        self.assertIn("total_active", data["governance"]["administrators"])

    def test_summary_denies_unauthenticated_and_institutional_users(self):
        # 1. Unauthenticated
        res = self.client.get("/api/v1/admin/control-centre/summary/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Principal
        self.client.force_authenticate(user=self.principal)
        res = self.client.get("/api/v1/admin/control-centre/summary/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Nodal Officer
        self.client.force_authenticate(user=self.nodal)
        res = self.client.get("/api/v1/admin/control-centre/summary/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Screening Reviewer
        self.client.force_authenticate(user=self.sc_reviewer)
        res = self.client.get("/api/v1/admin/control-centre/summary/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_governance_counts_accurate(self):
        # Add inactive Head Admin
        User.objects.create_user(
            email="inactive.head@dhe.haryana.gov.in",
            full_name="Inactive Head",
            role="head_admin",
            password="Pass!",
            is_active=False,
        )
        # Add Empowered Committee members
        User.objects.create_user(
            email="ec.chair@dhe.haryana.gov.in",
            full_name="EC Chair",
            role="empowered_committee_chair",
            password="Pass!",
            is_active=True,
        )
        User.objects.create_user(
            email="ec.member@dhe.haryana.gov.in",
            full_name="EC Member",
            role="empowered_committee",
            password="Pass!",
            is_active=True,
        )

        self.client.force_authenticate(user=self.head_admin)
        res = self.client.get("/api/v1/admin/control-centre/summary/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        gov = res.data["governance"]
        # Head Admins: 1 active, 1 inactive = 2 total
        self.assertEqual(gov["administrators"]["head_admins"]["active"], 1)
        self.assertEqual(gov["administrators"]["head_admins"]["inactive"], 1)
        self.assertEqual(gov["administrators"]["head_admins"]["total"], 2)

        # Sub Admins: 1 active
        self.assertEqual(gov["administrators"]["sub_admins"]["active"], 1)
        self.assertEqual(gov["administrators"]["sub_admins"]["total"], 1)

        # Screening Committee: 1 chair, 1 reviewer
        self.assertEqual(gov["screening_committee"]["chairs"]["active"], 1)
        self.assertEqual(gov["screening_committee"]["reviewers"]["active"], 1)

        # Empowered Committee: 1 chair, 1 reviewer
        self.assertEqual(gov["empowered_committee"]["chairs"]["active"], 1)
        self.assertEqual(gov["empowered_committee"]["reviewers"]["active"], 1)

    def test_assessment_stage_and_exception_counts(self):
        # 1. Unassigned submitted college assessment
        CollegeAssessment.objects.create(
            assessment_id="COL-EXC-001",
            college=self.college,
            academic_year="2025-2026",
            status="SUBMITTED",
            assigned_reviewer=None,
        )

        # 2. Blocked university assessment
        UniversityAssessment.objects.create(
            assessment_id="UNI-EXC-001",
            university=self.university,
            academic_year="2025-2026",
            status="UNDER_REVIEW",
            certification_status="BLOCKED_BY_SPECIFICATION",
            assigned_reviewer=self.sc_reviewer,
        )

        self.client.force_authenticate(user=self.head_admin)
        res = self.client.get("/api/v1/admin/control-centre/summary/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ops = res.data["operations"]
        self.assertEqual(ops["unassigned_count"], 1)
        self.assertEqual(ops["unassigned_items"][0]["assessment_id"], "COL-EXC-001")

        self.assertEqual(ops["blocked_count"], 1)
        self.assertEqual(ops["blocked_items"][0]["assessment_id"], "UNI-EXC-001")

        # Warnings should reflect these operational exceptions
        warning_codes = [w["code"] for w in res.data["warnings"]]
        self.assertIn("UNASSIGNED_SUBMISSIONS", warning_codes)
        self.assertIn("SPECIFICATION_BLOCKS", warning_codes)

    def test_empty_database_behavior(self):
        # Delete all assessments, colleges, and universities
        CollegeAssessment.objects.all().delete()
        UniversityAssessment.objects.all().delete()
        College.objects.all().delete()
        University.objects.all().delete()

        self.client.force_authenticate(user=self.head_admin)
        res = self.client.get("/api/v1/admin/control-centre/summary/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data["institutions"]["total"], 0)
        self.assertEqual(data["institutions"]["colleges"], 0)
        self.assertEqual(data["institutions"]["universities"], 0)
        self.assertEqual(data["operations"]["unassigned_count"], 0)
        self.assertEqual(data["operations"]["blocked_count"], 0)
        self.assertEqual(data["operations"]["returned_count"], 0)


class GlobalUserAuditFeedAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.head_admin = User.objects.create_user(
            email="head.admin@dhe.haryana.gov.in",
            full_name="State Head Admin",
            role="head_admin",
            password="SecurePassword123!",
            is_staff=True,
            is_superuser=True,
        )

        self.sub_admin = User.objects.create_user(
            email="sub.admin@dhe.haryana.gov.in",
            full_name="State Sub Admin",
            role="sub_admin",
            password="SecurePassword123!",
            is_staff=True,
        )

        self.target_user = User.objects.create_user(
            email="target.user@dhe.haryana.gov.in",
            full_name="Target User",
            role="principal",
            password="SecurePassword123!",
        )

        # Seed audit entries
        UserAuditLog.objects.create(
            actor=self.head_admin,
            target_user=self.target_user,
            action="ROLE_CHANGED",
            details={"old_role": "principal", "new_role": "sub_admin"},
        )
        UserAuditLog.objects.create(
            actor=self.head_admin,
            target_user=self.target_user,
            action="ACCOUNT_ACTIVATED",
            details={"is_active": True},
        )
        UserAuditLog.objects.create(
            actor=self.head_admin,
            target_user=self.target_user,
            action="PROFILE_UPDATED",
            details={"phone_number": "9876543210"},
        )

    def test_global_audit_feed_head_admin_access(self):
        self.client.force_authenticate(user=self.head_admin)
        res = self.client.get("/api/v1/admin/users/audit-trail/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertIn("count", data)
        self.assertIn("results", data)
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 3)

        first = data["results"][0]
        self.assertEqual(first["actor_email"], self.head_admin.email)
        self.assertEqual(first["target_user_email"], self.target_user.email)
        self.assertIn("action_label", first)

    def test_global_audit_feed_filtering_and_pagination(self):
        self.client.force_authenticate(user=self.head_admin)

        # Filter by action
        res = self.client.get("/api/v1/admin/users/audit-trail/?action=ROLE_CHANGED")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["action"], "ROLE_CHANGED")

        # Search by target email
        res = self.client.get("/api/v1/admin/users/audit-trail/?search=target.user")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 3)

        # Pagination
        res = self.client.get("/api/v1/admin/users/audit-trail/?page=1&page_size=2")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertEqual(res.data["total_pages"], 2)

    def test_global_audit_feed_denies_sub_admin_and_others(self):
        # Sub-Admin is denied global audit trail
        self.client.force_authenticate(user=self.sub_admin)
        res = self.client.get("/api/v1/admin/users/audit-trail/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Head Administrator authority required", str(res.data.get("detail", "")))

        # Target user (institutional) is denied
        self.client.force_authenticate(user=self.target_user)
        res = self.client.get("/api/v1/admin/users/audit-trail/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Unauthenticated is denied
        self.client.logout()
        res = self.client.get("/api/v1/admin/users/audit-trail/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_audit_feed_sanitizes_sensitive_information(self):
        # Create an entry with sensitive credentials in details
        UserAuditLog.objects.create(
            actor=self.head_admin,
            target_user=self.target_user,
            action="PASSWORD_RESET",
            details={
                "password": "ClearTextPassword123!",
                "token": "secret_jwt_token",
                "otp_code": "123456",
                "safe_note": "Password was reset by administrator.",
            },
        )

        self.client.force_authenticate(user=self.head_admin)
        res = self.client.get("/api/v1/admin/users/audit-trail/?action=PASSWORD_RESET")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        details = res.data["results"][0]["details"]
        self.assertEqual(details["password"], "[REDACTED]")
        self.assertEqual(details["token"], "[REDACTED]")
        self.assertEqual(details["otp_code"], "[REDACTED]")
        self.assertEqual(details["safe_note"], "Password was reset by administrator.")


class CertificationBoundaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.head_admin = User.objects.create_user(
            email="head.admin@dhe.haryana.gov.in",
            full_name="Head Admin",
            role="head_admin",
            password="SecurePassword123!",
            is_staff=True,
            is_superuser=True,
        )

        self.college = College.objects.create(name="Govt College Jind", aishe_code="C-40001")
        self.assessment = CollegeAssessment.objects.create(
            assessment_id="COL-CERT-001",
            college=self.college,
            academic_year="2025-2026",
            status="UNDER_REVIEW",
            certified_score=85.5,
            certification_status="FINALIZABLE",
        )

    def test_head_admin_cannot_certify_assessment(self):
        """
        Confirms that Head Admin cannot directly certify an assessment.
        Certification must remain strictly committee-led by the Screening Committee Chair.
        """
        self.client.force_authenticate(user=self.head_admin)
        payload = {"comments": "Head Admin trying to certify assessment directly."}
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.assessment.assessment_id}/certify/",
            payload,
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Screening Committee Chair", str(res.data.get("detail", "")))

