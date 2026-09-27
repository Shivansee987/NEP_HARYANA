"""
NEP Excellence Awards 2026 - Association-Level Evidence Data Model Tests (Step 4B)
Mandated by Step 4B specification: Tests A through H.
Verifies association-level metadata, independent verification, checksum integrity, and immutability.
"""
import hashlib
import uuid
from datetime import date
from django.db import IntegrityError
from django.test import TestCase

from apps.authentication.models import College, User
from apps.evidence.enums import (
    AssociationVerificationDecision,
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
)
from apps.evidence.exceptions import ImmutableRecordError
from apps.evidence.models import (
    EvidenceAssociationVerification,
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    EvidenceVerification,
)


class AssociationVerificationModelTestCase(TestCase):
    """
    Test suite for Step 4B Association-Level Data Model.
    """

    def setUp(self):
        super().setUp()
        self.college = College.objects.create(name="Govt College Karnal", aishe_code="C-1001")
        self.uploader = User.objects.create_user(
            email="uploader.karnal@haryana.gov.in",
            full_name="College Registrar",
            role="principal",
            college=self.college,
            password="SecurePassword123!",
        )
        self.reviewer = User.objects.create_user(
            email="reviewer.dhe@haryana.gov.in",
            full_name="Screening Committee Reviewer",
            role="committee",
            password="SecurePassword123!",
        )

        self.sample_bytes = b"%PDF-1.4 Mock NEP 2026 Comprehensive Evidence Dossier\n%%EOF"
        self.sample_checksum = hashlib.sha256(self.sample_bytes).hexdigest()

        self.doc_a = EvidenceDocument.objects.create(
            assessment_id="ASSESS-2026-TEST",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-001",
            original_filename="composite_dossier.pdf",
            file_path="mock/path/composite_dossier.pdf",
            file_size=len(self.sample_bytes),
            file_checksum=self.sample_checksum,
            uploader=self.uploader,
            evidence_type="EVID_U7_APPOINTMENT",
            document_date=date(2025, 9, 15),
            academic_year="2025-26",
            status=EvidenceLifecycleState.EVIDENCE_PRESENT,
        )

    # =========================================================================
    # TEST A — Multiple subcriteria per document
    # =========================================================================
    def test_a_multiple_subcriteria_per_document(self):
        """
        One document can have U7.1, U7.2, U7.3, U7.4 as distinct associations.
        All four associations must coexist cleanly.
        """
        subcriteria = ["U7.1", "U7.2", "U7.3", "U7.4"]
        for sub_id in subcriteria:
            EvidenceSubcriterionAssociation.objects.create(
                evidence=self.doc_a,
                parameter_id="U7",
                subcriterion_id=sub_id,
                associated_by=self.uploader,
            )

        self.assertEqual(self.doc_a.associations.count(), 4)
        associated_subs = set(self.doc_a.associations.values_list('subcriterion_id', flat=True))
        self.assertEqual(associated_subs, set(subcriteria))

    # =========================================================================
    # TEST B — Multiple documents per subcriterion
    # =========================================================================
    def test_b_multiple_documents_per_subcriterion(self):
        """
        Two distinct documents can both associate with the same subcriterion (e.g. U7.1).
        Both associations must coexist.
        """
        doc_b = EvidenceDocument.objects.create(
            assessment_id="ASSESS-2026-TEST",
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id="UNIV-001",
            original_filename="supplementary_proof.pdf",
            file_path="mock/path/supplementary_proof.pdf",
            file_size=25,
            file_checksum=hashlib.sha256(b"Supplementary doc").hexdigest(),
            uploader=self.uploader,
            evidence_type="EVID_U7_APPOINTMENT",
            document_date=date(2025, 9, 20),
            academic_year="2025-26",
            status=EvidenceLifecycleState.EVIDENCE_PRESENT,
        )

        assoc1 = EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc_a,
            parameter_id="U7",
            subcriterion_id="U7.1",
            associated_by=self.uploader,
        )
        assoc2 = EvidenceSubcriterionAssociation.objects.create(
            evidence=doc_b,
            parameter_id="U7",
            subcriterion_id="U7.1",
            associated_by=self.uploader,
        )

        u71_assocs = EvidenceSubcriterionAssociation.objects.filter(
            parameter_id="U7",
            subcriterion_id="U7.1",
        )
        self.assertEqual(u71_assocs.count(), 2)
        self.assertIn(assoc1, u71_assocs)
        self.assertIn(assoc2, u71_assocs)

    # =========================================================================
    # TEST C — Duplicate association protection
    # =========================================================================
    def test_c_duplicate_association_protection(self):
        """
        Attempting duplicate active association for (same document, same parameter, same subcriterion)
        must be rejected by the database uniqueness constraint.
        """
        EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc_a,
            parameter_id="U7",
            subcriterion_id="U7.1",
            associated_by=self.uploader,
        )

        with self.assertRaises(IntegrityError):
            EvidenceSubcriterionAssociation.objects.create(
                evidence=self.doc_a,
                parameter_id="U7",
                subcriterion_id="U7.1",
                associated_by=self.uploader,
            )

    # =========================================================================
    # TEST D — Association metadata
    # =========================================================================
    def test_d_association_metadata(self):
        """
        Create association with all Step 4B metadata fields:
        subcriterion_evidence_type, page_start, page_end, section_identifier, claim_description.
        All fields must persist correctly.
        """
        assoc = EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc_a,
            parameter_id="U7",
            subcriterion_id="U7.1",
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            page_start=1,
            page_end=4,
            section_identifier="Annexure-A: Appointment Letter",
            claim_description="Official Government appointment letter of Professor of Practice under NEP 2020.",
            associated_by=self.uploader,
        )

        assoc.refresh_from_db()
        self.assertEqual(assoc.subcriterion_evidence_type, "EVID_U7_APPOINTMENT")
        self.assertEqual(assoc.page_start, 1)
        self.assertEqual(assoc.page_end, 4)
        self.assertEqual(assoc.section_identifier, "Annexure-A: Appointment Letter")
        self.assertEqual(
            assoc.claim_description,
            "Official Government appointment letter of Professor of Practice under NEP 2020."
        )

    # =========================================================================
    # TEST E — Independent verification
    # =========================================================================
    def test_e_independent_verification(self):
        """
        Document A associated to U10.3 and U20.3.
        Verification A: U10.3 = VERIFIED
        Verification B: U20.3 = REJECTED
        Expected:
        - U10.3 latest association verification = VERIFIED
        - U20.3 latest association verification = REJECTED
        - EvidenceDocument itself must NOT be mutated by these association verification records.
        """
        assoc_u10 = EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc_a,
            parameter_id="U10",
            subcriterion_id="U10.3",
            subcriterion_evidence_type="EVID_U10_REG_CERT",
            page_start=12,
            page_end=15,
            associated_by=self.uploader,
        )
        assoc_u20 = EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc_a,
            parameter_id="U20",
            subcriterion_id="U20.3",
            subcriterion_evidence_type="EVID_U20_ACTIVITY_REPORTS",
            page_start=45,
            page_end=50,
            associated_by=self.uploader,
        )

        initial_doc_status = self.doc_a.status

        # Reviewer verifies Association A (U10.3)
        v_a = EvidenceAssociationVerification.objects.create(
            association=assoc_u10,
            verifier=self.reviewer,
            decision=VerificationDecision.VERIFIED,
            reason="Alumni funding section is fully verified and audited.",
        )

        # Reviewer rejects Association B (U20.3)
        v_b = EvidenceAssociationVerification.objects.create(
            association=assoc_u20,
            verifier=self.reviewer,
            decision=VerificationDecision.REJECTED,
            reason="Pages 45-50 lack required SDG activity outcome metrics.",
            rejection_code=RejectionReasonCode.INCOMPLETE_DOCUMENTATION,
        )

        # Association A checks
        self.assertEqual(assoc_u10.latest_verification.decision, VerificationDecision.VERIFIED)
        self.assertEqual(assoc_u10.verification_status, VerificationDecision.VERIFIED)
        self.assertEqual(assoc_u10.latest_verification.pk, v_a.pk)

        # Association B checks
        self.assertEqual(assoc_u20.latest_verification.decision, VerificationDecision.REJECTED)
        self.assertEqual(assoc_u20.verification_status, VerificationDecision.REJECTED)
        self.assertEqual(assoc_u20.latest_verification.pk, v_b.pk)

        # Crucial contract check: EvidenceDocument itself must NOT be mutated
        self.doc_a.refresh_from_db()
        self.assertEqual(
            self.doc_a.status,
            initial_doc_status,
            "Physical EvidenceDocument status must NOT be modified by association verification records."
        )

    # =========================================================================
    # TEST F — Historical document verification preserved
    # =========================================================================
    def test_f_historical_document_verification_preserved(self):
        """
        Document-level EvidenceVerification and association-level EvidenceAssociationVerification
        coexist and remain independently queryable without interfering with each other.
        """
        assoc = EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc_a,
            parameter_id="U4",
            subcriterion_id="U4.1",
            associated_by=self.uploader,
        )

        # Create historical document-level verification
        doc_v = EvidenceVerification.objects.create(
            evidence=self.doc_a,
            verifier=self.reviewer,
            decision=VerificationDecision.VERIFIED,
            reason="Document-level screening approved.",
            previous_state=EvidenceLifecycleState.EVIDENCE_PENDING,
            resulting_state=EvidenceLifecycleState.EVIDENCE_VERIFIED,
            inspected_checksum=self.sample_checksum,
        )

        # Create new association-level verification
        assoc_v = EvidenceAssociationVerification.objects.create(
            association=assoc,
            verifier=self.reviewer,
            decision=VerificationDecision.VERIFIED,
            reason="Subcriterion-level verification approved.",
            inspected_checksum=self.sample_checksum,
        )

        self.assertEqual(self.doc_a.verifications.count(), 1)
        self.assertEqual(self.doc_a.verifications.first().pk, doc_v.pk)

        self.assertEqual(assoc.verifications.count(), 1)
        self.assertEqual(assoc.verifications.first().pk, assoc_v.pk)

        # Both remain queryable and independent across separate models and tables
        self.assertNotEqual(doc_v.verification_id, assoc_v.verification_id)
        self.assertNotEqual(doc_v._meta.db_table, assoc_v._meta.db_table)
        self.assertIsInstance(doc_v, EvidenceVerification)
        self.assertIsInstance(assoc_v, EvidenceAssociationVerification)

    # =========================================================================
    # TEST G — Checksum integrity
    # =========================================================================
    def test_g_checksum_integrity(self):
        """
        Association verification stores inspected_checksum matching the EvidenceDocument checksum.
        Also validates automatic population from parent document when blank.
        """
        assoc = EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc_a,
            parameter_id="U7",
            subcriterion_id="U7.1",
            associated_by=self.uploader,
        )

        # 1. Explicit checksum
        v_explicit = EvidenceAssociationVerification.objects.create(
            association=assoc,
            verifier=self.reviewer,
            decision=VerificationDecision.VERIFIED,
            inspected_checksum=self.sample_checksum,
        )
        self.assertEqual(v_explicit.inspected_checksum, self.doc_a.file_checksum)

        # 2. Auto-populated checksum from parent document
        v_auto = EvidenceAssociationVerification.objects.create(
            association=assoc,
            verifier=self.reviewer,
            decision=VerificationDecision.VERIFIED,
        )
        self.assertEqual(v_auto.inspected_checksum, self.doc_a.file_checksum)

    # =========================================================================
    # TEST H — Immutability
    # =========================================================================
    def test_h_immutability(self):
        """
        Enforce strict append-only immutability.
        Neither existing EvidenceVerification nor EvidenceAssociationVerification can be modified or deleted.
        """
        assoc = EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc_a,
            parameter_id="U7",
            subcriterion_id="U7.1",
            associated_by=self.uploader,
        )

        # Association verification immutability
        v_assoc = EvidenceAssociationVerification.objects.create(
            association=assoc,
            verifier=self.reviewer,
            decision=VerificationDecision.VERIFIED,
            reason="Original verification note",
        )

        v_assoc.reason = "Tampered verification note"
        with self.assertRaises(ImmutableRecordError):
            v_assoc.save()

        with self.assertRaises(ImmutableRecordError):
            v_assoc.delete()

        # Document-level verification immutability
        v_doc = EvidenceVerification.objects.create(
            evidence=self.doc_a,
            verifier=self.reviewer,
            decision=VerificationDecision.VERIFIED,
            previous_state=EvidenceLifecycleState.EVIDENCE_PENDING,
            resulting_state=EvidenceLifecycleState.EVIDENCE_VERIFIED,
        )

        v_doc.reason = "Tampered document verification"
        with self.assertRaises(ImmutableRecordError):
            v_doc.save()

        with self.assertRaises(ImmutableRecordError):
            v_doc.delete()
