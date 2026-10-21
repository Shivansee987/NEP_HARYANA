"""
Security review 2026-10-21:
- S-03: the client address used for throttling comes only from trusted proxy hops, never from a client-supplied
  X-Forwarded-For value.
- S-04: failed logins lock the account only for the address they came from, so a third party cannot lock a user out;
  a much higher per-account ceiling still bounds distributed guessing.
- S-10: administrative audit rows record the same trusted client address.
"""
from django.conf import settings
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import AnonRateThrottle

from apps.authentication.models import User, UserAuditLog
from apps.authentication.utils import get_client_ip

PASSWORD = "Str0ng!Passw0rd#2026"


def _rest_framework(num_proxies):
    return {**settings.REST_FRAMEWORK, 'NUM_PROXIES': num_proxies}


class ClientAddressTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, xff=None, remote="10.0.0.5"):
        extra = {'REMOTE_ADDR': remote}
        if xff is not None:
            extra['HTTP_X_FORWARDED_FOR'] = xff
        return self.factory.get('/', **extra)

    @override_settings(TRUSTED_PROXY_COUNT=0, REST_FRAMEWORK=_rest_framework(0))
    def test_without_a_proxy_the_header_is_ignored(self):
        request = self._request(xff="6.6.6.6")
        self.assertEqual(get_client_ip(request), "10.0.0.5")
        self.assertEqual(AnonRateThrottle().get_ident(request), "10.0.0.5")

    @override_settings(TRUSTED_PROXY_COUNT=1, REST_FRAMEWORK=_rest_framework(1))
    def test_behind_one_proxy_only_the_hop_it_added_is_trusted(self):
        # The client sent "6.6.6.6"; Nginx appended the real peer address.
        request = self._request(xff="6.6.6.6, 203.0.113.9")
        self.assertEqual(get_client_ip(request), "203.0.113.9")
        self.assertEqual(AnonRateThrottle().get_ident(request), "203.0.113.9")

    def test_default_settings_do_not_trust_the_header(self):
        self.assertEqual(settings.REST_FRAMEWORK.get('NUM_PROXIES'), settings.TRUSTED_PROXY_COUNT)
        request = self._request(xff="6.6.6.6")
        self.assertEqual(AnonRateThrottle().get_ident(request), "10.0.0.5")


@override_settings(TRUSTED_PROXY_COUNT=0, REST_FRAMEWORK=_rest_framework(0))
class LoginLockoutScopeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="chair@example.com", full_name="Committee Chair", role="principal", password=PASSWORD,
            is_email_verified=True,
        )
        self.client = APIClient()

    def _login(self, password, ip):
        return self.client.post("/api/auth/login/", {"email": "chair@example.com", "password": password},
                                format="json", REMOTE_ADDR=ip)

    def test_failures_from_one_address_do_not_lock_out_the_owner_elsewhere(self):
        for _ in range(5):
            self._login("wrong-password", "198.51.100.7")
        self.assertEqual(self._login(PASSWORD, "198.51.100.7").status_code, 429)
        self.assertEqual(self._login(PASSWORD, "203.0.113.20").status_code, 200)

    @override_settings(LOGIN_ACCOUNT_LOCKOUT_ATTEMPTS=8)
    def test_account_ceiling_locks_after_failures_from_many_addresses(self):
        for i in range(8):
            self._login("wrong-password", f"192.0.2.{i + 1}")
        self.assertEqual(self._login(PASSWORD, "203.0.113.20").status_code, 429)


@override_settings(TRUSTED_PROXY_COUNT=1, REST_FRAMEWORK=_rest_framework(1),
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AdminAuditAddressTests(TestCase):
    def test_audit_row_records_trusted_address_not_spoofed_one(self):
        head = User.objects.create_user(email="head@example.com", full_name="Head Admin", role="head_admin",
                                        password=PASSWORD)
        client = APIClient()
        client.force_authenticate(user=head)
        response = client.post("/api/v1/admin/users/", {
            "email": "new.admin@example.com", "full_name": "New Admin", "role": "state_admin"},
            format="json", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.9", REMOTE_ADDR="10.0.0.5")
        self.assertIn(response.status_code, (200, 201), response.content[:300])
        row = UserAuditLog.objects.get(action="USER_CREATED", target_user__email="new.admin@example.com")
        self.assertEqual(row.ip_address, "203.0.113.9")


class UnexpectedErrorDisclosureTests(TestCase):
    """S-13: unexpected exceptions are logged, never echoed to the client."""
    SECRET_TEXT = "connection to db-host failed: password=hunter2"

    def test_activation_confirm_hides_internal_error(self):
        from unittest.mock import patch
        from apps.authentication.activation_service import AccountActivationService
        with patch.object(AccountActivationService, 'activate_account', side_effect=RuntimeError(self.SECRET_TEXT)):
            with self.assertLogs('apps.authentication.views', level='ERROR'):
                response = APIClient().post("/api/auth/activate/confirm/", {
                    "token": "t", "password": PASSWORD, "confirmPassword": PASSWORD}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("hunter2", response.content.decode())

    def test_email_verification_confirm_hides_internal_error(self):
        from unittest.mock import patch
        from apps.authentication.email_verification_service import EmailVerificationService
        with patch.object(EmailVerificationService, 'confirm_email_verification',
                          side_effect=RuntimeError(self.SECRET_TEXT)):
            with self.assertLogs('apps.authentication.views', level='ERROR'):
                response = APIClient().post("/api/auth/verify-email/confirm/", {"token": "t"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("hunter2", response.content.decode())


@override_settings(TRUSTED_PROXY_COUNT=0, REST_FRAMEWORK=_rest_framework(0))
class LogoutRevokesAccessTokenTests(TestCase):
    """S-12: after logout the access token used to log out stops working at once, other sessions keep working."""
    def setUp(self):
        cache.clear()
        User.objects.create_user(email="user@example.com", full_name="Some User", role="principal",
                                 password=PASSWORD, is_email_verified=True)

    def _login(self):
        response = APIClient().post("/api/auth/login/", {"email": "user@example.com", "password": PASSWORD},
                                    format="json")
        return response.json()["tokens"]

    def test_access_token_is_rejected_after_logout(self):
        tokens = self._login()
        other_session = self._login()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(client.get("/api/auth/me/").status_code, 200)
        self.assertEqual(client.post("/api/auth/logout/", {"refresh_token": tokens['refresh']},
                                     format="json").status_code, 200)
        self.assertEqual(client.get("/api/auth/me/").status_code, 401)

        other = APIClient()
        other.credentials(HTTP_AUTHORIZATION=f"Bearer {other_session['access']}")
        self.assertEqual(other.get("/api/auth/me/").status_code, 200)


class RefreshRotationRaceTests(TestCase):
    """
    S-17: a refresh token can be exchanged once. A concurrent exchange that read the token before the first one
    revoked it is treated as reuse: no new tokens, and the user's refresh tokens are revoked.
    """
    def test_concurrent_second_exchange_is_refused(self):
        from unittest.mock import patch
        from django.db.models.query import QuerySet
        from apps.authentication.models import RefreshToken
        from apps.authentication.utils import generate_auth_tokens, rotate_refresh_token_header

        user = User.objects.create_user(email="race@example.com", full_name="Race User", role="principal",
                                        password=PASSWORD, is_email_verified=True)
        refresh = generate_auth_tokens(user)['refresh']
        original_get = QuerySet.get

        def stale_get(queryset, *args, **kwargs):
            obj = original_get(queryset, *args, **kwargs)
            if queryset.model is RefreshToken:
                # Another request rotated this token after we read it.
                RefreshToken.objects.filter(pk=obj.pk).update(is_revoked=True)
            return obj

        with patch.object(QuerySet, 'get', stale_get):
            self.assertIsNone(rotate_refresh_token_header(refresh))
        self.assertFalse(RefreshToken.objects.filter(user=user, is_revoked=False).exists())
