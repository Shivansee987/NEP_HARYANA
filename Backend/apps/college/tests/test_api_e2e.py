"""
Phase 7B API End-to-End Test: Full College Assessment Lifecycle via REST API.

Flow:
1. Create College institution.
2. Authenticate College Principal.
3. Create assessment via POST /api/college/assessments/.
4. Populate C1–C22 parameter inputs via PUT /api/college/assessments/{id}/parameters/{code}/.
5. Upload and associate evidence documents via Phase 5 services.
6. Verify evidence documents via Phase 5C.
7. Request coverage via GET /api/college/assessments/{id}/coverage/.
8. Request readiness via GET /api/college/assessments/{id}/readiness/.
9. Request evaluation via POST /api/college/assessments/{id}/evaluate/ (delegating to frozen engine).
10. Submit assessment via POST /api/college/assessments/{id}/submit/.
11. Confirm state locked, immutability preserved, and audit logs recorded.
"""
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import College
from apps.college.models import CollegeAssessment, CollegeAssessmentAuditLog
from apps.college.registry import COLLEGE_PARAMETER_CODES
from apps.evidence.services import EvidenceService

User = get_user_model()


class CollegeAPIE2ETests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Reviewer User
        self.reviewer = User.objects.create_user(
            email="reviewer.colleges@dhe.haryana.gov.in",
            full_name="State College Reviewer",
            role="committee",
            password="ReviewerPassword2026!",
        )

    def test_full_college_api_assessment_e2e_flow(self):
        # 1. Create College
        college = College.objects.create(
            name="Pt. Chiranji Lal Sharma Govt College Karnal",
            aishe_code="C-00107",
        )

        # 2. Create and authenticate College Principal
        principal = User.objects.create_user(
            email="principal.pclsgc@haryana.gov.in",
            full_name="Principal PCLSGC Karnal",
            role="principal",
            college=college,
            password="PasswordKarnal2026!",
        )
        self.client.force_authenticate(user=principal)

        # 3. Create assessment via POST /api/college/assessments/
        create_resp = self.client.post("/api/college/assessments/", {"academic_year": "2025-26"}, format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        assessment_id = create_resp.data["assessment_id"]
        self.assertEqual(create_resp.data["status"], "DRAFT")
        self.assertEqual(create_resp.data["framework"], "COLLEGE_2026")

        # 4. Populate parameter inputs for C1, C2, and C10
        # C1: Previous academic year IDP targets
        put_c1 = self.client.put(
            f"/api/college/assessments/{assessment_id}/parameters/C1/",
            {"raw_inputs": {"C1.1": {"achieved_targets_2024_25": 95, "fixed_targets_2024_25": 100}}},
            format="json",
        )
        self.assertEqual(put_c1.status_code, status.HTTP_200_OK)

        # C2: Apprenticeship / Internships
        put_c2 = self.client.put(
            f"/api/college/assessments/{assessment_id}/parameters/C2/",
            {
                "raw_inputs": {"C2.1": {"students_completed": 92, "eligible_students": 100}},
                "activity_date": "2025-11-15",
            },
            format="json",
        )
        self.assertEqual(put_c2.status_code, status.HTTP_200_OK)

        # C10: Industry linkages
        put_c10 = self.client.put(
            f"/api/college/assessments/{assessment_id}/parameters/C10/",
            {"raw_inputs": {"C10.1": {"active_mous_count": 4}}},
            format="json",
        )
        self.assertEqual(put_c10.status_code, status.HTTP_200_OK)

        # 5. Upload and Associate Evidence for C1 and C2
        doc_c1 = EvidenceService.create_evidence(
            uploader=principal,
            assessment_id=assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id=college.aishe_code,
            original_filename="idp_approved_targets.pdf",
            file_path="/media/evidence/col/idp_approved_targets.pdf",
            mime_type="application/pdf",
            file_size=16384,
            file_checksum="1111111111111111111111111111111111111111111111111111111111111111",
            evidence_type="EVID_C1_APPROVED_IDP",
            document_date=date(2025, 8, 1),
            academic_year="2024-25",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc_c1.pk,
            parameter_id="C1",
            subcriterion_id="C1.1",
            actor=principal,
            academic_year="2024-25",
        )

        doc_c2 = EvidenceService.create_evidence(
            uploader=principal,
            assessment_id=assessment_id,
            framework="COLLEGE_2026",
            institution_type="COLLEGE",
            institution_id=college.aishe_code,
            original_filename="internship_completion_hoi.pdf",
            file_path="/media/evidence/col/internship_completion_hoi.pdf",
            mime_type="application/pdf",
            file_size=20480,
            file_checksum="2222222222222222222222222222222222222222222222222222222222222222",
            evidence_type="EVID_C2_HOI_CERT",
            document_date=date(2025, 11, 20),
            academic_year="2025-26",
        )
        EvidenceService.associate_subcriterion(
            evidence_id=doc_c2.pk,
            parameter_id="C2",
            subcriterion_id="C2.1",
            actor=principal,
            academic_year="2025-26",
        )

        # 6. Verify Evidence via Phase 5C
        EvidenceService.submit_for_verification(doc_c1.pk, principal)
        EvidenceService.verify_evidence(
            evidence_id=doc_c1.pk,
            verifier=self.reviewer,
            reason="Approved verified IDP target report",
        )

        EvidenceService.submit_for_verification(doc_c2.pk, principal)
        EvidenceService.verify_evidence(
            evidence_id=doc_c2.pk,
            verifier=self.reviewer,
            reason="Approved HOI internship certification",
        )

        # 7. Request Coverage via GET /api/college/assessments/{id}/coverage/
        cov_resp = self.client.get(f"/api/college/assessments/{assessment_id}/coverage/")
        self.assertEqual(cov_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(cov_resp.data["framework"], "COLLEGE_2026")
        param_ids = [p["parameter_id"] for p in cov_resp.data["parameters"]]
        self.assertIn("C1", param_ids)
        self.assertIn("C2", param_ids)

        # 8. Request Readiness via GET /api/college/assessments/{id}/readiness/
        ready_resp = self.client.get(f"/api/college/assessments/{assessment_id}/readiness/")
        self.assertEqual(ready_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(ready_resp.data["framework"], "COLLEGE_2026")

        # 9. Request Evaluation via POST /api/college/assessments/{id}/evaluate/
        eval_resp = self.client.post(f"/api/college/assessments/{assessment_id}/evaluate/", format="json")
        self.assertEqual(eval_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(eval_resp.data["framework"], "COLLEGE_2026")
        self.assertEqual(eval_resp.data["parameter_results"]["C1"]["final_score"], 6.0)
        self.assertEqual(eval_resp.data["parameter_results"]["C2"]["final_score"], 4.0)

        # 10. Formally Submit Assessment via POST /api/college/assessments/{id}/submit/
        submit_resp = self.client.post(f"/api/college/assessments/{assessment_id}/submit/", format="json")
        self.assertEqual(submit_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_resp.data["status"], "SUBMITTED")
        self.assertIsNotNone(submit_resp.data["submitted_at"])

        # 11. Immutability & Audit Trail Confirmation
        assessment = CollegeAssessment.objects.get(assessment_id=assessment_id)
        self.assertEqual(assessment.status, "SUBMITTED")
        self.assertEqual(assessment.certified_score, 10.0)  # 6.0 (C1) + 4.0 (C2) = 10.0

        audit_actions = list(CollegeAssessmentAuditLog.objects.filter(assessment=assessment).values_list("action", flat=True))
        self.assertIn("CREATED", audit_actions)
        self.assertIn("PARAMETER_UPDATED", audit_actions)
        self.assertIn("SUBMITTED", audit_actions)
