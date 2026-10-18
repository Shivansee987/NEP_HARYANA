"""
Unit and concurrency tests for Phase 1 backend remediation.
Validates:
1. Optimistic concurrency control on CollegeAssessment & UniversityAssessment parameter updates.
2. Atomic brute-force attempt increments in authentication LoginView.
"""
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.authentication.models import College, User
from apps.authentication.views import LoginView
from apps.college.models import CollegeAssessment
from apps.college.services import CollegeAssessmentService
from apps.college.validators import ConcurrentUpdateError
from apps.university.models import University, UniversityAssessment
from apps.university.services import UniversityAssessmentService
from apps.university.validators import ConcurrentUpdateError as UniConcurrentUpdateError


class AssessmentConcurrencyTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.college = College.objects.create(
            name="Government PG College Ambala",
            aishe_code="C-12345",
            district="Ambala",
            institute_type="Government",
        )
        self.assessment = CollegeAssessment.objects.create(
            assessment_id="ASSESS-2026-COL-C12345-TEST",
            college=self.college,
            academic_year="2025-26",
            status="DRAFT",
            parameter_data={},
            version=1,
        )
        self.university = University.objects.create(
            name="Kurukshetra University",
            aishe_code="U-0123",
            district="Kurukshetra",
            university_type="State University",
            is_active=True,
        )
        self.uni_assessment = UniversityAssessment.objects.create(
            assessment_id="ASSESS-2026-UNI-U0123-TEST",
            university=self.university,
            academic_year="2025-26",
            status="DRAFT",
            parameter_data={},
            version=1,
        )

    def test_college_assessment_version_increments_on_save(self):
        initial_version = self.assessment.version
        updated = CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"student_strength": 1200},
            expected_version=initial_version,
        )
        self.assertEqual(updated.version, initial_version + 1)
        self.assertIn("C1", updated.parameter_data)

    def test_college_assessment_concurrency_conflict_raises_error(self):
        # Initial save increments version to 2
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=self.assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"student_strength": 1200},
            expected_version=1,
        )
        # Attempting second update with stale expected_version=1 should fail with ConcurrentUpdateError
        with self.assertRaises(ConcurrentUpdateError):
            CollegeAssessmentService.update_parameter_inputs(
                assessment_id=self.assessment.assessment_id,
                parameter_code="C2",
                raw_inputs={"faculty_count": 80},
                expected_version=1,
            )

    def test_university_assessment_version_increments_and_conflicts(self):
        initial_version = self.uni_assessment.version
        updated = UniversityAssessmentService.update_parameter_inputs(
            assessment_id=self.uni_assessment.assessment_id,
            parameter_code="U1",
            raw_inputs={"total_students": 5000},
            expected_version=initial_version,
        )
        self.assertEqual(updated.version, initial_version + 1)
        self.assertIn("U1", updated.parameter_data)

        # Stale version raises UniConcurrentUpdateError
        with self.assertRaises(UniConcurrentUpdateError):
            UniversityAssessmentService.update_parameter_inputs(
                assessment_id=self.uni_assessment.assessment_id,
                parameter_code="U2",
                raw_inputs={"faculty": 250},
                expected_version=initial_version,
            )


class LoginLockoutAtomicTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()
        self.view = LoginView.as_view()
        self.user = User.objects.create_user(
            email="test_lockout@example.com",
            full_name="Test Applicant User",
            password="CorrectPassword123!",
            role="applicant",
            is_email_verified=True,
            is_active=True,
        )

    def test_failed_login_increments_atomically_and_locks_out(self):
        email = "test_lockout@example.com"
        for _ in range(4):
            request = self.factory.post(
                "/api/v1/auth/login/",
                {"email": email, "password": "WrongPassword"},
                format="json",
            )
            response = self.view(request)
            self.assertEqual(response.status_code, 401)

        # 5th attempt triggers lockout
        request = self.factory.post(
            "/api/v1/auth/login/",
            {"email": email, "password": "WrongPassword"},
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 429)
        self.assertIn("Account locked", response.data["detail"])
