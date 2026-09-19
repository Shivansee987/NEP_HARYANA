"""
NEP Excellence Awards 2026 - Comprehensive Evidence Domain & Lifecycle Tests
Verifies categories A through L as mandated by Phase 5A specification.
"""
import hashlib
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from apps.authentication.models import College, User
from apps.evidence.enums import (
    EvidenceAuditAction,
    EvidenceLifecycleState,
    VerificationDecision,
)
from apps.evidence.exceptions import (
    EvidenceDomainError,
    EvidenceIntegrityError,
    FrameworkMismatchError,
    ImmutableRecordError,
    InvalidStateTransitionError,
    UnauthorizedEvidenceActionError,
)
from apps.evidence.models import (
    EvidenceAuditLog,
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    EvidenceVerification,
)
from apps.evidence.services import EvidenceService
from apps.scoring.domain import (
    AssessmentContext,
    AssessmentInput,
    InstitutionType,
    FrameworkType,
    EvidenceDocument as ScoringEvidenceDoc,
)
from apps.scoring.engine import NEP2026ScoringEngine
from apps.scoring.enums import EvidenceState as ScoringEvidenceState, GatingStatus
from apps.scoring.evaluators.evidence_gating import evaluate_evidence


class EvidenceDomainTestCase(TestCase):
    """
    Base test setup providing users with explicit roles and sample colleges.
    """
    def setUp(self):
        self.college1 = College.objects.create(name="Govt College Sector 1", aishe_code="C-1001")
        self.college2 = College.objects.create(name="Govt College Sector 14", aishe_code="C-1002")

        self.principal_user = User.objects.create_user(
            email="principal1@college.edu",
            full_name="Principal User 1",
            role="principal",
            college=self.college1,
            password="securepassword123"
        )
        self.principal_user2 = User.objects.create_user(
            email="principal2@college.edu",
            full_name="Principal User 2",
            role="principal",
            college=self.college2,
            password="securepassword123"
        )
        self.committee_user = User.objects.create_user(
            email="evaluator@dhe.gov.in",
            full_name="Screening Committee Member",
            role="committee",
            password="securepassword123"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@dhe.gov.in",
            full_name="DHE State Admin",
            password="securepassword123"
        )
        self.sample_bytes = b"%PDF-1.4 Mock NEP 2026 Evidence Document Content"
        self.sample_checksum = hashlib.sha256(self.sample_bytes).hexdigest()


class TestEvidenceCreation(EvidenceDomainTestCase):
    """
    Category A: Evidence creation & basic integrity.
    """
    def test_valid_evidence_creation(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            original_filename="idp_plan.pdf",
            file_bytes=self.sample_bytes,
            mime_type="application/pdf",
            evidence_type="EVID_U4_IDP",
            document_date=date(2025, 8, 15),
            academic_year="2024-25",
        )
        self.assertIsNotNone(doc.document_id)
        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_PRESENT)
        self.assertEqual(doc.file_checksum, self.sample_checksum)
        self.assertEqual(doc.file_size, len(self.sample_bytes))
        self.assertEqual(doc.version, 1)
        self.assertTrue(doc.is_active)
        self.assertEqual(doc.uploader, self.principal_user)

    def test_mismatched_checksum_fails(self):
        with self.assertRaises(EvidenceIntegrityError):
            EvidenceService.create_evidence(
                uploader=self.principal_user,
                assessment_id="ASSESS-U-2026-001",
                framework="UNIVERSITY_2026",
                institution_type="UNIVERSITY",
                institution_id="UNIV-01",
                original_filename="tampered.pdf",
                file_bytes=self.sample_bytes,
                file_checksum="0000000000000000000000000000000000000000000000000000000000000000",
            )

    def test_committee_cannot_upload_institution_evidence(self):
        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceService.create_evidence(
                uploader=self.committee_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-1001",
                original_filename="report.pdf",
                file_bytes=self.sample_bytes,
            )


class TestStateTransitions(EvidenceDomainTestCase):
    """
    Category B: State transitions and lifecycle rules.
    """
    def setUp(self):
        super().setUp()
        self.doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="mou.pdf",
            file_bytes=self.sample_bytes,
            evidence_type="EVID_MOU",
        )

    def test_legal_transition_present_to_pending(self):
        updated = EvidenceService.submit_for_verification(self.doc.pk, self.principal_user)
        self.assertEqual(updated.status, EvidenceLifecycleState.EVIDENCE_PENDING)

    def test_legal_transition_pending_to_verified(self):
        EvidenceService.submit_for_verification(self.doc.pk, self.principal_user)
        verification = EvidenceService.verify_evidence(
            self.doc.pk,
            self.committee_user,
            reason="All criteria met and valid"
        )
        self.assertEqual(verification.decision, VerificationDecision.VERIFIED)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, EvidenceLifecycleState.EVIDENCE_VERIFIED)

    def test_legal_transition_pending_to_rejected(self):
        EvidenceService.submit_for_verification(self.doc.pk, self.principal_user)
        verification = EvidenceService.reject_evidence(
            self.doc.pk,
            self.committee_user,
            reason="Signatures missing on MoU page 3"
        )
        self.assertEqual(verification.decision, VerificationDecision.REJECTED)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, EvidenceLifecycleState.EVIDENCE_REJECTED)

    def test_illegal_transition_present_to_verified_rejected(self):
        # Cannot verify directly from EVIDENCE_PRESENT without submitting
        with self.assertRaises(InvalidStateTransitionError):
            EvidenceService.verify_evidence(self.doc.pk, self.committee_user, reason="Premature")

    def test_illegal_transition_present_to_rejected_rejected(self):
        with self.assertRaises(InvalidStateTransitionError):
            EvidenceService.reject_evidence(self.doc.pk, self.committee_user, reason="Premature")

    def test_illegal_transition_rejected_to_verified_rejected(self):
        EvidenceService.submit_for_verification(self.doc.pk, self.principal_user)
        EvidenceService.reject_evidence(self.doc.pk, self.committee_user, reason="Invalid date")
        with self.assertRaises(InvalidStateTransitionError):
            EvidenceService.verify_evidence(self.doc.pk, self.committee_user, reason="Attempted bypass")


class TestVerificationAuditAndHistory(EvidenceDomainTestCase):
    """
    Category C: Verification recording & auditability.
    """
    def test_verification_records_verifier_and_reason(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            original_filename="patent.pdf",
            file_bytes=self.sample_bytes,
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        verification = EvidenceService.verify_evidence(
            doc.pk,
            self.committee_user,
            reason="Patent registration verified with Indian Patent Office"
        )
        self.assertEqual(verification.verifier, self.committee_user)
        self.assertEqual(verification.reason, "Patent registration verified with Indian Patent Office")
        self.assertEqual(verification.evidence, doc)

    def test_rejection_requires_mandatory_reason(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            original_filename="patent.pdf",
            file_bytes=self.sample_bytes,
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        with self.assertRaises(EvidenceDomainError):
            EvidenceService.reject_evidence(doc.pk, self.committee_user, reason="  ")

    def test_verification_history_is_retained(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="doc1.pdf",
            file_bytes=self.sample_bytes,
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        v1 = EvidenceService.reject_evidence(doc.pk, self.committee_user, reason="Incorrect academic year")
        self.assertEqual(doc.verifications.count(), 1)
        self.assertEqual(doc.verifications.first().decision, VerificationDecision.REJECTED)


class TestImmutability(EvidenceDomainTestCase):
    """
    Category D: Immutability enforcement.
    """
    def setUp(self):
        super().setUp()
        self.doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="original.pdf",
            file_bytes=self.sample_bytes,
        )

    def test_checksum_immutable(self):
        self.doc.file_checksum = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        with self.assertRaises(EvidenceIntegrityError):
            self.doc.save()

    def test_document_id_immutable(self):
        import uuid
        self.doc.document_id = uuid.uuid4()
        with self.assertRaises(ImmutableRecordError):
            self.doc.save()

    def test_uploader_immutable(self):
        self.doc.uploader = self.admin_user
        with self.assertRaises(ImmutableRecordError):
            self.doc.save()

    def test_framework_immutable(self):
        self.doc.framework = "UNIVERSITY_2026"
        with self.assertRaises(ImmutableRecordError):
            self.doc.save()

    def test_verification_record_immutable(self):
        EvidenceService.submit_for_verification(self.doc.pk, self.principal_user)
        v = EvidenceService.verify_evidence(self.doc.pk, self.committee_user, reason="Looks good")
        v.reason = "Modified reason after the fact"
        with self.assertRaises(ImmutableRecordError):
            v.save()

    def test_verification_record_cannot_be_deleted(self):
        EvidenceService.submit_for_verification(self.doc.pk, self.principal_user)
        v = EvidenceService.verify_evidence(self.doc.pk, self.committee_user, reason="Looks good")
        with self.assertRaises(ImmutableRecordError):
            v.delete()

    def test_audit_log_cannot_be_modified_or_deleted(self):
        log = EvidenceAuditLog.objects.filter(evidence=self.doc).first()
        self.assertIsNotNone(log)
        log.reason = "Attempted tampering"
        with self.assertRaises(ImmutableRecordError):
            log.save()
        with self.assertRaises(ImmutableRecordError):
            log.delete()


class TestVersioningAndSupersession(EvidenceDomainTestCase):
    """
    Category E: Versioning and document replacement.
    """
    def test_supersede_creates_new_version_and_preserves_old(self):
        doc_v1 = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="v1.pdf",
            file_bytes=self.sample_bytes,
        )
        EvidenceService.submit_for_verification(doc_v1.pk, self.principal_user)
        EvidenceService.reject_evidence(doc_v1.pk, self.committee_user, reason="Missing signature page")

        # Replace with v2
        new_bytes = b"%PDF-1.4 Mock NEP 2026 Evidence V2 Content with Signature"
        doc_v2 = EvidenceService.supersede_evidence(
            old_evidence_id=doc_v1.pk,
            uploader=self.principal_user,
            original_filename="v2_signed.pdf",
            file_bytes=new_bytes,
            reason="Added missing signature page",
        )

        doc_v1.refresh_from_db()
        self.assertEqual(doc_v1.status, EvidenceLifecycleState.EVIDENCE_SUPERSEDED)
        self.assertFalse(doc_v1.is_active)
        self.assertEqual(doc_v1.superseded_by, doc_v2)

        self.assertEqual(doc_v2.version, 2)
        self.assertTrue(doc_v2.is_active)
        self.assertEqual(doc_v2.status, EvidenceLifecycleState.EVIDENCE_PRESENT)
        self.assertEqual(doc_v2.file_checksum, hashlib.sha256(new_bytes).hexdigest())

        # Old document remains historically intact and visible in DB
        self.assertEqual(EvidenceDocument.objects.filter(assessment_id="ASSESS-C-2026-001").count(), 2)


class TestAssessmentPeriod(EvidenceDomainTestCase):
    """
    Category F: Assessment period & activity date decoupling.
    """
    def test_activity_date_preserved_distinct_from_upload_date(self):
        activity_date = date(2025, 10, 24)
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            original_filename="workshop.pdf",
            file_bytes=self.sample_bytes,
            document_date=activity_date,
        )
        self.assertEqual(doc.document_date, activity_date)
        # Upload date is modern timestamp (today)
        self.assertEqual(doc.upload_timestamp.date(), timezone.now().date())
        self.assertNotEqual(doc.document_date, doc.upload_timestamp.date())


class TestAcademicYear(EvidenceDomainTestCase):
    """
    Category G: Academic-year handling.
    """
    def test_optional_academic_year_works(self):
        doc_generic = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="generic.pdf",
            file_bytes=self.sample_bytes,
        )
        self.assertIsNone(doc_generic.academic_year)

        doc_u4a = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            original_filename="idp_2024_25.pdf",
            file_bytes=self.sample_bytes,
            academic_year="2024-25",
            evidence_type="EVID_U4_IDP"
        )
        self.assertEqual(doc_u4a.academic_year, "2024-25")


class TestEvidenceAssociation(EvidenceDomainTestCase):
    """
    Category H: Explicit subcriterion association.
    """
    def test_association_and_reuse_distinction(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            original_filename="institutional_strategic_plan.pdf",
            file_bytes=self.sample_bytes,
        )
        # Attach to U4.1
        assoc1 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U4",
            subcriterion_id="U4.1",
            actor=self.principal_user,
            academic_year="2024-25",
        )
        # Attach same physical document to U4.2
        assoc2 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U4",
            subcriterion_id="U4.2",
            actor=self.principal_user,
            academic_year="2025-26",
        )
        self.assertEqual(doc.associations.count(), 2)
        self.assertEqual(assoc1.subcriterion_id, "U4.1")
        self.assertEqual(assoc2.subcriterion_id, "U4.2")


class TestVerificationGatingContract(EvidenceDomainTestCase):
    """
    Category I: Scoring engine evidence gating contract.
    NO VERIFIED EVIDENCE = NO EARNED MARKS.
    """
    def test_gating_present_yields_provisional_zero_earned(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="cert.pdf",
            file_bytes=self.sample_bytes,
            evidence_type="EVID_CERTIFICATE",
        )
        scoring_doc = EvidenceService.to_scoring_domain(doc)
        status, multiplier, trace = evaluate_evidence(
            mandatory_evidence_types=["EVID_CERTIFICATE"],
            uploaded_docs=[scoring_doc]
        )
        claimed_score = 10.0
        earned_score = claimed_score * multiplier
        self.assertEqual(status, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)
        self.assertEqual(earned_score, 0.0)

    def test_gating_pending_yields_provisional_zero_earned(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="cert.pdf",
            file_bytes=self.sample_bytes,
            evidence_type="EVID_CERTIFICATE",
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        doc.refresh_from_db()
        scoring_doc = EvidenceService.to_scoring_domain(doc)
        status, multiplier, trace = evaluate_evidence(
            mandatory_evidence_types=["EVID_CERTIFICATE"],
            uploaded_docs=[scoring_doc]
        )
        claimed_score = 10.0
        earned_score = claimed_score * multiplier
        self.assertEqual(status, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)
        self.assertEqual(earned_score, 0.0)

    def test_gating_rejected_yields_failed_zero_earned(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="cert.pdf",
            file_bytes=self.sample_bytes,
            evidence_type="EVID_CERTIFICATE",
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        EvidenceService.reject_evidence(doc.pk, self.committee_user, reason="Invalid issuer")
        doc.refresh_from_db()
        scoring_doc = EvidenceService.to_scoring_domain(doc)
        status, multiplier, trace = evaluate_evidence(
            mandatory_evidence_types=["EVID_CERTIFICATE"],
            uploaded_docs=[scoring_doc]
        )
        claimed_score = 10.0
        earned_score = claimed_score * multiplier
        self.assertEqual(status, GatingStatus.FAILED_EVIDENCE_REJECTED)
        self.assertEqual(earned_score, 0.0)

    def test_gating_verified_unlocks_earned_score(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="cert.pdf",
            file_bytes=self.sample_bytes,
            evidence_type="EVID_CERTIFICATE",
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        EvidenceService.verify_evidence(doc.pk, self.committee_user, reason="Authentic and verified")
        doc.refresh_from_db()
        scoring_doc = EvidenceService.to_scoring_domain(doc)
        status, multiplier, trace = evaluate_evidence(
            mandatory_evidence_types=["EVID_CERTIFICATE"],
            uploaded_docs=[scoring_doc]
        )
        claimed_score = 10.0
        earned_score = claimed_score * multiplier
        self.assertEqual(status, GatingStatus.PASSED_EVIDENCE_VERIFIED)
        self.assertEqual(earned_score, 10.0)


class TestFrameworkIsolation(EvidenceDomainTestCase):
    """
    Category J: Strict framework isolation.
    """
    def test_university_evidence_cannot_attach_to_college_param(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            original_filename="univ_doc.pdf",
            file_bytes=self.sample_bytes,
        )
        with self.assertRaises(FrameworkMismatchError):
            EvidenceService.associate_subcriterion(
                evidence_id=doc.pk,
                parameter_id="C1",
                subcriterion_id="C1.1",
                actor=self.principal_user,
            )

    def test_college_evidence_cannot_attach_to_university_param(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="college_doc.pdf",
            file_bytes=self.sample_bytes,
        )
        with self.assertRaises(FrameworkMismatchError):
            EvidenceService.associate_subcriterion(
                evidence_id=doc.pk,
                parameter_id="U4",
                subcriterion_id="U4.1",
                actor=self.principal_user,
            )


class TestAuthorization(EvidenceDomainTestCase):
    """
    Category K: Server-side role authorization & segregation of duties.
    """
    def test_principal_cannot_verify_evidence(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="test.pdf",
            file_bytes=self.sample_bytes,
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceService.verify_evidence(doc.pk, self.principal_user, reason="Self-approving")

    def test_segregation_of_duties_uploader_cannot_verify_own_evidence(self):
        doc = EvidenceService.create_evidence(
            uploader=self.admin_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            original_filename="admin_upload.pdf",
            file_bytes=self.sample_bytes,
        )
        EvidenceService.submit_for_verification(doc.pk, self.admin_user)
        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceService.verify_evidence(doc.pk, self.admin_user, reason="Self approval blocked")


class TestAuditTrail(EvidenceDomainTestCase):
    """
    Category L: Full lifecycle append-only audit trail.
    """
    def test_complete_lifecycle_audit_logged(self):
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-1001",
            original_filename="audit_test.pdf",
            file_bytes=self.sample_bytes,
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        EvidenceService.verify_evidence(doc.pk, self.committee_user, reason="Fully verified")
        EvidenceService.withdraw_evidence(doc.pk, self.principal_user, reason="Withdrawn by institution")

        actions = list(EvidenceAuditLog.objects.filter(evidence=doc).order_by('timestamp').values_list('action', flat=True))
        self.assertEqual(
            actions,
            [
                EvidenceAuditAction.UPLOADED,
                EvidenceAuditAction.SUBMITTED,
                EvidenceAuditAction.VERIFIED,
                EvidenceAuditAction.WITHDRAWN,
            ]
        )
