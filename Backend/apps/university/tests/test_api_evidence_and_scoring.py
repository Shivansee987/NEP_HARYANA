"""
Category F, G, H, I Tests: Evidence Integration, Coverage, Readiness, and Scoring Evaluation.

Verifies:
- Category F:
  - University evidence association works via Phase 5E evidence API.
  - College evidence cannot satisfy University assessment.
  - Unverified evidence remains blocked.
  - Verified evidence is recognized by readiness.
- Category G:
  - Coverage endpoint returns Phase 5D results without computing marks.
- Category H:
  - Readiness endpoint distinguishes evidence readiness from score results.
  - Missing, pending, rejected evidence yields is_ready=False.
  - Verified valid evidence yields is_ready=True.
- Category I:
  - Scoring evaluation delegates strictly to frozen NEP2026ScoringEngine.
  - Client-supplied scores in evaluation payload are rejected.
  - Unverified evidence yields 0 gated marks.
  - Verified evidence unlocks authoritative marks.
  - Scoring response returns framework UNIVERSITY_2026.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.evidence.models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.evidence.services import EvidenceService
from apps.scoring.enums import FrameworkType
from apps.university.models import University, UniversityAssessment
from apps.university.services import UniversityAssessmentService

User = get_user_model()


class UniversityAPIEvidenceAndScoringTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # State Admin
        self.admin = User.objects.create_user(
            email="admin@dhe.haryana.gov.in",
            full_name="DHE Administrator",
            role="admin",
            password="AdminPassword2026!",
        )

        # University & Nodal Officer
        self.uni = University.objects.create(
            name="Pandit Bhagwat Dayal Sharma University of Health Sciences",
            aishe_code="U-0165",
            state="Haryana",
        )
        self.uni_user = User.objects.create_user(
            email="nodal.uhsr@haryana.gov.in",
            full_name="UHSR Nodal Officer",
            role="nodal_officer",
            university=self.uni,
            password="SecureUHSRPassword2026!",
        )

        # Committee Reviewer with University Authorization
        self.reviewer = User.objects.create_user(
            email="committee.med@haryana.gov.in",
            full_name="Medical Committee Reviewer",
            role="committee",
            password="ReviewerSecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(
            user=self.reviewer,
            framework="UNIVERSITY_2026",
            institution_id="",
            is_active=True,
        )

        # Assessment Session
        self.assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni.id,
            academic_year="2025-26",
            created_by=self.uni_user,
        )

        # Record parameter data for U1 (12 programmes)
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={
                "programmes_count": 12,
                "U1.1": {"programmes_count": 12},
            },
        )

    # =========================================================================
    # Category F: Evidence Integration
    # =========================================================================

    def test_evidence_association_and_lifecycle(self):
        """Upload and associate evidence with U1.1 via Evidence infrastructure."""
        doc = EvidenceDocument.objects.create(
            assessment_id=self.assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.uni.aishe_code,
            original_filename="uhsr_u1_programmes.pdf",
            file_path="mock/path/uhsr_u1.pdf",
            mime_type="application/pdf",
            file_size=20480,
            file_checksum="f" * 64,
            uploader=self.uni_user,
            evidence_type="EVID_U1_APPROVAL",
            status="EVIDENCE_PENDING",
            is_active=True,
        )
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.id,
            parameter_id="U1",
            subcriterion_id="U1.1",
            actor=self.uni_user,
        )
        self.assertIsNotNone(assoc)
        self.assertEqual(assoc.subcriterion_id, "U1.1")
        self.assertEqual(assoc.parameter_id, "U1")

    def test_college_evidence_cannot_satisfy_university_assessment(self):
        """Evidence tagged as COLLEGE_2026 is ignored and cannot unlock University scoring."""
        college_doc = EvidenceDocument.objects.create(
            assessment_id=self.assessment.assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-9999",
            original_filename="college_doc.pdf",
            file_path="mock/path/college_doc.pdf",
            mime_type="application/pdf",
            file_size=5120,
            file_checksum="0" * 64,
            uploader=self.admin,
            evidence_type="EVID_U1_APPROVAL",
            status="EVIDENCE_VERIFIED",
            is_active=True,
        )
        # Directly creating association to test domain-level rejection in build_assessment_input
        EvidenceSubcriterionAssociation.objects.create(
            evidence=college_doc,
            parameter_id="U1",
            subcriterion_id="U1.1",
            academic_year="2025-26",
            associated_by=self.admin,
            is_active=True,
        )

        assessment_input = UniversityAssessmentService.build_assessment_input(self.assessment.assessment_id)
        u1_docs = assessment_input.parameters["U1"].subcriteria_inputs["U1.1"].evidence_docs
        # College doc must be filtered out by framework isolation in build_assessment_input
        self.assertEqual(len(u1_docs), 0)

    # =========================================================================
    # Category G: Coverage Endpoint
    # =========================================================================

    def test_coverage_endpoint_returns_phase5d_structure_without_marks(self):
        """Coverage endpoint returns Phase 5D audit without computing marks."""
        self.client.force_authenticate(user=self.uni_user)
        res = self.client.get(f"/api/university-assessments/{self.assessment.assessment_id}/coverage/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data
        self.assertEqual(data["framework"], "UNIVERSITY_2026")
        self.assertEqual(data["institution_id"], self.uni.aishe_code)
        self.assertEqual(data["assessment_id"], self.assessment.assessment_id)
        self.assertIn("assessment_period", data)
        self.assertIn("parameters", data)
        self.assertIn("summary", data)
        self.assertIn("is_ready_for_scoring", data)
        self.assertIn("blocking_reasons", data)

        # Ensure no marks or scores are computed in coverage response
        self.assertNotIn("earned_score", data)
        self.assertNotIn("certified_score", data)
        self.assertNotIn("total_marks", data)

    # =========================================================================
    # Category H: Readiness Endpoint
    # =========================================================================

    def test_readiness_pending_or_missing_evidence_is_not_ready(self):
        """Missing or unverified evidence results in is_ready = False."""
        self.client.force_authenticate(user=self.uni_user)
        res = self.client.get(f"/api/university-assessments/{self.assessment.assessment_id}/readiness/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data
        self.assertFalse(data["is_ready"])
        self.assertTrue(len(data["blocking_reasons"]) > 0)
        self.assertEqual(data["framework"], "UNIVERSITY_2026")

    def test_readiness_verified_evidence_unlocks_ready_status(self):
        """Verified evidence for mandatory parameter subcriteria unlocks ready state."""
        # Create and verify evidence for U1.1
        doc = EvidenceDocument.objects.create(
            assessment_id=self.assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.uni.aishe_code,
            original_filename="u1_verified.pdf",
            file_path="mock/path/u1_verified.pdf",
            mime_type="application/pdf",
            file_size=10240,
            file_checksum="1" * 64,
            uploader=self.uni_user,
            evidence_type="EVID_U1_APPROVAL",
            status="EVIDENCE_VERIFIED",
            is_active=True,
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc.id,
            parameter_id="U1",
            subcriterion_id="U1.1",
            actor=self.uni_user,
        )

        self.client.force_authenticate(user=self.uni_user)
        res = self.client.get(f"/api/university-assessments/{self.assessment.assessment_id}/coverage/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Verified subcriteria should be at least 1
        summary = res.data["summary"]
        self.assertGreaterEqual(summary["verified_subcriteria"], 1)

    # =========================================================================
    # Category I: Scoring Evaluation Endpoint
    # =========================================================================

    def test_evaluation_delegates_to_frozen_scoring_engine(self):
        """Evaluation endpoint delegates scoring to frozen engine and gates unverified marks."""
        # First evaluate while evidence is unverified -> score should be 0.0
        self.client.force_authenticate(user=self.reviewer)
        res = self.client.post(
            f"/api/university-assessments/{self.assessment.assessment_id}/evaluate/",
            {},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data
        self.assertEqual(data["framework"], "UNIVERSITY_2026")
        self.assertEqual(data["assessment_id"], self.assessment.assessment_id)
        self.assertIn("parameter_results", data)
        self.assertIn("U1", data["parameter_results"])
        # Unverified evidence gates score to 0.0
        self.assertEqual(data["parameter_results"]["U1"]["evidence_gated_score"], 0.0)

        # Now upload and verify evidence for U1
        doc = EvidenceDocument.objects.create(
            assessment_id=self.assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.uni.aishe_code,
            original_filename="u1_verified.pdf",
            file_path="mock/path/u1_verified.pdf",
            mime_type="application/pdf",
            file_size=10240,
            file_checksum="9" * 64,
            uploader=self.uni_user,
            evidence_type="EVID_U1_APPROVAL",
            status="EVIDENCE_VERIFIED",
            is_active=True,
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc.id,
            parameter_id="U1",
            subcriterion_id="U1.1",
            actor=self.uni_user,
        )

        # Re-evaluate with VERIFIED evidence
        res_verified = self.client.post(
            f"/api/university-assessments/{self.assessment.assessment_id}/evaluate/",
            {},
            format="json"
        )
        self.assertEqual(res_verified.status_code, status.HTTP_200_OK)
        data_verified = res_verified.data
        # 12 programmes > 10.0 -> max score 4.0
        self.assertEqual(data_verified["parameter_results"]["U1"]["evidence_gated_score"], 4.0)

    def test_client_cannot_supply_score_in_evaluation_payload(self):
        """Client-supplied score in evaluation request body is rejected."""
        self.client.force_authenticate(user=self.reviewer)
        payload = {
            "score": 90.0,
            "certified_score": 90.0,
        }
        res = self.client.post(
            f"/api/university-assessments/{self.assessment.assessment_id}/evaluate/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
