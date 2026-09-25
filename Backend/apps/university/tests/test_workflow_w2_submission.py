"""
NEP Excellence Awards 2026 - Phase W2 Assessment Submission Foundation Tests

Verifies the institutional assessment submission lifecycle contract:
- W2.1: University can submit assessment with pending evidence (DRAFT -> SUBMITTED)
- W2.2: College submission path remains coherent and valid
- W2.3: Parameter inputs editable in DRAFT/RETURNED, locked post-submission
- W2.4: Evidence association metadata (pages, section, claim, status) exposed in serializers/API
- W2.5: Modern evidence submission contract functions without legacy dependencies
- W2.6: Submission reaches SUBMITTED without requiring certification/scoring readiness
- W2.7: Isolation from legacy nominations infrastructure
"""
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import College
from apps.college.models import CollegeAssessment
from apps.college.services import CollegeAssessmentService
from apps.evidence.api.serializers import (
    EvidenceAssociationSerializer,
    EvidenceDocumentSerializer,
)
from apps.evidence.enums import (
    EvidenceLifecycleState,
    VerificationDecision,
)
from apps.evidence.models import (
    EvidenceAssociationVerification,
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.evidence.services import EvidenceService
from apps.nominations.models import Nomination
from apps.university.models import (
    University,
    UniversityAssessment,
    UniversityAssessmentAuditLog,
)
from apps.university.services import (
    UniversityAssessmentService,
    UniversityReviewService,
)
from apps.university.validators import (
    EvidenceNotReadyError,
    InvalidStateTransitionError,
    UniversityNotAuthorizedError,
    UniversityValidationError,
)

User = get_user_model()


class WorkflowW2SubmissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Institutions
        self.uni_a = University.objects.create(
            name="Kurukshetra University",
            aishe_code="U-0160",
            state="Haryana",
            is_active=True,
        )
        self.uni_b = University.objects.create(
            name="Maharshi Dayanand University",
            aishe_code="U-0161",
            state="Haryana",
            is_active=True,
        )
        self.college = College.objects.create(
            name="Govt College Karnal",
            aishe_code="C-1001",
        )

        # Users
        self.user_uni_a = User.objects.create_user(
            email="nodal.kuk@haryana.gov.in",
            full_name="KUK Nodal Officer",
            role="nodal_officer",
            university=self.uni_a,
            password="SecurePassword2026!",
        )
        self.user_uni_b = User.objects.create_user(
            email="nodal.mdu@haryana.gov.in",
            full_name="MDU Nodal Officer",
            role="nodal_officer",
            university=self.uni_b,
            password="SecurePassword2026!",
        )
        self.user_college = User.objects.create_user(
            email="principal.karnal@haryana.gov.in",
            full_name="Karnal Principal",
            role="principal",
            college=self.college,
            password="SecurePassword2026!",
        )
        self.admin_user = User.objects.create_superuser(
            email="admin.dhe@haryana.gov.in",
            full_name="State Admin DHE",
            password="SecurePassword2026!",
        )
        self.reviewer_user = User.objects.create_user(
            email="reviewer.screening@haryana.gov.in",
            full_name="Screening Reviewer",
            role="committee",
            password="SecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(
            user=self.reviewer_user,
            framework="UNIVERSITY_2026",
            is_active=True,
        )
        ReviewerAuthorization.objects.create(
            user=self.reviewer_user,
            framework="COLLEGE_2026",
            is_active=True,
        )

    # =========================================================================
    # W2.1 & W2.6: University Submission with Pending Evidence
    # =========================================================================

    def test_w2_a_university_submit_with_pending_evidence_reaches_submitted(self):
        """
        W2.1 & W2.6: University assessment can be submitted while evidence is PENDING.
        Submission transitions DRAFT -> SUBMITTED and does NOT require evidence to be verified.
        """
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={"U1.1": {"programmes_count": 15}},
            activity_date=date(2025, 10, 15),
        )

        # Upload evidence in PENDING state
        doc = EvidenceDocument.objects.create(
            uploader=self.user_uni_a,
            assessment_id=assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.uni_a.aishe_code,
            file_path="evidence/u1_doc.pdf",
            original_filename="u1_doc.pdf",
            file_size=2048,
            file_checksum="a" * 64,
            mime_type="application/pdf",
            status=EvidenceLifecycleState.EVIDENCE_PENDING,
            document_date=date(2025, 10, 15),
            academic_year="2025-26",
        )
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U1",
            subcriterion_id="U1.1",
            actor=self.user_uni_a,
            subcriterion_evidence_type="EVID_U1_APPROVAL",
        )
        self.assertIsNone(assoc.verification_status)

        # Evidence is NOT ready for scoring review/certification
        is_ready, blocking_reasons, _ = UniversityAssessmentService.check_assessment_readiness(
            assessment.assessment_id
        )
        self.assertFalse(is_ready)

        # Submission MUST succeed despite unverified evidence
        submitted = UniversityAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=self.user_uni_a,
        )
        self.assertEqual(submitted.status, "SUBMITTED")
        self.assertIsNotNone(submitted.submitted_at)
        self.assertIsNone(submitted.certified_score)

        # Audit log entry must exist
        audit_log = UniversityAssessmentAuditLog.objects.filter(
            assessment=submitted,
            action="SUBMITTED",
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.previous_status, "DRAFT")
        self.assertEqual(audit_log.new_status, "SUBMITTED")
        self.assertEqual(audit_log.actor, self.user_uni_a)

    def test_w2_c_university_api_submit_endpoint(self):
        """
        POST /api/university-assessments/<id>/submit/ succeeds with pending evidence.
        """
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={"U1.1": {"programmes_count": 12}},
            activity_date=date(2025, 10, 15),
        )

        self.client.force_authenticate(user=self.user_uni_a)
        res = self.client.post(
            f"/api/university-assessments/{assessment.assessment_id}/submit/",
            {},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "SUBMITTED")
        self.assertIsNotNone(res.data["submitted_at"])

    # =========================================================================
    # W2.1: Legitimate Submission Validation Rules
    # =========================================================================

    def test_w2_b_university_cannot_submit_without_parameter_data(self):
        """University cannot submit assessment with empty parameter data."""
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        with self.assertRaises(UniversityValidationError) as ctx:
            UniversityAssessmentService.submit_assessment(
                assessment_id=assessment.assessment_id,
                submitting_user=self.user_uni_a,
            )
        self.assertEqual(ctx.exception.code, "INVALID_PARAMETER_INPUT")

    def test_w2_b2_university_cannot_submit_if_not_draft(self):
        """Only DRAFT assessments can be submitted."""
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={"U1.1": {"programmes_count": 10}},
        )
        # First submission
        UniversityAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=self.user_uni_a,
        )

        # Second submission must fail
        with self.assertRaises(InvalidStateTransitionError):
            UniversityAssessmentService.submit_assessment(
                assessment_id=assessment.assessment_id,
                submitting_user=self.user_uni_a,
            )

    def test_w2_b3_unauthorized_user_cannot_submit(self):
        """User from University B cannot submit assessment belonging to University A."""
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={"U1.1": {"programmes_count": 10}},
        )

        with self.assertRaises(UniversityNotAuthorizedError):
            UniversityAssessmentService.submit_assessment(
                assessment_id=assessment.assessment_id,
                submitting_user=self.user_uni_b,
            )

    # =========================================================================
    # W2.2: College Submission Path Verification
    # =========================================================================

    def test_w2_d_college_submission_path_remains_valid(self):
        """College submission functions correctly under the same principles."""
        assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college.id,
            academic_year="2025-26",
            created_by=self.user_college,
        )
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"achieved_targets_2024_25": 85, "fixed_targets_2024_25": 100}},
        )

        submitted = CollegeAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=self.user_college,
        )
        self.assertEqual(submitted.status, "SUBMITTED")
        self.assertIsNotNone(submitted.submitted_at)

    # =========================================================================
    # W2.3: Parameter Input Save and Lock Contract
    # =========================================================================

    def test_w2_e_parameter_inputs_editable_in_draft(self):
        """Parameter input can be saved, updated, and retrieved while in DRAFT."""
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )

        # Save initial input
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={"U1.1": {"programmes_count": 8}},
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.parameter_data["U1"]["raw_inputs"]["U1.1"]["programmes_count"], 8)

        # Update input
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={"U1.1": {"programmes_count": 14}},
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.parameter_data["U1"]["raw_inputs"]["U1.1"]["programmes_count"], 14)

        # Retrieve via API
        self.client.force_authenticate(user=self.user_uni_a)
        res = self.client.get(
            f"/api/university-assessments/{assessment.assessment_id}/parameters/U1/"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["submitted_input"]["raw_inputs"]["U1.1"]["programmes_count"], 14)

    def test_w2_f_parameter_inputs_locked_after_submission(self):
        """Parameter inputs cannot be modified after submission."""
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={"U1.1": {"programmes_count": 10}},
        )
        UniversityAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=self.user_uni_a,
        )

        # Modification via service must raise InvalidStateTransitionError
        with self.assertRaises(InvalidStateTransitionError):
            UniversityAssessmentService.update_parameter_inputs(
                assessment_id=assessment.assessment_id,
                parameter_code="U1",
                raw_inputs={"U1.1": {"programmes_count": 99}},
            )

        # Modification via API must return HTTP 409 Conflict
        self.client.force_authenticate(user=self.user_uni_a)
        res = self.client.put(
            f"/api/university-assessments/{assessment.assessment_id}/parameters/U1/",
            {"raw_inputs": {"programmes_count": 99}},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    # =========================================================================
    # W2.4: Evidence Association Serialization
    # =========================================================================

    def test_w2_g_evidence_association_metadata_serialization(self):
        """
        EvidenceAssociationSerializer exposes:
        - page_start, page_end
        - section_identifier
        - claim_description
        - parameter_id, subcriterion_id, subcriterion_evidence_type
        - verification_status
        without leaking private filesystem paths.
        """
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        doc = EvidenceDocument.objects.create(
            uploader=self.user_uni_a,
            assessment_id=assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.uni_a.aishe_code,
            file_path="/var/secret/storage/internal_path/syndicate_u1.pdf",
            original_filename="syndicate_u1.pdf",
            file_size=4096,
            file_checksum="b" * 64,
            mime_type="application/pdf",
            status=EvidenceLifecycleState.EVIDENCE_PENDING,
            document_date=date(2025, 10, 15),
            academic_year="2025-26",
        )

        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U1",
            subcriterion_id="U1.1",
            actor=self.user_uni_a,
            subcriterion_evidence_type="EVID_U1_APPROVAL",
            page_start=12,
            page_end=15,
            section_identifier="Annexure-III",
            claim_description="Syndicate minutes approving 15 NEP multidisciplinary courses.",
        )

        # Serialize association directly
        serializer = EvidenceAssociationSerializer(assoc)
        data = serializer.data

        self.assertEqual(data["parameter_id"], "U1")
        self.assertEqual(data["subcriterion_id"], "U1.1")
        self.assertEqual(data["subcriterion_evidence_type"], "EVID_U1_APPROVAL")
        self.assertEqual(data["page_start"], 12)
        self.assertEqual(data["page_end"], 15)
        self.assertEqual(data["section_identifier"], "Annexure-III")
        self.assertEqual(data["claim_description"], "Syndicate minutes approving 15 NEP multidisciplinary courses.")
        self.assertIsNone(data["verification_status"])

        # Serialize document metadata
        doc_serializer = EvidenceDocumentSerializer(doc)
        doc_data = doc_serializer.data
        self.assertEqual(len(doc_data["associations"]), 1)
        self.assertEqual(doc_data["associations"][0]["page_start"], 12)
        self.assertEqual(doc_data["associations"][0]["section_identifier"], "Annexure-III")

        # Security check: no private filesystem path is exposed
        self.assertNotIn("file_path", doc_data)
        self.assertNotIn("/var/secret", str(doc_data))

        # When association is verified, verification_status reflects VERIFIED
        EvidenceAssociationVerification.objects.create(
            association=assoc,
            verifier=self.reviewer_user,
            decision=VerificationDecision.VERIFIED,
            reason="Annexure-III confirmed authentic.",
        )
        assoc.refresh_from_db()
        data_verified = EvidenceAssociationSerializer(assoc).data
        self.assertEqual(data_verified["verification_status"], "VERIFIED")

    def test_w2_g2_associate_api_endpoint_accepts_and_returns_metadata(self):
        """
        POST /api/evidence/<pk>/associate/ accepts and returns complete association metadata.
        """
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        doc = EvidenceDocument.objects.create(
            uploader=self.user_uni_a,
            assessment_id=assessment.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.uni_a.aishe_code,
            file_path="evidence/u7_doc.pdf",
            original_filename="u7_doc.pdf",
            file_size=2048,
            file_checksum="c" * 64,
            mime_type="application/pdf",
            status=EvidenceLifecycleState.EVIDENCE_PENDING,
            document_date=date(2025, 10, 15),
            academic_year="2025-26",
        )

        self.client.force_authenticate(user=self.user_uni_a)
        res = self.client.post(
            f"/api/evidence/{doc.pk}/associate/",
            {
                "parameter_id": "U7",
                "subcriterion_id": "U7.1",
                "subcriterion_evidence_type": "EVID_U7_APPOINTMENT",
                "page_start": 3,
                "page_end": 5,
                "section_identifier": "Section-B",
                "claim_description": "Appointment letter of PoP faculty.",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        assocs = res.data.get("associations", [])
        self.assertEqual(len(assocs), 1)
        assoc_data = assocs[0]
        self.assertEqual(assoc_data["parameter_id"], "U7")
        self.assertEqual(assoc_data["subcriterion_id"], "U7.1")
        self.assertEqual(assoc_data["subcriterion_evidence_type"], "EVID_U7_APPOINTMENT")
        self.assertEqual(assoc_data["page_start"], 3)
        self.assertEqual(assoc_data["page_end"], 5)
        self.assertEqual(assoc_data["section_identifier"], "Section-B")
        self.assertEqual(assoc_data["claim_description"], "Appointment letter of PoP faculty.")

    # =========================================================================
    # W2.7: Isolation from Legacy Nominations
    # =========================================================================

    def test_w2_i_modern_submission_does_not_touch_legacy_nominations(self):
        """
        Creating, updating, and submitting modern University assessments creates
        zero records in the legacy Nomination model.
        """
        initial_nomination_count = Nomination.objects.count()

        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={"U1.1": {"programmes_count": 10}},
        )
        UniversityAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=self.user_uni_a,
        )

        final_nomination_count = Nomination.objects.count()
        self.assertEqual(initial_nomination_count, final_nomination_count)

    # =========================================================================
    # Preservation of Review/Certification Gates
    # =========================================================================

    def test_w2_j_scoring_readiness_preserved_for_review_completion(self):
        """
        check_assessment_readiness remains active and blocks review completion
        when evidence is unverified.
        """
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={"U1.1": {"programmes_count": 10}},
        )
        UniversityAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=self.user_uni_a,
        )

        # Transition to UNDER_REVIEW
        UniversityReviewService.start_review(
            assessment_id=assessment.assessment_id,
            reviewer=self.reviewer_user,
        )

        # Attempting to complete review with unverified evidence must raise EvidenceNotReadyError
        with self.assertRaises(EvidenceNotReadyError):
            UniversityReviewService.complete_review(
                assessment_id=assessment.assessment_id,
                reviewer=self.reviewer_user,
            )
