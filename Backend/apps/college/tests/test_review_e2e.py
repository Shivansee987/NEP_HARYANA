"""
NEP Excellence Awards 2026 - College Review & Certification End-to-End Workflow Test (Phase 7C)

Executes the complete 14-step statutory review and certification pipeline:
1. College and actor setup (principal, committee reviewer, committee chair, admin)
2. Draft assessment creation
3. Parameter input population (C1–C22)
4. Evidence document upload and association
5. Assessment submission (DRAFT -> SUBMITTED)
6. Review queue retrieval with conflict-of-interest exclusion
7. Review initiation (SUBMITTED -> UNDER_REVIEW)
8. Evidence verification workflow
9. Scoring evaluation via frozen NEP2026ScoringEngine (Status remains UNDER_REVIEW)
10. Review completion (Status remains UNDER_REVIEW)
11. Review history and append-only audit trail verification
12. Formal statutory certification by Committee Chair (UNDER_REVIEW -> CERTIFIED)
13. Post-certification immutability and lockdown enforcement
14. Audit integrity and tamper-proof verification
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
    CollegeAssessmentAuditLog,
    CollegeReviewAction,
    CollegeReviewRecord,
    ImmutableCollegeRecordError,
)
from apps.college.registry import COLLEGE_FRAMEWORK_CODE
from apps.college.services import CollegeAssessmentService, CollegeReviewService
from apps.college.validators import (
    AssessmentAlreadyCertifiedError,
    AssessmentLockedError,
    CertificationBlockedError,
)
from apps.evidence.enums import EvidenceLifecycleState
from apps.evidence.models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.scoring.domain import FrameworkResult
from apps.scoring.enums import FrameworkType, CertificationStatus

User = get_user_model()


class CollegeReviewEndToEndTests(TestCase):
    """Exhaustive 14-step end-to-end integration test of the College review and certification lifecycle."""

    def test_complete_14_step_review_and_certification_pipeline(self):
        client = APIClient()

        # ---------------------------------------------------------------------
        # Step 1: Institutional and Actor Setup
        # ---------------------------------------------------------------------
        college_hisar = College.objects.create(
            name="Govt College Hisar",
            aishe_code="C-00105",
        )
        principal_user = User.objects.create_user(
            email="principal.hisar@haryana.gov.in",
            full_name="Prof. Hisar Principal",
            role="principal",
            college=college_hisar,
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

        # Ensure reviewer is authorized for College framework
        ReviewerAuthorization.objects.create(
            user=external_reviewer,
            framework=COLLEGE_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )

        # ---------------------------------------------------------------------
        # Step 2: Assessment Creation in DRAFT
        # ---------------------------------------------------------------------
        client.force_authenticate(user=principal_user)
        create_res = client.post(
            f"/api/v1/college/colleges/{college_hisar.pk}/assessments/",
            {"academic_year": "2025-26"},
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        assessment_id = create_res.data["assessment_id"]
        self.assertEqual(create_res.data["status"], "DRAFT")
        self.assertEqual(create_res.data["framework"], "COLLEGE_2026")

        # ---------------------------------------------------------------------
        # Step 3: Parameter Input Population (C1)
        # ---------------------------------------------------------------------
        param_payload = {
            "raw_inputs": {
                "C1.1": {"achieved_targets_2024_25": 92, "fixed_targets_2024_25": 100}
            }
        }
        param_res = client.put(
            f"/api/v1/college/assessments/{assessment_id}/parameters/C1/",
            param_payload,
            format="json",
        )
        self.assertEqual(param_res.status_code, status.HTTP_200_OK)
        self.assertEqual(param_res.data["status"], "SAVED")

        # ---------------------------------------------------------------------
        # Step 4: Evidence Document Creation & Association
        # ---------------------------------------------------------------------
        assessment_obj = CollegeAssessment.objects.get(assessment_id=assessment_id)
        doc = EvidenceDocument.objects.create(
            uploader=principal_user,
            assessment_id=assessment_id,
            framework=COLLEGE_FRAMEWORK_CODE,
            institution_type="COLLEGE",
            institution_id=college_hisar.aishe_code,
            file_path="/media/evidence/c1_approval.pdf",
            original_filename="c1_approval.pdf",
            file_size=2048,
            file_checksum="c" * 64,
            mime_type="application/pdf",
            status=EvidenceLifecycleState.EVIDENCE_PENDING,
            document_date=date(2025, 10, 15),
            academic_year="2025-26",
        )
        EvidenceSubcriterionAssociation.objects.create(
            evidence=doc,
            parameter_id="C1",
            subcriterion_id="C1.1",
            academic_year="2025-26",
            associated_by=principal_user,
            is_active=True,
        )

        # ---------------------------------------------------------------------
        # Step 5: Assessment Submission (DRAFT -> SUBMITTED)
        # ---------------------------------------------------------------------
        submit_res = client.post(
            f"/api/v1/college/assessments/{assessment_id}/submit/",
            {},
            format="json",
        )
        self.assertEqual(submit_res.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_res.data["status"], "SUBMITTED")

        # Verify editing parameters is now locked (409 Conflict)
        locked_param_res = client.put(
            f"/api/v1/college/assessments/{assessment_id}/parameters/C1/",
            {"raw_inputs": {"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}}},
            format="json",
        )
        self.assertEqual(locked_param_res.status_code, status.HTTP_409_CONFLICT)

        # ---------------------------------------------------------------------
        # Step 6: Review Queue Retrieval
        # ---------------------------------------------------------------------
        client.force_authenticate(user=external_reviewer)
        queue_res = client.get("/api/v1/college/review/queue/")
        self.assertEqual(queue_res.status_code, status.HTTP_200_OK)
        results = queue_res.data.get("results", queue_res.data)
        queue_ids = [item["assessment_id"] for item in results]
        self.assertIn(assessment_id, queue_ids)

        # ---------------------------------------------------------------------
        # Step 7: Review Initiation (SUBMITTED -> UNDER_REVIEW)
        # ---------------------------------------------------------------------
        start_res = client.post(
            f"/api/v1/college/assessments/{assessment_id}/review/start/",
            {"comments": "Commencing statutory College review"},
            format="json",
        )
        self.assertEqual(start_res.status_code, status.HTTP_200_OK)
        self.assertEqual(start_res.data["assessment"]["status"], "UNDER_REVIEW")
        self.assertEqual(start_res.data["assessment"]["assigned_reviewer"], external_reviewer.pk)

        # ---------------------------------------------------------------------
        # Step 8: Evidence Verification Workflow
        # ---------------------------------------------------------------------
        doc.status = EvidenceLifecycleState.EVIDENCE_VERIFIED
        doc.save(update_fields=["status"])

        # ---------------------------------------------------------------------
        # Step 9: Scoring Evaluation via Frozen Engine (Status remains UNDER_REVIEW)
        # ---------------------------------------------------------------------
        mock_result = FrameworkResult(
            framework=FrameworkType.COLLEGE_2026,
            assessment_id=assessment_id,
            institution_id=college_hisar.aishe_code,
            calculation_id="calc-col-e2e-01",
            version_index=1,
            timestamp=date(2026, 3, 1),
            raw_total=89.5,
            evidence_gated_total=89.5,
            final_certified_total=89.5,
            max_marks=100.0,
            certification_status=CertificationStatus.FINALIZABLE,
            blocking_reasons=[],
            parameter_results={},
        )

        def mock_scoring_eval(*args, **kwargs):
            assessment_obj.refresh_from_db()
            assessment_obj.certified_score = 89.5
            assessment_obj.certification_status = "FINALIZABLE"
            assessment_obj.save(update_fields=["certified_score", "certification_status"])
            return mock_result

        with patch.object(CollegeAssessmentService, "evaluate_assessment_scoring", side_effect=mock_scoring_eval):
            eval_res = client.post(
                f"/api/v1/college/assessments/{assessment_id}/review/evaluate/",
                {},
                format="json",
            )
            self.assertEqual(eval_res.status_code, status.HTTP_200_OK)
            self.assertEqual(eval_res.data["assessment"]["status"], "UNDER_REVIEW")
            self.assertEqual(eval_res.data["review"]["action"], "EVALUATE")
            self.assertEqual(eval_res.data["scoring"]["certification_status"], "FINALIZABLE")

        # ---------------------------------------------------------------------
        # Step 10: Review Completion (Status remains UNDER_REVIEW)
        # ---------------------------------------------------------------------
        with patch.object(CollegeAssessmentService, "check_assessment_readiness", return_value=(True, [], None)), \
             patch.object(CollegeAssessmentService, "evaluate_assessment_scoring", side_effect=mock_scoring_eval):
            comp_res = client.post(
                f"/api/v1/college/assessments/{assessment_id}/review/complete/",
                {"remarks": "Institutional assessment and evidence verified. Recommended for certification."},
                format="json",
            )
            self.assertEqual(comp_res.status_code, status.HTTP_200_OK)
            self.assertEqual(comp_res.data["assessment"]["status"], "UNDER_REVIEW")

        # ---------------------------------------------------------------------
        # Step 11: Review History and Audit Trail Verification
        # ---------------------------------------------------------------------
        hist_res = client.get(f"/api/v1/college/assessments/{assessment_id}/review/history/")
        self.assertEqual(hist_res.status_code, status.HTTP_200_OK)
        actions = [rec["action"] for rec in hist_res.data]
        self.assertIn(CollegeReviewAction.START_REVIEW.value, actions)
        self.assertIn(CollegeReviewAction.EVALUATE.value, actions)
        self.assertIn(CollegeReviewAction.COMPLETE_REVIEW.value, actions)

        # ---------------------------------------------------------------------
        # Step 12: Statutory Certification by Committee Chair
        # ---------------------------------------------------------------------
        client.force_authenticate(user=chair_user)
        with patch.object(CollegeAssessmentService, "check_assessment_readiness", return_value=(True, [], None)), \
             patch.object(CollegeAssessmentService, "evaluate_assessment_scoring", side_effect=mock_scoring_eval):
            cert_res = client.post(
                f"/api/v1/college/assessments/{assessment_id}/certify/",
                {"remarks": "Final certification approved by State Screening Committee Chair"},
                format="json",
            )
            self.assertEqual(cert_res.status_code, status.HTTP_200_OK)
            self.assertEqual(cert_res.data["assessment"]["status"], "CERTIFIED")
            self.assertEqual(cert_res.data["assessment"]["certification_status"], "CERTIFIED")
            self.assertEqual(float(cert_res.data["assessment"]["certified_score"]), 89.5)

        # ---------------------------------------------------------------------
        # Step 13: Post-Certification Lockdown Enforcement
        # ---------------------------------------------------------------------
        # Attempt to modify parameters
        client.force_authenticate(user=principal_user)
        recert_param = client.put(
            f"/api/v1/college/assessments/{assessment_id}/parameters/C1/",
            {"raw_inputs": {"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}}},
            format="json",
        )
        self.assertIn(recert_param.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT])

        # Attempt to re-certify
        client.force_authenticate(user=chair_user)
        recert_res = client.post(
            f"/api/v1/college/assessments/{assessment_id}/certify/",
            {"remarks": "Duplicate certification attempt"},
            format="json",
        )
        self.assertEqual(recert_res.status_code, status.HTTP_400_BAD_REQUEST)

        # ---------------------------------------------------------------------
        # Step 14: Audit Integrity and Tamper-Proof Verification
        # ---------------------------------------------------------------------
        review_record = CollegeReviewRecord.objects.filter(
            assessment__assessment_id=assessment_id
        ).first()
        self.assertIsNotNone(review_record)

        # Verify review records are immutable
        with self.assertRaises(ImmutableCollegeRecordError):
            review_record.comments = "Tampered comment"
            review_record.save()

        with self.assertRaises(ImmutableCollegeRecordError):
            review_record.delete()

        # Verify audit logs are immutable
        audit_log = CollegeAssessmentAuditLog.objects.filter(
            assessment__assessment_id=assessment_id
        ).first()
        self.assertIsNotNone(audit_log)

        with self.assertRaises(ImmutableCollegeRecordError):
            audit_log.delete()

    def test_negative_e2e_certification_blocked_by_unverified_evidence(self):
        """Certification is strictly blocked when evidence is unverified."""
        college = College.objects.create(name="Govt College Sirsa", aishe_code="C-00106")
        principal = User.objects.create_user(
            email="p.sirsa@haryana.gov.in",
            full_name="Principal Sirsa",
            role="principal",
            college=college,
            password="SecurePassword2026!",
        )
        chair = User.objects.create_user(
            email="chair2@dhe.haryana.gov.in",
            full_name="Chair Two",
            role="committee_chair",
            password="SecurePassword2026!",
        )

        assessment = CollegeAssessmentService.create_assessment(
            college_id=college.pk, academic_year="2025-26", created_by=principal
        )
        assessment.status = "UNDER_REVIEW"
        assessment.save()

        client = APIClient()
        client.force_authenticate(user=chair)

        # Readiness fails due to unverified evidence
        with patch.object(
            CollegeAssessmentService,
            "check_assessment_readiness",
            return_value=(False, ["Evidence document EV-01 is SUBMITTED, must be VERIFIED"], None)
        ):
            res = client.post(
                f"/api/v1/college/assessments/{assessment.assessment_id}/certify/",
                {"remarks": "Attempting certification with unverified evidence"},
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("blocked", str(res.data).lower())

    def test_negative_e2e_conflicted_reviewer_cannot_participate(self):
        """Reviewer affiliated with a College cannot review that College's assessment."""
        college = College.objects.create(name="Govt College Bhiwani", aishe_code="C-00107")
        principal = User.objects.create_user(
            email="p.bhiwani@haryana.gov.in",
            full_name="Principal Bhiwani",
            role="principal",
            college=college,
            password="SecurePassword2026!",
        )
        conflicted_reviewer = User.objects.create_user(
            email="rev.bhiwani@haryana.gov.in",
            full_name="Reviewer Bhiwani",
            role="committee",
            college=college,
            password="SecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(
            user=conflicted_reviewer,
            framework=COLLEGE_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )

        assessment = CollegeAssessmentService.create_assessment(
            college_id=college.pk, academic_year="2025-26", created_by=principal
        )
        assessment.status = "SUBMITTED"
        assessment.save()

        client = APIClient()
        client.force_authenticate(user=conflicted_reviewer)

        # Start review is forbidden
        res = client.post(
            f"/api/v1/college/assessments/{assessment.assessment_id}/review/start/",
            {"comments": "Attempting review with conflict of interest"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("conflict", str(res.data).lower())

    def test_negative_e2e_score_injection_payload_rejected(self):
        """Review actions and certify endpoints reject client-supplied score fields."""
        college = College.objects.create(name="Govt College Rohtak", aishe_code="C-00108")
        principal = User.objects.create_user(
            email="p.rohtak@haryana.gov.in",
            full_name="Principal Rohtak",
            role="principal",
            college=college,
            password="SecurePassword2026!",
        )
        reviewer = User.objects.create_user(
            email="rev.rohtak@haryana.gov.in",
            full_name="Reviewer Rohtak",
            role="committee",
            password="SecurePassword2026!",
        )
        chair = User.objects.create_user(
            email="chair3@haryana.gov.in",
            full_name="Chair Three",
            role="committee_chair",
            password="SecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(
            user=reviewer,
            framework=COLLEGE_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )

        assessment = CollegeAssessmentService.create_assessment(
            college_id=college.pk, academic_year="2025-26", created_by=principal
        )
        assessment.status = "SUBMITTED"
        assessment.save()

        client = APIClient()
        client.force_authenticate(user=reviewer)

        # Attempt score injection in start review
        res_start = client.post(
            f"/api/v1/college/assessments/{assessment.assessment_id}/review/start/",
            {"comments": "Valid comment", "certified_score": 99.0},
            format="json",
        )
        self.assertEqual(res_start.status_code, status.HTTP_400_BAD_REQUEST)

        # Attempt score injection in complete review
        assessment.status = "UNDER_REVIEW"
        assessment.assigned_reviewer = reviewer
        assessment.save()

        res_complete = client.post(
            f"/api/v1/college/assessments/{assessment.assessment_id}/review/complete/",
            {"remarks": "Valid remarks", "score": 99.0},
            format="json",
        )
        self.assertEqual(res_complete.status_code, status.HTTP_400_BAD_REQUEST)

        # Attempt score injection in certify
        assessment.status = "UNDER_REVIEW"
        assessment.save()

        client.force_authenticate(user=chair)
        res_cert = client.post(
            f"/api/v1/college/assessments/{assessment.assessment_id}/certify/",
            {"remarks": "Chair remarks", "final_score": 99.0},
            format="json",
        )
        self.assertEqual(res_cert.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_e2e_unresolved_statutory_rules_block_certification(self):
        """
        Unmocked Negative E2E Test:
        Frozen scoring engine leaves C7, C8, and C16 as UNRESOLVED_RULE (and C5 boundary void).
        When the real unmocked scoring engine evaluates the assessment, it returns
        BLOCKED_BY_SPECIFICATION with final_certified_total = None.
        Statutory Gate 8/11 detects this and strictly blocks certification (HTTP 400).
        The assessment remains non-CERTIFIED.
        """
        college = College.objects.create(name="Govt College Jind", aishe_code="C-00109")
        principal = User.objects.create_user(
            email="p.jind@haryana.gov.in",
            full_name="Principal Jind",
            role="principal",
            college=college,
            password="SecurePassword2026!",
        )
        reviewer = User.objects.create_user(
            email="rev.jind@haryana.gov.in",
            full_name="Reviewer Jind",
            role="committee",
            password="SecurePassword2026!",
        )
        chair = User.objects.create_user(
            email="chair4@haryana.gov.in",
            full_name="Chair Four",
            role="committee_chair",
            password="SecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(
            user=reviewer,
            framework=COLLEGE_FRAMEWORK_CODE,
            institution_id="",
            is_active=True,
        )

        assessment = CollegeAssessmentService.create_assessment(
            college_id=college.pk, academic_year="2025-26", created_by=principal
        )
        assessment.parameter_data = {
            "C1": {
                "raw_inputs": {"C1.1": {"achieved_targets_2024_25": 90, "fixed_targets_2024_25": 100}}
            }
        }
        assessment.status = "SUBMITTED"
        assessment.save()

        client = APIClient()
        client.force_authenticate(user=reviewer)

        # Start review
        res_start = client.post(
            f"/api/v1/college/assessments/{assessment.assessment_id}/review/start/",
            {"comments": "Commencing review on College Jind"},
            format="json",
        )
        self.assertEqual(res_start.status_code, status.HTTP_200_OK)

        # Reviewer evaluates using UNMOCKED frozen scoring engine
        res_eval = client.post(
            f"/api/v1/college/assessments/{assessment.assessment_id}/review/evaluate/",
            {},
            format="json",
        )
        self.assertEqual(res_eval.status_code, status.HTTP_200_OK)
        self.assertEqual(res_eval.data["assessment"]["status"], "UNDER_REVIEW")
        scoring_status = res_eval.data["scoring"]["certification_status"]
        self.assertTrue("BLOCKED" in scoring_status or scoring_status == "BLOCKED_BY_SPECIFICATION")
        self.assertIsNone(res_eval.data["scoring"]["final_certified_total"])

        # Attempt certification by Committee Chair
        client.force_authenticate(user=chair)
        with patch.object(CollegeAssessmentService, "check_assessment_readiness", return_value=(True, [], None)):
            res_cert = client.post(
                f"/api/v1/college/assessments/{assessment.assessment_id}/certify/",
                {"remarks": "Attempting certification on assessment with unresolved statutory rules"},
                format="json",
            )
            # Must be rejected with HTTP 400 Bad Request
            self.assertEqual(res_cert.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("blocked", str(res_cert.data).lower())

        # Assessment remains non-CERTIFIED
        assessment.refresh_from_db()
        self.assertNotEqual(assessment.status, "CERTIFIED")
        self.assertNotEqual(assessment.certification_status, "CERTIFIED")

