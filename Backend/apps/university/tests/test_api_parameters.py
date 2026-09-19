"""
Category E & L Tests: Parameter Input API, Authoritative Registry Reads, and Legacy Isolation.

Verifies:
- Category E:
  - Valid U1–U20 input accepted.
  - Invalid parameter rejected (e.g. U99, XYZ).
  - Invalid subcriterion rejected (e.g. U1.99).
  - Invalid percentage rejected (< 0.0 or > 100.0).
  - Invalid count rejected (negative, fractional).
  - Invalid temporal activity date rejected for period-sensitive parameter.
  - Protected score fields rejected.
  - Parameter GET returns authoritative metadata from registry with submitted state and no fabricated scores.
- Category L:
  - Legacy P-1–P-20 parameter inputs rejected.
  - College C1–C22 parameter inputs rejected.
"""
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.university.models import University, UniversityAssessment
from apps.university.services import UniversityAssessmentService

User = get_user_model()


class UniversityAPIParameterTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.uni = University.objects.create(
            name="Chaudhary Bansi Lal University",
            aishe_code="U-0164",
            state="Haryana",
        )
        self.uni_user = User.objects.create_user(
            email="nodal.cblu@haryana.gov.in",
            full_name="CBLU Nodal Officer",
            role="nodal_officer",
            university=self.uni,
            password="SecureCBLUPassword2026!",
        )
        self.assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni.id,
            academic_year="2025-26",
            created_by=self.uni_user,
        )
        self.client.force_authenticate(user=self.uni_user)

    # =========================================================================
    # Category E: Parameter Writes & Validations
    # =========================================================================

    def test_valid_u1_input_accepted(self):
        """Valid U1 (Apprenticeship) input is accepted and stored."""
        payload = {
            "raw_inputs": {
                "programmes_count": 8,
                "U1.1": {"programmes_count": 8},
            },
            "entities": [
                {
                    "entity_id": "prog-001",
                    "entity_type": "PROGRAMME",
                    "title": "B.Voc in Automotive Manufacturing",
                }
            ],
        }
        res = self.client.put(
            f"/api/university-assessments/{self.assessment.assessment_id}/parameters/U1/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data
        self.assertEqual(data["code"], "U1")
        self.assertEqual(data["max_marks"], 4.0)
        self.assertIn("submitted_input", data)
        self.assertEqual(data["submitted_input"]["raw_inputs"]["programmes_count"], 8)

    def test_invalid_parameter_rejected(self):
        """Non-existent parameter code (e.g. U99) is rejected with INVALID_PARAMETER."""
        res = self.client.put(
            f"/api/university-assessments/{self.assessment.assessment_id}/parameters/U99/",
            {"raw_inputs": {"val": 1}},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "INVALID_PARAMETER")

    def test_invalid_subcriterion_rejected(self):
        """Invalid subcriterion code (e.g. U1.99) is rejected with INVALID_SUBCRITERION."""
        payload = {
            "raw_inputs": {
                "U1.99": {"count": 5},
            }
        }
        res = self.client.put(
            f"/api/university-assessments/{self.assessment.assessment_id}/parameters/U1/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "INVALID_SUBCRITERION")

    def test_invalid_percentage_rejected(self):
        """Percentage > 100.0 or < 0.0 is rejected with INVALID_PARAMETER_INPUT."""
        payload = {
            "raw_inputs": {
                "placement_percentage": 110.0,
            }
        }
        res = self.client.put(
            f"/api/university-assessments/{self.assessment.assessment_id}/parameters/U5/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "INVALID_PARAMETER_INPUT")

    def test_invalid_count_rejected(self):
        """Negative count or non-integer is rejected with INVALID_PARAMETER_INPUT."""
        payload = {
            "raw_inputs": {
                "programmes_count": -5,
            }
        }
        res = self.client.put(
            f"/api/university-assessments/{self.assessment.assessment_id}/parameters/U1/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "INVALID_PARAMETER_INPUT")

    def test_invalid_temporal_activity_date_rejected(self):
        """Activity date outside assessment period (2025-07-01 to 2026-06-30) for period-sensitive parameter is rejected."""
        payload = {
            "raw_inputs": {
                "placement_percentage": 65.0,
            },
            "activity_date": "2024-03-15",  # Outside statutory period
        }
        res = self.client.put(
            f"/api/university-assessments/{self.assessment.assessment_id}/parameters/U5/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "INVALID_ASSESSMENT_PERIOD")

    def test_client_cannot_inject_scores_in_parameter_write(self):
        """Client cannot inject score fields into parameter inputs."""
        payload = {
            "raw_inputs": {"count": 10},
            "score": 4.0,
            "earned_marks": 4.0,
        }
        res = self.client.put(
            f"/api/university-assessments/{self.assessment.assessment_id}/parameters/U1/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_parameter_read_returns_authoritative_metadata(self):
        """GET parameter endpoints return authoritative metadata from registry."""
        # 1. Read single parameter U1
        res = self.client.get(
            f"/api/university-assessments/{self.assessment.assessment_id}/parameters/U1/"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data
        self.assertEqual(data["code"], "U1")
        self.assertEqual(data["max_marks"], 4.0)
        self.assertIn("subcriteria", data)
        self.assertIn("U1.1", data["subcriteria"])
        self.assertEqual(data["subcriteria"]["U1.1"]["max_score"], 4.0)
        self.assertIn("mandatory_evidence", data)
        self.assertIn("double_counting_rule", data)
        self.assertNotIn("fabricated_score", data)

        # 2. Read all 20 parameters
        list_res = self.client.get(
            f"/api/university-assessments/{self.assessment.assessment_id}/parameters/"
        )
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data), 20)
        codes = [p["code"] for p in list_res.data]
        self.assertEqual(codes, [f"U{i}" for i in range(1, 21)])

    # =========================================================================
    # Category L: Legacy Isolation
    # =========================================================================

    def test_legacy_p_parameters_rejected(self):
        """Legacy parameters (P1 through P20) cannot be submitted to University assessment."""
        for code in ["P1", "P-1", "P20"]:
            res = self.client.put(
                f"/api/university-assessments/{self.assessment.assessment_id}/parameters/{code}/",
                {"raw_inputs": {"val": 1}},
                format="json"
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(res.data.get("code"), "INVALID_PARAMETER")

    def test_college_c_parameters_rejected(self):
        """College parameters (C1 through C22) cannot be submitted to University assessment."""
        for code in ["C1", "C5", "C22"]:
            res = self.client.put(
                f"/api/university-assessments/{self.assessment.assessment_id}/parameters/{code}/",
                {"raw_inputs": {"val": 1}},
                format="json"
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(res.data.get("code"), "INVALID_PARAMETER")
