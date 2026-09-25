"""
NEP Excellence Awards 2026 - Workflow Phase W3 Checker Review Tests

Covers all 15 verification points mandated by Phase W3 specification:
1. Authorized checker sees submitted assessment in review queues
2. Unauthorized checker cannot see assessment
3. Checker can retrieve assessment detail (parameters, associations, coverage, review info)
4. Checker sees exact subcriterion associations without collapse
5. Association can be VERIFIED
6. Association can be REJECTED
7. Rejection reason is stored
8. Rejection affects only that association
9. Sibling association remains unchanged
10. Association history is preserved (append-only immutability)
11. Framework isolation works
12. Institution isolation works
13. Document access is authorized and secure (no path leakage, no public URL)
14. Legacy nomination system is not involved
15. Existing review completion remains functional
"""
import hashlib
import os
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import College
from apps.college.models import CollegeAssessment
from apps.college.services import CollegeAssessmentService, CollegeReviewService
from apps.evidence.enums import (
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
)
from apps.evidence.exceptions import ImmutableRecordError
from apps.evidence.models import (
    EvidenceAssociationVerification,
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.evidence.services import EvidenceService
from apps.evidence.storage import get_evidence_storage
from apps.nominations.models import Nomination
from apps.university.models import (
    University,
    UniversityAssessment,
    UniversityReviewRecord,
)
from apps.university.services import (
    UniversityAssessmentService,
    UniversityReviewService,
)

User = get_user_model()
TEST_VAULT_DIR = Path(settings.BASE_DIR) / 'test_w3_evidence_vault'


@override_settings(
    EVIDENCE_STORAGE_VAULT=TEST_VAULT_DIR,
    MAX_EVIDENCE_FILE_SIZE=1024 * 1024,
)
class WorkflowW3CheckerReviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        if TEST_VAULT_DIR.exists():
            shutil.rmtree(TEST_VAULT_DIR, ignore_errors=True)
        TEST_VAULT_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Institutions
        self.uni_a = University.objects.create(
            name="Kurukshetra University",
            aishe_code="U-0160",
            state="Haryana",
            is_active=True,
        )
        self.uni_b = University.objects.create(
            name="Maharshi Dayanand University",
            aishe_code="U-0161",
            state="Haryana",
            is_active=True,
        )
        self.college_a = College.objects.create(
            name="Govt College Karnal",
            aishe_code="C-1001",
        )
        self.college_b = College.objects.create(
            name="Govt College Rohtak",
            aishe_code="C-1002",
        )

        # 2. Institutional Users
        self.nodal_uni_a = User.objects.create_user(
            email="nodal.kuk@haryana.gov.in",
            full_name="KUK Nodal Officer",
            role="nodal_officer",
            university=self.uni_a,
            password="SecurePassword2026!",
        )
        self.nodal_uni_b = User.objects.create_user(
            email="nodal.mdu@haryana.gov.in",
            full_name="MDU Nodal Officer",
            role="nodal_officer",
            university=self.uni_b,
            password="SecurePassword2026!",
        )
        self.principal_col_a = User.objects.create_user(
            email="principal.karnal@haryana.gov.in",
            full_name="Karnal Principal",
            role="principal",
            college=self.college_a,
            password="SecurePassword2026!",
        )

        # 3. Administrators
        self.admin_user = User.objects.create_superuser(
            email="admin.dhe@haryana.gov.in",
            full_name="DHE Admin",
            password="SecurePassword2026!",
        )

        # 4. Reviewers
        # Authorized for ALL frameworks
        self.checker_all = User.objects.create_user(
            email="checker.all@haryana.gov.in",
            full_name="State Screening Reviewer",
            role="committee",
            password="SecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(
            user=self.checker_all,
            framework="ALL",
            is_active=True,
        )

        # Authorized only for University
        self.checker_uni_only = User.objects.create_user(
            email="checker.uni@haryana.gov.in",
            full_name="University Committee Reviewer",
            role="committee",
            password="SecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(
            user=self.checker_uni_only,
            framework="UNIVERSITY_2026",
            is_active=True,
        )

        # Authorized only for College
        self.checker_col_only = User.objects.create_user(
            email="checker.col@haryana.gov.in",
            full_name="College Committee Reviewer",
            role="committee",
            password="SecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(
            user=self.checker_col_only,
            framework="COLLEGE_2026",
            is_active=True,
        )

        # Reviewer with Conflict of Interest (affiliated with University A)
        self.checker_coi_uni_a = User.objects.create_user(
            email="reviewer.affiliated@haryana.gov.in",
            full_name="Affiliated Reviewer",
            role="committee",
            university=self.uni_a,
            password="SecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(
            user=self.checker_coi_uni_a,
            framework="UNIVERSITY_2026",
            is_active=True,
        )

        # Sample valid PDF content
        self.pdf_content = b"%PDF-1.4\n%NEP 2026 Authoritative Evidence Document\n%%EOF"
        self.pdf_checksum = hashlib.sha256(self.pdf_content).hexdigest()

    def tearDown(self):
        if TEST_VAULT_DIR.exists():
            shutil.rmtree(TEST_VAULT_DIR, ignore_errors=True)

    def _create_submitted_university_assessment(self, uni=None, nodal=None):
        uni = uni or self.uni_a
        nodal = nodal or self.nodal_uni_a
        assessment = UniversityAssessmentService.create_assessment(
            university_id=uni.id,
            academic_year="2025-26",
            created_by=nodal,
        )
        UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="U7",
            raw_inputs={
                "U7.1": {"appointed": True},
                "U7.2": {"completed_modules": 4},
                "U7.3": {"engagement_hours": 120},
                "U7.4": {"outcome_certified": True},
            },
            activity_date=date(2025, 10, 15),
        )
        return UniversityAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=nodal,
        )

    def _create_submitted_college_assessment(self, college=None, principal=None):
        college = college or self.college_a
        principal = principal or self.principal_col_a
        assessment = CollegeAssessmentService.create_assessment(
            college_id=college.id,
            academic_year="2025-26",
            created_by=principal,
        )
        CollegeAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code="C1",
            raw_inputs={"C1.1": {"programmes": 5}},
            activity_date=date(2025, 10, 15),
        )
        return CollegeAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=principal,
        )

    def _create_stored_evidence_doc(self, assessment, uploader, filename="proof.pdf"):
        storage = get_evidence_storage()
        storage_key = f"evidence/{assessment.framework}/{assessment.assessment_id}/{self.pdf_checksum[:2]}/{self.pdf_checksum}_{filename}"
        storage.save(storage_key, self.pdf_content, mime_type="application/pdf")

        inst_id = self.uni_a.aishe_code if hasattr(assessment, 'university') else self.college_a.aishe_code
        inst_type = "UNIVERSITY" if hasattr(assessment, 'university') else "COLLEGE"

        doc = EvidenceDocument.objects.create(
            uploader=uploader,
            assessment_id=assessment.assessment_id,
            framework=assessment.framework,
            institution_type=inst_type,
            institution_id=inst_id,
            file_path=storage_key,
            original_filename=filename,
            file_size=len(self.pdf_content),
            file_checksum=self.pdf_checksum,
            mime_type="application/pdf",
            status=EvidenceLifecycleState.EVIDENCE_PENDING,
            document_date=date(2025, 10, 15),
            academic_year="2025-26",
            is_active=True,
        )
        return doc

    # =========================================================================
    # 1. Authorized checker sees submitted assessment in review queues
    # =========================================================================

    def test_01_authorized_checker_sees_submitted_assessment_in_queues(self):
        uni_assess = self._create_submitted_university_assessment()
        col_assess = self._create_submitted_college_assessment()
        draft_uni = UniversityAssessmentService.create_assessment(
            university_id=self.uni_b.id,
            academic_year="2025-26",
            created_by=self.nodal_uni_b,
        )

        self.client.force_authenticate(user=self.checker_all)

        # Unified Queue
        res_unified = self.client.get("/api/v1/admin/review-queue/")
        self.assertEqual(res_unified.status_code, status.HTTP_200_OK)
        ids_unified = [item["assessment_id"] for item in res_unified.data["results"]]
        self.assertIn(uni_assess.assessment_id, ids_unified)
        self.assertIn(col_assess.assessment_id, ids_unified)
        self.assertNotIn(draft_uni.assessment_id, ids_unified)

        # University Framework Queue
        res_uni_queue = self.client.get("/api/v1/university/university-assessments/review-queue/")
        self.assertEqual(res_uni_queue.status_code, status.HTTP_200_OK)
        results = res_uni_queue.data.get("results", res_uni_queue.data)
        ids_uni = [item["assessment_id"] for item in results]
        self.assertIn(uni_assess.assessment_id, ids_uni)
        self.assertNotIn(col_assess.assessment_id, ids_uni)
        self.assertNotIn(draft_uni.assessment_id, ids_uni)

        # College Framework Queue
        res_col_queue = self.client.get("/api/v1/college/college-assessments/review/queue/")
        self.assertEqual(res_col_queue.status_code, status.HTTP_200_OK)
        col_results = res_col_queue.data.get("results", res_col_queue.data)
        ids_col = [item["assessment_id"] for item in col_results]
        self.assertIn(col_assess.assessment_id, ids_col)
        self.assertNotIn(uni_assess.assessment_id, ids_col)

    # =========================================================================
    # 2. Unauthorized checker cannot see assessment
    # =========================================================================

    def test_02_unauthorized_checker_cannot_see_assessment(self):
        uni_assess = self._create_submitted_university_assessment()

        # Unauthenticated: 401
        res_anon = self.client.get("/api/v1/admin/review-queue/")
        self.assertEqual(res_anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # Institutional user: 403
        self.client.force_authenticate(user=self.nodal_uni_a)
        res_inst = self.client.get("/api/v1/admin/review-queue/")
        self.assertEqual(res_inst.status_code, status.HTTP_403_FORBIDDEN)

        # Reviewer authorized only for College accessing University queue:
        # Sees empty queue (no university assessments exposed)
        self.client.force_authenticate(user=self.checker_col_only)
        res_uni = self.client.get("/api/v1/university/university-assessments/review-queue/")
        self.assertEqual(res_uni.status_code, status.HTTP_200_OK)
        results_uni = res_uni.data.get("results", res_uni.data)
        self.assertEqual(len(results_uni), 0)

        # Direct access to university assessment detail is forbidden
        res_uni_detail = self.client.get(f"/api/v1/university/university-assessments/{uni_assess.assessment_id}/")
        self.assertEqual(res_uni_detail.status_code, status.HTTP_403_FORBIDDEN)

        # Reviewer with Institutional COI does NOT see their own university assessment in queue
        self.client.force_authenticate(user=self.checker_coi_uni_a)
        res_coi = self.client.get("/api/v1/university/university-assessments/review-queue/")
        self.assertEqual(res_coi.status_code, status.HTTP_200_OK)
        results = res_coi.data.get("results", res_coi.data)
        ids = [item["assessment_id"] for item in results]
        self.assertNotIn(uni_assess.assessment_id, ids)

    # =========================================================================
    # 3. Checker can retrieve assessment detail
    # =========================================================================

    def test_03_checker_can_retrieve_assessment_detail(self):
        uni_assess = self._create_submitted_university_assessment()
        doc = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a)
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.nodal_uni_a,
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            page_start=1,
            page_end=3,
            section_identifier="Section A",
            claim_description="Appointment letter for Professor of Practice.",
        )

        self.client.force_authenticate(user=self.checker_all)

        # 3A: Admin Inspect endpoint
        res = self.client.get(f"/api/v1/admin/assessments/{uni_assess.assessment_id}/inspect/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data

        self.assertEqual(data["assessment_id"], uni_assess.assessment_id)
        self.assertEqual(data["framework"], "UNIVERSITY_2026")
        self.assertEqual(data["status"], "SUBMITTED")
        self.assertIsNotNone(data["submitted_at"])
        self.assertEqual(data["institution"]["name"], self.uni_a.name)
        self.assertEqual(data["institution"]["aishe_code"], self.uni_a.aishe_code)
        self.assertIn("parameter_data", data)
        self.assertIn("U7", data["parameter_data"])
        self.assertIn("evidence_associations", data)
        self.assertEqual(len(data["evidence_associations"]), 1)
        self.assertEqual(data["evidence_associations"][0]["parameter_id"], "U7")
        self.assertEqual(data["evidence_associations"][0]["subcriterion_id"], "U7.1")
        self.assertIn("evidence_coverage", data)
        self.assertIn("scoring", data)
        self.assertIn("review_history", data)

        # 3B: Admin Review alias endpoint
        res_alias = self.client.get(f"/api/v1/admin/assessments/{uni_assess.assessment_id}/review/")
        self.assertEqual(res_alias.status_code, status.HTTP_200_OK)

        # 3C: University assessment detail endpoint includes evidence_associations
        res_uni_detail = self.client.get(f"/api/v1/university/university-assessments/{uni_assess.assessment_id}/")
        self.assertEqual(res_uni_detail.status_code, status.HTTP_200_OK)
        self.assertIn("evidence_associations", res_uni_detail.data)
        self.assertEqual(len(res_uni_detail.data["evidence_associations"]), 1)

    # =========================================================================
    # 4. Checker sees exact subcriterion associations without collapse
    # =========================================================================

    def test_04_checker_sees_exact_subcriterion_associations(self):
        uni_assess = self._create_submitted_university_assessment()
        doc = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a, "composite_u7.pdf")

        # 4 distinct subcriterion associations on parameter U7
        assoc_7_1 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.nodal_uni_a,
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
            page_start=1,
            page_end=2,
            section_identifier="Annexure-1",
            claim_description="Appointment document",
        )
        assoc_7_2 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.2",
            actor=self.nodal_uni_a,
            subcriterion_evidence_type="EVID_U7_TEACHING_LOGS",
            page_start=3,
            page_end=5,
            section_identifier="Annexure-2",
            claim_description="Course completion document",
        )
        assoc_7_3 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.3",
            actor=self.nodal_uni_a,
            subcriterion_evidence_type="EVID_U7_WORKSHOP_REPORTS",
            page_start=6,
            page_end=8,
            section_identifier="Annexure-3",
            claim_description="Industry engagement document",
        )
        assoc_7_4 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.4",
            actor=self.nodal_uni_a,
            subcriterion_evidence_type="EVID_U7_PROJECT_REPORTS",
            page_start=9,
            page_end=12,
            section_identifier="Annexure-4",
            claim_description="Outcome report",
        )

        self.client.force_authenticate(user=self.checker_all)

        # Inspect via associations list API
        res = self.client.get(f"/api/evidence/associations/?assessment_id={uni_assess.assessment_id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        assocs_list = res.data.get("results", res.data)
        self.assertEqual(len(assocs_list), 4)

        sub_ids = [a["subcriterion_id"] for a in assocs_list]
        self.assertEqual(sub_ids, ["U7.1", "U7.2", "U7.3", "U7.4"])

        # Preserves exact individual metadata without collapse
        assoc_map = {a["subcriterion_id"]: a for a in assocs_list}
        self.assertEqual(assoc_map["U7.1"]["section_identifier"], "Annexure-1")
        self.assertEqual(assoc_map["U7.2"]["page_start"], 3)
        self.assertEqual(assoc_map["U7.3"]["subcriterion_evidence_type"], "EVID_U7_WORKSHOP_REPORTS")
        self.assertEqual(assoc_map["U7.4"]["claim_description"], "Outcome report")

    # =========================================================================
    # 5. Association can be VERIFIED
    # =========================================================================

    def test_05_association_can_be_verified(self):
        uni_assess = self._create_submitted_university_assessment()
        doc = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a)
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.nodal_uni_a,
        )

        self.client.force_authenticate(user=self.checker_all)

        # POST /api/evidence/associations/{id}/verify/
        res = self.client.post(
            f"/api/evidence/associations/{assoc.pk}/verify/",
            {"reason": "Document fully conforms to U7.1 guidelines."},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["decision"], "VERIFIED")
        self.assertEqual(res.data["verification_status"], "VERIFIED")
        self.assertEqual(res.data["parameter_id"], "U7")
        self.assertEqual(res.data["subcriterion_id"], "U7.1")

        assoc.refresh_from_db()
        self.assertEqual(assoc.verification_status, "VERIFIED")
        self.assertIsNotNone(assoc.latest_verification)
        self.assertEqual(assoc.latest_verification.decision, VerificationDecision.VERIFIED)
        self.assertEqual(assoc.latest_verification.reason, "Document fully conforms to U7.1 guidelines.")

    # =========================================================================
    # 6. Association can be REJECTED
    # =========================================================================

    def test_06_association_can_be_rejected(self):
        uni_assess = self._create_submitted_university_assessment()
        doc = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a)
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.2",
            actor=self.nodal_uni_a,
        )

        self.client.force_authenticate(user=self.checker_all)

        # Missing reason fails with HTTP 400
        res_fail = self.client.post(
            f"/api/evidence/associations/{assoc.pk}/reject/",
            {"reason": ""},
            format="json",
        )
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)

        # Rejection with mandatory reason and structured code
        res = self.client.post(
            f"/api/evidence/associations/{assoc.pk}/reject/",
            {
                "reason": "Submitted document does not establish completion of the required module.",
                "rejection_code": "INSUFFICIENT_SUBSTANTIATION",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["decision"], "REJECTED")
        self.assertEqual(res.data["verification_status"], "REJECTED")
        self.assertEqual(res.data["rejection_code"], "INSUFFICIENT_SUBSTANTIATION")

        assoc.refresh_from_db()
        self.assertEqual(assoc.verification_status, "REJECTED")

    # =========================================================================
    # 7. Rejection reason is stored
    # =========================================================================

    def test_07_rejection_reason_is_stored(self):
        uni_assess = self._create_submitted_university_assessment()
        doc = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a)
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.nodal_uni_a,
        )

        rejection_text = "Submitted document does not establish completion of the required module."
        EvidenceService.reject_association(
            association_id=assoc.pk,
            verifier=self.checker_all,
            reason=rejection_text,
            rejection_code=RejectionReasonCode.MISMATCHED_CRITERIA,
        )

        self.client.force_authenticate(user=self.checker_all)
        res = self.client.get(f"/api/evidence/associations/{assoc.pk}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["latest_verification"]["reason"], rejection_text)
        self.assertEqual(res.data["latest_verification"]["rejection_code"], RejectionReasonCode.MISMATCHED_CRITERIA)

    # =========================================================================
    # 8. Rejection affects only that association
    # 9. Sibling association remains unchanged
    # =========================================================================

    def test_08_and_09_rejection_isolation_and_sibling_independence(self):
        uni_assess = self._create_submitted_university_assessment()
        doc = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a, "composite.pdf")

        a1 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk, parameter_id="U7", subcriterion_id="U7.1", actor=self.nodal_uni_a,
            subcriterion_evidence_type="EVID_U7_APPOINTMENT",
        )
        a2 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk, parameter_id="U7", subcriterion_id="U7.2", actor=self.nodal_uni_a,
            subcriterion_evidence_type="EVID_U7_TEACHING_LOGS",
        )
        a3 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk, parameter_id="U7", subcriterion_id="U7.3", actor=self.nodal_uni_a,
            subcriterion_evidence_type="EVID_U7_WORKSHOP_REPORTS",
        )
        a4 = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk, parameter_id="U7", subcriterion_id="U7.4", actor=self.nodal_uni_a,
            subcriterion_evidence_type="EVID_U7_PROJECT_REPORTS",
        )

        self.client.force_authenticate(user=self.checker_all)

        # APPROVE U7.1
        self.client.post(f"/api/evidence/associations/{a1.pk}/verify/", {"reason": "U7.1 approved"})
        # REJECT U7.2
        self.client.post(
            f"/api/evidence/associations/{a2.pk}/reject/",
            {"reason": "U7.2 rejected: missing completion seal", "rejection_code": "INCOMPLETE_DOCUMENTATION"}
        )
        # APPROVE U7.3
        self.client.post(f"/api/evidence/associations/{a3.pk}/verify/", {"reason": "U7.3 approved"})
        # REJECT U7.4
        self.client.post(
            f"/api/evidence/associations/{a4.pk}/reject/",
            {"reason": "U7.4 rejected: uncertified outcome", "rejection_code": "MISMATCHED_CRITERIA"}
        )

        for a in (a1, a2, a3, a4):
            a.refresh_from_db()

        # Point 8: Independent verification states
        self.assertEqual(a1.verification_status, "VERIFIED")
        self.assertEqual(a2.verification_status, "REJECTED")
        self.assertEqual(a3.verification_status, "VERIFIED")
        self.assertEqual(a4.verification_status, "REJECTED")

        # Point 9: Sibling associations are not corrupted by U7.2 rejection
        self.assertEqual(a1.latest_verification.decision, VerificationDecision.VERIFIED)
        self.assertNotIn("missing completion seal", a1.latest_verification.reason)
        self.assertEqual(a3.latest_verification.decision, VerificationDecision.VERIFIED)
        self.assertNotIn("missing completion seal", a3.latest_verification.reason)

        # Global document lifecycle remains untouched
        doc.refresh_from_db()
        self.assertEqual(doc.status, EvidenceLifecycleState.EVIDENCE_PENDING)

    # =========================================================================
    # 10. Association history is preserved (append-only)
    # =========================================================================

    def test_10_association_history_is_preserved(self):
        uni_assess = self._create_submitted_university_assessment()
        doc = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a)
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id="U7",
            subcriterion_id="U7.1",
            actor=self.nodal_uni_a,
        )

        self.client.force_authenticate(user=self.checker_all)

        # 1. Reject first
        self.client.post(
            f"/api/evidence/associations/{assoc.pk}/reject/",
            {"reason": "First review: rejected"},
            format="json",
        )
        # 2. Later verify
        self.client.post(
            f"/api/evidence/associations/{assoc.pk}/verify/",
            {"reason": "Second review: verified after clarification"},
            format="json",
        )

        # History endpoint returns both records
        res_hist = self.client.get(f"/api/evidence/associations/{assoc.pk}/history/")
        self.assertEqual(res_hist.status_code, status.HTTP_200_OK)
        history = res_hist.data
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["decision"], "VERIFIED")
        self.assertEqual(history[0]["reason"], "Second review: verified after clarification")
        self.assertEqual(history[1]["decision"], "REJECTED")
        self.assertEqual(history[1]["reason"], "First review: rejected")

        # Immutability: existing record cannot be mutated or deleted
        rec = EvidenceAssociationVerification.objects.filter(association=assoc).first()
        with self.assertRaises(ImmutableRecordError):
            rec.reason = "Tampered reason"
            rec.save()

        with self.assertRaises(ImmutableRecordError):
            rec.delete()

    # =========================================================================
    # 11. Framework isolation works
    # =========================================================================

    def test_11_framework_isolation_works(self):
        uni_assess = self._create_submitted_university_assessment()
        col_assess = self._create_submitted_college_assessment()

        doc_uni = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a)
        assoc_uni = EvidenceService.associate_subcriterion(
            evidence_id=doc_uni.pk, parameter_id="U7", subcriterion_id="U7.1", actor=self.nodal_uni_a
        )

        doc_col = self._create_stored_evidence_doc(col_assess, self.principal_col_a)
        assoc_col = EvidenceService.associate_subcriterion(
            evidence_id=doc_col.pk, parameter_id="C1", subcriterion_id="C1.1", actor=self.principal_col_a
        )

        # College reviewer attempting to verify University association: 403
        self.client.force_authenticate(user=self.checker_col_only)
        res_col_on_uni = self.client.post(
            f"/api/evidence/associations/{assoc_uni.pk}/verify/",
            {"reason": "Illegal cross-framework verify"},
            format="json",
        )
        self.assertEqual(res_col_on_uni.status_code, status.HTTP_403_FORBIDDEN)

        # University reviewer attempting to verify College association: 403
        self.client.force_authenticate(user=self.checker_uni_only)
        res_uni_on_col = self.client.post(
            f"/api/evidence/associations/{assoc_col.pk}/verify/",
            {"reason": "Illegal cross-framework verify"},
            format="json",
        )
        self.assertEqual(res_uni_on_col.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # 12. Institution isolation works
    # =========================================================================

    def test_12_institution_isolation_works(self):
        uni_assess = self._create_submitted_university_assessment(uni=self.uni_a)
        doc = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a)
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk, parameter_id="U7", subcriterion_id="U7.1", actor=self.nodal_uni_a
        )

        # Reviewer with COI (affiliated with University A) cannot verify
        self.client.force_authenticate(user=self.checker_coi_uni_a)
        res_coi = self.client.post(
            f"/api/evidence/associations/{assoc.pk}/verify/",
            {"reason": "COI verification attempt"},
            format="json",
        )
        self.assertEqual(res_coi.status_code, status.HTTP_403_FORBIDDEN)

        # Institutional user cannot verify or reject
        self.client.force_authenticate(user=self.nodal_uni_a)
        res_inst = self.client.post(
            f"/api/evidence/associations/{assoc.pk}/verify/",
            {"reason": "Self verification attempt"},
            format="json",
        )
        self.assertEqual(res_inst.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # 13. Document access is authorized
    # =========================================================================

    def test_13_document_access_is_authorized(self):
        uni_assess = self._create_submitted_university_assessment()
        doc = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a, "confidential.pdf")
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk, parameter_id="U7", subcriterion_id="U7.1", actor=self.nodal_uni_a
        )

        # 13A: Authorized reviewer can stream via document UUID
        self.client.force_authenticate(user=self.checker_all)
        res_doc = self.client.get(f"/api/evidence/{doc.document_id}/document/")
        self.assertEqual(res_doc.status_code, status.HTTP_200_OK)
        self.assertEqual(res_doc.content, self.pdf_content)
        self.assertIn("inline; filename=", res_doc.headers.get("Content-Disposition", ""))
        self.assertNotIn(str(TEST_VAULT_DIR), str(res_doc.headers))

        # 13B: Authorized reviewer can stream via association UUID / ID
        res_assoc_doc = self.client.get(f"/api/evidence/associations/{assoc.association_id}/document/")
        self.assertEqual(res_assoc_doc.status_code, status.HTTP_200_OK)
        self.assertEqual(res_assoc_doc.content, self.pdf_content)

        # 13C: Reviewer with COI is blocked from streaming
        self.client.force_authenticate(user=self.checker_coi_uni_a)
        res_coi_stream = self.client.get(f"/api/evidence/{doc.document_id}/document/")
        self.assertEqual(res_coi_stream.status_code, status.HTTP_403_FORBIDDEN)

        # 13D: Reviewer authorized only for College cannot stream University evidence
        self.client.force_authenticate(user=self.checker_col_only)
        res_fw_stream = self.client.get(f"/api/evidence/{doc.document_id}/document/")
        self.assertEqual(res_fw_stream.status_code, status.HTTP_403_FORBIDDEN)

        # 13E: Anonymous user is blocked with 401
        self.client.logout()
        res_anon_stream = self.client.get(f"/api/evidence/{doc.document_id}/document/")
        self.assertEqual(res_anon_stream.status_code, status.HTTP_401_UNAUTHORIZED)

    # =========================================================================
    # 14. Legacy nomination system is not involved
    # =========================================================================

    def test_14_legacy_nomination_system_is_not_involved(self):
        # Assert database has zero Nomination records
        self.assertEqual(Nomination.objects.count(), 0)

        # Modern review workflow executes completely
        uni_assess = self._create_submitted_university_assessment()
        doc = self._create_stored_evidence_doc(uni_assess, self.nodal_uni_a)
        assoc = EvidenceService.associate_subcriterion(
            evidence_id=doc.pk, parameter_id="U7", subcriterion_id="U7.1", actor=self.nodal_uni_a
        )

        self.client.force_authenticate(user=self.checker_all)
        self.client.post(f"/api/evidence/associations/{assoc.pk}/verify/", {"reason": "Verified"})

        # Still zero Nomination records
        self.assertEqual(Nomination.objects.count(), 0)

        # Calling inspect on a fake nomination ID is rejected by modern control plane
        res = self.client.get("/api/v1/admin/assessments/nomination-99999/inspect/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # =========================================================================
    # 15. Existing review completion remains functional
    # =========================================================================

    def test_15_existing_review_completion_remains_functional(self):
        uni_assess = self._create_submitted_university_assessment()

        self.client.force_authenticate(user=self.checker_all)

        # Start review endpoint
        res_start = self.client.post(
            f"/api/v1/university/university-assessments/{uni_assess.assessment_id}/start-review/",
            {"comments": "Commencing review on submitted assessment."},
            format="json",
        )
        self.assertEqual(res_start.status_code, status.HTTP_200_OK)
        self.assertEqual(res_start.data["assessment"]["status"], "UNDER_REVIEW")

        uni_assess.refresh_from_db()
        self.assertEqual(uni_assess.status, "UNDER_REVIEW")
        self.assertEqual(uni_assess.assigned_reviewer, self.checker_all)
