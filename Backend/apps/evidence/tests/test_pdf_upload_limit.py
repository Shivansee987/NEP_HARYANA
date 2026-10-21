"""
test_pdf_upload_limit.py
Tests verifying the 5 MB (5,242,880 bytes) PDF upload limit across the backend pipeline and validators.
Covers:
1. Valid PDF smaller than 5 MB is accepted.
2. Valid PDF of exactly 5 MB (5,242,880 bytes) is accepted.
3. PDF exceeding 5 MB by 1 byte (5,242,881 bytes) is rejected with FileTooLargeError.
4. Significantly oversized PDF (10 MB) is rejected.
5. Non-PDF file renamed as .pdf is rejected (fails magic bytes '%PDF-').
6. Missing / empty file (0 bytes) is rejected with FileEmptyError.
7. Truncated PDF missing %%EOF trailer is rejected with MalformedFileError.
8. Rejected files do not leave persisted files or temporary artifacts in storage vault.
9. HTTP REST API returns 413 Payload Too Large when receiving oversized PDF.
"""
import io
import shutil
from pathlib import Path
from django.conf import settings
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.authentication.models import User, College
from apps.evidence.models import EvidenceDocument
from apps.evidence.pipeline import EvidenceUploadPipeline
from apps.evidence.storage import FileSystemEvidenceStorage
from apps.evidence.validators import (
    ContentValidator,
    FileTooLargeError,
    FileEmptyError,
    MimeMismatchError,
    MalformedFileError,
    MaliciousContentError,
)
from apps.evidence.api.views import EvidenceListCreateView
from apps.nominations.views import NominationEvidenceUploadView

TEST_VAULT_DIR = Path(settings.BASE_DIR) / 'test_pdf_limit_vault'


def make_dummy_pdf_bytes(size_bytes: int) -> bytes:
    """Creates byte buffer with genuine %PDF-1.4 header and %%EOF trailer."""
    header = b"%PDF-1.4\n"
    trailer = b"\n%%EOF"
    if size_bytes < len(header) + len(trailer):
        return header + trailer
    filler_len = size_bytes - len(header) - len(trailer)
    return header + (b"A" * filler_len) + trailer


@override_settings(
    EVIDENCE_STORAGE_VAULT=TEST_VAULT_DIR,
    MAX_PDF_FILE_SIZE=5 * 1024 * 1024,  # 5,242,880 bytes strict
    MAX_EVIDENCE_FILE_SIZE=25 * 1024 * 1024,
)
class PdfUploadLimitTestCase(TestCase):
    def setUp(self):
        TEST_VAULT_DIR.mkdir(parents=True, exist_ok=True)
        self.storage = FileSystemEvidenceStorage(base_dir=TEST_VAULT_DIR)

        self.college = College.objects.create(name="Govt PG College Panchkula", aishe_code="C-5001")
        self.principal = User.objects.create_user(
            email="principal.panchkula@college.edu",
            full_name="Principal Panchkula",
            role="principal",
            college=self.college,
            password="securepassword123"
        )
        self.assessment_id = "ASSESS-TEST-COLLEGE-2026-5001"
        self._seed_assessment()

    def tearDown(self):
        if TEST_VAULT_DIR.exists():
            shutil.rmtree(TEST_VAULT_DIR, ignore_errors=True)

    def _seed_assessment(self):
        from apps.college.models import CollegeAssessment
        CollegeAssessment.objects.filter(assessment_id=self.assessment_id).delete()
        CollegeAssessment.objects.create(
            assessment_id=self.assessment_id,
            academic_year="2025-26",
            college=self.college,
            status="DRAFT",
        )

    def test_01_valid_pdf_smaller_than_5mb_accepted(self):
        """1. A valid PDF smaller than 5 MB is accepted and persisted."""
        content = make_dummy_pdf_bytes(1024 * 50)  # 50 KB
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.principal,
            assessment_id=self.assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-5001",
            file_data=content,
            filename="valid_small.pdf",
            evidence_type="EVID_C1_APPROVED_IDP",
            parameter_id="C1",
            subcriterion_id="C1.1",
        )
        self.assertIsNotNone(doc.pk)
        self.assertEqual(doc.file_size, 1024 * 50)
        self.assertTrue(self.storage.exists(doc.file_path))

    def test_02_valid_pdf_exactly_5mb_accepted(self):
        """2. A valid PDF of exactly 5 MB (5,242,880 bytes) is accepted."""
        content = make_dummy_pdf_bytes(5 * 1024 * 1024)
        self.assertEqual(len(content), 5242880)

        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.principal,
            assessment_id=self.assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-5001",
            file_data=content,
            filename="boundary_5mb.pdf",
            evidence_type="EVID_C1_APPROVED_IDP",
            parameter_id="C1",
            subcriterion_id="C1.1",
        )
        self.assertIsNotNone(doc.pk)
        self.assertEqual(doc.file_size, 5242880)
        self.assertTrue(self.storage.exists(doc.file_path))

    def test_03_pdf_exceeding_5mb_by_one_byte_rejected(self):
        """3. A PDF larger than 5 MB by exactly one byte (5,242,881 bytes) is rejected."""
        content = make_dummy_pdf_bytes(5 * 1024 * 1024 + 1)
        self.assertEqual(len(content), 5242881)

        with self.assertRaises(FileTooLargeError) as ctx:
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal,
                assessment_id=self.assessment_id,
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-5001",
                file_data=content,
                filename="exceeded_one_byte.pdf",
                evidence_type="EVID_C1_APPROVED_IDP",
                parameter_id="C1",
                subcriterion_id="C1.1",
            )
        self.assertIn("exceeds the strict 5 MB limit", str(ctx.exception))

    def test_04_significantly_oversized_pdf_rejected(self):
        """4. A significantly oversized PDF (10 MB) is rejected."""
        content = make_dummy_pdf_bytes(10 * 1024 * 1024)
        with self.assertRaises(FileTooLargeError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal,
                assessment_id=self.assessment_id,
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-5001",
                file_data=content,
                filename="oversized_10mb.pdf",
                evidence_type="EVID_C1_APPROVED_IDP",
                parameter_id="C1",
                subcriterion_id="C1.1",
            )

    def test_05_non_pdf_renamed_as_pdf_rejected_by_magic_bytes(self):
        """5. A non-PDF file renamed with .pdf extension is rejected by magic byte inspection."""
        fake_payload = b"MZ\x90\x00\x03\x00\x00\x00ExecutableWindowsBinaryFakeData"
        with self.assertRaises((MimeMismatchError, MaliciousContentError)):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal,
                assessment_id=self.assessment_id,
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-5001",
                file_data=fake_payload,
                filename="disguised_exe.pdf",
                evidence_type="EVID_C1_APPROVED_IDP",
                parameter_id="C1",
                subcriterion_id="C1.1",
            )

    def test_06_empty_pdf_rejected(self):
        """6. A zero-byte file is rejected with FileEmptyError."""
        with self.assertRaises(FileEmptyError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal,
                assessment_id=self.assessment_id,
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-5001",
                file_data=b"",
                filename="empty.pdf",
                evidence_type="EVID_C1_APPROVED_IDP",
                parameter_id="C1",
                subcriterion_id="C1.1",
            )

    def test_07_pdf_missing_eof_trailer_rejected(self):
        """7. A corrupted PDF missing the %%EOF trailer marker is rejected."""
        broken_content = b"%PDF-1.4\nSome random content without eof marker"
        with self.assertRaises(MalformedFileError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal,
                assessment_id=self.assessment_id,
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-5001",
                file_data=broken_content,
                filename="corrupted.pdf",
                evidence_type="EVID_C1_APPROVED_IDP",
                parameter_id="C1",
                subcriterion_id="C1.1",
            )

    def test_08_rejected_files_leave_no_artifacts(self):
        """8. Rejected uploads do not leave persisted files or temporary artifacts in storage."""
        oversized = make_dummy_pdf_bytes(6 * 1024 * 1024)

        with self.assertRaises(FileTooLargeError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal,
                assessment_id=self.assessment_id,
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-5001",
                file_data=oversized,
                filename="rejected_persist_test.pdf",
                evidence_type="EVID_C1_APPROVED_IDP",
                parameter_id="C1",
                subcriterion_id="C1.1",
            )

        # Confirm no EvidenceDocument was created
        self.assertFalse(EvidenceDocument.objects.filter(original_filename="rejected_persist_test.pdf").exists())
        # Confirm directory state has no new files
        current_file_count = len([f for f in TEST_VAULT_DIR.rglob('*') if f.is_file()])
        self.assertEqual(current_file_count, 0)

    def test_09_api_endpoint_returns_413_for_oversized_pdf(self):
        """9. REST API returns HTTP 413 Payload Too Large when receiving an oversized PDF."""
        factory = APIRequestFactory()
        view = EvidenceListCreateView.as_view()

        oversized_content = make_dummy_pdf_bytes(5 * 1024 * 1024 + 100)
        upload_file = SimpleUploadedFile(
            "oversized_api.pdf",
            oversized_content,
            content_type="application/pdf"
        )

        request = factory.post(
            '/api/evidence/',
            {
                'file': upload_file,
                'assessment_id': self.assessment_id,
                'framework': 'COLLEGE_2026',
                'institution_type': 'COLLEGE',
                'evidence_type': 'EVID_C1_APPROVED_IDP',
                'parameter_id': 'C1',
                'subcriterion_id': 'C1.1',
            },
            format='multipart'
        )
        force_authenticate(request, user=self.principal)

        response = view(request)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.data.get('error'), 'file_too_large')
        self.assertIn('exceeds the strict 5 MB limit', response.data.get('detail', ''))

    def test_10_nomination_upload_rejects_oversized_pdf_before_cloud_storage(self):
        """The legacy nomination upload cannot bypass server-side PDF size validation."""
        factory = APIRequestFactory()
        upload_file = SimpleUploadedFile(
            "oversized_nomination.pdf",
            make_dummy_pdf_bytes(5 * 1024 * 1024 + 1),
            content_type="application/pdf",
        )
        request = factory.post('/api/nominations/upload/', {'file': upload_file}, format='multipart')
        force_authenticate(request, user=self.principal)

        response = NominationEvidenceUploadView.as_view()(request)

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.data.get('error'), 'file_too_large')
        self.assertIn('must not exceed 5 MB', response.data.get('detail', ''))
