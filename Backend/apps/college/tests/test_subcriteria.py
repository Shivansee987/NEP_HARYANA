"""
Unit Tests for Authoritative College Subcriteria
Verifies exact subcriteria definitions for all multi-part and single-part College parameters,
ensures invalid parameter/subcriterion combinations are rejected.
"""
from django.test import TestCase
from apps.college.registry import (
    get_all_college_subcriteria,
    get_college_subcriteria,
)
from apps.college.validators import (
    CollegeValidationError,
    validate_subcriterion,
)

EXPECTED_SUBCRITERIA = {
    "C1": ["C1.1"],
    "C2": ["C2.1"],
    "C3": ["C3.1"],
    "C4": ["C4.A", "C4.B"],
    "C5": ["C5.1"],
    "C6": ["C6.1"],
    "C7": ["C7.1"],
    "C8": ["C8.1"],
    "C9": ["C9.I", "C9.II"],
    "C10": ["C10.1"],
    "C11": ["C11.I", "C11.II.a", "C11.II.b"],
    "C12": ["C12.1", "C12.2", "C12.3", "C12.4", "C12.5"],
    "C13": ["C13.1"],
    "C14": ["C14.A", "C14.B"],
    "C15": ["C15.1", "C15.2", "C15.3", "C15.4", "C15.5", "C15.6"],
    "C16": ["C16.1", "C16.2", "C16.3", "C16.4", "C16.5"],
    "C17": ["C17.1"],
    "C18": ["C18.1", "C18.2", "C18.3", "C18.4"],
    "C19": ["C19.I", "C19.II", "C19.III"],
    "C20": ["C20.1", "C20.2", "C20.3", "C20.4"],
    "C21": ["C21.1", "C21.2"],
    "C22": ["C22.1", "C22.2"],
}


class CollegeSubcriteriaTests(TestCase):

    def test_authoritative_subcriteria_registered(self):
        """Verifies each C1–C22 parameter exposes its authoritative subcriteria."""
        for param_code, expected_subs in EXPECTED_SUBCRITERIA.items():
            subs = get_college_subcriteria(param_code)
            self.assertEqual(
                list(subs.keys()),
                expected_subs,
                f"Mismatch in subcriteria for parameter {param_code}",
            )
            for sub_code in expected_subs:
                self.assertEqual(subs[sub_code]["subcriterion_code"], sub_code)

    def test_flattened_subcriteria_map(self):
        """Verifies get_all_college_subcriteria flattens all subcriteria correctly."""
        all_subs = get_all_college_subcriteria()
        total_expected = sum(len(subs) for subs in EXPECTED_SUBCRITERIA.values())
        self.assertEqual(len(all_subs), total_expected)

        for param_code, expected_subs in EXPECTED_SUBCRITERIA.items():
            for sub_code in expected_subs:
                self.assertIn(sub_code, all_subs)
                self.assertEqual(all_subs[sub_code]["parent_parameter"], param_code)

    def test_validate_subcriterion_valid(self):
        """Verifies validate_subcriterion accepts matching pairs."""
        self.assertEqual(validate_subcriterion("C1", "C1.1"), "C1.1")
        self.assertEqual(validate_subcriterion("C4", "C4.A"), "C4.A")
        self.assertEqual(validate_subcriterion("C4", "c4.b"), "C4.B")
        self.assertEqual(validate_subcriterion("C11", "C11.II.a"), "C11.II.a")
        self.assertEqual(validate_subcriterion("C19", "C19.I"), "C19.I")
        self.assertEqual(validate_subcriterion("C20", "C20.1"), "C20.1")

    def test_validate_subcriterion_mismatch_rejected(self):
        """Verifies validate_subcriterion rejects subcriteria belonging to a different parameter."""
        with self.assertRaises(CollegeValidationError) as ctx:
            validate_subcriterion("C1", "C4.A")
        self.assertEqual(ctx.exception.code, "INVALID_SUBCRITERION")

        with self.assertRaises(CollegeValidationError):
            validate_subcriterion("C10", "C11.I")

        with self.assertRaises(CollegeValidationError):
            validate_subcriterion("C19", "U19.1")  # University subcriterion rejected

    def test_validate_subcriterion_invalid_param_rejected(self):
        """Verifies validate_subcriterion rejects non-existent parameters."""
        with self.assertRaises(CollegeValidationError) as ctx:
            validate_subcriterion("U1", "U1.1")
        self.assertEqual(ctx.exception.code, "INVALID_PARAMETER")

        with self.assertRaises(CollegeValidationError):
            validate_subcriterion("C25", "C25.1")
