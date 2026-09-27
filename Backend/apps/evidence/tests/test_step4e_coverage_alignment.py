"""
NEP Excellence Awards 2026 - Step 4E Coverage Engine Alignment Test Suite
Authoritative tests for subcriterion-aware evidence coverage evaluation and coverage/scoring consistency.

Covers:
Phase 4 Regression Cases (A through O):
- Case A: U7.1 vs U7.2 isolation
- Case B: U10 society vs funding
- Case C: U17 NIRF submission vs ranking
- Case D: C20 NAAC vs NIRF/AISHE
- Case E: Composite document with multiple independent associations
- Case F: Association rejection precedence
- Case G: Association pending state
- Case H: Legacy/quarantined evidence prevention
- Case I: Framework isolation (University vs College)
- Case J: Institution isolation (Institution A vs Institution B)
- Case K: Parameter isolation (U10 vs U20)
- Case L: Exact subcriterion isolation (sibling association rejected)
- Case M: Parameter-level evidence negative case (multi-subcriterion parameter)
- Case N: Source-silent contracts (U6, C5, C9)
- Case O: Unresolved contracts (U16.III, C19.III, U18.3)

Phase 5 Consistency Checks (1 through 7):
- 1. Valid verified exact association: coverage = COVERED, scoring = PASSED_EVIDENCE_VERIFIED
- 2. Missing exact association: coverage != COVERED, scoring = FAILED_EVIDENCE_ABSENT
- 3. Pending association: coverage != COVERED, scoring = PROVISIONAL_PENDING_VERIFICATION
- 4. Rejected association: coverage != COVERED, scoring = FAILED_EVIDENCE_REJECTED
- 5. Wrong evidence type: coverage != COVERED, scoring = FAILED_EVIDENCE_ABSENT
- 6. Wrong framework: coverage != COVERED, scoring = FAILED_EVIDENCE_ABSENT
- 7. Wrong institution: coverage != COVERED, scoring = FAILED_EVIDENCE_ABSENT
"""
import hashlib
from datetime import date
from django.test import TestCase

from apps.authentication.models import College, User
from apps.evidence.enums import (
    AssociationVerificationDecision,
    CoverageDeficiencyCode,
    CoverageState,
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
)
from apps.evidence.models import (
    EvidenceAssociationVerification,
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.evidence.services import EvidenceService
from apps.evidence.taxonomy import (
    ContractStatus,
    QuarantinedLegacyEvidenceError,
    get_subcriterion_contract,
    validate_subcriterion_evidence_contract,
)
from apps.scoring.domain import EvidenceDocument as ScoringEvidenceDoc
from apps.scoring.enums import EvidenceState as ScoringEvidenceState, GatingStatus
from apps.scoring.evaluators.evidence_gating import evaluate_subcriterion_contract_evidence
from apps.scoring.rules.definitions import UNIVERSITY_PARAMETERS, COLLEGE_PARAMETERS


class Step4ECoverageAlignmentTestCase(TestCase):
    """
    Test suite for Step 4E Coverage Engine Alignment.
    """

    def setUp(self):
        super().setUp()
        self.college_a = College.objects.create(name="Govt College Karnal", aishe_code="C-4001")
        self.college_b = College.objects.create(name="Govt College Kurukshetra", aishe_code="C-4002")

        self.univ_user_a = User.objects.create_user(
            email="registrar.mdu@univ.edu",
            full_name="Registrar MDU",
            role="principal",
            password="SecurePassword123!",
        )
        self.coll_user_a = User.objects.create_user(
            email="principal.karnal@college.edu",
            full_name="Principal Karnal",
            role="principal",
            college=self.college_a,
            password="SecurePassword123!",
        )
        self.reviewer = User.objects.create_user(
            email="reviewer.dhe@haryana.gov.in",
            full_name="Committee Reviewer",
            role="committee",
            password="SecurePassword123!",
        )
        self.admin = User.objects.create_superuser(
            email="admin@dhe.haryana.gov.in",
            full_name="State Administrator",
            password="SecurePassword123!",
        )

        ReviewerAuthorization.objects.create(
            user=self.reviewer,
            framework="UNIVERSITY_2026",
            granted_by=self.admin,
        )
        ReviewerAuthorization.objects.create(
            user=self.reviewer,
            framework="COLLEGE_2026",
            granted_by=self.admin,
        )

        self.sample_bytes = b"%PDF-1.4 Mock NEP 2026 Step 4E Test Dossier\n%%EOF"
        self.sample_checksum = hashlib.sha256(self.sample_bytes).hexdigest()

    def _create_doc(
        self,
        framework="UNIVERSITY_2026",
        institution_id="UNIV-001",
        assessment_id="ASSESS-2026-STEP4E",
        evidence_type="EVID_U7_APPOINTMENT",
        status=EvidenceLifecycleState.EVIDENCE_VERIFIED,
        document_date=date(2025, 9, 15),
        uploader=None,
    ) -> EvidenceDocument:
        uploader = uploader or (self.univ_user_a if framework == "UNIVERSITY_2026" else self.coll_user_a)
        inst_type = "UNIVERSITY" if framework == "UNIVERSITY_2026" else "COLLEGE"
        return EvidenceDocument.objects.create(
            assessment_id=assessment_id,
            framework=framework,
            institution_type=inst_type,
            institution_id=institution_id,
            original_filename=f"{evidence_type.lower()}_proof.pdf",
            file_path=f"mock/path/{evidence_type.lower()}_proof.pdf",
            file_size=len(self.sample_bytes),
            file_checksum=self.sample_checksum,
            uploader=uploader,
            evidence_type=evidence_type,
            document_date=document_date,
            academic_year="2025-26",
            status=status,
            is_active=True,
        )

    def _associate(
        self,
        doc: EvidenceDocument,
        parameter_id: str,
        subcriterion_id: str,
        subcriterion_evidence_type: str = "",
        verification_decision: str = None,
        rejection_code: str = "",
    ) -> EvidenceSubcriterionAssociation:
        assoc = EvidenceSubcriterionAssociation.objects.create(
            evidence=doc,
            parameter_id=parameter_id,
            subcriterion_id=subcriterion_id,
            subcriterion_evidence_type=subcriterion_evidence_type or doc.evidence_type,
            associated_by=doc.uploader,
        )
        if verification_decision:
            EvidenceAssociationVerification.objects.create(
                association=assoc,
                verifier=self.reviewer,
                decision=verification_decision,
                reason="Verification record for Step 4E test.",
                rejection_code=rejection_code,
            )
        return assoc

    # =========================================================================
    # PHASE 4 — CASE A: U7.1 vs U7.2 Isolation
    # =========================================================================
    def test_case_a_u71_vs_u72_isolation(self):
        """
        Verify:
        - Valid verified evidence for U7.1 (EVID_U7_APPOINTMENT) marks U7.1 COVERED.
        - Verifying U7.1 does NOT mark U7.2 covered.
        - U7.2 remains MISSING until evidence exists, and PENDING when unverified.
        """
        doc_u71 = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-U7",
            evidence_type="EVID_U7_APPOINTMENT",
        )
        self._associate(
            doc=doc_u71,
            parameter_id="U7",
            subcriterion_id="U7.1",
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            verification_decision=VerificationDecision.VERIFIED,
        )

        # Evaluate coverage for U7.1 and U7.2
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-U7",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1", "U7.2"],
        )
        results = {s.subcriterion_id: s for p in report.parameters for s in p.subcriteria}

        # U7.1 is COVERED
        self.assertEqual(results["U7.1"].coverage_state, CoverageState.COVERED)
        self.assertEqual(results["U7.1"].coverage_state, CoverageState.EVIDENCE_VERIFIED)

        # U7.2 is strictly MISSING (NO_EVIDENCE), NOT covered!
        self.assertEqual(results["U7.2"].coverage_state, CoverageState.MISSING)
        self.assertEqual(results["U7.2"].coverage_state, CoverageState.NO_EVIDENCE)
        self.assertEqual(results["U7.2"].verified_count, 0)

        # Now add unverified evidence for U7.2 -> state becomes PENDING
        doc_u72 = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-U7",
            evidence_type="EVID_U7_TEACHING_LOGS",
            status=EvidenceLifecycleState.EVIDENCE_PENDING,
        )
        self._associate(
            doc=doc_u72,
            parameter_id="U7",
            subcriterion_id="U7.2",
            subcriterion_evidence_type="EVID_U7_TEACHING_LOGS",
            verification_decision=None,  # Unreviewed / pending
        )

        report2 = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-U7",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1", "U7.2"],
        )
        results2 = {s.subcriterion_id: s for p in report2.parameters for s in p.subcriteria}

        self.assertEqual(results2["U7.1"].coverage_state, CoverageState.COVERED)
        self.assertEqual(results2["U7.2"].coverage_state, CoverageState.PENDING)
        self.assertEqual(results2["U7.2"].coverage_state, CoverageState.EVIDENCE_PENDING)

    # =========================================================================
    # PHASE 4 — CASE B: U10 Society vs Funding
    # =========================================================================
    def test_case_b_u10_society_vs_funding(self):
        """
        Verify:
        - U10.1 society registration proof does not satisfy U10.3 funding requirements.
        - U10.3 requires its own valid EVID_U10_FINANCIAL_RECORDS association.
        """
        doc_u101 = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-U10",
            evidence_type="EVID_U10_REG_CERT",
        )
        self._associate(
            doc=doc_u101,
            parameter_id="U10",
            subcriterion_id="U10.1",
            subcriterion_evidence_type="EVID_U10_REG_CERT",
            verification_decision=VerificationDecision.VERIFIED,
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-U10",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U10.1", "U10.3"],
        )
        results = {s.subcriterion_id: s for p in report.parameters for s in p.subcriteria}

        self.assertEqual(results["U10.1"].coverage_state, CoverageState.COVERED)
        self.assertEqual(results["U10.3"].coverage_state, CoverageState.MISSING)

        # Add valid verified funding evidence for U10.3
        doc_u103 = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-U10",
            evidence_type="EVID_U10_FINANCIAL_RECORDS",
        )
        self._associate(
            doc=doc_u103,
            parameter_id="U10",
            subcriterion_id="U10.3",
            subcriterion_evidence_type="EVID_U10_FINANCIAL_RECORDS",
            verification_decision=VerificationDecision.VERIFIED,
        )

        report2 = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-U10",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U10.1", "U10.3"],
        )
        results2 = {s.subcriterion_id: s for p in report2.parameters for s in p.subcriteria}
        self.assertEqual(results2["U10.3"].coverage_state, CoverageState.COVERED)

    # =========================================================================
    # PHASE 4 — CASE C: U17 NIRF Submission vs Ranking
    # =========================================================================
    def test_case_c_u17_nirf_submission_vs_ranking(self):
        """
        Verify:
        - NIRF 2026 submission proof (U17.1) does not satisfy NIRF 2025 ranking proof (U17.2).
        """
        doc_u171 = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-U17",
            evidence_type="EVID_U17_NIRF_2026_PROOF",
        )
        self._associate(
            doc=doc_u171,
            parameter_id="U17",
            subcriterion_id="U17.1",
            subcriterion_evidence_type="EVID_U17_NIRF_2026_PROOF",
            verification_decision=VerificationDecision.VERIFIED,
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-U17",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U17.1", "U17.2"],
        )
        results = {s.subcriterion_id: s for p in report.parameters for s in p.subcriteria}

        self.assertEqual(results["U17.1"].coverage_state, CoverageState.COVERED)
        self.assertEqual(results["U17.2"].coverage_state, CoverageState.MISSING)

    # =========================================================================
    # PHASE 4 — CASE D: C20 NAAC vs NIRF / AISHE
    # =========================================================================
    def test_case_d_c20_naac_vs_nirf_aishe(self):
        """
        Verify:
        - NAAC certificate evidence (C20.1) does not satisfy NIRF participation (C20.2)
          or AISHE certification (C20.3).
        """
        doc_c201 = self._create_doc(
            framework="COLLEGE_2026",
            institution_id="C-4001",
            assessment_id="ASSESS-C20",
            evidence_type="EVID_C20_NAAC_CERT",
        )
        self._associate(
            doc=doc_c201,
            parameter_id="C20",
            subcriterion_id="C20.1",
            subcriterion_evidence_type="EVID_C20_NAAC_CERT",
            verification_decision=VerificationDecision.VERIFIED,
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-C20",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C20.1", "C20.2", "C20.3"],
        )
        results = {s.subcriterion_id: s for p in report.parameters for s in p.subcriteria}

        self.assertEqual(results["C20.1"].coverage_state, CoverageState.COVERED)
        self.assertEqual(results["C20.2"].coverage_state, CoverageState.MISSING)
        self.assertEqual(results["C20.3"].coverage_state, CoverageState.MISSING)

    # =========================================================================
    # PHASE 4 — CASE E: Composite Document
    # =========================================================================
    def test_case_e_composite_document(self):
        """
        Verify:
        - One physical document can legitimately support multiple subcriteria ONLY through
          separate explicit associations.
        - Coverage is calculated independently per association.
        """
        doc_composite = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-COMPOSITE",
            evidence_type="EVID_U7_APPOINTMENT",
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED,
        )

        # Assoc 1: U7.1 verified
        self._associate(
            doc=doc_composite,
            parameter_id="U7",
            subcriterion_id="U7.1",
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            verification_decision=VerificationDecision.VERIFIED,
        )
        # Assoc 2: U7.2 unreviewed / pending
        self._associate(
            doc=doc_composite,
            parameter_id="U7",
            subcriterion_id="U7.2",
            subcriterion_evidence_type="EVID_U7_TEACHING_LOGS",
            verification_decision=None,
        )
        # Assoc 3: U7.3 rejected
        self._associate(
            doc=doc_composite,
            parameter_id="U7",
            subcriterion_id="U7.3",
            subcriterion_evidence_type="EVID_U7_WORKSHOP_REPORTS",
            verification_decision=VerificationDecision.REJECTED,
            rejection_code=RejectionReasonCode.MISMATCHED_CRITERIA,
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-COMPOSITE",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1", "U7.2", "U7.3"],
        )
        results = {s.subcriterion_id: s for p in report.parameters for s in p.subcriteria}

        self.assertEqual(results["U7.1"].coverage_state, CoverageState.COVERED)
        self.assertEqual(results["U7.2"].coverage_state, CoverageState.PENDING)
        self.assertEqual(results["U7.3"].coverage_state, CoverageState.REJECTED)

    # =========================================================================
    # PHASE 4 — CASE F: Association Rejection Precedence
    # =========================================================================
    def test_case_f_association_rejection(self):
        """
        Verify:
        - A document can remain physically present and document-level VERIFIED, while
          one specific association is REJECTED.
        - The rejected association must produce REJECTED coverage, not COVERED.
        """
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-ASSOC-REJECT",
            evidence_type="EVID_U7_APPOINTMENT",
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED,
        )
        self._associate(
            doc=doc,
            parameter_id="U7",
            subcriterion_id="U7.1",
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            verification_decision=VerificationDecision.REJECTED,
            rejection_code=RejectionReasonCode.INCOMPLETE_DOCUMENTATION,
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-ASSOC-REJECT",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1"],
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertEqual(sub.coverage_state, CoverageState.REJECTED)
        self.assertEqual(sub.coverage_state, CoverageState.EVIDENCE_REJECTED)
        self.assertIn(CoverageDeficiencyCode.EVIDENCE_REJECTED.value, sub.deficiency_codes)

    # =========================================================================
    # PHASE 4 — CASE G: Association Pending
    # =========================================================================
    def test_case_g_association_pending(self):
        """
        Verify:
        - An unverified association on a multi-subcriterion parameter must NOT produce COVERED,
          even if document-level status is EVIDENCE_VERIFIED.
        """
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-ASSOC-PENDING",
            evidence_type="EVID_U7_APPOINTMENT",
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED,
        )
        self._associate(
            doc=doc,
            parameter_id="U7",
            subcriterion_id="U7.1",
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            verification_decision=None,  # Unreviewed association
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-ASSOC-PENDING",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1"],
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertEqual(sub.coverage_state, CoverageState.PENDING)
        self.assertEqual(sub.coverage_state, CoverageState.EVIDENCE_PENDING)

    # =========================================================================
    # PHASE 4 — CASE H: Legacy / Quarantined Evidence Prevention
    # =========================================================================
    def test_case_h_legacy_quarantined_evidence(self):
        """
        Verify:
        - Legacy coarse evidence types cannot produce coverage on multi-subcriterion parameters.
        - Taxonomy raises QuarantinedLegacyEvidenceError at validation boundary.
        """
        # 1. Verify taxonomy contract layer rejects quarantined legacy types
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract(
                "UNIVERSITY_2026", "U7", "U7.2", "EVID_U7_APPOINTMENT"
            )

        # 2. If a document has a quarantined coarse type for U7.2, coverage fails closed
        doc_legacy = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-QUARANTINED",
            evidence_type="EVID_U7_APPOINTMENT",
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED,
        )
        assoc = EvidenceSubcriterionAssociation.objects.create(
            evidence=doc_legacy,
            parameter_id="U7",
            subcriterion_id="U7.2",
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            associated_by=self.univ_user_a,
        )
        EvidenceAssociationVerification.objects.create(
            association=assoc,
            verifier=self.reviewer,
            decision=VerificationDecision.VERIFIED,
            reason="Attempted review of quarantined evidence.",
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-QUARANTINED",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.2"],
        )
        sub = report.parameters[0].subcriteria[0]
        self.assertNotEqual(sub.coverage_state, CoverageState.COVERED)
        self.assertIn(CoverageDeficiencyCode.QUARANTINED_EVIDENCE.value, sub.deficiency_codes)


    # =========================================================================
    # PHASE 4 — CASE I: Framework Isolation
    # =========================================================================
    def test_case_i_framework_isolation(self):
        """
        Verify:
        - University evidence cannot satisfy College coverage.
        - College evidence cannot satisfy University coverage.
        """
        # University doc uploaded for college assessment C1
        doc_univ = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="C-4001",
            assessment_id="ASSESS-FW-MISMATCH",
            evidence_type="EVID_U7_APPOINTMENT",
        )
        self._associate(
            doc=doc_univ,
            parameter_id="C1",
            subcriterion_id="C1.1",
            verification_decision=VerificationDecision.VERIFIED,
        )

        report_coll = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-FW-MISMATCH",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C1.1"],
        )
        sub_coll = report_coll.parameters[0].subcriteria[0]
        self.assertNotEqual(sub_coll.coverage_state, CoverageState.COVERED)
        self.assertIn(CoverageDeficiencyCode.FRAMEWORK_MISMATCH.value, sub_coll.deficiency_codes)

        # College doc uploaded for university assessment U1
        doc_coll = self._create_doc(
            framework="COLLEGE_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-FW-MISMATCH-2",
            evidence_type="EVID_C20_NAAC_CERT",
        )
        self._associate(
            doc=doc_coll,
            parameter_id="U1",
            subcriterion_id="U1.1",
            verification_decision=VerificationDecision.VERIFIED,
        )

        report_univ = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-FW-MISMATCH-2",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U1.1"],
        )
        sub_univ = report_univ.parameters[0].subcriteria[0]
        self.assertNotEqual(sub_univ.coverage_state, CoverageState.COVERED)
        self.assertIn(CoverageDeficiencyCode.FRAMEWORK_MISMATCH.value, sub_univ.deficiency_codes)

    # =========================================================================
    # PHASE 4 — CASE J: Institution Isolation
    # =========================================================================
    def test_case_j_institution_isolation(self):
        """
        Verify:
        - Evidence belonging to Institution A cannot satisfy coverage for Institution B.
        """
        doc_inst_a = self._create_doc(
            framework="COLLEGE_2026",
            institution_id="C-4001",  # College A
            assessment_id="ASSESS-INST-A",
            evidence_type="EVID_C1_MANDATORY",
        )
        self._associate(
            doc=doc_inst_a,
            parameter_id="C1",
            subcriterion_id="C1.1",
            verification_decision=VerificationDecision.VERIFIED,
        )

        # Evaluating for Institution B (C-4002)
        report_inst_b = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-INST-B",
            framework="COLLEGE_2026",
            institution_id="C-4002",
            subcriterion_codes=["C1.1"],
        )
        sub_b = report_inst_b.parameters[0].subcriteria[0]
        self.assertEqual(sub_b.coverage_state, CoverageState.MISSING)
        self.assertEqual(sub_b.evidence_count, 0)

    # =========================================================================
    # PHASE 4 — CASE K: Parameter Isolation
    # =========================================================================
    def test_case_k_parameter_isolation(self):
        """
        Verify:
        - Evidence associated with one parameter (e.g. U10) cannot satisfy another parameter (e.g. U20).
        """
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-PARAM-ISO",
            evidence_type="EVID_U10_REG_CERT",
        )
        self._associate(
            doc=doc,
            parameter_id="U10",
            subcriterion_id="U10.1",
            verification_decision=VerificationDecision.VERIFIED,
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-PARAM-ISO",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U20.1"],
        )
        sub_u20 = report.parameters[0].subcriteria[0]
        self.assertEqual(sub_u20.coverage_state, CoverageState.MISSING)
        self.assertEqual(sub_u20.evidence_count, 0)

    # =========================================================================
    # PHASE 4 — CASE L: Exact Subcriterion Isolation
    # =========================================================================
    def test_case_l_exact_subcriterion_isolation(self):
        """
        Verify:
        - Evidence associated with sibling subcriterion U7.1 cannot satisfy target subcriterion U7.2.
        """
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-SUB-ISO",
            evidence_type="EVID_U7_APPOINTMENT",
        )
        self._associate(
            doc=doc,
            parameter_id="U7",
            subcriterion_id="U7.1",
            verification_decision=VerificationDecision.VERIFIED,
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-SUB-ISO",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.2"],
        )
        sub_u72 = report.parameters[0].subcriteria[0]
        self.assertEqual(sub_u72.coverage_state, CoverageState.MISSING)
        self.assertEqual(sub_u72.evidence_count, 0)

    # =========================================================================
    # PHASE 4 — CASE M: Parameter-Level Evidence Negative Case
    # =========================================================================
    def test_case_m_parameter_level_evidence_negative_case(self):
        """
        Verify:
        - Parameter-level verified evidence WITHOUT a valid exact subcriterion association
          must NOT mark a multi-subcriterion parameter's subcriterion as COVERED.
        """
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-PARAM-ONLY",
            evidence_type="EVID_U7_APPOINTMENT",
        )
        # Association has parameter_id="U7" but subcriterion_id="" (parameter-level fallback attempt)
        self._associate(
            doc=doc,
            parameter_id="U7",
            subcriterion_id="",
            verification_decision=VerificationDecision.VERIFIED,
        )

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-PARAM-ONLY",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1", "U7.2"],
        )
        results = {s.subcriterion_id: s for p in report.parameters for s in p.subcriteria}

        self.assertNotEqual(results["U7.1"].coverage_state, CoverageState.COVERED)
        self.assertNotEqual(results["U7.2"].coverage_state, CoverageState.COVERED)

    # =========================================================================
    # PHASE 4 — CASE N: Source-Silent Contracts
    # =========================================================================
    def test_case_n_source_silent_contracts(self):
        """
        Verify:
        - U6, C5, C9 remain governed by their Step 4C SOURCE_SILENT contract state.
        - Without evidence, coverage state is SOURCE_SILENT.
        - Does not invent documentary requirements or mark COVERED.
        """
        # Test U6 (U6.A)
        report_u = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-SOURCE-SILENT",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U6.A"],
        )
        sub_u6 = report_u.parameters[0].subcriteria[0]
        self.assertEqual(sub_u6.coverage_state, CoverageState.SOURCE_SILENT)
        self.assertIn(CoverageDeficiencyCode.CONTRACT_SOURCE_SILENT.value, sub_u6.deficiency_codes)
        self.assertNotEqual(sub_u6.coverage_state, CoverageState.COVERED)

        # Test C5 and C9 (C5.1 and C9.I)
        report_c = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-SOURCE-SILENT-C",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C5.1", "C9.I"],
        )
        results_c = {s.subcriterion_id: s for p in report_c.parameters for s in p.subcriteria}

        self.assertEqual(results_c["C5.1"].coverage_state, CoverageState.SOURCE_SILENT)
        self.assertIn(CoverageDeficiencyCode.CONTRACT_SOURCE_SILENT.value, results_c["C5.1"].deficiency_codes)
        self.assertNotEqual(results_c["C5.1"].coverage_state, CoverageState.COVERED)

        self.assertEqual(results_c["C9.I"].coverage_state, CoverageState.SOURCE_SILENT)
        self.assertIn(CoverageDeficiencyCode.CONTRACT_SOURCE_SILENT.value, results_c["C9.I"].deficiency_codes)
        self.assertNotEqual(results_c["C9.I"].coverage_state, CoverageState.COVERED)


    # =========================================================================
    # PHASE 4 — CASE O: Unresolved Contracts
    # =========================================================================
    def test_case_o_unresolved_contracts(self):
        """
        Verify:
        - U16.III Scopus, C19.III Scopus, U18.3 RPL workshop must remain UNRESOLVED.
        - Cannot be marked COVERED.
        """
        # Test U16.III and U18.3
        report_u = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-UNRESOLVED",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U16.III", "U18.3"],
        )
        results_u = {s.subcriterion_id: s for p in report_u.parameters for s in p.subcriteria}

        self.assertEqual(results_u["U16.III"].coverage_state, CoverageState.UNRESOLVED)
        self.assertIn(CoverageDeficiencyCode.CONTRACT_UNRESOLVED.value, results_u["U16.III"].deficiency_codes)
        self.assertNotEqual(results_u["U16.III"].coverage_state, CoverageState.COVERED)

        self.assertEqual(results_u["U18.3"].coverage_state, CoverageState.UNRESOLVED)
        self.assertIn(CoverageDeficiencyCode.CONTRACT_UNRESOLVED.value, results_u["U18.3"].deficiency_codes)
        self.assertNotEqual(results_u["U18.3"].coverage_state, CoverageState.COVERED)

        # Test C19.III
        report_c = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-UNRESOLVED-C",
            framework="COLLEGE_2026",
            institution_id="C-4001",
            subcriterion_codes=["C19.III"],
        )
        sub_c19 = report_c.parameters[0].subcriteria[0]
        self.assertEqual(sub_c19.coverage_state, CoverageState.UNRESOLVED)
        self.assertIn(CoverageDeficiencyCode.CONTRACT_UNRESOLVED.value, sub_c19.deficiency_codes)
        self.assertNotEqual(sub_c19.coverage_state, CoverageState.COVERED)

    # =========================================================================
    # PHASE 5 — COVERAGE / SCORING CONSISTENCY TESTS (1 THROUGH 7)
    # =========================================================================
    def test_consistency_1_valid_verified_exact_association(self):
        """
        Consistency 1: Valid verified exact association
        - coverage = COVERED
        - scoring gate = PASSED_EVIDENCE_VERIFIED (multiplier = 1.0)
        """
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-CONSISTENCY",
            evidence_type="EVID_U7_APPOINTMENT",
        )
        self._associate(
            doc=doc,
            parameter_id="U7",
            subcriterion_id="U7.1",
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            verification_decision=VerificationDecision.VERIFIED,
        )

        # 1. Coverage
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-CONSISTENCY",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1"],
        )
        sub_cov = report.parameters[0].subcriteria[0]
        self.assertEqual(sub_cov.coverage_state, CoverageState.COVERED)

        # 2. Scoring Gate
        scoring_doc = ScoringEvidenceDoc(
            document_id=str(doc.document_id),
            document_type="EVID_U7_APPOINTMENT",
            status=ScoringEvidenceState.EVIDENCE_VERIFIED,
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            association_verified=True,
        )
        status, mult, trace = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            uploaded_docs=[scoring_doc],
            param_def=UNIVERSITY_PARAMETERS.get("U7"),
            sub_def=UNIVERSITY_PARAMETERS.get("U7", {}).get("subcriteria", {}).get("U7.1"),
        )
        self.assertEqual(status, GatingStatus.PASSED_EVIDENCE_VERIFIED)
        self.assertEqual(mult, 1.0)

    def test_consistency_2_missing_exact_association(self):
        """
        Consistency 2: Missing exact association
        - coverage != COVERED (MISSING)
        - scoring gate = FAILED_EVIDENCE_ABSENT (multiplier = 0.0)
        """
        # 1. Coverage
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-EMPTY",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1"],
        )
        sub_cov = report.parameters[0].subcriteria[0]
        self.assertNotEqual(sub_cov.coverage_state, CoverageState.COVERED)
        self.assertEqual(sub_cov.coverage_state, CoverageState.MISSING)

        # 2. Scoring Gate
        status, mult, trace = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            uploaded_docs=[],
            param_def=UNIVERSITY_PARAMETERS.get("U7"),
            sub_def=UNIVERSITY_PARAMETERS.get("U7", {}).get("subcriteria", {}).get("U7.1"),
        )
        self.assertEqual(status, GatingStatus.FAILED_EVIDENCE_ABSENT)
        self.assertEqual(mult, 0.0)

    def test_consistency_3_pending_association(self):
        """
        Consistency 3: Pending association
        - coverage != COVERED (PENDING)
        - scoring gate = PROVISIONAL_PENDING_VERIFICATION (multiplier = 0.0)
        """
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-PENDING-C",
            evidence_type="EVID_U7_APPOINTMENT",
            status=EvidenceLifecycleState.EVIDENCE_PENDING,
        )
        self._associate(
            doc=doc,
            parameter_id="U7",
            subcriterion_id="U7.1",
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            verification_decision=None,
        )

        # 1. Coverage
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-PENDING-C",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1"],
        )
        sub_cov = report.parameters[0].subcriteria[0]
        self.assertNotEqual(sub_cov.coverage_state, CoverageState.COVERED)
        self.assertEqual(sub_cov.coverage_state, CoverageState.PENDING)

        # 2. Scoring Gate
        scoring_doc = ScoringEvidenceDoc(
            document_id=str(doc.document_id),
            document_type="EVID_U7_APPOINTMENT",
            status=ScoringEvidenceState.EVIDENCE_PENDING,
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            association_verified=None,
        )
        status, mult, trace = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            uploaded_docs=[scoring_doc],
            param_def=UNIVERSITY_PARAMETERS.get("U7"),
            sub_def=UNIVERSITY_PARAMETERS.get("U7", {}).get("subcriteria", {}).get("U7.1"),
        )
        self.assertEqual(status, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)
        self.assertEqual(mult, 0.0)

    def test_consistency_4_rejected_association(self):
        """
        Consistency 4: Rejected association
        - coverage != COVERED (REJECTED)
        - scoring gate = FAILED_EVIDENCE_REJECTED (multiplier = 0.0)
        """
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-REJECT-C",
            evidence_type="EVID_U7_APPOINTMENT",
        )
        self._associate(
            doc=doc,
            parameter_id="U7",
            subcriterion_id="U7.1",
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            verification_decision=VerificationDecision.REJECTED,
            rejection_code=RejectionReasonCode.INCOMPLETE_DOCUMENTATION,
        )

        # 1. Coverage
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-REJECT-C",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1"],
        )
        sub_cov = report.parameters[0].subcriteria[0]
        self.assertNotEqual(sub_cov.coverage_state, CoverageState.COVERED)
        self.assertEqual(sub_cov.coverage_state, CoverageState.REJECTED)

        # 2. Scoring Gate
        scoring_doc = ScoringEvidenceDoc(
            document_id=str(doc.document_id),
            document_type="EVID_U7_APPOINTMENT",
            status=ScoringEvidenceState.EVIDENCE_REJECTED,
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            association_verified=False,
        )
        status, mult, trace = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            uploaded_docs=[scoring_doc],
            param_def=UNIVERSITY_PARAMETERS.get("U7"),
            sub_def=UNIVERSITY_PARAMETERS.get("U7", {}).get("subcriteria", {}).get("U7.1"),
        )
        self.assertEqual(status, GatingStatus.FAILED_EVIDENCE_REJECTED)
        self.assertEqual(mult, 0.0)

    def test_consistency_5_wrong_evidence_type(self):
        """
        Consistency 5: Wrong evidence type
        - coverage != COVERED
        - scoring gate = FAILED_EVIDENCE_ABSENT (multiplier = 0.0)
        """
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-WRONG-TYPE",
            evidence_type="EVID_U10_REG_CERT",  # Wrong type for U7.1
        )
        self._associate(
            doc=doc,
            parameter_id="U7",
            subcriterion_id="U7.1",
            subcriterion_evidence_type="EVID_U10_REG_CERT",
            verification_decision=VerificationDecision.VERIFIED,
        )

        # 1. Coverage
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-WRONG-TYPE",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1"],
        )
        sub_cov = report.parameters[0].subcriteria[0]
        self.assertNotEqual(sub_cov.coverage_state, CoverageState.COVERED)

        # 2. Scoring Gate
        scoring_doc = ScoringEvidenceDoc(
            document_id=str(doc.document_id),
            document_type="EVID_U10_REG_CERT",
            status=ScoringEvidenceState.EVIDENCE_VERIFIED,
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            association_verified=True,
        )
        status, mult, trace = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            uploaded_docs=[scoring_doc],
            param_def=UNIVERSITY_PARAMETERS.get("U7"),
            sub_def=UNIVERSITY_PARAMETERS.get("U7", {}).get("subcriteria", {}).get("U7.1"),
        )
        self.assertEqual(status, GatingStatus.FAILED_EVIDENCE_ABSENT)
        self.assertEqual(mult, 0.0)

    def test_consistency_6_wrong_framework(self):
        """
        Consistency 6: Wrong framework
        - coverage != COVERED
        - scoring gate = FAILED_EVIDENCE_ABSENT (multiplier = 0.0)
        """
        doc = self._create_doc(
            framework="COLLEGE_2026",
            institution_id="UNIV-001",
            assessment_id="ASSESS-WRONG-FW",
            evidence_type="EVID_U7_APPOINTMENT",
        )
        self._associate(
            doc=doc,
            parameter_id="U7",
            subcriterion_id="U7.1",
            verification_decision=VerificationDecision.VERIFIED,
        )

        # 1. Coverage
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-WRONG-FW",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-001",
            subcriterion_codes=["U7.1"],
        )
        sub_cov = report.parameters[0].subcriteria[0]
        self.assertNotEqual(sub_cov.coverage_state, CoverageState.COVERED)

        # 2. Scoring Gate
        scoring_doc = ScoringEvidenceDoc(
            document_id=str(doc.document_id),
            document_type="EVID_U7_APPOINTMENT",
            status=ScoringEvidenceState.EVIDENCE_VERIFIED,
            framework="COLLEGE_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            association_verified=True,
        )
        status, mult, trace = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            uploaded_docs=[scoring_doc],
            param_def=UNIVERSITY_PARAMETERS.get("U7"),
            sub_def=UNIVERSITY_PARAMETERS.get("U7", {}).get("subcriteria", {}).get("U7.1"),
        )
        self.assertEqual(status, GatingStatus.FAILED_EVIDENCE_ABSENT)
        self.assertEqual(mult, 0.0)

    def test_consistency_7_wrong_institution(self):
        """
        Consistency 7: Wrong institution
        - coverage != COVERED
        - scoring gate = FAILED_EVIDENCE_ABSENT (multiplier = 0.0)
        """
        # Doc uploaded for Institution A
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            institution_id="UNIV-A",
            assessment_id="ASSESS-INST-A",
            evidence_type="EVID_U7_APPOINTMENT",
        )
        self._associate(
            doc=doc,
            parameter_id="U7",
            subcriterion_id="U7.1",
            verification_decision=VerificationDecision.VERIFIED,
        )

        # 1. Coverage for Institution B
        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id="ASSESS-INST-B",
            framework="UNIVERSITY_2026",
            institution_id="UNIV-B",
            subcriterion_codes=["U7.1"],
        )
        sub_cov = report.parameters[0].subcriteria[0]
        self.assertNotEqual(sub_cov.coverage_state, CoverageState.COVERED)

        # 2. Scoring Gate with no docs for Institution B
        status, mult, trace = evaluate_subcriterion_contract_evidence(
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            uploaded_docs=[],
            param_def=UNIVERSITY_PARAMETERS.get("U7"),
            sub_def=UNIVERSITY_PARAMETERS.get("U7", {}).get("subcriteria", {}).get("U7.1"),
        )
        self.assertEqual(status, GatingStatus.FAILED_EVIDENCE_ABSENT)
        self.assertEqual(mult, 0.0)
