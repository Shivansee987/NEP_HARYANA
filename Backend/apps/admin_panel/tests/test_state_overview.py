"""State Admin institution overview: GET /api/v1/admin/institutions/."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authentication.models import College
from apps.college.models import CollegeAssessment
from apps.university.models import University, UniversityAssessment

User = get_user_model()
URL = "/api/v1/admin/institutions/"


class StateOverviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        College.objects.all().delete()  # migrations seed demo colleges
        University.objects.all().delete()
        self.college_new = College.objects.create(name="Govt College Jind", aishe_code="C-1")
        self.college_sub = College.objects.create(name="Govt College Sirsa", aishe_code="C-2")
        self.uni = University.objects.create(name="Kurukshetra University", aishe_code="U-1")
        self.principal = User.objects.create_user(email="p@x.in", full_name="Principal Sirsa", role="principal",
                                                  college=self.college_sub, password="Pass@12345")
        User.objects.create_user(email="n@x.in", full_name="Nodal KUK", role="nodal_officer", university=self.uni,
                                 password="Pass@12345")
        self.reviewer = User.objects.create_user(email="r@x.in", full_name="Reviewer", role="committee",
                                                 password="Pass@12345")
        self.chair = User.objects.create_user(email="c@x.in", full_name="Chair", role="committee_chair",
                                              password="Pass@12345")
        self.admin = User.objects.create_user(email="a@x.in", full_name="State Admin", role="admin",
                                              password="Pass@12345")
        CollegeAssessment.objects.create(assessment_id="COL-SUB", college=self.college_sub, status="SUBMITTED")
        UniversityAssessment.objects.create(assessment_id="UNI-REV", university=self.uni, status="UNDER_REVIEW",
                                            assigned_reviewer=self.reviewer, certified_score=71.5)

    def test_admin_sees_every_institution_including_not_started(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        rows = {r["name"]: r for r in res.data["institutions"]}
        self.assertEqual(set(rows), {"Govt College Jind", "Govt College Sirsa", "Kurukshetra University"})
        self.assertEqual(rows["Govt College Jind"]["stage"], "NOT_STARTED")
        self.assertIsNone(rows["Govt College Jind"]["assessment_id"])
        self.assertEqual(rows["Govt College Sirsa"]["stage"], "SUBMITTED")
        self.assertEqual(rows["Govt College Sirsa"]["contact_email"], "p@x.in")
        uni = rows["Kurukshetra University"]
        self.assertEqual((uni["institution_type"], uni["stage"], uni["score"]), ("UNIVERSITY", "UNDER_REVIEW", 71.5))
        self.assertEqual(uni["assigned_reviewer_name"], "Reviewer")

    def test_summary_and_committee_workload(self):
        self.client.force_authenticate(self.admin)
        data = self.client.get(URL).data
        self.assertEqual(data["summary"]["universities"], 1)
        self.assertEqual(data["summary"]["colleges"], 2)
        self.assertEqual(data["summary"]["started"], 2)
        self.assertEqual(data["summary"]["by_stage"]["NOT_STARTED"], 1)
        self.assertEqual(data["committee"]["pending_reviews"], 2)
        self.assertEqual(data["committee"]["unassigned"], 1)
        load = {r["email"]: r["active_assignments"] for r in data["committee"]["reviewers"]}
        self.assertEqual(load, {"r@x.in": 1, "c@x.in": 0})

    def test_non_admin_roles_are_denied(self):
        for user in (self.principal, self.reviewer, self.chair):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(URL).status_code, 403, user.role)

    def test_read_only(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(URL, {}).status_code, 405)
