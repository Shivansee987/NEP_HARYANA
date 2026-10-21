from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import College
from .models import Nomination
from .scoring import calculate_nomination_score

User = get_user_model()

class NominationTests(APITestCase):
    def setUp(self):
        self.college = College.objects.create(name="Test University", aishe_code="U-12345")
        self.user = User.objects.create_user(
            email="principal@test.edu.in",
            full_name="Principal Test",
            role="principal",
            college=self.college,
            password="SecurePassword123!"
        )
        self.client.force_authenticate(user=self.user)
        self.form_id = "nep-excellence-nomination-2025"

    def test_get_nomination_creates_default(self):
        url = reverse('nomination-detail', kwargs={'form_id': self.form_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['form_id'], self.form_id)
        self.assertEqual(response.data['score'], 0)
        self.assertEqual(response.data['is_submitted'], False)

    def test_save_draft_and_score_calculation(self):
        # Initialize
        url_detail = reverse('nomination-detail', kwargs={'form_id': self.form_id})
        self.client.get(url_detail)
        
        # Save draft with custom answers
        url_save = reverse('nomination-save', kwargs={'form_id': self.form_id})
        data = {
            "head_name": "Dr. Signatory",
            "head_contact": "+91 9999999999",
            "address": "State Highway, City",
            "institution_type": "Government College",
            "answers": {
                "indicator_1": {"value": "Yes", "note": "Docs attached"}, # 4 marks
                "indicator_5": {"value": "Yes", "url": "https://test.edu.in/idp"}, # 6 marks
                "indicator_7": {"value": "A+"}, # 6 marks
                "indicator_8": {"value": "Yes"}, # 2 marks
                "indicator_9": {"value": "Yes", "percentage": "80"}, # >75% = 8 marks
                "indicator_10": {"value": "Yes"}, # 4 marks
                "indicator_11": {"value": "Yes", "items": ["PoP A", "PoP B"]}, # 2 pops = 4 marks
                "indicator_12": {"value": "Yes", "count": "12", "items": []}, # >10 = 6 marks
                "indicator_13": {"value": "Yes", "note": "Implemented"}, # 4 marks
                "indicator_19": {"value": "Yes", "note": "MOOCs policy"} # 4 marks
            }
        }
        # Expected Score: 4 + 6 + 6 + 2 + 8 + 4 + 4 + 6 + 4 + 4 = 48 (Silver Award, since > 50 is Silver, wait, 48 is <= 50, so No Award)
        response = self.client.post(url_save, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nomination']['score'], 48)
        self.assertEqual(response.data['nomination']['award_category'], "No Award")

    def test_submit_validation_fails_with_fewer_than_10_indicators(self):
        url_detail = reverse('nomination-detail', kwargs={'form_id': self.form_id})
        self.client.get(url_detail)
        
        # Save draft with only 2 indicators filled
        url_save = reverse('nomination-save', kwargs={'form_id': self.form_id})
        data = {
            "head_name": "Dr. Signatory",
            "head_contact": "+91 9999999999",
            "address": "State Highway, City",
            "institution_type": "Government College",
            "answers": {
                "indicator_1": {"value": "Yes"},
                "indicator_2": {"value": "Yes"}
            }
        }
        self.client.post(url_save, data, format='json')
        
        # Try to submit
        url_submit = reverse('nomination-submit', kwargs={'form_id': self.form_id})
        response = self.client.post(url_submit, {"declaration_accepted": True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You must fill out at least 10", response.data['detail'])

    def test_successful_submit_locks_form(self):
        url_detail = reverse('nomination-detail', kwargs={'form_id': self.form_id})
        self.client.get(url_detail)
        
        # Save draft with 10 indicators filled
        url_save = reverse('nomination-save', kwargs={'form_id': self.form_id})
        answers = {}
        for i in range(1, 11):
            answers[f"indicator_{i}"] = {"value": "Yes"}
        data = {
            "head_name": "Dr. Signatory",
            "head_contact": "+91 9999999999",
            "address": "State Highway, City",
            "institution_type": "Government College",
            "answers": answers
        }
        self.client.post(url_save, data, format='json')
        
        # Submit
        url_submit = reverse('nomination-submit', kwargs={'form_id': self.form_id})
        response = self.client.post(url_submit, {"declaration_accepted": True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nomination']['is_submitted'], True)
        
        # Attempt to save again should fail
        response_save_again = self.client.post(url_save, data, format='json')
        self.assertEqual(response_save_again.status_code, status.HTTP_400_BAD_REQUEST)


class NominationCollegeBindingTests(APITestCase):
    """
    S-01 (security review 2026-10-21): a user without an approved college binding must not reach any college's
    nomination. The removed fallback handed such users the first college in the database.
    """
    def setUp(self):
        self.form_id = "nep-excellence-nomination-2025"
        self.first_college = College.objects.order_by('pk').first() or College.objects.create(name="First College")
        self.nomination = Nomination.objects.create(
            form_id=self.form_id, college=self.first_college, head_name="Real Principal",
            answers={"indicator_1": {"value": "Yes"}},
        )
        requested = College.objects.create(name="Requested College")
        self.pending = User.objects.create_user(
            email="pending@test.edu.in", full_name="Pending Applicant", role="principal",
            password="SecurePassword123!", institution_status='PENDING', requested_college=requested,
        )
        self.unbound_admin = User.objects.create_user(
            email="state@test.gov.in", full_name="State Admin", role="state_admin", password="SecurePassword123!",
        )

    def _assert_no_access(self, user):
        self.client.force_authenticate(user=user)
        urls = [
            ('get', reverse('nomination-list')),
            ('get', reverse('my-submissions-list')),
            ('get', reverse('nomination-detail', kwargs={'form_id': self.form_id})),
            ('post', reverse('nomination-save', kwargs={'form_id': self.form_id})),
            ('post', reverse('nomination-submit', kwargs={'form_id': self.form_id})),
            ('get', reverse('principal-clarification', kwargs={'form_id': self.form_id})),
            ('post', reverse('principal-clarification', kwargs={'form_id': self.form_id})),
        ]
        for method, url in urls:
            response = getattr(self.client, method)(url, {'head_name': 'ATTACKER', 'response': 'x'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, f"{method.upper()} {url}")
        self.nomination.refresh_from_db()
        self.assertEqual(self.nomination.head_name, "Real Principal")
        self.assertEqual(Nomination.objects.count(), 1)

    def test_pending_applicant_cannot_reach_any_nomination(self):
        self._assert_no_access(self.pending)

    def test_user_without_college_cannot_reach_any_nomination(self):
        self._assert_no_access(self.unbound_admin)

    def test_rejected_binding_cannot_reach_its_college_nomination(self):
        self.pending.college = self.first_college
        self.pending.institution_status = 'REJECTED'
        self.pending.save()
        self._assert_no_access(self.pending)


class NominationConfigTests(APITestCase):
    """S-07: the legacy direct-upload settings come only from the environment; there is no built-in account."""
    def setUp(self):
        self.user = User.objects.create_user(
            email="config@test.edu.in", full_name="Principal Config", role="principal", password="SecurePassword123!"
        )
        self.client.force_authenticate(user=self.user)

    def test_no_default_cloudinary_account(self):
        from unittest.mock import patch
        with patch.dict('os.environ', {}, clear=False):
            import os
            os.environ.pop('CLOUDINARY_CLOUD_NAME', None)
            os.environ.pop('CLOUDINARY_UPLOAD_PRESET_NAME', None)
            response = self.client.get(reverse('nomination-config'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['cloudinary_cloud_name'], '')
        self.assertEqual(response.data['cloudinary_upload_preset'], '')
