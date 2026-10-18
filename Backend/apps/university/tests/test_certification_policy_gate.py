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

    def test_open_blockers_are_cleared_for_university_2026(self):
        """Now that U6.A, U6.B, and U18.3 evidence rules are approved and active, no blockers remain for them."""
        blockers = open_certification_policy_blockers("UNIVERSITY_2026")
        self.assertEqual(blockers, [])
        self.assertEqual(open_certification_policy_blockers("COLLEGE_2026"), [])

    def test_otherwise_ready_university_certifies_successfully(self):
        """With U6 and U18.3 rules resolved in the taxonomy, certification succeeds directly."""
        assessment, _ = self._certify_with_all_other_gates_passing()
        self.assertEqual(assessment.status, "CERTIFIED")
        self.assertEqual(assessment.certification_status, "CERTIFIED")
        self.assertEqual(assessment.certified_score, 90.0)

    def test_unresolved_council_blocker_still_blocks_certification(self):
        """Simulating an unresolved policy blocker confirms that the certification safeguard remains active."""
        from apps.evidence.taxonomy import ContractStatus, SubcriterionEvidenceContract
        mock_unresolved = SubcriterionEvidenceContract(
            framework="UNIVERSITY_2026",
            parameter_id="U6",
            subcriterion_id="U6.A",
            source_documentary_requirement="Unresolved requirement",
            canonical_evidence_type=None,
            score_unlock_requirement="Score unlock requirement",
            status=ContractStatus.UNRESOLVED_MISSING,
            allowed_evidence_types=(),
            allowed_file_formats=("pdf",),
            is_source_silent=False,
            is_unresolved=True,
        )
        with patch("apps.scoring.policy_gates.get_subcriterion_contract", return_value=mock_unresolved):
            blockers = open_certification_policy_blockers("UNIVERSITY_2026")
            self.assertTrue(len(blockers) > 0)
            with self.assertRaises(CertificationBlockedError) as ctx:
                self._certify_with_all_other_gates_passing()
            self.assertEqual(ctx.exception.code, "POLICY_DECISION_REQUIRED")
            self.assertIn("Official certification is on hold", ctx.exception.message)

    def test_resolved_status_is_visible_in_policy_register(self):
        """U6_U18_3_EVIDENCE is reported as RESOLVED without blocking certification."""
        item = next(p for p in get_policy_register() if p["policy_id"] == "U6_U18_3_EVIDENCE")
        self.assertFalse(item["blocks_certification"])
        self.assertEqual(item["status"], "RESOLVED")
        self.assertEqual(sorted(item["parameters"]), ["U18", "U6"])
