"""
NEP Excellence Awards 2026 - Evidence Verification Workflow Tests (Phase 5C)
Comprehensive tests covering Reviewer Queue, Authorization, Assignment, Verification,
Rejection, Immutability, Concurrency, Hash/Version Binding, Framework Isolation, and Scoring Integration.
"""
import hashlib
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.authentication.models import College, User
from apps.evidence.enums import (
    AssignmentStatus,
    EvidenceAuditAction,
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
)
from apps.evidence.exceptions import (
    ConcurrentVerificationConflictError,
    EvidenceDomainError,
    EvidenceIntegrityError,
    FrameworkMismatchError,
    ImmutableRecordError,
    InvalidStateTransitionError,
    MandatoryRejectionReasonError,
    ReviewerAssignmentError,
    ReviewerConflictOfInterestError,
    ReviewerNotAuthorizedError,
    UnauthorizedEvidenceActionError,
)
from apps.evidence.models import (
    EvidenceAuditLog,
    EvidenceDocument,
    EvidenceReviewAssignment,
    EvidenceSubcriterionAssociation,
    EvidenceVerification,
    ReviewerAuthorization,
)
from apps.evidence.services import EvidenceService
from apps.scoring.enums import EvidenceState as ScoringEvidenceState, GatingStatus
from apps.scoring.evaluators.evidence_gating import evaluate_evidence


class VerificationWorkflowTestCase(TestCase):
    """
    Base test fixture providing colleges, institutional users, authorized reviewers,
    and state administrators for Phase 5C verification testing.
    """
    def setUp(self):
        super().setUp()
        self.college1 = College.objects.create(name="Govt College Karnal", aishe_code="C-3001")
        self.college2 = College.objects.create(name="Govt College Kurukshetra", aishe_code="C-3002")

        # Principals (Uploaders)
        self.principal_karnal = User.objects.create_user(
            email="principal.karnal@college.edu",
            full_name="Principal Karnal",
            role="principal",
            college=self.college1,
            password="securepassword123"
        )
        self.principal_kurukshetra = User.objects.create_user(
            email="principal.kurukshetra@college.edu",
            full_name="Principal Kurukshetra",
            role="principal",
            college=self.college2,
            password="securepassword123"
        )

        # Committee Reviewers
        self.college_reviewer = User.objects.create_user(
            email="college.reviewer@dhe.gov.in",
            full_name="College Screening Reviewer",
            role="committee",
            password="securepassword123"
        )
        self.univ_reviewer = User.objects.create_user(
            email="univ.reviewer@dhe.gov.in",
            full_name="University Screening Reviewer",
            role="committee",
            password="securepassword123"
        )
        self.unauthorized_reviewer = User.objects.create_user(
            email="unauthorized.reviewer@dhe.gov.in",
            full_name="Unscoped Screening Reviewer",
            role="committee",
            password="securepassword123"
        )
        self.affiliated_reviewer = User.objects.create_user(
            email="affiliated.reviewer@college.edu",
            full_name="Affiliated Screening Reviewer",
            role="committee",
            college=self.college1,
            password="securepassword123"
        )

        # State Administrator
        self.admin_user = User.objects.create_superuser(
            email="state.admin@dhe.gov.in",
            full_name="DHE State Admin",
            password="securepassword123"
        )

        # Explicit Scopes for Reviewers
        EvidenceService.authorize_reviewer(self.college_reviewer, framework="COLLEGE_2026", granted_by=self.admin_user)
        EvidenceService.authorize_reviewer(self.univ_reviewer, framework="UNIVERSITY_2026", granted_by=self.admin_user)

        self.sample_bytes = b"%PDF-1.4 Mock NEP 2026 Verification Test Document"
        self.sample_checksum = hashlib.sha256(self.sample_bytes).hexdigest()

    def create_pending_evidence(
        self,
        framework="COLLEGE_2026",
        institution_id="C-3001",
        institution_type="COLLEGE",
        uploader=None,
        assessment_id="ASSESS-C-2026-001",
        parameter_id=None,
        subcriterion_id=None,
    ) -> EvidenceDocument:
        """Helper to create and submit evidence to PENDING state."""
        uploader = uploader or self.principal_karnal
        doc = EvidenceService.create_evidence(
            uploader=uploader,
            assessment_id=assessment_id,
            framework=framework,
            institution_type=institution_type,
            institution_id=institution_id,
            original_filename="sample_evidence.pdf",
            file_bytes=self.sample_bytes,
            evidence_type="EVID_CERTIFICATE",
            document_date=date(2025, 9, 15),
            academic_year="2025-26",
        )
        if parameter_id and subcriterion_id:
            EvidenceService.associate_subcriterion(
                evidence_id=doc.pk,
                parameter_id=parameter_id,
                subcriterion_id=subcriterion_id,
                actor=uploader,
            )
        EvidenceService.submit_for_verification(doc.pk, uploader)
        doc.refresh_from_db()
        return doc


class TestReviewerQueue(VerificationWorkflowTestCase):
    """
    Category A: Reviewer Queue query layer and filtering.
    """
    def test_pending_evidence_appears_in_queue_with_complete_metadata(self):
        doc = self.create_pending_evidence(parameter_id="C1", subcriterion_id="C1.1")

        queue = EvidenceService.get_reviewer_queue(self.college_reviewer)
        self.assertEqual(len(queue), 1)

        item = queue[0]
        self.assertEqual(item["document_id"], str(doc.document_id))
        self.assertEqual(item["original_filename"], "sample_evidence.pdf")
        self.assertEqual(item["file_checksum"], self.sample_checksum)
        self.assertEqual(item["framework"], "COLLEGE_2026")
        self.assertEqual(item["institution_id"], "C-3001")
        self.assertEqual(item["status"], EvidenceLifecycleState.EVIDENCE_PENDING)
        self.assertEqual(item["version"], 1)
        self.assertEqual(item["uploader"]["email"], self.principal_karnal.email)
        self.assertEqual(len(item["associations"]), 1)
        self.assertEqual(item["associations"][0]["parameter_id"], "C1")
        self.assertEqual(item["associations"][0]["subcriterion_id"], "C1.1")

    def test_verified_and_rejected_evidence_excluded_from_pending_queue(self):
        doc1 = self.create_pending_evidence(parameter_id="C1", subcriterion_id="C1.1")
        doc2 = self.create_pending_evidence(parameter_id="C2", subcriterion_id="C2.1")
        doc3 = self.create_pending_evidence(parameter_id="C3", subcriterion_id="C3.1")

        # Verify doc1
        EvidenceService.verify_evidence(doc1.pk, self.college_reviewer, reason="Approved")
        # Reject doc2
        EvidenceService.reject_evidence(doc2.pk, self.college_reviewer, reason="Defective proof", rejection_code=RejectionReasonCode.INCOMPLETE_DOCUMENTATION)

        queue = EvidenceService.get_reviewer_queue(self.college_reviewer)
        queue_doc_ids = [item["document_id"] for item in queue]

        self.assertNotIn(str(doc1.document_id), queue_doc_ids)
        self.assertNotIn(str(doc2.document_id), queue_doc_ids)
        self.assertIn(str(doc3.document_id), queue_doc_ids)

    def test_queue_filtering_by_framework_and_institution(self):
        self.create_pending_evidence(
            framework="COLLEGE_2026",
            institution_id="C-3001",
            parameter_id="C1",
            subcriterion_id="C1.1"
        )
        self.create_pending_evidence(
            framework="COLLEGE_2026",
            institution_id="C-3002",
            uploader=self.principal_kurukshetra,
            parameter_id="C2",
            subcriterion_id="C2.1"
        )

        # Filter by institution C-3001
        q_karnal = EvidenceService.get_reviewer_queue(self.college_reviewer, institution_id="C-3001")
        self.assertEqual(len(q_karnal), 1)
        self.assertEqual(q_karnal[0]["institution_id"], "C-3001")

        # Filter by institution C-3002
        q_kurukshetra = EvidenceService.get_reviewer_queue(self.college_reviewer, institution_id="C-3002")
        self.assertEqual(len(q_kurukshetra), 1)
        self.assertEqual(q_kurukshetra[0]["institution_id"], "C-3002")

    def test_queue_cross_framework_isolation(self):
        # Create college evidence
        self.create_pending_evidence(framework="COLLEGE_2026", institution_id="C-3001")
        # Create university evidence
        self.create_pending_evidence(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-KU",
            institution_type="UNIVERSITY",
            uploader=self.admin_user,
            assessment_id="ASSESS-U-2026-001"
        )

        # College reviewer should only see College evidence
        q_college = EvidenceService.get_reviewer_queue(self.college_reviewer)
        self.assertTrue(all(item["framework"] == "COLLEGE_2026" for item in q_college))
        self.assertEqual(len(q_college), 1)

        # University reviewer should only see University evidence
        q_univ = EvidenceService.get_reviewer_queue(self.univ_reviewer)
        self.assertTrue(all(item["framework"] == "UNIVERSITY_2026" for item in q_univ))
        self.assertEqual(len(q_univ), 1)

    def test_queue_excludes_conflict_of_interest(self):
        # Principal uploaded evidence
        doc = self.create_pending_evidence(framework="COLLEGE_2026", institution_id="C-3001")

        # Affiliated reviewer belongs to C-3001
        EvidenceService.authorize_reviewer(self.affiliated_reviewer, framework="COLLEGE_2026")
        q = EvidenceService.get_reviewer_queue(self.affiliated_reviewer)
        self.assertEqual(len(q), 0, "Reviewer affiliated with institution should not see its queue items")


class TestReviewerAuthorization(VerificationWorkflowTestCase):
    """
    Category B: Explicit reviewer authorization checks & conflict-of-interest blocking.
    """
    def test_authorized_reviewer_can_verify(self):
        doc = self.create_pending_evidence()
        v = EvidenceService.verify_evidence(doc.pk, self.college_reviewer, reason="Verified valid proof")
        self.assertEqual(v.decision, VerificationDecision.VERIFIED)
        self.assertEqual(v.verifier, self.college_reviewer)

    def test_unauthorized_reviewer_cannot_verify(self):
        doc = self.create_pending_evidence()
        with self.assertRaises(ReviewerNotAuthorizedError):
            EvidenceService.verify_evidence(doc.pk, self.unauthorized_reviewer, reason="Attempted unauthorized verification")

    def test_unauthorized_reviewer_cannot_reject(self):
        doc = self.create_pending_evidence()
        with self.assertRaises(ReviewerNotAuthorizedError):
            EvidenceService.reject_evidence(
                doc.pk,
                self.unauthorized_reviewer,
                reason="Attempted unauthorized rejection",
                rejection_code=RejectionReasonCode.INCOMPLETE_DOCUMENTATION
            )

    def test_self_verification_blocked(self):
        # Admin uploads evidence
        doc = EvidenceService.create_evidence(
            uploader=self.admin_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            original_filename="admin_doc.pdf",
            file_bytes=self.sample_bytes,
        )
        EvidenceService.submit_for_verification(doc.pk, self.admin_user)

        with self.assertRaises(ReviewerConflictOfInterestError):
            EvidenceService.verify_evidence(doc.pk, self.admin_user, reason="Self verification attempt")

        with self.assertRaises(ReviewerConflictOfInterestError):
            EvidenceService.reject_evidence(doc.pk, self.admin_user, reason="Self rejection attempt")

    def test_institutional_affiliation_conflict_of_interest_blocked(self):
        doc = self.create_pending_evidence(institution_id="C-3001")
        EvidenceService.authorize_reviewer(self.affiliated_reviewer, framework="COLLEGE_2026")

        with self.assertRaises(ReviewerConflictOfInterestError):
            EvidenceService.verify_evidence(doc.pk, self.affiliated_reviewer, reason="Affiliated review")

    def test_principal_role_cannot_verify_or_reject(self):
        doc = self.create_pending_evidence(institution_id="C-3002", uploader=self.principal_kurukshetra)
        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceService.verify_evidence(doc.pk, self.principal_karnal, reason="Peer principal review")


class TestReviewerAssignment(VerificationWorkflowTestCase):
    """
    Category C: Reviewer assignment workflow, authorization, and audit.
    """
    def test_admin_can_assign_authorized_reviewer(self):
        doc = self.create_pending_evidence()
        assignment = EvidenceService.assign_reviewer(
            evidence_id=doc.pk,
            reviewer=self.college_reviewer,
            assigned_by=self.admin_user,
            notes="Assigned for evaluation"
        )
        self.assertEqual(assignment.status, AssignmentStatus.ACTIVE)
        self.assertEqual(assignment.reviewer, self.college_reviewer)

        doc.refresh_from_db()
        self.assertEqual(doc.assigned_reviewer, self.college_reviewer)

    def test_principal_cannot_assign_reviewer(self):
        doc = self.create_pending_evidence()
        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceService.assign_reviewer(
                evidence_id=doc.pk,
                reviewer=self.college_reviewer,
                assigned_by=self.principal_karnal,
            )

    def test_committee_cannot_assign_reviewer(self):
        doc = self.create_pending_evidence()
        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceService.assign_reviewer(
                evidence_id=doc.pk,
                reviewer=self.college_reviewer,
                assigned_by=self.univ_reviewer,
            )

    def test_cannot_assign_cross_framework_reviewer(self):
        doc = self.create_pending_evidence(framework="COLLEGE_2026")
        # Attempt to assign University reviewer to College evidence
        with self.assertRaises(FrameworkMismatchError):
            EvidenceService.assign_reviewer(
                evidence_id=doc.pk,
                reviewer=self.univ_reviewer,
                assigned_by=self.admin_user,
            )

    def test_cannot_assign_uploader_conflict_of_interest(self):
        doc = EvidenceService.create_evidence(
            uploader=self.admin_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            original_filename="doc.pdf",
            file_bytes=self.sample_bytes,
        )
        EvidenceService.submit_for_verification(doc.pk, self.admin_user)
        with self.assertRaises(ReviewerConflictOfInterestError):
            EvidenceService.assign_reviewer(
                evidence_id=doc.pk,
                reviewer=self.admin_user,
                assigned_by=self.admin_user,
            )

    def test_assignment_audit_trail(self):
        doc = self.create_pending_evidence()
        EvidenceService.assign_reviewer(
            evidence_id=doc.pk,
            reviewer=self.college_reviewer,
            assigned_by=self.admin_user,
            notes="Priority assignment"
        )
        log = EvidenceAuditLog.objects.filter(evidence=doc, action=EvidenceAuditAction.ASSIGNED).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.admin_user)
        self.assertIn("college.reviewer@dhe.gov.in", log.reason)

    def test_unassigned_reviewer_cannot_verify_assigned_evidence(self):
        doc = self.create_pending_evidence()
        other_college_reviewer = User.objects.create_user(
            email="other.reviewer@dhe.gov.in",
            full_name="Other Reviewer",
            role="committee",
            password="securepassword123"
        )
        EvidenceService.authorize_reviewer(other_college_reviewer, framework="COLLEGE_2026")

        # Assign to college_reviewer
        EvidenceService.assign_reviewer(
            evidence_id=doc.pk,
            reviewer=self.college_reviewer,
            assigned_by=self.admin_user,
        )

        # other_college_reviewer tries to verify
        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceService.verify_evidence(doc.pk, other_college_reviewer, reason="Interfering review")


class TestVerificationDecision(VerificationWorkflowTestCase):
    """
    Category D: VERIFY operation, state transition, and record immutability.
    """
    def test_verify_creates_immutable_record_and_updates_status(self):
        doc = self.create_pending_evidence()
        v = EvidenceService.verify_evidence(
            evidence_id=doc.pk,
            verifier=self.college_reviewer,
            reason="Authentic document with official seal",
            expected_checksum=self.sample_checksum,
            expected_version=1,
        )
        self.assertEqual(v.decision, VerificationDecision.VERIFIED)
        self.assertEqual(v.inspected_checksum, self.sample_checksum)
        self.assertEqual(v.inspected_version, 1)

        doc.refresh_from_db()
        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_VERIFIED)

        # Audit log verification
        audit = EvidenceAuditLog.objects.filter(evidence=doc, action=EvidenceAuditAction.VERIFIED).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.new_state, EvidenceLifecycleState.EVIDENCE_VERIFIED)

    def test_verified_evidence_unlocks_scoring_engine_eligibility(self):
        doc = self.create_pending_evidence(parameter_id="C1", subcriterion_id="C1.1")
        EvidenceService.verify_evidence(doc.pk, self.college_reviewer, reason="Verified")
        doc.refresh_from_db()

        scoring_doc = EvidenceService.to_scoring_domain(doc)
        status, multiplier, _ = evaluate_evidence(
            mandatory_evidence_types=["EVID_CERTIFICATE"],
            uploaded_docs=[scoring_doc]
        )
        self.assertEqual(status, GatingStatus.PASSED_EVIDENCE_VERIFIED)
        self.assertEqual(multiplier, 1.0)


class TestRejectionDecision(VerificationWorkflowTestCase):
    """
    Category E: REJECT operation, mandatory reasons, and structured codes.
    """
    def test_reject_requires_mandatory_reason(self):
        doc = self.create_pending_evidence()
        with self.assertRaises(MandatoryRejectionReasonError):
            EvidenceService.reject_evidence(
                evidence_id=doc.pk,
                verifier=self.college_reviewer,
                reason="   ",
            )

    def test_reject_creates_immutable_record_with_structured_reason(self):
        doc = self.create_pending_evidence()
        v = EvidenceService.reject_evidence(
            evidence_id=doc.pk,
            verifier=self.college_reviewer,
            reason="Document lacks mandatory institutional stamp on page 2",
            rejection_code=RejectionReasonCode.UNAUTHORIZED_SIGNATORY,
            expected_checksum=self.sample_checksum,
            expected_version=1,
        )
        self.assertEqual(v.decision, VerificationDecision.REJECTED)
        self.assertEqual(v.rejection_code, RejectionReasonCode.UNAUTHORIZED_SIGNATORY)
        self.assertEqual(v.inspected_checksum, self.sample_checksum)
        self.assertEqual(v.inspected_version, 1)

        doc.refresh_from_db()
        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_REJECTED)

    def test_rejected_evidence_does_not_unlock_scoring(self):
        doc = self.create_pending_evidence(parameter_id="C1", subcriterion_id="C1.1")
        EvidenceService.reject_evidence(
            doc.pk,
            self.college_reviewer,
            reason="Expired accreditation certificate",
            rejection_code=RejectionReasonCode.OUT_OF_PERIOD
        )
        doc.refresh_from_db()

        scoring_doc = EvidenceService.to_scoring_domain(doc)
        status, multiplier, _ = evaluate_evidence(
            mandatory_evidence_types=["EVID_CERTIFICATE"],
            uploaded_docs=[scoring_doc]
        )
        self.assertEqual(status, GatingStatus.FAILED_EVIDENCE_REJECTED)
        self.assertEqual(multiplier, 0.0)


class TestHistoryAndImmutability(VerificationWorkflowTestCase):
    """
    Category F: Append-only history and record immutability.
    """
    def test_verification_records_cannot_be_modified_or_deleted(self):
        doc = self.create_pending_evidence()
        v = EvidenceService.verify_evidence(doc.pk, self.college_reviewer, reason="First verification")

        v.reason = "Tampered reason"
        with self.assertRaises(ImmutableRecordError):
            v.save()

        with self.assertRaises(ImmutableRecordError):
            v.delete()

    def test_verification_history_is_append_only(self):
        doc = self.create_pending_evidence()
        v1 = EvidenceService.reject_evidence(
            doc.pk,
            self.college_reviewer,
            reason="Missing principal signature",
            rejection_code=RejectionReasonCode.UNAUTHORIZED_SIGNATORY
        )
        # Supersede with version 2
        new_bytes = b"%PDF-1.4 Mock NEP 2026 Signed Evidence V2"
        doc_v2 = EvidenceService.supersede_evidence(
            old_evidence_id=doc.pk,
            uploader=self.principal_karnal,
            original_filename="v2_signed.pdf",
            file_bytes=new_bytes,
        )
        EvidenceService.submit_for_verification(doc_v2.pk, self.principal_karnal)
        v2 = EvidenceService.verify_evidence(doc_v2.pk, self.college_reviewer, reason="V2 verified")

        history_v1 = EvidenceService.get_verification_history(doc.pk)
        self.assertEqual(len(history_v1), 1)
        self.assertEqual(history_v1[0]["decision"], VerificationDecision.REJECTED)

        history_v2 = EvidenceService.get_verification_history(doc_v2.pk)
        self.assertEqual(len(history_v2), 1)
        self.assertEqual(history_v2[0]["decision"], VerificationDecision.VERIFIED)


class TestHashAndVersionBinding(VerificationWorkflowTestCase):
    """
    Category G: Hash & Version binding integrity.
    """
    def test_checksum_mismatch_fails_verification(self):
        doc = self.create_pending_evidence()
        with self.assertRaises(EvidenceIntegrityError):
            EvidenceService.verify_evidence(
                evidence_id=doc.pk,
                verifier=self.college_reviewer,
                reason="Verification",
                expected_checksum="1111111111111111111111111111111111111111111111111111111111111111",
            )

    def test_version_mismatch_fails_verification(self):
        doc = self.create_pending_evidence()
        with self.assertRaises(EvidenceIntegrityError):
            EvidenceService.verify_evidence(
                evidence_id=doc.pk,
                verifier=self.college_reviewer,
                reason="Verification",
                expected_version=99,
            )

    def test_superseded_document_new_version_requires_own_verification(self):
        doc_v1 = self.create_pending_evidence(parameter_id="C1", subcriterion_id="C1.1")
        EvidenceService.verify_evidence(doc_v1.pk, self.college_reviewer, reason="V1 verified")

        # Supersede with v2
        v2_bytes = b"%PDF-1.4 Mock Replacement File V2"
        doc_v2 = EvidenceService.supersede_evidence(
            old_evidence_id=doc_v1.pk,
            uploader=self.principal_karnal,
            original_filename="v2.pdf",
            file_bytes=v2_bytes,
        )
        # Associate v2
        EvidenceService.associate_subcriterion(doc_v2.pk, "C1", "C1.1", self.principal_karnal)

        # v1 is superseded (inactive for scoring)
        doc_v1.refresh_from_db()
        scoring_v1 = EvidenceService.to_scoring_domain(doc_v1)
        self.assertEqual(scoring_v1.status, ScoringEvidenceState.EVIDENCE_PRESENT)

        # v2 is PRESENT (unverified)
        scoring_v2 = EvidenceService.to_scoring_domain(doc_v2)
        self.assertEqual(scoring_v2.status, ScoringEvidenceState.EVIDENCE_PRESENT)

        # Subcriterion scoring must be blocked until v2 is verified!
        self.assertFalse(EvidenceService.is_subcriterion_scoring_eligible("C1", "C1.1", doc_v2.assessment_id))


class TestConcurrencyDoubleDecisionProtection(VerificationWorkflowTestCase):
    """
    Category H: Concurrency protection & double-decision blocking.
    """
    def test_double_verify_fails_second_decision(self):
        doc = self.create_pending_evidence()

        # First verification succeeds
        v1 = EvidenceService.verify_evidence(doc.pk, self.college_reviewer, reason="First decision")
        self.assertEqual(v1.decision, VerificationDecision.VERIFIED)

        # Second verification attempt fails explicitly
        with self.assertRaises(ConcurrentVerificationConflictError):
            EvidenceService.verify_evidence(doc.pk, self.college_reviewer, reason="Second decision")

    def test_verify_then_reject_concurrent_fails(self):
        doc = self.create_pending_evidence()

        # First decision: Verified
        EvidenceService.verify_evidence(doc.pk, self.college_reviewer, reason="First decision")

        # Attempt to reject already verified evidence fails
        with self.assertRaises(ConcurrentVerificationConflictError):
            EvidenceService.reject_evidence(doc.pk, self.college_reviewer, reason="Conflicting rejection")


class TestFrameworkIsolation(VerificationWorkflowTestCase):
    """
    Category I: University vs. College framework isolation.
    """
    def test_university_reviewer_cannot_verify_college_evidence(self):
        doc = self.create_pending_evidence(framework="COLLEGE_2026")
        with self.assertRaises(FrameworkMismatchError):
            EvidenceService.verify_evidence(doc.pk, self.univ_reviewer, reason="Cross framework attempt")

    def test_college_reviewer_cannot_verify_university_evidence(self):
        doc = self.create_pending_evidence(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-01",
            institution_type="UNIVERSITY",
            uploader=self.admin_user,
            assessment_id="ASSESS-U-2026-001"
        )
        with self.assertRaises(FrameworkMismatchError):
            EvidenceService.verify_evidence(doc.pk, self.college_reviewer, reason="Cross framework attempt")


class TestScoringEngineIntegration(VerificationWorkflowTestCase):
    """
    Category J: Clean domain scoring integration & multi-evidence replacement.
    """
    def test_rejected_evidence_remains_ineligible_until_replacement_verified(self):
        # 1. Upload defective doc1
        doc1 = self.create_pending_evidence(
            parameter_id="C1",
            subcriterion_id="C1.1",
            assessment_id="ASSESS-C-2026-001"
        )
        EvidenceService.reject_evidence(
            doc1.pk,
            self.college_reviewer,
            reason="Uncertified copy",
            rejection_code=RejectionReasonCode.UNAUTHORIZED_SIGNATORY
        )

        # Gating evaluation is blocked
        is_eligible = EvidenceService.is_subcriterion_scoring_eligible("C1", "C1.1", "ASSESS-C-2026-001")
        self.assertFalse(is_eligible)

        # 2. Upload independent valid doc2 for the same subcriterion
        valid_bytes = b"%PDF-1.4 Mock Independent Certified Evidence Document"
        doc2 = EvidenceService.create_evidence(
            uploader=self.principal_karnal,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-3001",
            original_filename="certified_proof.pdf",
            file_bytes=valid_bytes,
            evidence_type="EVID_CERTIFICATE",
        )
        # Note: doc1 had subcriterion association, now associate doc2
        # Since unique constraint is (evidence, parameter_id, subcriterion_id), doc2 can link cleanly
        EvidenceService.associate_subcriterion(
            evidence_id=doc2.pk,
            parameter_id="C1",
            subcriterion_id="C1.1",
            actor=self.principal_karnal
        )
        EvidenceService.submit_for_verification(doc2.pk, self.principal_karnal)

        # Doc2 still pending -> not eligible yet
        self.assertFalse(EvidenceService.is_subcriterion_scoring_eligible("C1", "C1.1", "ASSESS-C-2026-001"))

        # Verify Doc2
        EvidenceService.verify_evidence(doc2.pk, self.college_reviewer, reason="Properly certified copy")

        # Now subcriterion C1.1 unlocks scoring eligibility!
        self.assertTrue(EvidenceService.is_subcriterion_scoring_eligible("C1", "C1.1", "ASSESS-C-2026-001"))
