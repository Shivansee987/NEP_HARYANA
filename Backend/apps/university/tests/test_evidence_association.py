"""Category G Tests: University Evidence Association.

Verifies:
- Associating evidence documents with University parameters and subcriteria.
- Multi-subcriterion association (e.g., U4.A vs U4.B).
- Associating with UNIVERSITY_2026 framework validation.
- Rejection of cross-framework parameter codes.
- Querying evidence for University parameters and subcriteria.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.university.models import University, UniversityAssessment
from apps.university.services import UniversityAssessmentService
from apps.evidence.models import EvidenceDocument, EvidenceSubcriterionAssociation
from apps.evidence.services import EvidenceService
from apps.evidence.exceptions import FrameworkMismatchError

User = get_user_model()


class UniversityEvidenceAssociationTests(TestCase):
    """Test evidence association specifically under the University framework."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="officer@univ.ac.in",
            full_name="Uni Officer",
            role="admin",
            password="TestPassword123!",
        )
        self.university = University.objects.create(
            name="Central University of Haryana",
            aishe_code="U-CUH-001",
            state="Haryana",
        )
        self.assessment = UniversityAssessmentService.create_assessment(
            university_id=self.university.id,
            academic_year="2025-26",
            created_by=self.user,
        )
        self.doc1 = EvidenceDocument.objects.create(
            assessment_id=self.assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.university.aishe_code,
            original_filename="idp_24_25.pdf",
            file_path="mock/path/idp_24_25.pdf",
            mime_type="application/pdf",
            file_size=2048,
            file_checksum="a" * 64,
            uploader=self.user,
            evidence_type="EVID_U4_PROGRESS_REPORT",
            status="EVIDENCE_VERIFIED",
            is_active=True,
        )
        self.doc2 = EvidenceDocument.objects.create(
            assessment_id=self.assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.university.aishe_code,
            original_filename="idp_25_26.pdf",
            file_path="mock/path/idp_25_26.pdf",
            mime_type="application/pdf",
            file_size=4096,
            file_checksum="b" * 64,
            uploader=self.user,
            evidence_type="EVID_U4_PROGRESS_REPORT",
            status="EVIDENCE_VERIFIED",
            is_active=True,
        )

    def test_successful_subcriteria_association(self):
        """Associate doc1 with U4.A and doc2 with U4.B."""
        assoc1 = EvidenceService.associate_subcriterion(
            evidence_id=self.doc1.id,
            parameter_id="U4",
            subcriterion_id="U4.A",
            actor=self.user,
        )
        assoc2 = EvidenceService.associate_subcriterion(
            evidence_id=self.doc2.id,
            parameter_id="U4",
            subcriterion_id="U4.B",
            actor=self.user,
        )

        self.assertEqual(assoc1.parameter_id, "U4")
        self.assertEqual(assoc1.subcriterion_id, "U4.A")

        self.assertEqual(assoc2.parameter_id, "U4")
        self.assertEqual(assoc2.subcriterion_id, "U4.B")

        # Query associations for the assessment
        assocs = EvidenceSubcriterionAssociation.objects.filter(
            evidence__assessment_id=self.assessment.assessment_id,
            parameter_id="U4",
            is_active=True,
        )
        self.assertEqual(assocs.count(), 2)

    def test_rejection_of_college_parameter_under_university_framework(self):
        """Reject association if framework is UNIVERSITY_2026 but parameter is C1."""
        with self.assertRaises(FrameworkMismatchError):
            EvidenceService.associate_subcriterion(
                evidence_id=self.doc1.id,
                parameter_id="C1",
                subcriterion_id="C1.1",
                actor=self.user,
            )
