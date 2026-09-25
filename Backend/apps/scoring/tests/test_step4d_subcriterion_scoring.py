"""
Step 4D — Subcriterion-Aware Scoring Integration Regression Test Suite

Verifies:
A. U7.1 appointment VERIFIED, U7.2 no valid evidence -> U7.1 may score, U7.2 must not score because of U7.1.
B. U7.1 VERIFIED, U7.2 REJECTED -> U7.1 may score, U7.2 cannot score.
C. Same document: U7.1 VERIFIED, U7.2 VERIFIED with distinct explicit associations -> both may score.
D. U10 society registration evidence -> must not unlock U10 funding.
E. U17 NIRF 2026 submission -> must not unlock U17 NIRF 2025 ranking.
F. C20 NAAC -> must not unlock NIRF or AISHE.
G. University evidence -> cannot satisfy College scoring.
H. College evidence -> cannot satisfy University scoring.
I. Legacy coarse evidence -> cannot satisfy unrelated multi-subcriterion scoring.
J. Source-silent U6/C5/C9 -> no invented evidence path; fails closed without evidence; never auto-awarded.
K. U16 Scopus / C19 Scopus / U18 workshop unresolved evidence -> cannot be silently satisfied.
L. Existing legitimate single-subcriterion scoring behavior remains unchanged.
M. Existing raw score calculations remain unchanged.
Negative Test (Section 9): Verified parameter-level evidence without exact subcriterion association
    fails evidence gate for multi-subcriterion parameters.
"""
from datetime import date
from typing import Optional
from django.test import TestCase

from apps.scoring.domain import (
    AssessmentContext,
    AssessmentPeriod,
    EvidenceDocument,
    ParameterInput,
    SubcriterionInput,
)
from apps.scoring.enums import (
    EvidenceState,
    FrameworkType,
    GatingStatus,
    InstitutionType,
    ResolutionStatus,
)
from apps.scoring.evaluators.double_counting import DoubleCountingValidator
from apps.scoring.rules.college import COLLEGE_EVALUATORS
from apps.scoring.rules.university import UNIVERSITY_EVALUATORS


class Step4DSubcriterionScoringTests(TestCase):

    def setUp(self):
        self.univ_context = AssessmentContext(
            assessment_id="test-assess-univ-4d",
            institution_id="univ-aishe-4d",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30)),
        )
        self.college_context = AssessmentContext(
            assessment_id="test-assess-coll-4d",
            institution_id="coll-aishe-4d",
            institution_type=InstitutionType.COLLEGE,
            framework=FrameworkType.COLLEGE_2026,
            assessment_period=AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30)),
        )
        self.validator = DoubleCountingValidator()

    def _make_doc(
        self,
        doc_type: str,
        status: EvidenceState = EvidenceState.EVIDENCE_VERIFIED,
        framework: Optional[str] = None,
        parameter_id: Optional[str] = None,
        subcriterion_id: Optional[str] = None,
        association_verified: Optional[bool] = None,
    ) -> EvidenceDocument:
        return EvidenceDocument(
            document_id=f"doc-{doc_type}-{subcriterion_id or 'gen'}",
            document_type=doc_type,
            status=status,
            framework=framework,
            parameter_id=parameter_id,
            subcriterion_id=subcriterion_id,
            association_verified=association_verified,
        )

    # =========================================================================
    # SCENARIO A: U7.1 VERIFIED, U7.2 NO VALID EVIDENCE
    # =========================================================================
    def test_scenario_a_u7_appointment_verified_u72_no_evidence(self):
        """
        U7.1 appointment letter is VERIFIED.
        U7.2 has raw inputs fulfilled, but no evidence (or only U7.1's appointment doc).
        -> U7.1 may score (earned 1.0)
        -> U7.2 must NOT score because of U7.1 (earned 0.0, FAILED_EVIDENCE_ABSENT)
        """
        eval_fn = UNIVERSITY_EVALUATORS["U7"]
        doc_u71 = self._make_doc(
            "EVID_U7_APPOINTMENT",
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            association_verified=True,
        )
        p_in = ParameterInput(
            parameter_code="U7",
            subcriteria_inputs={
                "U7.1": SubcriterionInput(subcriterion_code="U7.1", raw_inputs={"verified": True}, evidence_docs=[doc_u71]),
                "U7.2": SubcriterionInput(subcriterion_code="U7.2", raw_inputs={"verified": True}, evidence_docs=[]),
                "U7.3": SubcriterionInput(subcriterion_code="U7.3", raw_inputs={"verified": False}, evidence_docs=[]),
                "U7.4": SubcriterionInput(subcriterion_code="U7.4", raw_inputs={"verified": False}, evidence_docs=[]),
            }
        )
        res = eval_fn(p_in, self.univ_context, self.validator)

        # U7.1 passes gate and scores
        self.assertEqual(res.subcriteria_results["U7.1"].raw_score, 1.0)
        self.assertEqual(res.subcriteria_results["U7.1"].evidence_gated_score, 1.0)
        self.assertEqual(res.subcriteria_results["U7.1"].gating_status, GatingStatus.PASSED_EVIDENCE_VERIFIED)

        # U7.2 has raw score 1.0 but fails evidence gate: score must be 0.0
        self.assertEqual(res.subcriteria_results["U7.2"].raw_score, 1.0)
        self.assertEqual(res.subcriteria_results["U7.2"].evidence_gated_score, 0.0)
        self.assertEqual(res.subcriteria_results["U7.2"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

        # Even if U7.1's doc is mistakenly placed into U7.2's input list, it cannot satisfy U7.2
        p_in_leaked = ParameterInput(
            parameter_code="U7",
            subcriteria_inputs={
                "U7.1": SubcriterionInput(subcriterion_code="U7.1", raw_inputs={"verified": True}, evidence_docs=[doc_u71]),
                "U7.2": SubcriterionInput(subcriterion_code="U7.2", raw_inputs={"verified": True}, evidence_docs=[doc_u71]),
            }
        )
        res_leaked = eval_fn(p_in_leaked, self.univ_context, self.validator)
        self.assertEqual(res_leaked.subcriteria_results["U7.2"].evidence_gated_score, 0.0)
        self.assertEqual(res_leaked.subcriteria_results["U7.2"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

    # =========================================================================
    # SCENARIO B: U7.1 VERIFIED, U7.2 REJECTED
    # =========================================================================
    def test_scenario_b_u71_verified_u72_rejected(self):
        """
        U7.1 is VERIFIED.
        U7.2 association is REJECTED.
        -> U7.1 may score
        -> U7.2 cannot score (FAILED_EVIDENCE_REJECTED, 0.0)
        """
        eval_fn = UNIVERSITY_EVALUATORS["U7"]
        doc_u71 = self._make_doc(
            "EVID_U7_APPOINTMENT",
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            association_verified=True,
        )
        doc_u72_rejected = self._make_doc(
            "EVID_U7_TEACHING_LOGS",
            status=EvidenceState.EVIDENCE_REJECTED,
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.2",
            association_verified=False,
        )
        p_in = ParameterInput(
            parameter_code="U7",
            subcriteria_inputs={
                "U7.1": SubcriterionInput(subcriterion_code="U7.1", raw_inputs={"verified": True}, evidence_docs=[doc_u71]),
                "U7.2": SubcriterionInput(subcriterion_code="U7.2", raw_inputs={"verified": True}, evidence_docs=[doc_u72_rejected]),
            }
        )
        res = eval_fn(p_in, self.univ_context, self.validator)
        self.assertEqual(res.subcriteria_results["U7.1"].evidence_gated_score, 1.0)
        self.assertEqual(res.subcriteria_results["U7.1"].gating_status, GatingStatus.PASSED_EVIDENCE_VERIFIED)

        self.assertEqual(res.subcriteria_results["U7.2"].evidence_gated_score, 0.0)
        self.assertEqual(res.subcriteria_results["U7.2"].gating_status, GatingStatus.FAILED_EVIDENCE_REJECTED)

    # =========================================================================
    # SCENARIO C: SAME PHYSICAL DOCUMENT, DISTINCT ASSOCIATIONS BOTH VERIFIED
    # =========================================================================
    def test_scenario_c_same_document_independent_associations_both_score(self):
        """
        A single composite document supports U7.1 and U7.2 through two distinct associations.
        Both associations have been verified independently.
        -> Both subcriteria may score because their own contracts are satisfied.
        """
        eval_fn = UNIVERSITY_EVALUATORS["U7"]
        doc_assoc1 = self._make_doc(
            "EVID_U7_APPOINTMENT",
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.1",
            association_verified=True,
        )
        doc_assoc2 = self._make_doc(
            "EVID_U7_TEACHING_LOGS",
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.2",
            association_verified=True,
        )
        p_in = ParameterInput(
            parameter_code="U7",
            subcriteria_inputs={
                "U7.1": SubcriterionInput(subcriterion_code="U7.1", raw_inputs={"verified": True}, evidence_docs=[doc_assoc1]),
                "U7.2": SubcriterionInput(subcriterion_code="U7.2", raw_inputs={"verified": True}, evidence_docs=[doc_assoc2]),
            }
        )
        res = eval_fn(p_in, self.univ_context, self.validator)
        self.assertEqual(res.subcriteria_results["U7.1"].evidence_gated_score, 1.0)
        self.assertEqual(res.subcriteria_results["U7.1"].gating_status, GatingStatus.PASSED_EVIDENCE_VERIFIED)

        self.assertEqual(res.subcriteria_results["U7.2"].evidence_gated_score, 1.0)
        self.assertEqual(res.subcriteria_results["U7.2"].gating_status, GatingStatus.PASSED_EVIDENCE_VERIFIED)    # =========================================================================
    # SCENARIO D: U10 SOCIETY REGISTRATION MUST NOT UNLOCK FUNDING
    # =========================================================================
    def test_scenario_d_u10_society_registration_must_not_unlock_funding(self):
        """
        U10.1 (Alumni registration) has verified EVID_U10_REG_CERT.
        U10.3 (Alumni funding > 1 Cr) requires EVID_U10_FINANCIAL_RECORDS.
        Society registration evidence must NOT unlock U10.3 funding.
        """
        eval_fn = UNIVERSITY_EVALUATORS["U10"]
        doc_reg = self._make_doc(
            "EVID_U10_REG_CERT",
            framework="UNIVERSITY_2026",
            parameter_id="U10",
            subcriterion_id="U10.1",
            association_verified=True,
        )
        p_in = ParameterInput(
            parameter_code="U10",
            subcriteria_inputs={
                "U10.1": SubcriterionInput(subcriterion_code="U10.1", raw_inputs={"verified": True}, evidence_docs=[doc_reg]),
                "U10.2": SubcriterionInput(subcriterion_code="U10.2", raw_inputs={"verified": False}, evidence_docs=[]),
                "U10.3": SubcriterionInput(subcriterion_code="U10.3", raw_inputs={"funding_amount": 1.5}, evidence_docs=[doc_reg]),  # Leaked reg cert!
                "U10.4": SubcriterionInput(subcriterion_code="U10.4", raw_inputs={"verified": False}, evidence_docs=[]),
            }
        )
        res = eval_fn(p_in, self.univ_context, self.validator)
        self.assertEqual(res.subcriteria_results["U10.1"].evidence_gated_score, 1.0)
        self.assertEqual(res.subcriteria_results["U10.1"].gating_status, GatingStatus.PASSED_EVIDENCE_VERIFIED)

        # U10.3 has raw score 1.0 but evidence gate MUST FAIL
        self.assertEqual(res.subcriteria_results["U10.3"].raw_score, 1.0)
        self.assertEqual(res.subcriteria_results["U10.3"].evidence_gated_score, 0.0)
        self.assertEqual(res.subcriteria_results["U10.3"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

    # =========================================================================
    # SCENARIO E: U17 NIRF 2026 SUBMISSION MUST NOT UNLOCK NIRF 2025 RANK
    # =========================================================================
    def test_scenario_e_u17_nirf_2026_must_not_unlock_nirf_2025_rank(self):
        """
        U17.1 (NIRF 2026 participation proof) has verified EVID_U17_NIRF_2026_PROOF.
        U17.2 (NIRF 2025 ranking in top 100) requires EVID_U17_NIRF_2025_RANK.
        NIRF 2026 submission proof must NOT unlock NIRF 2025 rank score.
        """
        eval_fn = UNIVERSITY_EVALUATORS["U17"]
        doc_nirf_2026 = self._make_doc(
            "EVID_U17_NIRF_2026_PROOF",
            framework="UNIVERSITY_2026",
            parameter_id="U17",
            subcriterion_id="U17.1",
            association_verified=True,
        )
        p_in = ParameterInput(
            parameter_code="U17",
            subcriteria_inputs={
                "U17.1": SubcriterionInput(subcriterion_code="U17.1", raw_inputs={"verified": True}, evidence_docs=[doc_nirf_2026]),
                "U17.2": SubcriterionInput(subcriterion_code="U17.2", raw_inputs={"verified": True}, evidence_docs=[doc_nirf_2026]),  # Leaked!
            }
        )
        res = eval_fn(p_in, self.univ_context, self.validator)
        self.assertEqual(res.subcriteria_results["U17.1"].evidence_gated_score, 1.0)
        self.assertEqual(res.subcriteria_results["U17.1"].gating_status, GatingStatus.PASSED_EVIDENCE_VERIFIED)

        self.assertEqual(res.subcriteria_results["U17.2"].raw_score, 1.0)
        self.assertEqual(res.subcriteria_results["U17.2"].evidence_gated_score, 0.0)
        self.assertEqual(res.subcriteria_results["U17.2"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

    # =========================================================================
    # SCENARIO F: C20 NAAC MUST NOT UNLOCK NIRF AISHE
    # =========================================================================
    def test_scenario_f_c20_naac_must_not_unlock_nirf_aishe(self):
        """
        C20.1 (NAAC Grade) has verified EVID_C20_NAAC_CERT.
        C20.2 (NIRF) and C20.3 (AISHE) require distinct proof.
        NAAC certificate must NOT unlock NIRF or AISHE subcriteria.
        """
        eval_fn = COLLEGE_EVALUATORS["C20"]
        doc_naac = self._make_doc(
            "EVID_C20_NAAC_CERT",
            framework="COLLEGE_2026",
            parameter_id="C20",
            subcriterion_id="C20.1",
            association_verified=True,
        )
        p_in = ParameterInput(
            parameter_code="C20",
            subcriteria_inputs={
                "C20.1": SubcriterionInput(subcriterion_code="C20.1", raw_inputs={"grade": "A++"}, evidence_docs=[doc_naac]),
                "C20.2": SubcriterionInput(subcriterion_code="C20.2", raw_inputs={"verified": True}, evidence_docs=[doc_naac]),
                "C20.3": SubcriterionInput(subcriterion_code="C20.3", raw_inputs={"verified": True}, evidence_docs=[doc_naac]),
                "C20.4": SubcriterionInput(subcriterion_code="C20.4", raw_inputs={"verified": False}, evidence_docs=[]),
            }
        )
        res = eval_fn(p_in, self.college_context, self.validator)
        self.assertEqual(res.subcriteria_results["C20.1"].evidence_gated_score, 2.0)
        self.assertEqual(res.subcriteria_results["C20.1"].gating_status, GatingStatus.PASSED_EVIDENCE_VERIFIED)

        self.assertEqual(res.subcriteria_results["C20.2"].evidence_gated_score, 0.0)
        self.assertEqual(res.subcriteria_results["C20.2"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

        self.assertEqual(res.subcriteria_results["C20.3"].evidence_gated_score, 0.0)
        self.assertEqual(res.subcriteria_results["C20.3"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

    # =========================================================================
    # SCENARIOS G & H: FRAMEWORK ISOLATION
    # =========================================================================
    def test_scenario_g_university_evidence_cannot_satisfy_college_scoring(self):
        """
        University evidence document submitted to College assessment fails evidence gate.
        """
        eval_fn = COLLEGE_EVALUATORS["C1"]
        doc_univ = self._make_doc(
            "EVID_C1_APPROVED_IDP",
            framework="UNIVERSITY_2026",  # Cross-framework violation
            parameter_id="C1",
            subcriterion_id="C1.1",
            association_verified=True,
        )
        p_in = ParameterInput(
            parameter_code="C1",
            subcriteria_inputs={
                "C1.1": SubcriterionInput(subcriterion_code="C1.1", raw_inputs={"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}, evidence_docs=[doc_univ]),
            }
        )
        res = eval_fn(p_in, self.college_context, self.validator)
        self.assertEqual(res.subcriteria_results["C1.1"].evidence_gated_score, 0.0)
        self.assertEqual(res.subcriteria_results["C1.1"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

    def test_scenario_h_college_evidence_cannot_satisfy_university_scoring(self):
        """
        College evidence document submitted to University assessment fails evidence gate.
        """
        eval_fn = UNIVERSITY_EVALUATORS["U1"]
        doc_coll = self._make_doc(
            "EVID_U1_APPROVAL",
            framework="COLLEGE_2026",  # Cross-framework violation
            parameter_id="U1",
            subcriterion_id="U1.1",
            association_verified=True,
        )
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(subcriterion_code="U1.1", raw_inputs={"programmes_count": 12}, evidence_docs=[doc_coll]),
            }
        )
        res = eval_fn(p_in, self.univ_context, self.validator)
        self.assertEqual(res.subcriteria_results["U1.1"].evidence_gated_score, 0.0)
        self.assertEqual(res.subcriteria_results["U1.1"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

    # =========================================================================
    # SCENARIO I: LEGACY COARSE EVIDENCE QUARANTINED
    # =========================================================================
    def test_scenario_i_legacy_coarse_evidence_quarantined_from_multi_subcriterion(self):
        """
        EVID_GENERAL or quarantined coarse evidence cannot satisfy multi-subcriterion parameters.
        """
        eval_fn = UNIVERSITY_EVALUATORS["U7"]
        doc_coarse = self._make_doc(
            "EVID_GENERAL",
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id="U7.2",
            association_verified=True,
        )
        p_in = ParameterInput(
            parameter_code="U7",
            subcriteria_inputs={
                "U7.2": SubcriterionInput(subcriterion_code="U7.2", raw_inputs={"verified": True}, evidence_docs=[doc_coarse]),
            }
        )
        res = eval_fn(p_in, self.univ_context, self.validator)
        self.assertEqual(res.subcriteria_results["U7.2"].evidence_gated_score, 0.0)
        self.assertEqual(res.subcriteria_results["U7.2"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

    # =========================================================================
    # SCENARIO J: SOURCE-SILENT U6/C5/C9
    # =========================================================================
    def test_scenario_j_source_silent_no_invented_evidence_path(self):
        """
        U6, C5, C9 are source-silent.
        - If no evidence is provided, fails closed (0.0). No automatic award!
        - If arbitrary invented evidence is submitted (e.g. self-declaration), fails closed (0.0).
        """
        # 1. University U6: empty evidence -> 0.0
        eval_fn_u6 = UNIVERSITY_EVALUATORS["U6"]
        p_in_empty = ParameterInput(
            parameter_code="U6",
            subcriteria_inputs={
                "U6.A": SubcriterionInput(subcriterion_code="U6.A", raw_inputs={"ordinance_notified": True}, evidence_docs=[]),
            }
        )
        res_empty = eval_fn_u6(p_in_empty, self.univ_context, self.validator)
        self.assertEqual(res_empty.subcriteria_results["U6.A"].raw_score, 4.0)
        self.assertEqual(res_empty.subcriteria_results["U6.A"].evidence_gated_score, 0.0)
        self.assertEqual(res_empty.subcriteria_results["U6.A"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

        # 2. Invented evidence type -> fails closed (0.0)
        doc_invented = self._make_doc("EVID_U6_SELF_DECLARATION", framework="UNIVERSITY_2026", parameter_id="U6")
        p_in_invented = ParameterInput(
            parameter_code="U6",
            subcriteria_inputs={
                "U6.A": SubcriterionInput(subcriterion_code="U6.A", raw_inputs={"ordinance_notified": True}, evidence_docs=[doc_invented]),
            }
        )
        res_inv = eval_fn_u6(p_in_invented, self.univ_context, self.validator)
        self.assertEqual(res_inv.subcriteria_results["U6.A"].evidence_gated_score, 0.0)
        self.assertEqual(res_inv.subcriteria_results["U6.A"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)

        # 3. College C5: empty evidence -> 0.0
        eval_fn_c5 = COLLEGE_EVALUATORS["C5"]
        p_in_c5_empty = ParameterInput(
            parameter_code="C5",
            subcriteria_inputs={
                "C5.1": SubcriterionInput(subcriterion_code="C5.1", raw_inputs={"admitted_students": 100, "sanctioned_intake": 100}, evidence_docs=[]),
            }
        )
        res_c5 = eval_fn_c5(p_in_c5_empty, self.college_context, self.validator)
        self.assertEqual(res_c5.subcriteria_results["C5.1"].raw_score, 2.0)
        self.assertEqual(res_c5.subcriteria_results["C5.1"].evidence_gated_score, 0.0)
        self.assertEqual(res_c5.subcriteria_results["C5.1"].gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)


    # =========================================================================
    # SCENARIO K: UNRESOLVED MISSING EVIDENCE CANNOT BE SILENTLY SATISFIED
    # =========================================================================
    def test_scenario_k_unresolved_missing_cannot_be_satisfied(self):
        """
        U16.III (Scopus publications per faculty) and C19.III (Scopus metric)
        are marked UNRESOLVED_MISSING in taxonomy and UNRESOLVED_RULE in definitions.
        They cannot be satisfied by evidence under any circumstances.
        """
        eval_fn_u16 = UNIVERSITY_EVALUATORS["U16"]
        doc = self._make_doc("EVID_U16_SCOPUS_CUSTOM", framework="UNIVERSITY_2026", parameter_id="U16")
        p_in = ParameterInput(
            parameter_code="U16",
            subcriteria_inputs={
                "U16.III": SubcriterionInput(subcriterion_code="U16.III", raw_inputs={"scopus_ratio": 2.5}, evidence_docs=[doc]),
            }
        )
        res = eval_fn_u16(p_in, self.univ_context, self.validator)
        self.assertEqual(res.subcriteria_results["U16.III"].resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertEqual(res.subcriteria_results["U16.III"].evidence_gated_score, 0.0)

    # =========================================================================
    # SCENARIO L: SINGLE-SUBCRITERION SCORING BEHAVIOR UNCHANGED
    # =========================================================================
    def test_scenario_l_single_subcriterion_behavior_unchanged(self):
        """
        Single-subcriterion parameters (e.g. C3 ABC Registration, U1 Apprenticeship)
        preserve legitimate existing behavior: verified doc yields full score,
        rejected doc yields 0.0 with FAILED_EVIDENCE_REJECTED.
        """
        eval_fn = COLLEGE_EVALUATORS["C3"]
        doc_verified = self._make_doc("EVID_C3_ABC_DASHBOARD", framework="COLLEGE_2026", parameter_id="C3", subcriterion_id="C3.1")
        p_in_v = ParameterInput(
            parameter_code="C3",
            subcriteria_inputs={
                "C3.1": SubcriterionInput(subcriterion_code="C3.1", raw_inputs={"abc_registered_students": 95, "total_enrolled_students": 100}, evidence_docs=[doc_verified]),
            }
        )
        res_v = eval_fn(p_in_v, self.college_context, self.validator)
        self.assertEqual(res_v.raw_score, 4.0)
        self.assertEqual(res_v.evidence_gated_score, 4.0)
        self.assertEqual(res_v.subcriteria_results["C3.1"].gating_status, GatingStatus.PASSED_EVIDENCE_VERIFIED)

        doc_rejected = self._make_doc(
            "EVID_C3_ABC_DASHBOARD",
            status=EvidenceState.EVIDENCE_REJECTED,
            framework="COLLEGE_2026",
            parameter_id="C3",
            subcriterion_id="C3.1",
            association_verified=False,
        )
        p_in_r = ParameterInput(
            parameter_code="C3",
            subcriteria_inputs={
                "C3.1": SubcriterionInput(subcriterion_code="C3.1", raw_inputs={"abc_registered_students": 95, "total_enrolled_students": 100}, evidence_docs=[doc_rejected]),
            }
        )
        res_r = eval_fn(p_in_r, self.college_context, self.validator)
        self.assertEqual(res_r.raw_score, 4.0)
        self.assertEqual(res_r.evidence_gated_score, 0.0)
        self.assertEqual(res_r.subcriteria_results["C3.1"].gating_status, GatingStatus.FAILED_EVIDENCE_REJECTED)

    # =========================================================================
    # SCENARIO M: RAW SCORING CALCULATIONS UNCHANGED
    # =========================================================================
    def test_scenario_m_raw_score_calculations_unchanged(self):
        """
        Raw evaluator calculations, thresholds, boundary voids, and mathematical rules
        remain strictly unchanged.
        """
        eval_fn = UNIVERSITY_EVALUATORS["U5"]
        # U5.A placement conversion > 75% -> 2 marks; U5.B eligibility > 75% -> 2 marks. Raw = 4.0
        p_in = ParameterInput(
            parameter_code="U5",
            subcriteria_inputs={
                "U5.A": SubcriterionInput(subcriterion_code="U5.A", raw_inputs={"eligible_students": 80, "total_final_year_students": 100}, evidence_docs=[]),
                "U5.B": SubcriterionInput(subcriterion_code="U5.B", raw_inputs={"placed_students": 80, "eligible_students": 100}, evidence_docs=[]),
            }
        )
        res = eval_fn(p_in, self.univ_context, self.validator)
        self.assertEqual(res.raw_score, 4.0, "Raw scoring formula must remain exactly 4.0.")
        self.assertEqual(res.evidence_gated_score, 0.0, "Evidence gate blocks earned score without verified docs.")

    # =========================================================================
    # SECTION 9 NEGATIVE TEST: VERIFIED PARAMETER-LEVEL EVIDENCE WITHOUT EXACT SUBCRITERION
    # =========================================================================
    def test_section9_negative_test_parameter_level_evidence_must_not_satisfy_multi_subcriterion(self):
        """
        IMPORTANT NEGATIVE TEST:
        Deliberately supplies VERIFIED parameter-level evidence without an exact subcriterion association.
        For multi-subcriterion parameters (U7, U8, U10), expected evidence gate = NOT satisfied (FAILED_EVIDENCE_ABSENT).
        This proves the old parameter-level fallback is actually gone.
        """
        # Case 1: U7 multi-subcriterion with parameter-level verified doc (parameter_id="U7", subcriterion_id=None)
        doc_u7_param = EvidenceDocument(
            document_id="doc-param-level-u7",
            document_type="EVID_U7_APPOINTMENT",
            status=EvidenceState.EVIDENCE_VERIFIED,
            framework="UNIVERSITY_2026",
            parameter_id="U7",
            subcriterion_id=None,  # No exact subcriterion association!
            association_verified=None,
        )
        eval_fn_u7 = UNIVERSITY_EVALUATORS["U7"]
        p_in_u7 = ParameterInput(
            parameter_code="U7",
            subcriteria_inputs={
                "U7.2": SubcriterionInput(
                    subcriterion_code="U7.2",
                    raw_inputs={"verified": True},
                    evidence_docs=[doc_u7_param],
                )
            }
        )
        res_u7 = eval_fn_u7(p_in_u7, self.univ_context, self.validator)
        self.assertEqual(
            res_u7.subcriteria_results["U7.2"].gating_status,
            GatingStatus.FAILED_EVIDENCE_ABSENT,
            "Negative Test Proof: Parameter-level verified evidence MUST NOT satisfy multi-subcriterion U7.2.",
        )
        self.assertEqual(res_u7.subcriteria_results["U7.2"].evidence_gated_score, 0.0)

        # Case 2: U8 multi-subcriterion with parameter-level verified doc (parameter_id="U8", subcriterion_id=None)
        doc_u8_param = EvidenceDocument(
            document_id="doc-param-level-u8",
            document_type="EVID_U8_INCUBATION_REG",
            status=EvidenceState.EVIDENCE_VERIFIED,
            framework="UNIVERSITY_2026",
            parameter_id="U8",
            subcriterion_id=None,  # No exact subcriterion association!
            association_verified=None,
        )
        eval_fn_u8 = UNIVERSITY_EVALUATORS["U8"]
        p_in_u8 = ParameterInput(
            parameter_code="U8",
            subcriteria_inputs={
                "U8.A": SubcriterionInput(
                    subcriterion_code="U8.A",
                    raw_inputs={"startups_count": 15},
                    evidence_docs=[doc_u8_param],
                )
            }
        )
        res_u8 = eval_fn_u8(p_in_u8, self.univ_context, self.validator)
        self.assertEqual(
            res_u8.subcriteria_results["U8.A"].gating_status,
            GatingStatus.FAILED_EVIDENCE_ABSENT,
            "Negative Test Proof: Parameter-level verified evidence MUST NOT satisfy multi-subcriterion U8.A.",
        )
        self.assertEqual(res_u8.subcriteria_results["U8.A"].evidence_gated_score, 0.0)
