"""
Unit Tests for All College Parameters (C1–C22)
Comprehensive coverage for each decomposed subcriterion, threshold tiers,
boundary voids, unresolved source specifications (C7, C8, C16, C19.III, C21), and evidence gating.
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
from apps.scoring.rules.definitions import COLLEGE_PARAMETERS


class CollegeParametersTests(TestCase):

    def setUp(self):
        self.context = AssessmentContext(
            assessment_id="test-college-assessment-001",
            institution_id="inst-college-haryana-01",
            institution_type=InstitutionType.COLLEGE,
            framework=FrameworkType.COLLEGE_2026,
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
    # C1: IDP and NEP Implementation Targets (Max: 6)
    # Thresholds: >90%: 6, (75, 90]: 4, (50, 75]: 2, <=50%: 1
    # Mandatory evidence: EVID_C1_APPROVED_IDP
    # -------------------------------------------------------------
    def test_c1_idp_targets(self):
        eval_fn = COLLEGE_EVALUATORS["C1"]
        doc = self._make_verified_doc("EVID_C1_APPROVED_IDP")

        # > 90% -> 6 marks
        p_in = ParameterInput(
            parameter_code="C1",
            subcriteria_inputs={
                "C1.1": SubcriterionInput(
                    subcriterion_code="C1.1",
                    raw_inputs={"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100},  # 95% > 90%
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 6.0)
        self.assertEqual(res.final_score, 6.0)

        # 75 < pct <= 90 -> 4 marks
        p_in.subcriteria_inputs["C1.1"].raw_inputs = {"achieved_targets_2024_25": 80, "fixed_targets_2024_25": 100}
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

        # 50 < pct <= 75 -> 2 marks
        p_in.subcriteria_inputs["C1.1"].raw_inputs = {"achieved_targets_2024_25": 60, "fixed_targets_2024_25": 100}
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 2.0)

        # <= 50 -> 1 mark
        p_in.subcriteria_inputs["C1.1"].raw_inputs = {"achieved_targets_2024_25": 40, "fixed_targets_2024_25": 100}
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 1.0)

    # -------------------------------------------------------------
    # C2: Apprenticeship / Internships (Max: 4)
    # Thresholds: >90%: 4, (75, 90]: 3, (50, 75]: 2, (25, 50]: 1, <=25%: 0
    # Mandatory evidence: EVID_C2_HOI_CERT
    # -------------------------------------------------------------
    def test_c2_internships(self):
        eval_fn = COLLEGE_EVALUATORS["C2"]
        doc = self._make_verified_doc("EVID_C2_HOI_CERT")
        p_in = ParameterInput(
            parameter_code="C2",
            subcriteria_inputs={
                "C2.1": SubcriterionInput(
                    subcriterion_code="C2.1",
                    raw_inputs={"students_completed": 92, "eligible_students": 100},  # 92% > 90%
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    # -------------------------------------------------------------
    # C3: Academic Bank of Credits (ABC) Registration (Max: 4)
    # Thresholds: >90%: 4, (75, 90]: 3, (60, 75]: 2, (50, 60]: 1, <=50%: 0
    # Mandatory evidence: EVID_C3_ABC_DASHBOARD
    # -------------------------------------------------------------
    def test_c3_abc_registration(self):
        eval_fn = COLLEGE_EVALUATORS["C3"]
        doc = self._make_verified_doc("EVID_C3_ABC_DASHBOARD")
        p_in = ParameterInput(
            parameter_code="C3",
            subcriteria_inputs={
                "C3.1": SubcriterionInput(
                    subcriterion_code="C3.1",
                    raw_inputs={"abc_registered_students": 950, "total_enrolled_students": 1000},  # 95% > 90%
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    # -------------------------------------------------------------
    # C4: Supporting Other Institutes and Schools (Max: 4)
    # Decomposed: C4.A (Max 2, heis_mentored) + C4.B (Max 2, schools_mentored >= 5) = Max 4
    # Mandatory evidence: EVID_C4_INSTITUTE_CERTS
    # -------------------------------------------------------------
    def test_c4_school_mentoring(self):
        eval_fn = COLLEGE_EVALUATORS["C4"]
        doc = self._make_verified_doc("EVID_C4_INSTITUTE_CERTS")
        p_in = ParameterInput(
            parameter_code="C4",
            subcriteria_inputs={
                "C4.A": SubcriterionInput(subcriterion_code="C4.A", raw_inputs={"heis_mentored": 2}, evidence_docs=[doc]),
                "C4.B": SubcriterionInput(subcriterion_code="C4.B", raw_inputs={"schools_mentored": 6}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    # -------------------------------------------------------------
    # C5: Student Enrollment against Sanctioned Seats (Max: 2)
    # CRITICAL: C5.1 has known source boundary void at exactly 75.0%
    # Thresholds: >=90%: 2, (75, 90): 1, <75%: 0
    # Mandatory evidence: EVID_C5_SANCTION_LETTER
    # -------------------------------------------------------------
    def test_c5_enrollment_and_boundary_void(self):
        eval_fn = COLLEGE_EVALUATORS["C5"]
        doc = self._make_verified_doc("EVID_C5_SANCTION_LETTER")

        # Valid score: 92% >= 90% -> 2 marks
        p_in = ParameterInput(
            parameter_code="C5",
            subcriteria_inputs={
                "C5.1": SubcriterionInput(
                    subcriterion_code="C5.1",
                    raw_inputs={"admitted_students": 92, "sanctioned_intake": 100},
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 2.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.CALCULABLE)

        # EXACT BOUNDARY VOID TEST: exactly 75.0%
        p_in.subcriteria_inputs["C5.1"].raw_inputs = {"admitted_students": 75, "sanctioned_intake": 100}
        res_void = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res_void.resolution_status, ResolutionStatus.BOUNDARY_UNRESOLVED)
        self.assertIsNone(res_void.final_score)

    # -------------------------------------------------------------
    # C6: VAC, AEC, SEC, NSQF-Aligned Courses (Max: 6)
    # Thresholds: >90%: 6, (80, 90]: 5, (70, 80]: 4, (60, 70]: 3, (50, 60]: 2, <=50%: 1
    # Mandatory evidence: EVID_C6_COURSE_APPROVAL
    # -------------------------------------------------------------
    def test_c6_skill_courses(self):
        eval_fn = COLLEGE_EVALUATORS["C6"]
        doc = self._make_verified_doc("EVID_C6_COURSE_APPROVAL")
        p_in = ParameterInput(
            parameter_code="C6",
            subcriteria_inputs={
                "C6.1": SubcriterionInput(
                    subcriterion_code="C6.1",
                    raw_inputs={"certified_students": 920, "total_enrolled_students": 1000},  # 92% > 90% -> 6 marks
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 6.0)

    # -------------------------------------------------------------
    # C7: Bridge Courses for SEDGs (Max: 6, but visible sum: 3)
    # CRITICAL: C7 has unresolved 3-mark deficit contradiction
    # Mandatory evidence: EVID_C7_OFFICE_ORDERS
    # -------------------------------------------------------------
    def test_c7_unresolved_deficit_contradiction(self):
        eval_fn = COLLEGE_EVALUATORS["C7"]
        doc = self._make_verified_doc("EVID_C7_OFFICE_ORDERS")
        p_in = ParameterInput(
            parameter_code="C7",
            subcriteria_inputs={
                "C7.1": SubcriterionInput(
                    subcriterion_code="C7.1",
                    raw_inputs={"sedg_bridge_students": 95, "total_sedg_students": 100},  # 95% > 90% -> 3 marks
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 3.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertIsNone(res.final_score)

    # -------------------------------------------------------------
    # C8: Nomination of NEP-SARTHI (Declared Max: 2)
    # CRITICAL: C8 has unresolved single unquantified textual line in source
    # Mandatory evidence: EVID_C8_OFFICE_ORDERS
    # -------------------------------------------------------------
    def test_c8_unresolved_single_line(self):
        eval_fn = COLLEGE_EVALUATORS["C8"]
        doc = self._make_verified_doc("EVID_C8_OFFICE_ORDERS")
        p_in = ParameterInput(
            parameter_code="C8",
            subcriteria_inputs={
                "C8.1": SubcriterionInput(subcriterion_code="C8.1", raw_inputs={"verified": True}, evidence_docs=[doc])
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertIsNone(res.final_score)

    # -------------------------------------------------------------
    # C9: Student Career Orientation and Placements (Max: 6)
    # Decomposed: C9.I (3) + C9.II (3) = Max 6
    # Thresholds: 100%: 3, >=75%: 2, >=50%: 1, <50%: 0
    # Mandatory evidence: EVID_C9_FAIR_REGISTER
    # -------------------------------------------------------------
    def test_c9_career_orientation(self):
        eval_fn = COLLEGE_EVALUATORS["C9"]
        doc = self._make_verified_doc("EVID_C9_FAIR_REGISTER")
        p_in = ParameterInput(
            parameter_code="C9",
            subcriteria_inputs={
                "C9.I": SubcriterionInput(
                    subcriterion_code="C9.I",
                    raw_inputs={"participating_students": 100, "eligible_students": 100},  # 100% -> 3
                    evidence_docs=[doc]
                ),
                "C9.II": SubcriterionInput(
                    subcriterion_code="C9.II",
                    raw_inputs={"placed_students": 80},  # 80/100 = 80% >= 75% -> 2
                    evidence_docs=[doc]
                ),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    # -------------------------------------------------------------
    # C10: Industry Collaboration, MoUs (Max: 5)
    # Thresholds: >=5: 5, 4: 4, 3: 3, 2: 2, 1: 1, 0: 0
    # Mandatory evidence: EVID_C10_MOU_DOCS
    # -------------------------------------------------------------
    def test_c10_industry_mous(self):
        eval_fn = COLLEGE_EVALUATORS["C10"]
        doc = self._make_verified_doc("EVID_C10_MOU_DOCS")
        p_in = ParameterInput(
            parameter_code="C10",
            subcriteria_inputs={
                "C10.1": SubcriterionInput(
                    subcriterion_code="C10.1",
                    raw_inputs={"active_mous_count": 5},
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    # -------------------------------------------------------------
    # C11: Incubation, Startup Cell (Max: 5)
    # Decomposed: C11.I (Max 3, >10: 3, 6-10: 2, 1-5: 1) + C11.II.a (1) + C11.II.b (1)
    # Mandatory evidence: EVID_C11_REGISTRATION
    # -------------------------------------------------------------
    def test_c11_incubation(self):
        eval_fn = COLLEGE_EVALUATORS["C11"]
        doc = self._make_verified_doc("EVID_C11_REGISTRATION")
        p_in = ParameterInput(
            parameter_code="C11",
            subcriteria_inputs={
                "C11.I": SubcriterionInput(subcriterion_code="C11.I", raw_inputs={"ventures_count": 12}, evidence_docs=[doc]),  # 3 marks
                "C11.II.a": SubcriterionInput(subcriterion_code="C11.II.a", raw_inputs={"cell_functional": True}, evidence_docs=[doc]),  # 1 mark
                "C11.II.b": SubcriterionInput(subcriterion_code="C11.II.b", raw_inputs={"monetized_count": 8}, evidence_docs=[doc]),  # 8/12 = 66% >= 50% -> 1 mark
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    # -------------------------------------------------------------
    # C12: Alumni Connect and External Expert Engagement (Max: 5)
    # 5 Items: C12.1..5 (1 mark each)
    # Mandatory evidence: EVID_C12_DATABASE
    # -------------------------------------------------------------
    def test_c12_alumni(self):
        eval_fn = COLLEGE_EVALUATORS["C12"]
        doc = self._make_verified_doc("EVID_C12_DATABASE")
        p_in = ParameterInput(
            parameter_code="C12",
            subcriteria_inputs={
                "C12.1": SubcriterionInput(subcriterion_code="C12.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C12.2": SubcriterionInput(subcriterion_code="C12.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C12.3": SubcriterionInput(subcriterion_code="C12.3", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C12.4": SubcriterionInput(subcriterion_code="C12.4", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C12.5": SubcriterionInput(subcriterion_code="C12.5", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    # -------------------------------------------------------------
    # C13: Faculty Development and NEP Orientation (Max: 4)
    # Thresholds: >80%: 4, (60, 80]: 3, (40, 60]: 2, (20, 40]: 1, <=20%: 0
    # Mandatory evidence: EVID_C13_FDP_CERTS
    # -------------------------------------------------------------
    def test_c13_fdp(self):
        eval_fn = COLLEGE_EVALUATORS["C13"]
        doc = self._make_verified_doc("EVID_C13_FDP_CERTS")
        p_in = ParameterInput(
            parameter_code="C13",
            subcriteria_inputs={
                "C13.1": SubcriterionInput(
                    subcriterion_code="C13.1",
                    raw_inputs={"trained_faculty": 85, "total_fulltime_faculty": 100},  # 85% > 80% -> 4 marks
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    # -------------------------------------------------------------
    # C14: Indian Languages and IKS (Max: 4)
    # Decomposed: C14.A (content_items >= 4 -> 2) + C14.B (iks_activities >= 5 -> 2) = Max 4
    # Mandatory evidence: EVID_C14_MATERIAL_CERT
    # -------------------------------------------------------------
    def test_c14_indian_languages(self):
        eval_fn = COLLEGE_EVALUATORS["C14"]
        doc = self._make_verified_doc("EVID_C14_MATERIAL_CERT")
        p_in = ParameterInput(
            parameter_code="C14",
            subcriteria_inputs={
                "C14.A": SubcriterionInput(subcriterion_code="C14.A", raw_inputs={"content_items": 4}, evidence_docs=[doc]),
                "C14.B": SubcriterionInput(subcriterion_code="C14.B", raw_inputs={"iks_activities": 5}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    # -------------------------------------------------------------
    # C15: Student Well-being, Physical Fitness, Sports (Max: 6)
    # 6 Items: C15.1..6 (1 mark each)
    # Mandatory evidence: EVID_C15_CENTRE_ORDER
    # -------------------------------------------------------------
    def test_c15_wellbeing(self):
        eval_fn = COLLEGE_EVALUATORS["C15"]
        doc = self._make_verified_doc("EVID_C15_CENTRE_ORDER")
        p_in = ParameterInput(
            parameter_code="C15",
            subcriteria_inputs={
                "C15.1": SubcriterionInput(subcriterion_code="C15.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C15.2": SubcriterionInput(subcriterion_code="C15.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C15.3": SubcriterionInput(subcriterion_code="C15.3", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C15.4": SubcriterionInput(subcriterion_code="C15.4", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C15.5": SubcriterionInput(subcriterion_code="C15.5", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C15.6": SubcriterionInput(subcriterion_code="C15.6", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 6.0)

    # -------------------------------------------------------------
    # C16: Gender Parity, Safety and Inclusion (Declared Max: 4, Visible Items: 5)
    # CRITICAL: C16 has unresolved 1-mark excess contradiction
    # Mandatory evidence: EVID_C16_ICC_ORDERS
    # -------------------------------------------------------------
    def test_c16_unresolved_excess_items(self):
        eval_fn = COLLEGE_EVALUATORS["C16"]
        doc = self._make_verified_doc("EVID_C16_ICC_ORDERS")
        p_in = ParameterInput(
            parameter_code="C16",
            subcriteria_inputs={
                "C16.1": SubcriterionInput(subcriterion_code="C16.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C16.2": SubcriterionInput(subcriterion_code="C16.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C16.3": SubcriterionInput(subcriterion_code="C16.3", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C16.4": SubcriterionInput(subcriterion_code="C16.4", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C16.5": SubcriterionInput(subcriterion_code="C16.5", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertIsNone(res.final_score)

    # -------------------------------------------------------------
    # C17: Outreach, Community Engagement (Max: 5)
    # Thresholds: >90%: 5, (75, 90]: 4, (60, 75]: 3, (50, 60]: 2, (0, 50]: 1, 0: 0
    # Mandatory evidence: EVID_C17_STUDENT_LIST
    # -------------------------------------------------------------
    def test_c17_outreach(self):
        eval_fn = COLLEGE_EVALUATORS["C17"]
        doc = self._make_verified_doc("EVID_C17_STUDENT_LIST")
        p_in = ParameterInput(
            parameter_code="C17",
            subcriteria_inputs={
                "C17.1": SubcriterionInput(
                    subcriterion_code="C17.1",
                    raw_inputs={"participating_students": 95, "total_enrolled_students": 100},  # 95% > 90% -> 5 marks
                    evidence_docs=[doc]
                )
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    # -------------------------------------------------------------
    # C18: Sustainable Development Goals (SDGs), Green Campus (Max: 5)
    # Decomposed: C18.1 (sdg_activities >= 5 -> 2) + C18.2 (1) + C18.3 (1) + C18.4 (1) = Max 5
    # Mandatory evidence: EVID_C18_ACTIVITY_REPORTS
    # -------------------------------------------------------------
    def test_c18_sdgs(self):
        eval_fn = COLLEGE_EVALUATORS["C18"]
        doc = self._make_verified_doc("EVID_C18_ACTIVITY_REPORTS")
        p_in = ParameterInput(
            parameter_code="C18",
            subcriteria_inputs={
                "C18.1": SubcriterionInput(subcriterion_code="C18.1", raw_inputs={"sdg_activities": 5}, evidence_docs=[doc]),
                "C18.2": SubcriterionInput(subcriterion_code="C18.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C18.3": SubcriterionInput(subcriterion_code="C18.3", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C18.4": SubcriterionInput(subcriterion_code="C18.4", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    # -------------------------------------------------------------
    # C19: Research, Innovation and Patents (Max: 6)
    # CRITICAL: C19.III Scopus index is UNRESOLVED in source rubric
    # Mandatory evidence: EVID_C19_FILING_CERTS
    # -------------------------------------------------------------
    def test_c19_patents_and_unresolved_scopus(self):
        eval_fn = COLLEGE_EVALUATORS["C19"]
        doc = self._make_verified_doc("EVID_C19_FILING_CERTS")
        p_in = ParameterInput(
            parameter_code="C19",
            subcriteria_inputs={
                "C19.I": SubcriterionInput(subcriterion_code="C19.I", raw_inputs={"patents_filed": 10}, evidence_docs=[doc]),  # 2 marks
                "C19.II": SubcriterionInput(subcriterion_code="C19.II", raw_inputs={"patents_granted": 10}, evidence_docs=[doc]),  # 2 marks
                "C19.III": SubcriterionInput(subcriterion_code="C19.III", raw_inputs={"scopus_publications": 50}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertIsNone(res.final_score)

    def test_c19_ii_patents_granted_exact_tiers(self):
        """
        P1-02 Regression Test:
        Rubric: 1 mark for each patent granted between July 2025 and June 2026, max 2 marks.
        0 granted -> 0
        1 granted -> 1
        2 granted -> 2
        3 granted -> 2
        5 granted -> 2
        """
        eval_fn = COLLEGE_EVALUATORS["C19"]
        doc = self._make_verified_doc("EVID_C19_FILING_CERTS")
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
                    parameter_code="C19",
                    subcriteria_inputs={
                        "C19.I": SubcriterionInput(subcriterion_code="C19.I", raw_inputs={"patents_filed": 0}, evidence_docs=[doc]),
                        "C19.II": SubcriterionInput(subcriterion_code="C19.II", raw_inputs={"patents_granted": cnt}, evidence_docs=[doc]),
                        "C19.III": SubcriterionInput(subcriterion_code="C19.III", raw_inputs={}, evidence_docs=[doc]),
                    }
                )
                res = eval_fn(p_in, self.context, self.validator)
                c19_ii_res = res.subcriteria_results["C19.II"]
                self.assertEqual(c19_ii_res.raw_score, expected_score)
                self.assertEqual(c19_ii_res.evidence_gated_score, expected_score)
                # Ensure C19 overall resolution_status remains UNRESOLVED_RULE due to C19.III
                self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)

    def test_c19_i_boundary_transitions_p2_02(self):
        """
        P2-02 Boundary Coverage Test for C19.I:
        Rubric: 1 mark per 2 patents filed, max 2 marks.
        0 filed -> 0.0
        1 filed -> 0.0
        2 filed -> 1.0
        3 filed -> 1.0
        4 filed -> 2.0
        6 filed -> 2.0 (capped at 2.0)
        """
        eval_fn = COLLEGE_EVALUATORS["C19"]
        doc = self._make_verified_doc("EVID_C19_FILING_CERTS")
        test_cases = [
            (0, 0.0),
            (1, 0.0),
            (2, 1.0),
            (3, 1.0),
            (4, 2.0),
            (6, 2.0),
        ]
        for cnt, expected_score in test_cases:
            with self.subTest(patents_filed=cnt):
                p_in = ParameterInput(
                    parameter_code="C19",
                    subcriteria_inputs={
                        "C19.I": SubcriterionInput(subcriterion_code="C19.I", raw_inputs={"patents_filed": cnt}, evidence_docs=[doc]),
                        "C19.II": SubcriterionInput(subcriterion_code="C19.II", raw_inputs={"patents_granted": 0}, evidence_docs=[doc]),
                        "C19.III": SubcriterionInput(subcriterion_code="C19.III", raw_inputs={}, evidence_docs=[doc]),
                    }
                )
                res = eval_fn(p_in, self.context, self.validator)
                c19_i_res = res.subcriteria_results["C19.I"]
                self.assertEqual(c19_i_res.raw_score, expected_score)
                self.assertEqual(c19_i_res.evidence_gated_score, expected_score)
                self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)

    # -------------------------------------------------------------
    # C20: Quality Assurance, NAAC/NIRF/AISHE (Max: 5)
    # Decomposed: C20.1 (Max 2, A/A+/A++/B++: 2, B/B+: 1) + C20.2 (1) + C20.3 (1) + C20.4 (1)
    # Mandatory evidence: EVID_C20_NAAC_CERT
    # -------------------------------------------------------------
    def test_c20_naac_quality(self):
        eval_fn = COLLEGE_EVALUATORS["C20"]
        doc = self._make_verified_doc("EVID_C20_NAAC_CERT")
        p_in = ParameterInput(
            parameter_code="C20",
            subcriteria_inputs={
                "C20.1": SubcriterionInput(subcriterion_code="C20.1", raw_inputs={"naac_grade": "A+"}, evidence_docs=[doc]),  # 2 marks
                "C20.2": SubcriterionInput(subcriterion_code="C20.2", raw_inputs={"verified": True}, evidence_docs=[doc]),  # 1 mark
                "C20.3": SubcriterionInput(subcriterion_code="C20.3", raw_inputs={"verified": True}, evidence_docs=[doc]),  # 1 mark
                "C20.4": SubcriterionInput(subcriterion_code="C20.4", raw_inputs={"verified": True}, evidence_docs=[doc]),  # 1 mark
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    # -------------------------------------------------------------
    # C21: Cultural Activities, Constitutional Values (Declared Max: 4, Criteria Sum: 3)
    # CRITICAL: C21 has source arithmetic deficit (C21.1: 2, C21.2: 1 = 3 vs Max 4)
    # Mandatory evidence: EVID_C21_ACTIVITY_REPORTS
    # -------------------------------------------------------------
    def test_c21_arithmetic_deficit(self):
        eval_fn = COLLEGE_EVALUATORS["C21"]
        doc = self._make_verified_doc("EVID_C21_ACTIVITY_REPORTS")
        p_in = ParameterInput(
            parameter_code="C21",
            subcriteria_inputs={
                "C21.1": SubcriterionInput(subcriterion_code="C21.1", raw_inputs={"activities_count": 15}, evidence_docs=[doc]),  # 2 marks
                "C21.2": SubcriterionInput(subcriterion_code="C21.2", raw_inputs={"verified": True}, evidence_docs=[doc]),  # 1 mark
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        # Raw score is 3.0, but resolution status must be SOURCE_INCONSISTENCY
        # and final_score must be None!
        self.assertEqual(res.raw_score, 3.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.SOURCE_INCONSISTENCY)
        self.assertIsNone(res.final_score)

    # -------------------------------------------------------------
    # C22: Governance, Student Feedback (Max: 2)
    # Decomposed: C22.1 (1) + C22.2 (1) = Max 2
    # Mandatory evidence: EVID_C22_NODAL_ORDER
    # -------------------------------------------------------------
    def test_c22_governance_feedback(self):
        eval_fn = COLLEGE_EVALUATORS["C22"]
        doc = self._make_verified_doc("EVID_C22_NODAL_ORDER")
        p_in = ParameterInput(
            parameter_code="C22",
            subcriteria_inputs={
                "C22.1": SubcriterionInput(subcriterion_code="C22.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C22.2": SubcriterionInput(subcriterion_code="C22.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
            }
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 2.0)
