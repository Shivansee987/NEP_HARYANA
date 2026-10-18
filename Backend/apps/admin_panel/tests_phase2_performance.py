"""
Tests for Phase 2: Database Performance, Indexing, and N+1 Query Elimination.
Asserts that admin institutions summary and dashboard stats execute with minimal constant queries (O(1) queries instead of O(N)).
"""
from django.test import TestCase
from apps.authentication.models import College, User
from apps.nominations.models import Nomination
from apps.admin_panel.services import get_institutions_summary, get_dashboard_stats, get_all_applications


class AdminQueryPerformanceTestCase(TestCase):
    def setUp(self):
        # Create 15 sample colleges with nominations to test N+1 elimination
        for i in range(15):
            college = College.objects.create(
                name=f"Govt College {i:02d} Rohtak",
                aishe_code=f"C-900{i:02d}",
                district="Rohtak",
                institute_type="Government",
            )
            Nomination.objects.create(
                form_id=f"FORM-{i:02d}",
                college=college,
                status="Pending Review" if i % 2 == 0 else "Approved",
                is_submitted=True,
                award_category="Gold" if i % 2 == 0 else "Platinum",
                score=75,
            )

    def test_institutions_summary_query_count_is_constant(self):
        # Now it must execute in exactly 2 queries: (1) College.objects.all(), (2) Nomination.objects.all()
        # regardless of how many colleges exist
        initial_colleges_count = College.objects.count()
        with self.assertNumQueries(2):
            summary = get_institutions_summary()
            self.assertEqual(len(summary), initial_colleges_count)

    def test_dashboard_stats_query_count_is_minimal(self):
        # Dashboard stats uses aggregate queries and no longer calls get_institutions_summary loop
        total_colleges = College.objects.count()
        with self.assertNumQueries(5):
            # 1: College.count, 2: User.filter(role=principal).count,
            # 3: Nomination.count, 4: Nomination.filter(is_submitted=True).count,
            # 5: Nomination.aggregate(...)
            stats = get_dashboard_stats()
            self.assertEqual(stats["total_colleges"], total_colleges)
            self.assertEqual(stats["total_applications"], 15)
            self.assertEqual(stats["submitted_applications"], 15)
            self.assertEqual(stats["approved_awards"], 7)
            self.assertEqual(stats["pending_review"], 8)

    def test_get_all_applications_query_count(self):
        # With select_related("college"), loading nominations and accessing college details is 1 query
        with self.assertNumQueries(1):
            apps = get_all_applications()
            self.assertEqual(len(apps), 15)
            for app in apps:
                self.assertTrue(app["college_name"].startswith("Govt College"))
