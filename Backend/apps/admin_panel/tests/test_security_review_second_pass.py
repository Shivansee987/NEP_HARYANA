"""
Security review 2026-10-21, second pass:
- S-21: malformed or oversized pagination parameters never cause a server error or an unbounded page.
- S-23: review scope can only be granted to committee roles, with a valid framework (FIN-21).
- S-24: approving an institution request takes effect immediately for the applicant's next request.
"""
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.authentication.authentication import get_user_cache_key
from apps.authentication.models import College, User
from apps.authentication.utils import generate_access_token
from apps.evidence.models import ReviewerAuthorization
from apps.nominations.models import Nomination

PASSWORD = "x-Str0ng!Passw0rd"


def _user(email, role, **extra):
    return User.objects.create_user(email=email, full_name="Test User", role=role, password=PASSWORD,
                                    is_email_verified=True, **extra)


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PaginationParameterTests(TestCase):
    def setUp(self):
        self.head = _user("head@example.com", "head_admin")

    def test_admin_lists_tolerate_malformed_page_parameters(self):
        client = _client(self.head)
        for url in ("/api/v1/admin/users/", "/api/v1/admin/users/audit-trail/"):
            for query in ("page=abc", "page_size=xyz", "page=-5&page_size=0", "page=1e9"):
                response = client.get(f"{url}?{query}")
                self.assertEqual(response.status_code, 200, f"{url}?{query}")

    def test_admin_page_size_is_capped(self):
        response = _client(self.head).get("/api/v1/admin/users/audit-trail/?page_size=100000")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(response.data["page_size"], 100)

    def test_committee_submission_list_tolerates_and_caps_page_size(self):
        college = College.objects.create(name="Some College")
        for i in range(3):
            Nomination.objects.create(form_id=f"form-{i}", college=college, is_submitted=True)
        client = _client(_user("legacy.committee@example.com", "committee"))
        for query in ("page_size=abc", "page=zz", "page_size=-1"):
            self.assertEqual(client.get(f"/api/nominations/committee/submissions/?{query}").status_code, 200, query)
        response = client.get("/api/nominations/committee/submissions/?page_size=1000000")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data["results"]), 100)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ReviewScopeGrantTests(TestCase):
    def setUp(self):
        self.state = _user("state@example.com", "state_admin")
        self.head = _user("head@example.com", "head_admin")

    def test_scope_cannot_be_granted_to_non_committee_roles(self):
        for role in ("principal", "nodal_officer", "council_admin", "sub_admin"):
            target = _user(f"{role}@example.com", role)
            response = _client(self.state).post(f"/api/v1/admin/users/{target.pk}/committee/",
                                                {"framework": "COLLEGE_2026", "action": "assign"}, format="json")
            self.assertEqual(response.status_code, 400, role)
            self.assertFalse(ReviewerAuthorization.objects.filter(user=target).exists(), role)

    def test_scope_can_be_granted_to_committee_member(self):
        member = _user("member@example.com", "committee")
        response = _client(self.state).post(f"/api/v1/admin/users/{member.pk}/committee/",
                                            {"framework": "COLLEGE_2026", "action": "assign"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ReviewerAuthorization.objects.filter(user=member, framework="COLLEGE_2026").exists())

    def test_user_creation_refuses_unknown_committee_framework(self):
        response = _client(self.head).post("/api/v1/admin/users/", {
            "email": "new.member@example.com", "full_name": "New Member", "role": "committee",
            "committee_framework": "EVERYTHING"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="new.member@example.com").exists())


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class InstitutionApprovalCacheTests(TestCase):
    def test_approval_takes_effect_on_next_request(self):
        cache.clear()
        college = College.objects.create(name="Requested College")
        applicant = _user("applicant@example.com", "principal", institution_status="PENDING",
                          requested_college=college)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {generate_access_token(applicant)}")
        self.assertEqual(client.get("/api/auth/me/").json().get("institution_status"), "PENDING")
        self.assertIsNotNone(cache.get(get_user_cache_key(applicant.pk)))

        response = _client(_user("head@example.com", "head_admin")).post(
            f"/api/v1/admin/users/{applicant.pk}/institution-access/", {"decision": "approve"}, format="json")
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertEqual(client.get("/api/auth/me/").json().get("institution_status"), "VERIFIED")
