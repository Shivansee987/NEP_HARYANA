"""
Unit Tests for College Parameter Inputs Validation and Evaluation (C1–C22)
Verifies input validators, percentage ranges, integer quantities, temporal dates,
and evaluates representative boundary inputs for all 22 parameters using the frozen scoring engine.
Preserves documented source ambiguities (C5, C7, C8, C16, C19.III, C21).
"""
from datetime import date
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
    InstitutionType,
    ResolutionStatus,
)
from apps.scoring.evaluators.double_counting import DoubleCountingValidator
from apps.scoring.rules.college import COLLEGE_EVALUATORS
from apps.college.validators import (
    CollegeValidationError,
    validate_count,
    validate_currency_amount,
    validate_framework_code,
    validate_institution_type,
    validate_percentage,
    validate_temporal_activity_date,
)


class CollegeParameterInputsTests(TestCase):

    def setUp(self):
        self.context = AssessmentContext(
            assessment_id="ASSESS-2026-COL-TEST-001",
            institution_id="C-12345",
            institution_type=InstitutionType.COLLEGE,
            framework=FrameworkType.COLLEGE_2026,
            assessment_period=AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30)),
        )
        self.validator = DoubleCountingValidator()

    def _make_verified_doc(self, doc_type: str) -> EvidenceDocument:
        return EvidenceDocument(
            document_id=f"doc-{doc_type}-test",
            document_type=doc_type,
            status=EvidenceState.EVIDENCE_VERIFIED,
        )

    # -------------------------------------------------------------
    # Domain Input Validators
    # -------------------------------------------------------------
    def test_validate_framework_and_institution(self):
        """Verifies framework and institution type validators."""
        self.assertEqual(validate_framework_code("COLLEGE_2026"), "COLLEGE_2026")
        self.assertEqual(validate_framework_code("COLLEGE"), "COLLEGE_2026")
        with self.assertRaises(CollegeValidationError):
            validate_framework_code("UNIVERSITY_2026")

        self.assertEqual(validate_institution_type("COLLEGE"), "COLLEGE")
        with self.assertRaises(CollegeValidationError):
            validate_institution_type("UNIVERSITY")

    def test_validate_percentage_bounds(self):
        """Verifies percentage validation within [0.0, 100.0]."""
        self.assertEqual(validate_percentage(0.0), 0.0)
        self.assertEqual(validate_percentage(100.0), 100.0)
        self.assertEqual(validate_percentage("75.5"), 75.5)

        with self.assertRaises(CollegeValidationError):
            validate_percentage(-0.1)
        with self.assertRaises(CollegeValidationError):
            validate_percentage(100.1)
        with self.assertRaises(CollegeValidationError):
            validate_percentage("invalid")

    def test_validate_count_quantity(self):
        """Verifies non-negative whole integer counts."""
        self.assertEqual(validate_count(0), 0)
        self.assertEqual(validate_count("15"), 15)

        with self.assertRaises(CollegeValidationError):
            validate_count(-1)
        with self.assertRaises(CollegeValidationError):
            validate_count("3.14")  # Non-integer rejected without silent truncation

    def test_validate_currency_amount(self):
        """Verifies non-negative monetary amounts."""
        self.assertEqual(validate_currency_amount(0.0), 0.0)
        self.assertEqual(validate_currency_amount("100000.50"), 100000.50)

        with self.assertRaises(CollegeValidationError):
            validate_currency_amount(-50.0)

    def test_validate_temporal_activity_date(self):
        """Verifies date enforcement for period-sensitive parameters (2025-07-01 to 2026-06-30)."""
        valid_date = date(2025, 9, 15)
        validate_temporal_activity_date(valid_date, "C2")  # Should not raise

        invalid_early = date(2024, 6, 30)
        with self.assertRaises(CollegeValidationError):
            validate_temporal_activity_date(invalid_early, "C2")

        invalid_late = date(2026, 7, 1)
        with self.assertRaises(CollegeValidationError):
            validate_temporal_activity_date(invalid_late, "C2")

    # -------------------------------------------------------------
    # Boundary Tests for Every Parameter (C1–C22)
    # -------------------------------------------------------------
    def test_c1_idp_boundary(self):
        """C1: IDP implementation targets (max 6.0)."""
        eval_fn = COLLEGE_EVALUATORS["C1"]
        doc = self._make_verified_doc("EVID_C1_APPROVED_IDP")
        p_in = ParameterInput(
            parameter_code="C1",
            subcriteria_inputs={
                "C1.1": SubcriterionInput(
                    subcriterion_code="C1.1",
                    raw_inputs={"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100},
                    evidence_docs=[doc],
                )
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 6.0)

    def test_c2_apprenticeship_boundary(self):
        """C2: Apprenticeship/internships (max 4.0)."""
        eval_fn = COLLEGE_EVALUATORS["C2"]
        doc = self._make_verified_doc("EVID_C2_HOI_CERT")
        p_in = ParameterInput(
            parameter_code="C2",
            subcriteria_inputs={
                "C2.1": SubcriterionInput(
                    subcriterion_code="C2.1",
                    raw_inputs={"students_completed": 76, "eligible_students": 100},  # 76% in (75, 90] -> 3.0
                    evidence_docs=[doc],
                )
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 3.0)

    def test_c3_abc_boundary(self):
        """C3: ABC registration percentage (max 4.0)."""
        eval_fn = COLLEGE_EVALUATORS["C3"]
        doc = self._make_verified_doc("EVID_C3_ABC_DASHBOARD")
        p_in = ParameterInput(
            parameter_code="C3",
            subcriteria_inputs={
                "C3.1": SubcriterionInput(
                    subcriterion_code="C3.1",
                    raw_inputs={"abc_registered_students": 950, "total_enrolled_students": 1000},  # >90% -> 4.0
                    evidence_docs=[doc],
                )
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    def test_c4_supporting_institutes_boundary(self):
        """C4: Supporting other institutes and schools (max 4.0)."""
        eval_fn = COLLEGE_EVALUATORS["C4"]
        doc = self._make_verified_doc("EVID_C4_INSTITUTE_CERTS")
        p_in = ParameterInput(
            parameter_code="C4",
            subcriteria_inputs={
                "C4.A": SubcriterionInput(
                    subcriterion_code="C4.A",
                    raw_inputs={"heis_mentored": 2},
                    evidence_docs=[doc],
                ),
                "C4.B": SubcriterionInput(
                    subcriterion_code="C4.B",
                    raw_inputs={"schools_mentored": 6},
                    evidence_docs=[doc],
                ),
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    def test_c5_enrollment_ambiguity_boundary(self):
        """C5: Student enrollment against sanctioned seats. Preserves exact 75% boundary void."""
        eval_fn = COLLEGE_EVALUATORS["C5"]
        doc = self._make_verified_doc("EVID_C5_SANCTION_LETTER")

        # >=90% -> 2.0
        p_in = ParameterInput(
            parameter_code="C5",
            subcriteria_inputs={
                "C5.1": SubcriterionInput(
                    subcriterion_code="C5.1",
                    raw_inputs={"admitted_students": 92, "sanctioned_intake": 100},
                    evidence_docs=[doc],
                )
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 2.0)

        # Exact 75.0% boundary void -> BOUNDARY_UNRESOLVED
        p_in_void = ParameterInput(
            parameter_code="C5",
            subcriteria_inputs={
                "C5.1": SubcriterionInput(
                    subcriterion_code="C5.1",
                    raw_inputs={"admitted_students": 75, "sanctioned_intake": 100},  # exactly 75.0%
                    evidence_docs=[doc],
                )
            },
        )
        res_void = eval_fn(p_in_void, self.context, self.validator)
        sub_res = res_void.subcriteria_results["C5.1"]
        self.assertEqual(sub_res.resolution_status, ResolutionStatus.BOUNDARY_UNRESOLVED)

    def test_c6_vac_aec_sec_boundary(self):
        """C6: VAC, AEC, SEC courses (max 6.0)."""
        eval_fn = COLLEGE_EVALUATORS["C6"]
        doc = self._make_verified_doc("EVID_C6_COURSE_APPROVAL")
        p_in = ParameterInput(
            parameter_code="C6",
            subcriteria_inputs={
                "C6.1": SubcriterionInput(
                    subcriterion_code="C6.1",
                    raw_inputs={"certified_students": 850, "total_enrolled_students": 1000},  # (80, 90] -> 5.0
                    evidence_docs=[doc],
                )
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    def test_c7_sedg_bridge_ambiguity(self):
        """C7: Bridge courses for SEDGs. Preserves UNRESOLVED_RULE (-3 mark deficit)."""
        eval_fn = COLLEGE_EVALUATORS["C7"]
        doc = self._make_verified_doc("EVID_C7_OFFICE_ORDERS")
        p_in = ParameterInput(
            parameter_code="C7",
            subcriteria_inputs={
                "C7.1": SubcriterionInput(
                    subcriterion_code="C7.1",
                    raw_inputs={"sedg_bridge_students": 95, "total_sedg_students": 100},
                    evidence_docs=[doc],
                )
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertIsNone(res.final_score)

    def test_c8_sarthi_ambiguity(self):
        """C8: NEP-SARTHI nomination. Preserves UNRESOLVED_RULE."""
        eval_fn = COLLEGE_EVALUATORS["C8"]
        doc = self._make_verified_doc("EVID_C8_OFFICE_ORDERS")
        p_in = ParameterInput(
            parameter_code="C8",
            subcriteria_inputs={
                "C8.1": SubcriterionInput(
                    subcriterion_code="C8.1",
                    raw_inputs={"verified": True},
                    evidence_docs=[doc],
                )
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertIsNone(res.final_score)

    def test_c9_career_orientation_boundary(self):
        """C9: Career orientation and placements (max 6.0)."""
        eval_fn = COLLEGE_EVALUATORS["C9"]
        doc = self._make_verified_doc("EVID_C9_FAIR_REGISTER")
        p_in = ParameterInput(
            parameter_code="C9",
            subcriteria_inputs={
                "C9.I": SubcriterionInput(
                    subcriterion_code="C9.I",
                    raw_inputs={"participating_students": 100, "eligible_students": 100},  # 100% -> 3.0
                    evidence_docs=[doc],
                ),
                "C9.II": SubcriterionInput(
                    subcriterion_code="C9.II",
                    raw_inputs={"placed_students": 80},  # 80/100 = 80% >= 75% -> 2.0
                    evidence_docs=[doc],
                ),
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    def test_c10_industry_collaboration_boundary(self):
        """C10: Industry collaboration and MoUs (max 5.0)."""
        eval_fn = COLLEGE_EVALUATORS["C10"]
        doc = self._make_verified_doc("EVID_C10_MOU_DOCS")
        p_in = ParameterInput(
            parameter_code="C10",
            subcriteria_inputs={
                "C10.1": SubcriterionInput(
                    subcriterion_code="C10.1",
                    raw_inputs={"active_mous_count": 5},  # >=5 -> 5.0
                    evidence_docs=[doc],
                )
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    def test_c11_incubation_boundary(self):
        """C11: Incubation, startup cell (max 5.0)."""
        eval_fn = COLLEGE_EVALUATORS["C11"]
        doc = self._make_verified_doc("EVID_C11_REGISTRATION")
        p_in = ParameterInput(
            parameter_code="C11",
            subcriteria_inputs={
                "C11.I": SubcriterionInput(
                    subcriterion_code="C11.I",
                    raw_inputs={"ventures_count": 12},  # 3.0
                    evidence_docs=[doc],
                ),
                "C11.II.a": SubcriterionInput(
                    subcriterion_code="C11.II.a",
                    raw_inputs={"cell_functional": True},  # 1.0
                    evidence_docs=[doc],
                ),
                "C11.II.b": SubcriterionInput(
                    subcriterion_code="C11.II.b",
                    raw_inputs={"monetized_count": 8},  # 8/12 >= 50% -> 1.0
                    evidence_docs=[doc],
                ),
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    def test_c12_alumni_connect_boundary(self):
        """C12: Alumni connect (max 5.0)."""
        eval_fn = COLLEGE_EVALUATORS["C12"]
        doc = self._make_verified_doc("EVID_C12_DATABASE")
        p_in = ParameterInput(
            parameter_code="C12",
            subcriteria_inputs={
                f"C12.{i}": SubcriterionInput(subcriterion_code=f"C12.{i}", raw_inputs={"verified": True}, evidence_docs=[doc])
                for i in range(1, 6)
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    def test_c13_faculty_development_boundary(self):
        """C13: Faculty development (max 4.0)."""
        eval_fn = COLLEGE_EVALUATORS["C13"]
        doc = self._make_verified_doc("EVID_C13_FDP_CERTS")
        p_in = ParameterInput(
            parameter_code="C13",
            subcriteria_inputs={
                "C13.1": SubcriterionInput(
                    subcriterion_code="C13.1",
                    raw_inputs={"trained_faculty": 85, "total_fulltime_faculty": 100},  # >80% -> 4.0
                    evidence_docs=[doc],
                )
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    def test_c14_iks_boundary(self):
        """C14: Indian Languages and IKS (max 4.0)."""
        eval_fn = COLLEGE_EVALUATORS["C14"]
        doc = self._make_verified_doc("EVID_C14_MATERIAL_CERT")
        p_in = ParameterInput(
            parameter_code="C14",
            subcriteria_inputs={
                "C14.A": SubcriterionInput(subcriterion_code="C14.A", raw_inputs={"content_items": 4}, evidence_docs=[doc]),
                "C14.B": SubcriterionInput(subcriterion_code="C14.B", raw_inputs={"iks_activities": 5}, evidence_docs=[doc]),
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 4.0)

    def test_c15_wellbeing_boundary(self):
        """C15: Well-being, sports, yoga (max 6.0)."""
        eval_fn = COLLEGE_EVALUATORS["C15"]
        doc = self._make_verified_doc("EVID_C15_CENTRE_ORDER")
        p_in = ParameterInput(
            parameter_code="C15",
            subcriteria_inputs={
                f"C15.{i}": SubcriterionInput(subcriterion_code=f"C15.{i}", raw_inputs={"verified": True}, evidence_docs=[doc])
                for i in range(1, 7)
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 6.0)

    def test_c16_gender_parity_ambiguity(self):
        """C16: Gender parity initiatives. Preserves UNRESOLVED_RULE (+1 mark excess)."""
        eval_fn = COLLEGE_EVALUATORS["C16"]
        doc = self._make_verified_doc("EVID_C16_ICC_ORDERS")
        p_in = ParameterInput(
            parameter_code="C16",
            subcriteria_inputs={
                f"C16.{i}": SubcriterionInput(subcriterion_code=f"C16.{i}", raw_inputs={"verified": True}, evidence_docs=[doc])
                for i in range(1, 6)
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertIsNone(res.final_score)

    def test_c17_outreach_boundary(self):
        """C17: Outreach, community engagement (max 5.0)."""
        eval_fn = COLLEGE_EVALUATORS["C17"]
        doc = self._make_verified_doc("EVID_C17_STUDENT_LIST")
        p_in = ParameterInput(
            parameter_code="C17",
            subcriteria_inputs={
                "C17.1": SubcriterionInput(
                    subcriterion_code="C17.1",
                    raw_inputs={"participating_students": 95, "total_enrolled_students": 100},  # >90% -> 5.0
                    evidence_docs=[doc],
                )
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    def test_c18_sdg_boundary(self):
        """C18: SDG and green campus (max 5.0)."""
        eval_fn = COLLEGE_EVALUATORS["C18"]
        doc = self._make_verified_doc("EVID_C18_ACTIVITY_REPORTS")
        p_in = ParameterInput(
            parameter_code="C18",
            subcriteria_inputs={
                "C18.1": SubcriterionInput(subcriterion_code="C18.1", raw_inputs={"sdg_activities": 5}, evidence_docs=[doc]),
                "C18.2": SubcriterionInput(subcriterion_code="C18.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C18.3": SubcriterionInput(subcriterion_code="C18.3", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C18.4": SubcriterionInput(subcriterion_code="C18.4", raw_inputs={"verified": True}, evidence_docs=[doc]),
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    def test_c19_patents_and_scopus_ambiguity(self):
        """C19: Patents, research, Scopus. C19.III preserves UNRESOLVED_RULE."""
        eval_fn = COLLEGE_EVALUATORS["C19"]
        doc = self._make_verified_doc("EVID_C19_FILING_CERTS")
        p_in = ParameterInput(
            parameter_code="C19",
            subcriteria_inputs={
                "C19.I": SubcriterionInput(subcriterion_code="C19.I", raw_inputs={"patents_filed": 10}, evidence_docs=[doc]),
                "C19.II": SubcriterionInput(subcriterion_code="C19.II", raw_inputs={"patents_granted": 10}, evidence_docs=[doc]),
                "C19.III": SubcriterionInput(subcriterion_code="C19.III", raw_inputs={"scopus_publications": 50}, evidence_docs=[doc]),
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.subcriteria_results["C19.III"].resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertEqual(res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)
        self.assertIsNone(res.final_score)

    def test_c20_naac_nirf_boundary(self):
        """C20: Quality assurance (max 5.0). NAAC Tier 1 -> 2.0, NIRF, AISHE, IQAC -> 1.0 each."""
        eval_fn = COLLEGE_EVALUATORS["C20"]
        doc = self._make_verified_doc("EVID_C20_NAAC_CERT")
        p_in = ParameterInput(
            parameter_code="C20",
            subcriteria_inputs={
                "C20.1": SubcriterionInput(subcriterion_code="C20.1", raw_inputs={"naac_grade": "A+"}, evidence_docs=[doc]),
                "C20.2": SubcriterionInput(subcriterion_code="C20.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C20.3": SubcriterionInput(subcriterion_code="C20.3", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C20.4": SubcriterionInput(subcriterion_code="C20.4", raw_inputs={"verified": True}, evidence_docs=[doc]),
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)

    def test_c21_cultural_ambiguity(self):
        """C21: Cultural activities. Preserves SOURCE_INCONSISTENCY (3 marks rubric vs 4 max)."""
        eval_fn = COLLEGE_EVALUATORS["C21"]
        doc = self._make_verified_doc("EVID_C21_ACTIVITY_REPORTS")
        p_in = ParameterInput(
            parameter_code="C21",
            subcriteria_inputs={
                "C21.1": SubcriterionInput(subcriterion_code="C21.1", raw_inputs={"activities_count": 15}, evidence_docs=[doc]),
                "C21.2": SubcriterionInput(subcriterion_code="C21.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 3.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.SOURCE_INCONSISTENCY)
        self.assertIsNone(res.final_score)

    def test_c22_governance_feedback_boundary(self):
        """C22: Governance, feedback, and ATR (max 2.0)."""
        eval_fn = COLLEGE_EVALUATORS["C22"]
        doc = self._make_verified_doc("EVID_C22_NODAL_ORDER")
        p_in = ParameterInput(
            parameter_code="C22",
            subcriteria_inputs={
                "C22.1": SubcriterionInput(subcriterion_code="C22.1", raw_inputs={"verified": True}, evidence_docs=[doc]),
                "C22.2": SubcriterionInput(subcriterion_code="C22.2", raw_inputs={"verified": True}, evidence_docs=[doc]),
            },
        )
        res = eval_fn(p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 2.0)
