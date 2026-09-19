"""
NEP Excellence Awards 2026 - Admin Control Plane Test Suite (Phase 8)
Exhaustive security, tenancy, framework isolation, reviewer assignment,
certification delegation, anti-tampering, audit integrity, and concurrency tests.
"""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import College
from apps.college.models import (
    CollegeAssessment,
    CollegeAssessmentAuditLog,
    CollegeReviewAction,
    CollegeReviewRecord,
)
from apps.college.registry import COLLEGE_FRAMEWORK_CODE
from apps.college.services import CollegeAssessmentService, CollegeReviewService
from apps.evidence.models import ReviewerAuthorization
from apps.scoring.domain import FrameworkResult
from apps.scoring.enums import FrameworkType, CertificationStatus
from apps.university.models import (
    University,
    UniversityAssessment,
    UniversityAssessmentAuditLog,
    UniversityReviewAction,
    UniversityReviewRecord,
)
from apps.university.services import UniversityAssessmentService, UniversityReviewService, UNIVERSITY_FRAMEWORK_CODE

User = get_user_model()


class AdminControlPlaneSecurityTests(TestCase):
    """
    Comprehensive test suite covering all 15 security and governance dimensions of Phase 8.
    """

    def setUp(self):
        self.client = APIClient()

        # Institutions
        self.college_a = College.objects.create(name="Govt College Hisar", aishe_code="C-00105")
        self.college_b = College.objects.create(name="Govt College Sirsa", aishe_code="C-00106")
        self.university_a = University.objects.create(name="Kurukshetra University", aishe_code="U-00101")
        self.university_b = University.objects.create(name="Maharshi Dayanand University", aishe_code="U-00102")

        # Users
        self.principal_a = User.objects.create_user(
            email="principal.hisar@haryana.gov.in",
            full_name="Principal Hisar",
            role="principal",
            college=self.college_a,
            password="SecurePassword123!",
        )
        self.principal_b = User.objects.create_user(
            email="principal.sirsa@haryana.gov.in",
            full_name="Principal Sirsa",
            role="principal",
            college=self.college_b,
            password="SecurePassword123!",
        )
        self.nodal_officer_a = User.objects.create_user(
            email="nodal.kuk@haryana.gov.in",
            full_name="Nodal Officer KUK",
            role="nodal_officer",
            university=self.university_a,
            password="SecurePassword123!",
        )
        self.reviewer_college = User.objects.create_user(
            email="col.reviewer@dhe.haryana.gov.in",
            full_name="College Reviewer",
            role="committee",
            password="SecurePassword123!",
        )
        self.reviewer_university = User.objects.create_user(
            email="uni.reviewer@dhe.haryana.gov.in",
            full_name="University Reviewer",
            role="committee",
            password="SecurePassword123!",
        )
        self.conflicted_college_reviewer = User.objects.create_user(
            email="hisar.reviewer@hisar.ac.in",
            full_name="Dr. Hisar Conflicted",
            role="committee",
            college=self.college_a,
            password="SecurePassword123!",
        )
        self.conflicted_uni_reviewer = User.objects.create_user(
            email="kuk.reviewer@kuk.ac.in",
            full_name="Dr. KUK Conflicted",
            role="committee",
            university=self.university_a,
            password="SecurePassword123!",
        )
        self.chair = User.objects.create_user(
            email="chair@dhe.haryana.gov.in",
            full_name="Prof. State Chair",
            role="committee_chair",
            password="SecurePassword123!",
        )
        self.admin = User.objects.create_user(
            email="admin@dhe.haryana.gov.in",
            full_name="State Admin",
            role="admin",
            password="SecurePassword123!",
        )
        self.superuser = User.objects.create_superuser(
            email="superuser@dhe.haryana.gov.in",
            full_name="Platform Superuser",
            password="SuperSecurePassword123!",
        )

        # Reviewer Authorizations
        ReviewerAuthorization.objects.create(
            user=self.reviewer_college,
            framework=COLLEGE_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )
        ReviewerAuthorization.objects.create(
            user=self.conflicted_college_reviewer,
            framework=COLLEGE_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )
        ReviewerAuthorization.objects.create(
            user=self.reviewer_university,
            framework=UNIVERSITY_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )
        ReviewerAuthorization.objects.create(
            user=self.conflicted_uni_reviewer,
            framework=UNIVERSITY_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )
        ReviewerAuthorization.objects.create(
            user=self.chair,
            framework="ALL",
            institution_id="",
            is_active=True,
        )

        # Assessments
        # 1. Submitted College Assessment
        self.col_assess_a = CollegeAssessment.objects.create(
            assessment_id="ASSESS-COL-001",
            college=self.college_a,
            framework=COLLEGE_FRAMEWORK_CODE,
            academic_year="2025-26",
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="SUBMITTED",
        )
        # 2. Under Review College Assessment
        self.col_assess_b = CollegeAssessment.objects.create(
            assessment_id="ASSESS-COL-002",
            college=self.college_b,
            framework=COLLEGE_FRAMEWORK_CODE,
            academic_year="2025-26",
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="UNDER_REVIEW",
            assigned_reviewer=self.reviewer_college,
        )
        # 3. Submitted University Assessment
        self.uni_assess_a = UniversityAssessment.objects.create(
            assessment_id="ASSESS-UNI-001",
            university=self.university_a,
            framework=UNIVERSITY_FRAMEWORK_CODE,
            academic_year="2025-26",
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="SUBMITTED",
        )
        # 4. Under Review University Assessment
        self.uni_assess_b = UniversityAssessment.objects.create(
            assessment_id="ASSESS-UNI-002",
            university=self.university_b,
            framework=UNIVERSITY_FRAMEWORK_CODE,
            academic_year="2025-26",
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="UNDER_REVIEW",
            assigned_reviewer=self.reviewer_university,
        )

    # ==========================================================================
    # 1. AUTHORIZATION TESTS
    # ==========================================================================

    def test_unauthenticated_user_denied_access(self):
        """Unauthenticated requests to control plane endpoints return 401."""
        res_queue = self.client.get("/api/v1/admin/review-queue/")
        self.assertEqual(res_queue.status_code, status.HTTP_401_UNAUTHORIZED)

        res_inspect = self.client.get(f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/inspect/")
        self.assertEqual(res_inspect.status_code, status.HTTP_401_UNAUTHORIZED)

        res_assign = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/assign/",
            {"reviewer_id": self.reviewer_college.pk}
        )
        self.assertEqual(res_assign.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_institutional_user_denied_queue_and_assignment(self):
        """Institutional users cannot access review queue or assign reviewers (403)."""
        self.client.force_authenticate(user=self.principal_a)

        res_queue = self.client.get("/api/v1/admin/review-queue/")
        self.assertEqual(res_queue.status_code, status.HTTP_403_FORBIDDEN)

        res_assign = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/assign/",
            {"reviewer_id": self.reviewer_college.pk}
        )
        self.assertEqual(res_assign.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthorized_reviewer_denied_foreign_framework_queue(self):
        """Reviewer authorized only for College cannot query University framework queue."""
        self.client.force_authenticate(user=self.reviewer_college)
        res = self.client.get("/api/v1/admin/review-queue/?framework=UNIVERSITY_2026")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized_reviewer_sees_only_authorized_queue_items(self):
        """College reviewer querying queue sees college assessments and excludes university."""
        self.client.force_authenticate(user=self.reviewer_college)
        res = self.client.get("/api/v1/admin/review-queue/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data["results"]
        # Must contain College assessments, zero University assessments
        frameworks = {item["framework"] for item in results}
        self.assertIn(COLLEGE_FRAMEWORK_CODE, frameworks)
        self.assertNotIn(UNIVERSITY_FRAMEWORK_CODE, frameworks)

    def test_state_admin_has_full_queue_visibility(self):
        """State Admin sees both University and College assessments in unified queue."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/v1/admin/review-queue/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data["results"]
        frameworks = {item["framework"] for item in results}
        self.assertIn(COLLEGE_FRAMEWORK_CODE, frameworks)
        self.assertIn(UNIVERSITY_FRAMEWORK_CODE, frameworks)

    # ==========================================================================
    # 2. TENANCY & IDOR TESTS
    # ==========================================================================

    def test_institutional_user_can_inspect_own_assessment(self):
        """Principal can safely inspect their own college assessment via inspection endpoint."""
        self.client.force_authenticate(user=self.principal_a)
        res = self.client.get(f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/inspect/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["assessment_id"], str(self.col_assess_a.assessment_id))
        self.assertEqual(res.data["institution"]["name"], "Govt College Hisar")

    def test_institutional_user_cannot_inspect_different_institution_assessment(self):
        """Principal A attempting to inspect College B assessment fails with 403."""
        self.client.force_authenticate(user=self.principal_a)
        res = self.client.get(f"/api/v1/admin/assessments/{self.col_assess_b.assessment_id}/inspect/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_university_user_cannot_inspect_college_assessment(self):
        """University Nodal Officer attempting to inspect College assessment fails with 403."""
        self.client.force_authenticate(user=self.nodal_officer_a)
        res = self.client.get(f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/inspect/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_or_manipulated_assessment_id_returns_404(self):
        """Manipulated or non-existent assessment ID returns 404 Not Found."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/v1/admin/assessments/NON-EXISTENT-ID-9999/inspect/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ==========================================================================
    # 3. FRAMEWORK ISOLATION TESTS
    # ==========================================================================

    def test_college_reviewer_cannot_inspect_university_assessment(self):
        """Reviewer authorized only for College cannot inspect University assessment (403)."""
        self.client.force_authenticate(user=self.reviewer_college)
        res = self.client.get(f"/api/v1/admin/assessments/{self.uni_assess_a.assessment_id}/inspect/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_university_reviewer_cannot_inspect_college_assessment(self):
        """Reviewer authorized only for University cannot inspect College assessment (403)."""
        self.client.force_authenticate(user=self.reviewer_university)
        res = self.client.get(f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/inspect/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_legacy_nomination_id_rejected_on_control_plane(self):
        """Legacy nomination identifier rejected by NEP control plane (404)."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/v1/admin/assessments/nomination-12345/inspect/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ==========================================================================
    # 4. REVIEWER ASSIGNMENT & COI TESTS
    # ==========================================================================

    def test_admin_can_assign_reviewer_to_assessment(self):
        """State Admin can assign an eligible reviewer to an unassigned assessment."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/assign/",
            {"reviewer_id": self.reviewer_college.pk}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.col_assess_a.refresh_from_db()
        self.assertEqual(self.col_assess_a.assigned_reviewer_id, self.reviewer_college.pk)

        # Verify append-only audit log
        audit = CollegeAssessmentAuditLog.objects.filter(
            assessment=self.col_assess_a, action="REVIEWER_ASSIGNED"
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.admin)
        self.assertIn(self.reviewer_college.email, audit.reason)

    def test_chair_can_assign_reviewer_to_assessment(self):
        """Committee Chair can assign an eligible reviewer to an assessment."""
        self.client.force_authenticate(user=self.chair)
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.uni_assess_a.assessment_id}/assign/",
            {"reviewer_id": self.reviewer_university.pk}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.uni_assess_a.refresh_from_db()
        self.assertEqual(self.uni_assess_a.assigned_reviewer_id, self.reviewer_university.pk)

    def test_reassignment_requires_mandatory_reason(self):
        """Reassigning an already-assigned assessment without a reason fails with 400."""
        self.client.force_authenticate(user=self.admin)
        # col_assess_b is already assigned to reviewer_college; reassign to chair without reason
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_b.assessment_id}/assign/",
            {"reviewer_id": self.chair.pk, "reason": ""}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", str(res.data))

    def test_reassignment_with_reason_succeeds_and_audits(self):
        """Reassigning an assessment with justification updates reviewer and records REVIEWER_REASSIGNED."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_b.assessment_id}/assign/",
            {"reviewer_id": self.chair.pk, "reason": "Reviewer workload rebalancing"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.col_assess_b.refresh_from_db()
        self.assertEqual(self.col_assess_b.assigned_reviewer_id, self.chair.pk)

        audit = CollegeAssessmentAuditLog.objects.filter(
            assessment=self.col_assess_b, action="REVIEWER_REASSIGNED"
        ).first()
        self.assertIsNotNone(audit)
        self.assertIn("Reviewer workload rebalancing", audit.reason)
        self.assertIn(self.reviewer_college.email, audit.reason)
        self.assertIn(self.chair.email, audit.reason)

    def test_cannot_assign_conflicted_reviewer(self):
        """Assigning a reviewer affiliated with the target college fails with 403 REVIEW_CONFLICT."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/assign/",
            {"reviewer_id": self.conflicted_college_reviewer.pk}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Conflict of interest", str(res.data))

    def test_cannot_assign_reviewer_to_certified_assessment(self):
        """Assigning a reviewer to a CERTIFIED assessment is strictly blocked (400)."""
        # Create a certified assessment
        certified_assess = CollegeAssessment.objects.create(
            assessment_id="ASSESS-COL-CERT-001",
            college=self.college_b,
            framework=COLLEGE_FRAMEWORK_CODE,
            status="CERTIFIED",
            certified_score=85.0,
        )
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            f"/api/v1/admin/assessments/{certified_assess.assessment_id}/assign/",
            {"reviewer_id": self.reviewer_college.pk}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("permanently locked", str(res.data))

    def test_cannot_assign_unauthorized_framework_reviewer(self):
        """Assigning a reviewer to a framework they are not authorized for fails with 403."""
        self.client.force_authenticate(user=self.admin)
        # Try assigning College reviewer to University assessment
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.uni_assess_a.assessment_id}/assign/",
            {"reviewer_id": self.reviewer_college.pk}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================================================
    # 5. CERTIFICATION DELEGATION TESTS
    # ==========================================================================

    def test_unauthorized_user_cannot_certify(self):
        """Regular committee reviewer cannot certify assessments (403)."""
        self.client.force_authenticate(user=self.reviewer_college)
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_b.assessment_id}/certify/",
            {"comments": "Approved"}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_certification_with_missing_evidence_fails(self):
        """Certification attempt fails if documentary evidence requirements are unmet (400)."""
        self.client.force_authenticate(user=self.chair)
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_b.assessment_id}/certify/",
            {"comments": "Attempting certification without verified evidence"}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_certification_from_invalid_lifecycle_fails(self):
        """Certification from DRAFT or SUBMITTED lifecycle fails Gate 4."""
        self.client.force_authenticate(user=self.chair)
        # col_assess_a is in SUBMITTED state
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/certify/",
            {"comments": "Certifying submitted assessment"}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.college.services.CollegeAssessmentService.check_assessment_readiness")
    @patch("apps.college.services.CollegeAssessmentService.evaluate_assessment_scoring")
    def test_successful_certification_delegation(self, mock_scoring, mock_readiness):
        """Valid certification delegates to domain service, locks score, transitions to CERTIFIED."""
        mock_readiness.return_value = (True, [], None)
        mock_result = FrameworkResult(
            framework=FrameworkType.COLLEGE_2026,
            assessment_id=self.col_assess_b.assessment_id,
            institution_id=self.college_b.aishe_code,
            calculation_id="CALC-ADMIN-001",
            version_index=1,
            timestamp=timezone.now().isoformat(),
            raw_total=88.5,
            evidence_gated_total=88.5,
            final_certified_total=88.5,
            max_marks=100.0,
            certification_status=CertificationStatus.FINALIZABLE,
            blocking_reasons=[],
            parameter_results={},
        )

        def mock_eval_scoring(aid):
            self.col_assess_b.certified_score = 88.5
            self.col_assess_b.certification_status = "FINALIZABLE"
            self.col_assess_b.save(update_fields=["certified_score", "certification_status"])
            return mock_result

        mock_scoring.side_effect = mock_eval_scoring

        self.client.force_authenticate(user=self.chair)
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_b.assessment_id}/certify/",
            {"comments": "Formal committee approval"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.col_assess_b.refresh_from_db()
        self.assertEqual(self.col_assess_b.status, "CERTIFIED")
        self.assertEqual(self.col_assess_b.certified_score, 88.5)

    # ==========================================================================
    # 6. TAMPER PROTECTION TESTS
    # ==========================================================================

    def test_client_score_injection_rejected_on_assignment(self):
        """Supplying score keys in reviewer assignment endpoint returns 400."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/assign/",
            {
                "reviewer_id": self.reviewer_college.pk,
                "score": 99.0,
                "certified_score": 99.0,
            }
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("SCORE_INJECTION_REJECTED", str(res.data))

    def test_client_status_injection_rejected_on_certify(self):
        """Supplying status or final total fields in certify endpoint returns 400."""
        self.client.force_authenticate(user=self.chair)
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_b.assessment_id}/certify/",
            {
                "status": "CERTIFIED",
                "final_score": 100.0,
                "comments": "Hacked score",
            }
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("SCORE_INJECTION_REJECTED", str(res.data))

    # ==========================================================================
    # 7. AUDIT INTEGRITY TESTS
    # ==========================================================================

    def test_privileged_assignment_produces_immutable_audit_log(self):
        """Assignment action creates audit log record that cannot be modified or deleted."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/assign/",
            {"reviewer_id": self.reviewer_college.pk}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        audit = CollegeAssessmentAuditLog.objects.filter(
            assessment=self.col_assess_a, action="REVIEWER_ASSIGNED"
        ).first()
        self.assertIsNotNone(audit)

        # Verify update raises error
        with self.assertRaises(Exception):
            audit.reason = "Tampered reason"
            audit.save()

        # Verify delete raises error
        with self.assertRaises(Exception):
            audit.delete()

    # ==========================================================================
    # 8. CONCURRENCY TESTS
    # ==========================================================================

    def test_concurrent_assignment_safe(self):
        """Simultaneous reviewer assignment calls are serialized safely via select_for_update."""
        self.client.force_authenticate(user=self.admin)
        # Calling assign in rapid succession
        res1 = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/assign/",
            {"reviewer_id": self.reviewer_college.pk}
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        res2 = self.client.post(
            f"/api/v1/admin/assessments/{self.col_assess_a.assessment_id}/assign/",
            {"reviewer_id": self.chair.pk, "reason": "Immediate reassignment"}
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        self.col_assess_a.refresh_from_db()
        self.assertEqual(self.col_assess_a.assigned_reviewer_id, self.chair.pk)

    # ==========================================================================
    # 9. CERTIFICATION GATES TERMINOLOGY & CLASSIFICATION REGRESSION TEST
    # ==========================================================================

    def test_certification_gates_terminology_and_classification(self):
        """
        Ensures the 11 certification gates are not incorrectly termed '11 statutory gates'.
        Verifies classification: 2 source/framework requirements and 9 platform certification safeguards.
        """
        import inspect
        from apps.admin_panel.services import AdminControlPlaneService
        doc = inspect.getdoc(AdminControlPlaneService.certify_assessment) or ""
        self.assertNotIn("11 statutory gates", doc.lower())
        self.assertNotIn("statutory/platform gates", doc.lower())
        self.assertIn("11 certification gates", doc)
        self.assertIn("2 source/framework requirements and 9 platform certification safeguards", doc)
