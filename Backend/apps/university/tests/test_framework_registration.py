"""Category A Tests: University Framework Registration and Structural Integrity.

Verifies:
- Framework UNIVERSITY_2026 is registered.
- Exactly 20 parameters (U1 to U20).
- Total maximum marks sum to exactly 100.0.
- Each parameter definition has code, title, max_marks, subcriteria, evidence types, and validation rules.
- University vs College validation.
"""

from decimal import Decimal
from django.test import SimpleTestCase

from apps.scoring.rules.definitions import UNIVERSITY_PARAMETERS
from apps.university.registry import (
    get_university_framework_info,
    get_university_parameters,
    get_university_parameter,
    validate_university_parameter_code,
    UNIVERSITY_FRAMEWORK_CODE,
    UNIVERSITY_TOTAL_MARKS,
)
from apps.university.validators import (
    validate_framework_code,
    validate_institution_type,
    validate_parameter,
    validate_subcriterion,
    UniversityValidationError,
)


class UniversityFrameworkRegistrationTests(SimpleTestCase):
    """Test framework registration and structure for UNIVERSITY_2026."""

    def test_framework_code_and_academic_year(self):
        """Verify authoritative framework code and academic year."""
        info = get_university_framework_info()
        self.assertEqual(info["framework_code"], "UNIVERSITY_2026")
        self.assertEqual(info["statutory_assessment_period"]["academic_year"], "2025-26")

    def test_parameter_count_is_exactly_20(self):
        """Verify that UNIVERSITY_PARAMETERS has exactly 20 parameters (U1 to U20)."""
        params = get_university_parameters()
        self.assertEqual(len(params), 20)
        expected_keys = [f"U{i}" for i in range(1, 21)]
        self.assertEqual(list(params.keys()), expected_keys)

    def test_parameter_marks_sum_to_exactly_100(self):
        """Verify that total maximum marks across U1 to U20 sum to exactly 100.0."""
        self.assertEqual(Decimal(str(UNIVERSITY_TOTAL_MARKS)), Decimal("100.0"))

        # Also verify directly from definitions
        manual_sum = sum(Decimal(str(p["max_marks"])) for p in UNIVERSITY_PARAMETERS.values())
        self.assertEqual(manual_sum, Decimal("100.0"))

    def test_parameter_definition_attributes(self):
        """Verify every parameter has title, code, max_marks, subcriteria, and evidence types."""
        params = get_university_parameters()
        for code, param in params.items():
            self.assertEqual(param["parameter_code"], code)
            self.assertTrue(len(param["title"]) > 0)
            self.assertTrue(Decimal(str(param["max_marks"])) > Decimal("0.0"))
            self.assertIsInstance(param["subcriteria"], dict)
            self.assertTrue(len(param["subcriteria"]) >= 1)
            # Evidence requirements: either mandatory_evidence or allowed_evidence
            has_evidence = bool(param.get("mandatory_evidence") or param.get("allowed_evidence"))
            self.assertTrue(has_evidence, f"Parameter {code} must declare evidence requirements")

    def test_parameter_lookup(self):
        """Verify get_university_parameter fetches valid codes and raises on invalid."""
        u1 = get_university_parameter("U1")
        self.assertEqual(u1["parameter_code"], "U1")
        self.assertEqual(Decimal(str(u1["max_marks"])), Decimal("4.0"))

        with self.assertRaises(KeyError):
            get_university_parameter("C1")  # College parameter not allowed

        with self.assertRaises(KeyError):
            get_university_parameter("U21")  # Non-existent

    def test_framework_validator(self):
        """Verify framework validator enforces UNIVERSITY_2026."""
        # Valid
        code = validate_framework_code("UNIVERSITY_2026")
        self.assertEqual(code, "UNIVERSITY_2026")

        # Invalid
        with self.assertRaises(UniversityValidationError):
            validate_framework_code("COLLEGE_2026")

        with self.assertRaises(UniversityValidationError):
            validate_framework_code("NEP_2020")

    def test_parameter_code_validator(self):
        """Verify parameter code validator checks U1 to U20."""
        for i in range(1, 21):
            valid_code = validate_parameter(f"U{i}")
            self.assertEqual(valid_code, f"U{i}")

        with self.assertRaises(UniversityValidationError):
            validate_parameter("C1")

        with self.assertRaises(UniversityValidationError):
            validate_parameter("U0")

        with self.assertRaises(UniversityValidationError):
            validate_parameter("U21")

    def test_subcriterion_validator(self):
        """Verify subcriterion validator checks known subcriteria for parameters."""
        # U4 has A and B (and aliases 1, 2)
        validate_subcriterion("U4", "U4.A")
        validate_subcriterion("U4", "U4.B")

        with self.assertRaises(UniversityValidationError):
            validate_subcriterion("U4", "U4.C")

        # U5 has U5.A and U5.B
        validate_subcriterion("U5", "U5.A")
        validate_subcriterion("U5", "U5.B")

        with self.assertRaises(UniversityValidationError):
            validate_subcriterion("U5", "U5.X")
