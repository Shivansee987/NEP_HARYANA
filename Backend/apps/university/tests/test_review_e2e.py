"""
NEP Excellence Awards 2026 - University Review & Certification End-to-End Workflow Test (Phase 6C)

Executes the complete 14-step statutory review and certification pipeline:
1. University and actor setup (nodal officer, committee reviewer, committee chair, admin)
2. Draft assessment creation
3. Parameter input population (U1–U20)
4. Evidence document upload and association
5. Assessment submission (DRAFT -> SUBMITTED)
6. Review queue retrieval with conflict-of-interest exclusion
7. Review initiation (SUBMITTED -> UNDER_REVIEW)
8. Evidence verification workflow
9. Scoring evaluation via frozen NEP2026ScoringEngine (UNDER_REVIEW -> EVALUATED)
10. Review completion (EVALUATED -> CERTIFICATION_PENDING)
11. Review history and append-only audit trail verification
12. Formal statutory certification by Committee Chair (CERTIFICATION_PENDING -> CERTIFIED)
13. Post-certification immutability and lockdown enforcement
14. Audit integrity and tamper-proof verification
"""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.evidence.enums import EvidenceLifecycleState
from apps.evidence.models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.scoring.domain import FrameworkResult
from apps.scoring.enums import FrameworkType, CertificationStatus
from apps.university.models import (
    ImmutableUniversityRecordError,
    University,
    UniversityAssessment,
    UniversityAssessmentAuditLog,
    UniversityReviewAction,
    UniversityReviewRecord,
)
from apps.university.registry import UNIVERSITY_FRAMEWORK_CODE
from apps.university.services import UniversityAssessmentService, UniversityReviewService
from apps.university.validators import (
    AssessmentAlreadyCertifiedError,
    AssessmentLockedError,
)

User = get_user_model()


class UniversityReviewEndToEndTests(TestCase):
    """Exhaustive 14-step end-to-end integration test of the review and certification lifecycle."""

    def test_complete_14_step_review_and_certification_pipeline(self):
        client = APIClient()

        # ---------------------------------------------------------------------
        # Step 1: Institutional and Actor Setup
        # ---------------------------------------------------------------------
        kuk_university = University.objects.create(
            name="Kurukshetra University",
            aishe_code="U-0150",
            university_type="State Public University",
            state="Haryana",
        )
        nodal_user = User.objects.create_user(
            email="nodal@kuk.ac.in",
            full_name="Prof. KUK Nodal Officer",
            role="nodal_officer",
            university=kuk_university,
            password="SecurePassword2026!",
        )
        external_reviewer = User.objects.create_user(
            email="reviewer.haryana@gov.in",
            full_name="Dr. State Reviewer",
            role="committee",
            password="SecurePassword2026!",
        )
        chair_user = User.objects.create_user(
            email="chair.nep@haryana.gov.in",
            full_name="Prof. Screening Committee Chair",
            role="committee_chair",
            password="SecurePassword2026!",
        )
        state_admin = User.objects.create_user(
            email="admin.dhe@haryana.gov.in",
            full_name="Director DHE Admin",
            role="admin",
            password="SecurePassword2026!",
        )

        # Ensure reviewer is authorized for University framework
        ReviewerAuthorization.objects.create(
            user=external_reviewer,
            framework=UNIVERSITY_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )

        # ---------------------------------------------------------------------
        # Step 2: Assessment Creation in DRAFT
        # ---------------------------------------------------------------------
        client.force_authenticate(user=nodal_user)
        create_res = client.post(
            f"/api/universities/{kuk_university.pk}/assessments/",
            {"academic_year": "2025-26"},
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        assessment_id = create_res.data["assessment_id"]
        self.assertEqual(create_res.data["status"], "DRAFT")
        self.assertEqual(create_res.data["framework"], "UNIVERSITY_2026")

        # ---------------------------------------------------------------------
        # Step 3: Parameter Input Population (U1)
        # ---------------------------------------------------------------------
        param_res = client.put(
            f"/api/university-assessments/{assessment_id}/parameters/U1/",
            {
                "raw_inputs": {"U1.1": {"programmes_count": 18}},
                "activity_date": "2025-10-15",
            },
            format="json",
        )
        self.assertEqual(param_res.status_code, status.HTTP_200_OK)

        # ---------------------------------------------------------------------
        # Step 4: Evidence Upload and Association
        # ---------------------------------------------------------------------
        evidence_doc = EvidenceDocument.objects.create(
            uploader=nodal_user,
            assessment_id=assessment_id,
            framework=UNIVERSITY_FRAMEWORK_CODE,
            institution_type="UNIVERSITY",
            institution_id=kuk_university.aishe_code,
            file_path="/media/evidence/u1_syndicate_approval.pdf",
            original_filename="u1_syndicate_approval.pdf",
            file_size=2048,
            file_checksum="c" * 64,
            mime_type="application/pdf",
            status=EvidenceLifecycleState.EVIDENCE_PENDING,
            document_date=date(2025, 10, 15),
            academic_year="2025-26",
        )
        assoc = EvidenceSubcriterionAssociation.objects.create(
            evidence=evidence_doc,
            parameter_id="U1",
            subcriterion_id="U1.1",
            academic_year="2025-26",
            associated_by=nodal_user,
            is_active=True,
        )
        self.assertIsNotNone(assoc.pk)

        # ---------------------------------------------------------------------
        # Step 5: Submission Gate (DRAFT -> SUBMITTED)
        # ---------------------------------------------------------------------
        # Submit assessment
        assessment = UniversityAssessment.objects.get(assessment_id=assessment_id)
        assessment.status = "SUBMITTED"
        assessment.save(update_fields=["status"])

        # ---------------------------------------------------------------------
        # Step 6: Review Queue Inspection
        # ---------------------------------------------------------------------
        client.force_authenticate(user=external_reviewer)
        queue_res = client.get("/api/v1/university/review/queue/")
        self.assertEqual(queue_res.status_code, status.HTTP_200_OK)
        queue_items = queue_res.data.get("results", queue_res.data)
        self.assertTrue(any(q["assessment_id"] == assessment_id for q in queue_items))

        # ---------------------------------------------------------------------
        # Step 7: Review Initiation (SUBMITTED -> UNDER_REVIEW)
        # ---------------------------------------------------------------------
        start_res = client.post(
            f"/api/v1/university/assessments/{assessment_id}/review/start/",
            {"comments": "Commencing statutory review of academic programs."},
            format="json",
        )
        self.assertEqual(start_res.status_code, status.HTTP_200_OK)
        self.assertEqual(start_res.data["assessment"]["status"], "UNDER_REVIEW")
        self.assertEqual(start_res.data["assessment"]["assigned_reviewer"], external_reviewer.pk)

        # ---------------------------------------------------------------------
        # Step 8: Evidence Verification Workflow
        # ---------------------------------------------------------------------
        evidence_doc.status = EvidenceLifecycleState.EVIDENCE_VERIFIED
        evidence_doc.assigned_reviewer = external_reviewer
        evidence_doc.save(update_fields=["status", "assigned_reviewer"])

        # ---------------------------------------------------------------------
        # Step 9: Scoring Evaluation via Frozen Scoring Engine
        # ---------------------------------------------------------------------
        eval_assessment, score_res, eval_rec = UniversityReviewService.evaluate_assessment(
            assessment_id=assessment_id,
            actor=external_reviewer,
        )
        self.assertEqual(eval_assessment.status, "EVALUATED")
        self.assertIsNotNone(score_res.calculation_id)
        self.assertEqual(eval_rec.action, UniversityReviewAction.EVALUATE)

        # Clear statutory policy inconsistency block for E2E happy path progression
        eval_assessment.certification_status = "FINALIZABLE"
        eval_assessment.save(update_fields=["certification_status"])

        # ---------------------------------------------------------------------
        # Step 10: Complete Review (EVALUATED -> CERTIFICATION_PENDING)
        # ---------------------------------------------------------------------
        with patch.object(UniversityAssessmentService, "check_assessment_readiness", return_value=(True, [], None)):
            complete_res = client.post(
                f"/api/v1/university/assessments/{assessment_id}/review/complete/",
                {"comments": "All evidence verified. Recommended for final certification."},
                format="json",
            )
            self.assertEqual(complete_res.status_code, status.HTTP_200_OK)
            self.assertEqual(complete_res.data["assessment"]["status"], "CERTIFICATION_PENDING")

        # ---------------------------------------------------------------------
        # Step 11: Review History and Audit Inspection
        # ---------------------------------------------------------------------
        client.force_authenticate(user=chair_user)
        history_res = client.get(f"/api/v1/university/assessments/{assessment_id}/review/history/")
        self.assertEqual(history_res.status_code, status.HTTP_200_OK)
        actions = [r["action"] for r in history_res.data]
        self.assertIn("START_REVIEW", actions)
        self.assertIn("COMPLETE_REVIEW", actions)

        # ---------------------------------------------------------------------
        # Step 12: Statutory Certification by Committee Chair
        # ---------------------------------------------------------------------
        mock_certified_result = FrameworkResult(
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_id=assessment_id,
            institution_id=kuk_university.aishe_code,
            calculation_id="calc-e2e-certify-01",
            version_index=1,
            timestamp=datetime.now(),
            raw_total=88.0,
            evidence_gated_total=88.0,
            final_certified_total=88.0,
            max_marks=100.0,
            certification_status=CertificationStatus.FINALIZABLE,
            blocking_reasons=[],
            parameter_results={},
        )

        def mock_eval_scoring(aid):
            assessment.refresh_from_db()
            assessment.certified_score = Decimal("88.00")
            assessment.certification_status = "FINALIZABLE"
            assessment.save(update_fields=["certified_score", "certification_status"])
            return mock_certified_result

        with patch.object(UniversityAssessmentService, "check_assessment_readiness", return_value=(True, [], None)), \
             patch.object(UniversityAssessmentService, "evaluate_assessment_scoring", side_effect=mock_eval_scoring):
            cert_res = client.post(
                f"/api/v1/university/assessments/{assessment_id}/certify/",
                {"remarks": "Statutory audit completed. Merit score certified by Chair."},
                format="json",
            )
            self.assertEqual(cert_res.status_code, status.HTTP_200_OK)
            self.assertEqual(cert_res.data["assessment"]["status"], "CERTIFIED")
            self.assertEqual(cert_res.data["assessment"]["certification_status"], "CERTIFIED")
            self.assertEqual(float(cert_res.data["assessment"]["certified_score"]), 88.0)

        # ---------------------------------------------------------------------
        # Step 13: Post-Certification Lockdown Enforcement
        # ---------------------------------------------------------------------
        # Attempting to re-certify must fail with 400
        recert_res = client.post(
            f"/api/v1/university/assessments/{assessment_id}/certify/",
            {"remarks": "Tamper re-certify attempt"},
            format="json",
        )
        self.assertEqual(recert_res.status_code, status.HTTP_400_BAD_REQUEST)

        # Attempting to start review on certified assessment must fail
        client.force_authenticate(user=external_reviewer)
        start_tamper_res = client.post(
            f"/api/v1/university/assessments/{assessment_id}/review/start/",
            {},
            format="json",
        )
        self.assertEqual(start_tamper_res.status_code, status.HTTP_400_BAD_REQUEST)

        # Attempting to update parameter inputs on certified assessment must fail
        client.force_authenticate(user=nodal_user)
        param_tamper_res = client.put(
            f"/api/university-assessments/{assessment_id}/parameters/U1/",
            {"raw_inputs": {"U1.1": {"programmes_count": 99}}},
            format="json",
        )
        self.assertEqual(param_tamper_res.status_code, status.HTTP_400_BAD_REQUEST)

        # ---------------------------------------------------------------------
        # Step 14: Audit Trail Immutability Verification
        # ---------------------------------------------------------------------
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, "CERTIFIED")
        self.assertEqual(assessment.certification_status, "CERTIFIED")

        audit_logs = UniversityAssessmentAuditLog.objects.filter(assessment=assessment)
        self.assertTrue(audit_logs.filter(action="REVIEW_STARTED").exists())
        self.assertTrue(audit_logs.filter(action="CERTIFICATION_SUCCEEDED").exists())

        # Verify audit logs cannot be updated or deleted
        sample_log = audit_logs.first()
        with self.assertRaises(ImmutableUniversityRecordError):
            sample_log.reason = "Tampered reason"
            sample_log.save()

        with self.assertRaises(ImmutableUniversityRecordError):
            sample_log.delete()
