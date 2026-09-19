"""
NEP Excellence Awards 2026 - Phase 5E Evidence API Integration & Security Test Suite
Exercises all REST endpoints via real HTTP requests (DRF APITestCase).
Tests authentication, isolation, upload validation, lifecycle, decisions, coverage, readiness, and E2E flow.
"""
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import College, User
from apps.evidence.enums import (
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
)
from apps.evidence.models import (
    EvidenceAuditLog,
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    EvidenceVerification,
    ReviewerAuthorization,
)
from apps.evidence.services import EvidenceService
from apps.scoring.enums import FrameworkType


class EvidenceAPITestBase(APITestCase):
    """
    Base test fixture providing authentic users, institutions, and file payloads.
    """
    def setUp(self):
        super().setUp()
        self.college_a = College.objects.create(name="Govt College Ambala", aishe_code="C-5001")
        self.college_b = College.objects.create(name="Govt College Bhiwani", aishe_code="C-5002")

        # Users
        self.principal_a = User.objects.create_user(
            email="principal.a@ambala.edu",
            full_name="Principal Ambala",
            role="principal",
            college=self.college_a,
            password="securepassword123"
        )
        self.principal_b = User.objects.create_user(
            email="principal.b@bhiwani.edu",
            full_name="Principal Bhiwani",
            role="principal",
            college=self.college_b,
            password="securepassword123"
        )
        self.committee_reviewer = User.objects.create_user(
            email="reviewer.dhe@haryana.gov.in",
            full_name="Committee Reviewer",
            role="committee",
            password="securepassword123"
        )
        self.unauthorized_reviewer = User.objects.create_user(
            email="other.reviewer@dhe.gov.in",
            full_name="Unauthorized Reviewer",
            role="committee",
            password="securepassword123"
        )
        self.admin_user = User.objects.create_user(
            email="admin@dhe.haryana.gov.in",
            full_name="State Administrator",
            role="state_admin",
            password="securepassword123"
        )

        # Authorize committee_reviewer for COLLEGE_2026
        EvidenceService.authorize_reviewer(
            self.committee_reviewer,
            framework="COLLEGE_2026",
            granted_by=self.admin_user
        )

        # Standard authentic test file payloads
        self.valid_pdf_bytes = b"%PDF-1.4\n%Mock Valid PDF Header and stream content for NEP 2026\n%%EOF"

    def create_sample_doc(
        self,
        uploader=None,
        college=None,
        assessment_id="ASSESS-2026-COLLEGE-01",
        framework="COLLEGE_2026",
        status_val=EvidenceLifecycleState.EVIDENCE_PRESENT,
        document_date=date(2025, 9, 15),
    ) -> EvidenceDocument:
        uploader = uploader or self.principal_a
        college = college or self.college_a
        checksum = EvidenceService.calculate_checksum(self.valid_pdf_bytes)

        return EvidenceDocument.objects.create(
            assessment_id=assessment_id,
            framework=framework,
            institution_type="COLLEGE",
            institution_id=college.aishe_code,
            original_filename="proof.pdf",
            file_path="vault/proof.pdf",
            mime_type="application/pdf",
            file_size=len(self.valid_pdf_bytes),
            file_checksum=checksum,
            uploader=uploader,
            evidence_type="EVID_CERTIFICATE",
            document_date=document_date,
            academic_year="2025-26",
            status=status_val,
            is_active=True,
        )


class TestAuthenticationSecurity(EvidenceAPITestBase):
    """
    Category A: Unauthenticated requests must be denied.
    """
    def test_unauthenticated_list_denied(self):
        url = reverse('evidence-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_upload_denied(self):
        url = reverse('evidence-list-create')
        uploaded = SimpleUploadedFile("proof.pdf", self.valid_pdf_bytes, content_type="application/pdf")
        response = self.client.post(url, {"file": uploaded, "assessment_id": "A-1", "framework": "COLLEGE_2026"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestInstitutionIsolation(EvidenceAPITestBase):
    """
    Category B: Institution Isolation. College A cannot view or mutate College B evidence.
    """
    def test_principal_cannot_view_other_college_evidence(self):
        doc_b = self.create_sample_doc(uploader=self.principal_b, college=self.college_b)
        self.client.force_authenticate(user=self.principal_a)

        url = reverse('evidence-detail', kwargs={'pk': doc_b.pk})
        response = self.client.get(url)
        # Principal A must be forbidden from accessing College B's document
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_principal_cannot_submit_other_college_evidence(self):
        doc_b = self.create_sample_doc(uploader=self.principal_b, college=self.college_b)
        self.client.force_authenticate(user=self.principal_a)

        url = reverse('evidence-submit', kwargs={'pk': doc_b.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_principal_list_is_scoped_to_own_college(self):
        doc_a = self.create_sample_doc(uploader=self.principal_a, college=self.college_a)
        doc_b = self.create_sample_doc(uploader=self.principal_b, college=self.college_b)

        self.client.force_authenticate(user=self.principal_a)
        url = reverse('evidence-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Handle paginated or unpaginated response
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        doc_ids = [item['document_id'] for item in results]
        self.assertIn(str(doc_a.document_id), doc_ids)
        self.assertNotIn(str(doc_b.document_id), doc_ids)


class TestReviewerAuthorizationAndQueue(EvidenceAPITestBase):
    """
    Category D & E: Reviewer queue access, scoping, and conflict-of-interest prevention.
    """
    def test_authorized_reviewer_can_access_queue(self):
        # Create pending evidence for College A
        doc = self.create_sample_doc(uploader=self.principal_a, status_val=EvidenceLifecycleState.EVIDENCE_PENDING)

        self.client.force_authenticate(user=self.committee_reviewer)
        url = reverse('evidence-review-queue')
        response = self.client.get(url, {'framework': 'COLLEGE_2026'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        queue_ids = [item['document_id'] for item in results]
        self.assertIn(str(doc.document_id), queue_ids)

    def test_institutional_user_cannot_access_review_queue(self):
        self.client.force_authenticate(user=self.principal_a)
        url = reverse('evidence-review-queue')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reviewer_conflict_of_interest_own_college_excluded(self):
        # Affiliate committee_reviewer with College A
        self.committee_reviewer.college = self.college_a
        self.committee_reviewer.save()

        # Evidence belongs to College A
        doc = self.create_sample_doc(uploader=self.principal_a, status_val=EvidenceLifecycleState.EVIDENCE_PENDING)

        self.client.force_authenticate(user=self.committee_reviewer)
        url = reverse('evidence-review-queue')
        response = self.client.get(url, {'framework': 'COLLEGE_2026'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        queue_ids = [item['document_id'] for item in results]
        # Must be automatically excluded due to institutional conflict!
        self.assertNotIn(str(doc.document_id), queue_ids)

    def test_uploader_cannot_self_verify_own_evidence(self):
        # If a reviewer uploaded an evidence document, they cannot verify it
        doc = self.create_sample_doc(
            uploader=self.committee_reviewer,
            college=self.college_a,
            status_val=EvidenceLifecycleState.EVIDENCE_PENDING
        )

        self.client.force_authenticate(user=self.committee_reviewer)
        url = reverse('evidence-verify', kwargs={'pk': doc.pk})
        response = self.client.post(url, {"reason": "Self verification attempt"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestUploadPipelineAPI(EvidenceAPITestBase):
    """
    Category F: Upload endpoint integration with Phase 5B pipeline.
    """
    def test_valid_upload_returns_201_created(self):
        self.client.force_authenticate(user=self.principal_a)
        url = reverse('evidence-list-create')
        uploaded = SimpleUploadedFile("official_accreditation.pdf", self.valid_pdf_bytes, content_type="application/pdf")

        data = {
            "file": uploaded,
            "assessment_id": "ASSESS-2026-UPLOAD-01",
            "framework": "COLLEGE_2026",
            "institution_id": "C-5001",
            "evidence_type": "EVID_CERTIFICATE",
            "document_date": "2025-09-15",
            "parameter_id": "C1",
            "subcriterion_id": "C1.1",
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("document_id", response.data)
        self.assertEqual(response.data["status"], EvidenceLifecycleState.EVIDENCE_PRESENT)
        self.assertNotIn("file_path", response.data)  # Internal storage paths must not leak!

    def test_empty_file_upload_rejected(self):
        self.client.force_authenticate(user=self.principal_a)
        url = reverse('evidence-list-create')
        empty_file = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")

        data = {
            "file": empty_file,
            "assessment_id": "ASSESS-2026-UPLOAD-02",
            "framework": "COLLEGE_2026",
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_path_traversal_filename_rejected(self):
        self.client.force_authenticate(user=self.principal_a)
        url = reverse('evidence-list-create')
        traversal_file = SimpleUploadedFile("passwd.pdf", self.valid_pdf_bytes, content_type="application/pdf")

        data = {
            "file": traversal_file,
            "filename": "../../etc/passwd.pdf",
            "assessment_id": "ASSESS-2026-UPLOAD-03",
            "framework": "COLLEGE_2026",
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestLifecycleAndAssociationAPI(EvidenceAPITestBase):
    """
    Category G: Lifecycle transitions and subcriterion associations.
    """
    def test_submit_transitions_to_pending(self):
        doc = self.create_sample_doc(uploader=self.principal_a, status_val=EvidenceLifecycleState.EVIDENCE_PRESENT)
        self.client.force_authenticate(user=self.principal_a)

        url = reverse('evidence-submit', kwargs={'pk': doc.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], EvidenceLifecycleState.EVIDENCE_PENDING)

    def test_cannot_directly_modify_lifecycle_state_via_put_or_patch(self):
        doc = self.create_sample_doc(uploader=self.principal_a, status_val=EvidenceLifecycleState.EVIDENCE_PRESENT)
        self.client.force_authenticate(user=self.principal_a)

        url = reverse('evidence-detail', kwargs={'pk': doc.pk})
        # Attempting direct state manipulation should fail or be ignored
        response = self.client.patch(url, {"status": "EVIDENCE_VERIFIED"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_associate_subcriterion_via_api(self):
        doc = self.create_sample_doc(uploader=self.principal_a)
        self.client.force_authenticate(user=self.principal_a)

        url = reverse('evidence-associate', kwargs={'pk': doc.pk})
        data = {
            "parameter_id": "C1",
            "subcriterion_id": "C1.1",
            "academic_year": "2025-26"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["associations"]), 1)
        self.assertEqual(response.data["associations"][0]["subcriterion_id"], "C1.1")


class TestVerificationAndRejectionAPI(EvidenceAPITestBase):
    """
    Category H, I, J: Verify, Reject, Concurrency, and Hash/Version binding.
    """
    def test_verify_evidence_success(self):
        doc = self.create_sample_doc(status_val=EvidenceLifecycleState.EVIDENCE_PENDING)
        self.client.force_authenticate(user=self.committee_reviewer)

        url = reverse('evidence-verify', kwargs={'pk': doc.pk})
        data = {
            "reason": "Authentic accreditation",
            "expected_checksum": doc.file_checksum,
            "expected_version": 1
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["decision"], VerificationDecision.VERIFIED)
        self.assertEqual(response.data["resulting_state"], EvidenceLifecycleState.EVIDENCE_VERIFIED)

    def test_verify_hash_mismatch_fails(self):
        doc = self.create_sample_doc(status_val=EvidenceLifecycleState.EVIDENCE_PENDING)
        self.client.force_authenticate(user=self.committee_reviewer)

        url = reverse('evidence-verify', kwargs={'pk': doc.pk})
        data = {
            "reason": "Check",
            "expected_checksum": "bad_checksum_hash_value"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_evidence_requires_mandatory_reason(self):
        doc = self.create_sample_doc(status_val=EvidenceLifecycleState.EVIDENCE_PENDING)
        self.client.force_authenticate(user=self.committee_reviewer)

        url = reverse('evidence-reject', kwargs={'pk': doc.pk})
        response = self.client.post(url, {"reason": ""}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_evidence_success(self):
        doc = self.create_sample_doc(status_val=EvidenceLifecycleState.EVIDENCE_PENDING)
        self.client.force_authenticate(user=self.committee_reviewer)

        url = reverse('evidence-reject', kwargs={'pk': doc.pk})
        data = {
            "reason": "Document date outside assessment period",
            "rejection_code": RejectionReasonCode.OUT_OF_PERIOD
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["decision"], VerificationDecision.REJECTED)
        self.assertEqual(response.data["resulting_state"], EvidenceLifecycleState.EVIDENCE_REJECTED)

    def test_concurrency_double_decision_conflict_returns_409(self):
        doc = self.create_sample_doc(status_val=EvidenceLifecycleState.EVIDENCE_PENDING)
        self.client.force_authenticate(user=self.committee_reviewer)

        url_verify = reverse('evidence-verify', kwargs={'pk': doc.pk})
        # Decision 1
        resp1 = self.client.post(url_verify, {"reason": "First decision"})
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)

        # Decision 2 on already decided document must return 409 Conflict
        url_reject = reverse('evidence-reject', kwargs={'pk': doc.pk})
        resp2 = self.client.post(url_reject, {"reason": "Conflicting decision"})
        self.assertEqual(resp2.status_code, status.HTTP_409_CONFLICT)


class TestCoverageAndReadinessAPI(EvidenceAPITestBase):
    """
    Category K: Coverage and Readiness endpoints.
    """
    def test_coverage_endpoint_returns_structured_report(self):
        doc = self.create_sample_doc(status_val=EvidenceLifecycleState.EVIDENCE_VERIFIED)
        EvidenceSubcriterionAssociation.objects.create(
            evidence=doc,
            parameter_id="C1",
            subcriterion_id="C1.1",
            associated_by=self.principal_a
        )

        self.client.force_authenticate(user=self.principal_a)
        url = reverse('evidence-coverage')
        response = self.client.get(url, {
            'assessment_id': doc.assessment_id,
            'framework': 'COLLEGE_2026',
            'institution_id': self.college_a.aishe_code,
            'subcriterion_codes': 'C1.1'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("parameters", response.data)
        self.assertIn("summary", response.data)
        self.assertIn("assessment_period", response.data)

    def test_readiness_endpoint_returns_boolean_and_summary(self):
        doc = self.create_sample_doc(status_val=EvidenceLifecycleState.EVIDENCE_VERIFIED)
        EvidenceSubcriterionAssociation.objects.create(
            evidence=doc,
            parameter_id="C1",
            subcriterion_id="C1.1",
            associated_by=self.principal_a
        )

        self.client.force_authenticate(user=self.principal_a)
        url = reverse('evidence-readiness')
        response = self.client.get(url, {
            'assessment_id': doc.assessment_id,
            'framework': 'COLLEGE_2026',
            'institution_id': self.college_a.aishe_code,
            'subcriterion_codes': 'C1.1'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_ready_for_scoring"])
        self.assertEqual(len(response.data["blocking_reasons"]), 0)


class TestEndToEndAPIFlow(EvidenceAPITestBase):
    """
    Category L: Full lifecycle end-to-end API test.
    upload -> associate -> submit -> review-queue -> assign -> verify -> history -> coverage -> readiness.
    """
    def test_complete_end_to_end_evidence_workflow(self):
        # 1. Upload evidence document as Principal
        self.client.force_authenticate(user=self.principal_a)
        upload_url = reverse('evidence-list-create')
        uploaded = SimpleUploadedFile("e2e_naac.pdf", self.valid_pdf_bytes, content_type="application/pdf")

        upload_data = {
            "file": uploaded,
            "assessment_id": "ASSESS-E2E-001",
            "framework": "COLLEGE_2026",
            "institution_id": self.college_a.aishe_code,
            "evidence_type": "EVID_CERTIFICATE",
            "document_date": "2025-09-20",
        }
        resp_upload = self.client.post(upload_url, upload_data, format='multipart')
        self.assertEqual(resp_upload.status_code, status.HTTP_201_CREATED)
        doc_id = resp_upload.data["document_id"]

        # 2. Associate evidence with C1 / C1.1
        assoc_url = reverse('evidence-associate', kwargs={'pk': doc_id})
        resp_assoc = self.client.post(assoc_url, {
            "parameter_id": "C1",
            "subcriterion_id": "C1.1",
            "academic_year": "2025-26"
        }, format='json')
        self.assertEqual(resp_assoc.status_code, status.HTTP_200_OK)

        # 3. Submit evidence for review
        submit_url = reverse('evidence-submit', kwargs={'pk': doc_id})
        resp_submit = self.client.post(submit_url)
        self.assertEqual(resp_submit.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_submit.data["status"], EvidenceLifecycleState.EVIDENCE_PENDING)

        # 4. State Admin assigns reviewer
        self.client.force_authenticate(user=self.admin_user)
        assign_url = reverse('evidence-assign', kwargs={'pk': doc_id})
        resp_assign = self.client.post(assign_url, {
            "reviewer_id": self.committee_reviewer.email,
            "notes": "E2E review test"
        }, format='json')
        self.assertEqual(resp_assign.status_code, status.HTTP_200_OK)

        # 5. Reviewer inspects queue
        self.client.force_authenticate(user=self.committee_reviewer)
        queue_url = reverse('evidence-review-queue')
        resp_queue = self.client.get(queue_url, {'framework': 'COLLEGE_2026'})
        self.assertEqual(resp_queue.status_code, status.HTTP_200_OK)
        queue_items = resp_queue.data.get('results', resp_queue.data) if isinstance(resp_queue.data, dict) else resp_queue.data
        self.assertIn(doc_id, [item['document_id'] for item in queue_items])

        # 6. Reviewer verifies evidence with checksum & version binding
        verify_url = reverse('evidence-verify', kwargs={'pk': doc_id})
        resp_verify = self.client.post(verify_url, {
            "reason": "E2E verification approved",
            "expected_checksum": resp_upload.data["file_checksum"],
            "expected_version": 1
        }, format='json')
        self.assertEqual(resp_verify.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_verify.data["resulting_state"], EvidenceLifecycleState.EVIDENCE_VERIFIED)

        # 7. Check immutable verification history
        history_url = reverse('evidence-history', kwargs={'pk': doc_id})
        resp_history = self.client.get(history_url)
        self.assertEqual(resp_history.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_history.data), 1)
        self.assertEqual(resp_history.data[0]["decision"], VerificationDecision.VERIFIED)

        # 8. Check coverage report via API
        self.client.force_authenticate(user=self.principal_a)
        coverage_url = reverse('evidence-coverage')
        resp_cov = self.client.get(coverage_url, {
            'assessment_id': 'ASSESS-E2E-001',
            'framework': 'COLLEGE_2026',
            'institution_id': self.college_a.aishe_code,
            'subcriterion_codes': 'C1.1'
        })
        self.assertEqual(resp_cov.status_code, status.HTTP_200_OK)
        sub_cov = resp_cov.data["parameters"][0]["subcriteria"][0]
        self.assertEqual(sub_cov["coverage_state"], "EVIDENCE_VERIFIED")

        # 9. Check readiness via API
        readiness_url = reverse('evidence-readiness')
        resp_ready = self.client.get(readiness_url, {
            'assessment_id': 'ASSESS-E2E-001',
            'framework': 'COLLEGE_2026',
            'institution_id': self.college_a.aishe_code,
            'subcriterion_codes': 'C1.1'
        })
        self.assertEqual(resp_ready.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_ready.data["is_ready_for_scoring"])
        self.assertEqual(len(resp_ready.data["blocking_reasons"]), 0)
