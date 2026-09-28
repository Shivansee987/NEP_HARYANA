"""Only the Screening Committee Chair may certify; State Admin and superusers oversee but cannot certify."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authentication.models import College
from apps.college.models import CollegeAssessment
from apps.college.services import CollegeReviewService
from apps.college.validators import CertificationNotAuthorizedError as CollegeCertNotAuthorized
from apps.university.models import University, UniversityAssessment
from apps.university.services import UniversityReviewService
from apps.university.validators import CertificationNotAuthorizedError as UniversityCertNotAuthorized

User = get_user_model()


class CertificationAuthorityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        college = College.objects.create(name="Govt College Jind", aishe_code="C-CERT-1")
        uni = University.objects.create(name="Test University", aishe_code="U-CERT-1")
        self.col = CollegeAssessment.objects.create(assessment_id="COL-CERT", college=college, status="CERTIFICATION_PENDING")
        self.uni = UniversityAssessment.objects.create(assessment_id="UNI-CERT", university=uni, status="CERTIFICATION_PENDING")
        self.admin = User.objects.create_user(email="a@x.in", full_name="State Admin", role="admin", password="Pass@12345")
        self.superuser = User.objects.create_superuser(email="s@x.in", full_name="Superuser", password="Pass@12345")
        self.chair = User.objects.create_user(email="c@x.in", full_name="Chair", role="committee_chair",
                                              password="Pass@12345")

    def test_admin_and_superuser_cannot_certify_via_any_endpoint(self):
        urls = [
            "/api/v1/admin/assessments/COL-CERT/certify/",
            "/api/v1/college/college-assessments/COL-CERT/certify/",
            "/api/v1/university/university-assessments/UNI-CERT/certify/",
        ]
        for user in (self.admin, self.superuser):
            self.client.force_authenticate(user)
            for url in urls:
                res = self.client.post(url, {"comments": "Attempt"}, format="json")
                self.assertEqual(res.status_code, 403, f"{user.email} {url}")
        self.col.refresh_from_db()
        self.uni.refresh_from_db()
        self.assertEqual((self.col.status, self.uni.status), ("CERTIFICATION_PENDING", "CERTIFICATION_PENDING"))

    def test_domain_services_reject_non_chair(self):
        for user in (self.admin, self.superuser):
            with self.assertRaises(CollegeCertNotAuthorized):
                CollegeReviewService.validate_certification_authority(user, self.col)
            with self.assertRaises(UniversityCertNotAuthorized):
                UniversityReviewService.validate_certification_authority(user, self.uni)

    def test_chair_passes_authority_check(self):
        self.assertTrue(CollegeReviewService.validate_certification_authority(self.chair, self.col))
        self.assertTrue(UniversityReviewService.validate_certification_authority(self.chair, self.uni))
