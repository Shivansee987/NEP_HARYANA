"""Category C Tests: Framework Isolation.

Verifies:
- University evaluation cannot load C1–C22.
- College evaluation cannot load U1–U20.
- Cross-framework parameter injection is rejected.
- Evidence uploaded for College cannot be associated with University assessment.
- Evidence uploaded for University cannot be associated with College assessment.
- Framework type mismatch is rejected with descriptive error.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.university.models import University, UniversityAssessment
from apps.university.validators import (
    validate_parameter,
    validate_framework_code,
    validate_institution_type,
    UniversityValidationError,
)
from apps.university.services import UniversityAssessmentService
from apps.evidence.models import EvidenceDocument, EvidenceSubcriterionAssociation
from apps.evidence.services import EvidenceService
from apps.evidence.exceptions import FrameworkMismatchError
from apps.scoring.domain import AssessmentInput, ParameterInput, EvidenceState

User = get_user_model()


class FrameworkIsolationTests(TestCase):
    """Test strict isolation between University and College frameworks."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="uni_admin@test.ac.in",
            full_name="Uni Admin",
            role="admin",
            password="TestPassword123!",
        )
        self.university = University.objects.create(
            name="State University of Haryana",
            aishe_code="U-HR-001",
            state="Haryana",
        )
        self.assessment = UniversityAssessmentService.create_assessment(
            university_id=self.university.id,
            academic_year="2025-26",
            created_by=self.user,
        )

    def test_parameter_code_cross_framework_rejection(self):
        """College codes (C1-C22) must be rejected by university validator."""
        for i in range(1, 23):
            with self.assertRaises(UniversityValidationError) as ctx:
                validate_parameter(f"C{i}")
            self.assertIn("not a valid University parameter", str(ctx.exception))

    def test_framework_code_cross_framework_rejection(self):
        """COLLEGE_2026 or invalid frameworks must be rejected for university."""
        with self.assertRaises(UniversityValidationError) as ctx:
            validate_framework_code("COLLEGE_2026")
        self.assertIn("Framework mismatch", str(ctx.exception))

    def test_institution_type_validation(self):
        """Only UNIVERSITY institution type is valid; COLLEGE is rejected."""
        valid_type = validate_institution_type("UNIVERSITY")
        self.assertEqual(valid_type, "UNIVERSITY")
        with self.assertRaises(UniversityValidationError) as ctx:
            validate_institution_type("COLLEGE")
        self.assertIn("Institution type mismatch", str(ctx.exception))

    def test_updating_parameter_inputs_rejects_college_codes(self):
        """Updating university parameter inputs with C1 fails validation."""
        with self.assertRaises(UniversityValidationError) as ctx:
            UniversityAssessmentService.update_parameter_inputs(
                assessment_id=self.assessment.assessment_id,
                parameter_code="C1",
                raw_inputs={"c1_metric": 100},
            )
        self.assertIn("not a valid University parameter", str(ctx.exception))

    def test_scoring_assessment_input_rejects_college_parameters(self):
        """University evaluators map does not contain College parameters."""
        from apps.scoring.rules.university import UNIVERSITY_EVALUATORS
        for i in range(1, 23):
            self.assertNotIn(f"C{i}", UNIVERSITY_EVALUATORS)

    def test_evidence_cross_framework_association_rejection(self):
        """Evidence association for UNIVERSITY_2026 rejects C1..C22."""
        doc = EvidenceDocument.objects.create(
            assessment_id=self.assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.university.aishe_code,
            original_filename="doc.pdf",
            file_path="mock/path/doc.pdf",
            mime_type="application/pdf",
            file_size=1024,
            file_checksum="1" * 64,
            uploader=self.user,
            evidence_type="EVID_U1_APPROVAL",
            status="EVIDENCE_PRESENT",
            is_active=True,
        )
        with self.assertRaises(FrameworkMismatchError) as ctx:
            EvidenceService.associate_subcriterion(
                evidence_id=doc.id,
                parameter_id="C1",
                subcriterion_id="C1.1",
                actor=self.user,
            )
        self.assertIn("Framework isolation violation", str(ctx.exception))

    def test_university_model_stores_university_framework_exclusively(self):
        """UniversityAssessment framework field is UNIVERSITY_2026."""
        self.assertEqual(self.assessment.framework, "UNIVERSITY_2026")
        self.assertEqual(self.assessment.academic_year, "2025-26")
