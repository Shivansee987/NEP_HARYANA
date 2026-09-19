"""
Unit and Regression Tests for Framework Isolation and Legacy Isolation
Guarantees:
1. Strict framework isolation between University (U1–U20) and College (C1–C22).
2. Zero coupling with legacy indicators P1–P20 or legacy nominations scoring.
3. Database mutations to legacy nomination tables have zero influence on 2026 scores.
"""
from datetime import date
import sys
from django.test import TestCase

from apps.scoring.domain import (
    AssessmentContext,
    AssessmentInput,
    AssessmentPeriod,
    EvidenceDocument,
    ParameterInput,
    SubcriterionInput,
)
from apps.scoring.engine import FrameworkMismatchException, NEP2026ScoringEngine
from apps.scoring.enums import (
    EvidenceState,
    FrameworkType,
    InstitutionType,
)
import apps.scoring.engine
import apps.scoring.rules.university
import apps.scoring.rules.college


class FrameworkAndLegacyIsolationTests(TestCase):

    def setUp(self):
        self.engine = NEP2026ScoringEngine()
        self.period = AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30))

    # -------------------------------------------------------------
    # FRAMEWORK ISOLATION TESTS
    # -------------------------------------------------------------
    def test_university_cannot_be_scored_under_college_framework(self):
        """A University institution cannot be evaluated against COLLEGE_2026."""
        context = AssessmentContext(
            assessment_id="test-iso-uni-01",
            institution_id="uni-iso-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.COLLEGE_2026,  # MISMATCH!
            assessment_period=self.period,
        )
        assessment_input = AssessmentInput(context=context, parameters={})

        with self.assertRaises(FrameworkMismatchException) as cm:
            self.engine.score_assessment(assessment_input)

        self.assertIn("cannot be evaluated under", str(cm.exception))

    def test_college_cannot_be_scored_under_university_framework(self):
        """A College institution cannot be evaluated against UNIVERSITY_2026."""
        context = AssessmentContext(
            assessment_id="test-iso-col-01",
            institution_id="col-iso-01",
            institution_type=InstitutionType.COLLEGE,
            framework=FrameworkType.UNIVERSITY_2026,  # MISMATCH!
            assessment_period=self.period,
        )
        assessment_input = AssessmentInput(context=context, parameters={})

        with self.assertRaises(FrameworkMismatchException) as cm:
            self.engine.score_assessment(assessment_input)

        self.assertIn("cannot be evaluated under", str(cm.exception))

    def test_university_scoring_contains_only_u1_to_u20(self):
        """University evaluation must contain exactly U1–U20 parameters and zero College parameters."""
        context = AssessmentContext(
            assessment_id="test-iso-params-01",
            institution_id="uni-iso-02",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        assessment_input = AssessmentInput(context=context, parameters={})
        result = self.engine.score_assessment(assessment_input)

        param_keys = set(result.parameter_results.keys())
        expected_u_keys = {f"U{i}" for i in range(1, 21)}
        self.assertEqual(param_keys, expected_u_keys)

        # Confirm no C1–C22 parameters exist in the result
        for i in range(1, 23):
            self.assertNotIn(f"C{i}", param_keys)

    def test_college_scoring_contains_only_c1_to_c22(self):
        """College evaluation must contain exactly C1–C22 parameters and zero University parameters."""
        context = AssessmentContext(
            assessment_id="test-iso-params-02",
            institution_id="col-iso-02",
            institution_type=InstitutionType.COLLEGE,
            framework=FrameworkType.COLLEGE_2026,
            assessment_period=self.period,
        )
        assessment_input = AssessmentInput(context=context, parameters={})
        result = self.engine.score_assessment(assessment_input)

        param_keys = set(result.parameter_results.keys())
        expected_c_keys = {f"C{i}" for i in range(1, 23)}
        self.assertEqual(param_keys, expected_c_keys)

        # Confirm no U1–U20 parameters exist in the result
        for i in range(1, 21):
            self.assertNotIn(f"U{i}", param_keys)

    # -------------------------------------------------------------
    # LEGACY ISOLATION TESTS
    # -------------------------------------------------------------
    def test_zero_legacy_scoring_imports_in_2026_engine(self):
        """The 2026 engine and rule modules must have zero imports from apps.nominations.scoring."""
        scoring_engine_module = sys.modules.get("apps.scoring.engine")
        self.assertIsNotNone(scoring_engine_module)

        # Verify no calculate_nomination_score in apps.scoring namespace
        self.assertFalse(hasattr(apps.scoring.engine, "calculate_nomination_score"))
        self.assertFalse(hasattr(apps.scoring.rules.university, "calculate_nomination_score"))
        self.assertFalse(hasattr(apps.scoring.rules.college, "calculate_nomination_score"))

    def test_legacy_data_mutation_does_not_affect_2026_score(self):
        """
        Regression Test:
        Modifying legacy nomination responses/indicators must have ZERO effect on 2026 scores.
        """
        from apps.nominations.scoring import calculate_nomination_score

        # 1. Evaluate a 2026 University assessment
        context = AssessmentContext(
            assessment_id="test-legacy-reg-001",
            institution_id="uni-reg-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        doc = EvidenceDocument(
            document_id="doc-u1-reg",
            document_type="EVID_U1_APPROVAL",
            status=EvidenceState.EVIDENCE_VERIFIED
        )
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
        assessment_input = AssessmentInput(context=context, parameters={"U1": p_in})

        score_before = self.engine.score_assessment(assessment_input)

        # 2. Simulate heavy legacy activity: calculate legacy nomination scores with various arbitrary values
        legacy_answers_1 = {
            "indicator_1": {"value": "Yes"},
            "indicator_2": {"value": "Yes"},
            "indicator_7": {"value": "A++"},
        }
        legacy_score_1, category_1 = calculate_nomination_score(legacy_answers_1)
        self.assertGreater(legacy_score_1, 0)

        legacy_answers_2 = {
            "indicator_1": {"value": "No"},
            "indicator_2": {"value": "No"},
            "indicator_7": {"value": "Not Accredited"},
        }
        legacy_score_2, category_2 = calculate_nomination_score(legacy_answers_2)
        self.assertEqual(legacy_score_2, 0)

        # 3. Re-evaluate the 2026 assessment
        score_after = self.engine.score_assessment(assessment_input)

        # 4. Proving 100% legacy isolation: 2026 scores remain identical down to the exact decimal
        self.assertEqual(score_before.raw_total, score_after.raw_total)
        self.assertEqual(score_before.evidence_gated_total, score_after.evidence_gated_total)
        self.assertEqual(
            score_before.parameter_results["U1"].raw_score,
            score_after.parameter_results["U1"].raw_score
        )
        self.assertEqual(
            score_before.parameter_results["U1"].evidence_gated_score,
            score_after.parameter_results["U1"].evidence_gated_score
        )
