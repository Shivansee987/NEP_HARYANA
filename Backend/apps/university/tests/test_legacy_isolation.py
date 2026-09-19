"""Category I Tests: Legacy System Isolation.

Verifies:
- University domain models and services have zero coupling with legacy nominations.
- No legacy 20-indicator scoring logic (indicator_1 to indicator_20) is imported or used.
- UniversityAssessment schema is independent of legacy Nomination schema.
"""

from django.test import SimpleTestCase
from apps.university import models, services, registry, validators


class UniversityLegacyIsolationTests(SimpleTestCase):
    """Ensure zero contamination from legacy nomination scoring system."""

    def test_no_legacy_fields_on_university_assessment(self):
        """UniversityAssessment does not contain legacy indicator_1..20 fields."""
        fields = [f.name for f in models.UniversityAssessment._meta.get_fields()]
        for i in range(1, 21):
            self.assertNotIn(f"indicator_{i}", fields)
            self.assertNotIn(f"score_{i}", fields)

    def test_no_legacy_nominations_import_in_university_modules(self):
        """None of the university modules import from apps.nominations."""
        for module in [models, services, registry, validators]:
            module_content = dir(module)
            self.assertNotIn("Nomination", module_content)
            self.assertNotIn("calculate_nomination_score", module_content)

    def test_scoring_delegates_only_to_frozen_engine(self):
        """Scoring delegation is exclusively to NEP2026ScoringEngine."""
        import inspect
        source = inspect.getsource(services.UniversityAssessmentService.evaluate_assessment_scoring)
        self.assertIn("NEP2026ScoringEngine", source)
        self.assertNotIn("nominations", source)
        self.assertNotIn("calculate_nomination_score", source)
