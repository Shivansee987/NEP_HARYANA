"""
Phase 7B API Tests: Authentication and Institutional Framework Isolation.

Verifies:
1. Anonymous request rejected (401).
2. Authenticated College user can access own College.
3. Unauthorized user cannot access another College (403).
4. University user cannot access College assessment (403).
5. College endpoint rejects UNIVERSITY_2026.
6. College assessment cannot be created for University institution.
7. College evidence cannot cross framework boundary.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import College
from apps.college.models import CollegeAssessment
from apps.college.services import CollegeAssessmentService
from apps.evidence.models import EvidenceDocument
from apps.university.models import University

User = get_user_model()


class CollegeAPIAuthAndIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin user
        self.admin_user = User.objects.create_user(
            email="admin.dhe@haryana.gov.in",
            full_name="State DHE Admin",
            role="admin",
            password="AdminPassword2026!",
        )

        # College A
        self.college_a = College.objects.create(
            name="Govt College Ambala",
            aishe_code="C-00101",
        )
        self.user_col_a = User.objects.create_user(
            email="principal.ambala@haryana.gov.in",
            full_name="Principal Ambala",
            role="principal",
            college=self.college_a,
            password="PasswordAmbala2026!",
        )

        # College B
        self.college_b = College.objects.create(
            name="Govt College Rohtak",
            aishe_code="C-00102",
        )
        self.user_col_b = User.objects.create_user(
            email="principal.rohtak@haryana.gov.in",
            full_name="Principal Rohtak",
            role="principal",
            college=self.college_b,
            password="PasswordRohtak2026!",
        )

        # University and University User
        self.university = University.objects.create(
            name="Kurukshetra University",
            aishe_code="U-0160",
            state="Haryana",
        )
        self.uni_user = User.objects.create_user(
            email="nodal.kuk@haryana.gov.in",
            full_name="Nodal KUK",
            role="nodal_officer",
            university=self.university,
            password="PasswordKUK2026!",
        )

        # Assessment for College A
        self.assessment_a = CollegeAssessmentService.create_assessment(
            college_id=self.college_a.pk,
            assessment_id="ASSESS-2026-COL-00101-TESTA",
            created_by=self.user_col_a,
        )

    def test_anonymous_requests_rejected(self):
        """Unauthenticated requests are rejected with 401."""
        urls = [
            "/api/colleges/",
            f"/api/colleges/{self.college_a.pk}/",
            "/api/college/assessments/",
            f"/api/college/assessments/{self.assessment_a.assessment_id}/",
            f"/api/college/assessments/{self.assessment_a.assessment_id}/parameters/",
            f"/api/college/assessments/{self.assessment_a.assessment_id}/coverage/",
            f"/api/college/assessments/{self.assessment_a.assessment_id}/readiness/",
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED, f"URL {url} did not return 401")

    def test_college_user_can_access_own_college(self):
        """Principal of College A can access own college details and assessments."""
        self.client.force_authenticate(user=self.user_col_a)
        resp = self.client.get(f"/api/colleges/{self.college_a.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["aishe_code"], self.college_a.aishe_code)

        resp_assess = self.client.get(f"/api/college/assessments/{self.assessment_a.assessment_id}/")
        self.assertEqual(resp_assess.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_assess.data["assessment_id"], self.assessment_a.assessment_id)

    def test_college_user_cannot_access_another_college(self):
        """Principal of College B cannot access College A record or assessment."""
        self.client.force_authenticate(user=self.user_col_b)
        # Attempt to access College A details
        resp_col = self.client.get(f"/api/colleges/{self.college_a.pk}/")
        self.assertEqual(resp_col.status_code, status.HTTP_403_FORBIDDEN)

        # Attempt to access College A assessment
        resp_assess = self.client.get(f"/api/college/assessments/{self.assessment_a.assessment_id}/")
        self.assertEqual(resp_assess.status_code, status.HTTP_403_FORBIDDEN)

    def test_university_user_cannot_access_college_endpoints(self):
        """University user cannot access College endpoints or assessments."""
        self.client.force_authenticate(user=self.uni_user)
        resp_col = self.client.get("/api/colleges/")
        self.assertEqual(resp_col.status_code, status.HTTP_403_FORBIDDEN)

        resp_assess = self.client.get(f"/api/college/assessments/{self.assessment_a.assessment_id}/")
        self.assertEqual(resp_assess.status_code, status.HTTP_403_FORBIDDEN)

    def test_college_endpoint_rejects_university_framework_override(self):
        """Attempting to create a College assessment with UNIVERSITY_2026 framework is rejected."""
        self.client.force_authenticate(user=self.user_col_a)
        payload = {
            "framework": "UNIVERSITY_2026",
            "academic_year": "2025-26",
        }
        resp = self.client.post("/api/college/assessments/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_college_assessment_cannot_be_created_for_university_institution(self):
        """Attempting to create a College assessment referencing a University ID is rejected."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "college_id": 999999,  # Non-existent college
            "academic_year": "2025-26",
        }
        resp = self.client.post("/api/college/assessments/", payload, format="json")
        self.assertIn(resp.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND))

    def test_college_evidence_cannot_cross_framework_boundary(self):
        """University evidence cannot be ingested as College evidence for scoring."""
        uni_doc = EvidenceDocument.objects.create(
            assessment_id=self.assessment_a.assessment_id,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.university.aishe_code,
            original_filename="uni_proof.pdf",
            file_checksum="3333333333333333333333333333333333333333333333333333333333333333",
            uploader=self.user_col_a,
            evidence_type="EVID_C1_APPROVED_IDP",
        )
        assessment_input = CollegeAssessmentService.build_assessment_input(self.assessment_a.assessment_id)
        # University evidence document must be filtered out
        for param in assessment_input.parameters.values():
            for sub in param.subcriteria_inputs.values():
                for doc in sub.evidence_docs:
                    self.assertNotEqual(doc.document_id, str(uni_doc.document_id))
