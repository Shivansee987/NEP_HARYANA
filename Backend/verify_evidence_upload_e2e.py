"""
End-to-End Verification Test Script: Evidence Upload & Verification Pipeline
Tests the complete lifecycle:
1. College Demo Authentication (principal@dev.local)
2. Evidence upload using real PDF (AkashIML.pdf)
3. Deterministic canonical evidence derivation (EVID_C1_APPROVED_IDP)
4. Association creation with PENDING verification status and complete citation metadata
5. Assessment submission (DRAFT -> SUBMITTED)
6. Checker authentication (checker@dev.local)
7. Queue visibility, document streaming, and independent association verification (PENDING -> VERIFIED)
8. Comprehensive negative test suite (arbitrary type, OFFICIAL_RECORD, cross-framework, source-silent, quarantined)
"""
import os
import sys
import uuid
import django
from io import BytesIO

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")

from django.test import Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.authentication.models import College
from apps.college.models import CollegeAssessment

from apps.evidence.models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    EvidenceAssociationVerification,
)
from apps.evidence.enums import VerificationDecision, RejectionReasonCode
from apps.evidence.taxonomy import (
    get_subcriterion_contract,
    derive_or_validate_evidence_type,
    ALL_EVIDENCE_TYPES,
)

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

def get_auth_client(user):
    c = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return c

def run_tests():
    print("=" * 70)
    print("STARTING NEP 2026 EVIDENCE UPLOAD & VERIFICATION E2E SUITE")
    print("=" * 70)

    # ---------------------------------------------------------
    # 0. User & Assessment Pre-conditions
    # ---------------------------------------------------------
    principal = User.objects.filter(email="principal@dev.local").first()
    assert principal is not None, "principal@dev.local must exist in dev database"
    assert principal.college is not None, "principal must be associated with a college"
    college = principal.college
    aishe_code = college.aishe_code

    checker = User.objects.filter(email="checker@dev.local").first()
    if not checker:
        checker = User.objects.create_user(
            email="checker@dev.local",
            full_name="Dev Checker",
            role="committee",
            password="DevChecker@123"
        )

    # Ensure an active DRAFT assessment for College 2026
    session = CollegeAssessment.objects.filter(college=college, academic_year="2025-26").first()
    if not session:
        session = CollegeAssessment.objects.create(
            assessment_id=f"COL-ASSESS-{aishe_code}-2026",
            college=college,
            academic_year="2025-26",
            status="DRAFT",
        )
    else:
        if session.status != "DRAFT":
            session.status = "DRAFT"
            session.save(update_fields=['status'])

    assessment_id = session.assessment_id
    print(f"[OK] College Demo Assessment Ready: ID={assessment_id}, College={college.name} ({aishe_code})")

    # ---------------------------------------------------------
    # 1. Test PDF Source Resolution
    # ---------------------------------------------------------
    pdf_path = r"C:\Users\Devansh Datta\Downloads\AkashIML.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        filename = "AkashIML.pdf"
        print(f"[OK] Using real production test document: {filename} ({len(pdf_bytes):,} bytes)")
    else:
        # Fallback to valid PDF bytes if path moved
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        filename = "test_document.pdf"
        print(f"[NOTE] Using fallback valid PDF bytes: {filename} ({len(pdf_bytes)} bytes)")

    # ---------------------------------------------------------
    # 2. Canonical Evidence Contract Resolution for C1.1
    # ---------------------------------------------------------
    contract_c1_1 = get_subcriterion_contract("COLLEGE_2026", "C1", "C1.1")
    assert contract_c1_1 is not None, "Contract for C1.1 must exist in backend taxonomy"
    canonical_type = contract_c1_1.canonical_evidence_type
    print(f"[OK] Subcriterion C1.1 Authoritative Canonical Evidence Type: '{canonical_type}'")
    assert canonical_type == "EVID_C1_APPROVED_IDP"

    # ---------------------------------------------------------
    # 3. Successful Upload & Direct Association
    # ---------------------------------------------------------
    client = get_auth_client(principal)
    uploaded_file = SimpleUploadedFile(
        filename,
        pdf_bytes,
        content_type="application/pdf"
    )

    upload_payload = {
        "file": uploaded_file,
        "assessment_id": assessment_id,
        "framework": "COLLEGE_2026",
        "institution_type": "COLLEGE",
        "institution_id": aishe_code,
        "evidence_type": canonical_type,
        "document_date": "2025-10-15",
        "academic_year": "2025-26",
        "parameter_id": "C1",
        "subcriterion_id": "C1.1",
    }

    res_upload = client.post("/api/evidence/", upload_payload, format="multipart")
    print(f"Upload API Status: {res_upload.status_code}")
    if res_upload.status_code != 201:
        print("Upload Error Response:", res_upload.data)
    assert res_upload.status_code == 201, f"Expected 201 Created, got {res_upload.status_code}"

    doc_data = res_upload.data
    doc_uuid = doc_data["document_id"]
    print(f"[OK] Evidence Document Created: UUID={doc_uuid}, type={doc_data['evidence_type']}")
    assert doc_data["evidence_type"] == "EVID_C1_APPROVED_IDP"
    assert len(doc_data["associations"]) > 0, "Association to C1.1 must be created automatically"
    assoc_info = doc_data["associations"][0]
    assert assoc_info["parameter_id"] == "C1"
    assert assoc_info["subcriterion_id"] == "C1.1"

    # ---------------------------------------------------------
    # 4. Association Metadata Update (Page Numbers, Section, Claim)
    # ---------------------------------------------------------
    assoc_update_payload = {
        "parameter_id": "C1",
        "subcriterion_id": "C1.1",
        "academic_year": "2025-26",
        "evidence_type": canonical_type,
        "subcriterion_evidence_type": canonical_type,
        "page_start": 1,
        "page_end": 5,
        "section_identifier": "Section 2.3",
        "claim_description": "Approved IDP target documentation for AY 2024-25",
    }
    res_assoc = client.post(f"/api/evidence/{doc_uuid}/associate/", assoc_update_payload, content_type="application/json")
    assert res_assoc.status_code == 200, f"Expected 200 OK from association update, got {res_assoc.status_code}"
    print(f"[OK] Association Citation Metadata Updated: Pages 1-5, Section 2.3")

    # ---------------------------------------------------------
    # 5. Query Associations Endpoint & Verification Status PENDING
    # ---------------------------------------------------------
    res_assocs = client.get(f"/api/evidence/associations/?assessment_id={assessment_id}")
    assert res_assocs.status_code == 200
    assocs_list = res_assocs.data if isinstance(res_assocs.data, list) else res_assocs.data.get("results", [])
    target_assoc = next((a for a in assocs_list if a["subcriterion_id"] == "C1.1"), None)
    assert target_assoc is not None, "Association C1.1 must appear in assessment associations"
    print(f"[OK] Association Confirmed in Assessment: ID={target_assoc['id']}, Subcriterion={target_assoc['subcriterion_id']}")
    print(f"     Subcriterion Evidence Type: {target_assoc['subcriterion_evidence_type']}")
    print(f"     Latest Verification Status: {target_assoc.get('verification_status') or 'PENDING (Unreviewed)'}")
    assert target_assoc["subcriterion_evidence_type"] == "EVID_C1_APPROVED_IDP"

    # ---------------------------------------------------------
    # 6. Institution CANNOT Verify Own Evidence (Fail-closed)
    # ---------------------------------------------------------
    res_unauth_verify = client.post(f"/api/evidence/associations/{target_assoc['id']}/verify/", {"reason": "Self-approval"})
    assert res_unauth_verify.status_code in (401, 403), f"Institution must be forbidden from verifying evidence (got {res_unauth_verify.status_code})"
    print("[OK] Negative Check: Institution role cannot verify evidence (HTTP 403 Forbidden)")

    # ---------------------------------------------------------
    # 7. Submit Assessment
    # ---------------------------------------------------------
    res_submit = client.post(f"/api/college/assessments/{assessment_id}/submit/", {}, content_type="application/json")
    assert res_submit.status_code == 200, f"Assessment submission failed: {res_submit.data}"
    session.refresh_from_db()
    assert session.status == "SUBMITTED", "Session status must be SUBMITTED"
    print(f"[OK] Assessment Submitted Successfully: Status={session.status}")

    # ---------------------------------------------------------
    # 8. Checker Login & Queue Inspection
    # ---------------------------------------------------------
    checker_client = get_auth_client(checker)
    res_queue = checker_client.get("/api/evidence/review-queue/")
    assert res_queue.status_code == 200, f"Failed to retrieve reviewer queue: {res_queue.data}"
    print(f"[OK] Checker Queue Retrieved Successfully ({len(res_queue.data)} entries)")

    # ---------------------------------------------------------
    # 9. Checker View Document via Secure Streaming Path
    # ---------------------------------------------------------
    res_stream = checker_client.get(f"/api/evidence/associations/{target_assoc['id']}/document/")
    assert res_stream.status_code == 200, f"Failed to stream document for association {target_assoc['id']}: {res_stream.status_code}"
    assert res_stream["Content-Type"] == "application/pdf"
    content_len = len(res_stream.content)
    print(f"[OK] Checker Opened & Streamed Document: {content_len:,} bytes (Matches uploaded PDF)")
    assert content_len == len(pdf_bytes)

    # ---------------------------------------------------------
    # 10. Checker Approves / Verifies Association
    # ---------------------------------------------------------
    verify_payload = {
        "reason": "Statutory IDP targets verified against official council documentation guidelines."
    }
    res_verify = checker_client.post(f"/api/evidence/associations/{target_assoc['id']}/verify/", verify_payload, format="json")
    assert res_verify.status_code == 200, f"Checker verify action failed: {res_verify.data}"
    verify_data = res_verify.data
    print(f"[OK] Checker Verification Recorded: Decision={verify_data.get('decision')}, verifier={checker.email}")
    assert verify_data.get("decision") == "VERIFIED"

    # Re-fetch association to confirm latest verification status is VERIFIED
    res_assocs_post = checker_client.get(f"/api/evidence/associations/?assessment_id={assessment_id}")
    assocs_post_list = res_assocs_post.data if isinstance(res_assocs_post.data, list) else res_assocs_post.data.get("results", [])
    updated_target = next((a for a in assocs_post_list if a["id"] == target_assoc["id"]), None)
    assert updated_target is not None
    assert updated_target["verification_status"] == "VERIFIED"
    print(f"[OK] Association Verification Status Confirmed: VERIFIED")

    # =========================================================
    # NEGATIVE TEST SUITE
    # =========================================================
    print("-" * 70)
    print("RUNNING NEGATIVE TEST SCENARIOS")
    print("-" * 70)

    client = get_auth_client(principal)

    # Reset assessment to DRAFT for negative upload tests
    session.status = "DRAFT"
    session.save(update_fields=['status'])

    # Neg 1: Arbitrary evidence_type must be rejected
    res_neg1 = client.post("/api/evidence/", {
        "file": SimpleUploadedFile("dummy.pdf", b"%PDF-1.4 dummy", content_type="application/pdf"),
        "assessment_id": assessment_id,
        "framework": "COLLEGE_2026",
        "evidence_type": "ARBITRARY_EVIDENCE_TYPE_123",
        "parameter_id": "C1",
        "subcriterion_id": "C1.1",
    }, format="multipart")
    assert res_neg1.status_code == 400
    print("[OK] Neg 1 PASS: Arbitrary evidence_type rejected (HTTP 400)")

    # Neg 2: OFFICIAL_RECORD must be strictly rejected
    res_neg2 = client.post("/api/evidence/", {
        "file": SimpleUploadedFile("dummy.pdf", b"%PDF-1.4 dummy", content_type="application/pdf"),
        "assessment_id": assessment_id,
        "framework": "COLLEGE_2026",
        "evidence_type": "OFFICIAL_RECORD",
        "parameter_id": "C1",
        "subcriterion_id": "C1.1",
    }, format="multipart")
    assert res_neg2.status_code == 400
    err_msg = str(res_neg2.data)
    assert "OFFICIAL_RECORD" in err_msg and "Must be a recognized NEP 2026 evidence identifier" in err_msg
    print("[OK] Neg 2 PASS: 'OFFICIAL_RECORD' strictly rejected (HTTP 400, Unknown evidence_type)")

    # Neg 3: Wrong framework evidence rejected (University evidence on College assessment)
    res_neg3 = client.post("/api/evidence/", {
        "file": SimpleUploadedFile("dummy.pdf", b"%PDF-1.4 dummy", content_type="application/pdf"),
        "assessment_id": assessment_id,
        "framework": "COLLEGE_2026",
        "evidence_type": "EVID_U1_SYNDICATE_APPROVAL",
        "parameter_id": "C1",
        "subcriterion_id": "C1.1",
    }, format="multipart")
    assert res_neg3.status_code == 400
    print("[OK] Neg 3 PASS: Cross-framework evidence rejected (HTTP 400)")

    # Neg 4: Wrong parameter evidence rejected (e.g. C2 evidence on C1)
    res_neg4 = client.post("/api/evidence/", {
        "file": SimpleUploadedFile("dummy.pdf", b"%PDF-1.4 dummy", content_type="application/pdf"),
        "assessment_id": assessment_id,
        "framework": "COLLEGE_2026",
        "evidence_type": "EVID_C2_HOI_CERT",
        "parameter_id": "C1",
        "subcriterion_id": "C1.1",
    }, format="multipart")
    assert res_neg4.status_code == 400
    print("[OK] Neg 4 PASS: Parameter/subcriterion mismatch rejected (HTTP 400)")

    # Neg 5: Evidence upload on SOURCE_SILENT subcriterion rejected (C5.1)
    res_neg5 = client.post("/api/evidence/", {
        "file": SimpleUploadedFile("dummy.pdf", b"%PDF-1.4 dummy", content_type="application/pdf"),
        "assessment_id": assessment_id,
        "framework": "COLLEGE_2026",
        "parameter_id": "C5",
        "subcriterion_id": "C5.1",
    }, format="multipart")
    assert res_neg5.status_code == 400
    print("[OK] Neg 5 PASS: Source-silent subcriterion upload rejected (HTTP 400)")

    # Neg 6: Evidence upload on UNRESOLVED_MISSING subcriterion rejected (C19.III)
    res_neg6 = client.post("/api/evidence/", {
        "file": SimpleUploadedFile("dummy.pdf", b"%PDF-1.4 dummy", content_type="application/pdf"),
        "assessment_id": assessment_id,
        "framework": "COLLEGE_2026",
        "parameter_id": "C19",
        "subcriterion_id": "C19.III",
    }, format="multipart")
    assert res_neg6.status_code == 400
    print("[OK] Neg 6 PASS: Unresolved subcriterion upload rejected (HTTP 400)")

    # Neg 7: Quarantined legacy evidence EVID_GENERAL rejected
    res_neg7 = client.post("/api/evidence/", {
        "file": SimpleUploadedFile("dummy.pdf", b"%PDF-1.4 dummy", content_type="application/pdf"),
        "assessment_id": assessment_id,
        "framework": "COLLEGE_2026",
        "evidence_type": "EVID_GENERAL",
        "parameter_id": "C1",
        "subcriterion_id": "C1.1",
    }, format="multipart")
    assert res_neg7.status_code == 400
    print("[OK] Neg 7 PASS: Quarantined legacy EVID_GENERAL rejected (HTTP 400)")

    print("=" * 70)
    print("ALL E2E WORKFLOW AND NEGATIVE TEST SCENARIOS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
