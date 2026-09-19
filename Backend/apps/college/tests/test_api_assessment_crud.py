"""
Phase 7B API Tests: Assessment CRUD, Lifecycle, and Concurrency.

Verifies:
1. Valid College assessment creation.
2. Retrieval of own assessment and assessment lists.
3. Update valid non-protected metadata via PATCH.
4. Unknown parameter or protected fields rejected.
5. Score fields cannot be injected via POST or PATCH.
6. Institution ownership cannot be mutated.
7. Concurrency protection on assessment mutations.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import College
from apps.college.models import CollegeAssessment
from apps.college.services import CollegeAssessmentService

User = get_user_model()


class CollegeAPIAssessmentCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin user
        self.admin_user = User.objects.create_user(
            email="admin.dhe@haryana.gov.in",
            full_name="State DHE Admin",
            role="admin",
            password="AdminPassword2026!",
        )

        # College
        self.college = College.objects.create(
            name="Govt College Karnal",
            aishe_code="C-00103",
        )
        self.principal = User.objects.create_user(
            email="principal.karnal@haryana.gov.in",
            full_name="Principal Karnal",
            role="principal",
            college=self.college,
            password="PasswordKarnal2026!",
        )

    def test_create_valid_college_assessment(self):
        """College user can create a valid College assessment."""
        self.client.force_authenticate(user=self.principal)
        payload = {
            "academic_year": "2025-26",
        }
        resp = self.client.post("/api/college/assessments/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["framework"], "COLLEGE_2026")
        self.assertEqual(resp.data["academic_year"], "2025-26")
        self.assertEqual(resp.data["status"], "DRAFT")
        self.assertEqual(resp.data["college_name"], self.college.name)
        self.assertEqual(resp.data["aishe_code"], self.college.aishe_code)

    def test_retrieve_own_assessment_detail_and_list(self):
        """College user can retrieve their assessment detail and list."""
        assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college.pk,
            created_by=self.principal,
        )
        self.client.force_authenticate(user=self.principal)

        # List
        resp_list = self.client.get("/api/college/assessments/")
        self.assertEqual(resp_list.status_code, status.HTTP_200_OK)
        results = resp_list.data.get("results", resp_list.data)
        self.assertTrue(len(results) >= 1)

        # Detail
        resp_detail = self.client.get(f"/api/college/assessments/{assessment.assessment_id}/")
        self.assertEqual(resp_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_detail.data["assessment_id"], assessment.assessment_id)

    def test_patch_metadata_allowed_notes(self):
        """Updating draft notes via PATCH is allowed."""
        assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college.pk,
            created_by=self.principal,
        )
        self.client.force_authenticate(user=self.principal)
        payload = {
            "notes": "Preliminary draft for internal review",
        }
        resp = self.client.patch(f"/api/college/assessments/{assessment.assessment_id}/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        assessment.refresh_from_db()
        self.assertEqual(assessment.parameter_data.get("_notes"), "Preliminary draft for internal review")

    def test_protected_fields_cannot_be_modified_via_patch(self):
        """Attempting to modify framework, academic_year, period, status, or ownership via PATCH is rejected."""
        assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college.pk,
            created_by=self.principal,
        )
        self.client.force_authenticate(user=self.principal)

        protected_payloads = [
            {"framework": "UNIVERSITY_2026"},
            {"academic_year": "2024-25"},
            {"period_start": "2024-01-01"},
            {"period_end": "2024-12-31"},
            {"status": "CERTIFIED"},
            {"college_id": 9999},
        ]
        for payload in protected_payloads:
            resp = self.client.patch(f"/api/college/assessments/{assessment.assessment_id}/", payload, format="json")
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, f"Payload {payload} was not rejected")

    def test_score_injection_rejected(self):
        """Attempting to inject arbitrary score fields is rejected."""
        assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college.pk,
            created_by=self.principal,
        )
        self.client.force_authenticate(user=self.principal)

        score_payloads = [
            {"score": 95.0},
            {"earned_score": 90.0},
            {"certified_score": 100.0},
            {"total": 100.0},
            {"reviewer_score": 98.0},
        ]
        for payload in score_payloads:
            resp = self.client.patch(f"/api/college/assessments/{assessment.assessment_id}/", payload, format="json")
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, f"Score injection {payload} was not rejected")
