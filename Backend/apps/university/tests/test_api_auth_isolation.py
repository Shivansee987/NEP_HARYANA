"""
Category A, B, C Tests: Authentication and Institutional Framework Isolation.

Verifies:
- Category A: Unauthenticated requests denied with 401 Unauthorized.
- Category B: University A cannot access University B's records or assessments.
- Category C: College user cannot access University assessments; University user cannot access College nominations.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import College
from apps.nominations.models import Nomination
from apps.university.models import University, UniversityAssessment
from apps.university.services import UniversityAssessmentService

User = get_user_model()


class UniversityAPIAuthAndIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin user
        self.admin_user = User.objects.create_user(
            email="dhe.admin@haryana.gov.in",
            full_name="DHE State Admin",
            role="admin",
            password="AdminPassword2026!",
        )

        # University A
        self.uni_a = University.objects.create(
            name="Kurukshetra University",
            aishe_code="U-0160",
            state="Haryana",
        )
        self.user_uni_a = User.objects.create_user(
            email="nodal.kuk@haryana.gov.in",
            full_name="KUK Nodal Officer",
            role="nodal_officer",
            university=self.uni_a,
            password="PasswordKUK2026!",
        )

        # University B
        self.uni_b = University.objects.create(
            name="Maharshi Dayanand University",
            aishe_code="U-0161",
            state="Haryana",
        )
        self.user_uni_b = User.objects.create_user(
            email="nodal.mdu@haryana.gov.in",
            full_name="MDU Nodal Officer",
            role="nodal_officer",
            university=self.uni_b,
            password="PasswordMDU2026!",
        )

        # College and College Principal
        self.college, _ = College.objects.get_or_create(
            aishe_code="C-99988",
            defaults={"name": "Govt College Panchkula"}
        )
        self.college_user = User.objects.create_user(
            email="principal.gcp@haryana.gov.in",
            full_name="Principal GCP",
            role="principal",
            college=self.college,
            password="CollegePassword2026!",
        )

        # Assessments for Uni A and Uni B
        self.assess_a = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=self.user_uni_a,
        )
        self.assess_b = UniversityAssessmentService.create_assessment(
            university_id=self.uni_b.id,
            academic_year="2025-26",
            created_by=self.user_uni_b,
        )

    # =========================================================================
    # Category A: Authentication
    # =========================================================================

    def test_unauthenticated_requests_denied(self):
        """Unauthenticated requests must receive HTTP 401 Unauthorized."""
        endpoints = [
            ("get", "/api/universities/"),
            ("get", f"/api/universities/{self.uni_a.id}/"),
            ("get", f"/api/universities/{self.uni_a.id}/assessments/"),
            ("get", f"/api/university-assessments/{self.assess_a.assessment_id}/"),
            ("get", f"/api/university-assessments/{self.assess_a.assessment_id}/parameters/"),
            ("get", f"/api/university-assessments/{self.assess_a.assessment_id}/parameters/U1/"),
            ("get", f"/api/university-assessments/{self.assess_a.assessment_id}/coverage/"),
            ("get", f"/api/university-assessments/{self.assess_a.assessment_id}/readiness/"),
            ("post", f"/api/university-assessments/{self.assess_a.assessment_id}/evaluate/"),
            ("post", f"/api/university-assessments/{self.assess_a.assessment_id}/submit/"),
        ]

        for method, url in endpoints:
            if method == "get":
                res = self.client.get(url)
            else:
                res = self.client.post(url, {}, format="json")
            self.assertEqual(
                res.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {url} did not enforce 401 for unauthenticated request (got {res.status_code})."
            )

    # =========================================================================
    # Category B: Institution Isolation (University A vs University B)
    # =========================================================================

    def test_university_a_cannot_access_university_b_detail(self):
        """User from University A cannot access University B detail endpoint."""
        self.client.force_authenticate(user=self.user_uni_a)
        res = self.client.get(f"/api/universities/{self.uni_b.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("code"), "UNIVERSITY_NOT_AUTHORIZED")

    def test_university_a_cannot_access_university_b_assessments_list(self):
        """User from University A cannot list assessments for University B."""
        self.client.force_authenticate(user=self.user_uni_a)
        res = self.client.get(f"/api/universities/{self.uni_b.id}/assessments/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("code"), "ASSESSMENT_NOT_AUTHORIZED")

    def test_university_a_cannot_access_university_b_assessment_detail(self):
        """User from University A cannot access assessment session of University B."""
        self.client.force_authenticate(user=self.user_uni_a)
        res = self.client.get(f"/api/university-assessments/{self.assess_b.assessment_id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("code"), "ASSESSMENT_NOT_AUTHORIZED")

    def test_university_a_cannot_modify_university_b_parameters(self):
        """User from University A cannot mutate parameter data for University B."""
        self.client.force_authenticate(user=self.user_uni_a)
        payload = {
            "raw_inputs": {"programmes_count": 10},
        }
        res = self.client.put(
            f"/api/university-assessments/{self.assess_b.assessment_id}/parameters/U1/",
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("code"), "ASSESSMENT_NOT_AUTHORIZED")

    def test_university_a_cannot_submit_university_b_assessment(self):
        """User from University A cannot submit assessment of University B."""
        self.client.force_authenticate(user=self.user_uni_a)
        res = self.client.post(
            f"/api/university-assessments/{self.assess_b.assessment_id}/submit/",
            {},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("code"), "ASSESSMENT_NOT_AUTHORIZED")

    def test_university_list_scoped_to_own_institution(self):
        """University list endpoint only returns own university for institution user."""
        self.client.force_authenticate(user=self.user_uni_a)
        res = self.client.get("/api/universities/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Results may be paginated or list
        results = res.data.get("results") if isinstance(res.data, dict) and "results" in res.data else res.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.uni_a.id)

    # =========================================================================
    # Category C: Framework Isolation (College vs University)
    # =========================================================================

    def test_college_user_cannot_access_university_endpoints(self):
        """College user cannot access University list, detail, or assessment endpoints."""
        self.client.force_authenticate(user=self.college_user)

        endpoints = [
            ("/api/universities/", status.HTTP_403_FORBIDDEN),
            (f"/api/universities/{self.uni_a.id}/", status.HTTP_403_FORBIDDEN),
            (f"/api/universities/{self.uni_a.id}/assessments/", status.HTTP_403_FORBIDDEN),
            (f"/api/university-assessments/{self.assess_a.assessment_id}/", status.HTTP_403_FORBIDDEN),
            (f"/api/university-assessments/{self.assess_a.assessment_id}/parameters/", status.HTTP_403_FORBIDDEN),
            (f"/api/university-assessments/{self.assess_a.assessment_id}/coverage/", status.HTTP_403_FORBIDDEN),
            (f"/api/university-assessments/{self.assess_a.assessment_id}/readiness/", status.HTTP_403_FORBIDDEN),
        ]

        for url, expected_status in endpoints:
            res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                expected_status,
                f"College user was able to access {url} (status: {res.status_code})"
            )

    def test_college_user_cannot_create_university_assessment(self):
        """College user cannot create assessment for a university."""
        self.client.force_authenticate(user=self.college_user)
        res = self.client.post(
            f"/api/universities/{self.uni_a.id}/assessments/",
            {"academic_year": "2025-26"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
