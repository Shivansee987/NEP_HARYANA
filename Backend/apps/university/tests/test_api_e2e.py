"""
Category 20 Test: Complete End-to-End University API Integration Flow.

Exercises the full lifecycle via HTTP REST API endpoints without mocking domain logic:
1. University creation (Admin)
2. Assessment creation (Nodal User)
3. Parameter input submission (U1: 15 degree programmes)
4. Evidence file upload (Phase 5E Evidence API)
5. Evidence subcriterion association (Phase 5E Evidence API)
6. Evidence submission for review (Phase 5E Evidence API)
7. Reviewer queue inspection (Reviewer)
8. Reviewer assignment (Admin)
9. Reviewer verification (Reviewer)
10. Assessment coverage inspection (Nodal User)
11. Assessment readiness inspection (Nodal User)
12. Authoritative scoring evaluation via frozen scoring engine (Reviewer)
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.evidence.models import ReviewerAuthorization
from apps.university.models import University, UniversityAssessment

User = get_user_model()


class UniversityAPIEndToEndIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin user
        self.admin = User.objects.create_user(
            email="super.admin@dhe.haryana.gov.in",
            full_name="State Super Admin",
            role="admin",
            password="SuperAdminPassword2026!",
        )

        # Committee reviewer
        self.reviewer = User.objects.create_user(
            email="dr.sharma.committee@haryana.gov.in",
            full_name="Dr. Sharma (Reviewer)",
            role="committee",
            password="ReviewerSecurePassword2026!",
        )
        ReviewerAuthorization.objects.create(
            user=self.reviewer,
            framework="UNIVERSITY_2026",
            institution_id="",
            is_active=True,
        )

    def test_complete_university_assessment_e2e_pipeline(self):
        # ---------------------------------------------------------------------
        # Step 1: University Creation (Admin)
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=self.admin)
        uni_payload = {
            "name": "Chaudhary Charan Singh Haryana Agricultural University",
            "aishe_code": "U-0166",
            "university_type": "State Public University",
            "state": "Haryana",
            "contact_email": "vc@ccshau.ac.in",
            "contact_phone": "01662-284301",
        }
        res_uni = self.client.post("/api/universities/", uni_payload, format="json")
        self.assertEqual(res_uni.status_code, status.HTTP_201_CREATED)
        uni_id = res_uni.data["id"]
        aishe_code = res_uni.data["aishe_code"]
        self.assertEqual(aishe_code, "U-0166")

        # ---------------------------------------------------------------------
        # Step 2: Create University Nodal User linked to this University
        # ---------------------------------------------------------------------
        uni_instance = University.objects.get(pk=uni_id)
        nodal_user = User.objects.create_user(
            email="nodal.ccshau@haryana.gov.in",
            full_name="CCSHAU Nodal Officer",
            role="nodal_officer",
            university=uni_instance,
            password="CCSHAUNodalPassword2026!",
        )

        # ---------------------------------------------------------------------
        # Step 3: Assessment Creation (Nodal User)
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=nodal_user)
        assess_payload = {
            "academic_year": "2025-26",
        }
        res_assess = self.client.post(
            f"/api/universities/{uni_id}/assessments/",
            assess_payload,
            format="json"
        )
        self.assertEqual(res_assess.status_code, status.HTTP_201_CREATED)
        assessment_id = res_assess.data["assessment_id"]
        self.assertEqual(res_assess.data["status"], "DRAFT")
        self.assertEqual(res_assess.data["framework"], "UNIVERSITY_2026")
        self.assertEqual(res_assess.data["period_start"], "2025-07-01")
        self.assertEqual(res_assess.data["period_end"], "2026-06-30")

        # ---------------------------------------------------------------------
        # Step 4: Parameter Input (Nodal User -> U1 Apprenticeship)
        # ---------------------------------------------------------------------
        param_payload = {
            "raw_inputs": {
                "programmes_count": 15,
                "U1.1": {"programmes_count": 15},
            },
            "entities": [
                {
                    "entity_id": "prog-agri-01",
                    "entity_type": "PROGRAMME",
                    "title": "B.Tech in Agricultural Engineering (Apprenticeship)",
                }
            ],
        }
        res_param = self.client.put(
            f"/api/university-assessments/{assessment_id}/parameters/U1/",
            param_payload,
            format="json"
        )
        self.assertEqual(res_param.status_code, status.HTTP_200_OK)
        self.assertEqual(res_param.data["code"], "U1")
        self.assertEqual(res_param.data["submitted_input"]["raw_inputs"]["programmes_count"], 15)

        # ---------------------------------------------------------------------
        # Step 5: Evidence File Upload (Nodal User -> Phase 5E Evidence API)
        # ---------------------------------------------------------------------
        pdf_content = b"%PDF-1.4 official approval document for apprenticeship embedded degree programmes"
        uploaded_file = SimpleUploadedFile(
            name="ccshau_u1_syndicate_approval.pdf",
            content=pdf_content,
            content_type="application/pdf",
        )
        upload_data = {
            "file": uploaded_file,
            "assessment_id": assessment_id,
            "framework": "UNIVERSITY_2026",
            "institution_type": "UNIVERSITY",
            "institution_id": aishe_code,
            "evidence_type": "EVID_U1_APPROVAL",
            "academic_year": "2025-26",
        }
        res_upload = self.client.post("/api/evidence/", upload_data, format="multipart")
        self.assertEqual(res_upload.status_code, status.HTTP_201_CREATED)
        doc_uuid = res_upload.data["document_id"]
        doc_status = res_upload.data["status"]
        self.assertEqual(doc_status, "EVIDENCE_PRESENT")

        # ---------------------------------------------------------------------
        # Step 6: Evidence Subcriterion Association (Nodal User)
        # ---------------------------------------------------------------------
        assoc_payload = {
            "parameter_id": "U1",
            "subcriterion_id": "U1.1",
            "academic_year": "2025-26",
        }
        res_assoc = self.client.post(
            f"/api/evidence/{doc_uuid}/associate/",
            assoc_payload,
            format="json"
        )
        self.assertEqual(res_assoc.status_code, status.HTTP_200_OK)

        # ---------------------------------------------------------------------
        # Step 7: Evidence Submission for Review (Nodal User)
        # ---------------------------------------------------------------------
        res_sub = self.client.post(f"/api/evidence/{doc_uuid}/submit/", {}, format="json")
        self.assertEqual(res_sub.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sub.data["status"], "EVIDENCE_PENDING")

        # ---------------------------------------------------------------------
        # Step 8: Reviewer Queue Inspection (Reviewer)
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=self.reviewer)
        res_queue = self.client.get("/api/evidence/review-queue/")
        self.assertEqual(res_queue.status_code, status.HTTP_200_OK)
        queue_items = res_queue.data.get("results", res_queue.data)
        queue_uuids = [item["document_id"] for item in queue_items]
        self.assertIn(doc_uuid, queue_uuids)

        # ---------------------------------------------------------------------
        # Step 9: Reviewer Assignment (Admin)
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=self.admin)
        res_assign = self.client.post(
            f"/api/evidence/{doc_uuid}/assign/",
            {"reviewer_id": self.reviewer.id},
            format="json"
        )
        self.assertEqual(res_assign.status_code, status.HTTP_200_OK)

        # ---------------------------------------------------------------------
        # Step 10: Evidence Verification (Reviewer)
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=self.reviewer)
        res_verify = self.client.post(
            f"/api/evidence/{doc_uuid}/verify/",
            {
                "reason": "Syndicate resolution confirmed for 15 degree programmes.",
            },
            format="json"
        )
        self.assertEqual(res_verify.status_code, status.HTTP_200_OK)
        self.assertEqual(res_verify.data["resulting_state"], "EVIDENCE_VERIFIED")

        # ---------------------------------------------------------------------
        # Step 11: Assessment Coverage Inspection (Nodal User)
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=nodal_user)
        res_cov = self.client.get(f"/api/university-assessments/{assessment_id}/coverage/")
        self.assertEqual(res_cov.status_code, status.HTTP_200_OK)
        cov_summary = res_cov.data["summary"]
        self.assertGreaterEqual(cov_summary["verified_subcriteria"], 1)

        # ---------------------------------------------------------------------
        # Step 12: Assessment Readiness Inspection (Nodal User)
        # ---------------------------------------------------------------------
        res_readiness = self.client.get(f"/api/university-assessments/{assessment_id}/readiness/")
        self.assertEqual(res_readiness.status_code, status.HTTP_200_OK)
        self.assertEqual(res_readiness.data["framework"], "UNIVERSITY_2026")
        self.assertIn("evidence_readiness_summary", res_readiness.data)

        # ---------------------------------------------------------------------
        # Step 13: Scoring Evaluation via Frozen Scoring Engine (Reviewer)
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=self.reviewer)
        res_eval = self.client.post(
            f"/api/university-assessments/{assessment_id}/evaluate/",
            {},
            format="json"
        )
        self.assertEqual(res_eval.status_code, status.HTTP_200_OK)
        eval_data = res_eval.data
        self.assertEqual(eval_data["framework"], "UNIVERSITY_2026")
        self.assertEqual(eval_data["assessment_id"], assessment_id)
        self.assertEqual(eval_data["institution_id"], aishe_code)

        # Parameter U1: 15 programmes > 10 threshold => 4.0 max marks unlocked
        u1_res = eval_data["parameter_results"]["U1"]
        self.assertEqual(u1_res["evidence_gated_score"], 4.0)
        self.assertEqual(eval_data["evidence_gated_total"], 4.0)

        # ---------------------------------------------------------------------
        # Step 14: Verification of Persisted Assessment State in DB
        # ---------------------------------------------------------------------
        assessment_db = UniversityAssessment.objects.get(assessment_id=assessment_id)
        self.assertEqual(assessment_db.certified_score, Decimal("4.0"))
        self.assertIsNotNone(assessment_db.certification_status)
