"""Category D Tests: Assessment Period Enforcement.

Verifies:
- University assessments enforce 2025-07-01 to 2026-06-30 window.
- Period-sensitive parameters reject activity dates outside window.
- Period-insensitive parameters allow activity dates outside window.
- Future activity dates beyond 2026-06-30 are rejected for period-sensitive parameters.
"""

from datetime import date
from django.test import SimpleTestCase

from apps.evidence.period_validator import AssessmentPeriodValidator
from apps.university.validators import (
    validate_temporal_activity_date,
    UniversityValidationError,
)


class AssessmentPeriodEnforcementTests(SimpleTestCase):
    """Test temporal enforcement for University assessment period."""

    def test_assessment_window_constants(self):
        """Authoritative assessment period is July 1, 2025 to June 30, 2026."""
        self.assertEqual(AssessmentPeriodValidator.START_DATE, date(2025, 7, 1))
        self.assertEqual(AssessmentPeriodValidator.END_DATE, date(2026, 6, 30))
        self.assertEqual(AssessmentPeriodValidator.ACADEMIC_YEAR, "2025-26")

    def test_period_sensitive_parameter_enforces_window(self):
        """Period-sensitive parameter (e.g., U5, U6, U7, U8, U9, U10) rejects out-of-period dates."""
        # Inside window: should not raise
        validate_temporal_activity_date(date(2025, 10, 1), "U5")
        validate_temporal_activity_date(date(2026, 3, 1), "U8")

        # Before window: must raise
        with self.assertRaises(UniversityValidationError) as ctx:
            validate_temporal_activity_date(date(2025, 5, 1), "U5")
        self.assertIn("OUTSIDE_ASSESSMENT_PERIOD", str(ctx.exception))

        # After window: must raise
        with self.assertRaises(UniversityValidationError) as ctx:
            validate_temporal_activity_date(date(2026, 8, 1), "U8")
        self.assertIn("OUTSIDE_ASSESSMENT_PERIOD", str(ctx.exception))

    def test_period_insensitive_parameter_allows_out_of_period_dates(self):
        """Period-insensitive parameter (e.g., U1, U2, U3, U14, U15) allows dates outside window."""
        # Should not raise for period-insensitive parameters
        validate_temporal_activity_date(date(2024, 8, 1), "U1")
        validate_temporal_activity_date(date(2023, 5, 1), "U2")
        validate_temporal_activity_date(date(2024, 1, 1), "U3")
        validate_temporal_activity_date(date(2022, 12, 1), "U14")
        validate_temporal_activity_date(date(2023, 6, 1), "U15")

    def test_period_sensitive_missing_date_rejected(self):
        """Period-sensitive parameters reject None activity date."""
        with self.assertRaises(UniversityValidationError) as ctx:
            validate_temporal_activity_date(None, "U5")
        self.assertIn("PERIOD_DATA_MISSING", str(ctx.exception))
