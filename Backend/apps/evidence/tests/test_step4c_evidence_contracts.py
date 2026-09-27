"""
NEP Excellence Awards 2026 - Step 4C Evidence Contract & Taxonomy Enforcement Test Suite

Tests Required (Tasks 13.A - 13.M):
A. U7.1 appointment evidence does not unlock U7.2/U7.3/U7.4.
B. U7.1 explicit evidence contract is recognized as valid.
C. U7.2 without an explicit valid contract does not inherit U7.1 evidence.
D. U10 society registration does not satisfy U10 funding.
E. U17 NIRF 2026 submission does not satisfy NIRF 2025 ranking.
F. C20 NAAC does not satisfy NIRF or AISHE.
G. One composite document can explicitly associate with multiple subcriteria without cross-unlocking.
H. Invalid evidence type is rejected.
I. University evidence cannot satisfy College contract.
J. College evidence cannot satisfy University contract.
K. Source-silent U6/C5/C9 remain unresolved and do not receive invented evidence policy.
L. U16/C19 Scopus and U18 workshop remain unresolved/missing rather than silently fabricated.
M. Legacy coarse evidence cannot unlock unrelated multi-subcriterion requirements.
"""
import hashlib
from datetime import date
from django.test import TestCase

from apps.authentication.models import College, User
from apps.evidence.enums import (
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
)
from apps.evidence.exceptions import (
    FrameworkMismatchError,
    MandatoryRejectionReasonError,
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
    SourceSilentSubcriterionError,
    SubcriterionEvidenceContractViolationError,
    UnknownEvidenceTypeError,
    UnresolvedEvidenceRequirementError,
    derive_or_validate_evidence_type,
    get_allowed_evidence_types,
    get_subcriterion_contract,
    validate_subcriterion_evidence_contract,
    ALL_EVIDENCE_TYPES,
    EvidenceTypeFrameworkMismatchError,
    EvidenceTypeParameterMismatchError,
    LEGACY_COARSE_EVIDENCE_TYPES,
    MULTI_SUBCRITERION_PARAMETERS,
    SINGLE_SUBCRITERION_PARAMETERS,
)
from apps.scoring.enums import EvidenceState as ScoringEvidenceState


class TestStep4CEvidenceContracts(TestCase):
    """
    Focused verification of Step 4C: Evidence Contract & Taxonomy Enforcement Layer.
    """

    def setUp(self):
        super().setUp()
        self.college = College.objects.create(name="Govt College Rohtak", aishe_code="C-7001")
        self.univ_user = User.objects.create_user(
            email="registrar.step4c@haryana.gov.in",
            full_name="Registrar MDU",
            role="principal",
            password="SecurePassword123!",
        )
        self.coll_user = User.objects.create_user(
            email="principal.step4c@haryana.gov.in",
            full_name="Principal GC Rohtak",
            role="principal",
            college=self.college,
            password="SecurePassword123!",
        )
        self.reviewer = User.objects.create_user(
            email="reviewer.step4c@haryana.gov.in",
            full_name="Committee Reviewer",
            role="committee",
            password="SecurePassword123!",
        )
        self.admin = User.objects.create_superuser(
            email="admin.step4c@haryana.gov.in",
            full_name="Admin",
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

        self.sample_bytes = b"%PDF-1.4 Mock NEP 2026 Step 4C PDF Content\n%%EOF"
        self.sample_checksum = hashlib.sha256(self.sample_bytes).hexdigest()

    def _create_doc(self, framework="UNIVERSITY_2026", evidence_type="EVID_U7_APPOINTMENT", filename="doc.pdf"):
        user = self.univ_user if framework == "UNIVERSITY_2026" else self.coll_user
        inst_type = "UNIVERSITY" if framework == "UNIVERSITY_2026" else "COLLEGE"
        inst_id = "UNIV-01" if framework == "UNIVERSITY_2026" else "C-7001"
        return EvidenceService.create_evidence(
            uploader=user,
            assessment_id="ASSESS-2026-STEP4C",
            framework=framework,
            institution_type=inst_type,
            institution_id=inst_id,
            original_filename=filename,
            file_bytes=self.sample_bytes,
            mime_type="application/pdf",
            evidence_type=evidence_type,
            document_date=date(2025, 10, 1),
            academic_year="2025-26",
        )

    # =========================================================================
    # TEST A: U7.1 appointment evidence does not unlock U7.2/U7.3/U7.4
    # =========================================================================
    def test_a_u7_appointment_does_not_unlock_siblings(self):
        """
        Appointment evidence (EVID_U7_APPOINTMENT) is valid ONLY for U7.1.
        It must not be allowed for or unlock U7.2, U7.3, or U7.4.
        """
        # 1. Allowed evidence for U7.1 vs siblings
        u71_allowed = get_allowed_evidence_types("UNIVERSITY_2026", "U7", "U7.1")
        u72_allowed = get_allowed_evidence_types("UNIVERSITY_2026", "U7", "U7.2")
        u73_allowed = get_allowed_evidence_types("UNIVERSITY_2026", "U7", "U7.3")
        u74_allowed = get_allowed_evidence_types("UNIVERSITY_2026", "U7", "U7.4")

        self.assertIn("EVID_U7_APPOINTMENT", u71_allowed)
        self.assertNotIn("EVID_U7_APPOINTMENT", u72_allowed)
        self.assertNotIn("EVID_U7_APPOINTMENT", u73_allowed)
        self.assertNotIn("EVID_U7_APPOINTMENT", u74_allowed)

        # 2. Attempting validation of EVID_U7_APPOINTMENT for siblings must be rejected
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract(
                "UNIVERSITY_2026", "U7", "U7.2", "EVID_U7_APPOINTMENT"
            )
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract(
                "UNIVERSITY_2026", "U7", "U7.3", "EVID_U7_APPOINTMENT"
            )
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract(
                "UNIVERSITY_2026", "U7", "U7.4", "EVID_U7_APPOINTMENT"
            )

        # 3. Attempting association of appointment doc to U7.2 without specific subcriterion evidence type must fail
        doc = self._create_doc(framework="UNIVERSITY_2026", evidence_type="EVID_U7_APPOINTMENT")
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            EvidenceService.associate_subcriterion(
                evidence_id=doc.pk,
                parameter_id="U7",
                subcriterion_id="U7.2",
                actor=self.univ_user,
            )

    # =========================================================================
    # TEST B: U7.1 explicit evidence contract is recognized as valid
    # =========================================================================
    def test_b_u71_explicit_evidence_contract_valid(self):
        """
        U7.1 explicit evidence contract must be fully populated and active.
        """
        contract = get_subcriterion_contract("UNIVERSITY_2026", "U7", "U7.1")
        self.assertIsNotNone(contract)
        self.assertEqual(contract.status, ContractStatus.ACTIVE)
        self.assertEqual(contract.canonical_evidence_type, "EVID_U7_APPOINTMENT")
        self.assertIn("EVID_U7_APPOINTMENT", contract.allowed_evidence_types)
        self.assertIsNotNone(contract.source_documentary_requirement)
        self.assertIsNotNone(contract.score_unlock_requirement)

        # Validation succeeds
        validated = validate_subcriterion_evidence_contract(
            "UNIVERSITY_2026", "U7", "U7.1", "EVID_U7_APPOINTMENT"
        )
        self.assertEqual(validated.canonical_evidence_type, "EVID_U7_APPOINTMENT")

        # Association succeeds
        doc = self._create_doc(framework="UNIVERSITY_2026", evidence_type="EVID_U7_APPOINTMENT")
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.univ_user,
        )
        self.assertEqual(assoc.subcriterion_evidence_type, "EVID_U7_APPOINTMENT")

    # =========================================================================
    # TEST C: U7.2 without explicit valid contract does not inherit U7.1 evidence
    # =========================================================================
    def test_c_u72_no_fallback_to_u71(self):
        """
        Absence of a matching contract for a multi-subcriterion parameter
        must FAIL CLOSED, returning [] and never inheriting from parameter level.
        """
        # Nonexistent subcriterion under U7 fails closed
        allowed_fake = get_allowed_evidence_types("UNIVERSITY_2026", "U7", "U7.99")
        self.assertEqual(allowed_fake, [])

        with self.assertRaises(SubcriterionEvidenceContractViolationError):
            validate_subcriterion_evidence_contract(
                "UNIVERSITY_2026", "U7", "U7.99", "EVID_U7_APPOINTMENT"
            )

        # U7.2 allowed types do NOT contain U7.1 evidence
        allowed_u72 = get_allowed_evidence_types("UNIVERSITY_2026", "U7", "U7.2")
        self.assertEqual(allowed_u72, ["EVID_U7_TEACHING_LOGS"])
        self.assertNotIn("EVID_U7_APPOINTMENT", allowed_u72)

    # =========================================================================
    # TEST D: U10 society registration does not satisfy U10 funding
    # =========================================================================
    def test_d_u10_society_registration_does_not_satisfy_funding(self):
        """
        Society registration (EVID_U10_REG_CERT) satisfies U10.1,
        but must NOT satisfy U10.3 (funding proof requires EVID_U10_FINANCIAL_RECORDS).
        """
        contract_u101 = get_subcriterion_contract("UNIVERSITY_2026", "U10", "U10.1")
        self.assertEqual(contract_u101.canonical_evidence_type, "EVID_U10_REG_CERT")

        contract_u103 = get_subcriterion_contract("UNIVERSITY_2026", "U10", "U10.3")
        self.assertEqual(contract_u103.canonical_evidence_type, "EVID_U10_FINANCIAL_RECORDS")

        # Validation of society reg against U10.3 must fail with QuarantinedLegacyEvidenceError
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract(
                "UNIVERSITY_2026", "U10", "U10.3", "EVID_U10_REG_CERT"
            )

        # Valid financial records against U10.3 succeeds
        validated = validate_subcriterion_evidence_contract(
            "UNIVERSITY_2026", "U10", "U10.3", "EVID_U10_FINANCIAL_RECORDS"
        )
        self.assertEqual(validated.canonical_evidence_type, "EVID_U10_FINANCIAL_RECORDS")

    # =========================================================================
    # TEST E: U17 NIRF 2026 submission does not satisfy NIRF 2025 ranking
    # =========================================================================
    def test_e_u17_nirf_2026_submission_does_not_satisfy_2025_rank(self):
        """
        NIRF 2026 application submission proof (EVID_U17_NIRF_2026_PROOF) satisfies U17.1,
        but must NOT satisfy U17.2 (NIRF 2025 rank card requires EVID_U17_NIRF_2025_RANK).
        """
        contract_u171 = get_subcriterion_contract("UNIVERSITY_2026", "U17", "U17.1")
        self.assertEqual(contract_u171.canonical_evidence_type, "EVID_U17_NIRF_2026_PROOF")

        contract_u172 = get_subcriterion_contract("UNIVERSITY_2026", "U17", "U17.2")
        self.assertEqual(contract_u172.canonical_evidence_type, "EVID_U17_NIRF_2025_RANK")

        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract(
                "UNIVERSITY_2026", "U17", "U17.2", "EVID_U17_NIRF_2026_PROOF"
            )

        validated = validate_subcriterion_evidence_contract(
            "UNIVERSITY_2026", "U17", "U17.2", "EVID_U17_NIRF_2025_RANK"
        )
        self.assertEqual(validated.canonical_evidence_type, "EVID_U17_NIRF_2025_RANK")

    # =========================================================================
    # TEST F: C20 NAAC does not satisfy NIRF or AISHE
    # =========================================================================
    def test_f_c20_naac_does_not_satisfy_nirf_or_aishe(self):
        """
        NAAC accreditation certificate (EVID_C20_NAAC_CERT) satisfies C20.1,
        but must NOT satisfy C20.2 (NIRF), C20.3 (AISHE), or C20.4 (IQAC).
        """
        contract_c201 = get_subcriterion_contract("COLLEGE_2026", "C20", "C20.1")
        self.assertEqual(contract_c201.canonical_evidence_type, "EVID_C20_NAAC_CERT")

        # Quarantined from C20.2 (NIRF)
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract(
                "COLLEGE_2026", "C20", "C20.2", "EVID_C20_NAAC_CERT"
            )

        # Quarantined from C20.3 (AISHE)
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract(
                "COLLEGE_2026", "C20", "C20.3", "EVID_C20_NAAC_CERT"
            )

        # Quarantined from C20.4 (IQAC)
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract(
                "COLLEGE_2026", "C20", "C20.4", "EVID_C20_NAAC_CERT"
            )

        # Respective canonical evidence types succeed
        self.assertEqual(
            validate_subcriterion_evidence_contract("COLLEGE_2026", "C20", "C20.2", "EVID_C20_NIRF_PROOF").canonical_evidence_type,
            "EVID_C20_NIRF_PROOF"
        )
        self.assertEqual(
            validate_subcriterion_evidence_contract("COLLEGE_2026", "C20", "C20.3", "EVID_C20_AISHE_CERT").canonical_evidence_type,
            "EVID_C20_AISHE_CERT"
        )
        self.assertEqual(
            validate_subcriterion_evidence_contract("COLLEGE_2026", "C20", "C20.4", "EVID_C20_IQAC_MINUTES").canonical_evidence_type,
            "EVID_C20_IQAC_MINUTES"
        )

    # =========================================================================
    # TEST G: One composite document can explicitly associate with multiple subcriteria without cross-unlocking
    # =========================================================================
    def test_g_composite_document_independent_associations_no_cross_unlock(self):
        """
        Legitimate document reuse:
        A single physical document can associate to both U7.1 and U7.2 with explicit subcriterion_evidence_types.
        Verifying Association 1 (U7.1) must NOT automatically verify or unlock Association 2 (U7.2).
        """
        doc = self._create_doc(
            framework="UNIVERSITY_2026",
            evidence_type="EVID_U7_APPOINTMENT",
            filename="comprehensive_pop_dossier.pdf"
        )

        # Association 1: U7.1 (pages 1-5, Appointment letter)
        assoc1 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.univ_user,
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            page_start=1,
            page_end=5,
            section_identifier="Part-A: Appointment Letter",
            claim_description="Official Government appointment orders for PoP.",
        )

        # Association 2: U7.2 (pages 6-20, Teaching logs)
        assoc2 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.2",
            actor=self.univ_user,
            subcriterion_evidence_type="EVID_U7_TEACHING_LOGS",
            page_start=6,
            page_end=20,
            section_identifier="Part-B: Teaching and Interaction Logs",
            claim_description="Detailed logs of 45 hours student engagement.",
        )

        self.assertEqual(doc.associations.count(), 2)
        self.assertEqual(assoc1.subcriterion_evidence_type, "EVID_U7_APPOINTMENT")
        self.assertEqual(assoc2.subcriterion_evidence_type, "EVID_U7_TEACHING_LOGS")

        # Prior to verification, scoring domain sees both as pending/present
        scoring_assoc1_init = EvidenceService.to_scoring_domain(assoc1)
        scoring_assoc2_init = EvidenceService.to_scoring_domain(assoc2)
        self.assertEqual(scoring_assoc1_init.document_type, "EVID_U7_APPOINTMENT")
        self.assertEqual(scoring_assoc2_init.document_type, "EVID_U7_TEACHING_LOGS")
        self.assertNotEqual(scoring_assoc1_init.status, ScoringEvidenceState.EVIDENCE_VERIFIED)
        self.assertNotEqual(scoring_assoc2_init.status, ScoringEvidenceState.EVIDENCE_VERIFIED)

        # Reviewer verifies Association 1 ONLY
        v1 = EvidenceService.verify_association(
            association_id=assoc1.pk,
            verifier=self.reviewer,
            reason="Appointment letter verified authentic",
        )
        self.assertEqual(v1.decision, VerificationDecision.VERIFIED)

        # Association 1 is now verified
        scoring_assoc1_post = EvidenceService.to_scoring_domain(assoc1)
        self.assertEqual(scoring_assoc1_post.status, ScoringEvidenceState.EVIDENCE_VERIFIED)

        # Association 2 MUST STILL BE UNVERIFIED (NO cross-unlocking!)
        scoring_assoc2_post = EvidenceService.to_scoring_domain(assoc2)
        self.assertNotEqual(
            scoring_assoc2_post.status,
            ScoringEvidenceState.EVIDENCE_VERIFIED,
            "Verification of Association 1 must NOT unlock Association 2!"
        )

        # Now reviewer rejects Association 2 due to insufficient hours
        v2 = EvidenceService.reject_association(
            association_id=assoc2.pk,
            verifier=self.reviewer,
            reason="Teaching logs only reflect 22 hours, minimum 40 required.",
            rejection_code=RejectionReasonCode.INCOMPLETE_DOCUMENTATION,
        )
        self.assertEqual(v2.decision, VerificationDecision.REJECTED)

        # Association 2 is rejected
        scoring_assoc2_final = EvidenceService.to_scoring_domain(assoc2)
        self.assertEqual(scoring_assoc2_final.status, ScoringEvidenceState.EVIDENCE_REJECTED)

        # Association 1 STILL REMAINS VERIFIED
        scoring_assoc1_final = EvidenceService.to_scoring_domain(assoc1)
        self.assertEqual(scoring_assoc1_final.status, ScoringEvidenceState.EVIDENCE_VERIFIED)

    # =========================================================================
    # TEST H: Invalid evidence type is rejected
    # =========================================================================
    def test_h_invalid_evidence_type_rejected(self):
        """
        Unrecognized strings and EVID_GENERAL must be strictly rejected.
        """
        with self.assertRaises(UnknownEvidenceTypeError):
            validate_subcriterion_evidence_contract(
                "UNIVERSITY_2026", "U7", "U7.1", "EVID_COMPLETELY_FABRICATED"
            )

        with self.assertRaises(UnknownEvidenceTypeError):
            validate_subcriterion_evidence_contract(
                "UNIVERSITY_2026", "U7", "U7.1", "EVID_GENERAL"
            )

        with self.assertRaises(UnknownEvidenceTypeError):
            derive_or_validate_evidence_type(
                "UNIVERSITY_2026",
                evidence_type="EVID_COMPLETELY_FABRICATED",
                parameter_id="U7",
                subcriterion_id="U7.1",
            )

    # =========================================================================
    # TEST I: University evidence cannot satisfy College contract
    # =========================================================================
    def test_i_university_evidence_cannot_satisfy_college_contract(self):
        """
        Framework isolation: University evidence types and documents
        cannot satisfy College contracts.
        """
        # Evidence type mismatch
        with self.assertRaises(EvidenceTypeFrameworkMismatchError):
            validate_subcriterion_evidence_contract(
                "COLLEGE_2026", "C1", "C1.1", "EVID_U1_APPROVAL"
            )

        # Association mismatch
        univ_doc = self._create_doc(framework="UNIVERSITY_2026", evidence_type="EVID_U1_APPROVAL")
        with self.assertRaises(FrameworkMismatchError):
            EvidenceService.associate_subcriterion(
                evidence_id=univ_doc.pk,
                parameter_id="C1",
                subcriterion_id="C1.1",
                actor=self.univ_user,
            )

    # =========================================================================
    # TEST J: College evidence cannot satisfy University contract
    # =========================================================================
    def test_j_college_evidence_cannot_satisfy_university_contract(self):
        """
        Framework isolation: College evidence types and documents
        cannot satisfy University contracts.
        """
        # Evidence type mismatch
        with self.assertRaises(EvidenceTypeFrameworkMismatchError):
            validate_subcriterion_evidence_contract(
                "UNIVERSITY_2026", "U1", "U1.1", "EVID_C1_APPROVED_IDP"
            )

        # Association mismatch
        coll_doc = self._create_doc(framework="COLLEGE_2026", evidence_type="EVID_C1_APPROVED_IDP")
        with self.assertRaises(FrameworkMismatchError):
            EvidenceService.associate_subcriterion(
                evidence_id=coll_doc.pk,
                parameter_id="U1",
                subcriterion_id="U1.1",
                actor=self.coll_user,
            )

    # =========================================================================
    # TEST K: Source-silent U6/C5/C9 remain unresolved and do not receive invented evidence policy
    # =========================================================================
    def test_k_source_silent_subcriteria_preserved(self):
        """
        U6 (University Academic Reforms), C5 (College Student Enrollment),
        and C9 (College Career Orientation) have NO evidence requirement in source PDF.
        They must remain explicitly marked as SOURCE_SILENT.
        No evidence may be submitted, derived, or associated (fail closed).
        """
        for fw, param, subs in [
            ("UNIVERSITY_2026", "U6", ["U6.A", "U6.B", "U6.1", "U6.2"]),
            ("COLLEGE_2026", "C5", ["C5.1"]),
            ("COLLEGE_2026", "C9", ["C9.I", "C9.II", "C9.1", "C9.2"]),
        ]:
            for s in subs:
                contract = get_subcriterion_contract(fw, param, s)
                self.assertIsNotNone(contract, f"Contract for {param}:{s} must exist.")
                self.assertEqual(contract.status, ContractStatus.SOURCE_SILENT)
                self.assertTrue(contract.is_source_silent)
                self.assertIsNone(contract.canonical_evidence_type)
                self.assertEqual(contract.allowed_evidence_types, ())

                # get_allowed_evidence_types must return []
                allowed = get_allowed_evidence_types(fw, param, s)
                self.assertEqual(allowed, [])

                # Attempting validation must raise SourceSilentSubcriterionError
                with self.assertRaises(SourceSilentSubcriterionError):
                    validate_subcriterion_evidence_contract(fw, param, s, "EVID_ANY")

                # Derivation must raise SourceSilentSubcriterionError
                with self.assertRaises(SourceSilentSubcriterionError):
                    derive_or_validate_evidence_type(fw, parameter_id=param, subcriterion_id=s)

    # =========================================================================
    # TEST L: U16/C19 Scopus and U18 workshop remain unresolved/missing
    # =========================================================================
    def test_l_unresolved_missing_evidence_preserved(self):
        """
        U16.III (University Scopus), C19.III (College Scopus), and U18.3 (RPL workshop)
        have metrics mentioned in source text but the documentary evidence section is silent.
        These must remain explicitly marked as UNRESOLVED_MISSING (no fabricated identifiers).
        """
        for fw, param, sub in [
            ("UNIVERSITY_2026", "U16", "U16.III"),
            ("COLLEGE_2026", "C19", "C19.III"),
            ("UNIVERSITY_2026", "U18", "U18.3"),
        ]:
            contract = get_subcriterion_contract(fw, param, sub)
            self.assertIsNotNone(contract, f"Contract for {param}:{sub} must exist.")
            self.assertEqual(contract.status, ContractStatus.UNRESOLVED_MISSING)
            self.assertTrue(contract.is_unresolved)
            self.assertIsNone(contract.canonical_evidence_type)
            self.assertEqual(contract.allowed_evidence_types, ())

            allowed = get_allowed_evidence_types(fw, param, sub)
            self.assertEqual(allowed, [])

            with self.assertRaises(UnresolvedEvidenceRequirementError):
                validate_subcriterion_evidence_contract(fw, param, sub, "EVID_ANY")

            with self.assertRaises(UnresolvedEvidenceRequirementError):
                derive_or_validate_evidence_type(fw, parameter_id=param, subcriterion_id=sub)

    # =========================================================================
    # TEST M: Legacy coarse evidence cannot unlock unrelated multi-subcriterion requirements
    # =========================================================================
    def test_m_legacy_coarse_evidence_quarantine(self):
        """
        Legacy coarse evidence identifiers must be quarantined from unlocking
        unrelated multi-subcriterion requirements.
        """
        # Verify quarantine registry contains expected coarse identifiers
        self.assertIn("EVID_U7_APPOINTMENT", LEGACY_COARSE_EVIDENCE_TYPES)
        self.assertIn("EVID_U10_REG_CERT", LEGACY_COARSE_EVIDENCE_TYPES)
        self.assertIn("EVID_U17_NIRF_2026_PROOF", LEGACY_COARSE_EVIDENCE_TYPES)
        self.assertIn("EVID_C20_NAAC_CERT", LEGACY_COARSE_EVIDENCE_TYPES)

        # U7: Appointment cannot satisfy teaching logs or workshops
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract("UNIVERSITY_2026", "U7", "U7.2", "EVID_U7_APPOINTMENT")
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract("UNIVERSITY_2026", "U7", "U7.3", "EVID_U7_APPOINTMENT")

        # U10: Registration cert cannot satisfy funding or guest lectures
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract("UNIVERSITY_2026", "U10", "U10.3", "EVID_U10_REG_CERT")
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract("UNIVERSITY_2026", "U10", "U10.4", "EVID_U10_REG_CERT")

        # U17: NIRF 2026 submission cannot satisfy NIRF 2025 ranking
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract("UNIVERSITY_2026", "U17", "U17.2", "EVID_U17_NIRF_2026_PROOF")

        # C20: NAAC cert cannot satisfy NIRF, AISHE, or IQAC
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract("COLLEGE_2026", "C20", "C20.2", "EVID_C20_NAAC_CERT")
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract("COLLEGE_2026", "C20", "C20.3", "EVID_C20_NAAC_CERT")
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            validate_subcriterion_evidence_contract("COLLEGE_2026", "C20", "C20.4", "EVID_C20_NAAC_CERT")
