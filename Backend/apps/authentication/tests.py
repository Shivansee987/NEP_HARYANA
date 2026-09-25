import json
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from .models import College, RefreshToken
from .utils import generate_access_token, decode_token, hash_token

User = get_user_model()


class JWTAuthTests(APITestCase):
    """
    Tests for the JWT auth endpoints.

    Token delivery protocol: tokens are returned in the JSON response body
    under {'tokens': {'access': '...', 'refresh': '...'}}  — NOT in HTTP
    cookies.  The refresh token is sent in the POST body (not a cookie) when
    calling the /auth/refresh/ and /auth/logout/ endpoints.
    """

    def setUp(self):
        self.college = College.objects.create(name="Test College", aishe_code="C-TEST1")
        self.user_password = "SecurePassword123!"
        self.user = User.objects.create_user(
            email="test@college.edu.in",
            full_name="Dr. Test User",
            role="principal",
            college=self.college,
            password=self.user_password,
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    def _login(self):
        """Return a successful login response."""
        url = reverse("login")
        return self.client.post(
            url,
            {"email": "test@college.edu.in", "password": self.user_password},
            format="json",
        )

    # ── signup ────────────────────────────────────────────────────────────────

    def test_signup(self):
        url = reverse("signup")
        data = {
            "fullName": "New User",
            "email": "newuser@college.edu.in",
            "collegeId": self.college.id,
            "role": "principal",
            "password": "Password123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        # Tokens are in the JSON body under the 'tokens' key
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

    # ── login ─────────────────────────────────────────────────────────────────

    def test_login_success(self):
        response = self._login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

        # Refresh token must be persisted (hashed) in the database
        rf_token = response.data["tokens"]["refresh"]
        hashed = hash_token(rf_token)
        self.assertTrue(RefreshToken.objects.filter(token=hashed).exists())

    def test_login_invalid_credentials(self):
        url = reverse("login")
        response = self.client.post(
            url,
            {"email": "test@college.edu.in", "password": "WrongPassword"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("tokens", response.data)

    # ── token refresh ─────────────────────────────────────────────────────────

    def test_refresh_token_success(self):
        login_response = self._login()
        refresh_token = login_response.data["tokens"]["refresh"]

        # Send refresh_token in the request body (body-based protocol)
        refresh_url = reverse("refresh")
        response = self.client.post(
            refresh_url, {"refresh_token": refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

        # The old refresh token must be revoked after rotation
        old_hashed = hash_token(refresh_token)
        old_db_token = RefreshToken.objects.get(token=old_hashed)
        self.assertTrue(old_db_token.is_revoked)

    def test_refresh_token_revocation_on_reuse(self):
        """Reusing a rotated refresh token must be rejected (HTTP 410)."""
        login_response = self._login()
        refresh_token = login_response.data["tokens"]["refresh"]

        refresh_url = reverse("refresh")
        # Use the token once — it gets rotated
        self.client.post(
            refresh_url, {"refresh_token": refresh_token}, format="json"
        )

        # Attempt reuse of the now-revoked token
        response = self.client.post(
            refresh_url, {"refresh_token": refresh_token}, format="json"
        )
        # View returns HTTP 410 Gone for an invalid/reused refresh token
        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    # ── /me endpoint ──────────────────────────────────────────────────────────

    def test_me_endpoint_authenticated(self):
        login_response = self._login()
        access_token = login_response.data["tokens"]["access"]

        me_url = reverse("me")
        response = self.client.get(
            me_url, HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "test@college.edu.in")

    def test_me_endpoint_unauthenticated(self):
        me_url = reverse("me")
        response = self.client.get(me_url)
        # No token provided — must be rejected
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    # ── logout ────────────────────────────────────────────────────────────────

    def test_logout(self):
        login_response = self._login()
        refresh_token = login_response.data["tokens"]["refresh"]

        logout_url = reverse("logout")
        response = self.client.post(
            logout_url, {"refresh_token": refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh token in DB must be revoked after logout
        hashed = hash_token(refresh_token)
        db_token = RefreshToken.objects.get(token=hashed)
        self.assertTrue(db_token.is_revoked)
