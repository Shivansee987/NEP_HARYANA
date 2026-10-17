"""
FIN-03 / SCO-01 regression: official University certification is held while U6.A, U6.B and U18.3 have no approved
documentary-evidence rule (every university would otherwise be certified at a maximum of 90/100).

Before the gate, an assessment that passed every other gate was certified (the audit certified a fully approved
university at 85 with U6 = 0/8 and U18.3 = 0/2). No scoring rule is invented: the hold lifts only when the evidence
taxonomy gives each listed subcriterion an ACTIVE contract with an accepted evidence type, after the council decides.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.scoring.domain import FrameworkResult
from apps.scoring.enums import CertificationStatus, FrameworkType
from apps.scoring.policy import get_policy_register
from apps.scoring.policy_gates import open_certification_policy_blockers
from apps.scoring.test_support import council_decision_resolved, grant_review_scope, record_complete_review
from apps.university.models import University
from apps.university.services import UniversityAssessmentService, UniversityReviewService
from apps.university.validators import CertificationBlockedError

User = get_user_model()


class UniversityCertificationPolicyGateTests(TestCase):
    def setUp(self):
        self.uni = University.objects.create(name="Gate University", aishe_code="U-GATE-1")
        self.nodal = User.objects.create_user(email="nodal@gate.test", full_name="Nodal", role="nodal_officer",
                                              password="x", university=self.uni)
        self.chair = User.objects.create_user(email="chair@gate.test", full_name="Chair", role="committee_chair",
                                              password="x")
        grant_review_scope(self.chair)
        self.assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni.id, academic_year="2025-26", created_by=self.nodal)
        self.assessment.status = "CERTIFICATION_PENDING"
        self.assessment.save(update_fields=["status"])
        record_complete_review(self.assessment, self.chair)

    def _certify_with_all_other_gates_passing(self):
        """Every other certification gate passes (readiness, finalizable scoring, complete review recorded)."""
        result = FrameworkResult(
            framework=FrameworkType.UNIVERSITY_2026, assessment_id=self.assessment.assessment_id,
            institution_id=self.uni.aishe_code, calculation_id="calc-policy-gate", version_index=1,
            timestamp="2026-03-01T00:00:00Z", raw_total=90.0, evidence_gated_total=90.0, final_certified_total=90.0,
            max_marks=100.0, certification_status=CertificationStatus.FINALIZABLE, blocking_reasons=[],
            parameter_results={})
        with patch.object(UniversityAssessmentService, "check_assessment_readiness", return_value=(True, [], None)), \
             patch.object(UniversityAssessmentService, "evaluate_assessment_scoring", return_value=result):
            return UniversityReviewService.certify_assessment(self.assessment.assessment_id, actor=self.chair)

    def test_open_blockers_are_reported(self):
        blockers = open_certification_policy_blockers("UNIVERSITY_2026")
        self.assertEqual(sorted(s for b in blockers for s in b["unresolved_subcriteria"]), ["U18.3", "U6.A", "U6.B"])
        self.assertEqual(sum(b["marks"] for b in blockers), 10.0)
        self.assertEqual(open_certification_policy_blockers("COLLEGE_2026"), [])

    def test_otherwise_ready_university_is_held(self):
        with self.assertRaises(CertificationBlockedError) as ctx:
            self._certify_with_all_other_gates_passing()
        self.assertEqual(ctx.exception.code, "POLICY_DECISION_REQUIRED")
        for sub in ("U6.A", "U6.B", "U18.3"):
            self.assertIn(sub, ctx.exception.message)
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status, "CERTIFICATION_PENDING")
        self.assertIsNone(self.assessment.certified_score)

    def test_hold_lifts_only_when_taxonomy_resolves(self):
        with council_decision_resolved():
            self.assertEqual(open_certification_policy_blockers("UNIVERSITY_2026"), [])
            assessment, _ = self._certify_with_all_other_gates_passing()
        self.assertEqual(assessment.status, "CERTIFIED")

    def test_configuration_alone_cannot_lift_the_hold(self):
        decisions = {"U6_U18_3_EVIDENCE": {"status": "RESOLVED", "decided_by": "configuration only"}}
        with self.settings(NEP_2026_POLICY_DECISIONS=decisions):
            with self.assertRaises(CertificationBlockedError) as ctx:
                self._certify_with_all_other_gates_passing()
        self.assertEqual(ctx.exception.code, "POLICY_DECISION_REQUIRED")

    def test_hold_is_visible_in_policy_register(self):
        item = next(p for p in get_policy_register() if p["policy_id"] == "U6_U18_3_EVIDENCE")
        self.assertTrue(item["blocks_certification"])
        self.assertEqual(item["status"], "UNRESOLVED")
        self.assertEqual(sorted(item["parameters"]), ["U18", "U6"])
        with council_decision_resolved():
            item = next(p for p in get_policy_register() if p["policy_id"] == "U6_U18_3_EVIDENCE")
            self.assertFalse(item["blocks_certification"])
