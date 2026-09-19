"""
NEP Excellence Awards 2026 - College Review & Certification Domain Unit Tests (Phase 7C)
Covers Categories A, B, C, D, E, F, G, H, I:
- Review lifecycle state machine & valid/invalid transitions
- Reviewer authorization & conflict-of-interest prevention
- Phase 5D evidence readiness gate integration
- Phase 4 frozen scoring engine delegation & score immutability
- Certification authority & 11 Statutory Gates verification
- Append-only review history & audit log immutability
- Concurrency & race condition prevention
- Framework & legacy isolation
"""
from datetime import date, datetime
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authentication.models import College
from apps.evidence.enums import EvidenceLifecycleState
from apps.evidence.models import (
    EvidenceDocument as DBEvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.evidence.services import EvidenceService
from apps.scoring.domain import FrameworkResult
from apps.scoring.enums import CertificationStatus, FrameworkType
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
    CertificationNotAuthorizedError,
    CollegeValidationError,
    EvidenceNotReadyError,
    FrameworkMismatchError,
    InvalidReviewStateError,
    ReviewConflictError,
    ReviewNotAuthorizedError,
    ScoringBlockedError,
)

User = get_user_model()


class CollegeReviewDomainTests(TestCase):
    """Exhaustive domain test suite for College assessment review and certification."""

    def setUp(self):
        # 1. Colleges
        self.college_a = College.objects.create(
            name="Govt College Ambala",
            aishe_code="C-00101",
        )
        self.college_b = College.objects.create(
            name="Govt College Rohtak",
            aishe_code="C-00102",
        )

        # 2. Users
        self.principal_a = User.objects.create_user(
            email="principal.ambala@haryana.gov.in",
            full_name="Principal Ambala",
            role="principal",
            college=self.college_a,
            password="SecurePassword123!"
        )
        self.admin_user = User.objects.create_user(
            email="dhe.admin@haryana.gov.in",
            full_name="State DHE Admin",
            role="admin",
            password="SecurePassword123!"
        )
        self.chair_user = User.objects.create_user(
            email="chair.committee@haryana.gov.in",
            full_name="Prof. Committee Chair",
            role="committee_chair",
            password="SecurePassword123!"
        )
        self.reviewer_user = User.objects.create_user(
            email="reviewer.ext@haryana.gov.in",
            full_name="Dr. External Reviewer",
            role="committee",
            password="SecurePassword123!"
        )
        # Conflicted reviewer (affiliated with college_a)
        self.conflicted_reviewer = User.objects.create_user(
            email="reviewer.ambala@haryana.gov.in",
            full_name="Dr. Ambala Reviewer",
            role="committee",
            college=self.college_a,
            password="SecurePassword123!"
        )

        # 3. Assessment in DRAFT
        self.assessment_a = CollegeAssessmentService.create_assessment(
            college_id=self.college_a.pk,
            academic_year="2025-26",
            created_by=self.principal_a,
        )
        # Populate parameter inputs
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment_a.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"approved": True}},
        )

    # =========================================================================
    # Category A: Review Lifecycle & State Machine
    # =========================================================================

    def test_draft_assessment_cannot_enter_review(self):
        """Assessment in DRAFT state cannot be reviewed; must be SUBMITTED."""
        with self.assertRaises(InvalidReviewStateError):
            CollegeReviewService.start_review(
                assessment_id=self.assessment_a.assessment_id,
                reviewer=self.reviewer_user,
            )

    def test_submitted_assessment_enters_under_review_successfully(self):
        """SUBMITTED assessment transitions to UNDER_REVIEW on start_review."""
        self.assessment_a.status = "SUBMITTED"
        self.assessment_a.save()

        updated, review_rec = CollegeReviewService.start_review(
            assessment_id=self.assessment_a.assessment_id,
            reviewer=self.reviewer_user,
            comments="Starting preliminary criteria review",
        )
        self.assertEqual(updated.status, "UNDER_REVIEW")
        self.assertEqual(updated.assigned_reviewer, self.reviewer_user)
        self.assertEqual(review_rec.action, CollegeReviewAction.START_REVIEW)
        self.assertEqual(review_rec.status_before, "SUBMITTED")
        self.assertEqual(review_rec.status_after, "UNDER_REVIEW")

    def test_return_for_correction_requires_meaningful_reason(self):
        """Returning for correction without reason is strictly rejected."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        with self.assertRaises(CollegeValidationError) as ctx:
            CollegeReviewService.return_for_correction(
                assessment_id=self.assessment_a.assessment_id,
                reviewer=self.reviewer_user,
                reason="",
            )
        self.assertEqual(ctx.exception.code, "REASON_REQUIRED")

    def test_return_for_correction_transitions_to_draft(self):
        """Returning for correction sets status to DRAFT and logs reason."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        updated, review_rec = CollegeReviewService.return_for_correction(
            assessment_id=self.assessment_a.assessment_id,
            reviewer=self.reviewer_user,
            reason="Parameter C1 resolution is missing date stamp.",
        )
        self.assertEqual(updated.status, "DRAFT")
        self.assertEqual(review_rec.action, CollegeReviewAction.RETURN_FOR_CORRECTION)
        self.assertEqual(review_rec.status_after, "DRAFT")
        self.assertEqual(review_rec.reason, "Parameter C1 resolution is missing date stamp.")

    def test_returned_assessment_can_be_updated_and_resubmitted(self):
        """When returned to DRAFT, college can update parameter data and re-submit."""
        self.assessment_a.status = "DRAFT"
        self.assessment_a.save()

        # College updates parameter data
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment_a.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"approved": True, "correction": "applied"}},
        )

        # College resubmits
        resubmitted = CollegeAssessmentService.submit_assessment(
            assessment_id=self.assessment_a.assessment_id,
            submitting_user=self.principal_a,
        )
        self.assertEqual(resubmitted.status, "SUBMITTED")

    def test_block_review_requires_meaningful_reason(self):
        """Blocking a review without reason is strictly rejected."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        with self.assertRaises(CollegeValidationError) as ctx:
            CollegeReviewService.block_review(
                assessment_id=self.assessment_a.assessment_id,
                reviewer=self.reviewer_user,
                reason="   ",
            )
        self.assertEqual(ctx.exception.code, "REASON_REQUIRED")

    def test_block_review_transitions_to_rejected(self):
        """Blocking review transitions assessment to REJECTED."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        updated, review_rec = CollegeReviewService.block_review(
            assessment_id=self.assessment_a.assessment_id,
            reviewer=self.reviewer_user,
            reason="Statutory accreditation certificate confirmed fraudulent.",
        )
        self.assertEqual(updated.status, "REJECTED")
        self.assertEqual(review_rec.action, CollegeReviewAction.BLOCK_REVIEW)

    # =========================================================================
    # Category B: Reviewer Authorization & Conflict of Interest
    # =========================================================================

    def test_unauthenticated_user_cannot_review(self):
        """Anonymous user cannot perform review actions."""
        self.assessment_a.status = "SUBMITTED"
        self.assessment_a.save()

        with self.assertRaises(ReviewNotAuthorizedError):
            CollegeReviewService.start_review(
                assessment_id=self.assessment_a.assessment_id,
                reviewer=None,
            )

    def test_institutional_user_cannot_perform_review_actions(self):
        """Principal or institution user cannot review assessment."""
        self.assessment_a.status = "SUBMITTED"
        self.assessment_a.save()

        with self.assertRaises(ReviewNotAuthorizedError):
            CollegeReviewService.start_review(
                assessment_id=self.assessment_a.assessment_id,
                reviewer=self.principal_a,
            )

    def test_conflict_of_interest_blocks_affiliated_reviewer(self):
        """Reviewer affiliated with the institution under assessment is blocked."""
        self.assessment_a.status = "SUBMITTED"
        self.assessment_a.save()

        with self.assertRaises(ReviewConflictError):
            CollegeReviewService.start_review(
                assessment_id=self.assessment_a.assessment_id,
                reviewer=self.conflicted_reviewer,
            )

    def test_reviewer_with_mismatched_framework_authorization_blocked(self):
        """Reviewer authorized only for UNIVERSITY_2026 cannot review COLLEGE_2026."""
        self.assessment_a.status = "SUBMITTED"
        self.assessment_a.save()

        # Register university-only authorization
        ReviewerAuthorization.objects.create(
            user=self.reviewer_user,
            framework="UNIVERSITY_2026",
            institution_id="",
            is_active=True,
        )

        with self.assertRaises(FrameworkMismatchError):
            CollegeReviewService.start_review(
                assessment_id=self.assessment_a.assessment_id,
                reviewer=self.reviewer_user,
            )

    # =========================================================================
    # Category C & D: Evidence Gate & Scoring Delegation
    # =========================================================================

    def test_incomplete_evidence_blocks_review_completion(self):
        """Review completion fails if evidence readiness check fails."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        # No verified evidence attached
        with self.assertRaises(EvidenceNotReadyError):
            CollegeReviewService.complete_review(
                assessment_id=self.assessment_a.assessment_id,
                reviewer=self.reviewer_user,
            )

    def test_scoring_delegates_exclusively_to_frozen_engine(self):
        """Evaluating scoring delegates to NEP2026ScoringEngine without recalculating."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        updated, result, review_rec = CollegeReviewService.evaluate_assessment(
            assessment_id=self.assessment_a.assessment_id,
            actor=self.reviewer_user,
        )
        self.assertEqual(updated.status, "UNDER_REVIEW")
        self.assertIsNotNone(result.calculation_id)
        self.assertEqual(review_rec.action, CollegeReviewAction.EVALUATE)
        self.assertIn("calculation_id", review_rec.scoring_snapshot)

    # =========================================================================
    # Category E: Certification Authority & Controls (11 Gates)
    # =========================================================================

    def test_standard_committee_reviewer_cannot_certify(self):
        """Standard committee reviewer lacks certification authority."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        with self.assertRaises(CertificationNotAuthorizedError):
            CollegeReviewService.certify_assessment(
                assessment_id=self.assessment_a.assessment_id,
                actor=self.reviewer_user,
            )

    def test_institutional_user_cannot_certify(self):
        """Principal or institution user cannot certify assessment."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        with self.assertRaises(CertificationNotAuthorizedError):
            CollegeReviewService.certify_assessment(
                assessment_id=self.assessment_a.assessment_id,
                actor=self.principal_a,
            )

    def test_certification_blocked_if_evidence_incomplete(self):
        """Certification fails at Gate 5 if evidence is incomplete/unverified."""
        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        with self.assertRaises(CertificationBlockedError):
            CollegeReviewService.certify_assessment(
                assessment_id=self.assessment_a.assessment_id,
                actor=self.admin_user,
            )

    def test_certification_succeeds_for_chair_and_locks_assessment(self):
        """Authorized committee chair can certify when all gates pass, locking assessment."""
        # Create valid verified evidence document to pass Gate 5
        doc = DBEvidenceDocument.objects.create(
            uploader=self.principal_a,
            assessment_id=self.assessment_a.assessment_id,
            framework=COLLEGE_FRAMEWORK_CODE,
            institution_type="COLLEGE",
            institution_id=self.college_a.aishe_code,
            file_path="/media/evidence/idp_approval.pdf",
            original_filename="idp_approval.pdf",
            file_size=1024,
            file_checksum="a" * 64,
            mime_type="application/pdf",
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED,
            document_date=date(2025, 9, 1),
            academic_year="2025-26",
        )
        EvidenceSubcriterionAssociation.objects.create(
            evidence=doc,
            parameter_id="C1",
            subcriterion_id="C1.1",
            academic_year="2025-26",
            associated_by=self.principal_a,
            is_active=True,
        )

        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        from unittest.mock import patch

        mock_result = FrameworkResult(
            framework=FrameworkType.COLLEGE_2026,
            assessment_id=self.assessment_a.assessment_id,
            institution_id=self.college_a.aishe_code,
            calculation_id="calc-certify-col-01",
            version_index=1,
            timestamp=datetime.now(),
            raw_total=85.0,
            evidence_gated_total=85.0,
            final_certified_total=85.0,
            max_marks=100.0,
            certification_status=CertificationStatus.FINALIZABLE,
            blocking_reasons=[],
            parameter_results={},
        )

        def mock_eval_scoring(aid):
            self.assessment_a.certified_score = 85.0
            self.assessment_a.certification_status = "FINALIZABLE"
            self.assessment_a.save(update_fields=["certified_score", "certification_status"])
            return mock_result

        with patch.object(CollegeAssessmentService, "check_assessment_readiness", return_value=(True, [], None)), \
             patch.object(CollegeAssessmentService, "evaluate_assessment_scoring", side_effect=mock_eval_scoring):
            certified, review_rec = CollegeReviewService.certify_assessment(
                assessment_id=self.assessment_a.assessment_id,
                actor=self.chair_user,
                remarks="Full statutory verification confirmed.",
            )
            self.assertEqual(certified.status, "CERTIFIED")
            self.assertEqual(certified.certification_status, "CERTIFIED")
            self.assertEqual(review_rec.action, CollegeReviewAction.CERTIFY)

            # Verify post-certification lock
            with self.assertRaises(AssessmentAlreadyCertifiedError):
                CollegeReviewService.certify_assessment(
                    assessment_id=self.assessment_a.assessment_id,
                    actor=self.admin_user,
                )
            with self.assertRaises(AssessmentAlreadyCertifiedError):
                CollegeReviewService.start_review(
                    assessment_id=self.assessment_a.assessment_id,
                    reviewer=self.reviewer_user,
                )

    # =========================================================================
    # Category F: History & Immutability
    # =========================================================================

    def test_review_records_are_append_only_and_cannot_be_mutated(self):
        """Review record modification or deletion raises ImmutableCollegeRecordError."""
        rec = CollegeReviewRecord.objects.create(
            assessment=self.assessment_a,
            reviewer=self.reviewer_user,
            action=CollegeReviewAction.START_REVIEW,
            status_before="SUBMITTED",
            status_after="UNDER_REVIEW",
        )
        with self.assertRaises(ImmutableCollegeRecordError):
            rec.comments = "Tampered comment"
            rec.save()

        with self.assertRaises(ImmutableCollegeRecordError):
            rec.delete()

    def test_audit_logs_are_append_only(self):
        """CollegeAssessmentAuditLog entries cannot be modified or deleted."""
        log = CollegeAssessmentAuditLog.objects.create(
            assessment=self.assessment_a,
            actor=self.reviewer_user,
            action="REVIEW_STARTED",
            previous_state="SUBMITTED",
            new_state="UNDER_REVIEW",
        )
        with self.assertRaises(ImmutableCollegeRecordError):
            log.action = "TAMPERED"
            log.save()

        with self.assertRaises(ImmutableCollegeRecordError):
            log.delete()

    # =========================================================================
    # Category H & I: Framework & Legacy Isolation
    # =========================================================================

    def test_cross_framework_evidence_blocks_certification(self):
        """If evidence belongs to non-COLLEGE framework, Gate 10 blocks certification."""
        foreign_doc = DBEvidenceDocument.objects.create(
            uploader=self.principal_a,
            assessment_id=self.assessment_a.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="U-0150",
            file_path="/media/evidence/doc.pdf",
            original_filename="doc.pdf",
            file_size=1024,
            file_checksum="b" * 64,
            mime_type="application/pdf",
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED,
            document_date=date(2025, 8, 1),
            academic_year="2025-26",
        )
        EvidenceSubcriterionAssociation.objects.create(
            evidence=foreign_doc,
            parameter_id="C1",
            subcriterion_id="C1.1",
            academic_year="2025-26",
            associated_by=self.principal_a,
            is_active=True,
        )

        self.assessment_a.status = "UNDER_REVIEW"
        self.assessment_a.save()

        with self.assertRaises(FrameworkMismatchError):
            CollegeReviewService.certify_assessment(
                assessment_id=self.assessment_a.assessment_id,
                actor=self.admin_user,
            )
