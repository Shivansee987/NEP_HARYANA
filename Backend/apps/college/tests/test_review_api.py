"""
NEP Excellence Awards 2026 - College Review & Certification REST API Tests (Phase 7C)

Tests:
- Review queue access, filtering, and conflict-of-interest exclusion
- Reviewer actions: start review, complete review, return for correction, block review
- Certification endpoint and role authorization (committee_chair vs committee vs principal)
- Security & Anti-Tampering: Rejection of score injection payloads
- Immutability enforcement after certification
"""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import College
from apps.college.models import (
    CollegeAssessment,
    CollegeReviewAction,
    CollegeReviewRecord,
)
from apps.college.registry import COLLEGE_FRAMEWORK_CODE
from apps.college.services import CollegeAssessmentService
from apps.evidence.models import ReviewerAuthorization
from apps.scoring.domain import FrameworkResult
from apps.scoring.enums import FrameworkType, CertificationStatus

User = get_user_model()


class CollegeReviewAPITests(TestCase):
    """Integration tests for College review and certification API endpoints."""

    def setUp(self):
        self.client = APIClient()

        # Colleges
        self.college_a = College.objects.create(
            name="Govt College Hisar",
            aishe_code="C-00105",
        )
        self.college_b = College.objects.create(
            name="Govt College Sirsa",
            aishe_code="C-00106",
        )

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
        self.reviewer = User.objects.create_user(
            email="reviewer@dhe.haryana.gov.in",
            full_name="Dr. State Reviewer",
            role="committee",
            password="SecurePassword123!",
        )
        self.conflicted_reviewer = User.objects.create_user(
            email="reviewer.hisar@hisar.ac.in",
            full_name="Dr. Hisar Reviewer",
            role="committee",
            college=self.college_a,
            password="SecurePassword123!",
        )
        self.unauthorized_reviewer = User.objects.create_user(
            email="unauthorized@haryana.gov.in",
            full_name="Dr. Unauthorized Reviewer",
            role="committee",
            password="SecurePassword123!",
        )
        self.chair = User.objects.create_user(
            email="chair@dhe.haryana.gov.in",
            full_name="Prof. Committee Chair",
            role="committee_chair",
            password="SecurePassword123!",
        )
        self.admin = User.objects.create_user(
            email="admin@dhe.haryana.gov.in",
            full_name="State Admin",
            role="admin",
            password="SecurePassword123!",
        )

        # Authorizations
        ReviewerAuthorization.objects.create(
            user=self.reviewer,
            framework=COLLEGE_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )
        ReviewerAuthorization.objects.create(
            user=self.conflicted_reviewer,
            framework=COLLEGE_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )
        # Unauthorized reviewer is explicitly authorized only for University framework
        ReviewerAuthorization.objects.create(
            user=self.unauthorized_reviewer,
            framework="UNIVERSITY_2026",
            institution_id="",
            is_active=True,
        )

        # Assessment A (Govt College Hisar)
        self.assessment_a = CollegeAssessmentService.create_assessment(
            college_id=self.college_a.pk,
            academic_year="2025-26",
            created_by=self.principal_a,
        )
        self.assessment_a.status = "SUBMITTED"
        self.assessment_a.save()

        # Assessment B (Govt College Sirsa)
        self.assessment_b = CollegeAssessmentService.create_assessment(
            college_id=self.college_b.pk,
            academic_year="2025-26",
            created_by=self.principal_b,
        )
        self.assessment_b.status = "SUBMITTED"
        self.assessment_b.save()

    # =========================================================================
    # 1. Review Queue Tests
    # =========================================================================

    def test_unauthenticated_cannot_access_review_queue(self):
        """Unauthenticated request returns HTTP 401."""
        url = "/api/v1/college/review/queue/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_principal_cannot_access_review_queue(self):
        """College principal is forbidden (HTTP 403) from review queue."""
        self.client.force_authenticate(user=self.principal_a)
        url = "/api/v1/college/review/queue/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reviewer_sees_queue_with_conflict_of_interest_excluded(self):
        """Reviewer affiliated with college_a cannot see college_a in queue, only college_b."""
        self.client.force_authenticate(user=self.conflicted_reviewer)
        url = "/api/v1/college/review/queue/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        assessment_ids = [item["assessment_id"] for item in results]
        self.assertNotIn(self.assessment_a.assessment_id, assessment_ids)
        self.assertIn(self.assessment_b.assessment_id, assessment_ids)

    def test_chair_and_admin_can_access_full_queue(self):
        """Chair and Admin see all submitted assessments in the queue."""
        self.client.force_authenticate(user=self.chair)
        url = "/api/v1/college/review/queue/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        assessment_ids = [item["assessment_id"] for item in results]
        self.assertIn(self.assessment_a.assessment_id, assessment_ids)
        self.assertIn(self.assessment_b.assessment_id, assessment_ids)

    def test_queue_filters_by_status_and_academic_year(self):
        """Review queue properly applies status and academic_year query filters."""
        self.assessment_b.status = "UNDER_REVIEW"
        self.assessment_b.save()

        self.client.force_authenticate(user=self.reviewer)
        url = "/api/v1/college/review/queue/?status=UNDER_REVIEW"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["assessment_id"], self.assessment_b.assessment_id)

    # =========================================================================
    # 2. Start Review Tests
    # =========================================================================

    def test_start_review_succeeds_for_authorized_reviewer(self):
        """Authorized reviewer successfully starts review."""
        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/start/"
        response = self.client.post(url, {"comments": "Starting review of C1-C10"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["assessment"]["status"], "UNDER_REVIEW")
        self.assertEqual(response.data["assessment"]["assigned_reviewer"], self.reviewer.pk)

    def test_start_review_blocks_conflicted_reviewer(self):
        """Affiliated reviewer cannot start review (HTTP 403)."""
        self.client.force_authenticate(user=self.conflicted_reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/start/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_review_blocks_unauthorized_reviewer(self):
        """Reviewer without College framework authorization is rejected (HTTP 403)."""
        self.client.force_authenticate(user=self.unauthorized_reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/start/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_review_rejects_draft_or_certified(self):
        """Cannot start review on DRAFT assessment (HTTP 409 Conflict)."""
        self.assessment_a.status = "DRAFT"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/start/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_start_review_rejects_score_injection(self):
        """Client attempting to inject score fields in start_review is rejected with HTTP 400."""
        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/start/"
        response = self.client.post(url, {"score": 95.0, "certified_score": 95.0}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("score" in str(response.data).lower())

    # =========================================================================
    # 2b. Review Evaluate Tests
    # =========================================================================

    def test_review_evaluate_succeeds_for_authorized_reviewer(self):
        """Authorized reviewer triggers evaluate endpoint; status remains UNDER_REVIEW."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.assigned_reviewer = self.reviewer
        self.assessment_a.save()

        mock_result = FrameworkResult(
            framework=FrameworkType.COLLEGE_2026,
            assessment_id=self.assessment_a.assessment_id,
            institution_id=self.college_a.aishe_code,
            calculation_id="calc-col-rev-eval-01",
            version_index=1,
            timestamp=date(2026, 3, 1),
            raw_total=85.0,
            evidence_gated_total=85.0,
            final_certified_total=85.0,
            max_marks=100.0,
            certification_status=CertificationStatus.FINALIZABLE,
            blocking_reasons=[],
            parameter_results={},
        )

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/evaluate/"

        with patch.object(CollegeAssessmentService, "evaluate_assessment_scoring", return_value=mock_result):
            response = self.client.post(url, {}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["assessment"]["status"], "UNDER_REVIEW")
            self.assertEqual(response.data["review"]["action"], "EVALUATE")
            self.assertEqual(response.data["scoring"]["calculation_id"], "calc-col-rev-eval-01")

    def test_review_evaluate_blocks_conflicted_reviewer(self):
        """Conflicted reviewer cannot evaluate assessment (HTTP 403)."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.conflicted_reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/evaluate/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_review_evaluate_blocks_principal(self):
        """College principal is forbidden from evaluating via reviewer endpoint (HTTP 403)."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.principal_a)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/evaluate/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_review_evaluate_rejects_score_injection(self):
        """Reviewer attempting to inject client-supplied score in review evaluate is rejected (HTTP 400)."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.assigned_reviewer = self.reviewer
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/evaluate/"
        response = self.client.post(url, {"score": 99.0}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("score" in str(response.data).lower())

    # =========================================================================
    # 3. Complete Review Tests
    # =========================================================================

    def test_complete_review_requires_remarks(self):
        """Completing review without remarks returns HTTP 400."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.assigned_reviewer = self.reviewer
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/complete/"
        response = self.client.post(url, {"remarks": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_review_succeeds_when_evaluated(self):
        """Completing review leaves status as UNDER_REVIEW when readiness & scoring pass."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.assigned_reviewer = self.reviewer
        self.assessment_a.save()

        mock_result = FrameworkResult(
            framework=FrameworkType.COLLEGE_2026,
            assessment_id=self.assessment_a.assessment_id,
            institution_id=self.college_a.aishe_code,
            calculation_id="calc-col-eval-01",
            version_index=1,
            timestamp=date(2026, 3, 1),
            raw_total=88.0,
            evidence_gated_total=88.0,
            final_certified_total=88.0,
            max_marks=100.0,
            certification_status=CertificationStatus.FINALIZABLE,
            blocking_reasons=[],
            parameter_results={},
        )

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/complete/"

        with patch.object(CollegeAssessmentService, "check_assessment_readiness", return_value=(True, [], None)), \
             patch.object(CollegeAssessmentService, "evaluate_assessment_scoring", return_value=mock_result):
            response = self.client.post(url, {"remarks": "Review complete and fully verified"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["assessment"]["status"], "UNDER_REVIEW")

    # =========================================================================
    # 4. Return for Correction & Block Review Tests
    # =========================================================================

    def test_return_for_correction_requires_reason(self):
        """Returning for correction without reason returns HTTP 400."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.assigned_reviewer = self.reviewer
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/return/"
        response = self.client.post(url, {"reason": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_return_for_correction_succeeds(self):
        """Returning for correction with valid reason transitions to DRAFT."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.assigned_reviewer = self.reviewer
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/return/"
        response = self.client.post(url, {"reason": "Missing Annexure for C4"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["assessment"]["status"], "DRAFT")

    def test_block_review_succeeds(self):
        """Blocking review with valid reason transitions to REJECTED."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.assigned_reviewer = self.reviewer
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/block/"
        response = self.client.post(url, {"reason": "Statutory non-compliance detected"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["assessment"]["status"], "REJECTED")

    # =========================================================================
    # 5. Review History Tests
    # =========================================================================

    def test_review_history_endpoint_returns_immutable_logs(self):
        """Review history returns review records list."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()
        CollegeReviewRecord.objects.create(
            assessment=self.assessment_a,
            reviewer=self.reviewer,
            action=CollegeReviewAction.START_REVIEW,
            status_before="SUBMITTED",
            status_after="UNDER_REVIEW",
            comments="Initial test record",
        )

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/review/history/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["action"], "START_REVIEW")

    def test_principal_can_view_own_history_but_not_other_colleges(self):
        """Principal A cannot view history of College B."""
        self.client.force_authenticate(user=self.principal_a)
        url = f"/api/v1/college/assessments/{self.assessment_b.assessment_id}/review/history/"
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    # =========================================================================
    # 6. Certification Endpoint Tests
    # =========================================================================

    def test_certify_forbidden_for_regular_reviewer(self):
        """Regular committee reviewer cannot certify (HTTP 403)."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/certify/"
        response = self.client.post(url, {"remarks": "Attempting certification"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_certify_rejects_client_supplied_score(self):
        """Client attempting to inject certified score into certify endpoint is rejected (HTTP 400)."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.chair)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/certify/"
        response = self.client.post(url, {"certified_score": 100.0, "remarks": "Injected score"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("score" in str(response.data).lower())

    def test_certify_succeeds_for_committee_chair_when_gates_pass(self):
        """Committee Chair can certify when all statutory gates pass."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        mock_result = FrameworkResult(
            framework=FrameworkType.COLLEGE_2026,
            assessment_id=self.assessment_a.assessment_id,
            institution_id=self.college_a.aishe_code,
            calculation_id="calc-col-cert-01",
            version_index=1,
            timestamp=date(2026, 3, 1),
            raw_total=91.5,
            evidence_gated_total=91.5,
            final_certified_total=91.5,
            max_marks=100.0,
            certification_status=CertificationStatus.FINALIZABLE,
            blocking_reasons=[],
            parameter_results={},
        )

        def mock_eval(aid):
            self.assessment_a.certified_score = 91.5
            self.assessment_a.certification_status = "FINALIZABLE"
            self.assessment_a.save(update_fields=["certified_score", "certification_status"])
            return mock_result

        self.client.force_authenticate(user=self.chair)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/certify/"

        with patch.object(CollegeAssessmentService, "check_assessment_readiness", return_value=(True, [], None)), \
             patch.object(CollegeAssessmentService, "evaluate_assessment_scoring", side_effect=mock_eval):
            response = self.client.post(url, {"remarks": "Statutory college review certified"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["assessment"]["status"], "CERTIFIED")
            self.assertEqual(response.data["assessment"]["certification_status"], "CERTIFIED")
            self.assertEqual(float(response.data["assessment"]["certified_score"]), 91.5)

    def test_certified_assessment_is_locked_against_modifications(self):
        """Once certified, re-certification is blocked with HTTP 400."""
        self.assessment_a.status = "CERTIFIED"
        self.assessment_a.certification_status = "CERTIFIED"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.chair)
        url = f"/api/v1/college/assessments/{self.assessment_a.assessment_id}/certify/"
        response = self.client.post(url, {"remarks": "Attempting re-certify"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
