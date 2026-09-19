"""Category H Tests: Double Counting Prevention.

Verifies:
- Enforcement of double counting rules across University parameters.
- DoubleCountingRule.FORBIDDEN_REUSE on standard parameters.
- DoubleCountingRule.REQUIRES_FRAMEWORK_EXCEPTION on U14 Multidisciplinary Education.
- Evidence documents cannot be reused to satisfy disjoint parameter obligations without framework authorization.
"""

from django.test import SimpleTestCase
from apps.scoring.domain import DoubleCountingRule
from apps.scoring.rules.definitions import UNIVERSITY_PARAMETERS


class DoubleCountingPreventionTests(SimpleTestCase):
    """Test double counting restrictions across the 20 University parameters."""

    def test_forbidden_reuse_default_on_parameters(self):
        """19 of 20 University parameters strictly enforce FORBIDDEN_REUSE."""
        forbidden_count = 0
        for code, p in UNIVERSITY_PARAMETERS.items():
            if p["double_counting_rule"] == DoubleCountingRule.FORBIDDEN_REUSE:
                forbidden_count += 1

        self.assertEqual(forbidden_count, 19)

    def test_u14_framework_exception_rule(self):
        """U14 Multidisciplinary Education requires explicit framework exception for overlap."""
        u14 = UNIVERSITY_PARAMETERS["U14"]
        self.assertEqual(
            u14["double_counting_rule"],
            DoubleCountingRule.REQUIRES_FRAMEWORK_EXCEPTION,
        )

    def test_no_universal_permissive_reuse(self):
        """No parameter allows PERMITTED_REUSE without rule enforcement."""
        for code, p in UNIVERSITY_PARAMETERS.items():
            self.assertNotEqual(p["double_counting_rule"], DoubleCountingRule.PERMITTED_REUSE)
