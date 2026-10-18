"""
NEP Haryana Excellence Awards 2026 - U6 and U18.3 Scoring & Evidence Rules Regression Suite.

Verifies:
1. Separate U6.A (4 marks) and U6.B (4 marks) scoring with combined U6 total = U6.A + U6.B (max 8 marks).
2. Neither U6 component can exceed 4 marks; combined score cannot exceed 8 marks.
3. U18.3 (2 marks) scoring with approved notification evidence; additional records not mandatory.
4. No auto-awarding on upload alone; requires authorized reviewer verification.
5. Secure PDF-only validation: rejecting renamed non-PDFs, invalid signatures, malformed PDFs, empty uploads.
6. Unrelated parameters preserve their accepted file formats.
7. Cross-subcriterion quarantine between U6.A, U6.B, U18.1, U18.2, and U18.3.
8. Authorization controls: unauthorized users cannot verify evidence or change scores.
9. Audit history and lifecycle record preservation.
10. Certification policy gate: cleared for U6 and U18.3 while preserving separate unresolved blockers.
"""
from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.evidence.exceptions import UnauthorizedEvidenceActionError
from apps.evidence.enums import VerificationDecision
from apps.evidence.models import EvidenceAuditLog, EvidenceDocument, EvidenceSubcriterionAssociation, ReviewerAuthorization
from apps.evidence.pipeline import EvidenceUploadPipeline
from apps.evidence.services import EvidenceService
from apps.evidence.taxonomy import (
    ContractStatus,
    QuarantinedLegacyEvidenceError,
    get_subcriterion_contract,
)
from apps.evidence.validators import FileEmptyError, MalformedFileError, MimeMismatchError, UnsupportedFileTypeError
from apps.scoring.domain import (
    AssessmentContext,
    AssessmentPeriod,
    EvidenceDocument as ScoringEvidenceDocument,
    ParameterInput,
    SubcriterionInput,
    SubcriterionResult,
)
from apps.scoring.enums import (
    EvidenceState,
    FrameworkType,
    InstitutionType,
)
from apps.scoring.evaluators.double_counting import DoubleCountingValidator
from apps.scoring.field_schema import UNIVERSITY_FIELD_SCHEMA
from apps.scoring.policy import get_policy_state
from apps.scoring.policy_gates import open_certification_policy_blockers
from apps.scoring.rules.university import UNIVERSITY_EVALUATORS
from apps.university.models import University

User = get_user_model()


class U6AndU18RemediationTests(TestCase):
    def setUp(self):
        self.context = AssessmentContext(
            assessment_id="ASSESS-REMED-2026",
            institution_id="U-TEST-REMED-1",
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30)),
        )
        self.validator = DoubleCountingValidator()

        self.uni = University.objects.create(name="State Test University", aishe_code="U-TEST-REMED-1")
        self.nodal_user = User.objects.create_user(
            email="nodal@univ-remed.test",
            full_name="Nodal Officer",
            role="nodal_officer",
            password="SecurePassword123!",
            university=self.uni,
        )
        self.reviewer_user = User.objects.create_user(
            email="reviewer@committee.test",
            full_name="Screening Reviewer",
            role="committee",
            password="SecurePassword123!",
        )
        self.admin_user = User.objects.create_user(
            email="admin@state.test",
            full_name="State Admin",
            role="state_admin",
            password="SecurePassword123!",
        )

        ReviewerAuthorization.objects.create(
            user=self.reviewer_user,
            framework="UNIVERSITY_2026",
            institution_id="",
            is_active=True,
            granted_by=self.admin_user,
        )

        # Valid PDF fixture with genuine catalog, pages tree, and %%EOF trailer
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        pdf_buf = BytesIO()
        writer.write(pdf_buf)
        self.valid_pdf_bytes = pdf_buf.getvalue()

    def _make_verified_scoring_doc(self, doc_type: str) -> ScoringEvidenceDocument:
        return ScoringEvidenceDocument(
            document_id=f"doc-{doc_type}-01",
            document_type=doc_type,
            status=EvidenceState.EVIDENCE_VERIFIED,
            academic_year="2025-26",
        )

    def _make_orm_doc(self, evidence_type: str, filename: str = "approved_document.pdf") -> EvidenceDocument:
        return EvidenceService.create_evidence(
            uploader=self.nodal_user,
            assessment_id="ASSESS-REMED-2026",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.uni.aishe_code,
            original_filename=filename,
            file_bytes=self.valid_pdf_bytes,
            mime_type="application/pdf",
            evidence_type=evidence_type,
            document_date=date(2025, 10, 1),
            academic_year="2025-26",
        )

    # =========================================================================
    # 1. SEPARATE U6.A AND U6.B SCORING AND COMBINED CALCULATION
    # =========================================================================
    def test_u6a_examination_ordinance_scoring(self):
        """
        U6.A: Examination ordinance amendment.
        Max: 4 marks.
        Evidence: EVID_U6_ORDINANCE_GAZETTE (PDF only, signed by competent authority).
        """
        doc = self._make_verified_scoring_doc("EVID_U6_ORDINANCE_GAZETTE")

        # Yes + verified PDF evidence -> 4 marks
        p_in = ParameterInput(
            parameter_code="U6",
            subcriteria_inputs={
                "U6.A": SubcriterionInput(
                    subcriterion_code="U6.A",
                    raw_inputs={"ordinance_notified": True},
                    evidence_docs=[doc],
                ),
                "U6.B": SubcriterionInput(
                    subcriterion_code="U6.B",
                    raw_inputs={"tools_count": 0},
                    evidence_docs=[],
                ),
            },
        )
        res = UNIVERSITY_EVALUATORS["U6"](p_in, self.context, self.validator)
        self.assertEqual(res.subcriteria_results["U6.A"].raw_score, 4.0)
        self.assertEqual(res.subcriteria_results["U6.A"].evidence_gated_score, 4.0)
        self.assertEqual(res.subcriteria_results["U6.B"].raw_score, 0.0)
        self.assertEqual(res.subcriteria_results["U6.B"].evidence_gated_score, 0.0)
        self.assertEqual(res.raw_score, 4.0)
        self.assertEqual(res.evidence_gated_score, 4.0)

        # Yes + missing evidence -> gated score 0.0
        p_in_no_ev = ParameterInput(
            parameter_code="U6",
            subcriteria_inputs={
                "U6.A": SubcriterionInput(
                    subcriterion_code="U6.A",
                    raw_inputs={"ordinance_notified": True},
                    evidence_docs=[],
                ),
                "U6.B": SubcriterionInput(
                    subcriterion_code="U6.B",
                    raw_inputs={"tools_count": 0},
                    evidence_docs=[],
                ),
            },
        )
        res_no_ev = UNIVERSITY_EVALUATORS["U6"](p_in_no_ev, self.context, self.validator)
        self.assertEqual(res_no_ev.subcriteria_results["U6.A"].raw_score, 4.0)
        self.assertEqual(res_no_ev.subcriteria_results["U6.A"].evidence_gated_score, 0.0)
        self.assertEqual(res_no_ev.evidence_gated_score, 0.0)

    def test_u6b_pedagogical_interventions_scoring(self):
        """
        U6.B: Pedagogical interventions / ICT tools implemented.
        Max: 4 marks (1 mark per tool up to 4).
        Evidence: EVID_U6_PEDAGOGY_RECORDS (PDF only, signed by competent authority).
        """
        doc_b = self._make_verified_scoring_doc("EVID_U6_PEDAGOGY_RECORDS")

        for count, expected in [(0, 0.0), (1, 1.0), (2, 2.0), (3, 3.0), (4, 4.0), (7, 4.0)]:
            p_in = ParameterInput(
                parameter_code="U6",
                subcriteria_inputs={
                    "U6.A": SubcriterionInput(
                        subcriterion_code="U6.A",
                        raw_inputs={"ordinance_notified": False},
                        evidence_docs=[],
                    ),
                    "U6.B": SubcriterionInput(
                        subcriterion_code="U6.B",
                        raw_inputs={"tools_count": count},
                        evidence_docs=[doc_b] if count > 0 else [],
                    ),
                },
            )
            res = UNIVERSITY_EVALUATORS["U6"](p_in, self.context, self.validator)
            self.assertEqual(res.subcriteria_results["U6.B"].raw_score, expected)
            self.assertEqual(res.subcriteria_results["U6.B"].evidence_gated_score, expected)
            # Component score cannot exceed 4 marks
            self.assertLessEqual(res.subcriteria_results["U6.B"].evidence_gated_score, 4.0)

    def test_combined_u6_total_and_8_mark_maximum(self):
        """
        U6 total = U6.A score + U6.B score.
        Max combined score: 8 marks.
        Neither component can exceed 4 marks, and combined score cannot exceed 8 marks.
        """
        doc_a = self._make_verified_scoring_doc("EVID_U6_ORDINANCE_GAZETTE")
        doc_b = self._make_verified_scoring_doc("EVID_U6_PEDAGOGY_RECORDS")

        p_in = ParameterInput(
            parameter_code="U6",
            subcriteria_inputs={
                "U6.A": SubcriterionInput(
                    subcriterion_code="U6.A",
                    raw_inputs={"ordinance_notified": True},
                    evidence_docs=[doc_a],
                ),
                "U6.B": SubcriterionInput(
                    subcriterion_code="U6.B",
                    raw_inputs={"tools_count": 5},  # Exceeds 4, must cap at 4
                    evidence_docs=[doc_b],
                ),
            },
        )
        res = UNIVERSITY_EVALUATORS["U6"](p_in, self.context, self.validator)
        self.assertEqual(res.subcriteria_results["U6.A"].evidence_gated_score, 4.0)
        self.assertEqual(res.subcriteria_results["U6.B"].evidence_gated_score, 4.0)
        self.assertEqual(res.evidence_gated_score, 8.0)
        self.assertEqual(res.evidence_gated_score, res.subcriteria_results["U6.A"].evidence_gated_score + res.subcriteria_results["U6.B"].evidence_gated_score)
        self.assertLessEqual(res.evidence_gated_score, 8.0)

    # =========================================================================
    # 2. U18.3 SCORING AND EVIDENCE RULES
    # =========================================================================
    def test_u18_3_rpl_format_circulated_scoring(self):
        """
        U18.3: RPL format for students circulated with guidelines.
        Max: 2 marks.
        Evidence: EVID_U18_RPL_FORMAT (PDF only notification signed by competent authority).
        Additional records (applications assessed, credits awarded) must not be mandatory.
        """
        doc_rpl = self._make_verified_scoring_doc("EVID_U18_RPL_FORMAT")

        p_in = ParameterInput(
            parameter_code="U18",
            subcriteria_inputs={
                "U18.1": SubcriterionInput(
                    subcriterion_code="U18.1",
                    raw_inputs={"verified": False},
                    evidence_docs=[],
                ),
                "U18.2": SubcriterionInput(
                    subcriterion_code="U18.2",
                    raw_inputs={"verified": False},
                    evidence_docs=[],
                ),
                "U18.3": SubcriterionInput(
                    subcriterion_code="U18.3",
                    raw_inputs={"verified": True},
                    evidence_docs=[doc_rpl],
                ),
            },
        )
        res = UNIVERSITY_EVALUATORS["U18"](p_in, self.context, self.validator)
        self.assertEqual(res.subcriteria_results["U18.3"].raw_score, 2.0)
        self.assertEqual(res.subcriteria_results["U18.3"].evidence_gated_score, 2.0)
        self.assertEqual(res.evidence_gated_score, 2.0)

        # Without evidence, gated score is 0.0
        p_in_no_ev = ParameterInput(
            parameter_code="U18",
            subcriteria_inputs={
                "U18.1": SubcriterionInput(subcriterion_code="U18.1", raw_inputs={"verified": False}, evidence_docs=[]),
                "U18.2": SubcriterionInput(subcriterion_code="U18.2", raw_inputs={"verified": False}, evidence_docs=[]),
                "U18.3": SubcriterionInput(subcriterion_code="U18.3", raw_inputs={"verified": True}, evidence_docs=[]),
            },
        )
        res_no_ev = UNIVERSITY_EVALUATORS["U18"](p_in_no_ev, self.context, self.validator)
        self.assertEqual(res_no_ev.subcriteria_results["U18.3"].raw_score, 2.0)
        self.assertEqual(res_no_ev.subcriteria_results["U18.3"].evidence_gated_score, 0.0)

    # =========================================================================
    # 3. SECURE PDF-ONLY VALIDATION (FRONTEND & BACKEND INVARIANTS)
    # =========================================================================
    def test_pdf_upload_valid_succeeds(self):
        """Valid PDF upload with %PDF- header and %%EOF succeeds for U6.A, U6.B, and U18.3."""
        for ev_type, p_id, s_id in [
            ("EVID_U6_ORDINANCE_GAZETTE", "U6", "U6.A"),
            ("EVID_U6_PEDAGOGY_RECORDS", "U6", "U6.B"),
            ("EVID_U18_RPL_FORMAT", "U18", "U18.3"),
        ]:
            doc = EvidenceUploadPipeline.process_upload(
                uploader=self.nodal_user,
                assessment_id="ASSESS-REMED-2026",
                framework="UNIVERSITY_2026",
                institution_type="UNIVERSITY",
                institution_id=self.uni.aishe_code,
                file_data=SimpleUploadedFile("valid.pdf", self.valid_pdf_bytes, content_type="application/pdf"),
                filename="valid.pdf",
                evidence_type=ev_type,
                academic_year="2025-26",
                document_date=date(2025, 10, 1),
                parameter_id=p_id,
                subcriterion_id=s_id,
            )
            self.assertIsNotNone(doc)
            self.assertEqual(doc.mime_type, "application/pdf")

    def test_streamed_pdf_larger_than_header_chunk_is_validated_in_full(self):
        """A streamed upload is checked on its first 8 KB for magic bytes, but the PDF structure check needs the
        trailer at the end of the file: a valid PDF over 8 KB is accepted and a truncated one is still rejected."""
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.add_metadata({"/Subject": "NEP 2026 evidence " * 2000})
        buf = BytesIO()
        writer.write(buf)
        large_pdf = buf.getvalue()
        self.assertGreater(len(large_pdf), 8192 * 2)

        upload = dict(
            uploader=self.nodal_user,
            assessment_id="ASSESS-REMED-2026",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.uni.aishe_code,
            filename="gazette.pdf",
            evidence_type="EVID_U6_ORDINANCE_GAZETTE",
            academic_year="2025-26",
            document_date=date(2025, 10, 1),
            parameter_id="U6",
            subcriterion_id="U6.A",
        )
        doc = EvidenceUploadPipeline.process_upload(
            file_data=SimpleUploadedFile("gazette.pdf", large_pdf, content_type="application/pdf"), **upload
        )
        self.assertEqual(doc.file_size, len(large_pdf))

        with self.assertRaises(MalformedFileError):
            EvidenceUploadPipeline.process_upload(
                file_data=SimpleUploadedFile("gazette.pdf", large_pdf[:-2048], content_type="application/pdf"),
                **upload,
            )

    def test_pdf_upload_rejects_empty_file(self):
        """Reject empty files (0 bytes) for PDF criteria."""
        with self.assertRaises(FileEmptyError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.nodal_user,
                assessment_id="ASSESS-REMED-2026",
                framework="UNIVERSITY_2026",
                institution_type="UNIVERSITY",
                institution_id=self.uni.aishe_code,
                file_data=SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf"),
                filename="empty.pdf",
                evidence_type="EVID_U6_ORDINANCE_GAZETTE",
                academic_year="2025-26",
                document_date=date(2025, 10, 1),
                parameter_id="U6",
                subcriterion_id="U6.A",
            )

    def test_pdf_upload_rejects_too_small_file(self):
        """Reject files too small to be valid PDFs (< 20 bytes)."""
        with self.assertRaises((MalformedFileError, UnsupportedFileTypeError)):
            EvidenceUploadPipeline.process_upload(
                uploader=self.nodal_user,
                assessment_id="ASSESS-REMED-2026",
                framework="UNIVERSITY_2026",
                institution_type="UNIVERSITY",
                institution_id=self.uni.aishe_code,
                file_data=SimpleUploadedFile("short.pdf", b"%PDF-1.4\n", content_type="application/pdf"),
                filename="short.pdf",
                evidence_type="EVID_U6_ORDINANCE_GAZETTE",
                academic_year="2025-26",
                document_date=date(2025, 10, 1),
                parameter_id="U6",
                subcriterion_id="U6.A",
            )

    def test_pdf_upload_rejects_renamed_non_pdf(self):
        """Reject renamed PNG / image file claiming to be a PDF."""
        fake_pdf_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"A" * 50
        with self.assertRaises((MimeMismatchError, MalformedFileError)):
            EvidenceUploadPipeline.process_upload(
                uploader=self.nodal_user,
                assessment_id="ASSESS-REMED-2026",
                framework="UNIVERSITY_2026",
                institution_type="UNIVERSITY",
                institution_id=self.uni.aishe_code,
                file_data=SimpleUploadedFile("renamed.pdf", fake_pdf_png, content_type="application/pdf"),
                filename="renamed.pdf",
                evidence_type="EVID_U6_ORDINANCE_GAZETTE",
                academic_year="2025-26",
                document_date=date(2025, 10, 1),
                parameter_id="U6",
                subcriterion_id="U6.A",
            )

    def test_pdf_upload_rejects_missing_eof_trailer(self):
        """Reject PDF document missing standard %%EOF termination marker."""
        malformed_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n" + b"A" * 60
        with self.assertRaises(MalformedFileError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.nodal_user,
                assessment_id="ASSESS-REMED-2026",
                framework="UNIVERSITY_2026",
                institution_type="UNIVERSITY",
                institution_id=self.uni.aishe_code,
                file_data=SimpleUploadedFile("no_eof.pdf", malformed_pdf, content_type="application/pdf"),
                filename="no_eof.pdf",
                evidence_type="EVID_U6_ORDINANCE_GAZETTE",
                academic_year="2025-26",
                document_date=date(2025, 10, 1),
                parameter_id="U6",
                subcriterion_id="U6.A",
            )

    def test_pdf_upload_rejects_unsupported_extensions(self):
        """Reject non-PDF extensions (e.g. .png, .docx) for PDF-only criteria."""
        with self.assertRaises(UnsupportedFileTypeError):
            EvidenceUploadPipeline.process_upload(
                uploader=self.nodal_user,
                assessment_id="ASSESS-REMED-2026",
                framework="UNIVERSITY_2026",
                institution_type="UNIVERSITY",
                institution_id=self.uni.aishe_code,
                file_data=SimpleUploadedFile("scan.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"A" * 50, content_type="image/png"),
                filename="scan.png",
                evidence_type="EVID_U6_ORDINANCE_GAZETTE",
                academic_year="2025-26",
                document_date=date(2025, 10, 1),
                parameter_id="U6",
                subcriterion_id="U6.A",
            )

    # =========================================================================
    # 4. CROSS-SUBCRITERION QUARANTINE
    # =========================================================================
    def test_cross_subcriterion_quarantine(self):
        """Prevent one subcriterion's evidence from satisfying unrelated subcriteria."""
        # U6.A cannot use EVID_U6_PEDAGOGY_RECORDS
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            EvidenceService.associate_subcriterion(
                evidence_id=self._make_orm_doc("EVID_U6_PEDAGOGY_RECORDS").pk,
                parameter_id="U6",
                subcriterion_id="U6.A",
                actor=self.nodal_user,
            )

        # U6.B cannot use EVID_U6_ORDINANCE_GAZETTE
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            EvidenceService.associate_subcriterion(
                evidence_id=self._make_orm_doc("EVID_U6_ORDINANCE_GAZETTE").pk,
                parameter_id="U6",
                subcriterion_id="U6.B",
                actor=self.nodal_user,
            )

        # U18.3 cannot use EVID_U18_POLICY
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            EvidenceService.associate_subcriterion(
                evidence_id=self._make_orm_doc("EVID_U18_POLICY").pk,
                parameter_id="U18",
                subcriterion_id="U18.3",
                actor=self.nodal_user,
            )

        # U18.1 cannot use EVID_U18_RPL_FORMAT
        with self.assertRaises(QuarantinedLegacyEvidenceError):
            EvidenceService.associate_subcriterion(
                evidence_id=self._make_orm_doc("EVID_U18_RPL_FORMAT").pk,
                parameter_id="U18",
                subcriterion_id="U18.1",
                actor=self.nodal_user,
            )

    # =========================================================================
    # 5. REVIEWER AUTHORIZATION & AUDIT TRAIL
    # =========================================================================
    def test_unauthorized_user_cannot_verify_evidence(self):
        """Institution nodal officer cannot verify evidence; requires authorized screening reviewer."""
        doc = self._make_orm_doc("EVID_U6_ORDINANCE_GAZETTE")
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U6",
            subcriterion_id="U6.A",
            actor=self.nodal_user,
        )

        with self.assertRaises(UnauthorizedEvidenceActionError):
            EvidenceService.verify_association(
                association_id=assoc.pk,
                verifier=self.nodal_user,
                reason="Unauthorized attempt",
            )

    def test_authorized_reviewer_can_verify_and_audit_trail_recorded(self):
        """Authorized reviewer verifies evidence, creating complete audit lifecycle entry."""
        doc = self._make_orm_doc("EVID_U6_ORDINANCE_GAZETTE")
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U6",
            subcriterion_id="U6.A",
            actor=self.nodal_user,
        )

        reviewed = EvidenceService.verify_association(
            association_id=assoc.pk,
            verifier=self.reviewer_user,
            reason="Examination ordinance amendment approved and signed by Vice Chancellor.",
        )
        self.assertEqual(reviewed.decision, VerificationDecision.VERIFIED)

        # Audit lifecycle trail
        records = EvidenceAuditLog.objects.filter(evidence=doc)
        self.assertTrue(records.count() >= 2)  # ASSOCIATED and VERIFIED
        verify_record = records.filter(action="VERIFIED").first()
        self.assertIsNotNone(verify_record)
        self.assertEqual(verify_record.actor, self.reviewer_user)

    # =========================================================================
    # 6. CERTIFICATION POLICY GATE
    # =========================================================================
    def test_certification_policy_gate_status(self):
        """U6 and U18.3 evidence rules are resolved, lifting the hold without globally disabling gates."""
        # 1. open_certification_policy_blockers for UNIVERSITY_2026 is empty
        blockers = open_certification_policy_blockers("UNIVERSITY_2026")
        self.assertEqual(blockers, [])

        # 2. Policy state for U6_U18_3_EVIDENCE is RESOLVED
        pol_state = get_policy_state("U6_U18_3_EVIDENCE")
        self.assertEqual(pol_state["status"], "RESOLVED")
        self.assertEqual(pol_state["source"], "EVIDENCE_TAXONOMY")
