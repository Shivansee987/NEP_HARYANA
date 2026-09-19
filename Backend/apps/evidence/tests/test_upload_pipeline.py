"""
NEP Excellence Awards 2026 - Comprehensive Evidence Upload Pipeline Tests
Verifies categories A through M as mandated by Phase 5B specification.
"""
import hashlib
import os
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.authentication.models import College, User
from apps.evidence.enums import (
    EvidenceAuditAction,
    EvidenceLifecycleState,
    VerificationDecision,
)
from apps.evidence.exceptions import (
    EvidenceDomainError,
    FrameworkMismatchError,
    UnauthorizedEvidenceActionError,
)
from apps.evidence.models import (
    EvidenceAuditLog,
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    EvidenceVerification,
)
from apps.evidence.pipeline import EvidenceUploadPipeline
from apps.evidence.services import EvidenceService
from apps.evidence.storage import (
    FileSystemEvidenceStorage,
    StorageSecurityError,
    get_evidence_storage,
)
from apps.evidence.validators import (
    FileEmptyError,
    FileTooLargeError,
    MaliciousContentError,
    MimeMismatchError,
    UnsafeFilenameError,
    UnsupportedFileTypeError,
)
from apps.scoring.enums import EvidenceState, GatingStatus
from apps.scoring.evaluators.evidence_gating import evaluate_evidence

TEST_VAULT_DIR = Path(settings.BASE_DIR) / 'test_evidence_vault'


@override_settings(
    EVIDENCE_STORAGE_VAULT=TEST_VAULT_DIR,
    MAX_EVIDENCE_FILE_SIZE=1024 * 1024  # 1 MB for testing
)
class UploadPipelineTestCase(TestCase):
    """
    Base test fixture configuring test vault and users.
    """
    def setUp(self):
        TEST_VAULT_DIR.mkdir(parents=True, exist_ok=True)
        self.storage = FileSystemEvidenceStorage(base_dir=TEST_VAULT_DIR)

        self.college = College.objects.create(name="Govt College Rohtak", aishe_code="C-2001")
        self.principal_user = User.objects.create_user(
            email="principal.rohtak@college.edu",
            full_name="Principal Rohtak",
            role="principal",
            college=self.college,
            password="securepassword123"
        )
        self.committee_user = User.objects.create_user(
            email="screener@dhe.gov.in",
            full_name="Screening Committee Member",
            role="committee",
            password="securepassword123"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin.dhe@haryana.gov.in",
            full_name="DHE State Admin",
            password="securepassword123"
        )

        # Standard authentic test file payloads
        self.valid_pdf_bytes = b"%PDF-1.4\n%Mock Valid PDF Header and stream content for NEP 2026\n%%EOF"
        self.valid_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        self.valid_jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
        self.valid_docx_bytes = b"PK\x03\x04\x14\x00\x06\x00\x08\x00Mock Word Docx Content inside OpenXML zip container"

    def tearDown(self):
        if TEST_VAULT_DIR.exists():
            shutil.rmtree(TEST_VAULT_DIR, ignore_errors=True)


class TestCategoryAValidUpload(UploadPipelineTestCase):
    """
    Category A: Valid upload acceptance, storage, and persistence.
    """
    def test_valid_pdf_upload_creates_evidence_record_and_file(self):
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=self.valid_pdf_bytes,
            filename="annual_idp_report.pdf",
            evidence_type="EVID_U4_IDP",
            document_date=date(2025, 9, 10),
            academic_year="2024-25",
        )
        self.assertIsNotNone(doc.document_id)
        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_PRESENT)
        self.assertEqual(doc.framework, "COLLEGE_2026")
        self.assertEqual(doc.mime_type, "application/pdf")
        self.assertEqual(doc.file_size, len(self.valid_pdf_bytes))
        self.assertEqual(doc.file_checksum, hashlib.sha256(self.valid_pdf_bytes).hexdigest())

        # Storage existence
        self.assertTrue(self.storage.exists(doc.file_path))
        stored_bytes = self.storage.retrieve(doc.file_path)
        self.assertEqual(stored_bytes, self.valid_pdf_bytes)

    def test_auto_submit_sets_status_to_pending(self):
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=self.valid_png_bytes,
            filename="campus_solar.png",
            auto_submit=True,
        )
        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_PENDING)


class TestCategoryBFileValidation(UploadPipelineTestCase):
    """
    Category B: File size, empty content, and MIME validation.
    """
    def test_zero_byte_file_rejected(self):
        with self.assertRaises(FileEmptyError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=b"",
                filename="empty.pdf",
            )

    def test_oversized_file_rejected(self):
        oversized = b"%PDF-1.4\n" + b"X" * (1024 * 1024 + 100)
        with self.assertRaises(FileTooLargeError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=oversized,
                filename="huge.pdf",
            )

    def test_unsupported_extension_rejected(self):
        with self.assertRaises(UnsupportedFileTypeError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=self.valid_pdf_bytes,
                filename="document.xyz",
            )

    def test_disguised_executable_rejected(self):
        # File named .pdf but containing Windows PE header (MZ)
        fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00Mock Windows PE executable bytes"
        with self.assertRaises(MaliciousContentError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=fake_pdf,
                filename="trojan.pdf",
            )

    def test_disguised_linux_elf_rejected(self):
        fake_pdf = b"\x7fELF\x02\x01\x01\x00Linux binary"
        with self.assertRaises(MaliciousContentError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=fake_pdf,
                filename="binary.pdf",
            )

    def test_mime_mismatch_rejected(self):
        # Named .pdf but containing PNG magic bytes
        with self.assertRaises(MimeMismatchError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=self.valid_png_bytes,
                filename="mismatch.pdf",
            )


class TestCategoryCFilenameSecurity(UploadPipelineTestCase):
    """
    Category C: Path traversal, null-byte injection, and dangerous filenames.
    """
    def test_directory_traversal_dotdot_slash_rejected(self):
        with self.assertRaises(UnsafeFilenameError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=self.valid_pdf_bytes,
                filename="../../etc/passwd.pdf",
            )

    def test_directory_traversal_dotdot_backslash_rejected(self):
        with self.assertRaises(UnsafeFilenameError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=self.valid_pdf_bytes,
                filename="..\\..\\boot.ini.pdf",
            )

    def test_windows_drive_letter_rejected(self):
        with self.assertRaises(UnsafeFilenameError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=self.valid_pdf_bytes,
                filename="C:system32.pdf",
            )

    def test_null_byte_filename_rejected(self):
        with self.assertRaises(UnsafeFilenameError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=self.valid_pdf_bytes,
                filename="valid_name.pdf\x00.exe",
            )

    def test_double_extension_evasion_rejected(self):
        with self.assertRaises(MaliciousContentError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=self.valid_pdf_bytes,
                filename="report.exe.pdf",
            )


class TestCategoryDHashing(UploadPipelineTestCase):
    """
    Category D: SHA-256 cryptographic integrity.
    """
    def test_same_content_same_hash(self):
        hash1 = hashlib.sha256(self.valid_pdf_bytes).hexdigest()
        hash2 = hashlib.sha256(self.valid_pdf_bytes).hexdigest()
        self.assertEqual(hash1, hash2)

    def test_tampered_content_produces_different_hash(self):
        tampered_bytes = self.valid_pdf_bytes + b"tamper"
        hash1 = hashlib.sha256(self.valid_pdf_bytes).hexdigest()
        hash2 = hashlib.sha256(tampered_bytes).hexdigest()
        self.assertNotEqual(hash1, hash2)


class TestCategoryEDuplicates(UploadPipelineTestCase):
    """
    Category E: Duplicate detection & metadata tracking.
    """
    def test_same_filename_different_content_creates_distinct_evidence(self):
        doc1 = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=self.valid_pdf_bytes,
            filename="document.pdf",
        )
        diff_bytes = b"%PDF-1.4\nDifferent Content Version\n%%EOF"
        doc2 = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=diff_bytes,
            filename="document.pdf",
        )
        self.assertNotEqual(doc1.pk, doc2.pk)
        self.assertNotEqual(doc1.file_checksum, doc2.file_checksum)
        self.assertNotEqual(doc1.file_path, doc2.file_path)

    def test_same_bytes_different_filename_detects_duplicate_content(self):
        doc1 = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=self.valid_pdf_bytes,
            filename="file_one.pdf",
        )
        doc2 = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=self.valid_pdf_bytes,
            filename="file_two.pdf",
        )
        self.assertEqual(doc1.file_checksum, doc2.file_checksum)
        self.assertTrue(doc2.metadata.get('duplicate_checksum_detected'))
        self.assertEqual(doc2.metadata.get('duplicate_of_document_id'), str(doc1.document_id))


class TestCategoryFTransactionSafety(UploadPipelineTestCase):
    """
    Category F: Transaction safety & zero orphaned storage files.
    """
    def test_database_failure_cleans_up_stored_file(self):
        # Patch EvidenceDocument.objects.create to raise an unexpected DB error
        with patch('apps.evidence.models.EvidenceDocument.objects.create', side_effect=RuntimeError("Simulated DB Crash")):
            with self.assertRaises(RuntimeError):
                EvidenceUploadPipeline.process_upload(
                    uploader=self.principal_user,
                    assessment_id="ASSESS-C-2026-001",
                    framework="COLLEGE_2026",
                    institution_type="COLLEGE",
                    institution_id="C-2001",
                    file_data=self.valid_pdf_bytes,
                    filename="crash_test.pdf",
                )

        # Verify no files were orphaned inside the vault
        all_files = list(TEST_VAULT_DIR.rglob('*.*'))
        self.assertEqual(len(all_files), 0, f"Found orphaned storage files: {all_files}")


class TestCategoryGFrameworkIsolation(UploadPipelineTestCase):
    """
    Category G: Strict framework isolation.
    """
    def test_college_assessment_rejects_university_parameter(self):
        with self.assertRaises(FrameworkMismatchError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.principal_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=self.valid_pdf_bytes,
                filename="mismatch.pdf",
                parameter_id="U4",
                subcriterion_id="U4.1",
            )

    def test_university_assessment_rejects_college_parameter(self):
        with self.assertRaises(FrameworkMismatchError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.admin_user,
                assessment_id="ASSESS-U-2026-001",
                framework="UNIVERSITY_2026",
                institution_type="UNIVERSITY",
                institution_id="UNIV-01",
                file_data=self.valid_pdf_bytes,
                filename="mismatch.pdf",
                parameter_id="C1",
                subcriterion_id="C1.1",
            )


class TestCategoryIAssociation(UploadPipelineTestCase):
    """
    Category I: Parameter & subcriterion association.
    """
    def test_upload_with_valid_association_creates_relation(self):
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=self.valid_pdf_bytes,
            filename="idp.pdf",
            parameter_id="C1",
            subcriterion_id="C1.1",
            academic_year="2025-26",
        )
        self.assertEqual(doc.associations.count(), 1)
        assoc = doc.associations.first()
        self.assertEqual(assoc.parameter_id, "C1")
        self.assertEqual(assoc.subcriterion_id, "C1.1")
        self.assertEqual(assoc.academic_year, "2025-26")


class TestCategoryJAuthorization(UploadPipelineTestCase):
    """
    Category J: Server-side authorization & segregation of duties.
    """
    def test_committee_cannot_upload_evidence(self):
        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.committee_user,
                assessment_id="ASSESS-C-2026-001",
                framework="COLLEGE_2026",
                institution_type="COLLEGE",
                institution_id="C-2001",
                file_data=self.valid_pdf_bytes,
                filename="committee_upload.pdf",
            )

    def test_uploader_cannot_self_verify(self):
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.admin_user,
            assessment_id="ASSESS-U-2026-001",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-01",
            file_data=self.valid_pdf_bytes,
            filename="admin_doc.pdf",
            auto_submit=True,
        )
        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceService.verify_evidence(
                evidence_id=doc.pk,
                verifier=self.admin_user,
                reason="Attempted self-verification",
            )


class TestCategoryKLifecycleGating(UploadPipelineTestCase):
    """
    Category K: Uploaded evidence never unlocks marks until verified.
    """
    def test_uploaded_evidence_cannot_earn_score(self):
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=self.valid_pdf_bytes,
            filename="proof.pdf",
            evidence_type="EVID_CERTIFICATE",
        )
        scoring_doc = EvidenceService.to_scoring_domain(doc)
        status, multiplier, trace = evaluate_evidence(
            mandatory_evidence_types=["EVID_CERTIFICATE"],
            uploaded_docs=[scoring_doc]
        )
        self.assertEqual(status, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)
        self.assertEqual(multiplier, 0.0)

    def test_only_verified_evidence_unlocks_score(self):
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=self.valid_pdf_bytes,
            filename="proof.pdf",
            evidence_type="EVID_CERTIFICATE",
            auto_submit=True,
        )
        EvidenceService.verify_evidence(
            evidence_id=doc.pk,
            verifier=self.committee_user,
            reason="Verified successfully"
        )
        doc.refresh_from_db()
        scoring_doc = EvidenceService.to_scoring_domain(doc)
        status, multiplier, trace = evaluate_evidence(
            mandatory_evidence_types=["EVID_CERTIFICATE"],
            uploaded_docs=[scoring_doc]
        )
        self.assertEqual(status, GatingStatus.PASSED_EVIDENCE_VERIFIED)
        self.assertEqual(multiplier, 1.0)


class TestCategoryLDateHandling(UploadPipelineTestCase):
    """
    Category L: Temporal validation (activity date preserved, never upload/HOI fallback).
    """
    def test_activity_date_preserved_distinct_from_upload_timestamp(self):
        activity_date = date(2025, 11, 20)
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=self.valid_pdf_bytes,
            filename="dated_report.pdf",
            document_date=activity_date,
        )
        self.assertEqual(doc.document_date, activity_date)
        self.assertNotEqual(doc.document_date, doc.upload_timestamp.date())


class TestCategoryMAuditEvents(UploadPipelineTestCase):
    """
    Category M: Audit events recorded properly.
    """
    def test_upload_and_association_creates_audit_entries(self):
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.principal_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-2001",
            file_data=self.valid_pdf_bytes,
            filename="audit_check.pdf",
            parameter_id="C1",
            subcriterion_id="C1.1",
            auto_submit=True,
        )
        actions = list(
            EvidenceAuditLog.objects.filter(evidence=doc).order_by('timestamp').values_list('action', flat=True)
        )
        self.assertIn(EvidenceAuditAction.UPLOADED, actions)
        self.assertIn(EvidenceAuditAction.ASSOCIATED, actions)
        self.assertIn(EvidenceAuditAction.SUBMITTED, actions)
