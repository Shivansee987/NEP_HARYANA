"""
NEP Excellence Awards 2026 - University Nodal Officer role boundaries

The nodal officer prepares, submits and resubmits their own University's assessment. They must not
certify or return it themselves, add evidence once it is locked or to another institution, or see
other institutions' evidence. They may read (never persist) their own live score breakdown.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.evidence.enums import EvidenceLifecycleState
from apps.evidence.models import EvidenceDocument, ReviewerAuthorization
from apps.university.models import University, UniversityAssessment, UniversityAssessmentAuditLog
from apps.university.services import UniversityAssessmentService, UniversityReviewService

User = get_user_model()


class NodalOfficerBoundaryTests(TestCase):
    def setUp(self):
        self.uni_a = University.objects.create(name="Kurukshetra University", aishe_code="U-0170", state="Haryana", is_active=True)
        self.uni_b = University.objects.create(name="Maharshi Dayanand University", aishe_code="U-0171", state="Haryana", is_active=True)
        self.nodal_a = User.objects.create_user(
            email="nodal.a@haryana.gov.in", full_name="Nodal A", role="nodal_officer",
            university=self.uni_a, password="SecurePassword2026!",
        )
        self.uni_admin_a = User.objects.create_user(
            email="uniadmin.a@haryana.gov.in", full_name="Uni Admin A", role="university_admin",
            university=self.uni_a, password="SecurePassword2026!",
        )
        self.reviewer = User.objects.create_user(
            email="reviewer@haryana.gov.in", full_name="Reviewer", role="committee", password="SecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(user=self.reviewer, framework="ALL", is_active=True)

        self.assessment_a = self._create_assessment(self.uni_a, self.nodal_a)
        self.assessment_b = self._create_assessment(self.uni_b, None)
        self.client = APIClient()
        self.client.force_authenticate(self.nodal_a)

    def _create_assessment(self, uni, user):
        assessment = UniversityAssessmentService.create_assessment(university_id=uni.id, academic_year="2025-26", created_by=user)
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id, parameter_code="U1",
            raw_inputs={"U1.1": {"programmes_count": 15}}, activity_date=date(2025, 10, 15),
        )
        return assessment

    def _set_status(self, assessment, value):
        UniversityAssessment.objects.filter(pk=assessment.pk).update(status=value)

    def _status(self, assessment):
        return UniversityAssessment.objects.get(pk=assessment.pk).status

    def _detail_url(self, assessment):
        return f"/api/v1/university/university-assessments/{assessment.assessment_id}/"

    def _upload(self, assessment, institution_id):
        return self.client.post("/api/evidence/", {
            "file": SimpleUploadedFile("u1.pdf", b"%PDF-1.4 approval document", content_type="application/pdf"),
            "assessment_id": assessment.assessment_id,
            "framework": "UNIVERSITY_2026",
            "institution_type": "UNIVERSITY",
            "institution_id": institution_id,
            "evidence_type": "EVID_U1_APPROVAL",
        }, format="multipart")

    # --- status route cannot certify or self-return ---------------------------------------------

    def test_nodal_cannot_certify_via_status_patch(self):
        for start in ("EVALUATED", "CERTIFICATION_PENDING", "FINALIZED"):
            self._set_status(self.assessment_a, start)
            res = self.client.patch(self._detail_url(self.assessment_a), {"status": "CERTIFIED"}, format="json")
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, start)
            self.assertEqual(self._status(self.assessment_a), start)

    def test_reviewer_cannot_certify_via_status_patch(self):
        self._set_status(self.assessment_a, "EVALUATED")
        self.client.force_authenticate(self.reviewer)
        res = self.client.patch(self._detail_url(self.assessment_a), {"status": "CERTIFIED"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self._status(self.assessment_a), "EVALUATED")

    def test_nodal_cannot_self_return_submitted_assessment(self):
        self._set_status(self.assessment_a, "SUBMITTED")
        res = self.client.patch(self._detail_url(self.assessment_a), {"status": "RETURNED"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self._status(self.assessment_a), "SUBMITTED")

    # --- returned assessments can be corrected and resubmitted -----------------------------------

    def test_returned_assessment_can_be_resubmitted(self):
        UniversityAssessmentService.submit_assessment(self.assessment_a.assessment_id, submitting_user=self.nodal_a)
        UniversityReviewService.return_for_correction(
            self.assessment_a.assessment_id, reviewer=self.reviewer,
            reason="U1 programme count does not match the syndicate approval document.",
        )
        self.assertEqual(self._status(self.assessment_a), "RETURNED")

        res = self.client.post(f"{self._detail_url(self.assessment_a)}submit/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        self.assertEqual(self._status(self.assessment_a), "SUBMITTED")
        log = UniversityAssessmentAuditLog.objects.filter(assessment=self.assessment_a, action="SUBMITTED").latest("pk")
        self.assertEqual(log.previous_status, "RETURNED")

    # --- evidence upload ownership & lock -------------------------------------------------------

    def test_upload_to_other_university_assessment_is_denied(self):
        res = self._upload(self.assessment_b, self.uni_b.aishe_code)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(EvidenceDocument.objects.filter(assessment_id=self.assessment_b.assessment_id).exists())

    def test_upload_after_submission_is_denied(self):
        self._set_status(self.assessment_a, "SUBMITTED")
        res = self._upload(self.assessment_a, self.uni_a.aishe_code)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_allowed_when_returned(self):
        self._set_status(self.assessment_a, "RETURNED")
        res = self._upload(self.assessment_a, self.uni_a.aishe_code)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.content)

    def test_upload_is_filed_under_assessment_institution_not_client_value(self):
        res = self._upload(self.assessment_a, "U-SPOOFED")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.content)
        self.assertEqual(EvidenceDocument.objects.get(document_id=res.data["document_id"]).institution_id, self.uni_a.aishe_code)

    # --- evidence list scoping ------------------------------------------------------------------

    def _doc(self, assessment, institution_id):
        return EvidenceDocument.objects.create(
            uploader=self.nodal_a, assessment_id=assessment.assessment_id, framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY", institution_id=institution_id, file_path="evidence/x.pdf",
            original_filename="x.pdf", file_size=10, file_checksum=institution_id.ljust(64, "0")[:64],
            mime_type="application/pdf", status=EvidenceLifecycleState.EVIDENCE_PENDING,
        )

    def test_university_users_list_only_own_evidence(self):
        own = self._doc(self.assessment_a, self.uni_a.aishe_code)
        self._doc(self.assessment_b, self.uni_b.aishe_code)
        for user in (self.nodal_a, self.uni_admin_a):
            self.client.force_authenticate(user)
            res = self.client.get("/api/evidence/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            ids = [row["document_id"] for row in res.data["results"]]
            self.assertEqual(ids, [str(own.document_id)], user.role)

    # --- live score preview ---------------------------------------------------------------------

    def test_nodal_can_read_but_not_persist_own_score(self):
        url = f"{self._detail_url(self.assessment_a)}evaluate/"
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(url, {}, format="json").status_code, status.HTTP_403_FORBIDDEN)
        other = f"{self._detail_url(self.assessment_b)}evaluate/"
        self.assertEqual(self.client.get(other).status_code, status.HTTP_403_FORBIDDEN)

    # --- readiness exposes the submission gate --------------------------------------------------

    def test_readiness_reports_submission_gate(self):
        url = f"{self._detail_url(self.assessment_a)}readiness/"
        data = self.client.get(url).data
        self.assertIn("submission_issues", data)
        self.assertEqual(data["submission_ready"], not data["submission_issues"])

        self._set_status(self.assessment_a, "SUBMITTED")
        self.assertFalse(self.client.get(url).data["submission_ready"])
