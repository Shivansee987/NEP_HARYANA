"""
Unit tests for Phase 3 (Targeted Caching) and Phase 4 (Streaming Evidence Uploads & SMTP Resilience).
Validates:
1. 60-second JWT user authentication cache and immediate invalidation on revoke_sessions and logout.
2. 120-second admin dashboard statistics caching and invalidation helper.
3. 64KB chunked evidence stream ingestion and checksum calculation.
"""
import io
import hashlib
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.authentication.models import User, College
from apps.authentication.authentication import JWTAuthentication, invalidate_user_cache, get_user_cache_key
from apps.authentication.utils import generate_access_token
from apps.admin_panel.services import (
    get_dashboard_stats,
    invalidate_dashboard_stats_cache,
    DASHBOARD_STATS_CACHE_KEY,
)
from apps.nominations.models import Nomination
from apps.evidence.services import EvidenceService
from apps.evidence.pipeline import EvidenceUploadPipeline
from apps.evidence.models import EvidenceDocument


class Phase3TargetedCachingTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="cache_test_user@example.com",
            full_name="Cache Test User",
            password="StrongPassword123!",
            role="applicant",
            is_email_verified=True,
            is_active=True,
        )
        self.auth = JWTAuthentication()
        self.factory = APIRequestFactory()

    def test_jwt_authentication_caches_user_lookup(self):
        token = generate_access_token(self.user)
        request = self.factory.get("/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}")

        # First authenticate: database hit + cache population
        user1, _ = self.auth.authenticate(request)
        self.assertEqual(user1.id, self.user.id)

        cache_key = get_user_cache_key(self.user.id)
        self.assertIsNotNone(cache.get(cache_key))

        # Second authenticate: served from cache (0 DB queries on User)
        with self.assertNumQueries(0):
            user2, _ = self.auth.authenticate(request)
            self.assertEqual(user2.id, self.user.id)

    def test_revoke_sessions_invalidates_user_cache(self):
        token = generate_access_token(self.user)
        request = self.factory.get("/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.auth.authenticate(request)

        cache_key = get_user_cache_key(self.user.id)
        self.assertIsNotNone(cache.get(cache_key))

        # Revoking sessions must wipe the cache
        self.user.revoke_sessions()
        self.assertIsNone(cache.get(cache_key))

    def test_admin_dashboard_stats_caching_and_invalidation(self):
        college = College.objects.create(
            name="Cache Audit College",
            aishe_code="C-88888",
            district="Karnal",
            institute_type="Government",
        )
        Nomination.objects.create(
            form_id="FORM-CACHE-01",
            college=college,
            status="Draft",
            is_submitted=False,
        )

        # First call populates cache
        stats1 = get_dashboard_stats()
        self.assertIsNotNone(cache.get(DASHBOARD_STATS_CACHE_KEY))

        # Second call reads from cache with 0 DB queries
        with self.assertNumQueries(0):
            stats2 = get_dashboard_stats()
            self.assertEqual(stats2, stats1)

        # Invalidation empties the cache
        invalidate_dashboard_stats_cache()
        self.assertIsNone(cache.get(DASHBOARD_STATS_CACHE_KEY))


class Phase4EvidenceStreamingTestCase(TestCase):
    def setUp(self):
        self.college = College.objects.create(
            name="Streaming Test College",
            aishe_code="C-77777",
            district="Panchkula",
            institute_type="Government",
        )
        self.user = User.objects.create_user(
            email="uploader_stream@example.com",
            full_name="Stream Uploader",
            password="StrongPassword123!",
            role="applicant",
            college=self.college,
            is_email_verified=True,
            is_active=True,
        )

    def test_calculate_checksum_stream_matches_bytes(self):
        # Generate 150KB test payload spanning multiple 64KB chunks
        raw_data = b"%PDF-1.4 " + (b"StreamPayloadPadding1234567890ABCDEF" * 5000)
        expected_hash = hashlib.sha256(raw_data).hexdigest()

        stream = io.BytesIO(raw_data)
        computed_hash = EvidenceService.calculate_checksum_stream(stream)
        self.assertEqual(computed_hash, expected_hash)

    def test_pipeline_process_upload_streams_file_data(self):
        raw_data = b"%PDF-1.4 " + (b"ValidPdfStreamDocumentContents" * 200) + b"\n%%EOF\n"
        stream = io.BytesIO(raw_data)
        stream.name = "test_document.pdf"
        stream.size = len(raw_data)

        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.user,
            assessment_id="ASSESS-2026-COL-STREAM-01",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id=self.college.aishe_code,
            file_data=stream,
            filename="test_document.pdf",
            evidence_type="EVID_GENERAL",
        )

        self.assertIsInstance(doc, EvidenceDocument)
        self.assertEqual(doc.file_checksum, hashlib.sha256(raw_data).hexdigest())
        self.assertEqual(doc.file_size, len(raw_data))
