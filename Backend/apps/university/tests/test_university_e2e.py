"""Category J Tests: End-to-End University Evaluation.

Verifies:
- Full lifecycle: University creation, assessment initiation, parameter inputs update.
- Evidence upload and subcriterion association.
- Evidence readiness inspection.
- Evidence-gated evaluation before verification (blocked / 0 marks).
- Evidence verification.
- Authoritative scoring calculation via frozen NEP2026ScoringEngine.
- Persistence of calculated marks and results on UniversityAssessment.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.university.models import University, UniversityAssessment
from apps.university.services import UniversityAssessmentService
from apps.evidence.models import EvidenceDocument
from apps.evidence.services import EvidenceService

User = get_user_model()


class UniversityEndToEndTests(TestCase):
    """End-to-end integration test for the University assessment workflow."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="dean@haryanauniv.edu.in",
            full_name="Dean Academic",
            role="admin",
            password="SecureDeanPassword2026!",
        )
        self.university = University.objects.create(
            name="Kurukshetra University",
            aishe_code="U-0160",
            state="Haryana",
        )

    def test_full_lifecycle_university_assessment(self):
        # 1. Create University Assessment
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.university.id,
            academic_year="2025-26",
            created_by=self.user,
        )
        self.assertEqual(assessment.status, "DRAFT")
        self.assertEqual(assessment.framework, "UNIVERSITY_2026")
        self.assertIsNone(assessment.certified_score)

        # 2. Update parameter inputs for U1 (Apprenticeship Embedded Degree Programmes)
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={
                "programmes_count": 12,
                "U1.1": {"programmes_count": 12},
            },
        )

        # 3. Upload evidence document (status initially EVIDENCE_PENDING)
        doc = EvidenceDocument.objects.create(
            assessment_id=assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.university.aishe_code,
            original_filename="u1_programmes.pdf",
            file_path="mock/path/u1_programmes.pdf",
            mime_type="application/pdf",
            file_size=10240,
            file_checksum="c" * 64,
            uploader=self.user,
            evidence_type="EVID_U1_APPROVAL",
            status="EVIDENCE_PENDING",
            is_active=True,
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc.id,
            parameter_id="U1",
            subcriterion_id="U1.1",
            actor=self.user,
        )

        # 4. Check readiness - evidence is PENDING, so not ready
        is_ready, blocking_reasons, summary = UniversityAssessmentService.check_assessment_readiness(
            assessment.assessment_id
        )
        self.assertFalse(is_ready)

        # 5. Evaluate scoring while evidence is PENDING -> score should be 0.0
        pending_result = UniversityAssessmentService.evaluate_assessment_scoring(
            assessment.assessment_id
        )
        u1_pending_marks = pending_result.parameter_results["U1"].evidence_gated_score
        self.assertEqual(u1_pending_marks, 0.0)

        # 6. Verify evidence
        doc.status = "EVIDENCE_VERIFIED"
        doc.save(update_fields=["status"])

        # 7. Check coverage now - U1.1 has verified evidence
        coverage = UniversityAssessmentService.evaluate_assessment_coverage(
            assessment.assessment_id
        )
        self.assertEqual(coverage.summary.verified_subcriteria, 1)

        # 8. Evaluate scoring with VERIFIED evidence
        verified_result = UniversityAssessmentService.evaluate_assessment_scoring(
            assessment.assessment_id
        )
        u1_verified_marks = verified_result.parameter_results["U1"].evidence_gated_score
        # Programme count 12 > 10.0 -> max score 4.0
        self.assertEqual(u1_verified_marks, 4.0)

        # 9. Verify assessment model updated
        assessment.refresh_from_db()
        self.assertEqual(assessment.certified_score, Decimal("4.0"))
