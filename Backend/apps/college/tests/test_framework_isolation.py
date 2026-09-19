"""
Unit Tests for Framework Isolation: COLLEGE_2026 vs UNIVERSITY_2026 (Section 26)
Verifies:
- College cannot load U1–U20 parameters
- University cannot load C1–C22 parameters
- College evidence cannot satisfy University parameters
- University evidence cannot satisfy College parameters
- College assessment cannot be scored with University rules
- University assessment cannot be scored with College rules
"""
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authentication.models import College
from apps.college.models import CollegeAssessment
from apps.college.registry import (
    get_college_parameter,
    validate_college_parameter_code,
)
from apps.college.services import CollegeAssessmentService
from apps.college.validators import (
    CollegeValidationError,
    validate_framework_code as validate_college_framework,
    validate_institution_type as validate_college_institution,
    validate_parameter as validate_college_param,
)
from apps.evidence.enums import EvidenceLifecycleState
from apps.evidence.models import EvidenceDocument, EvidenceSubcriterionAssociation
from apps.scoring.domain import (
    AssessmentContext,
    AssessmentInput,
    AssessmentPeriod,
    ParameterInput,
)
from apps.scoring.engine import FrameworkMismatchException, NEP2026ScoringEngine
from apps.scoring.enums import FrameworkType, InstitutionType
from apps.university.models import University, UniversityAssessment
from apps.university.registry import (
    get_university_parameter,
    validate_university_parameter_code,
)
from apps.university.validators import (
    UniversityValidationError,
    validate_framework_code as validate_uni_framework,
    validate_institution_type as validate_uni_institution,
    validate_parameter as validate_uni_param,
)

User = get_user_model()


class FrameworkIsolationTests(TestCase):

    def setUp(self):
        self.college = College.objects.create(name="Isolation College", aishe_code="C-ISO-01")
        self.university = University.objects.create(name="Isolation University", aishe_code="U-ISO-01")

        self.user = User.objects.create_user(
            email="admin@iso.edu",
            full_name="Admin Iso",
            role="admin",
            password="pass",
        )

        self.college_assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college.pk,
            assessment_id="ASSESS-2026-COL-ISO-01",
            created_by=self.user,
        )

    def test_college_cannot_load_university_parameters(self):
        """College parameter registry rejects U1 through U20."""
        for i in range(1, 21):
            u_code = f"U{i}"
            self.assertFalse(validate_college_parameter_code(u_code))
            with self.assertRaises(KeyError):
                get_college_parameter(u_code)
            with self.assertRaises(CollegeValidationError):
                validate_college_param(u_code)

    def test_university_cannot_load_college_parameters(self):
        """University parameter registry rejects C1 through C22."""
        for i in range(1, 23):
            c_code = f"C{i}"
            self.assertFalse(validate_university_parameter_code(c_code))
            with self.assertRaises(KeyError):
                get_university_parameter(c_code)
            with self.assertRaises(UniversityValidationError):
                validate_uni_param(c_code)

    def test_framework_and_institution_validators_isolated(self):
        """College validators reject University codes and vice-versa."""
        with self.assertRaises(CollegeValidationError):
            validate_college_framework("UNIVERSITY_2026")
        with self.assertRaises(CollegeValidationError):
            validate_college_institution("UNIVERSITY")

        with self.assertRaises(UniversityValidationError):
            validate_uni_framework("COLLEGE_2026")
        with self.assertRaises(UniversityValidationError):
            validate_uni_institution("COLLEGE")

    def test_scoring_engine_rejects_framework_institution_mismatch(self):
        """NEP2026ScoringEngine rejects College framework with University institution or vice-versa."""
        engine = NEP2026ScoringEngine()

        # Mismatch 1: Framework = COLLEGE_2026, Institution = UNIVERSITY
        mismatched_context = AssessmentContext(
            assessment_id="ASSESS-MISMATCH-01",
            institution_id="C-ISO-01",
            institution_type=InstitutionType.UNIVERSITY,  # WRONG
            framework=FrameworkType.COLLEGE_2026,
            assessment_period=AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30)),
        )
        bad_input = AssessmentInput(context=mismatched_context, parameters={})
        with self.assertRaises(FrameworkMismatchException):
            engine.score_assessment(bad_input)

        # Mismatch 2: Framework = UNIVERSITY_2026, Institution = COLLEGE
        mismatched_context_2 = AssessmentContext(
            assessment_id="ASSESS-MISMATCH-02",
            institution_id="U-ISO-01",
            institution_type=InstitutionType.COLLEGE,  # WRONG
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30)),
        )
        bad_input_2 = AssessmentInput(context=mismatched_context_2, parameters={})
        with self.assertRaises(FrameworkMismatchException):
            engine.score_assessment(bad_input_2)

    def test_cross_framework_evidence_isolation(self):
        """College assessment input builder completely filters out University evidence."""
        # Create University evidence
        uni_doc = EvidenceDocument.objects.create(
            assessment_id=self.college_assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="U-ISO-01",
            original_filename="uni_evidence.pdf",
            file_checksum="3333333333333333333333333333333333333333333333333333333333333333",
            uploader=self.user,
            evidence_type="EVID_C1_APPROVED_IDP",
            status=EvidenceLifecycleState.EVIDENCE_VERIFIED,
        )

        EvidenceSubcriterionAssociation.objects.create(
            evidence=uni_doc,
            parameter_id="C1",
            subcriterion_id="C1.1",
            associated_by=self.user,
            academic_year="2025-26",
            is_active=True,
        )

        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.college_assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}},
        )

        # Build input: College builder must discard uni_doc because doc.framework != COLLEGE_2026
        built_input = CollegeAssessmentService.build_assessment_input(self.college_assessment.assessment_id)
        c1_docs = built_input.parameters["C1"].subcriteria_inputs["C1.1"].evidence_docs
        self.assertEqual(len(c1_docs), 0)
