"""
Unit Tests for College Evidence Integration and Gating (Section 23)
Verifies:
- College evidence associations to C1–C22 subcriteria
- Evidence gating:
  - EVIDENCE_PRESENT: 0 marks unlocked
  - EVIDENCE_PENDING: 0 marks unlocked
  - EVIDENCE_REJECTED: 0 marks unlocked
  - EVIDENCE_VERIFIED: unlocks eligible scoring marks
- Invalid period evidence blocked
- Wrong framework / institution rejected
- Cross-framework contamination: University evidence cannot satisfy College subcriteria
"""
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authentication.models import College
from apps.college.models import CollegeAssessment
from apps.college.services import CollegeAssessmentService
from apps.evidence.enums import (
    EvidenceLifecycleState,
    VerificationDecision,
)
from apps.evidence.models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
)
from apps.evidence.services import EvidenceService
from apps.scoring.enums import FrameworkType, GatingStatus

User = get_user_model()


class CollegeEvidenceIntegrationTests(TestCase):

    def setUp(self):
        self.college = College.objects.create(name="Govt College Karnal", aishe_code="C-00101")
        self.other_college = College.objects.create(name="Govt College Rohtak", aishe_code="C-00102")

        self.principal_user = User.objects.create_user(
            email="principal@gckarnal.ac.in",
            full_name="Principal Karnal",
            role="principal",
            college=self.college,
            password="pass",
        )
        self.reviewer_user = User.objects.create_user(
            email="reviewer@dhe.haryana.gov.in",
            full_name="Committee Reviewer",
            role="committee",
            password="pass",
        )

        self.assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college.pk,
            assessment_id="ASSESS-2026-COL-00101-EVTEST",
            created_by=self.principal_user,
        )

    def _upload_college_doc(
        self,
        doc_type: str = "EVID_C1_APPROVED_IDP",
        checksum: str = "1111111111111111111111111111111111111111111111111111111111111111",
        doc_date: date = date(2025, 9, 1),
        academic_year: str = "2024-25",
    ) -> EvidenceDocument:
        return EvidenceService.create_evidence(
            uploader=self.principal_user,
            assessment_id=self.assessment.assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id=self.college.aishe_code,
            original_filename="idp_target_doc.pdf",
            file_path="/media/evidence/col/idp_target_doc.pdf",
            mime_type="application/pdf",
            file_size=10240,
            file_checksum=checksum,
            evidence_type=doc_type,
            document_date=doc_date,
            academic_year=academic_year,
        )

    def test_valid_college_evidence_association(self):
        """Verifies associating uploaded College evidence to C1.1."""
        doc = self._upload_college_doc()
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="C1",
            subcriterion_id="C1.1",
            actor=self.principal_user,
            academic_year="2024-25",
        )
        self.assertTrue(assoc.is_active)
        self.assertEqual(assoc.parameter_id, "C1")
        self.assertEqual(assoc.subcriterion_id, "C1.1")

    def test_evidence_gating_present_state(self):
        """EVIDENCE_PRESENT (uploaded but not verified) does NOT unlock scoring."""
        doc = self._upload_college_doc()
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="C1",
            subcriterion_id="C1.1",
            actor=self.principal_user,
            academic_year="2024-25",
        )

        # Update assessment parameter inputs with 95% target achievement
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}},
        )

        result = CollegeAssessmentService.evaluate_assessment_scoring(self.assessment.assessment_id)
        c1_res = result.parameter_results["C1"]
        # Raw score may be 6.0 based on raw inputs, but evidence_gated_score MUST be 0.0
        self.assertEqual(c1_res.raw_score, 6.0)
        self.assertEqual(c1_res.evidence_gated_score, 0.0)
        self.assertIsNone(c1_res.final_score)

    def test_evidence_gating_pending_state(self):
        """EVIDENCE_PENDING (submitted for verification) does NOT unlock scoring."""
        doc = self._upload_college_doc()
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="C1",
            subcriterion_id="C1.1",
            actor=self.principal_user,
            academic_year="2024-25",
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)

        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}},
        )

        result = CollegeAssessmentService.evaluate_assessment_scoring(self.assessment.assessment_id)
        c1_res = result.parameter_results["C1"]
        self.assertEqual(c1_res.evidence_gated_score, 0.0)
        self.assertIsNone(c1_res.final_score)

    def test_evidence_gating_rejected_state(self):
        """EVIDENCE_REJECTED does NOT unlock scoring."""
        doc = self._upload_college_doc()
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="C1",
            subcriterion_id="C1.1",
            actor=self.principal_user,
            academic_year="2024-25",
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        EvidenceService.reject_evidence(
            evidence_id=doc.pk,
            verifier=self.reviewer_user,
            reason="Blurry scanned copy",
            rejection_code="REJ_BLURRY",
        )

        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}},
        )

        result = CollegeAssessmentService.evaluate_assessment_scoring(self.assessment.assessment_id)
        c1_res = result.parameter_results["C1"]
        self.assertEqual(c1_res.evidence_gated_score, 0.0)
        self.assertIsNone(c1_res.final_score)

    def test_evidence_gating_verified_state_unlocks_score(self):
        """EVIDENCE_VERIFIED successfully unlocks scoring eligibility."""
        doc = self._upload_college_doc()
        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="C1",
            subcriterion_id="C1.1",
            actor=self.principal_user,
            academic_year="2024-25",
        )
        EvidenceService.submit_for_verification(doc.pk, self.principal_user)
        EvidenceService.verify_evidence(
            evidence_id=doc.pk,
            verifier=self.reviewer_user,
            reason="Approved valid IDP targets",
        )

        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}},
        )

        result = CollegeAssessmentService.evaluate_assessment_scoring(self.assessment.assessment_id)
        c1_res = result.parameter_results["C1"]
        self.assertEqual(c1_res.raw_score, 6.0)
        self.assertEqual(c1_res.evidence_gated_score, 6.0)
        self.assertEqual(c1_res.final_score, 6.0)

    def test_university_evidence_cannot_satisfy_college(self):
        """University evidence associated with a University framework cannot satisfy College scoring."""
        uni_doc = EvidenceDocument.objects.create(
            assessment_id="ASSESS-2026-COL-00101-EVTEST",  # same assessment_id spoof
            framework="UNIVERSITY_2026",  # University framework
            institution_type="UNIVERSITY",
            institution_id="U-99999",
            original_filename="spoofed_uni_doc.pdf",
            file_checksum="2222222222222222222222222222222222222222222222222222222222222222",
            uploader=self.principal_user,
            evidence_type="EVID_C1_APPROVED_IDP",
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED,
        )

        # Associate to C1.1
        EvidenceSubcriterionAssociation.objects.create(
            evidence=uni_doc,
            parameter_id="C1",
            subcriterion_id="C1.1",
            associated_by=self.principal_user,
            academic_year="2025-26",
            is_active=True,
        )

        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}},
        )

        # CollegeAssessmentService.build_assessment_input filters doc.framework == COLLEGE_FRAMEWORK_CODE
        assessment_input = CollegeAssessmentService.build_assessment_input(self.assessment.assessment_id)
        c1_input = assessment_input.parameters["C1"]
        c1_1_input = c1_input.subcriteria_inputs["C1.1"]

        # University evidence is ignored
        self.assertEqual(len(c1_1_input.evidence_docs), 0)

        # Scoring remains locked: evidence_gated_score=0.0, final_score=None
        result = CollegeAssessmentService.evaluate_assessment_scoring(self.assessment.assessment_id)
        self.assertEqual(result.parameter_results["C1"].evidence_gated_score, 0.0)
        self.assertIsNone(result.parameter_results["C1"].final_score)
