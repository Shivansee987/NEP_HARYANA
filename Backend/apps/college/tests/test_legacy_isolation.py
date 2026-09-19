"""
Unit Tests for Legacy Isolation (Section 25)
Verifies:
- Legacy Nomination models and P-1–P-20 indicators cannot affect CollegeAssessment
- Legacy reviewer_scores and integer score fields cannot affect CollegeAssessment scoring
- Legacy score synthesis cannot be invoked on CollegeAssessment
- CollegeAssessment strictly uses the frozen NEP2026ScoringEngine with C1–C22 rules
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authentication.models import College
from apps.college.models import CollegeAssessment
from apps.college.services import CollegeAssessmentService
from apps.nominations.models import Nomination

User = get_user_model()


class LegacyIsolationTests(TestCase):

    def setUp(self):
        self.college = College.objects.create(name="Legacy Isolation College", aishe_code="C-LEG-01")
        self.user = User.objects.create_user(
            email="admin@legacy.edu",
            full_name="Legacy Admin",
            role="admin",
            password="pass",
        )

        # Create legacy nomination with legacy answers and legacy scores
        self.legacy_nomination = Nomination.objects.create(
            form_id="FORM-2024-LEG-01",
            college=self.college,
            answers={
                "indicator_1": {"value": 100, "legacy_points": 25},
                "P-1": 10,
                "P-2": 20,
            },
            score=95,
            reviewer_scores={"rev_1": 90, "rev_2": 95},
            status="Approved",
            award_category="Outstanding College",
        )

        # Create new first-class College assessment
        self.assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college.pk,
            assessment_id="ASSESS-2026-COL-LEG-01",
            created_by=self.user,
        )

    def test_legacy_indicators_do_not_populate_college_assessment(self):
        """CollegeAssessment parameter_data is empty and isolated from Nomination.answers."""
        self.assertEqual(self.assessment.parameter_data, {})
        self.assertNotIn("P-1", self.assessment.parameter_data)
        self.assertNotIn("indicator_1", self.assessment.parameter_data)

    def test_legacy_scores_do_not_affect_college_assessment_scoring(self):
        """Legacy Nomination.score (95) does not populate or influence CollegeAssessment.certified_score."""
        self.assertIsNone(self.assessment.certified_score)
        self.assertEqual(self.assessment.framework, "COLLEGE_2026")

        # Evaluate scoring without evidence: must score 0.0, ignoring Nomination.score=95
        result = CollegeAssessmentService.evaluate_assessment_scoring(self.assessment.assessment_id)
        self.assertEqual(result.evidence_gated_total, 0.0)
        self.assertEqual(result.framework, "COLLEGE_2026")

        # Refreshed assessment has 0.0, not 95
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.certified_score, 0.0)

    def test_legacy_nomination_remains_untouched(self):
        """Updating CollegeAssessment does not alter legacy Nomination record."""
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 90, "fixed_targets_2024_25": 100}},
        )

        self.legacy_nomination.refresh_from_db()
        self.assertEqual(self.legacy_nomination.score, 95)
        self.assertEqual(self.legacy_nomination.answers["P-1"], 10)
        self.assertEqual(self.legacy_nomination.status, "Approved")
