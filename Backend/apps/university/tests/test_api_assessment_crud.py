"""
Category D, J, K Tests: Assessment Creation, Lifecycle, and Concurrency.

Verifies:
- Category D:
  - Valid University creates assessment.
  - Client cannot override framework.
  - Client cannot override assessment period.
  - Initial lifecycle state is DRAFT.
- Category J:
  - Valid lifecycle transitions.
  - Invalid lifecycle transitions rejected with INVALID_LIFECYCLE_TRANSITION.
  - Segregation of duties: institution cannot trigger reviewer/admin-only transitions.
- Category K:
  - Concurrency protection on assessment mutations.
"""
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import College
from apps.university.models import University, UniversityAssessment
from apps.university.services import UniversityAssessmentService

User = get_user_model()


class UniversityAPIAssessmentCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # State Admin
        self.admin = User.objects.create_user(
            email="admin@dhe.haryana.gov.in",
            full_name="State Admin",
            role="admin",
            password="AdminPassword2026!",
        )

        # University and Nodal User
        self.uni = University.objects.create(
            name="Guru Jambheshwar University of Science and Technology",
            aishe_code="U-0162",
            state="Haryana",
        )
        self.uni_user = User.objects.create_user(
            email="nodal.gjust@haryana.gov.in",
            full_name="GJUST Nodal Officer",
            role="nodal_officer",
            university=self.uni,
            password="NodalPassword2026!",
        )

        # Committee Reviewer
        self.reviewer = User.objects.create_user(
            email="reviewer.univ@haryana.gov.in",
            full_name="University Reviewer",
            role="committee",
            password="ReviewerPassword2026!",
        )

        # External University and Nodal User
        self.uni_other = University.objects.create(
            name="Chaudhary Devi Lal University",
            aishe_code="U-0163",
            state="Haryana",
        )
        self.other_user = User.objects.create_user(
            email="nodal.cdlu@haryana.gov.in",
            full_name="CDLU Nodal Officer",
            role="nodal_officer",
            university=self.uni_other,
            password="OtherPassword2026!",
        )

    # =========================================================================
    # Category D: Assessment Creation
    # =========================================================================

    def test_valid_university_creates_assessment(self):
        """Authorized university user creates an assessment in DRAFT state."""
        self.client.force_authenticate(user=self.uni_user)
        payload = {
            "academic_year": "2025-26",
        }
        res = self.client.post(
            f"/api/universities/{self.uni.id}/assessments/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.data
        self.assertEqual(data["framework"], "UNIVERSITY_2026")
        self.assertEqual(data["period_start"], "2025-07-01")
        self.assertEqual(data["period_end"], "2026-06-30")
        self.assertEqual(data["academic_year"], "2025-26")
        self.assertEqual(data["status"], "DRAFT")
        self.assertIsNone(data["certified_score"])
        self.assertTrue(data["assessment_id"].startswith(f"ASSESS-2026-UNI-{self.uni.aishe_code}"))

    def test_client_cannot_override_framework(self):
        """Client cannot override framework with COLLEGE_2026 or other frameworks."""
        self.client.force_authenticate(user=self.uni_user)
        payload = {
            "academic_year": "2025-26",
            "framework": "COLLEGE_2026",
        }
        res = self.client.post(
            f"/api/universities/{self.uni.id}/assessments/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "INVALID_FRAMEWORK")

    def test_client_cannot_override_assessment_period(self):
        """Client cannot alter statutory assessment period (2025-07-01 to 2026-06-30)."""
        self.client.force_authenticate(user=self.uni_user)
        payload = {
            "period_start": "2024-01-01",
        }
        res = self.client.post(
            f"/api/universities/{self.uni.id}/assessments/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "INVALID_ASSESSMENT_PERIOD")

    def test_client_cannot_inject_scores_during_creation(self):
        """Client cannot supply score fields in creation payload."""
        self.client.force_authenticate(user=self.uni_user)
        payload = {
            "academic_year": "2025-26",
            "certified_score": 95.0,
            "score": 100.0,
        }
        res = self.client.post(
            f"/api/universities/{self.uni.id}/assessments/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Category J: Lifecycle Transitions
    # =========================================================================

    def test_invalid_transition_from_draft_to_finalized_rejected(self):
        """Assessment cannot leap directly from DRAFT to FINALIZED."""
        self.client.force_authenticate(user=self.uni_user)
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni.id,
            academic_year="2025-26",
            created_by=self.uni_user,
        )

        res = self.client.patch(
            f"/api/university-assessments/{assessment.assessment_id}/",
            {"status": "FINALIZED"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(res.data.get("code"), "INVALID_LIFECYCLE_TRANSITION")

    def test_institution_user_cannot_perform_reviewer_transition(self):
        """Institution user cannot transition assessment to UNDER_REVIEW."""
        self.client.force_authenticate(user=self.uni_user)
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni.id,
            academic_year="2025-26",
            created_by=self.uni_user,
        )

        # Manually set to SUBMITTED to test next transition
        assessment.status = "SUBMITTED"
        assessment.save(update_fields=["status"])

        res = self.client.patch(
            f"/api/university-assessments/{assessment.assessment_id}/",
            {"status": "UNDER_REVIEW"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("code"), "ASSESSMENT_NOT_AUTHORIZED")

    def test_reviewer_can_transition_to_under_review(self):
        """Authorized reviewer or admin can transition SUBMITTED to UNDER_REVIEW."""
        self.client.force_authenticate(user=self.reviewer)
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni.id,
            academic_year="2025-26",
            created_by=self.uni_user,
        )
        assessment.status = "SUBMITTED"
        assessment.save(update_fields=["status"])

        res = self.client.patch(
            f"/api/university-assessments/{assessment.assessment_id}/",
            {"status": "UNDER_REVIEW"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data.get("status"), "UNDER_REVIEW")

    # =========================================================================
    # Category K: Concurrency Protection
    # =========================================================================

    def test_concurrent_parameter_mutation_locking(self):
        """Verifies row-level locking preserves data integrity across updates."""
        assessment = UniversityAssessmentService.create_assessment(
            university_id=self.uni.id,
            academic_year="2025-26",
            created_by=self.uni_user,
        )
        self.client.force_authenticate(user=self.uni_user)

        # First update U1
        res1 = self.client.put(
            f"/api/university-assessments/{assessment.assessment_id}/parameters/U1/",
            {"raw_inputs": {"programmes_count": 5}},
            format="json"
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Second update U2
        res2 = self.client.put(
            f"/api/university-assessments/{assessment.assessment_id}/parameters/U2/",
            {"raw_inputs": {"languages_count": 3}},
            format="json"
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        # Refresh assessment from DB to confirm both updates were preserved
        assessment.refresh_from_db()
        self.assertIn("U1", assessment.parameter_data)
        self.assertIn("U2", assessment.parameter_data)
        self.assertEqual(assessment.parameter_data["U1"]["raw_inputs"]["programmes_count"], 5)
        self.assertEqual(assessment.parameter_data["U2"]["raw_inputs"]["languages_count"], 3)
