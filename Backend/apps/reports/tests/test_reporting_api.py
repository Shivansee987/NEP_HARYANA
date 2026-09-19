"""
NEP Excellence Awards 2026 - Reports & Analytics Test Suite (Phase 9)
Covers authentication, tenant isolation, cross-framework security, parameter reports,
evidence readiness, scoring projections, review history, admin analytics, and read-only enforcement.
"""
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import College
from apps.college.models import CollegeAssessment
from apps.university.models import University, UniversityAssessment
from apps.evidence.models import ReviewerAuthorization

User = get_user_model()


class ReportingAPITests(TestCase):
    """
    Comprehensive test suite for Phase 9 Reports & Analytics.
    """

    def setUp(self):
        self.client = APIClient()

        # 1. Institutions
        self.college_a = College.objects.create(name="Govt College A", aishe_code="C-001")
        self.college_b = College.objects.create(name="Govt College B", aishe_code="C-002")
        self.university_a = University.objects.create(name="State University A", aishe_code="U-001")
        self.university_b = University.objects.create(name="State University B", aishe_code="U-002")

        # 2. Users
        self.admin = User.objects.create_user(
            email="admin@test.gov.in", full_name="Admin User", role="admin", password="Password123!"
        )
        self.chair = User.objects.create_user(
            email="chair@test.gov.in", full_name="Committee Chair", role="committee_chair", password="Password123!"
        )
        self.committee = User.objects.create_user(
            email="reviewer@test.gov.in", full_name="Reviewer User", role="committee", password="Password123!"
        )
        self.principal_a = User.objects.create_user(
            email="principal.a@test.gov.in", full_name="Principal A", role="principal", college=self.college_a, password="Password123!"
        )
        self.principal_b = User.objects.create_user(
            email="principal.b@test.gov.in", full_name="Principal B", role="principal", college=self.college_b, password="Password123!"
        )
        self.nodal_a = User.objects.create_user(
            email="nodal.a@test.gov.in", full_name="Nodal A", role="nodal_officer", university=self.university_a, password="Password123!"
        )
        self.nodal_b = User.objects.create_user(
            email="nodal.b@test.gov.in", full_name="Nodal B", role="nodal_officer", university=self.university_b, password="Password123!"
        )

        # 3. Assessments
        self.col_assess_a = CollegeAssessment.objects.create(
            assessment_id="ASSESS-COL-A-001",
            college=self.college_a,
            framework="COLLEGE_2026",
            academic_year="2025-26",
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="SUBMITTED",
            certified_score=78.5,
            certification_status="FINALIZABLE",
            parameter_data={"C1": {"c1_1_ratio": 12.0}},
        )

        self.col_assess_b = CollegeAssessment.objects.create(
            assessment_id="ASSESS-COL-B-002",
            college=self.college_b,
            framework="COLLEGE_2026",
            academic_year="2025-26",
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="DRAFT",
            parameter_data={},
        )

        self.uni_assess_a = UniversityAssessment.objects.create(
            assessment_id="ASSESS-UNI-A-001",
            university=self.university_a,
            framework="UNIVERSITY_2026",
            academic_year="2025-26",
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="UNDER_REVIEW",
            certified_score=84.0,
            certification_status="FINALIZABLE",
            parameter_data={"U1": {"u1_1_ratio": 15.0}},
        )

        self.uni_assess_b = UniversityAssessment.objects.create(
            assessment_id="ASSESS-UNI-B-002",
            university=self.university_b,
            framework="UNIVERSITY_2026",
            academic_year="2025-26",
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="CERTIFIED",
            certified_score=92.0,
            certification_status="CERTIFIED",
            parameter_data={},
        )

    # ──────────────────────────────────────────────────────────────────────────
    # 1. AUTHENTICATION
    # ──────────────────────────────────────────────────────────────────────────
    def test_unauthenticated_request_returns_401(self):
        """Unauthenticated requests must be rejected with HTTP 401."""
        res = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. CROSS-FRAMEWORK ADMIN & CHAIR VISIBILITY
    # ──────────────────────────────────────────────────────────────────────────
    def test_admin_can_view_both_university_and_college_reports(self):
        """DHE Admin has full read-only access across both frameworks."""
        self.client.force_authenticate(user=self.admin)

        # College Report
        res_col = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/")
        self.assertEqual(res_col.status_code, status.HTTP_200_OK)
        data = res_col.json()
        self.assertEqual(data["framework"], "COLLEGE_2026")
        self.assertEqual(data["institution"]["name"], "Govt College A")
        self.assertEqual(len(data["parameters"]), 22)  # C1–C22
        self.assertIn("scoring", data)
        self.assertIn("evidence", data)
        self.assertIn("certification", data)

        # University Report
        res_uni = self.client.get(f"/api/v1/reports/assessments/{self.uni_assess_a.assessment_id}/")
        self.assertEqual(res_uni.status_code, status.HTTP_200_OK)
        data_u = res_uni.json()
        self.assertEqual(data_u["framework"], "UNIVERSITY_2026")
        self.assertEqual(data_u["institution"]["name"], "State University A")
        self.assertEqual(len(data_u["parameters"]), 20)  # U1–U20

    def test_committee_chair_can_view_cross_framework_reports(self):
        """Committee Chair has cross-framework read-only report access."""
        self.client.force_authenticate(user=self.chair)

        res_col = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/")
        self.assertEqual(res_col.status_code, status.HTTP_200_OK)

        res_uni = self.client.get(f"/api/v1/reports/assessments/{self.uni_assess_a.assessment_id}/")
        self.assertEqual(res_uni.status_code, status.HTTP_200_OK)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. TENANT ISOLATION & FRAMEWORK SECURITY
    # ──────────────────────────────────────────────────────────────────────────
    def test_tenant_isolation_college_cannot_view_other_college(self):
        """Principal of College A cannot view College B report (403 Forbidden)."""
        self.client.force_authenticate(user=self.principal_a)

        # Own college: OK
        res_own = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/")
        self.assertEqual(res_own.status_code, status.HTTP_200_OK)

        # Other college: FORBIDDEN
        res_other = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_b.assessment_id}/")
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_isolation_college_cannot_view_university(self):
        """Principal of College cannot view University assessment (403 Forbidden)."""
        self.client.force_authenticate(user=self.principal_a)
        res = self.client.get(f"/api/v1/reports/assessments/{self.uni_assess_a.assessment_id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_isolation_university_cannot_view_other_university(self):
        """Nodal officer of University A cannot view University B report (403 Forbidden)."""
        self.client.force_authenticate(user=self.nodal_a)

        # Own university: OK
        res_own = self.client.get(f"/api/v1/reports/assessments/{self.uni_assess_a.assessment_id}/")
        self.assertEqual(res_own.status_code, status.HTTP_200_OK)

        # Other university: FORBIDDEN
        res_other = self.client.get(f"/api/v1/reports/assessments/{self.uni_assess_b.assessment_id}/")
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_isolation_university_cannot_view_college(self):
        """Nodal officer of University cannot view College assessment (403 Forbidden)."""
        self.client.force_authenticate(user=self.nodal_a)
        res = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_idor_manipulated_assessment_id(self):
        """Manipulated or forged assessment ID returns 404 or 403."""
        self.client.force_authenticate(user=self.principal_a)
        res = self.client.get("/api/v1/reports/assessments/FORGED-ID-999/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ──────────────────────────────────────────────────────────────────────────
    # 4. GRANULAR REPORT ENDPOINTS
    # ──────────────────────────────────────────────────────────────────────────
    def test_parameter_report_reflects_authoritative_definitions(self):
        """Parameter report returns exact statutory parameter list without client scoring."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/v1/reports/assessments/{self.uni_assess_a.assessment_id}/parameters/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(len(data["parameters"]), 20)
        p1 = data["parameters"][0]
        self.assertEqual(p1["parameter_code"], "U1")
        self.assertEqual(p1["max_marks"], 4.0)

    def test_subcriteria_report_returns_traces(self):
        """Subcriteria report returns subcriteria breakdown and traces."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/subcriteria/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn("subcriteria", data)
        self.assertGreater(len(data["subcriteria"]), 0)

    def test_evidence_report_returns_structured_readiness(self):
        """Evidence readiness report returns authoritative apps.evidence coverage."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/evidence-readiness/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn("summary", data)
        self.assertIn("is_ready_for_scoring", data)

    def test_scoring_report_returns_authoritative_frozen_engine_data(self):
        """Scoring report returns frozen scoring engine output."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/scoring/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn("scoring", data)
        scoring = data["scoring"]
        self.assertEqual(scoring["max_marks"], 100.0)

    def test_review_report_returns_lifecycle_and_history(self):
        """Review report returns lifecycle state and append-only records."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/review/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn("lifecycle", data)
        self.assertIn("review", data)
        self.assertIn("certification", data)

    # ──────────────────────────────────────────────────────────────────────────
    # 5. DRAFT ASSESSMENT NOT CONVERTED TO FAKE ZERO SCORE
    # ──────────────────────────────────────────────────────────────────────────
    def test_draft_assessment_shows_not_evaluated_not_zero(self):
        """Draft assessment must show NOT_EVALUATED and never present 0 as an evaluated score."""
        self.client.force_authenticate(user=self.principal_b)
        res = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_b.assessment_id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["scoring"]["scoring_status"], "NOT_EVALUATED")
        self.assertIsNone(data["scoring"]["raw_total"])
        self.assertIsNone(data["scoring"]["evidence_gated_total"])

    # ──────────────────────────────────────────────────────────────────────────
    # 6. ADMIN CROSS-FRAMEWORK ANALYTICS
    # ──────────────────────────────────────────────────────────────────────────
    def test_admin_cross_framework_summary_aggregates_without_rankings(self):
        """Admin summary aggregates counts across frameworks with NO institutional rankings."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/v1/reports/admin/summary/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["total_assessments"], 4)
        self.assertEqual(data["framework_distribution"]["university_assessments"], 2)
        self.assertEqual(data["framework_distribution"]["college_assessments"], 2)
        self.assertIn("lifecycle_distribution", data)
        # Verify no comparative score rankings or top 10 lists
        self.assertNotIn("top_institutions", data)
        self.assertNotIn("rankings", data)

    # ──────────────────────────────────────────────────────────────────────────
    # 7. INSTITUTION SUMMARY (OWN)
    # ──────────────────────────────────────────────────────────────────────────
    def test_institution_summary_for_principal(self):
        """Principal receives summary strictly for own college."""
        self.client.force_authenticate(user=self.principal_a)
        res = self.client.get("/api/v1/reports/institution/summary/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["institution_name"], "Govt College A")
        self.assertEqual(len(data["assessments"]), 1)
        self.assertEqual(data["assessments"][0]["assessment_id"], self.col_assess_a.assessment_id)

    # ──────────────────────────────────────────────────────────────────────────
    # 8. CSV EXPORT
    # ──────────────────────────────────────────────────────────────────────────
    def test_csv_export_returns_authoritative_data(self):
        """CSV export returns text/csv format containing authoritative parameters."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/export/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/csv")
        content = res.content.decode("utf-8")
        self.assertIn("Assessment ID", content)
        self.assertIn(self.col_assess_a.assessment_id, content)
        self.assertIn("Govt College A", content)
        self.assertIn("C1", content)

    # ──────────────────────────────────────────────────────────────────────────
    # 9. READ-ONLY ENFORCEMENT
    # ──────────────────────────────────────────────────────────────────────────
    def test_report_endpoints_reject_mutations(self):
        """POST, PUT, DELETE to report endpoints must return 405 Method Not Allowed."""
        self.client.force_authenticate(user=self.admin)
        url = f"/api/v1/reports/assessments/{self.col_assess_a.assessment_id}/"

        res_post = self.client.post(url, {"score": 100})
        self.assertEqual(res_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res_put = self.client.put(url, {"score": 100})
        self.assertEqual(res_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res_delete = self.client.delete(url)
        self.assertEqual(res_delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
