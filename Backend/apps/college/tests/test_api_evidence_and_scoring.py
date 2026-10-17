"""
Phase 7B API Tests: Coverage, Readiness, Scoring Evaluation, Submission, and Immutability.

Verifies:
1. Coverage endpoint delegates to Phase 5D.
2. Readiness endpoint returns blocking reasons.
3. Evaluation delegates strictly to frozen NEP2026ScoringEngine.
4. Score immutability: arbitrary client scores rejected.
5. Submission lifecycle: DRAFT -> SUBMITTED.
6. Submission does NOT certify assessment.
7. Unauthorized user cannot submit another college's assessment.
8. Double submission rejected with 409 conflict.
9. Legacy nomination/scoring system isolation preserved.
"""
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import College
from apps.college.services import CollegeAssessmentService
from apps.evidence.models import EvidenceDocument
from apps.evidence.services import EvidenceService
from apps.nominations.models import Nomination
from apps.scoring.test_support import fill_assessment

User = get_user_model()


class CollegeAPIEvidenceAndScoringTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin user
        self.admin = User.objects.create_user(
            email="admin@dhe.haryana.gov.in",
            full_name="State Admin",
            role="admin",
            password="AdminPassword2026!",
        )

        # College A
        self.college_a = College.objects.create(
            name="Govt College Hisar",
            aishe_code="C-00105",
        )
        self.principal_a = User.objects.create_user(
            email="principal.hisar@haryana.gov.in",
            full_name="Principal Hisar",
            role="principal",
            college=self.college_a,
            password="PasswordHisar2026!",
        )

        # College B
        self.college_b = College.objects.create(
            name="Govt College Sirsa",
            aishe_code="C-00106",
        )
        self.principal_b = User.objects.create_user(
            email="principal.sirsa@haryana.gov.in",
            full_name="Principal Sirsa",
            role="principal",
            college=self.college_b,
            password="PasswordSirsa2026!",
        )

        # Reviewer
        self.reviewer = User.objects.create_user(
            email="reviewer@dhe.haryana.gov.in",
            full_name="College Reviewer",
            role="committee",
            password="ReviewerPassword2026!",
        )

        # Assessment for College A
        self.assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college_a.pk,
            created_by=self.principal_a,
        )
        # Review scope is explicit (COM-01): committee users without a scoped authorization get framework-wide scope.
        from apps.authentication.models import User as _ScopeUser
        from apps.evidence.models import ReviewerAuthorization as _ScopeAuth
        from apps.scoring.test_support import grant_review_scope as _grant_scope
        for _reviewer in _ScopeUser.objects.filter(role__in=("committee", "committee_chair")):
            if not _ScopeAuth.objects.filter(user=_reviewer).exists():
                _grant_scope(_reviewer)

    def test_coverage_endpoint_delegation(self):
        """GET /coverage/ delegates to Phase 5D EvidenceCoverageEvaluator."""
        self.client.force_authenticate(user=self.principal_a)
        resp = self.client.get(f"/api/college/assessments/{self.assessment.assessment_id}/coverage/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["framework"], "COLLEGE_2026")
        self.assertIn("parameters", resp.data)
        self.assertIn("summary", resp.data)

    def test_readiness_endpoint_blocking_reasons(self):
        """GET /readiness/ indicates assessment readiness status and blocking reasons."""
        self.client.force_authenticate(user=self.principal_a)
        resp = self.client.get(f"/api/college/assessments/{self.assessment.assessment_id}/readiness/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("is_ready", resp.data)
        self.assertIn("blocking_reasons", resp.data)
        self.assertEqual(resp.data["framework"], "COLLEGE_2026")

    def test_evaluate_endpoint_delegation_to_frozen_engine(self):
        """POST /evaluate/ delegates to frozen NEP2026ScoringEngine."""
        # Populate parameter input
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}},
        )
        self.client.force_authenticate(user=self.principal_a)
        resp = self.client.post(f"/api/college/assessments/{self.assessment.assessment_id}/evaluate/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["framework"], "COLLEGE_2026")
        self.assertEqual(resp.data["assessment_id"], self.assessment.assessment_id)
        self.assertIn("parameter_results", resp.data)
        self.assertIn("C1", resp.data["parameter_results"])
        self.assertEqual(resp.data["parameter_results"]["C1"]["raw_score"], 6.0)

    def test_score_injection_rejected_in_evaluate(self):
        """Injecting client-supplied scores into POST /evaluate/ is rejected."""
        self.client.force_authenticate(user=self.principal_a)
        payload = {"score": 100.0, "certified_score": 100.0}
        resp = self.client.post(
            f"/api/college/assessments/{self.assessment.assessment_id}/evaluate/",
            payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_assessment_lifecycle_and_audit(self):
        """POST /submit/ transitions assessment DRAFT -> SUBMITTED, locks updates, does not certify."""
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 90, "fixed_targets_2024_25": 100}},
        )
        # Every parameter must be answered before submission (completeness gate); the C1 values above are kept.
        self.assessment.refresh_from_db()
        fill_assessment(self.assessment)
        self.client.force_authenticate(user=self.principal_a)
        resp = self.client.post(f"/api/college/assessments/{self.assessment.assessment_id}/submit/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "SUBMITTED")
        self.assertIsNotNone(resp.data["submitted_at"])
        self.assertIsNone(resp.data["certified_score"])  # Submission does NOT certify

        # Submitted assessment cannot be modified via parameter update
        resp_update = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C1/",
            {"raw_inputs": {"C1.1": {"achieved_targets_2024_25": 99, "fixed_targets_2024_25": 100}}},
            format="json",
        )
        self.assertIn(resp_update.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT))

    def test_incomplete_submission_rejected(self):
        """A partially answered assessment cannot be submitted through the API."""
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 90, "fixed_targets_2024_25": 100}},
        )
        self.client.force_authenticate(user=self.principal_a)
        resp = self.client.post(f"/api/college/assessments/{self.assessment.assessment_id}/submit/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["code"], "SUBMISSION_INCOMPLETE")

    def test_double_submission_rejected(self):
        """Attempting to submit an already submitted assessment returns 409 conflict."""
        self.assessment.refresh_from_db()
        fill_assessment(self.assessment)
        self.client.force_authenticate(user=self.principal_a)
        first = self.client.post(f"/api/college/assessments/{self.assessment.assessment_id}/submit/", format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        # Second submission attempt
        resp_double = self.client.post(f"/api/college/assessments/{self.assessment.assessment_id}/submit/", format="json")
        self.assertEqual(resp_double.status_code, status.HTTP_409_CONFLICT)

    def test_cross_college_submission_blocked(self):
        """Principal of College B cannot submit assessment of College A."""
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 90, "fixed_targets_2024_25": 100}},
        )
        self.client.force_authenticate(user=self.principal_b)
        resp = self.client.post(f"/api/college/assessments/{self.assessment.assessment_id}/submit/", format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def _add_evidence(self, param_code: str, subcrit_code: str, evid_type: str):
        """Uploads and associates evidence while the institution is still editing (DRAFT)."""
        doc = EvidenceService.create_evidence(
            uploader=self.principal_a,
            assessment_id=self.assessment.assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id=self.college_a.aishe_code,
            original_filename=f"{subcrit_code.lower()}_doc.pdf",
            file_path=f"/media/col/{subcrit_code.lower()}_doc.pdf",
            mime_type="application/pdf",
            file_size=15000,
            file_checksum="a" * 64,
            evidence_type=evid_type,
            document_date=date(2025, 8, 1),
            academic_year="2025-26",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id=param_code,
            subcriterion_id=subcrit_code,
            actor=self.principal_a,
            academic_year="2025-26",
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_a)
        return doc

    def _submit_and_verify(self, *docs):
        """The institution submits; the committee then verifies the evidence (it cannot before submission)."""
        self.assessment.refresh_from_db()
        fill_assessment(self.assessment)
        CollegeAssessmentService.submit_assessment(self.assessment.assessment_id, submitting_user=self.principal_a)
        for doc in docs:
            EvidenceService.verify_evidence(evidence_id=doc.pk, verifier=self.reviewer, reason="Verified for test")

    def test_reviewer_access_in_phase_7c(self):
        """Committee reviewers read a College assessment only once it is submitted, and never modify parameters."""
        self.client.force_authenticate(user=self.reviewer)
        # A DRAFT belongs to the institution: reviewers cannot see it (COM-02)
        resp_draft = self.client.get(f"/api/college/assessments/{self.assessment.assessment_id}/")
        self.assertEqual(resp_draft.status_code, status.HTTP_403_FORBIDDEN)

        self.assessment.refresh_from_db()
        fill_assessment(self.assessment)
        CollegeAssessmentService.submit_assessment(self.assessment.assessment_id, submitting_user=self.principal_a)
        # Committee reviewer can inspect the submitted assessment
        resp_detail = self.client.get(f"/api/college/assessments/{self.assessment.assessment_id}/")
        self.assertEqual(resp_detail.status_code, status.HTTP_200_OK)

        # Reviewer cannot modify parameter inputs directly (institutional duty segregation)
        resp_put = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C1/",
            {"raw_inputs": {"C1.1": {"approved": True}}},
            format="json",
        )
        self.assertEqual(resp_put.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_c5_boundary_void_preservation(self):
        """API evaluates C5: exactly 75.0% falls in boundary void -> BOUNDARY_UNRESOLVED, 0 raw score.
        C5.1 is SOURCE_SILENT, so no evidence may be attached to it."""
        self.client.force_authenticate(user=self.principal_a)

        # Submit exactly 75.0% (75 / 100)
        put_resp = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C5/",
            {"raw_inputs": {"C5.1": {"admitted_students": 75, "sanctioned_intake": 100}}},
            format="json",
        )
        self.assertEqual(put_resp.status_code, status.HTTP_200_OK)

        # Evaluate via API
        eval_resp = self.client.post(
            f"/api/college/assessments/{self.assessment.assessment_id}/evaluate/",
            format="json",
        )
        self.assertEqual(eval_resp.status_code, status.HTTP_200_OK)
        c5_res = eval_resp.data["parameter_results"]["C5"]
        c5_sub = c5_res["subcriteria_results"]["C5.1"]
        self.assertEqual(c5_sub["resolution_status"], "BOUNDARY_UNRESOLVED")
        self.assertEqual(c5_sub["raw_score"], 0.0)

    def test_api_c7_no_invented_multiplier(self):
        """API evaluates C7: tops out at 3.0 marks (the source's highest tier); no x2 multiplier towards the stated 6."""
        self.client.force_authenticate(user=self.principal_a)

        # 100% of SEDG students covered: the highest tier (I) = 3 marks
        put_resp = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C7/",
            {"raw_inputs": {"C7.1": {"sedg_bridge_students": 100, "total_sedg_students": 100}}},
            format="json",
        )
        self.assertEqual(put_resp.status_code, status.HTTP_200_OK)
        doc = self._add_evidence("C7", "C7.1", "EVID_C7_OFFICE_ORDERS")
        self._submit_and_verify(doc)

        eval_resp = self.client.get(f"/api/college/assessments/{self.assessment.assessment_id}/evaluate/")
        self.assertEqual(eval_resp.status_code, status.HTTP_200_OK)
        c7_res = eval_resp.data["parameter_results"]["C7"]
        # ADVISORY policy C7_MAXIMUM: scored literally from the tiers
        self.assertEqual(c7_res["resolution_status"], "CALCULABLE")
        # Raw score must be 3.0 and NOT 6.0 (proving no invented x2 multiplier)
        self.assertEqual(c7_res["raw_score"], 3.0)
        self.assertEqual(c7_res["evidence_gated_score"], 3.0)

    def test_api_c8_no_invented_marks(self):
        """API evaluates C8: binary nomination (policy C8_BINARY). A claimed nomination is worth 2 marks, but
        without verified documentary proof no marks are awarded."""
        self.client.force_authenticate(user=self.principal_a)

        put_resp = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C8/",
            {"raw_inputs": {"C8.1": {"verified": True}}},
            format="json",
        )
        self.assertEqual(put_resp.status_code, status.HTTP_200_OK)

        # Evaluate via API
        eval_resp = self.client.post(
            f"/api/college/assessments/{self.assessment.assessment_id}/evaluate/",
            format="json",
        )
        self.assertEqual(eval_resp.status_code, status.HTTP_200_OK)
        c8_res = eval_resp.data["parameter_results"]["C8"]
        self.assertEqual(c8_res["resolution_status"], "CALCULABLE")
        self.assertEqual(c8_res["raw_score"], 2.0)
        self.assertEqual(c8_res["evidence_gated_score"], 0.0)  # no verified proof -> no marks

    def test_api_c16_max_mark_ceiling_preserved(self):
        """API evaluates C16: 5 1-mark items cannot exceed declared max marks of 4.0 (ADVISORY cap)."""
        self.client.force_authenticate(user=self.principal_a)

        # Submit all 5 items
        put_resp = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C16/",
            {"raw_inputs": {f"C16.{i}": {"verified": True} for i in range(1, 6)}},
            format="json",
        )
        self.assertEqual(put_resp.status_code, status.HTTP_200_OK)

        # Evaluate via API
        eval_resp = self.client.post(
            f"/api/college/assessments/{self.assessment.assessment_id}/evaluate/",
            format="json",
        )
        self.assertEqual(eval_resp.status_code, status.HTTP_200_OK)
        c16_res = eval_resp.data["parameter_results"]["C16"]
        self.assertEqual(c16_res["resolution_status"], "CALCULABLE")
        self.assertEqual(c16_res["max_marks"], 4.0)
        # Score can never exceed declared max marks
        self.assertEqual(c16_res["raw_score"], 4.0)
        if c16_res["final_score"] is not None:
            self.assertLessEqual(c16_res["final_score"], 4.0)

    def test_legacy_nominations_isolation(self):
        """Legacy nominations cannot interact with College assessment API."""
        self.client.force_authenticate(user=self.principal_a)
        # Verify legacy Nomination model count is independent of College assessments
        nom_count_before = Nomination.objects.count()
        # One assessment per college per year: create College B's (College A already has one)
        CollegeAssessmentService.create_assessment(
            college_id=self.college_b.pk,
            created_by=self.principal_b,
        )
        nom_count_after = Nomination.objects.count()
        self.assertEqual(nom_count_before, nom_count_after)
