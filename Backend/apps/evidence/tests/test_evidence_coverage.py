"""
NEP Excellence Awards 2026 - Phase 5D Evidence Coverage & Assessment Period Test Suite
Verifies assessment period enforcement, coverage states, multiple evidence coexistence,
framework isolation, association integrity, duplicate detection, and scoring readiness.
"""
from datetime import date, timedelta
from django.test import TestCase

from apps.authentication.models import College, User
from apps.evidence.enums import (
    CoverageDeficiencyCode,
    CoverageState,
    EvidenceAuditAction,
    EvidenceLifecycleState,
    RejectionReasonCode,
)
from apps.evidence.exceptions import (
    FrameworkMismatchError,
    UnauthorizedEvidenceActionError,
)
from apps.evidence.models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.evidence.period_validator import AssessmentPeriodValidator
from apps.evidence.services import EvidenceService
from apps.scoring.enums import FrameworkType


class EvidenceCoverageTestCase(TestCase):
    """
    Base test fixture providing institutional users, colleges, and reviewer fixtures.
    """
    def setUp(self):
        super().setUp()
        self.college1 = College.objects.create(name="Govt College Karnal", aishe_code="C-4001")
        self.college2 = College.objects.create(name="Govt College Kurukshetra", aishe_code="C-4002")

        # Users
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
        self.committee_reviewer = User.objects.create_user(
            email="reviewer.dhe@haryana.gov.in",
            full_name="Committee Reviewer",
            role="committee",
            password="securepassword123"
        )
        self.admin_user = User.objects.create_user(
            email="admin@dhe.haryana.gov.in",
            full_name="State Administrator",
            role="state_admin",
            password="securepassword123"
        )

        # Authorize reviewer for COLLEGE_2026
        EvidenceService.authorize_reviewer(
            self.committee_reviewer,
            framework="COLLEGE_2026",
            granted_by=self.admin_user
        )

    def create_doc(
        self,
        assessment_id="ASSESS-COLLEGE-2026-01",
        framework="COLLEGE_2026",
        institution_id="C-4001",
        evidence_type="EVID_GENERAL",
        document_date=None,
        status=EvidenceLifecycleState.EVIDENCE_PENDING,
        uploader=None,
        parameter_id="C1",
        subcriterion_id="C1.1",
        associate=True,
        metadata=None,
    ) -> EvidenceDocument:
        """Helper to create and optionally associate an evidence document."""
        uploader = uploader or self.principal_karnal
        file_bytes = b"%PDF-1.4 Mock Evidence Content for Coverage Testing"
        checksum = EvidenceService.calculate_checksum(file_bytes)

        doc = EvidenceDocument.objects.create(
            assessment_id=assessment_id,
            framework=framework,
            institution_type="COLLEGE",
            institution_id=institution_id,
            original_filename="coverage_proof.pdf",
            file_path="mock/path/coverage_proof.pdf",
            mime_type="application/pdf",
            file_size=len(file_bytes),
            file_checksum=checksum,
            uploader=uploader,
            evidence_type=evidence_type,
            document_date=document_date,
            academic_year="2025-26",
            status=status,
            metadata=metadata or {},
            is_active=True,
        )

        if associate and parameter_id and subcriterion_id:
            EvidenceSubcriterionAssociation.objects.create(
                evidence=doc,
                parameter_id=parameter_id,
                subcriterion_id=subcriterion_id,
                associated_by=uploader,
            )

        return doc


class TestCategoryAAssessmentPeriod(EvidenceCoverageTestCase):
    """
    Category A: Assessment Period Boundaries & Validation.
    Authoritative window: 2025-07-01 to 2026-06-30 inclusive.
    """
    def test_start_boundary_accepted(self):
        start_date = date(2025, 7, 1)
        valid, reason, code = AssessmentPeriodValidator.validate_activity_date(start_date)
        self.assertTrue(valid)
        self.assertIsNone(reason)
        self.assertIsNone(code)

    def test_end_boundary_accepted(self):
        end_date = date(2026, 6, 30)
        valid, reason, code = AssessmentPeriodValidator.validate_activity_date(end_date)
        self.assertTrue(valid)
        self.assertIsNone(reason)
        self.assertIsNone(code)

    def test_prior_to_start_boundary_rejected(self):
        prior_date = date(2025, 6, 30)
        valid, reason, code = AssessmentPeriodValidator.validate_activity_date(prior_date)
        self.assertFalse(valid)
        self.assertIn("prior to assessment start", reason)
        self.assertEqual(code, CoverageDeficiencyCode.OUTSIDE_ASSESSMENT_PERIOD)

    def test_after_end_boundary_rejected(self):
        post_date = date(2026, 7, 1)
        valid, reason, code = AssessmentPeriodValidator.validate_activity_date(post_date)
        self.assertFalse(valid)
        self.assertIn("after assessment end", reason)
        self.assertEqual(code, CoverageDeficiencyCode.OUTSIDE_ASSESSMENT_PERIOD)

    def test_missing_required_date_fails_without_fallback_to_hoi_date(self):
        # Missing date on period-sensitive criterion must fail with PERIOD_DATA_MISSING
        doc = self.create_doc(
            document_date=None,
            metadata={"hoi_certification_date": "2025-09-01", "upload_date": "2025-09-02"}
        )
        valid, reason, code = AssessmentPeriodValidator.validate_document_period(doc, is_period_sensitive=True)
        self.assertFalse(valid)
        self.assertEqual(code, CoverageDeficiencyCode.PERIOD_DATA_MISSING)
        self.assertIn("missing for a period-sensitive criterion", reason)

    def test_period_insensitive_criterion_permits_none_date(self):
        # Period-insensitive criteria (like U1-U3, C3) do not require an activity date
        valid, reason, code = AssessmentPeriodValidator.validate_activity_date(None, is_period_sensitive=False)
        self.assertTrue(valid)
        self.assertIsNone(code)

    def test_invalid_date_range_rejected(self):
        start = date(2025, 11, 15)
        end = date(2025, 11, 10)  # end before start
        valid, reason, code = AssessmentPeriodValidator.validate_date_range(start, end)
        self.assertFalse(valid)
        self.assertEqual(code, CoverageDeficiencyCode.INVALID_DATE_RANGE)
        self.assertIn("start date 2025-11-15 cannot be after end date 2025-11-10", reason)

    def test_valid_date_range_accepted(self):
        start = date(2025, 8, 1)
        end = date(2025, 8, 15)
        valid, reason, code = AssessmentPeriodValidator.validate_date_range(start, end)
        self.assertTrue(valid)
        self.assertIsNone(code)


class TestCategoryBCoverageStates(EvidenceCoverageTestCase):
    """
    Category B: Representation and determination of CoverageState.
    """
    def test_no_evidence_state(self):
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-EMPTY",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertEqual(sub.coverage_state, CoverageState.NO_EVIDENCE)
        self.assertEqual(sub.evidence_count, 0)
        self.assertIn(CoverageDeficiencyCode.NO_ASSOCIATED_EVIDENCE.value, sub.deficiency_codes)

    def test_evidence_present_state(self):
        # PRESENT (unsubmitted)
        self.create_doc(
            assessment_id="ASSESS-PRESENT",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 15),
            status=EvidenceLifecycleState.EVIDENCE_PRESENT
        )
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-PRESENT",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertEqual(sub.coverage_state, CoverageState.EVIDENCE_PRESENT)
        self.assertIn(CoverageDeficiencyCode.UNVERIFIED_EVIDENCE.value, sub.deficiency_codes)

    def test_evidence_pending_state(self):
        self.create_doc(
            assessment_id="ASSESS-PENDING",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 15),
            status=EvidenceLifecycleState.EVIDENCE_PENDING
        )
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-PENDING",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertEqual(sub.coverage_state, CoverageState.EVIDENCE_PENDING)
        self.assertEqual(sub.pending_count, 1)
        self.assertIn(CoverageDeficiencyCode.VERIFICATION_PENDING.value, sub.deficiency_codes)

    def test_evidence_verified_state(self):
        self.create_doc(
            assessment_id="ASSESS-VERIFIED",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 15),
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-VERIFIED",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertEqual(sub.coverage_state, CoverageState.EVIDENCE_VERIFIED)
        self.assertEqual(sub.verified_count, 1)
        self.assertEqual(sub.period_valid_count, 1)
        self.assertEqual(len(sub.blocking_reasons), 0)

    def test_evidence_rejected_state(self):
        self.create_doc(
            assessment_id="ASSESS-REJECTED",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 15),
            status=EvidenceLifecycleState.EVIDENCE_REJECTED
        )
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-REJECTED",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertEqual(sub.coverage_state, CoverageState.EVIDENCE_REJECTED)
        self.assertEqual(sub.rejected_count, 1)
        self.assertIn(CoverageDeficiencyCode.EVIDENCE_REJECTED.value, sub.deficiency_codes)

    def test_evidence_invalid_period_state(self):
        # Document verified but out of period on period-sensitive criterion C1
        self.create_doc(
            assessment_id="ASSESS-OUT-OF-PERIOD",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2024, 12, 1),  # outside 2025-07-01 to 2026-06-30
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-OUT-OF-PERIOD",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertEqual(sub.coverage_state, CoverageState.EVIDENCE_INVALID_PERIOD)
        self.assertEqual(sub.period_invalid_count, 1)
        self.assertIn(CoverageDeficiencyCode.OUTSIDE_ASSESSMENT_PERIOD.value, sub.deficiency_codes)


class TestCategoryCMultipleEvidenceDocuments(EvidenceCoverageTestCase):
    """
    Category C: Coexistence of multiple documents and duplicate detection.
    """
    def test_verified_and_rejected_evidence_on_same_subcriterion(self):
        # Doc 1 is rejected, Doc 2 is verified and valid
        doc_rejected = self.create_doc(
            assessment_id="ASSESS-MULTI-01",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 8, 1),
            status=EvidenceLifecycleState.EVIDENCE_REJECTED
        )
        doc_verified = self.create_doc(
            assessment_id="ASSESS-MULTI-01",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 1),
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-MULTI-01",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        # Verified document preserves scoring eligibility: state must be EVIDENCE_VERIFIED!
        self.assertEqual(sub.coverage_state, CoverageState.EVIDENCE_VERIFIED)
        self.assertEqual(sub.evidence_count, 2)
        self.assertEqual(sub.verified_count, 1)
        self.assertEqual(sub.rejected_count, 1)

    def test_pending_and_verified_evidence_on_same_subcriterion(self):
        # Doc 1 is verified, Doc 2 is newly uploaded pending review
        self.create_doc(
            assessment_id="ASSESS-MULTI-02",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 8, 1),
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )
        self.create_doc(
            assessment_id="ASSESS-MULTI-02",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 1),
            status=EvidenceLifecycleState.EVIDENCE_PENDING
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-MULTI-02",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        # Verified document exists -> subcriterion achieves verified state
        self.assertEqual(sub.coverage_state, CoverageState.EVIDENCE_VERIFIED)
        self.assertEqual(sub.verified_count, 1)
        self.assertEqual(sub.pending_count, 1)

    def test_multiple_verified_documents(self):
        self.create_doc(
            assessment_id="ASSESS-MULTI-03",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 8, 1),
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )
        self.create_doc(
            assessment_id="ASSESS-MULTI-03",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 1),
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-MULTI-03",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertEqual(sub.coverage_state, CoverageState.EVIDENCE_VERIFIED)
        self.assertEqual(sub.evidence_count, 2)
        self.assertEqual(sub.verified_count, 2)

    def test_duplicate_evidence_reference_surfaced_in_report(self):
        # Associate single document with both C4.A and C4.B
        doc = self.create_doc(
            assessment_id="ASSESS-DUP",
            parameter_id="C4",
            subcriterion_id="C4.A",
            document_date=date(2025, 10, 1),
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED,
            associate=True
        )
        # Add second association to C4.B
        EvidenceSubcriterionAssociation.objects.create(
            evidence=doc,
            parameter_id="C4",
            subcriterion_id="C4.B",
            associated_by=self.principal_karnal
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-DUP",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C4.A", "C4.B"]
        )
        # Duplicate detection must be surfaced in report
        self.assertGreaterEqual(len(report.duplicates_detected), 1)
        dup_entry = report.duplicates_detected[0]
        self.assertEqual(dup_entry["document_id"], str(doc.document_id))
        self.assertEqual(len(dup_entry["associations"]), 2)


class TestCategoryDFrameworkIsolation(EvidenceCoverageTestCase):
    """
    Category D: Framework isolation. University vs College boundary.
    """
    def test_university_evidence_cannot_satisfy_college_coverage(self):
        # Upload doc under UNIVERSITY_2026
        doc = self.create_doc(
            assessment_id="ASSESS-MISMATCH",
            framework="UNIVERSITY_2026",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 1),
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-MISMATCH",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        # Framework mismatch flags deficiency and blocks verified status
        self.assertIn(CoverageDeficiencyCode.FRAMEWORK_MISMATCH.value, sub.deficiency_codes)
        self.assertNotEqual(sub.coverage_state, CoverageState.EVIDENCE_VERIFIED)

    def test_college_evidence_cannot_satisfy_university_coverage(self):
        # Upload doc under COLLEGE_2026
        doc = self.create_doc(
            assessment_id="ASSESS-UNIV",
            framework="COLLEGE_2026",
            parameter_id="U1",
            subcriterion_id="U1.1",
            document_date=date(2025, 9, 1),
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-UNIV",
            framework="UNIVERSITY_2026",
            institution_id="C-4001",
            subcriterion_codes=["U1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertIn(CoverageDeficiencyCode.FRAMEWORK_MISMATCH.value, sub.deficiency_codes)
        self.assertNotEqual(sub.coverage_state, CoverageState.EVIDENCE_VERIFIED)


class TestCategoryEAssociationIntegrity(EvidenceCoverageTestCase):
    """
    Category E: Association verification and active status integrity.
    """
    def test_unassociated_evidence_does_not_satisfy_subcriterion(self):
        # Document uploaded with associate=False
        doc = self.create_doc(
            assessment_id="ASSESS-UNASSOC",
            parameter_id=None,
            subcriterion_id=None,
            associate=False,
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-UNASSOC",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertEqual(sub.coverage_state, CoverageState.NO_EVIDENCE)
        self.assertEqual(sub.evidence_count, 0)

    def test_superseded_evidence_association_is_invalidated(self):
        doc_v1 = self.create_doc(
            assessment_id="ASSESS-SUPERSEDED",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 1),
            status=EvidenceLifecycleState.EVIDENCE_SUPERSEDED
        )
        doc_v1.is_active = False
        doc_v1.save()

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-SUPERSEDED",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        sub = report.parameters[0].subcriteria[0]
        # Inactive superseded document does not count as active coverage
        self.assertEqual(sub.evidence_count, 0)
        self.assertEqual(sub.coverage_state, CoverageState.NO_EVIDENCE)


class TestCategoryFEvidenceReadiness(EvidenceCoverageTestCase):
    """
    Category F: is_assessment_evidence_ready evaluation.
    """
    def test_missing_evidence_is_not_ready(self):
        is_ready, blocking, summary = EvidenceService.is_assessment_evidence_ready(
            assessment_id="ASSESS-NOT-READY",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        self.assertFalse(is_ready)
        self.assertGreater(len(blocking), 0)
        self.assertIn("No associated evidence", blocking[0])

    def test_pending_evidence_is_not_ready(self):
        self.create_doc(
            assessment_id="ASSESS-PENDING-READY",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 1),
            status=EvidenceLifecycleState.EVIDENCE_PENDING
        )
        is_ready, blocking, summary = EvidenceService.is_assessment_evidence_ready(
            assessment_id="ASSESS-PENDING-READY",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        self.assertFalse(is_ready)
        self.assertGreater(len(blocking), 0)
        self.assertIn("pending verification", blocking[0])

    def test_rejected_only_evidence_is_not_ready(self):
        self.create_doc(
            assessment_id="ASSESS-REJECT-READY",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 1),
            status=EvidenceLifecycleState.EVIDENCE_REJECTED
        )
        is_ready, blocking, summary = EvidenceService.is_assessment_evidence_ready(
            assessment_id="ASSESS-REJECT-READY",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        self.assertFalse(is_ready)
        self.assertGreater(len(blocking), 0)
        self.assertIn("rejected", blocking[0])

    def test_invalid_period_evidence_is_not_ready(self):
        self.create_doc(
            assessment_id="ASSESS-PERIOD-READY",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2024, 6, 1),  # out of period
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )
        is_ready, blocking, summary = EvidenceService.is_assessment_evidence_ready(
            assessment_id="ASSESS-PERIOD-READY",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        self.assertFalse(is_ready)
        self.assertGreater(len(blocking), 0)
        self.assertIn("assessment period", blocking[0])

    def test_verified_valid_evidence_is_ready(self):
        self.create_doc(
            assessment_id="ASSESS-READY",
            parameter_id="C1",
            subcriterion_id="C1.1",
            document_date=date(2025, 9, 15),
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED
        )
        is_ready, blocking, summary = EvidenceService.is_assessment_evidence_ready(
            assessment_id="ASSESS-READY",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"]
        )
        self.assertTrue(is_ready)
        self.assertEqual(len(blocking), 0)
        self.assertEqual(summary.verified_subcriteria, 1)

    def test_authorization_prevents_principal_accessing_other_institution(self):
        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceService.evaluate_evidence_coverage(
                assessment_id="ASSESS-OTHER",
                framework="COLLEGE_2026",
                institution_id="C-4002",  # College 2
                requesting_user=self.principal_karnal,  # from College 1
                subcriterion_codes=["C1.1"]
            )
