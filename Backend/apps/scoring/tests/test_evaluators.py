"""
Unit Tests for Core Evaluators: Thresholds, Percentages, Periods, Evidence Gating, Double-Counting
"""
from datetime import date
from django.test import TestCase

from apps.scoring.domain import AssetEntity, AssessmentPeriod, EvidenceDocument, SubcriterionInput
from apps.scoring.enums import (
    DoubleCountingRule,
    EvidenceState,
    GatingStatus,
    PeriodRule,
    ResolutionStatus,
    ThresholdOperator,
)
from apps.scoring.evaluators.counts import validate_count_quantity
from apps.scoring.evaluators.double_counting import DoubleCountingValidator
from apps.scoring.evaluators.evidence_gating import evaluate_evidence
from apps.scoring.evaluators.percentages import calculate_percentage
from apps.scoring.evaluators.periods import validate_period
from apps.scoring.evaluators.thresholds import evaluate_threshold


class EvaluatorTests(TestCase):

    # -------------------------------------------------------------
    # 1. THRESHOLD EVALUATOR TESTS
    # -------------------------------------------------------------
    def test_threshold_operators_exact_matching(self):
        thresholds = [
            {"operator": ThresholdOperator.OP_GT, "min_val": 90.0, "score": 4.0},
            {"operator": ThresholdOperator.OP_GT_AND_LTE, "min_val": 75.0, "max_val": 90.0, "score": 3.0},
            {"operator": ThresholdOperator.OP_GT_AND_LTE, "min_val": 50.0, "max_val": 75.0, "score": 2.0},
            {"operator": ThresholdOperator.OP_LTE, "max_val": 50.0, "score": 1.0},
        ]

        # Test strictly greater than 90.0
        score, op, _, res = evaluate_threshold(90.0001, thresholds)
        self.assertEqual(score, 4.0)
        self.assertEqual(op, ThresholdOperator.OP_GT)
        self.assertEqual(res, ResolutionStatus.CALCULABLE)

        # Boundary test: exactly 90.0 must fall into (75, 90] tier
        score, op, _, res = evaluate_threshold(90.0, thresholds)
        self.assertEqual(score, 3.0)
        self.assertEqual(op, ThresholdOperator.OP_GT_AND_LTE)

        # Boundary test: 75.0 must fall into (50, 75] tier
        score, op, _, res = evaluate_threshold(75.0, thresholds)
        self.assertEqual(score, 2.0)
        self.assertEqual(op, ThresholdOperator.OP_GT_AND_LTE)

        # Boundary test: 50.0 must fall into <= 50 tier
        score, op, _, res = evaluate_threshold(50.0, thresholds)
        self.assertEqual(score, 1.0)
        self.assertEqual(op, ThresholdOperator.OP_LTE)

    def test_threshold_open_interval(self):
        # Open interval test: > 75 and < 90
        thresholds = [
            {"operator": ThresholdOperator.OP_GTE, "min_val": 90.0, "score": 2.0},
            {"operator": ThresholdOperator.OP_GT_AND_LT, "min_val": 75.0, "max_val": 90.0, "score": 1.0},
            {"operator": ThresholdOperator.OP_LT, "max_val": 75.0, "score": 0.0},
        ]
        score, op, _, _ = evaluate_threshold(80.0, thresholds)
        self.assertEqual(score, 1.0)
        self.assertEqual(op, ThresholdOperator.OP_GT_AND_LT)

        # 89.999 is inside
        score, op, _, _ = evaluate_threshold(89.999, thresholds)
        self.assertEqual(score, 1.0)

        # 90.0 is in >= 90
        score, op, _, _ = evaluate_threshold(90.0, thresholds)
        self.assertEqual(score, 2.0)

    def test_known_boundary_void_u5_a(self):
        # U5.A: exactly 50.0% is a mathematical void in source rubric
        voids = [{"exact_val": 50.0, "reason": "U5.A 50% boundary void"}]
        thresholds = [
            {"operator": ThresholdOperator.OP_GT, "min_val": 75.0, "score": 2.0},
            {"operator": ThresholdOperator.OP_GT_AND_LTE, "min_val": 50.0, "max_val": 75.0, "score": 1.0},
            {"operator": ThresholdOperator.OP_LT, "max_val": 50.0, "score": 0.0},
        ]
        score, op, trace, res = evaluate_threshold(50.0, thresholds, boundary_unresolved_conditions=voids)
        self.assertIsNone(score)
        self.assertEqual(op, ThresholdOperator.BOUNDARY_UNRESOLVED)
        self.assertEqual(res, ResolutionStatus.BOUNDARY_UNRESOLVED)
        self.assertTrue(trace["boundary_unresolved"])

        # Non-boundary values around 50%
        score_above, _, _, _ = evaluate_threshold(50.0001, thresholds, boundary_unresolved_conditions=voids)
        self.assertEqual(score_above, 1.0)

        score_below, _, _, _ = evaluate_threshold(49.9999, thresholds, boundary_unresolved_conditions=voids)
        self.assertEqual(score_below, 0.0)

    def test_known_boundary_void_u10_3(self):
        # U10.3: exactly Rs. 1,00,00,000 is a void in source rubric
        voids = [{"exact_val": 10000000.0, "reason": "U10.3 ₹1 Crore boundary void"}]
        thresholds = [
            {"operator": ThresholdOperator.OP_GT, "min_val": 10000000.0, "score": 2.0},
            {"operator": ThresholdOperator.OP_LT, "max_val": 10000000.0, "score": 1.0},
            {"operator": ThresholdOperator.OP_EQ, "target_val": 0.0, "score": 0.0},
        ]
        score, op, trace, res = evaluate_threshold(10000000.0, thresholds, boundary_unresolved_conditions=voids)
        self.assertIsNone(score)
        self.assertEqual(op, ThresholdOperator.BOUNDARY_UNRESOLVED)
        self.assertEqual(res, ResolutionStatus.BOUNDARY_UNRESOLVED)

    def test_known_boundary_void_c5_1(self):
        # C5.1: exactly 75.0% is a void in source rubric
        voids = [{"exact_val": 75.0, "reason": "C5.1 75% boundary void"}]
        thresholds = [
            {"operator": ThresholdOperator.OP_GTE, "min_val": 90.0, "score": 2.0},
            {"operator": ThresholdOperator.OP_GT_AND_LT, "min_val": 75.0, "max_val": 90.0, "score": 1.0},
            {"operator": ThresholdOperator.OP_LT, "max_val": 75.0, "score": 0.0},
        ]
        score, op, trace, res = evaluate_threshold(75.0, thresholds, boundary_unresolved_conditions=voids)
        self.assertIsNone(score)
        self.assertEqual(op, ThresholdOperator.BOUNDARY_UNRESOLVED)
        self.assertEqual(res, ResolutionStatus.BOUNDARY_UNRESOLVED)

    # -------------------------------------------------------------
    # 2. PERCENTAGE CALCULATOR TESTS
    # -------------------------------------------------------------
    def test_percentage_valid_calculation(self):
        pct, trace, valid = calculate_percentage(18, 20)
        self.assertTrue(valid)
        self.assertAlmostEqual(pct, 90.0)
        self.assertEqual(trace["computed_percentage"], 90.0)

    def test_percentage_zero_denominator_zero_numerator(self):
        # Valid baseline cohort with zero population -> 0.0%
        pct, trace, valid = calculate_percentage(0, 0)
        self.assertTrue(valid)
        self.assertEqual(pct, 0.0)

    def test_percentage_zero_denominator_positive_numerator(self):
        # Division by zero contradiction -> invalid
        pct, trace, valid = calculate_percentage(5, 0)
        self.assertFalse(valid)
        self.assertIsNone(pct)
        self.assertIn("error", trace)

    def test_percentage_negative_inputs(self):
        pct, trace, valid = calculate_percentage(-5, 10)
        self.assertFalse(valid)
        self.assertIsNone(pct)

        pct, trace, valid = calculate_percentage(5, -10)
        self.assertFalse(valid)
        self.assertIsNone(pct)

    def test_percentage_numerator_exceeds_denominator_standard(self):
        # For standard metrics, numerator cannot exceed denominator
        pct, trace, valid = calculate_percentage(110, 100, allow_over_enrollment=False)
        self.assertFalse(valid)
        self.assertIsNone(pct)

    def test_percentage_numerator_exceeds_denominator_supernumerary(self):
        # C5 supernumerary enrollment exception
        pct, trace, valid = calculate_percentage(110, 100, allow_over_enrollment=True)
        self.assertTrue(valid)
        self.assertEqual(pct, 110.0)

    # -------------------------------------------------------------
    # 3. PERIOD VALIDATION TESTS
    # -------------------------------------------------------------
    def test_period_sensitive_within_academic_year(self):
        period = AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30))
        
        # Valid date
        ok, _ = validate_period(date(2025, 10, 15), PeriodRule.PERIOD_SENSITIVE, period)
        self.assertTrue(ok)

        # Before period
        ok, reason = validate_period(date(2025, 5, 20), PeriodRule.PERIOD_SENSITIVE, period)
        self.assertFalse(ok)
        self.assertIn("OUTSIDE", reason)

        # After period
        ok, reason = validate_period(date(2026, 8, 1), PeriodRule.PERIOD_SENSITIVE, period)
        self.assertFalse(ok)
        self.assertIn("OUTSIDE", reason)

    def test_period_multi_period_routing(self):
        period = AssessmentPeriod()
        ok_a, _ = validate_period(None, PeriodRule.MULTI_PERIOD, period, target_academic_year="2024-25")
        self.assertTrue(ok_a)

        ok_b, _ = validate_period(None, PeriodRule.MULTI_PERIOD, period, target_academic_year="2025-26")
        self.assertTrue(ok_b)

        ok_c, _ = validate_period(None, PeriodRule.MULTI_PERIOD, period, target_academic_year="2023-24")
        self.assertFalse(ok_c)

    def test_period_insensitive(self):
        period = AssessmentPeriod()
        ok, _ = validate_period(date(2022, 1, 1), PeriodRule.PERIOD_INSENSITIVE, period)
        self.assertTrue(ok)

    # -------------------------------------------------------------
    # 4. EVIDENCE GATING TESTS
    # -------------------------------------------------------------
    def test_evidence_missing(self):
        # Mandatory evidence missing -> FAILED_EVIDENCE_ABSENT, multiplier = 0.0
        status, mult, _ = evaluate_evidence(["EVID_U1_APPROVAL"], [])
        self.assertEqual(status, GatingStatus.FAILED_EVIDENCE_ABSENT)
        self.assertEqual(mult, 0.0)

    def test_evidence_pending(self):
        # Evidence present but pending verification -> multiplier = 0.0 for earned score
        docs = [EvidenceDocument(document_id="D1", document_type="EVID_U1_APPROVAL", status=EvidenceState.EVIDENCE_PENDING)]
        status, mult, _ = evaluate_evidence(["EVID_U1_APPROVAL"], docs)
        self.assertEqual(status, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)
        self.assertEqual(mult, 0.0)

    def test_evidence_present_unverified(self):
        # Evidence present but not yet verified -> multiplier = 0.0
        docs = [EvidenceDocument(document_id="D1", document_type="EVID_U1_APPROVAL", status=EvidenceState.EVIDENCE_PRESENT)]
        status, mult, _ = evaluate_evidence(["EVID_U1_APPROVAL"], docs)
        self.assertEqual(status, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)
        self.assertEqual(mult, 0.0)

    def test_evidence_rejected(self):
        # Evidence rejected -> FAILED_EVIDENCE_REJECTED, multiplier = 0.0
        docs = [EvidenceDocument(document_id="D1", document_type="EVID_U1_APPROVAL", status=EvidenceState.EVIDENCE_REJECTED)]
        status, mult, _ = evaluate_evidence(["EVID_U1_APPROVAL"], docs)
        self.assertEqual(status, GatingStatus.FAILED_EVIDENCE_REJECTED)
        self.assertEqual(mult, 0.0)

    def test_evidence_verified(self):
        # Evidence verified -> PASSED_EVIDENCE_VERIFIED, multiplier = 1.0
        docs = [EvidenceDocument(document_id="D1", document_type="EVID_U1_APPROVAL", status=EvidenceState.EVIDENCE_VERIFIED)]
        status, mult, _ = evaluate_evidence(["EVID_U1_APPROVAL"], docs)
        self.assertEqual(status, GatingStatus.PASSED_EVIDENCE_VERIFIED)
        self.assertEqual(mult, 1.0)

    # -------------------------------------------------------------
    # 5. DOUBLE-COUNTING TESTS
    # -------------------------------------------------------------
    def test_double_counting_forbidden_entity_reuse(self):
        validator = DoubleCountingValidator()
        patent = AssetEntity(entity_id="E1", entity_type="PATENT", identifier_key="IN2026-0912")

        # First claim under U16.I -> valid
        valid1, rej1, _ = validator.validate_entities("U16.I", [patent], DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(valid1), 1)
        self.assertEqual(len(rej1), 0)

        # Duplicate claim under U16.II -> rejected
        valid2, rej2, trace2 = validator.validate_entities("U16.II", [patent], DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(valid2), 0)
        self.assertEqual(len(rej2), 1)
        self.assertEqual(len(validator.conflicts), 1)
        self.assertIn("already claimed under U16.I", trace2["duplicates_detected"][0]["reason"])

    def test_permitted_document_reuse(self):
        validator = DoubleCountingValidator()
        # Master document referenced across multiple criteria
        validator.record_document_reference("DOC_ANNUAL_REPORT", "U1.1")
        validator.record_document_reference("DOC_ANNUAL_REPORT", "U6.A")
        validator.record_document_reference("DOC_ANNUAL_REPORT", "U15.1")

        # Document reuse is allowed, no conflicts generated
        self.assertEqual(len(validator.conflicts), 0)
        self.assertEqual(len(validator._referenced_documents["DOC_ANNUAL_REPORT"]), 3)

    # -------------------------------------------------------------
    # P2-04: RAW SCALAR INPUT DOUBLE-COUNTING TESTS
    # -------------------------------------------------------------
    def test_p2_04_unique_asset_normal(self):
        validator = DoubleCountingValidator()
        sub_in = SubcriterionInput(
            subcriterion_code="U16.I",
            raw_inputs={"patent_id": "PAT-2026-001"}
        )
        valid, rej, _ = validator.validate_subcriterion_input("U16.I", sub_in, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(rej), 0)
        self.assertEqual(len(validator.conflicts), 0)

    def test_p2_04_same_asset_twice_asset_entity(self):
        validator = DoubleCountingValidator()
        ent = AssetEntity(entity_id="E1", entity_type="PATENT", identifier_key="PAT-2026-001")
        sub1 = SubcriterionInput(subcriterion_code="U16.I", entities=[ent])
        sub2 = SubcriterionInput(subcriterion_code="U16.II", entities=[ent])

        v1, r1, _ = validator.validate_subcriterion_input("U16.I", sub1, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(v1), 1)
        self.assertEqual(len(r1), 0)

        v2, r2, _ = validator.validate_subcriterion_input("U16.II", sub2, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(v2), 0)
        self.assertEqual(len(r2), 1)
        self.assertEqual(len(validator.conflicts), 1)

    def test_p2_04_asset_entity_and_raw_scalar_conflict(self):
        validator = DoubleCountingValidator()
        ent = AssetEntity(entity_id="E1", entity_type="PATENT", identifier_key="PAT-2026-001")
        sub1 = SubcriterionInput(subcriterion_code="U16.I", entities=[ent])
        sub2 = SubcriterionInput(subcriterion_code="U16.II", raw_inputs={"patent_id": "PAT-2026-001"})

        v1, r1, _ = validator.validate_subcriterion_input("U16.I", sub1, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(v1), 1)
        self.assertEqual(len(r1), 0)

        v2, r2, _ = validator.validate_subcriterion_input("U16.II", sub2, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(v2), 0)
        self.assertEqual(len(r2), 1)
        self.assertEqual(len(validator.conflicts), 1)

    def test_p2_04_same_asset_twice_raw_inputs(self):
        validator = DoubleCountingValidator()
        sub1 = SubcriterionInput(subcriterion_code="U16.I", raw_inputs={"patent_id": "PAT-2026-001"})
        sub2 = SubcriterionInput(subcriterion_code="U16.II", raw_inputs={"patents": ["PAT-2026-001"]})

        v1, r1, _ = validator.validate_subcriterion_input("U16.I", sub1, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(v1), 1)
        self.assertEqual(len(r1), 0)

        v2, r2, _ = validator.validate_subcriterion_input("U16.II", sub2, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(v2), 0)
        self.assertEqual(len(r2), 1)
        self.assertEqual(len(validator.conflicts), 1)

    def test_p2_04_case_and_whitespace_insensitivity(self):
        validator = DoubleCountingValidator()
        sub1 = SubcriterionInput(subcriterion_code="U16.I", raw_inputs={"patent_id": "  pat-2026-001  "})
        sub2 = SubcriterionInput(subcriterion_code="U16.II", raw_inputs={"patent_id": "PAT-2026-001"})

        v1, r1, _ = validator.validate_subcriterion_input("U16.I", sub1, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(v1), 1)
        self.assertEqual(len(r1), 0)

        v2, r2, _ = validator.validate_subcriterion_input("U16.II", sub2, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(v2), 0)
        self.assertEqual(len(r2), 1)
        self.assertEqual(len(validator.conflicts), 1)

    def test_p2_04_scalar_count_not_falsely_flagged(self):
        validator = DoubleCountingValidator()
        # Pure numeric counts like programmes_count: 5 or activities_count: 10
        sub1 = SubcriterionInput(subcriterion_code="U1.1", raw_inputs={"programmes_count": 5})
        sub2 = SubcriterionInput(subcriterion_code="U9.B", raw_inputs={"activities_count": 5})

        v1, r1, _ = validator.validate_subcriterion_input("U1.1", sub1, DoubleCountingRule.FORBIDDEN_REUSE)
        v2, r2, _ = validator.validate_subcriterion_input("U9.B", sub2, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(validator.conflicts), 0)

    # -------------------------------------------------------------
    # P2-05: COUNT QUANTITY VALIDATION & FLOAT ADJUSTMENT TESTS
    # -------------------------------------------------------------
    def test_p2_05_count_validation_integer_values(self):
        # count = 0 -> pass
        ok0, val0, err0 = validate_count_quantity(0, "test_count")
        self.assertTrue(ok0)
        self.assertEqual(val0, 0)
        self.assertIsNone(err0)

        # count = 1 -> pass
        ok1, val1, err1 = validate_count_quantity(1, "test_count")
        self.assertTrue(ok1)
        self.assertEqual(val1, 1)
        self.assertIsNone(err1)

        # count = 2 -> pass
        ok2, val2, err2 = validate_count_quantity(2, "test_count")
        self.assertTrue(ok2)
        self.assertEqual(val2, 2)
        self.assertIsNone(err2)

        # count = 2.0 (integral float) -> pass, converted to integer 2
        ok2f, val2f, err2f = validate_count_quantity(2.0, "test_count")
        self.assertTrue(ok2f)
        self.assertEqual(val2f, 2)
        self.assertIsInstance(val2f, int)
        self.assertIsNone(err2f)

    def test_p2_05_count_validation_fractional_rejected(self):
        # count = 1.5 -> fail
        ok1_5, val1_5, err1_5 = validate_count_quantity(1.5, "test_count")
        self.assertFalse(ok1_5)
        self.assertIsNone(val1_5)
        self.assertIn("whole integer", err1_5)

        # count = 2.5 -> fail
        ok2_5, val2_5, err2_5 = validate_count_quantity(2.5, "test_count")
        self.assertFalse(ok2_5)
        self.assertIsNone(val2_5)
        self.assertIn("whole integer", err2_5)

        # count = -1 -> fail (negative count)
        ok_neg, val_neg, err_neg = validate_count_quantity(-1, "test_count")
        self.assertFalse(ok_neg)
        self.assertIsNone(val_neg)
        self.assertIn("non-negative", err_neg)

        # count = True (boolean) -> fail
        ok_bool, val_bool, err_bool = validate_count_quantity(True, "test_count")
        self.assertFalse(ok_bool)
        self.assertIsNone(val_bool)
        self.assertIn("Boolean", err_bool)

    def test_p2_05_percentage_fractional_not_rejected(self):
        # 66.7% rate is valid and not rejected by calculate_percentage
        pct, trace, valid = calculate_percentage(2, 3, metric_label="Rate Test")
        self.assertTrue(valid)
        self.assertAlmostEqual(pct, 66.6666667, places=4)
        self.assertIn("computed_percentage", trace)
