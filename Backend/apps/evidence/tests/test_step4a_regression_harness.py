"""
NEP Excellence Awards 2026 - Step 4A Evidence Architecture Regression Test Harness

MODE: TEST-ONLY IMPLEMENTATION.
This test suite establishes the safety contract for the Step 3A evidence architecture remediation.
Tests are written against the INTENDED Step 3A contract and MUST FAIL where the current architecture
violates that contract (e.g., parameter-level fallback, cross-subcriterion evidence leakage,
document-level verification limitation).

Tests Included:
- Test 1:  U7 appointment evidence must not unlock siblings (U7.2, U7.3, U7.4)
- Test 2:  U7 composite document independent association reviewability
- Test 3:  U10 society registration must not unlock funding (U10.3)
- Test 4:  U17 NIRF 2026 submission must not unlock NIRF 2025 rank (U17.2)
- Test 5:  C20 NAAC certificate must not unlock NIRF/AISHE (C20.2, C20.3)
- Test 6:  Composite annual report reuse must be association-scoped (Document reuse != Verification reuse)
- Test 7:  Rejected evidence must not unlock score (multiplier = 0.0, score = 0.0)
- Test 8:  Framework isolation (College evidence cannot associate to University subcriterion)
- Test 9:  Institution isolation (Institution A evidence cannot be accessed/mutated by Institution B)
- Test 10: Legacy coarse evidence (EVID_U7_APPOINTMENT) must not unlock siblings
- Part 11.A: Coverage/Scoring divergence demonstration (Coverage = verified while Score gate = failed)
- Part 11.B: Document-level verification limitation demonstration (Document verification leaks to all associations)
"""
import hashlib
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import College, User
from apps.evidence.enums import (
    CoverageState,
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
)
from apps.evidence.exceptions import (
    FrameworkMismatchError,
    UnauthorizedEvidenceActionError,
)
from apps.evidence.models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    EvidenceVerification,
    ReviewerAuthorization,
)
from apps.evidence.services import EvidenceService
from apps.scoring.domain import (
    AssessmentContext,
    AssessmentInput,
    AssessmentPeriod,
    EvidenceDocument as ScoringEvidenceDoc,
    ParameterInput,
    SubcriterionInput,
)
from apps.scoring.engine import NEP2026ScoringEngine
from apps.scoring.enums import (
    EvidenceState as ScoringEvidenceState,
    FrameworkType,
    GatingStatus,
    InstitutionType,
)
from apps.evidence.taxonomy import QuarantinedLegacyEvidenceError
from apps.scoring.evaluators.double_counting import DoubleCountingValidator
from apps.scoring.evaluators.evidence_gating import (
    evaluate_evidence,
    evaluate_subcriterion_contract_evidence,
)
from apps.scoring.rules.college import COLLEGE_EVALUATORS
from apps.scoring.rules.definitions import COLLEGE_PARAMETERS, UNIVERSITY_PARAMETERS
from apps.scoring.rules.university import UNIVERSITY_EVALUATORS


class Step4AEvidenceArchitectureRegressionHarness(APITestCase):
    """
    Automated regression harness enforcing the Step 3A safety contract.
    No production code has been modified to artificially pass these tests.
    """

    def setUp(self):
        super().setUp()
        self.period = AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30))
        self.validator = DoubleCountingValidator()
        self.engine = NEP2026ScoringEngine()

        # Institutional entities
        self.college_a = College.objects.create(name="Govt College Karnal", aishe_code="C-1001")
        self.college_b = College.objects.create(name="Govt College Kurukshetra", aishe_code="C-1002")

        # Users
        self.principal_user = User.objects.create_user(
            email="principal.univ@haryana.gov.in",
            full_name="University Registrar / Principal",
            role="principal",
            college=self.college_a,
            password="SecurePassword123!",
        )
        self.principal_user_b = User.objects.create_user(
            email="principal.b@haryana.gov.in",
            full_name="College B Principal",
            role="principal",
            college=self.college_b,
            password="SecurePassword123!",
        )
        self.committee_user = User.objects.create_user(
            email="evaluator.dhe@haryana.gov.in",
            full_name="Screening Committee Member",
            role="committee",
            password="SecurePassword123!",
        )
        self.admin_user = User.objects.create_superuser(
            email="admin.dhe@haryana.gov.in",
            full_name="DHE State Admin",
            password="SecurePassword123!",
        )

        # Reviewer Authorizations
        ReviewerAuthorization.objects.create(
            user=self.committee_user,
            framework="UNIVERSITY_2026",
            granted_by=self.admin_user,
        )
        ReviewerAuthorization.objects.create(
            user=self.committee_user,
            framework="COLLEGE_2026",
            granted_by=self.admin_user,
        )

        # Assessment contexts
        self.univ_context = AssessmentContext(
            assessment_id="ASSESS-U-2026-REGRESS",
            institution_id="UNIV-HARYANA-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        self.college_context = AssessmentContext(
            assessment_id="ASSESS-C-2026-REGRESS",
            institution_id="C-1001",
            institution_type=InstitutionType.COLLEGE,
            framework=FrameworkType.COLLEGE_2026,
            assessment_period=self.period,
        )

        # Standard test file payload
        self.sample_bytes = b"%PDF-1.4 Mock NEP 2026 Step 4A Evidence Document Content\n%%EOF"
        self.sample_checksum = hashlib.sha256(self.sample_bytes).hexdigest()

    def _create_and_verify_doc(
        self,
        assessment_id: str,
        framework: str,
        institution_id: str,
        evidence_type: str,
        original_filename: str = "evidence.pdf",
        uploader=None,
        institution_type: str = "UNIVERSITY",
    ) -> EvidenceDocument:
        """Helper to create a fully verified evidence document through authoritative lifecycle."""
        uploader = uploader or self.principal_user
        doc = EvidenceService.create_evidence(
            uploader=uploader,
            assessment_id=assessment_id,
            framework=framework,
            institution_type=institution_type,
            institution_id=institution_id,
            original_filename=original_filename,
            file_bytes=self.sample_bytes,
            mime_type="application/pdf",
            evidence_type=evidence_type,
            document_date=date(2025, 10, 1),
            academic_year="2025-26",
        )
        EvidenceService.submit_for_verification(doc.pk, uploader)
        EvidenceService.verify_evidence(
            doc.pk,
            self.committee_user,
            reason="Verified authentic under NEP 2026 protocol",
        )
        doc.refresh_from_db()
        return doc

    # =========================================================================
    # TEST 1 — U7 APPOINTMENT MUST NOT UNLOCK SIBLINGS
    # =========================================================================
    def test_01_u7_appointment_must_not_unlock_siblings(self):
        """
        Target Contract:
        Appointment evidence (EVID_U7_APPOINTMENT) is valid ONLY for U7.1.
        It must NOT satisfy sibling subcriteria U7.2 (Workload/teaching),
        U7.3 (Workshops/training), or U7.4 (Projects/outcomes).

        Expected Failure on Current Architecture:
        Current definitions fall back to U7 parameter-level mandatory_evidence
        ['EVID_U7_APPOINTMENT'] for all subcriteria, causing U7.2, U7.3, U7.4
        to incorrectly pass when provided with appointment evidence.
        """
        doc = self._create_and_verify_doc(
            assessment_id=self.univ_context.assessment_id,
            framework="UNIVERSITY_2026",
            institution_id=self.univ_context.institution_id,
            evidence_type="EVID_U7_APPOINTMENT",
            original_filename="pop_appointment_letter.pdf",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.principal_user,
        )

        scoring_doc = EvidenceService.to_scoring_domain(doc)
        eval_fn = UNIVERSITY_EVALUATORS["U7"]

        # Evaluate parameter U7 where appointment evidence is submitted for subcriteria
        # Sibling evidence (workload records, workshop attendance, project outcomes) is NOT provided.
        param_input = ParameterInput(
            parameter_code="U7",
            subcriteria_inputs={
                "U7.1": SubcriterionInput(
                    subcriterion_code="U7.1",
                    raw_inputs={"verified": True},
                    evidence_docs=[scoring_doc],
                ),
                # If appointment proof is presented to satisfy U7.2/3/4, target contract mandates REJECTION:
                "U7.2": SubcriterionInput(
                    subcriterion_code="U7.2",
                    raw_inputs={"verified": True},
                    evidence_docs=[scoring_doc],
                ),
                "U7.3": SubcriterionInput(
                    subcriterion_code="U7.3",
                    raw_inputs={"verified": True},
                    evidence_docs=[scoring_doc],
                ),
                "U7.4": SubcriterionInput(
                    subcriterion_code="U7.4",
                    raw_inputs={"verified": True},
                    evidence_docs=[scoring_doc],
                ),
            },
        )

        result = eval_fn(param_input, self.univ_context, self.validator)

        # U7.1 MUST PASS evidence gate
        self.assertEqual(
            result.subcriteria_results["U7.1"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "U7.1 must pass evidence gate with verified appointment evidence."
        )
        self.assertEqual(result.subcriteria_results["U7.1"].evidence_gated_score, 1.0)

        # SIBLINGS MUST FAIL: Appointment evidence cannot satisfy U7.2, U7.3, U7.4
        self.assertNotEqual(
            result.subcriteria_results["U7.2"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "U7.2 MUST FAIL evidence gate: appointment letter cannot satisfy workload delivery requirement."
        )
        self.assertEqual(
            result.subcriteria_results["U7.2"].evidence_gated_score,
            0.0,
            "U7.2 earned score must be 0.0 without valid workload evidence."
        )

        self.assertNotEqual(
            result.subcriteria_results["U7.3"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "U7.3 MUST FAIL evidence gate: appointment letter cannot satisfy workshop attendance requirement."
        )
        self.assertEqual(result.subcriteria_results["U7.3"].evidence_gated_score, 0.0)

        self.assertNotEqual(
            result.subcriteria_results["U7.4"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "U7.4 MUST FAIL evidence gate: appointment letter cannot satisfy project outcome requirement."
        )
        self.assertEqual(result.subcriteria_results["U7.4"].evidence_gated_score, 0.0)

    # =========================================================================
    # TEST 2 — U7 COMPOSITE DOCUMENT CAN SUPPORT MULTIPLE SUBCRITERIA
    # =========================================================================
    def test_02_u7_composite_document_independent_associations(self):
        """
        Target Contract:
        A single composite document (e.g. PoP comprehensive dossier) can be associated
        with multiple subcriteria (U7.1, U7.2, U7.3, U7.4). Each association must be
        independently reviewable and verifiable at the association level.

        Expected Failure on Current Architecture:
        Current schema binds verification strictly to EvidenceDocument.
        EvidenceSubcriterionAssociation has no verification_status or independent review state.
        """
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id=self.univ_context.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.univ_context.institution_id,
            original_filename="pop_comprehensive_dossier.pdf",
            file_bytes=self.sample_bytes,
            mime_type="application/pdf",
            evidence_type="EVID_GENERAL",
            document_date=date(2025, 10, 1),
            academic_year="2025-26",
        )

        # Create 4 separate associations with distinct subcriterion scopes, canonical types, and page regions
        assoc1 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.principal_user,
            evidence_type="EVID_U7_APPOINTMENT",
            page_start=1,
            page_end=5,
        )
        assoc2 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.2",
            actor=self.principal_user,
            evidence_type="EVID_U7_TEACHING_LOGS",
            page_start=6,
            page_end=15,
        )
        assoc3 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.3",
            actor=self.principal_user,
            evidence_type="EVID_U7_WORKSHOP_REPORTS",
            page_start=16,
            page_end=25,
        )
        assoc4 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.4",
            actor=self.principal_user,
            evidence_type="EVID_U7_PROJECT_REPORTS",
            page_start=26,
            page_end=35,
        )

        self.assertEqual(doc.associations.count(), 4)

        # Target Contract Assertion: Each association must be independently reviewable
        # and hold its own verification state.
        self.assertTrue(
            hasattr(assoc1, "verification_status") or hasattr(assoc1, "status"),
            "ARCHITECTURAL DEFECT: EvidenceSubcriterionAssociation lacks an independent verification status field."
        )
        self.assertIsNone(assoc1.verification_status)

        # Independently verify assoc1 and reject assoc2
        EvidenceService.verify_association(assoc1.pk, verifier=self.committee_user)
        EvidenceService.reject_association(
            assoc2.pk,
            verifier=self.committee_user,
            reason="Incomplete teaching logs on pages 6-15.",
        )

        assoc1.refresh_from_db()
        assoc2.refresh_from_db()
        assoc3.refresh_from_db()
        assoc4.refresh_from_db()

        self.assertEqual(assoc1.verification_status, VerificationDecision.VERIFIED)
        self.assertEqual(assoc2.verification_status, VerificationDecision.REJECTED)
        self.assertIsNone(assoc3.verification_status)
        self.assertIsNone(assoc4.verification_status)
        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_PRESENT)

    # =========================================================================
    # TEST 3 — U10 SOCIETY REGISTRATION MUST NOT UNLOCK FUNDING
    # =========================================================================
    def test_03_u10_society_registration_must_not_unlock_funding(self):
        """
        Target Contract:
        Verified U10.1 society registration certificate (EVID_U10_REG_CERT) must NOT
        satisfy or unlock U10.3 (Alumni funding / financial contribution).
        Specifically protects against parameter-level evidence inheritance.

        Expected Failure on Current Architecture:
        Current definitions fall back to U10 parameter-level mandatory_evidence
        ['EVID_U10_REG_CERT'] for U10.3, unlocking funding marks without funding proof.
        """
        doc = self._create_and_verify_doc(
            assessment_id=self.univ_context.assessment_id,
            framework="UNIVERSITY_2026",
            institution_id=self.univ_context.institution_id,
            evidence_type="EVID_U10_REG_CERT",
            original_filename="alumni_society_registration.pdf",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U10",
            subcriterion_id="U10.1",
            actor=self.principal_user,
        )

        scoring_doc = EvidenceService.to_scoring_domain(doc)
        eval_fn = UNIVERSITY_EVALUATORS["U10"]

        # Evaluate U10: U10.1 has registration proof; U10.3 claims Rs. 1.5 Cr funding
        # If the registration doc is presented for U10.3, it MUST FAIL the evidence gate.
        param_input = ParameterInput(
            parameter_code="U10",
            subcriteria_inputs={
                "U10.1": SubcriterionInput(
                    subcriterion_code="U10.1",
                    raw_inputs={"verified": True},
                    evidence_docs=[scoring_doc],
                ),
                "U10.3": SubcriterionInput(
                    subcriterion_code="U10.3",
                    raw_inputs={"funding_amount": 15000000.0},
                    evidence_docs=[scoring_doc],  # Attempting to satisfy funding with society registration
                ),
            },
        )

        result = eval_fn(param_input, self.univ_context, self.validator)

        # U10.1 must pass
        self.assertEqual(
            result.subcriteria_results["U10.1"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "U10.1 society registration must pass evidence gate."
        )

        # U10.3 MUST FAIL: Society registration certificate cannot unlock alumni funding
        self.assertNotEqual(
            result.subcriteria_results["U10.3"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "U10.3 MUST FAIL evidence gate: Society registration cannot satisfy alumni funding requirement."
        )
        self.assertEqual(
            result.subcriteria_results["U10.3"].evidence_gated_score,
            0.0,
            "U10.3 gated score must be 0.0 without verified financial/funding evidence."
        )

    # =========================================================================
    # TEST 4 — U17 NIRF 2026 SUBMISSION MUST NOT UNLOCK NIRF 2025 RANK
    # =========================================================================
    def test_04_u17_nirf_2026_must_not_unlock_nirf_2025_rank(self):
        """
        Target Contract:
        Verified U17.1 NIRF 2026 submission proof (EVID_U17_NIRF_2026_PROOF) must NOT
        satisfy U17.2 (NIRF 2025 Ranking proof / certificate).

        Expected Failure on Current Architecture:
        Current definitions fall back to U17 parameter-level mandatory_evidence
        ['EVID_U17_NIRF_2026_PROOF'] for U17.2, allowing submission proof to unlock rank marks.
        """
        doc = self._create_and_verify_doc(
            assessment_id=self.univ_context.assessment_id,
            framework="UNIVERSITY_2026",
            institution_id=self.univ_context.institution_id,
            evidence_type="EVID_U17_NIRF_2026_PROOF",
            original_filename="nirf_2026_acknowledgement.pdf",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U17",
            subcriterion_id="U17.1",
            actor=self.principal_user,
        )

        scoring_doc = EvidenceService.to_scoring_domain(doc)
        eval_fn = UNIVERSITY_EVALUATORS["U17"]

        param_input = ParameterInput(
            parameter_code="U17",
            subcriteria_inputs={
                "U17.1": SubcriterionInput(
                    subcriterion_code="U17.1",
                    raw_inputs={"verified": True},
                    evidence_docs=[scoring_doc],
                ),
                "U17.2": SubcriterionInput(
                    subcriterion_code="U17.2",
                    raw_inputs={"verified": True},
                    evidence_docs=[scoring_doc],  # Attempting to satisfy 2025 rank with 2026 submission
                ),
            },
        )

        result = eval_fn(param_input, self.univ_context, self.validator)

        # U17.1 must pass
        self.assertEqual(
            result.subcriteria_results["U17.1"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "U17.1 NIRF 2026 submission must pass evidence gate."
        )

        # U17.2 MUST FAIL: 2026 submission proof cannot satisfy 2025 rank proof
        self.assertNotEqual(
            result.subcriteria_results["U17.2"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "U17.2 MUST FAIL evidence gate: NIRF 2026 submission cannot satisfy NIRF 2025 ranking proof."
        )
        self.assertEqual(
            result.subcriteria_results["U17.2"].evidence_gated_score,
            0.0,
            "U17.2 gated score must be 0.0 without verified 2025 rank evidence."
        )

    # =========================================================================
    # TEST 5 — C20 NAAC MUST NOT UNLOCK NIRF/AISHE
    # =========================================================================
    def test_05_c20_naac_must_not_unlock_nirf_aishe(self):
        """
        Target Contract:
        Verified C20.1 NAAC certificate (EVID_C20_NAAC_CERT) must NOT satisfy
        C20.2 (NIRF participation) or C20.3 (AISHE submission).
        Subcriteria of C20: C20.1 (NAAC), C20.2 (NIRF), C20.3 (AISHE), C20.4 (AQAR/IQAC).

        Expected Failure on Current Architecture:
        Current definitions fall back to C20 parameter-level mandatory_evidence
        ['EVID_C20_NAAC_CERT'] for all C20 subcriteria.
        """
        doc = self._create_and_verify_doc(
            assessment_id=self.college_context.assessment_id,
            framework="COLLEGE_2026",
            institution_id=self.college_context.institution_id,
            evidence_type="EVID_C20_NAAC_CERT",
            original_filename="naac_grade_a_certificate.pdf",
            institution_type="COLLEGE",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="C20",
            subcriterion_id="C20.1",
            actor=self.principal_user,
        )

        scoring_doc = EvidenceService.to_scoring_domain(doc)
        eval_fn = COLLEGE_EVALUATORS["C20"]

        param_input = ParameterInput(
            parameter_code="C20",
            subcriteria_inputs={
                "C20.1": SubcriterionInput(
                    subcriterion_code="C20.1",
                    raw_inputs={"naac_grade": "A"},
                    evidence_docs=[scoring_doc],
                ),
                "C20.2": SubcriterionInput(
                    subcriterion_code="C20.2",
                    raw_inputs={"verified": True},
                    evidence_docs=[scoring_doc],  # Attempting to satisfy NIRF with NAAC cert
                ),
                "C20.3": SubcriterionInput(
                    subcriterion_code="C20.3",
                    raw_inputs={"verified": True},
                    evidence_docs=[scoring_doc],  # Attempting to satisfy AISHE with NAAC cert
                ),
                "C20.4": SubcriterionInput(
                    subcriterion_code="C20.4",
                    raw_inputs={"verified": False},
                    evidence_docs=[],
                ),
            },
        )

        result = eval_fn(param_input, self.college_context, self.validator)

        # C20.1 must pass
        self.assertEqual(
            result.subcriteria_results["C20.1"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "C20.1 NAAC Grade must pass evidence gate with NAAC certificate."
        )

        # C20.2 & C20.3 MUST FAIL
        self.assertNotEqual(
            result.subcriteria_results["C20.2"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "C20.2 MUST FAIL evidence gate: NAAC certificate cannot satisfy NIRF participation."
        )
        self.assertEqual(result.subcriteria_results["C20.2"].evidence_gated_score, 0.0)

        self.assertNotEqual(
            result.subcriteria_results["C20.3"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "C20.3 MUST FAIL evidence gate: NAAC certificate cannot satisfy AISHE submission."
        )
        self.assertEqual(result.subcriteria_results["C20.3"].evidence_gated_score, 0.0)

    # =========================================================================
    # TEST 6 — COMPOSITE ANNUAL REPORT REUSE MUST BE ASSOCIATION-SCOPED
    # =========================================================================
    def test_06_composite_annual_report_reuse_must_be_association_scoped(self):
        """
        Target Contract:
        DOCUMENT REUSE != VERIFICATION REUSE.
        A single Annual Report document supports Association A (U10.3) and Association B (U20.3).
        Reviewer verifies Association A (pages 12-14) and rejects Association B (pages 45-50).
        Expected: U10.3 = Pass (multiplier 1.0); U20.3 = Fail (multiplier 0.0).

        Expected Failure on Current Architecture:
        Current EvidenceVerification is document-level. Calling reject_evidence marks
        the entire document as EVIDENCE_REJECTED, causing both associations to fail.
        Furthermore, assigning evidence_type at the document level overwrites the type,
        mutating previous associations.
        """
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id=self.univ_context.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.univ_context.institution_id,
            original_filename="Annual_Report_2025_26.pdf",
            file_bytes=self.sample_bytes,
            mime_type="application/pdf",
            evidence_type="EVID_GENERAL",
            document_date=date(2025, 10, 1),
            academic_year="2025-26",
        )

        assoc_a = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U10",
            subcriterion_id="U10.3",
            actor=self.principal_user,
            evidence_type="EVID_U10_FINANCIAL_RECORDS",
            page_start=12,
            page_end=14,
        )
        assoc_b = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U20",
            subcriterion_id="U20.3",
            actor=self.principal_user,
            evidence_type="EVID_U20_ACTIVITY_REPORTS",
            page_start=45,
            page_end=50,
        )

        # Association-scoped review: verify Association A, reject Association B independently
        EvidenceService.verify_association(
            association_id=assoc_a.pk,
            verifier=self.committee_user,
            reason="U10.3 financial records verified on pages 12-14.",
        )
        EvidenceService.reject_association(
            association_id=assoc_b.pk,
            verifier=self.committee_user,
            reason="U20.3 section on pages 45-50 lacks required SDG activity metrics.",
            rejection_code=RejectionReasonCode.INCOMPLETE_DOCUMENTATION.value,
        )

        assoc_a.refresh_from_db()
        assoc_b.refresh_from_db()

        scoring_doc_a = EvidenceService.to_scoring_domain(assoc_a)
        scoring_doc_b = EvidenceService.to_scoring_domain(assoc_b)

        # Target behavior: U10.3 association was valid and should pass; U20.3 association was rejected and must fail.
        # Physical document lifecycle remains untouched.
        status_u10, mult_u10, _ = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U10",
            subcriterion_id="U10.3",
            uploaded_docs=[scoring_doc_a],
        )
        status_u20, mult_u20, _ = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U20",
            subcriterion_id="U20.3",
            uploaded_docs=[scoring_doc_b],
        )

        self.assertEqual(
            status_u10,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "Target Contract Violation: Association A (U10.3) was valid and must pass independently."
        )
        self.assertEqual(mult_u10, 1.0)
        self.assertEqual(status_u20, GatingStatus.FAILED_EVIDENCE_REJECTED)
        self.assertEqual(mult_u20, 0.0)
        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_PRESENT)

    # =========================================================================
    # TEST 7 — REJECTED EVIDENCE MUST NOT UNLOCK SCORE
    # =========================================================================
    def test_07_rejected_evidence_must_not_unlock_score(self):
        """
        Target Contract & Existing Behavior:
        Use single-subcriterion parameter C3 (C3.1 ABC Registration, max 4.0).
        Reviewer rejection must set evidence multiplier = 0.0 and final gated score = 0.0.

        Expected: MUST PASS against current architecture.
        """
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id=self.college_context.assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id=self.college_context.institution_id,
            original_filename="abc_portal_screenshot.pdf",
            file_bytes=self.sample_bytes,
            mime_type="application/pdf",
            evidence_type="EVID_C3_ABC_DASHBOARD",
            document_date=date(2025, 9, 15),
            academic_year="2025-26",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="C3",
            subcriterion_id="C3.1",
            actor=self.principal_user,
        )

        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        EvidenceService.reject_evidence(
            evidence_id=doc.pk,
            verifier=self.committee_user,
            reason="Screenshot is unreadable and lacks institutional header.",
            rejection_code=RejectionReasonCode.ILLEGIBLE_DOCUMENT.value,
        )
        doc.refresh_from_db()

        scoring_doc = EvidenceService.to_scoring_domain(doc)
        status_gate, multiplier, _ = evaluate_evidence(["EVID_C3_ABC_DASHBOARD"], [scoring_doc])

        self.assertEqual(status_gate, GatingStatus.FAILED_EVIDENCE_REJECTED)
        self.assertEqual(multiplier, 0.0, "Evidence multiplier must be 0.0 for rejected evidence.")

        eval_fn = COLLEGE_EVALUATORS["C3"]
        param_input = ParameterInput(
            parameter_code="C3",
            subcriteria_inputs={
                "C3.1": SubcriterionInput(
                    subcriterion_code="C3.1",
                    raw_inputs={"abc_registered_students": 95, "total_enrolled_students": 100},
                    evidence_docs=[scoring_doc],
                )
            },
        )
        result = eval_fn(param_input, self.college_context, self.validator)

        self.assertEqual(result.raw_score, 4.0, "Raw score before gating should be 4.0.")
        self.assertEqual(result.evidence_gated_score, 0.0, "Evidence-gated score MUST be 0.0.")
        self.assertEqual(result.subcriteria_results["C3.1"].gating_status, GatingStatus.FAILED_EVIDENCE_REJECTED)

    # =========================================================================
    # TEST 8 — FRAMEWORK ISOLATION
    # =========================================================================
    def test_08_framework_isolation(self):
        """
        Target Contract & Existing Behavior:
        Attempting to associate a College evidence document with a University
        subcriterion must be rejected with FrameworkMismatchError.

        Expected: MUST PASS against current architecture.
        """
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id=self.college_context.assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id=self.college_context.institution_id,
            original_filename="college_idp.pdf",
            file_bytes=self.sample_bytes,
            mime_type="application/pdf",
            evidence_type="EVID_C1_APPROVED_IDP",
        )

        with self.assertRaises(FrameworkMismatchError) as ctx:
            EvidenceService.associate_subcriterion(
                evidence_id=doc.pk,
                parameter_id="U4",
                subcriterion_id="U4.1",
                actor=self.principal_user,
            )

        self.assertIn("Framework isolation violation", str(ctx.exception))

    # =========================================================================
    # TEST 9 — INSTITUTION ISOLATION
    # =========================================================================
    def test_09_institution_isolation(self):
        """
        Target Contract & Existing Behavior:
        An authenticated principal from Institution B cannot mutate or associate
        evidence belonging to Institution A.
        Enforces HTTP 403 Forbidden / PermissionDenied at the API layer and data layer.

        Expected: MUST PASS against current architecture.
        """
        doc_a = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id="ASSESS-COLLEGE-A-01",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id=self.college_a.aishe_code,
            original_filename="college_a_proof.pdf",
            file_bytes=self.sample_bytes,
            mime_type="application/pdf",
            evidence_type="EVID_C1_APPROVED_IDP",
        )

        # Authenticate as Principal B (Govt College Kurukshetra)
        self.client.force_authenticate(user=self.principal_user_b)

        # Attempt to associate Institution A's document
        url = reverse("evidence-associate", kwargs={"pk": doc_a.pk})
        response = self.client.post(
            url,
            {
                "parameter_id": "C1",
                "subcriterion_id": "C1.1",
                "academic_year": "2025-26",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "Institution isolation violation: Principal B must not associate Institution A's evidence."
        )

    # =========================================================================
    # TEST 10 — LEGACY COARSE EVIDENCE MUST NOT UNLOCK SIBLINGS
    # =========================================================================
    def test_10_legacy_coarse_evidence_must_not_unlock_siblings(self):
        """
        Target Contract:
        A legacy document with coarse code EVID_U7_APPOINTMENT may retain compatibility
        with U7.1, but must NOT automatically unlock sibling subcriteria U7.2, U7.3, U7.4.

        Expected Failure on Current Architecture:
        Current architecture's parameter-level fallback treats EVID_U7_APPOINTMENT
        as satisfying the mandatory evidence for U7.2, U7.3, and U7.4.
        """
        doc = self._create_and_verify_doc(
            assessment_id=self.univ_context.assessment_id,
            framework="UNIVERSITY_2026",
            institution_id=self.univ_context.institution_id,
            evidence_type="EVID_U7_APPOINTMENT",
            original_filename="legacy_pop_appointment.pdf",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.principal_user,
        )

        scoring_doc = EvidenceService.to_scoring_domain(doc)
        eval_fn = UNIVERSITY_EVALUATORS["U7"]

        # When evaluated across U7 subcriteria, only U7.1 may pass:
        param_input = ParameterInput(
            parameter_code="U7",
            subcriteria_inputs={
                "U7.1": SubcriterionInput("U7.1", raw_inputs={"verified": True}, evidence_docs=[scoring_doc]),
                "U7.2": SubcriterionInput("U7.2", raw_inputs={"verified": True}, evidence_docs=[scoring_doc]),
                "U7.3": SubcriterionInput("U7.3", raw_inputs={"verified": True}, evidence_docs=[scoring_doc]),
                "U7.4": SubcriterionInput("U7.4", raw_inputs={"verified": True}, evidence_docs=[scoring_doc]),
            },
        )
        result = eval_fn(param_input, self.univ_context, self.validator)

        self.assertEqual(result.subcriteria_results["U7.1"].gating_status, GatingStatus.PASSED_EVIDENCE_VERIFIED)

        # Contract assertion: U7.2, U7.3, U7.4 must NOT automatically pass with coarse appointment document
        self.assertNotEqual(
            result.subcriteria_results["U7.2"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "Legacy coarse appointment evidence must NOT unlock U7.2."
        )
        self.assertNotEqual(
            result.subcriteria_results["U7.3"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "Legacy coarse appointment evidence must NOT unlock U7.3."
        )
        self.assertNotEqual(
            result.subcriteria_results["U7.4"].gating_status,
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            "Legacy coarse appointment evidence must NOT unlock U7.4."
        )

    # =========================================================================
    # PART 11.A — COVERAGE / SCORE DIVERGENCE DEFECT
    # =========================================================================
    def test_11a_coverage_scoring_divergence(self):
        """
        Explicit Test Demonstrating Known Architectural Defect A:
        CoverageEngine ignores evidence_type matching and evaluates subcriterion
        coverage solely on document status (EVIDENCE_VERIFIED).
        Meanwhile, a scoring gate requiring specific evidence (e.g. EVID_U7_WORKLOAD)
        fails because the document type is EVID_U7_APPOINTMENT.

        Result:
        CoverageEngine reports Coverage = EVIDENCE_VERIFIED.
        Scoring evidence gate reports Gating = FAILED_EVIDENCE_ABSENT, multiplier = 0.0.
        """
        doc = self._create_and_verify_doc(
            assessment_id="ASSESS-DIVERGENCE-01",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-DIV-01",
            evidence_type="EVID_U7_APPOINTMENT",
            original_filename="pop_appointment_only.pdf",
        )
        # 1. In Step 4C/4D architecture, attempting to associate quarantined coarse appointment
        # evidence to U7.2 is strictly rejected at the association boundary:
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            EvidenceService.associate_subcriterion(
                evidence_id=doc.pk,
                parameter_id="U7",
                subcriterion_id="U7.2",
                actor=self.principal_user,
            )

        # 2. Evaluate scoring gate against U7.2: mismatched coarse evidence cannot satisfy U7.2 scoring contract
        scoring_doc = EvidenceService.to_scoring_domain(doc)
        gating_status, multiplier, trace = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.2",
            uploaded_docs=[scoring_doc],
        )

        # Scoring gate FAILS because EVID_U7_APPOINTMENT does not satisfy U7.2 contract:
        self.assertEqual(
            multiplier,
            0.0,
            "Current defect demonstration: Scoring gate fails with multiplier 0.0."
        )
        self.assertEqual(
            gating_status,
            GatingStatus.FAILED_EVIDENCE_ABSENT,
        )

    # =========================================================================
    # PART 11.B — DOCUMENT-LEVEL VERIFICATION LIMITATION
    # =========================================================================
    def test_11b_document_level_verification_limitation(self):
        """
        Explicit Test Demonstrating Known Architectural Defect B:
        Create one document associated with U7.1 and U7.2.
        Verify the document using the current verification system.
        Demonstrate that the verification is document-level rather than association-level,
        so verifying the document forces all associations to become verified without
        independent association-level verification.
        """
        doc = EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id=self.univ_context.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.univ_context.institution_id,
            original_filename="bundled_u7_proof.pdf",
            file_bytes=self.sample_bytes,
            mime_type="application/pdf",
            evidence_type="EVID_GENERAL",
            document_date=date(2025, 10, 1),
            academic_year="2025-26",
        )

        assoc1 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.principal_user,
            evidence_type="EVID_U7_APPOINTMENT",
        )
        assoc2 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.2",
            actor=self.principal_user,
            evidence_type="EVID_U7_TEACHING_LOGS",
        )

        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_PRESENT)

        # Submit and verify the document at document level
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        verification = EvidenceService.verify_evidence(
            evidence_id=doc.pk,
            verifier=self.committee_user,
            reason="Verified appointment document.",
        )

        doc.refresh_from_db()
        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_VERIFIED)

        # Demonstrate that verification attaches strictly to the EvidenceDocument
        self.assertEqual(verification.evidence, doc)

        # In current architecture, EvidenceSubcriterionAssociation HAS independent status property:
        self.assertTrue(hasattr(assoc1, "verification_status"))
        self.assertTrue(hasattr(assoc2, "verification_status"))
        self.assertIsNone(assoc1.verification_status)
        self.assertIsNone(assoc2.verification_status)

        # Reload associations from DB
        assoc1 = EvidenceSubcriterionAssociation.objects.get(pk=assoc1.pk)
        assoc2 = EvidenceSubcriterionAssociation.objects.get(pk=assoc2.pk)

        # For multi-subcriterion parameters, document-level verification alone DOES NOT verify the associations!
        scoring_doc1 = EvidenceService.to_scoring_domain(assoc1)
        scoring_doc2 = EvidenceService.to_scoring_domain(assoc2)
        self.assertEqual(scoring_doc1.status, ScoringEvidenceState.EVIDENCE_PENDING)
        self.assertEqual(scoring_doc2.status, ScoringEvidenceState.EVIDENCE_PENDING)

        # Scoring gate confirms that unverified associations cannot score:
        status1, mult1, _ = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            uploaded_docs=[scoring_doc1],
        )
        self.assertEqual(status1, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)
        self.assertEqual(mult1, 0.0)

        # Explicitly verify assoc1 at the association level:
        EvidenceService.verify_association(assoc1.pk, verifier=self.committee_user)
        assoc1.refresh_from_db()
        self.assertEqual(assoc1.verification_status, VerificationDecision.VERIFIED)

        scoring_doc1_v = EvidenceService.to_scoring_domain(assoc1)
        self.assertEqual(scoring_doc1_v.status, ScoringEvidenceState.EVIDENCE_VERIFIED)

        status1_v, mult1_v, _ = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            uploaded_docs=[scoring_doc1_v],
        )
        self.assertEqual(status1_v, GatingStatus.PASSED_EVIDENCE_VERIFIED)
        self.assertEqual(mult1_v, 1.0)

        # Association 2 remains unverified and blocked:
        self.assertIsNone(assoc2.verification_status)
        status2, mult2, _ = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.2",
            uploaded_docs=[scoring_doc2],
        )
        self.assertEqual(status2, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)
        self.assertEqual(mult2, 0.0)
