"""
NEP Excellence Awards 2026 - University Review & Certification REST API Tests (Phase 6C)
Tests:
- Review queue access, filtering, and conflict-of-interest exclusion
- Reviewer actions: start review, complete review, return for correction, block review
- Certification endpoint and role authorization (committee_chair vs committee vs nodal officer)
- Security & Anti-Tampering: Rejection of score injection payloads
- Immutability enforcement after certification
"""
from datetime import date
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.scoring.domain import FrameworkResult
from apps.scoring.enums import FrameworkType, CertificationStatus
from apps.university.models import (
    University,
    UniversityAssessment,
    UniversityReviewAction,
    UniversityReviewRecord,
)
from apps.university.services import UniversityAssessmentService

User = get_user_model()


class UniversityReviewAPITests(TestCase):
    """Integration tests for University review and certification API endpoints."""

    def setUp(self):
        self.client = APIClient()

        # Universities
        self.uni_a = University.objects.create(
            name="Kurukshetra University",
            aishe_code="U-0150",
            state="Haryana",
        )
        self.uni_b = University.objects.create(
            name="Maharshi Dayanand University",
            aishe_code="U-0158",
            state="Haryana",
        )

        # Users
        self.nodal_a = User.objects.create_user(
            email="nodal@kuk.ac.in",
            full_name="Dr. Nodal KUK",
            role="nodal_officer",
            university=self.uni_a,
            password="SecurePassword123!",
        )
        self.reviewer = User.objects.create_user(
            email="reviewer@haryana.gov.in",
            full_name="Dr. State Reviewer",
            role="committee",
            password="SecurePassword123!",
        )
        self.conflicted_reviewer = User.objects.create_user(
            email="reviewer.kuk@kuk.ac.in",
            full_name="Dr. KUK Reviewer",
            role="committee",
            university=self.uni_a,
            password="SecurePassword123!",
        )
        self.chair = User.objects.create_user(
            email="chair@haryana.gov.in",
            full_name="Prof. Committee Chair",
            role="committee_chair",
            password="SecurePassword123!",
        )
        self.admin = User.objects.create_user(
            email="admin@haryana.gov.in",
            full_name="State Admin",
            role="admin",
            password="SecurePassword123!",
        )

        # Assessment A (Kurukshetra University)
        self.assessment_a = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.pk,
            academic_year="2025-26",
            created_by=self.nodal_a,
        )
        self.assessment_a.status = "SUBMITTED"
        self.assessment_a.save()

        # Assessment B (Maharshi Dayanand University)
        self.assessment_b = UniversityAssessmentService.create_assessment(
            university_id=self.uni_b.pk,
            academic_year="2025-26",
            created_by=self.admin,
        )
        self.assessment_b.status = "SUBMITTED"
        self.assessment_b.save()

    # =========================================================================
    # Review Queue Tests
    # =========================================================================

    def test_institutional_user_cannot_access_review_queue(self):
        """Nodal officer is forbidden (HTTP 403) from review queue."""
        self.client.force_authenticate(user=self.nodal_a)
        url = "/api/v1/university/review/queue/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reviewer_sees_queue_with_conflict_of_interest_excluded(self):
        """Reviewer affiliated with uni_a cannot see uni_a in queue, only uni_b."""
        self.client.force_authenticate(user=self.conflicted_reviewer)
        url = "/api/v1/university/review/queue/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        assessment_ids = [item["assessment_id"] for item in results]
        self.assertNotIn(self.assessment_a.assessment_id, assessment_ids)
        self.assertIn(self.assessment_b.assessment_id, assessment_ids)

    def test_admin_and_chair_can_access_full_queue(self):
        """Chair and Admin see all submitted assessments in the queue."""
        self.client.force_authenticate(user=self.chair)
        url = "/api/v1/university/review/queue/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        assessment_ids = [item["assessment_id"] for item in results]
        self.assertIn(self.assessment_a.assessment_id, assessment_ids)
        self.assertIn(self.assessment_b.assessment_id, assessment_ids)

    def test_queue_filters_by_status_and_university(self):
        """Review queue properly applies status and university query filters."""
        self.assessment_b.status = "UNDER_REVIEW"
        self.assessment_b.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/university/review/queue/?status=UNDER_REVIEW"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["assessment_id"], self.assessment_b.assessment_id)

    # =========================================================================
    # Start Review Tests
    # =========================================================================

    def test_start_review_succeeds_for_authorized_reviewer(self):
        """Authorized reviewer successfully starts review."""
        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/review/start/"
        response = self.client.post(url, {"comments": "Starting review of U1-U5"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["assessment"]["status"], "UNDER_REVIEW")
        self.assertEqual(response.data["assessment"]["assigned_reviewer"], self.reviewer.pk)

    def test_start_review_blocks_conflicted_reviewer(self):
        """Affiliated reviewer cannot start review (HTTP 403)."""
        self.client.force_authenticate(user=self.conflicted_reviewer)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/review/start/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_review_rejects_score_injection(self):
        """Client attempting to inject score fields in start_review is rejected with HTTP 400."""
        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/review/start/"
        response = self.client.post(url, {"score": 95.0, "certified_score": 95.0}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("score" in str(response.data).lower())

    # =========================================================================
    # Return for Correction & Block Review Tests
    # =========================================================================

    def test_return_for_correction_requires_reason(self):
        """Returning for correction without reason returns HTTP 400."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/review/return/"
        response = self.client.post(url, {"reason": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_return_for_correction_succeeds(self):
        """Returning for correction with valid reason transitions to RETURNED."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/review/return/"
        response = self.client.post(url, {"reason": "Missing Annexure B for U4"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["assessment"]["status"], "RETURNED")

    def test_block_review_succeeds(self):
        """Blocking review with valid reason transitions to BLOCKED."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/review/block/"
        response = self.client.post(url, {"reason": "Statutory non-compliance detected"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["assessment"]["status"], "BLOCKED")

    # =========================================================================
    # Review History Tests
    # =========================================================================

    def test_review_history_endpoint_returns_immutable_logs(self):
        """Review history returns review records list."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()
        UniversityReviewRecord.objects.create(
            assessment=self.assessment_a,
            reviewer=self.reviewer,
            action=UniversityReviewAction.START_REVIEW,
            status_before="SUBMITTED",
            status_after="UNDER_REVIEW",
            comments="Initial test record",
        )

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/review/history/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["action"], "START_REVIEW")

    # =========================================================================
    # Certification Endpoint Tests
    # =========================================================================

    def test_certify_forbidden_for_regular_reviewer(self):
        """Regular committee reviewer cannot certify (HTTP 403)."""
        self.assessment_a.status = "CERTIFICATION_PENDING"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.reviewer)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/certify/"
        response = self.client.post(url, {"remarks": "Attempting certification"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_certify_rejects_client_supplied_score(self):
        """Client attempting to inject certified score into certify endpoint is rejected (HTTP 400)."""
        self.assessment_a.status = "CERTIFICATION_PENDING"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.chair)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/certify/"
        response = self.client.post(url, {"certified_score": 100.0, "remarks": "Injected score"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("score" in str(response.data).lower())

    def test_certify_succeeds_for_committee_chair_when_gates_pass(self):
        """Committee Chair can certify when all statutory gates pass."""
        self.assessment_a.status = "CERTIFICATION_PENDING"
        self.assessment_a.save()

        mock_result = FrameworkResult(
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_id=self.assessment_a.assessment_id,
            institution_id=self.uni_a.aishe_code,
            calculation_id="calc-api-cert-01",
            version_index=1,
            timestamp=date(2026, 3, 1),
            raw_total=92.5,
            evidence_gated_total=92.5,
            final_certified_total=92.5,
            max_marks=100.0,
            certification_status=CertificationStatus.FINALIZABLE,
            blocking_reasons=[],
            parameter_results={},
        )

        def mock_eval(aid):
            self.assessment_a.certified_score = 92.5
            self.assessment_a.certification_status = "FINALIZABLE"
            self.assessment_a.save(update_fields=["certified_score", "certification_status"])
            return mock_result

        self.client.force_authenticate(user=self.chair)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/certify/"

        with patch.object(UniversityAssessmentService, "check_assessment_readiness", return_value=(True, [], None)), \
             patch.object(UniversityAssessmentService, "evaluate_assessment_scoring", side_effect=mock_eval):
            response = self.client.post(url, {"remarks": "Statutory review certified"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["assessment"]["status"], "CERTIFIED")
            self.assertEqual(response.data["assessment"]["certification_status"], "CERTIFIED")
            self.assertEqual(float(response.data["assessment"]["certified_score"]), 92.5)

    def test_certified_assessment_is_locked_against_modifications(self):
        """Once certified, review actions and re-certification are blocked."""
        self.assessment_a.status = "CERTIFIED"
        self.assessment_a.certification_status = "CERTIFIED"
        self.assessment_a.save()

        self.client.force_authenticate(user=self.chair)
        url = f"/api/v1/university/assessments/{self.assessment_a.assessment_id}/certify/"
        response = self.client.post(url, {"remarks": "Attempting re-certify"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
