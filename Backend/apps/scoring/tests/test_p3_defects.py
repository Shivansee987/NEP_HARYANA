"""
NEP Excellence Awards 2026 - Phase 4B-D P3 Defect Correction Regression Test Suite

Covers:
- P3-01: Omitted dates falling back to HOI certification
- P3-02: Double-counting conflicts missing from parameter traces
- P3-03: C20.1 NAAC grade-string vs numeric metadata inconsistency
- P3-04: Successive reviewer adjustments overwriting trace history
"""
from datetime import date, datetime
from typing import Optional
from django.test import TestCase

from apps.scoring.adjustments import ReviewerAdjustmentService
from apps.scoring.domain import (
    AssessmentContext,
    AssessmentInput,
    AssessmentPeriod,
    AssetEntity,
    EvidenceDocument,
    FrameworkResult,
    ParameterInput,
    ParameterResult,
    ReviewerAdjustment,
    SubcriterionInput,
    SubcriterionResult,
)
from apps.scoring.engine import NEP2026ScoringEngine
from apps.scoring.enums import (
    CertificationStatus,
    DoubleCountingRule,
    EvaluationType,
    EvidenceState,
    FrameworkType,
    GatingStatus,
    InstitutionType,
    PeriodRule,
    ResolutionStatus,
)
from apps.scoring.evaluators.double_counting import DoubleCountingValidator
from apps.scoring.evaluators.periods import validate_period
from apps.scoring.rules.college import COLLEGE_EVALUATORS
from apps.scoring.rules.definitions import COLLEGE_PARAMETERS, UNIVERSITY_PARAMETERS
from apps.scoring.rules.university import UNIVERSITY_EVALUATORS


class P3_01_TemporalValidationHOIFallbackTests(TestCase):
    """
    P3-01 Regression Tests:
    1. valid date inside assessment period -> eligible
    2. valid date before assessment period -> not eligible
    3. valid date after assessment period -> not eligible
    4. omitted required date -> does NOT use HOI certification date
    5. omitted date cannot manufacture an eligible score
    6. HOI certification date does not substitute for missing activity/document date
    """

    def setUp(self):
        self.period = AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30))

    def test_1_valid_date_inside_assessment_period_eligible(self):
        ok, reason = validate_period(date(2025, 10, 15), PeriodRule.PERIOD_SENSITIVE, self.period)
        self.assertTrue(ok)
        self.assertIn("within assessment period", reason)

    def test_2_valid_date_before_assessment_period_not_eligible(self):
        ok, reason = validate_period(date(2025, 5, 31), PeriodRule.PERIOD_SENSITIVE, self.period)
        self.assertFalse(ok)
        self.assertIn("OUTSIDE assessment period", reason)

    def test_3_valid_date_after_assessment_period_not_eligible(self):
        ok, reason = validate_period(date(2026, 7, 1), PeriodRule.PERIOD_SENSITIVE, self.period)
        self.assertFalse(ok)
        self.assertIn("OUTSIDE assessment period", reason)

    def test_4_omitted_required_date_does_not_use_hoi_certification(self):
        ok, reason = validate_period(None, PeriodRule.PERIOD_SENSITIVE, self.period)
        self.assertFalse(ok)
        self.assertIn("fallback to HOI certification date is not permitted", reason)

    def test_5_omitted_date_cannot_manufacture_eligible_score(self):
        """When an institution provides HOI certification date without activity date, score is not manufactured."""
        context = AssessmentContext(
            assessment_id="test-p3-01-omitted-date",
            institution_id="inst-p3-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        validator = DoubleCountingValidator()
        doc = EvidenceDocument(
            document_id="doc-p3-01",
            document_type="EVID_U18_POLICY",
            status=EvidenceState.EVIDENCE_VERIFIED,
        )
        # Supply hoi_certification_date attempting to substitute for missing activity_date
        sub_in = SubcriterionInput(
            subcriterion_code="U18.1",
            raw_inputs={"verified": True, "hoi_certification_date": "2025-10-01"},
            evidence_docs=[doc],
            activity_date=None,
        )
        p_in = ParameterInput(
            parameter_code="U18",
            subcriteria_inputs={"U18.1": sub_in},
        )
        eval_fn = UNIVERSITY_EVALUATORS["U18"]
        res = eval_fn(p_in, context, validator)
        # U18.1 raw score must be zero due to rejected HOI fallback
        sub_res = res.subcriteria_results["U18.1"]
        self.assertEqual(sub_res.raw_score, 0.0)
        self.assertFalse(sub_res.trace["period_validation"]["valid"])
        self.assertIn("HOI certification date cannot substitute", sub_res.trace["period_validation"]["reason"])

    def test_6_hoi_certification_date_does_not_substitute_for_activity_date(self):
        ok, reason = validate_period(
            None,
            PeriodRule.PERIOD_SENSITIVE,
            self.period,
            hoi_certification_date=date(2025, 11, 1),
        )
        self.assertFalse(ok)
        self.assertIn("HOI certification date cannot substitute for missing activity/document date", reason)


class P3_02_DoubleCountingParameterTraceElevationTests(TestCase):
    """
    P3-02 Regression Tests:
    1. no conflict -> no false conflict trace
    2. duplicate identity -> conflict detected
    3. conflict appears in subcriterion trace
    4. conflict appears in parameter trace
    5. affected entity/output identity is retained
    6. score consequence remains correct
    7. unrelated parameters are not polluted with the conflict
    """

    def setUp(self):
        self.period = AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30))
        self.context = AssessmentContext(
            assessment_id="test-p3-02-dc-trace",
            institution_id="inst-p3-02",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        self.engine = NEP2026ScoringEngine()

    def test_1_no_conflict_no_false_conflict_trace(self):
        validator = DoubleCountingValidator()
        doc = EvidenceDocument(document_id="doc-u8", document_type="EVID_U8_INCUBATION", status=EvidenceState.EVIDENCE_VERIFIED)
        ent1 = AssetEntity(entity_id="ent-1", entity_type="STARTUP", identifier_key="STARTUP_REG_001")
        p_in = ParameterInput(
            parameter_code="U8",
            subcriteria_inputs={
                "U8.A": SubcriterionInput(
                    subcriterion_code="U8.A",
                    raw_inputs={"startups_count": 1},
                    entities=[ent1],
                    evidence_docs=[doc],
                )
            },
        )
        eval_fn = UNIVERSITY_EVALUATORS["U8"]
        res = eval_fn(p_in, self.context, validator)
        self.assertEqual(len(validator.conflicts), 0)
        self.assertNotIn("duplicates_detected", res.trace)
        self.assertNotIn("double_counting_conflicts", res.trace)

    def test_2_through_6_duplicate_identity_trace_elevation_and_score_consequence(self):
        """Proves duplicate conflict appears in subcriterion trace, parameter trace, retains identity, and adjusts score."""
        validator = DoubleCountingValidator()
        doc_u8 = EvidenceDocument(document_id="doc-u8", document_type="EVID_U8_INCUBATION", status=EvidenceState.EVIDENCE_VERIFIED)
        doc_u9 = EvidenceDocument(document_id="doc-u9", document_type="EVID_U9_MOU_COPIES", status=EvidenceState.EVIDENCE_VERIFIED)

        # Entity registered first under U8.A
        ent_dup = AssetEntity(entity_id="shared-ent-01", entity_type="STARTUP", identifier_key="VENTURE_ALPHA_999")

        p_u8 = ParameterInput(
            parameter_code="U8",
            subcriteria_inputs={
                "U8.A": SubcriterionInput(
                    subcriterion_code="U8.A",
                    raw_inputs={"startups_count": 1},
                    entities=[ent_dup],
                    evidence_docs=[doc_u8],
                )
            },
        )
        res_u8 = UNIVERSITY_EVALUATORS["U8"](p_u8, self.context, validator)
        self.assertEqual(len(validator.conflicts), 0)

        # Attempt to claim same entity under U9.B
        p_u9 = ParameterInput(
            parameter_code="U9",
            subcriteria_inputs={
                "U9.A": SubcriterionInput(
                    subcriterion_code="U9.A",
                    raw_inputs={"active_percentage": 80.0},
                    evidence_docs=[doc_u9],
                ),
                "U9.B": SubcriterionInput(
                    subcriterion_code="U9.B",
                    raw_inputs={"activities_count": 1},
                    entities=[ent_dup],  # Duplicate claim!
                    evidence_docs=[doc_u9],
                ),
            },
        )
        res_u9 = UNIVERSITY_EVALUATORS["U9"](p_u9, self.context, validator)

        # 2. Duplicate conflict detected
        self.assertEqual(len(validator.conflicts), 1)

        # 3. Conflict appears in subcriterion trace
        sub_trace = res_u9.subcriteria_results["U9.B"].trace
        self.assertIn("double_counting", sub_trace)
        self.assertEqual(len(sub_trace["double_counting"]["duplicates_detected"]), 1)
        sub_conflict = sub_trace["double_counting"]["duplicates_detected"][0]
        self.assertEqual(sub_conflict["entity_key"], "STARTUP::VENTURE_ALPHA_999")
        self.assertEqual(sub_conflict["first_claimed_by"], "U8.A")
        self.assertEqual(sub_conflict["rejected_in"], "U9.B")

        # 4. Conflict appears in parameter trace
        self.assertIn("duplicates_detected", res_u9.trace)
        self.assertIn("double_counting_conflicts", res_u9.trace)
        param_conflict = res_u9.trace["duplicates_detected"][0]

        # 5. Affected entity identity retained
        self.assertEqual(param_conflict["entity_key"], "STARTUP::VENTURE_ALPHA_999")
        self.assertEqual(param_conflict["entity_id"], "shared-ent-01")
        self.assertEqual(param_conflict["first_claimed_parameter"], "U8")
        self.assertEqual(param_conflict["affected_parameter"], "U9")

        # 6. Score consequence: Entity count reduced from 1 to 0 -> 0 marks awarded for U9.B
        self.assertEqual(res_u9.subcriteria_results["U9.B"].raw_score, 0.0)
        self.assertEqual(param_conflict["score_consequence"], "Entity rejected from subcriterion count; score adjusted based on remaining valid entities.")
        self.assertEqual(param_conflict["resulting_state"], "REJECTED_DUPLICATE")

    def test_7_unrelated_parameters_not_polluted_with_conflict(self):
        """In a full engine evaluation, only affected parameters carry conflict traces; unrelated parameters remain clean."""
        doc = EvidenceDocument(document_id="doc-gen", document_type="EVID_U1_APPROVAL", status=EvidenceState.EVIDENCE_VERIFIED)
        ent_dup = AssetEntity(entity_id="ent-dup-10", entity_type="MOU", identifier_key="MOU_PARTNER_X")

        u1_in = ParameterInput(
            parameter_code="U1",
            subcriteria_inputs={
                "U1.1": SubcriterionInput(
                    subcriterion_code="U1.1",
                    raw_inputs={"programmes_count": 5},
                    evidence_docs=[doc],
                )
            },
        )
        u8_in = ParameterInput(
            parameter_code="U8",
            subcriteria_inputs={
                "U8.A": SubcriterionInput(
                    subcriterion_code="U8.A",
                    raw_inputs={"startups_count": 1},
                    entities=[ent_dup],
                    evidence_docs=[doc],
                )
            },
        )
        u9_in = ParameterInput(
            parameter_code="U9",
            subcriteria_inputs={
                "U9.B": SubcriterionInput(
                    subcriterion_code="U9.B",
                    raw_inputs={"activities_count": 1},
                    entities=[ent_dup],  # Duplicate
                    evidence_docs=[doc],
                )
            },
        )
        assessment_input = AssessmentInput(
            context=self.context,
            parameters={"U1": u1_in, "U8": u8_in, "U9": u9_in},
        )
        fw_res = self.engine.score_assessment(assessment_input)

        # U9 is affected: must have conflict trace
        self.assertIn("duplicates_detected", fw_res.parameter_results["U9"].trace)

        # U1 is completely unrelated: must NOT have conflict trace
        self.assertNotIn("duplicates_detected", fw_res.parameter_results["U1"].trace)
        self.assertNotIn("double_counting_conflicts", fw_res.parameter_results["U1"].trace)

        # Global trace contains structured conflict list
        self.assertEqual(fw_res.trace["double_counting_conflicts_count"], 1)
        self.assertEqual(len(fw_res.trace["double_counting_conflicts"]), 1)


class P3_03_C20_1_NAACRepresentationTests(TestCase):
    """
    P3-03 Regression Tests:
    1. valid NAAC grade string
    2. valid corresponding numeric metadata
    3. equivalent string + numeric representation
    4. contradictory string + numeric representation
    5. malformed/unsupported grade string
    6. missing NAAC value
    7. correct resulting C20.1 state/score
    """

    def setUp(self):
        self.period = AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30))
        self.context = AssessmentContext(
            assessment_id="test-p3-03-c20",
            institution_id="inst-p3-03",
            institution_type=InstitutionType.COLLEGE,
            framework=FrameworkType.COLLEGE_2026,
            assessment_period=self.period,
        )
        self.validator = DoubleCountingValidator()
        self.doc = EvidenceDocument(
            document_id="doc-c20",
            document_type="EVID_C20_NAAC_CERT",
            status=EvidenceState.EVIDENCE_VERIFIED,
        )

    def _eval_c20_with_c20_1(self, raw_inputs: dict) -> ParameterResult:
        p_in = ParameterInput(
            parameter_code="C20",
            subcriteria_inputs={
                "C20.1": SubcriterionInput(
                    subcriterion_code="C20.1",
                    raw_inputs=raw_inputs,
                    evidence_docs=[self.doc],
                )
            },
        )
        eval_fn = COLLEGE_EVALUATORS["C20"]
        return eval_fn(p_in, self.context, self.validator)

    def test_1_valid_naac_grade_string(self):
        # Tier 1 grades -> 2.0 marks
        for g in ["A++", "A+", "A", "B++", " a+ ", "A"]:
            res = self._eval_c20_with_c20_1({"naac_grade": g})
            sub = res.subcriteria_results["C20.1"]
            self.assertEqual(sub.raw_score, 2.0)
            self.assertEqual(sub.resolution_status, ResolutionStatus.CALCULABLE)

        # Tier 2 grades -> 1.0 mark
        for g in ["B+", "B", "b+"]:
            res = self._eval_c20_with_c20_1({"naac_grade": g})
            sub = res.subcriteria_results["C20.1"]
            self.assertEqual(sub.raw_score, 1.0)
            self.assertEqual(sub.resolution_status, ResolutionStatus.CALCULABLE)

        # Lower grades -> 0.0 marks
        for g in ["C", "D", "UNACCREDITED"]:
            res = self._eval_c20_with_c20_1({"naac_grade": g})
            sub = res.subcriteria_results["C20.1"]
            self.assertEqual(sub.raw_score, 0.0)
            self.assertEqual(sub.resolution_status, ResolutionStatus.CALCULABLE)

    def test_2_valid_corresponding_numeric_metadata(self):
        # Numeric 2.0 -> 2.0 marks
        res2 = self._eval_c20_with_c20_1({"naac_score": 2.0})
        self.assertEqual(res2.subcriteria_results["C20.1"].raw_score, 2.0)
        self.assertEqual(res2.subcriteria_results["C20.1"].resolution_status, ResolutionStatus.CALCULABLE)

        # Numeric 1.0 -> 1.0 mark
        res1 = self._eval_c20_with_c20_1({"score": 1.0})
        self.assertEqual(res1.subcriteria_results["C20.1"].raw_score, 1.0)
        self.assertEqual(res1.subcriteria_results["C20.1"].resolution_status, ResolutionStatus.CALCULABLE)

        # Numeric 0.0 -> 0.0 marks
        res0 = self._eval_c20_with_c20_1({"naac_points": 0.0})
        self.assertEqual(res0.subcriteria_results["C20.1"].raw_score, 0.0)
        self.assertEqual(res0.subcriteria_results["C20.1"].resolution_status, ResolutionStatus.CALCULABLE)

    def test_3_equivalent_string_and_numeric_representation(self):
        # "A+" and 2.0 -> equivalent (2.0)
        res = self._eval_c20_with_c20_1({"naac_grade": "A+", "naac_score": 2.0})
        sub = res.subcriteria_results["C20.1"]
        self.assertEqual(sub.raw_score, 2.0)
        self.assertEqual(sub.resolution_status, ResolutionStatus.CALCULABLE)
        self.assertEqual(sub.trace["naac_evaluation"]["status"], "EQUIVALENT")

        # "B+" and 1.0 -> equivalent (1.0)
        res_b = self._eval_c20_with_c20_1({"grade": "B+", "score": 1.0})
        sub_b = res_b.subcriteria_results["C20.1"]
        self.assertEqual(sub_b.raw_score, 1.0)
        self.assertEqual(sub_b.resolution_status, ResolutionStatus.CALCULABLE)
        self.assertEqual(sub_b.trace["naac_evaluation"]["status"], "EQUIVALENT")

    def test_4_contradictory_string_and_numeric_representation(self):
        """Contradictory string ('A+') and numeric (1.0) must be flagged INVALID_INPUT and block certification."""
        res = self._eval_c20_with_c20_1({"naac_grade": "A+", "naac_score": 1.0})
        sub = res.subcriteria_results["C20.1"]
        self.assertEqual(sub.raw_score, 0.0)
        self.assertEqual(sub.resolution_status, ResolutionStatus.INVALID_INPUT)
        self.assertIsNone(sub.final_score)
        self.assertEqual(sub.trace["naac_evaluation"]["status"], "CONTRADICTORY")
        self.assertIn("Contradictory NAAC representations", sub.trace["naac_evaluation"]["reason"])

        # Parameter-level result must also reflect INVALID_INPUT and final_score = None
        self.assertEqual(res.resolution_status, ResolutionStatus.INVALID_INPUT)
        self.assertIsNone(res.final_score)
        self.assertIn("naac_contradiction", res.trace)

        # In full assessment engine, contradiction blocks certification
        engine = NEP2026ScoringEngine()
        p_in = ParameterInput(
            parameter_code="C20",
            subcriteria_inputs={
                "C20.1": SubcriterionInput(
                    subcriterion_code="C20.1",
                    raw_inputs={"naac_grade": "A+", "naac_score": 1.0},
                    evidence_docs=[self.doc],
                )
            },
        )
        assessment_input = AssessmentInput(context=self.context, parameters={"C20": p_in})
        fw_res = engine.score_assessment(assessment_input)
        self.assertNotEqual(fw_res.certification_status, CertificationStatus.FINALIZABLE)
        self.assertIsNone(fw_res.final_certified_total)
        self.assertTrue(any("Parameter C20 is BLOCKED: Input data is invalid, contradictory, or malformed." in r for r in fw_res.blocking_reasons))

    def test_5_malformed_unsupported_grade_string(self):
        res = self._eval_c20_with_c20_1({"naac_grade": "XYZ_UNSUPPORTED_GRADE"})
        sub = res.subcriteria_results["C20.1"]
        self.assertEqual(sub.raw_score, 0.0)
        self.assertEqual(sub.resolution_status, ResolutionStatus.INVALID_INPUT)
        self.assertIsNone(sub.final_score)
        self.assertEqual(sub.trace["naac_evaluation"]["status"], "MALFORMED_INPUT")

    def test_6_missing_naac_value(self):
        res = self._eval_c20_with_c20_1({})
        sub = res.subcriteria_results["C20.1"]
        self.assertEqual(sub.raw_score, 0.0)
        self.assertEqual(sub.resolution_status, ResolutionStatus.CALCULABLE)
        self.assertEqual(sub.trace["naac_evaluation"]["status"], "MISSING_VALUE")

    def test_7_correct_resulting_c20_1_state_and_score(self):
        """Full C20 evaluation with verified documents and valid grade yields certified score."""
        p_in = ParameterInput(
            parameter_code="C20",
            subcriteria_inputs={
                "C20.1": SubcriterionInput(subcriterion_code="C20.1", raw_inputs={"naac_grade": "A++"}, evidence_docs=[self.doc]),
                "C20.2": SubcriterionInput(subcriterion_code="C20.2", raw_inputs={"verified": True}, evidence_docs=[self.doc]),
                "C20.3": SubcriterionInput(subcriterion_code="C20.3", raw_inputs={"verified": True}, evidence_docs=[self.doc]),
                "C20.4": SubcriterionInput(subcriterion_code="C20.4", raw_inputs={"verified": True}, evidence_docs=[self.doc]),
            },
        )
        res = COLLEGE_EVALUATORS["C20"](p_in, self.context, self.validator)
        self.assertEqual(res.raw_score, 5.0)
        self.assertEqual(res.evidence_gated_score, 5.0)
        self.assertEqual(res.final_score, 5.0)
        self.assertEqual(res.resolution_status, ResolutionStatus.CALCULABLE)


class P3_04_ReviewerAdjustmentAppendOnlyHistoryTests(TestCase):
    """
    P3-04 Regression Tests:
    1. first adjustment is retained
    2. second adjustment is appended
    3. first adjustment is not overwritten
    4. ordering is deterministic
    5. accepted + accepted history is preserved
    6. accepted + rejected history is preserved
    7. rejection still blocks certification
    8. multiple adjustments remain auditable
    """

    def setUp(self):
        self.sub = SubcriterionResult(
            subcriterion_code="U1.1",
            raw_score=2.0,
            evidence_gated_score=2.0,
            review_adjusted_score=None,
            final_score=2.0,
            max_score=4.0,
            resolution_status=ResolutionStatus.CALCULABLE,
            gating_status=GatingStatus.PASSED_EVIDENCE_VERIFIED,
            trace={},
        )
        self.param = ParameterResult(
            parameter_code="U1",
            max_marks=4.0,
            raw_score=2.0,
            evidence_gated_score=2.0,
            review_adjusted_score=None,
            final_score=2.0,
            resolution_status=ResolutionStatus.CALCULABLE,
            aggregation_strategy=EvaluationType.SUM,
            subcriteria_results={"U1.1": self.sub},
            trace={},
        )
        self.fw = FrameworkResult(
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_id="test-p3-04-audit",
            institution_id="inst-p3-04",
            calculation_id="calc-p3-04",
            version_index=1,
            timestamp=datetime.utcnow().isoformat() + "Z",
            raw_total=2.0,
            evidence_gated_total=2.0,
            final_certified_total=2.0,
            max_marks=100.0,
            certification_status=CertificationStatus.FINALIZABLE,
            blocking_reasons=[],
            parameter_results={"U1": self.param},
            trace={},
        )

    def test_1_through_5_accepted_plus_accepted_history_preserved(self):
        # Adjustment 1: 2.0 -> 3.0
        adj1 = ReviewerAdjustment(
            subcriterion_code="U1.1",
            reviewer_id="reviewer-01",
            original_score=2.0,
            adjusted_score=3.0,
            reason="Additional valid programme credit documentation verified.",
        )
        ok1, err1 = ReviewerAdjustmentService.validate_and_apply_adjustment(self.fw, adj1)
        self.assertTrue(ok1)
        self.assertIsNone(err1)

        # 1. First adjustment is retained
        self.assertIn("reviewer_adjustments", self.fw.trace)
        self.assertEqual(len(self.fw.trace["reviewer_adjustments"]), 1)
        rec1 = self.fw.trace["reviewer_adjustments"][0]
        self.assertEqual(rec1["sequence"], 1)
        self.assertEqual(rec1["reviewer_id"], "reviewer-01")
        self.assertEqual(rec1["previous_score"], 2.0)
        self.assertEqual(rec1["adjusted_score"], 3.0)
        self.assertEqual(rec1["status"], "ACCEPTED")

        # Adjustment 2: 3.0 -> 2.5
        adj2 = ReviewerAdjustment(
            subcriterion_code="U1.1",
            reviewer_id="reviewer-senior-02",
            original_score=3.0,
            adjusted_score=2.5,
            reason="Senior audit moderation adjusted programme credit weighting.",
        )
        ok2, err2 = ReviewerAdjustmentService.validate_and_apply_adjustment(self.fw, adj2)
        self.assertTrue(ok2)
        self.assertIsNone(err2)

        # 2. Second adjustment is appended
        self.assertEqual(len(self.fw.trace["reviewer_adjustments"]), 2)
        rec2 = self.fw.trace["reviewer_adjustments"][1]
        self.assertEqual(rec2["sequence"], 2)
        self.assertEqual(rec2["reviewer_id"], "reviewer-senior-02")
        self.assertEqual(rec2["previous_score"], 3.0)
        self.assertEqual(rec2["adjusted_score"], 2.5)
        self.assertEqual(rec2["status"], "ACCEPTED")

        # 3. First adjustment is NOT overwritten
        self.assertEqual(self.fw.trace["reviewer_adjustments"][0]["sequence"], 1)
        self.assertEqual(self.fw.trace["reviewer_adjustments"][0]["adjusted_score"], 3.0)

        # 4. Ordering is deterministic
        self.assertEqual(self.fw.trace["reviewer_adjustments"][0]["sequence"], 1)
        self.assertEqual(self.fw.trace["reviewer_adjustments"][1]["sequence"], 2)

        # 5. Both records in subcriterion trace as well
        sub_history = self.sub.trace["reviewer_adjustments"]
        self.assertEqual(len(sub_history), 2)
        self.assertEqual(sub_history[0]["adjusted_score"], 3.0)
        self.assertEqual(sub_history[1]["adjusted_score"], 2.5)

    def test_6_through_8_accepted_plus_rejected_history_preserved_and_certification_blocked(self):
        # Adjustment 1 (Valid): 2.0 -> 3.0
        adj1 = ReviewerAdjustment(
            subcriterion_code="U1.1",
            reviewer_id="reviewer-01",
            original_score=2.0,
            adjusted_score=3.0,
            reason="Additional valid programme credit documentation verified.",
        )
        ok1, _ = ReviewerAdjustmentService.validate_and_apply_adjustment(self.fw, adj1)
        self.assertTrue(ok1)

        # Adjustment 2 (Invalid - exceeds max 4.0): 3.0 -> 99.0
        adj2 = ReviewerAdjustment(
            subcriterion_code="U1.1",
            reviewer_id="reviewer-rogue-03",
            original_score=3.0,
            adjusted_score=99.0,
            reason="Exorbitant out-of-bounds adjustment attempt.",
        )
        ok2, err2 = ReviewerAdjustmentService.validate_and_apply_adjustment(self.fw, adj2)
        self.assertFalse(ok2)
        self.assertIn("exceeds subcriterion maximum", err2)

        # 6. Accepted + rejected history preserved in append-only sequence
        history = self.fw.trace["reviewer_adjustments"]
        self.assertEqual(len(history), 2)

        rec1 = history[0]
        self.assertEqual(rec1["sequence"], 1)
        self.assertEqual(rec1["status"], "ACCEPTED")
        self.assertEqual(rec1["adjusted_score"], 3.0)

        rec2 = history[1]
        self.assertEqual(rec2["sequence"], 2)
        self.assertEqual(rec2["status"], "REJECTED")
        self.assertEqual(rec2["proposed_score"], 99.0)
        self.assertEqual(rec2["rejection_reason"], err2)
        self.assertEqual(rec2["resulting_score"], 3.0)

        # 7. Rejection still blocks certification
        self.assertEqual(self.fw.certification_status, CertificationStatus.BLOCKED_BY_VALIDATION)
        self.assertIsNone(self.fw.final_certified_total)
        self.assertTrue(any("Reviewer adjustment rejected" in r for r in self.fw.blocking_reasons))

        # 8. Complete auditability of all required fields
        for rec in history:
            self.assertIn("sequence", rec)
            self.assertIn("reviewer_id", rec)
            self.assertIn("timestamp", rec)
            self.assertIn("target_subcriterion", rec)
            self.assertIn("target_parameter", rec)
            self.assertIn("previous_score", rec)
            self.assertIn("proposed_score", rec)
            self.assertIn("validation_result", rec)
            self.assertIn("status", rec)
            self.assertIn("rejection_reason", rec)
            self.assertIn("resulting_score", rec)
            self.assertIn("resulting_state", rec)
