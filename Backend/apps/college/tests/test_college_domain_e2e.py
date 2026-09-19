"""
End-to-End Domain Service Tests for College Framework (Phase 7A)
Verifies full domain integration lifecycle:
1. Assessment creation (COLLEGE_2026, 2025-26, 2025-07-01 to 2026-06-30)
2. Parameter input recording across C1–C22
3. Evidence upload and association to subcriteria
4. Evidence verification through Phase 5C
5. Evidence coverage and readiness evaluation through Phase 5D
6. Formal assessment submission
7. Deterministic frozen scoring evaluation via NEP2026ScoringEngine
8. Immutable audit trail verification
"""
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authentication.models import College
from apps.college.models import CollegeAssessment, CollegeAssessmentAuditLog
from apps.college.services import CollegeAssessmentService
from apps.college.validators import (
    CollegeValidationError,
    InvalidStateTransitionError,
)
from apps.evidence.enums import (
    EvidenceLifecycleState,
    VerificationDecision,
)
from apps.evidence.services import EvidenceService

User = get_user_model()


class CollegeDomainE2ETests(TestCase):

    def setUp(self):
        self.college = College.objects.create(name="Govt College Gurugram", aishe_code="C-00301")
        self.principal = User.objects.create_user(
            email="principal@gcgurugram.ac.in",
            full_name="Principal Gurugram",
            role="principal",
            college=self.college,
            password="pass",
        )
        self.reviewer = User.objects.create_user(
            email="reviewer@dhe.gov.in",
            full_name="Committee Reviewer",
            role="committee",
            password="pass",
        )

    def test_complete_college_assessment_lifecycle(self):
        """End-to-end integration test across all Phase 7A domain responsibilities."""
        # 1. Create Assessment
        assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college.pk,
            academic_year="2025-26",
            created_by=self.principal,
        )
        self.assertEqual(assessment.framework, "COLLEGE_2026")
        self.assertEqual(assessment.status, "DRAFT")
        self.assertEqual(assessment.period_start, date(2025, 7, 1))
        self.assertEqual(assessment.period_end, date(2026, 6, 30))

        # 2. Update parameter inputs for C1 (IDP), C2 (Internship), C10 (MoUs)
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}},
        )
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="C2",
            raw_inputs={"C2.1": {"students_completed": 92, "eligible_students": 100}},
            activity_date=date(2025, 11, 10),
        )
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="C10",
            raw_inputs={"C10.1": {"active_mous_count": 5}},
        )

        assessment.refresh_from_db()
        self.assertIn("C1", assessment.parameter_data)
        self.assertIn("C2", assessment.parameter_data)
        self.assertIn("C10", assessment.parameter_data)

        # 3. Upload and Associate Evidence for C1 and C2
        doc_c1 = EvidenceService.create_evidence(
            uploader=self.principal,
            assessment_id=assessment.assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id=self.college.aishe_code,
            original_filename="idp_approval.pdf",
            file_path="/media/col/idp_approval.pdf",
            mime_type="application/pdf",
            file_size=15000,
            file_checksum="4444444444444444444444444444444444444444444444444444444444444444",
            evidence_type="EVID_C1_APPROVED_IDP",
            document_date=date(2025, 8, 1),
            academic_year="2024-25",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc_c1.pk,
            parameter_id="C1",
            subcriterion_id="C1.1",
            actor=self.principal,
            academic_year="2024-25",
        )

        doc_c2 = EvidenceService.create_evidence(
            uploader=self.principal,
            assessment_id=assessment.assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id=self.college.aishe_code,
            original_filename="hoi_internship_cert.pdf",
            file_path="/media/col/hoi_internship_cert.pdf",
            mime_type="application/pdf",
            file_size=12000,
            file_checksum="5555555555555555555555555555555555555555555555555555555555555555",
            evidence_type="EVID_C2_HOI_CERT",
            document_date=date(2025, 11, 1),
            academic_year="2025-26",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc_c2.pk,
            parameter_id="C2",
            subcriterion_id="C2.1",
            actor=self.principal,
            academic_year="2025-26",
        )

        # 4. Verify Evidence via Phase 5C
        EvidenceService.submit_for_verification(doc_c1.pk, self.principal)
        EvidenceService.verify_evidence(
            evidence_id=doc_c1.pk,
            verifier=self.reviewer,
            reason="Approved IDP document",
        )

        EvidenceService.submit_for_verification(doc_c2.pk, self.principal)
        EvidenceService.verify_evidence(
            evidence_id=doc_c2.pk,
            verifier=self.reviewer,
            reason="Approved HOI certificate",
        )

        # 5. Evaluate Coverage and Readiness via Phase 5D
        coverage_report = CollegeAssessmentService.evaluate_assessment_coverage(
            assessment_id=assessment.assessment_id,
            user=self.principal,
        )
        self.assertEqual(coverage_report.framework, "COLLEGE_2026")
        param_ids = [p.parameter_id for p in coverage_report.parameters]
        self.assertIn("C1", param_ids)
        self.assertIn("C2", param_ids)

        # 6. Submit Assessment
        submitted_assessment = CollegeAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=self.principal,
        )
        self.assertEqual(submitted_assessment.status, "SUBMITTED")
        self.assertIsNotNone(submitted_assessment.submitted_at)

        # Cannot resubmit when already submitted
        with self.assertRaises(InvalidStateTransitionError):
            CollegeAssessmentService.submit_assessment(
                assessment_id=assessment.assessment_id,
                submitting_user=self.principal,
            )

        # 7. Evaluate Scoring via frozen NEP2026ScoringEngine
        score_result = CollegeAssessmentService.evaluate_assessment_scoring(assessment.assessment_id)
        self.assertEqual(score_result.framework, "COLLEGE_2026")
        self.assertEqual(score_result.parameter_results["C1"].final_score, 6.0)
        self.assertEqual(score_result.parameter_results["C2"].final_score, 4.0)

        # C10 has no verified evidence uploaded -> evidence_gated_score must be 0.0
        self.assertEqual(score_result.parameter_results["C10"].raw_score, 5.0)
        self.assertEqual(score_result.parameter_results["C10"].evidence_gated_score, 0.0)

        # Assessment model score snapshot updated
        assessment.refresh_from_db()
        self.assertEqual(assessment.certified_score, 10.0)  # 6.0 (C1) + 4.0 (C2) = 10.0

        # 8. Audit logs populated
        audit_logs = CollegeAssessmentAuditLog.objects.filter(assessment=assessment)
        self.assertTrue(audit_logs.filter(action="CREATED").exists())
        self.assertTrue(audit_logs.filter(action="PARAMETER_UPDATED").exists())
        self.assertTrue(audit_logs.filter(action="SUBMITTED").exists())
