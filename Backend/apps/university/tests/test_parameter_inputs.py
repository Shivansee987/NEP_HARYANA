"""Category F Tests: University Parameter Inputs and Boundary Conditions.

Verifies:
- Representative inputs for University parameters U1 to U20.
- Boundary conditions and threshold transitions.
- Known edge cases:
  - U5.A exactly 50.0% -> BOUNDARY_UNRESOLVED
  - U10.3 exactly 10,000,000 -> BOUNDARY_UNRESOLVED
  - U16.III Scopus index -> UNRESOLVED_RULE
  - U20 components sum to 5 vs max marks 4 -> SOURCE_INCONSISTENCY
- Invalid input validation (negative numbers, percentages > 100, non-integers).
"""

from datetime import date
from decimal import Decimal
from django.test import SimpleTestCase

from apps.university.validators import (
    validate_percentage,
    validate_count,
    validate_currency_amount,
    UniversityValidationError,
)
from apps.scoring.domain import (
    AssessmentContext,
    AssessmentInput,
    AssessmentPeriod,
    EvidenceDocument,
    EvidenceState,
    ParameterInput,
    SubcriterionInput,
    ResolutionStatus,
)
from apps.scoring.enums import FrameworkType, InstitutionType
from apps.scoring.engine import NEP2026ScoringEngine


class UniversityParameterInputsTests(SimpleTestCase):
    """Test parameter input validation, boundary conditions, and edge cases."""

    def setUp(self):
        self.engine = NEP2026ScoringEngine()
        self.period = AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30))
        self.context = AssessmentContext(
            assessment_id="test-input-uni-001",
            institution_id="uni-input-01",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=self.period,
        )
        self.verified_doc = EvidenceDocument(
            document_id="doc-v-01",
            document_type="EVID_GENERAL",
            status=EvidenceState.EVIDENCE_VERIFIED,
        )

    def test_percentage_validator(self):
        """Percentages must be between 0.0 and 100.0 inclusive."""
        self.assertEqual(validate_percentage(0.0), 0.0)
        self.assertEqual(validate_percentage(50.5), 50.5)
        self.assertEqual(validate_percentage(100.0), 100.0)

        with self.assertRaises(UniversityValidationError):
            validate_percentage(-0.1)

        with self.assertRaises(UniversityValidationError):
            validate_percentage(100.01)

    def test_integer_count_validator(self):
        """Counts must be non-negative integers."""
        self.assertEqual(validate_count(0), 0)
        self.assertEqual(validate_count(5), 5)

        with self.assertRaises(UniversityValidationError):
            validate_count(-1)

        with self.assertRaises(UniversityValidationError):
            validate_count("3.5")

    def test_currency_amount_validator(self):
        """Monetary amounts must be non-negative."""
        self.assertEqual(validate_currency_amount(0), 0.0)
        self.assertEqual(validate_currency_amount(10000000), 10000000.0)

        with self.assertRaises(UniversityValidationError):
            validate_currency_amount(-500)

    def test_u5_boundary_unresolved_at_50_percent(self):
        """U5.A at exactly 50.0% triggers BOUNDARY_UNRESOLVED in the frozen engine."""
        p_input = ParameterInput(
            parameter_code="U5",
            subcriteria_inputs={
                "U5.A": SubcriterionInput(
                    subcriterion_code="U5.A",
                    raw_inputs={"eligible_students": 50, "total_final_year_students": 100},
                    evidence_docs=[self.verified_doc],
                ),
                "U5.B": SubcriterionInput(
                    subcriterion_code="U5.B",
                    raw_inputs={"placed_students": 30, "eligible_students": 50},
                    evidence_docs=[self.verified_doc],
                ),
            },
        )
        assessment_input = AssessmentInput(context=self.context, parameters={"U5": p_input})
        result = self.engine.score_assessment(assessment_input)
        u5_res = result.parameter_results["U5"]
        self.assertEqual(u5_res.resolution_status, ResolutionStatus.BOUNDARY_UNRESOLVED)

    def test_u10_boundary_unresolved_at_1_crore(self):
        """U10.3 at exactly Rs. 10,000,000 triggers BOUNDARY_UNRESOLVED."""
        p_input = ParameterInput(
            parameter_code="U10",
            subcriteria_inputs={
                "U10.1": SubcriterionInput("U10.1", raw_inputs={"verified": True}, evidence_docs=[self.verified_doc]),
                "U10.2": SubcriterionInput("U10.2", raw_inputs={"verified": True}, evidence_docs=[self.verified_doc]),
                "U10.3": SubcriterionInput("U10.3", raw_inputs={"funding_amount": 10000000.0}, evidence_docs=[self.verified_doc]),
                "U10.4": SubcriterionInput("U10.4", raw_inputs={"verified": True}, evidence_docs=[self.verified_doc]),
            },
        )
        assessment_input = AssessmentInput(context=self.context, parameters={"U10": p_input})
        result = self.engine.score_assessment(assessment_input)
        u10_res = result.parameter_results["U10"]
        self.assertEqual(u10_res.resolution_status, ResolutionStatus.BOUNDARY_UNRESOLVED)

    def test_u16_scopus_index_unresolved_rule(self):
        """U16.III has UNRESOLVED_RULE status due to undefined Scopus index metric."""
        p_input = ParameterInput(
            parameter_code="U16",
            subcriteria_inputs={
                "U16.I": SubcriterionInput("U16.I", raw_inputs={"patents_filed": 12}, evidence_docs=[self.verified_doc]),
                "U16.II": SubcriterionInput("U16.II", raw_inputs={"patents_granted": 3}, evidence_docs=[self.verified_doc]),
                "U16.III": SubcriterionInput("U16.III", raw_inputs={"scopus_index": 50}, evidence_docs=[self.verified_doc]),
            },
        )
        assessment_input = AssessmentInput(context=self.context, parameters={"U16": p_input})
        result = self.engine.score_assessment(assessment_input)
        u16_res = result.parameter_results["U16"]
        self.assertEqual(u16_res.resolution_status, ResolutionStatus.UNRESOLVED_RULE)

    def test_u20_source_inconsistency_preserved(self):
        """U20 preserves SOURCE_INCONSISTENCY (subcriteria sum to 5 vs max marks 4)."""
        p_input = ParameterInput(
            parameter_code="U20",
            subcriteria_inputs={
                "U20.1": SubcriterionInput("U20.1", raw_inputs={"activities_count": 12}, evidence_docs=[self.verified_doc]),
                "U20.2": SubcriterionInput("U20.2", raw_inputs={"verified": True}, evidence_docs=[self.verified_doc]),
                "U20.3": SubcriterionInput("U20.3", raw_inputs={"verified": True}, evidence_docs=[self.verified_doc]),
            },
        )
        assessment_input = AssessmentInput(context=self.context, parameters={"U20": p_input})
        result = self.engine.score_assessment(assessment_input)
        u20_res = result.parameter_results["U20"]
        self.assertEqual(u20_res.resolution_status, ResolutionStatus.SOURCE_INCONSISTENCY)
