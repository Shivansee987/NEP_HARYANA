"""
Workflow Phase W4 — Acceptance Verification Test Suite
Executes the exact 13-step practical acceptance workflow defined in Phase W4:

1. Login as checker
2. Open review queue
3. Open a submitted assessment
4. Select a subcriterion
5. Open its evidence
6. View document
7. Verify one association
8. Reject another association with feedback
9. Confirm sibling association is unchanged
10. View history
11. Navigate to another association
12. Return to queue
13. Confirm assessment remains in correct state
"""
import hashlib
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import College
from apps.evidence.enums import EvidenceLifecycleState
from apps.evidence.models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.evidence.storage import get_evidence_storage
from apps.university.models import University, UniversityAssessment

User = get_user_model()


class WorkflowW4AcceptanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Create Checker User
        self.checker_user = User.objects.create_user(
            email="committee@dev.local",
            full_name="State Screening Reviewer",
            role="committee",
            password="DevCommittee@123",
        )
        ReviewerAuthorization.objects.create(
            user=self.checker_user,
            framework="ALL",
            is_active=True,
        )

        # 2. Create University & Assessment
        self.uni = University.objects.create(
            name="Dev Test University",
            aishe_code="U-DEV-001",
            state="Haryana",
            is_active=True,
        )
        self.nodal = User.objects.create_user(
            email="nodal@dev.local",
            full_name="Nodal Officer",
            role="university",
            university=self.uni,
            password="DevNodal@123",
        )
        self.assessment = UniversityAssessment.objects.create(
            assessment_id="ASSESS-2026-UNI-DEV-001",
            university=self.uni,
            framework="UNIVERSITY_2026",
            academic_year="2025-26",
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="SUBMITTED",
            submitted_at=timezone.now(),
            parameter_data={
                "U1": {"raw_inputs": {"U1.1": {"achieved": 90}, "U1.2": {"minors": 14}}},
                "U2": {"raw_inputs": {"U2.1": {"pop_count": 6}}},
            },
        )

        # 3. Store valid PDF documents in vault
        self.pdf_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>\nendobj\n"
            b"4 0 obj\n<< /Length 55 >>\nstream\n"
            b"BT /F1 12 Tf 72 712 Td (NEP 2026 Haryana Official Evidence Document) Tj ET\n"
            b"endstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
            b"0000000115 00000 n \n0000000216 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n321\n%%EOF\n"
        )
        self.pdf_checksum = hashlib.sha256(self.pdf_bytes).hexdigest()
        storage = get_evidence_storage()

        # Doc 1: Curriculum Revision
        storage_key_1 = f"evidence/UNIVERSITY_2026/{self.assessment.assessment_id}/{self.pdf_checksum[:2]}/{self.pdf_checksum}_curriculum.pdf"
        storage.save(storage_key_1, self.pdf_bytes, mime_type="application/pdf")
        self.doc1 = EvidenceDocument.objects.create(
            assessment_id=self.assessment.assessment_id,
            uploader=self.nodal,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.uni.aishe_code,
            file_path=storage_key_1,
            original_filename="curriculum_revision_u1_1.pdf",
            file_size=len(self.pdf_bytes),
            file_checksum=self.pdf_checksum,
            mime_type="application/pdf",
            status=EvidenceLifecycleState.EVIDENCE_PENDING,
            document_date=timezone.now().date(),
            academic_year="2025-26",
            is_active=True,
        )

        # Doc 2: PoP Orders
        storage_key_2 = f"evidence/UNIVERSITY_2026/{self.assessment.assessment_id}/{self.pdf_checksum[:2]}/{self.pdf_checksum}_pop.pdf"
        storage.save(storage_key_2, self.pdf_bytes, mime_type="application/pdf")
        self.doc2 = EvidenceDocument.objects.create(
            assessment_id=self.assessment.assessment_id,
            uploader=self.nodal,
            framework="UNIVERSITY_2026",
            institution_type="UNIVERSITY",
            institution_id=self.uni.aishe_code,
            file_path=storage_key_2,
            original_filename="pop_orders_u2_1.pdf",
            file_size=len(self.pdf_bytes),
            file_checksum=self.pdf_checksum,
            mime_type="application/pdf",
            status=EvidenceLifecycleState.EVIDENCE_PENDING,
            document_date=timezone.now().date(),
            academic_year="2025-26",
            is_active=True,
        )

        # Associations:
        # U1.1 (under U1)
        self.assoc_u1_1 = EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc1,
            parameter_id="U1",
            subcriterion_id="U1.1",
            associated_by=self.nodal,
            subcriterion_evidence_type="EVID_U1_CURRICULUM_DOC",
            page_start=1,
            page_end=4,
            section_identifier="Annexure A - Syllabus",
            claim_description="Approved curriculum restructuring under NEP 2020.",
            academic_year="2025-26",
            is_active=True,
        )
        # U1.2 (sibling under U1)
        self.assoc_u1_2 = EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc1,
            parameter_id="U1",
            subcriterion_id="U1.2",
            associated_by=self.nodal,
            subcriterion_evidence_type="EVID_U1_PROGRAM_LIST",
            page_start=2,
            page_end=6,
            section_identifier="Resolution 14/B",
            claim_description="Approval of 14 multidisciplinary minor combinations.",
            academic_year="2025-26",
            is_active=True,
        )
        # U2.1 (under U2)
        self.assoc_u2_1 = EvidenceSubcriterionAssociation.objects.create(
            evidence=self.doc2,
            parameter_id="U2",
            subcriterion_id="U2.1",
            associated_by=self.nodal,
            subcriterion_evidence_type="EVID_U2_POP_APPOINTMENT",
            page_start=1,
            page_end=3,
            section_identifier="EC Order #882",
            claim_description="Appointment orders of Professors of Practice.",
            academic_year="2025-26",
            is_active=True,
        )

    def test_complete_w4_checker_acceptance_flow(self):
        """
        Executes all 13 points of the Phase W4 Manual Acceptance Test end-to-end.
        """
        # =====================================================================
        # Step 1: Login as checker
        # =====================================================================
        login_resp = self.client.post(
            "/api/auth/login/",
            {"email": "committee@dev.local", "password": "DevCommittee@123"},
            format="json",
        )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        access_token = login_resp.data.get("access") or login_resp.data.get("tokens", {}).get("access")
        self.assertIsNotNone(access_token, "Checker login must yield access token")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # =====================================================================
        # Step 2: Open review queue
        # =====================================================================
        queue_resp = self.client.get("/api/v1/admin/review-queue/")
        self.assertEqual(queue_resp.status_code, status.HTTP_200_OK)
        queue_results = queue_resp.data.get("results", queue_resp.data)
        assessment_ids = [item["assessment_id"] for item in queue_results]
        self.assertIn(self.assessment.assessment_id, assessment_ids)

        # =====================================================================
        # Step 3: Open submitted assessment
        # =====================================================================
        inspect_resp = self.client.get(
            f"/api/v1/admin/assessments/{self.assessment.assessment_id}/inspect/"
        )
        self.assertEqual(inspect_resp.status_code, status.HTTP_200_OK)
        inspect_data = inspect_resp.data
        self.assertEqual(inspect_data["assessment_id"], self.assessment.assessment_id)
        self.assertEqual(inspect_data["framework"], "UNIVERSITY_2026")
        self.assertEqual(inspect_data["status"], "SUBMITTED")
        self.assertEqual(inspect_data["institution"]["name"], "Dev Test University")
        self.assertIn("evidence_associations", inspect_data)
        assocs = inspect_data["evidence_associations"]
        self.assertEqual(len(assocs), 3)

        # =====================================================================
        # Step 4: Select a subcriterion
        # =====================================================================
        target_subcriterion = "U1.1"
        u1_1_assocs = [a for a in assocs if a["subcriterion_id"] == target_subcriterion]
        self.assertEqual(len(u1_1_assocs), 1)

        # =====================================================================
        # Step 5: Open its evidence
        # =====================================================================
        target_assoc = u1_1_assocs[0]
        self.assertEqual(target_assoc["verification_status"], "PENDING")
        filename = target_assoc.get("original_filename") or target_assoc.get("evidence", {}).get("original_filename")
        self.assertEqual(filename, "curriculum_revision_u1_1.pdf")
        self.assertEqual(target_assoc["page_start"], 1)
        self.assertEqual(target_assoc["page_end"], 4)

        # =====================================================================
        # Step 6: View document
        # =====================================================================
        doc_resp = self.client.get(f"/api/evidence/associations/{target_assoc['id']}/document/")
        self.assertEqual(doc_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(doc_resp["Content-Type"], "application/pdf")
        self.assertTrue(doc_resp.content.startswith(b"%PDF"))

        # =====================================================================
        # Step 7: Verify one association
        # =====================================================================
        verify_resp = self.client.post(
            f"/api/evidence/associations/{target_assoc['id']}/verify/",
            {"reason": "Curriculum revision officially verified by screening committee."},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_resp.data["verification_status"], "VERIFIED")

        # =====================================================================
        # Step 8: Reject another association with feedback
        # =====================================================================
        sibling_assoc = next(a for a in assocs if a["subcriterion_id"] == "U1.2")
        reject_resp = self.client.post(
            f"/api/evidence/associations/{sibling_assoc['id']}/reject/",
            {
                "reason": "Missing Academic Council ratification signature on page 4.",
                "rejection_code": "UNAUTHORIZED_SIGNATORY",
            },
            format="json",
        )
        self.assertEqual(reject_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_resp.data["verification_status"], "REJECTED")
        self.assertEqual(reject_resp.data["rejection_code"], "UNAUTHORIZED_SIGNATORY")
        self.assertEqual(
            reject_resp.data["reason"],
            "Missing Academic Council ratification signature on page 4.",
        )

        # =====================================================================
        # Step 9: Confirm sibling association is unchanged
        # =====================================================================
        u2_1_assoc = next(a for a in assocs if a["subcriterion_id"] == "U2.1")
        detail_u2_1 = self.client.get(f"/api/evidence/associations/{u2_1_assoc['id']}/")
        self.assertEqual(detail_u2_1.status_code, status.HTTP_200_OK)
        self.assertIn(
            detail_u2_1.data["verification_status"],
            [None, "PENDING"],
            "Independent association U2.1 must remain PENDING/unreviewed",
        )

        # Also confirm U1.1 remains VERIFIED despite sibling U1.2 rejection
        detail_u1_1 = self.client.get(f"/api/evidence/associations/{target_assoc['id']}/")
        self.assertEqual(detail_u1_1.status_code, status.HTTP_200_OK)
        self.assertEqual(
            detail_u1_1.data["verification_status"],
            "VERIFIED",
            "Association U1.1 must remain VERIFIED",
        )

        # =====================================================================
        # Step 10: View history
        # =====================================================================
        history_resp = self.client.get(f"/api/evidence/associations/{sibling_assoc['id']}/history/")
        self.assertEqual(history_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(history_resp.data), 1)
        latest_event = history_resp.data[0]
        self.assertEqual(latest_event["decision"], "REJECTED")
        self.assertEqual(latest_event["rejection_code"], "UNAUTHORIZED_SIGNATORY")
        self.assertEqual(
            latest_event["reason"],
            "Missing Academic Council ratification signature on page 4.",
        )
        self.assertEqual(latest_event["verifier_email"], "committee@dev.local")

        # =====================================================================
        # Step 11: Navigate to another association
        # =====================================================================
        nav_assoc = next(a for a in assocs if a["subcriterion_id"] == "U2.1")
        doc_u2_resp = self.client.get(f"/api/evidence/associations/{nav_assoc['id']}/document/")
        self.assertEqual(doc_u2_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(doc_u2_resp["Content-Type"], "application/pdf")

        # =====================================================================
        # Step 12: Return to queue
        # =====================================================================
        queue_return_resp = self.client.get("/api/v1/admin/review-queue/")
        self.assertEqual(queue_return_resp.status_code, status.HTTP_200_OK)

        # =====================================================================
        # Step 13: Confirm assessment remains in correct state
        # =====================================================================
        final_inspect = self.client.get(
            f"/api/v1/admin/assessments/{self.assessment.assessment_id}/inspect/"
        )
        self.assertEqual(final_inspect.status_code, status.HTTP_200_OK)
        self.assertEqual(final_inspect.data["status"], "SUBMITTED")
        final_assocs = final_inspect.data["evidence_associations"]

        status_by_subcriterion = {a["subcriterion_id"]: a["verification_status"] for a in final_assocs}
        self.assertEqual(status_by_subcriterion["U1.1"], "VERIFIED")
        self.assertEqual(status_by_subcriterion["U1.2"], "REJECTED")
        self.assertEqual(status_by_subcriterion["U2.1"], "PENDING")
