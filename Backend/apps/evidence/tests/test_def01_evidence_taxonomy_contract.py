"""
NEP Excellence Awards 2026 - DEF-01 Forensic Test Suite
Validates the evidence upload taxonomy contract remediation:
1. Valid University evidence_type accepted.
2. Valid College evidence_type accepted.
3. Unknown evidence_type rejected.
4. EVID_GENERAL is not silently assigned to a normal NEP assessment upload.
5. Correct evidence_type survives persistence and association.
6. Reviewer verification still required.
7. Correct evidence_type reaches the existing scoring input unchanged.
8. Wrong evidence_type does not satisfy a mandatory evidence requirement.
9. Framework mismatch rejected.
10. Existing score-manipulation protections still pass.
"""
import hashlib
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.college.models import College
from apps.evidence.enums import (
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
)
from apps.evidence.exceptions import (
    EvidenceDomainError,
)
from apps.evidence.models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.evidence.pipeline import EvidenceUploadPipeline
from apps.evidence.services import EvidenceService
from apps.evidence.taxonomy import (
    derive_or_validate_evidence_type,
    UnknownEvidenceTypeError,
    EvidenceTypeFrameworkMismatchError,
    EvidenceTypeParameterMismatchError,
    AmbiguousEvidenceTypeError,
    MissingEvidenceTypeError,
)
from apps.scoring.domain import EvidenceDocument as ScoringEvidenceDoc
from apps.scoring.enums import (
    EvidenceState as ScoringEvidenceState,
    FrameworkType,
    GatingStatus,
)
from apps.scoring.evaluators.evidence_gating import evaluate_evidence


class TestDEF01EvidenceTaxonomyContract(APITestCase):
    """
    Focused verification for DEF-01 remediation.
    """
    def setUp(self):
        # Create test users
        self.college_user = User.objects.create_user(
            email="principal.c1@haryana.gov.in",
            full_name="Principal Karnal College",
            password="SecurePassword123!",
            role="principal",
        )
        self.college = College.objects.create(
            name="Government College Karnal",
            aishe_code="C-5001",
        )
        self.college_user.college = self.college
        self.college_user.save()

        self.university_user = User.objects.create_user(
            email="registrar.u1@haryana.gov.in",
            full_name="Registrar Haryana University",
            password="SecurePassword123!",
            role="principal",
        )

        self.committee_reviewer = User.objects.create_user(
            email="reviewer.def01@haryana.gov.in",
            full_name="Reviewer Committee Member",
            password="SecurePassword123!",
            role="committee",
        )

        self.admin_user = User.objects.create_superuser(
            email="admin.def01@haryana.gov.in",
            full_name="State Admin",
            password="SecurePassword123!",
        )

        # Grant framework authorizations to reviewer
        ReviewerAuthorization.objects.create(
            user=self.committee_reviewer,
            framework="COLLEGE_2026",
            granted_by=self.admin_user,
        )
        ReviewerAuthorization.objects.create(
            user=self.committee_reviewer,
            framework="UNIVERSITY_2026",
            granted_by=self.admin_user,
        )

        self.valid_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    def _get_upload_file(self, filename="evidence.pdf"):
        return SimpleUploadedFile(filename, self.valid_pdf_bytes, content_type="application/pdf")

    # 1. Valid University evidence_type accepted
    def test_valid_university_evidence_type_accepted(self):
        self.client.force_authenticate(user=self.university_user)
        url = reverse('evidence-list-create')
        
        # Test explicit valid type
        payload = {
            "file": self._get_upload_file("u1_curriculum.pdf"),
            "assessment_id": "ASSESS-U-2026-001",
            "framework": "UNIVERSITY_2026",
            "parameter_id": "U1",
            "subcriterion_id": "U1.1",
            "evidence_type": "EVID_U1_APPROVAL",
        }
        res = self.client.post(url, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["evidence_type"], "EVID_U1_APPROVAL")

        # Test deterministic server-side derivation when evidence_type is omitted
        payload_derived = {
            "file": self._get_upload_file("u1_scheme.pdf"),
            "assessment_id": "ASSESS-U-2026-001",
            "framework": "UNIVERSITY_2026",
            "parameter_id": "U1",
            "subcriterion_id": "U1.1",
        }
        res_derived = self.client.post(url, payload_derived, format='multipart')
        self.assertEqual(res_derived.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_derived.data["evidence_type"], "EVID_U1_APPROVAL")

    # 2. Valid College evidence_type accepted
    def test_valid_college_evidence_type_accepted(self):
        self.client.force_authenticate(user=self.college_user)
        url = reverse('evidence-list-create')

        # Test explicit valid type
        payload = {
            "file": self._get_upload_file("c1_idp.pdf"),
            "assessment_id": "ASSESS-C-2026-001",
            "framework": "COLLEGE_2026",
            "parameter_id": "C1",
            "subcriterion_id": "C1.1",
            "evidence_type": "EVID_C1_APPROVED_IDP",
        }
        res = self.client.post(url, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["evidence_type"], "EVID_C1_APPROVED_IDP")

        # Test deterministic server-side derivation when evidence_type is omitted
        payload_derived = {
            "file": self._get_upload_file("c1_idp_auto.pdf"),
            "assessment_id": "ASSESS-C-2026-001",
            "framework": "COLLEGE_2026",
            "parameter_id": "C1",
            "subcriterion_id": "C1.1",
        }
        res_derived = self.client.post(url, payload_derived, format='multipart')
        self.assertEqual(res_derived.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_derived.data["evidence_type"], "EVID_C1_APPROVED_IDP")

    # 3. Unknown evidence_type rejected
    def test_unknown_evidence_type_rejected(self):
        self.client.force_authenticate(user=self.college_user)
        url = reverse('evidence-list-create')

        payload = {
            "file": self._get_upload_file("fake.pdf"),
            "assessment_id": "ASSESS-C-2026-001",
            "framework": "COLLEGE_2026",
            "parameter_id": "C1",
            "evidence_type": "EVID_ARBITRARY_NONEXISTENT",
        }
        res = self.client.post(url, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("evidence_type", res.data)
        self.assertIn("Unknown evidence_type", str(res.data["evidence_type"]))

    # 4. EVID_GENERAL is not silently assigned to a normal NEP assessment upload
    def test_evid_general_not_silently_assigned_and_explicitly_rejected(self):
        self.client.force_authenticate(user=self.college_user)
        url = reverse('evidence-list-create')

        # Upload without evidence_type and without parameter_id -> must be rejected
        payload_no_param = {
            "file": self._get_upload_file("unclassified.pdf"),
            "assessment_id": "ASSESS-C-2026-001",
            "framework": "COLLEGE_2026",
        }
        res = self.client.post(url, payload_no_param, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("evidence_type", res.data)

        # Upload with explicit EVID_GENERAL -> must be rejected
        payload_general = {
            "file": self._get_upload_file("general.pdf"),
            "assessment_id": "ASSESS-C-2026-001",
            "framework": "COLLEGE_2026",
            "parameter_id": "C1",
            "evidence_type": "EVID_GENERAL",
        }
        res_general = self.client.post(url, payload_general, format='multipart')
        self.assertEqual(res_general.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("evidence_type", res_general.data)
        self.assertIn("not a valid evidence type", str(res_general.data["evidence_type"]))

    # 5. Correct evidence_type survives persistence and association
    def test_correct_evidence_type_survives_persistence_and_association(self):
        self.client.force_authenticate(user=self.college_user)
        url = reverse('evidence-list-create')

        payload = {
            "file": self._get_upload_file("c1_idp_record.pdf"),
            "assessment_id": "ASSESS-C-2026-001",
            "framework": "COLLEGE_2026",
            "parameter_id": "C1",
            "subcriterion_id": "C1.1",
        }
        res = self.client.post(url, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        doc_id = res.data["document_id"]

        # Check persistence in database
        doc = EvidenceDocument.objects.get(document_id=doc_id)
        self.assertEqual(doc.evidence_type, "EVID_C1_APPROVED_IDP")

        # Check association record
        assoc = EvidenceSubcriterionAssociation.objects.get(evidence=doc)
        self.assertEqual(assoc.parameter_id, "C1")
        self.assertEqual(assoc.subcriterion_id, "C1.1")
        self.assertTrue(assoc.is_active)

    # 6. Reviewer verification still required
    def test_reviewer_verification_still_required(self):
        # Upload valid C1 document
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.college_user,
            assessment_id="ASSESS-C-2026-001",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-5001",
            file_data=self.valid_pdf_bytes,
            filename="idp.pdf",
            parameter_id="C1",
            subcriterion_id="C1.1",
            validate_taxonomy=True,
        )
        self.assertEqual(doc.evidence_type, "EVID_C1_APPROVED_IDP")
        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_PRESENT)

        # Before verification: scoring eligibility is blocked
        status_code, mult, trace = EvidenceService.evaluate_subcriterion_scoring_eligibility(
            "C1", "C1.1", "ASSESS-C-2026-001", ["EVID_C1_APPROVED_IDP"]
        )
        self.assertEqual(mult, 0.0)
        self.assertEqual(status_code, GatingStatus.PROVISIONAL_PENDING_VERIFICATION)

        # Submit for verification
        EvidenceService.submit_for_verification(doc.pk, self.college_user)
        # Assign reviewer
        EvidenceService.assign_reviewer(doc.pk, self.committee_reviewer, self.admin_user)
        # Reviewer verifies document
        EvidenceService.verify_evidence(doc.pk, self.committee_reviewer)

        # After verification: scoring eligibility is unlocked!
        status_code, mult, trace = EvidenceService.evaluate_subcriterion_scoring_eligibility(
            "C1", "C1.1", "ASSESS-C-2026-001", ["EVID_C1_APPROVED_IDP"]
        )
        self.assertEqual(mult, 1.0)
        self.assertEqual(status_code, GatingStatus.PASSED_EVIDENCE_VERIFIED)

    # 7. Correct evidence_type reaches the existing scoring input unchanged
    def test_correct_evidence_type_reaches_scoring_input_unchanged(self):
        doc = EvidenceUploadPipeline.process_upload(
            uploader=self.college_user,
            assessment_id="ASSESS-C-2026-SCORING",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-5001",
            file_data=self.valid_pdf_bytes,
            filename="idp.pdf",
            parameter_id="C1",
            subcriterion_id="C1.1",
            validate_taxonomy=True,
        )
        scoring_docs = EvidenceService.get_subcriterion_scoring_evidence(
            "C1", "C1.1", "ASSESS-C-2026-SCORING"
        )
        self.assertEqual(len(scoring_docs), 1)
        self.assertEqual(scoring_docs[0].document_type, "EVID_C1_APPROVED_IDP")
        self.assertEqual(scoring_docs[0].document_id, str(doc.document_id))

    # 8. Wrong evidence_type does not satisfy a mandatory evidence requirement
    def test_wrong_evidence_type_does_not_satisfy_mandatory_evidence(self):
        # Upload an evidence document with C2 evidence type
        doc_c2 = EvidenceUploadPipeline.process_upload(
            uploader=self.college_user,
            assessment_id="ASSESS-C-2026-MISMATCH",
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id="C-5001",
            file_data=self.valid_pdf_bytes,
            filename="hoi_cert.pdf",
            evidence_type="EVID_C2_HOI_CERT",
            parameter_id="C2",
            subcriterion_id="C2.1",
            validate_taxonomy=True,
        )
        # Verify it
        doc_c2.status = EvidenceLifecycleState.EVIDENCE_VERIFIED
        doc_c2.save(update_fields=['status'])

        # Create scoring doc and evaluate against C1 requirements (which expects EVID_C1_APPROVED_IDP)
        scoring_doc = EvidenceService.to_scoring_domain(doc_c2)
        gating_status, mult, trace = evaluate_evidence(["EVID_C1_APPROVED_IDP"], [scoring_doc])
        
        self.assertEqual(gating_status, GatingStatus.FAILED_EVIDENCE_ABSENT)
        self.assertEqual(mult, 0.0)
        self.assertIn("EVID_C1_APPROVED_IDP", trace["missing_types"])

        # Also verify that attempting to associate C2 evidence to C1 parameter is rejected
        with self.assertRaises(EvidenceDomainError):
            EvidenceService.associate_subcriterion(
                evidence_id=doc_c2.pk,
                parameter_id="C1",
                subcriterion_id="C1.1",
                actor=self.college_user,
            )

    # 9. Framework mismatch rejected
    def test_framework_mismatch_rejected(self):
        self.client.force_authenticate(user=self.college_user)
        url = reverse('evidence-list-create')

        # College assessment trying to upload University evidence type
        payload_u_on_c = {
            "file": self._get_upload_file("uni_doc.pdf"),
            "assessment_id": "ASSESS-C-2026-001",
            "framework": "COLLEGE_2026",
            "parameter_id": "C1",
            "evidence_type": "EVID_U1_APPROVAL",
        }
        res_u_on_c = self.client.post(url, payload_u_on_c, format='multipart')
        self.assertEqual(res_u_on_c.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("belongs to the University framework", str(res_u_on_c.data))

        # University assessment trying to upload College evidence type
        self.client.force_authenticate(user=self.university_user)
        payload_c_on_u = {
            "file": self._get_upload_file("college_doc.pdf"),
            "assessment_id": "ASSESS-U-2026-001",
            "framework": "UNIVERSITY_2026",
            "parameter_id": "U1",
            "evidence_type": "EVID_C1_APPROVED_IDP",
        }
        res_c_on_u = self.client.post(url, payload_c_on_u, format='multipart')
        self.assertEqual(res_c_on_u.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("belongs to the College framework", str(res_c_on_u.data))

    # 10. Existing score-manipulation protections still pass
    def test_score_manipulation_protection(self):
        self.client.force_authenticate(user=self.college_user)
        url = reverse('evidence-list-create')

        payload_score_injection = {
            "file": self._get_upload_file("score_hack.pdf"),
            "assessment_id": "ASSESS-C-2026-001",
            "framework": "COLLEGE_2026",
            "parameter_id": "C1",
            "evidence_type": "EVID_C1_APPROVED_IDP",
            "score": 6.0,
            "earned_score": 6.0,
            "certified_score": 6.0,
        }
        res = self.client.post(url, payload_score_injection, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any(f in res.data for f in ["score", "earned_score", "certified_score"]))
