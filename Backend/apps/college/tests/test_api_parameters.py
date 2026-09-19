"""
Phase 7B API Tests: Parameter Endpoints (C1–C22) and Domain Validation.

Verifies:
1. C1–C22 exposed from authoritative registry.
2. Maximum marks match frozen definitions (sum = 100.0).
3. Parameter input update via PUT/PATCH.
4. Unknown parameter rejected.
5. Unknown subcriterion rejected.
6. Percentage and count boundaries enforced.
7. Temporal assessment period validation enforced.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import College
from apps.college.registry import COLLEGE_PARAMETER_CODES, get_college_parameters
from apps.college.services import CollegeAssessmentService

User = get_user_model()


class CollegeAPIParametersTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.college = College.objects.create(
            name="Govt College Kurukshetra",
            aishe_code="C-00104",
        )
        self.principal = User.objects.create_user(
            email="principal.gckuk@haryana.gov.in",
            full_name="Principal Kurukshetra",
            role="principal",
            college=self.college,
            password="PasswordKurukshetra2026!",
        )

        self.assessment = CollegeAssessmentService.create_assessment(
            college_id=self.college.pk,
            created_by=self.principal,
        )

    def test_list_all_parameters_exposed_from_registry(self):
        """GET /parameters/ exposes exactly C1 through C22 with correct max marks summing to 100.0."""
        self.client.force_authenticate(user=self.principal)
        resp = self.client.get(f"/api/college/assessments/{self.assessment.assessment_id}/parameters/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        param_codes = [p["parameter_code"] for p in resp.data]
        self.assertEqual(len(param_codes), 22)
        for expected in COLLEGE_PARAMETER_CODES:
            self.assertIn(expected, param_codes)

        total_max_marks = sum(p["max_marks"] for p in resp.data)
        self.assertEqual(total_max_marks, 100.0)

    def test_get_parameter_detail_metadata(self):
        """GET /parameters/{code}/ returns parameter metadata and current submitted inputs."""
        self.client.force_authenticate(user=self.principal)
        resp = self.client.get(f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C1/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["parameter_code"], "C1")
        self.assertEqual(resp.data["max_marks"], 6.0)
        self.assertIn("C1.1", resp.data["subcriteria"])

    def test_update_valid_parameter_input(self):
        """PUT /parameters/{code}/ saves valid parameter input."""
        self.client.force_authenticate(user=self.principal)
        payload = {
            "raw_inputs": {
                "C1.1": {"achieved_targets_2024_25": 92, "fixed_targets_2024_25": 100}
            }
        }
        resp = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C1/",
            payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "SAVED")

        # Verify saved in DB
        self.assessment.refresh_from_db()
        self.assertIn("C1", self.assessment.parameter_data)

    def test_unknown_parameter_rejected(self):
        """Requesting or updating an unknown parameter is rejected with 400."""
        self.client.force_authenticate(user=self.principal)
        resp = self.client.get(f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C99/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        payload = {"raw_inputs": {"C99.1": 10}}
        resp_put = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C99/",
            payload,
            format="json",
        )
        self.assertEqual(resp_put.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_subcriterion_rejected(self):
        """Supplying an unknown subcriterion for a parameter is rejected."""
        self.client.force_authenticate(user=self.principal)
        payload = {
            "raw_inputs": {
                "C1.99": {"value": 50}
            }
        }
        resp = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C1/",
            payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_percentage_boundary_validation(self):
        """Percentage values < 0 or > 100 are rejected."""
        self.client.force_authenticate(user=self.principal)
        payload_invalid = {
            "raw_inputs": {
                "C1.1": {"percentage_achieved": 150.0}
            }
        }
        resp = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C1/",
            payload_invalid,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_count_rejected(self):
        """Negative count values are rejected."""
        self.client.force_authenticate(user=self.principal)
        payload_invalid = {
            "raw_inputs": {
                "C10.1": {"active_mous_count": -3}
            }
        }
        resp = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C10/",
            payload_invalid,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_temporal_activity_date_validation(self):
        """Activity date outside the statutory assessment window is rejected."""
        self.client.force_authenticate(user=self.principal)
        payload_outside = {
            "raw_inputs": {
                "C2.1": {"students_completed": 85, "eligible_students": 100}
            },
            "activity_date": "2024-01-15",  # Outside 2025-07-01 to 2026-06-30
        }
        resp = self.client.put(
            f"/api/college/assessments/{self.assessment.assessment_id}/parameters/C2/",
            payload_outside,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
