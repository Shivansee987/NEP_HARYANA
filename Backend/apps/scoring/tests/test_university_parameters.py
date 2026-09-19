"""
Unit Tests for All University Parameters (U1–U20)
Comprehensive coverage for each decomposed subcriterion, threshold tiers,
boundary voids, unresolved source specifications, and evidence gating.
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
from apps.scoring.rules.definitions import UNIVERSITY_PARAMETERS
from apps.scoring.rules.university import UNIVERSITY_EVALUATORS


class UniversityParametersTests(TestCase):

    def setUp(self):
        self.context = AssessmentContext(
            assessment_id="test-uni-assessment-001",
            institution_id="inst-uni-haryana-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30)),
        )
        self.validator = DoubleCountingValidator()

    def _make_verified_doc(self, doc_type: str, academic_year: Optional[str] = None) -> EvidenceDocument:
        return EvidenceDocument(
            document_id=f"doc-{doc_type}-01",
            document_type=doc_type,
            status=EvidenceState.EVIDENCE_VERIFIED,
            academic_year=academic_year,
        )

    # -------------------------------------------------------------
    # U1: Apprenticeship Embedded Degree Programmes (Max: 4)
    # Thresholds: >10: 4, (7, 10]: 3, (4, 7]: 2, (0, 4]: 1, 0: 0
    # Mandatory evidence: EVID_U1_APPROVAL
    # -------------------------------------------------------------
    def test_u1_thresholds_and_evidence(self):
        eval_fn = UNIVERSITY_EVALUATORS["U1"]
        doc = self._make_verified_doc("EVID_U1_APPROVAL")

        # Tier 1: > 10 (e.g. 12) -> 4 marks
        p_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 12},
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)
        self.assertEqual(res.evidence_gated_score, 4.0)
        self.assertEqual(res.final_score, 4.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.CALCULABLE)

        # Tier 2: 7 < count <= 10 (e.g. 8) -> 3 marks
        p_in.subcriteria_inputs["U1.1"].raw_inputs["programmes_count"] = 8
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 3.0)

        # Tier 3: 4 < count <= 7 (e.g. 5) -> 2 marks
        p_in.subcriteria_inputs["U1.1"].raw_inputs["programmes_count"] = 5
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 2.0)

        # Tier 4: 0 < count <= 4 (e.g. 2) -> 1 mark
        p_in.subcriteria_inputs["U1.1"].raw_inputs["programmes_count"] = 2
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 1.0)

        # Tier 5: 0 -> 0 marks
        p_in.subcriteria_inputs["U1.1"].raw_inputs["programmes_count"] = 0
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 0.0)

    # -------------------------------------------------------------
    # U2: Courses Offered in Indian Languages (Max: 4)
    # Thresholds: >75%: 4, (50, 75]: 3, (25, 50]: 2, (0, 25]: 1, 0: 0
    # Mandatory evidence: EVID_U2_COURSE_LIST
    # -------------------------------------------------------------
    def test_u2_percentage_calculation_and_tiers(self):
        eval_fn = UNIVERSITY_EVALUATORS["U2"]
        doc = self._make_verified_doc("EVID_U2_COURSE_LIST")

        # 80 / 100 = 80.0% -> Tier > 75% -> 4 marks
        p_in = ParameterInput(
            parameter_code="U2",
            subcriteria_inputs={
                "U2.1": SubcriterionInput(
                    subcriterion_code="U2.1",
                    raw_inputs={"indian_lang_programmes": 80, "total_degree_programmes": 100},
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)
        self.assertEqual(res.evidence_gated_score, 4.0)

        # 60 / 100 = 60% -> Tier (50, 75] -> 3 marks
        p_in.subcriteria_inputs["U2.1"].raw_inputs["indian_lang_programmes"] = 60
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 3.0)

        # 30 / 100 = 30% -> Tier (25, 50] -> 2 marks
        p_in.subcriteria_inputs["U2.1"].raw_inputs["indian_lang_programmes"] = 30
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 2.0)

        # 10 / 100 = 10% -> Tier (0, 25] -> 1 mark
        p_in.subcriteria_inputs["U2.1"].raw_inputs["indian_lang_programmes"] = 10
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 1.0)

    # -------------------------------------------------------------
    # U3: Integration of Indian Knowledge Systems (IKS) (Max: 4)
    # Thresholds: >25%: 4, (15, 25]: 3, (5, 15]: 2, (0, 5]: 1, 0: 0
    # Mandatory evidence: EVID_U3_SYLLABUS
    # -------------------------------------------------------------
    def test_u3_iks_tiers(self):
        eval_fn = UNIVERSITY_EVALUATORS["U3"]
        doc = self._make_verified_doc("EVID_U3_SYLLABUS")
        p_in = ParameterInput(
            parameter_code="U3",
            subcriteria_inputs={
                "U3.1": SubcriterionInput(
                    subcriterion_code="U3.1",
                    raw_inputs={"iks_programmes": 30, "total_degree_programmes": 100},  # 30% > 25%
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    # -------------------------------------------------------------
    # U4: Targets Achieved under IDP (Max: 6)
    # Decomposed: U4.A (2024-25, Max 3) + U4.B (2025-26, Max 3)
    # Thresholds per part: >90%: 3, (75, 90]: 2, (50, 75]: 1, <=50%: 0
    # Mandatory evidence: ["EVID_U4_IDP", "EVID_U4_PROGRESS_REPORT"]
    # -------------------------------------------------------------
    def test_u4_multi_period_decomposition(self):
        eval_fn = UNIVERSITY_EVALUATORS["U4"]
        doc1 = self._make_verified_doc("EVID_U4_IDP")
        doc2 = self._make_verified_doc("EVID_U4_PROGRESS_REPORT")

        # Both parts > 90% -> 3 + 3 = 6 marks
        p_in = ParameterInput(
            parameter_code="U4",
            subcriteria_inputs={
                "U4.A": SubcriterionInput(
                    subcriterion_code="U4.A",
                    raw_inputs={"achieved_targets_2024_25": 95, "total_targets_2024_25": 100},
                    evidence_docs=[doc1, doc2]
                ),
                "U4.B": SubcriterionInput(
                    subcriterion_code="U4.B",
                    raw_inputs={"achieved_targets_2025_26": 92, "total_targets_2025_26": 100},
                    evidence_docs=[doc1, doc2]
                ),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 6.0)
        self.assertEqual(res.max_marks, 6.0)
        self.assertEqual(res.subcriteria_results["U4.A"].raw_score, 3.0)
        self.assertEqual(res.subcriteria_results["U4.B"].raw_score, 3.0)

        # Mixed tiers: Part A 80% (2 marks), Part B 40% (0 marks) -> 2 marks total
        p_in.subcriteria_inputs["U4.A"].raw_inputs["achieved_targets_2024_25"] = 80
        p_in.subcriteria_inputs["U4.B"].raw_inputs["achieved_targets_2025_26"] = 40
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 2.0)
        self.assertEqual(res.subcriteria_results["U4.A"].raw_score, 2.0)
        self.assertEqual(res.subcriteria_results["U4.B"].raw_score, 0.0)

    def test_u4_multi_document_evidence_p2_03(self):
        """
        P2-03 Regression Tests:
        1. Only U4.1 evidence uploaded (verified) -> U4.1 scores, U4.2 = 0, final = U4.1 score
        2. Only U4.2 evidence uploaded (verified) -> U4.2 scores, U4.1 = 0, final = U4.2 score
        3. Both uploaded and verified -> full sum
        4. Unrelated/incorrect-year document uploaded -> gated to 0
        5. Missing evidence for one component does not zero out the other verified component
        6. Multiple valid documents uploaded for the same component -> handled cleanly
        7. Subcriteria identifiable by both canonical (U4.A/U4.B) and alias (U4.1/U4.2)
        """
        eval_fn = UNIVERSITY_EVALUATORS["U4"]
        doc_2024 = self._make_verified_doc("EVID_U4_PROGRESS_REPORT", academic_year="2024-25")
        doc_2025 = self._make_verified_doc("EVID_U4_PROGRESS_REPORT", academic_year="2025-26")
        doc_idp = self._make_verified_doc("EVID_U4_IDP")
        doc_unrelated = self._make_verified_doc("EVID_UNRELATED_DOC")

        # 1. Only U4.1 / U4.A evidence uploaded (verified)
        p_in_1 = ParameterInput(
            parameter_code="U4",
            subcriteria_inputs={
                "U4.1": SubcriterionInput(
                    subcriterion_code="U4.1",
                    raw_inputs={"achieved_targets_2024_25": 95, "total_targets_2024_25": 100},
                    evidence_docs=[doc_2024],
                ),
                "U4.2": SubcriterionInput(
                    subcriterion_code="U4.2",
                    raw_inputs={"achieved_targets_2025_26": 95, "total_targets_2025_26": 100},
                    evidence_docs=[],  # Missing evidence
                ),
            }
        )
        res_1 = eval_fn(p_in_1, self.context, self.validator)
        self.assertEqual(res_1.subcriteria_results["U4.1"].evidence_gated_score, 3.0)
        self.assertEqual(res_1.subcriteria_results["U4.A"].evidence_gated_score, 3.0)
        self.assertEqual(res_1.subcriteria_results["U4.2"].evidence_gated_score, 0.0)
        self.assertEqual(res_1.subcriteria_results["U4.B"].evidence_gated_score, 0.0)
        self.assertEqual(res_1.evidence_gated_score, 3.0)
        # Final score is preserved and equals U4.1 score!
        self.assertEqual(res_1.final_score, 3.0)
        self.assertEqual(res_1.trace["component_evidence_status"]["U4.1"], "PASSED_EVIDENCE_VERIFIED")
        self.assertEqual(res_1.trace["component_evidence_status"]["U4.2"], "FAILED_EVIDENCE_ABSENT")

        # 2. Only U4.2 / U4.B evidence uploaded (verified)
        p_in_2 = ParameterInput(
            parameter_code="U4",
            subcriteria_inputs={
                "U4.A": SubcriterionInput(
                    subcriterion_code="U4.A",
                    raw_inputs={"achieved_targets_2024_25": 95, "total_targets_2024_25": 100},
                    evidence_docs=[],
                ),
                "U4.B": SubcriterionInput(
                    subcriterion_code="U4.B",
                    raw_inputs={"achieved_targets_2025_26": 95, "total_targets_2025_26": 100},
                    evidence_docs=[doc_2025],
                ),
            }
        )
        res_2 = eval_fn(p_in_2, self.context, self.validator)
        self.assertEqual(res_2.subcriteria_results["U4.A"].evidence_gated_score, 0.0)
        self.assertEqual(res_2.subcriteria_results["U4.B"].evidence_gated_score, 3.0)
        self.assertEqual(res_2.evidence_gated_score, 3.0)
        self.assertEqual(res_2.final_score, 3.0)

        # 3. Both uploaded and verified -> full sum (6.0)
        p_in_3 = ParameterInput(
            parameter_code="U4",
            subcriteria_inputs={
                "U4.1": SubcriterionInput(
                    subcriterion_code="U4.1",
                    raw_inputs={"achieved_targets_2024_25": 95, "total_targets_2024_25": 100},
                    evidence_docs=[doc_2024],
                ),
                "U4.2": SubcriterionInput(
                    subcriterion_code="U4.2",
                    raw_inputs={"achieved_targets_2025_26": 95, "total_targets_2025_26": 100},
                    evidence_docs=[doc_2025],
                ),
            }
        )
        res_3 = eval_fn(p_in_3, self.context, self.validator)
        self.assertEqual(res_3.raw_score, 6.0)
        self.assertEqual(res_3.evidence_gated_score, 6.0)
        self.assertEqual(res_3.final_score, 6.0)

        # 4. Unrelated/incorrect-year document uploaded -> gated to 0
        doc_wrong_year = self._make_verified_doc("EVID_U4_PROGRESS_REPORT", academic_year="2025-26")
        p_in_4 = ParameterInput(
            parameter_code="U4",
            subcriteria_inputs={
                "U4.1": SubcriterionInput(
                    subcriterion_code="U4.1",
                    raw_inputs={"achieved_targets_2024_25": 95, "total_targets_2024_25": 100},
                    evidence_docs=[doc_wrong_year],  # Wrong academic year for 2024-25!
                ),
                "U4.2": SubcriterionInput(
                    subcriterion_code="U4.2",
                    raw_inputs={"achieved_targets_2025_26": 95, "total_targets_2025_26": 100},
                    evidence_docs=[doc_unrelated],  # Unrelated document type!
                ),
            }
        )
        res_4 = eval_fn(p_in_4, self.context, self.validator)
        self.assertEqual(res_4.subcriteria_results["U4.1"].evidence_gated_score, 0.0)
        self.assertEqual(res_4.subcriteria_results["U4.2"].evidence_gated_score, 0.0)
        self.assertEqual(res_4.evidence_gated_score, 0.0)
        self.assertEqual(res_4.final_score, 0.0)

        # 5. Missing evidence for one component does not zero out the other verified component
        # (Verified in test 1 and 2 above, but tested explicitly here)
        p_in_5 = ParameterInput(
            parameter_code="U4",
            subcriteria_inputs={
                "U4.A": SubcriterionInput(
                    subcriterion_code="U4.A",
                    raw_inputs={"achieved_targets_2024_25": 80, "total_targets_2024_25": 100},  # Tier 2: 2.0 marks
                    evidence_docs=[doc_2024],
                ),
                "U4.B": SubcriterionInput(
                    subcriterion_code="U4.B",
                    raw_inputs={"achieved_targets_2025_26": 95, "total_targets_2025_26": 100},
                    evidence_docs=[],  # Missing
                ),
            }
        )
        res_5 = eval_fn(p_in_5, self.context, self.validator)
        self.assertEqual(res_5.subcriteria_results["U4.A"].evidence_gated_score, 2.0)
        self.assertEqual(res_5.final_score, 2.0)

        # 6. Multiple valid documents uploaded for the same component -> handled cleanly
        p_in_6 = ParameterInput(
            parameter_code="U4",
            subcriteria_inputs={
                "U4.1": SubcriterionInput(
                    subcriterion_code="U4.1",
                    raw_inputs={"achieved_targets_2024_25": 95, "total_targets_2024_25": 100},
                    evidence_docs=[doc_idp, doc_2024],  # Multiple valid docs!
                ),
                "U4.2": SubcriterionInput(
                    subcriterion_code="U4.2",
                    raw_inputs={"achieved_targets_2025_26": 95, "total_targets_2025_26": 100},
                    evidence_docs=[doc_idp, doc_2025],
                ),
            }
        )
        res_6 = eval_fn(p_in_6, self.context, self.validator)
        self.assertEqual(res_6.evidence_gated_score, 6.0)
        self.assertEqual(res_6.final_score, 6.0)

    # -------------------------------------------------------------
    # U5: Percentage of Students Placed (Max: 4)
    # Decomposed: U5.A (Eligibility %, Max 2) + U5.B (Placement Conversion %, Max 2)
    # CRITICAL: U5.A has known source boundary void at exactly 50.0%
    # Mandatory evidence: EVID_U5_HOI_CERT
    # -------------------------------------------------------------
    def test_u5_decomposition_and_boundary_void(self):
        eval_fn = UNIVERSITY_EVALUATORS["U5"]
        doc = self._make_verified_doc("EVID_U5_HOI_CERT")

        # Normal valid values: U5.A = 80% (>75 -> 2), U5.B = 80% (>75 -> 2) -> 4 marks
        p_in = ParameterInput(
            parameter_code="U5",
            subcriteria_inputs={
                "U5.A": SubcriterionInput(
                    subcriterion_code="U5.A",
                    raw_inputs={"eligible_students": 80, "total_final_year_students": 100},
                    evidence_docs=[doc]
                ),
                "U5.B": SubcriterionInput(
                    subcriterion_code="U5.B",
                    raw_inputs={"placed_students": 64, "eligible_students": 80},  # 80% > 75% -> 2
                    evidence_docs=[doc]
                ),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.CALCULABLE)

        # EXACT BOUNDARY VOID TEST: U5.A at exactly 50.0%
        p_in.subcriteria_inputs["U5.A"].raw_inputs = {"eligible_students": 50, "total_final_year_students": 100}
        res_void = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res_void.resolution_status, ResolutionStatus.BOUNDARY_UNRESOLVED)
        self.assertIsNone(res_void.final_score)
        self.assertEqual(res_void.subcriteria_results["U5.A"].resolution_status, ResolutionStatus.BOUNDARY_UNRESOLVED)

    # -------------------------------------------------------------
    # U6: Academic Reforms (Max: 8)
    # Decomposed: U6.A (ABC Ordinance, Max 4) + U6.B (APAAR Tools, Max 4)
    # Mandatory evidence: EVID_U6_ORDINANCE_GAZETTE
    # -------------------------------------------------------------
    def test_u6_abc_and_apaar(self):
        eval_fn = UNIVERSITY_EVALUATORS["U6"]
        doc = self._make_verified_doc("EVID_U6_ORDINANCE_GAZETTE")
        p_in = ParameterInput(
            parameter_code="U6",
            subcriteria_inputs={
                "U6.A": SubcriterionInput(
                    subcriterion_code="U6.A",
                    raw_inputs={"ordinance_notified": True},
                    evidence_docs=[doc]
                ),
                "U6.B": SubcriterionInput(
                    subcriterion_code="U6.B",
                    raw_inputs={"tools_count": 4},
                    evidence_docs=[doc]
                ),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 8.0)
        self.assertEqual(res.final_score, 8.0)

    # -------------------------------------------------------------
    # U7: Professor of Practice (PoP) Engagement (Max: 4)
    # 4 Fixed Items: U7.1, U7.2, U7.3, U7.4 (1 mark each)
    # Mandatory evidence: EVID_U7_APPOINTMENT
    # -------------------------------------------------------------
    def test_u7_sedg_fixed_items(self):
        eval_fn = UNIVERSITY_EVALUATORS["U7"]
        doc = self._make_verified_doc("EVID_U7_APPOINTMENT")
        p_in = ParameterInput(
            parameter_code="U7",
            subcriteria_inputs={
                "U7.1": SubcriterionInput(subcriterion_code="U7.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U7.2": SubcriterionInput(subcriterion_code="U7.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U7.3": SubcriterionInput(subcriterion_code="U7.3", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U7.4": SubcriterionInput(subcriterion_code="U7.4", raw_inputs={"verified": False}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 3.0)
        self.assertEqual(res.evidence_gated_score, 3.0)

    # -------------------------------------------------------------
    # U8: Incubation / Startup Cell Performance as per NISP (Max: 6)
    # Decomposed: U8.A (Startups count, Max 4) + U8.B (Monetization %, Max 2)
    # Mandatory evidence: EVID_U8_INCUBATION_REG
    # -------------------------------------------------------------
    def test_u8_startups_and_monetization(self):
        eval_fn = UNIVERSITY_EVALUATORS["U8"]
        doc = self._make_verified_doc("EVID_U8_INCUBATION_REG")
        p_in = ParameterInput(
            parameter_code="U8",
            subcriteria_inputs={
                "U8.A": SubcriterionInput(
                    subcriterion_code="U8.A",
                    raw_inputs={"startups_count": 12},  # > 10 -> 4 marks
                    evidence_docs=[doc]
                ),
                "U8.B": SubcriterionInput(
                    subcriterion_code="U8.B",
                    raw_inputs={"monetized_count": 8},  # 8/12 = 66.7% >= 50% -> 2 marks
                    evidence_docs=[doc]
                ),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 6.0)

    # -------------------------------------------------------------
    # U9: Academic / Research Collaboration with Foreign HEIs (Max: 6)
    # Decomposed: U9.A (Active MoUs %, Max 1) + U9.B (Activities Count, Max 5)
    # Mandatory evidence: EVID_U9_MOU
    # -------------------------------------------------------------
    def test_u9_internationalization(self):
        eval_fn = UNIVERSITY_EVALUATORS["U9"]
        doc = self._make_verified_doc("EVID_U9_MOU")
        p_in = ParameterInput(
            parameter_code="U9",
            subcriteria_inputs={
                "U9.A": SubcriterionInput(
                    subcriterion_code="U9.A",
                    raw_inputs={"active_mous": 8, "total_mous": 10},  # 80% > 75% -> 1 mark
                    evidence_docs=[doc]
                ),
                "U9.B": SubcriterionInput(
                    subcriterion_code="U9.B",
                    raw_inputs={"activities_count": 5},  # >= 5 -> 5 marks
                    evidence_docs=[doc]
                ),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 6.0)

    # -------------------------------------------------------------
    # U10: Functional Alumni Connect Cell (Max: 5)
    # Decomposed: U10.1 (1), U10.2 (1), U10.3 (2), U10.4 (1)
    # CRITICAL: U10.3 has known source boundary void at exactly ₹1,00,00,000 (1 Crore)
    # Mandatory evidence: EVID_U10_REG_CERT
    # -------------------------------------------------------------
    def test_u10_alumni_and_boundary_void(self):
        eval_fn = UNIVERSITY_EVALUATORS["U10"]
        doc = self._make_verified_doc("EVID_U10_REG_CERT")
        p_in = ParameterInput(
            parameter_code="U10",
            subcriteria_inputs={
                "U10.1": SubcriterionInput(subcriterion_code="U10.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U10.2": SubcriterionInput(subcriterion_code="U10.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U10.3": SubcriterionInput(subcriterion_code="U10.3", raw_inputs={"funding_amount": 15000000.0}, evidence_docs=[doc]), # 1.5 Cr > 1 Cr -> 2 marks
                "U10.4": SubcriterionInput(subcriterion_code="U10.4", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.CALCULABLE)

        # BOUNDARY VOID TEST: U10.3 at exactly ₹1,00,00,000
        p_in.subcriteria_inputs["U10.3"].raw_inputs = {"funding_amount": 10000000.0}
        res_void = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res_void.resolution_status, ResolutionStatus.BOUNDARY_UNRESOLVED)
        self.assertIsNone(res_void.final_score)

    # -------------------------------------------------------------
    # U11: Gender Parity Initiatives (Max: 4)
    # 4 Fixed Items (1 mark each)
    # Mandatory evidence: EVID_U11_BOARDS
    # -------------------------------------------------------------
    def test_u11_fdp(self):
        eval_fn = UNIVERSITY_EVALUATORS["U11"]
        doc = self._make_verified_doc("EVID_U11_BOARDS")
        p_in = ParameterInput(
            parameter_code="U11",
            subcriteria_inputs={
                "U11.1": SubcriterionInput(subcriterion_code="U11.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U11.2": SubcriterionInput(subcriterion_code="U11.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U11.3": SubcriterionInput(subcriterion_code="U11.3", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U11.4": SubcriterionInput(subcriterion_code="U11.4", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    # -------------------------------------------------------------
    # U12: Physical Fitness, Sports, Yoga, Welfare (Max: 5)
    # 5 Items: U12.1..5 (1 mark each) -> Max 5
    # Mandatory evidence: EVID_U12_CENTRE_NOTIF
    # -------------------------------------------------------------
    def test_u12_research_rankings(self):
        eval_fn = UNIVERSITY_EVALUATORS["U12"]
        doc = self._make_verified_doc("EVID_U12_CENTRE_NOTIF")
        p_in = ParameterInput(
            parameter_code="U12",
            subcriteria_inputs={
                "U12.1": SubcriterionInput(subcriterion_code="U12.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U12.2": SubcriterionInput(subcriterion_code="U12.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U12.3": SubcriterionInput(subcriterion_code="U12.3", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U12.4": SubcriterionInput(subcriterion_code="U12.4", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U12.5": SubcriterionInput(subcriterion_code="U12.5", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)
        self.assertEqual(res.max_marks, 5.0)

    # -------------------------------------------------------------
    # U13: Online Courses / MOOCs Policy and Adoption (Max: 6)
    # Thresholds: >75%: 6, (50, 75]: 5, (25, 50]: 3, (0, 25]: 2, 0: 0
    # Mandatory evidence: EVID_U13_POLICY
    # -------------------------------------------------------------
    def test_u13_digital_learning(self):
        eval_fn = UNIVERSITY_EVALUATORS["U13"]
        doc = self._make_verified_doc("EVID_U13_POLICY")
        p_in = ParameterInput(
            parameter_code="U13",
            subcriteria_inputs={
                "U13.1": SubcriterionInput(
                    subcriterion_code="U13.1",
                    raw_inputs={"regular_mooc_learners": 800, "total_regular_learners": 1000},  # 80% > 75% -> 6 marks
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 6.0)

    # -------------------------------------------------------------
    # U14: Multidisciplinary Education (Max: 6)
    # Decomposed: U14.A (Max 4, >90: 4, 75-90: 3, 50-75: 2, 25-50: 1), U14.B (1), U14.C (1)
    # Mandatory evidence: EVID_U14_CURRICULUM
    # -------------------------------------------------------------
    def test_u14_multidisciplinary(self):
        eval_fn = UNIVERSITY_EVALUATORS["U14"]
        doc = self._make_verified_doc("EVID_U14_CURRICULUM")
        p_in = ParameterInput(
            parameter_code="U14",
            subcriteria_inputs={
                "U14.A": SubcriterionInput(
                    subcriterion_code="U14.A",
                    raw_inputs={"multidisciplinary_programmes": 95, "total_degree_programmes": 100},  # 95% > 90% -> 4 marks
                    evidence_docs=[doc]
                ),
                "U14.B": SubcriterionInput(subcriterion_code="U14.B", raw_inputs={"verified": True}, evidence_docs=[doc]),  # 1 mark
                "U14.C": SubcriterionInput(subcriterion_code="U14.C", raw_inputs={"verified": True}, evidence_docs=[doc]),  # 1 mark
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 6.0)

    # -------------------------------------------------------------
    # U15: Multiple Entry-Exit Operationalized (Max: 2)
    # Decomposed: U15.1 (1) + U15.2 (1) = Max 2
    # Mandatory evidence: EVID_U15_ORDINANCE
    # -------------------------------------------------------------
    def test_u15_community_engagement(self):
        eval_fn = UNIVERSITY_EVALUATORS["U15"]
        doc = self._make_verified_doc("EVID_U15_ORDINANCE")
        p_in = ParameterInput(
            parameter_code="U15",
            subcriteria_inputs={
                "U15.1": SubcriterionInput(subcriterion_code="U15.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U15.2": SubcriterionInput(subcriterion_code="U15.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 2.0)

    # -------------------------------------------------------------
    # U16: Research Outcome: Patents Filed and Granted (Max: 8)
    # CRITICAL: U16.III Scopus index is UNRESOLVED in source rubric
    # Mandatory evidence: EVID_U16_FILING
    # -------------------------------------------------------------
    def test_u16_patents_and_unresolved_scopus(self):
        eval_fn = UNIVERSITY_EVALUATORS["U16"]
        doc = self._make_verified_doc("EVID_U16_FILING")
        p_in = ParameterInput(
            parameter_code="U16",
            subcriteria_inputs={
                "U16.I": SubcriterionInput(subcriterion_code="U16.I", raw_inputs={"patents_filed": 10}, evidence_docs=[doc]),  # 2 marks
                "U16.II": SubcriterionInput(subcriterion_code="U16.II", raw_inputs={"patents_granted": 10}, evidence_docs=[doc]),  # 2 marks
                "U16.III": SubcriterionInput(subcriterion_code="U16.III", raw_inputs={"scopus_publications": 50}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertIsNone(res.final_score)
        self.assertEqual(res.subcriteria_results["U16.III"].resolution_status, ResolutionStatus.UNRESOLVED_RULE)

    def test_u16_ii_patents_granted_exact_tiers(self):
        """
        P1-01 Regression Test:
        Rubric: 1 mark for each patent granted/commercialised/licensed during assessment period, max 2 marks.
        0 granted -> 0
        1 granted -> 1
        2 granted -> 2
        3 granted -> 2
        5 granted -> 2
        """
        eval_fn = UNIVERSITY_EVALUATORS["U16"]
        doc = self._make_verified_doc("EVID_U16_FILING")
        test_cases = [
            (0, 0.0),
            (1, 1.0),
            (2, 2.0),
            (3, 2.0),
            (5, 2.0),
        ]
        for cnt, expected_score in test_cases:
            with self.subTest(patents_granted=cnt):
                p_in = ParameterInput(
                    parameter_code="U16",
                    subcriteria_inputs={
                        "U16.I": SubcriterionInput(subcriterion_code="U16.I", raw_inputs={"patents_filed": 0}, evidence_docs=[doc]),
                        "U16.II": SubcriterionInput(subcriterion_code="U16.II", raw_inputs={"patents_granted": cnt}, evidence_docs=[doc]),
                        "U16.III": SubcriterionInput(subcriterion_code="U16.III", raw_inputs={}, evidence_docs=[doc]),
                    }
                )
                res = eval_fn(p_in, self.context, self.validator)
                u16_ii_res = res.subcriteria_results["U16.II"]
                self.assertEqual(u16_ii_res.raw_score, expected_score)
                self.assertEqual(u16_ii_res.evidence_gated_score, expected_score)
                # Ensure U16 overall resolution_status remains UNRESOLVED_RULE due to U16.III
                self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)

    def test_u16_i_boundary_transitions_p2_01(self):
        """
        P2-01 Boundary Coverage Test for U16.I:
        Rubric: 1 mark per 5 patents filed, max 2 marks.
        0 filed -> 0.0
        1 filed -> 0.0
        4 filed -> 0.0
        5 filed -> 1.0
        9 filed -> 1.0
        10 filed -> 2.0
        15 filed -> 2.0 (capped at 2.0)
        """
        eval_fn = UNIVERSITY_EVALUATORS["U16"]
        doc = self._make_verified_doc("EVID_U16_FILING")
        test_cases = [
            (0, 0.0),
            (1, 0.0),
            (4, 0.0),
            (5, 1.0),
            (9, 1.0),
            (10, 2.0),
            (15, 2.0),
        ]
        for cnt, expected_score in test_cases:
            with self.subTest(patents_filed=cnt):
                p_in = ParameterInput(
                    parameter_code="U16",
                    subcriteria_inputs={
                        "U16.I": SubcriterionInput(subcriterion_code="U16.I", raw_inputs={"patents_filed": cnt}, evidence_docs=[doc]),
                        "U16.II": SubcriterionInput(subcriterion_code="U16.II", raw_inputs={"patents_granted": 0}, evidence_docs=[doc]),
                        "U16.III": SubcriterionInput(subcriterion_code="U16.III", raw_inputs={}, evidence_docs=[doc]),
                    }
                )
                res = eval_fn(p_in, self.context, self.validator)
                u16_i_res = res.subcriteria_results["U16.I"]
                self.assertEqual(u16_i_res.raw_score, expected_score)
                self.assertEqual(u16_i_res.evidence_gated_score, expected_score)
                self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)

    # -------------------------------------------------------------
    # U17: Registration and Performance in NIRF (Max: 2)
    # Decomposed: U17.1 (1) + U17.2 (1) = Max 2
    # Mandatory evidence: EVID_U17_NIRF_2026_PROOF
    # -------------------------------------------------------------
    def test_u17_vocational(self):
        eval_fn = UNIVERSITY_EVALUATORS["U17"]
        doc = self._make_verified_doc("EVID_U17_NIRF_2026_PROOF")
        p_in = ParameterInput(
            parameter_code="U17",
            subcriteria_inputs={
                "U17.1": SubcriterionInput(subcriterion_code="U17.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U17.2": SubcriterionInput(subcriterion_code="U17.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 2.0)

    # -------------------------------------------------------------
    # U18: RPL Adoption and Implementation (Max: 4)
    # Decomposed: U18.1 (1) + U18.2 (1) + U18.3 (2) = Max 4
    # Mandatory evidence: EVID_U18_POLICY
    # -------------------------------------------------------------
    def test_u18_governance(self):
        eval_fn = UNIVERSITY_EVALUATORS["U18"]
        doc = self._make_verified_doc("EVID_U18_POLICY")
        p_in = ParameterInput(
            parameter_code="U18",
            subcriteria_inputs={
                "U18.1": SubcriterionInput(subcriterion_code="U18.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U18.2": SubcriterionInput(subcriterion_code="U18.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "U18.3": SubcriterionInput(subcriterion_code="U18.3", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    # -------------------------------------------------------------
    # U19: Adoption of Outcome-Based Education (OBE) (Max: 8)
    # Decomposed: U19.A (Max 6, >90: 6, 80-90: 5, 70-80: 4, 60-70: 3, 50-60: 2, 25-50: 1) + U19.B (2)
    # Mandatory evidence: EVID_U19_OBE_FRAMEWORK
    # -------------------------------------------------------------
    def test_u19_obe(self):
        eval_fn = UNIVERSITY_EVALUATORS["U19"]
        doc = self._make_verified_doc("EVID_U19_OBE_FRAMEWORK")
        p_in = ParameterInput(
            parameter_code="U19",
            subcriteria_inputs={
                "U19.A": SubcriterionInput(
                    subcriterion_code="U19.A",
                    raw_inputs={"obe_programmes": 95, "total_degree_programmes": 100},  # 95% > 90% -> 6 marks
                    evidence_docs=[doc]
                ),
                "U19.B": SubcriterionInput(subcriterion_code="U19.B", raw_inputs={"verified": True}, evidence_docs=[doc]),  # 2 marks
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 8.0)

    # -------------------------------------------------------------
    # U20: Activities Aligned with SDGs (Declared Max: 4, Criteria Sum: 5)
    # CRITICAL: U20 has known source internal arithmetic discrepancy
    # U20.1 (Activities count >= 10: 2) + U20.2 (2) + U20.3 (1) = 5 marks!
    # Mandatory evidence: EVID_U20_ACTIVITY_REPORTS
    # -------------------------------------------------------------
    def test_u20_arithmetic_discrepancy(self):
        eval_fn = UNIVERSITY_EVALUATORS["U20"]
        doc = self._make_verified_doc("EVID_U20_ACTIVITY_REPORTS")
        p_in = ParameterInput(
            parameter_code="U20",
            subcriteria_inputs={
                "U20.1": SubcriterionInput(subcriterion_code="U20.1", raw_inputs={"activities_count": 15}, evidence_docs=[doc]),  # 2 marks
                "U20.2": SubcriterionInput(subcriterion_code="U20.2", raw_inputs={"verified": True}, evidence_docs=[doc]),  # 2 marks
                "U20.3": SubcriterionInput(subcriterion_code="U20.3", raw_inputs={"verified": True}, evidence_docs=[doc]),  # 1 mark
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        # Raw score must be capped at declared max 4.0, but resolution status must be SOURCE_INCONSISTENCY
        # and final_score must be None!
        self.assertEqual(res.raw_score, 4.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.SOURCE_INCONSISTENCY)
        self.assertIsNone(res.final_score)
