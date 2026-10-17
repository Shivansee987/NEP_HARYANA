"""
NEP Excellence Awards 2026 - University Applicant Registration Test Suite
Tests AISHE lookup, registration security, institution identity, and isolation.
"""
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import College
from apps.authentication.test_utils import last_sms_code, verify_phone
from apps.university.models import University, UniversityAssessment
from apps.university.services import UniversityAssessmentService

User = get_user_model()


class UniversityRegistrationTests(TestCase):
    def _verified(self, payload, phone):
        """Adds a phone number verified through the real OTP flow to a registration payload."""
        token = verify_phone(self.client, phone)
        return {**payload, "phoneNumber": phone, "phoneVerificationToken": token}

    def setUp(self):
        self.client = APIClient()

        # Canonical Universities
        self.uni_a = University.objects.create(
            name="Kurukshetra University, Kurukshetra",
            aishe_code="U-0160",
            university_type="State Public University",
            state="Haryana",
            address="Kurukshetra, Haryana 136119",
            contact_email="registrar@kuk.ac.in",
            is_active=True,
        )
        self.uni_b = University.objects.create(
            name="Maharshi Dayanand University, Rohtak",
            aishe_code="U-0161",
            university_type="State Public University",
            state="Haryana",
            address="Rohtak, Haryana 124001",
            contact_email="registrar@mdu.ac.in",
            is_active=True,
        )
        self.uni_inactive = University.objects.create(
            name="Inactive University Example",
            aishe_code="U-0999",
            is_active=False,
        )

        # Canonical College
        self.college = College.objects.create(
            name="Government College Panchkula",
            aishe_code="C-10001",
        )

        # Existing State Admin
        self.admin_user = User.objects.create_user(
            email="admin@hshec.gov.in",
            full_name="State Admin HSHEC",
            role="admin",
            password="AdminPassword2026!",
            is_staff=True,
            is_superuser=True,
        )

    # =========================================================================
    # Phase 3: AISHE Lookup Tests
    # =========================================================================

    def test_valid_aishe_lookup(self):
        """Looking up a valid active University AISHE code returns canonical metadata."""
        # Exact code via GET query param
        res = self.client.get("/api/auth/university/lookup/", {"aishe_code": "U-0160"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["verified"])
        inst = res.data["institution"]
        self.assertEqual(inst["id"], self.uni_a.id)
        self.assertEqual(inst["name"], self.uni_a.name)
        self.assertEqual(inst["aishe_code"], "U-0160")
        self.assertEqual(inst["university_type"], "State Public University")
        self.assertEqual(inst["state"], "Haryana")

        # Case-insensitive with whitespace normalization
        res_norm = self.client.get("/api/auth/university/lookup/", {"code": "  u-0160  "})
        self.assertEqual(res_norm.status_code, status.HTTP_200_OK)
        self.assertEqual(res_norm.data["institution"]["aishe_code"], "U-0160")

        # POST lookup format
        res_post = self.client.post("/api/auth/university/lookup/", {"aishe_code": "U-0161"}, format="json")
        self.assertEqual(res_post.status_code, status.HTTP_200_OK)
        self.assertEqual(res_post.data["institution"]["name"], self.uni_b.name)

        # University app API lookup path /api/v1/university/lookup/
        res_v1 = self.client.get("/api/v1/university/lookup/", {"aishe_code": "U-0160"})
        self.assertEqual(res_v1.status_code, status.HTTP_200_OK)
        self.assertTrue(res_v1.data["verified"])

    def test_invalid_aishe_format(self):
        """Invalid AISHE formats or empty queries are rejected with 400 Bad Request."""
        # Missing code
        res_empty = self.client.get("/api/auth/university/lookup/")
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res_empty.data.get("verified", True))

        # College AISHE code in university lookup
        res_college = self.client.get("/api/auth/university/lookup/", {"aishe_code": "C-10001"})
        self.assertEqual(res_college.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("College", res_college.data.get("detail", ""))

        # Invalid characters
        res_invalid = self.client.get("/api/auth/university/lookup/", {"aishe_code": "U-0160<script>"})
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_or_inactive_aishe_code(self):
        """Unknown or inactive AISHE codes return 404 with a helpful message."""
        # Non-existent code
        res_unknown = self.client.get("/api/auth/university/lookup/", {"aishe_code": "U-8888"})
        self.assertEqual(res_unknown.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(res_unknown.data["verified"])
        self.assertIn("No active University found", res_unknown.data["detail"])

        # Inactive university
        res_inactive = self.client.get("/api/auth/university/lookup/", {"aishe_code": "U-0999"})
        self.assertEqual(res_inactive.status_code, status.HTTP_404_NOT_FOUND)

    # =========================================================================
    # Phase 4: Institution Identity and Uniqueness
    # =========================================================================

    def test_shared_aishe_code_requires_institute_code(self):
        """
        The DHE registry legitimately has institutions sharing an AISHE code, so it is not unique in the
        database; registration must then be disambiguated by the DHE institute code instead of binding to an
        arbitrary match.
        """
        University.objects.filter(pk=self.uni_a.pk).update(institute_code="9101")
        University.objects.create(name="Shared Code Campus", aishe_code="U-0160", institute_code="9102", state="Haryana")
        payload = self._verified({
            "fullName": "Shared Code Applicant", "email": "shared@kuk.ac.in", "aisheCode": "U-0160",
            "password": "SecurePassword2026!"}, "9876500101")
        res = self.client.post("/api/auth/university/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("aisheCode", res.data)
        payload["instituteCode"] = "9101"
        res = self.client.post("/api/auth/university/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(User.objects.get(email="shared@kuk.ac.in").requested_university, self.uni_a)

    # =========================================================================
    # Phase 5: Secure Applicant Account Creation
    # =========================================================================

    def test_successful_university_registration(self):
        """Applicant registers as University Nodal Officer for verified university."""
        initial_uni_count = University.objects.count()

        payload = {
            "fullName": "Dr. Ramesh Sharma",
            "email": "nodal.ramesh@kuk.ac.in",
            "aisheCode": "U-0160",
            "designation": "University Nodal Officer",
            "institutionType": "UNIVERSITY",
            "password": "SecurePassword2026!",
            "confirmPassword": "SecurePassword2026!",
        }
        payload = self._verified(payload, "9876500102")

        res = self.client.post("/api/auth/university/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertNotIn("tokens", res.data)
        self.assertTrue(res.data.get("verification_sent"))
        self.assertFalse(res.data["user"]["is_email_verified"])
        self.assertEqual(res.data["user"]["email"], "nodal.ramesh@kuk.ac.in")
        self.assertEqual(res.data["user"]["role"], "nodal_officer")
        # Ownership is only requested: no institution binding until an administrator approves it.
        self.assertEqual(res.data["user"]["institution_status"], "PENDING")
        self.assertIsNone(res.data["user"]["university_id"])
        self.assertEqual(res.data["user"]["requested_institution_name"], self.uni_a.name)

        # Verify DB record
        user = User.objects.get(email="nodal.ramesh@kuk.ac.in")
        self.assertEqual(user.full_name, "Dr. Ramesh Sharma")
        self.assertEqual(user.role, "nodal_officer")
        self.assertIsNone(user.university)
        self.assertEqual(user.requested_university, self.uni_a)
        self.assertIsNone(user.college)
        self.assertTrue(user.check_password("SecurePassword2026!"))

        # Existing university must be reused without creating duplicates
        self.assertEqual(University.objects.count(), initial_uni_count)
        self.assertEqual(self.uni_a.name, "Kurukshetra University, Kurukshetra")

    def test_duplicate_email_rejected(self):
        """Registration with an already-registered email is rejected."""
        User.objects.create_user(
            email="existing.nodal@kuk.ac.in",
            full_name="Existing Officer",
            role="nodal_officer",
            password="Password123!",
            university=self.uni_a,
        )

        payload = {
            "fullName": "Another Officer",
            "email": "existing.nodal@kuk.ac.in",
            "aisheCode": "U-0160",
            "password": "Password2026!",
        }
        res = self.client.post("/api/auth/university/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_rejection_of_privileged_roles(self):
        """Attempts to register with privileged roles (admin, committee) are strictly rejected."""
        for forbidden_role in ["admin", "committee", "committee_chair", "university_admin"]:
            payload = {
                "fullName": "Hacker Attempt",
                "email": f"hacker_{forbidden_role}@test.local",
                "aisheCode": "U-0160",
                "role": forbidden_role,
                "password": "Password2026!",
            }
            res = self.client.post("/api/auth/university/register/", payload, format="json")
            self.assertEqual(
                res.status_code,
                status.HTTP_400_BAD_REQUEST,
                f"Role {forbidden_role} was not rejected!"
            )

    def test_rejection_of_unverified_or_college_aishe_code(self):
        """Attempts to register with an unverified AISHE code are rejected."""
        payload = {
            "fullName": "Test Applicant",
            "email": "test@unverified.edu",
            "aisheCode": "U-NONEXISTENT",
            "password": "Password2026!",
        }
        res = self.client.post("/api/auth/university/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("aisheCode", res.data)

        # College code in university registration
        payload_college = {
            "fullName": "Test College In Uni",
            "email": "test_college@edu.in",
            "aisheCode": "C-10001",
            "password": "Password2026!",
        }
        res_col = self.client.post("/api/auth/university/register/", payload_college, format="json")
        self.assertEqual(res_col.status_code, status.HTTP_400_BAD_REQUEST)

    def test_general_signup_handles_university_applicant(self):
        """The general /api/auth/signup/ endpoint also safely creates a university applicant when institutionType=UNIVERSITY."""
        payload = {
            "fullName": "Prof. Anita Sen",
            "email": "anita.sen@mdu.ac.in",
            "aisheCode": "U-0161",
            "institutionType": "UNIVERSITY",
            "role": "nodal_officer",
            "password": "SecurePassword2026!",
        }
        payload = self._verified(payload, "9876500103")
        res = self.client.post("/api/auth/signup/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["user"]["role"], "nodal_officer")
        self.assertEqual(res.data["user"]["institution_status"], "PENDING")
        self.assertEqual(User.objects.get(email="anita.sen@mdu.ac.in").requested_university, self.uni_b)

    # =========================================================================
    # Phase 6: University-Specific Access Control & Isolation
    # =========================================================================

    def test_university_applicant_cannot_access_college_apis(self):
        """A registered University Nodal Officer is strictly forbidden from College APIs."""
        uni_user = User.objects.create_user(
            email="nodal.kuk@gov.in",
            full_name="KUK Nodal Officer",
            role="nodal_officer",
            password="Password2026!",
            university=self.uni_a,
        )
        self.client.force_authenticate(user=uni_user)

        # Attempt to access college resources
        res_col_inst = self.client.get(f"/api/v1/college/colleges/{self.college.id}/")
        self.assertEqual(res_col_inst.status_code, status.HTTP_403_FORBIDDEN)

        res_col_list = self.client.get("/api/v1/college/colleges/")
        self.assertEqual(res_col_list.status_code, status.HTTP_403_FORBIDDEN)

        res_col_assess = self.client.get(f"/api/v1/college/colleges/{self.college.id}/assessments/")
        self.assertEqual(res_col_assess.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_university_isolation(self):
        """User from University A cannot access University B's records or assessment workspace."""
        user_a = User.objects.create_user(
            email="nodal.a@kuk.ac.in",
            full_name="Officer A",
            role="nodal_officer",
            password="Password2026!",
            university=self.uni_a,
        )
        user_b = User.objects.create_user(
            email="nodal.b@mdu.ac.in",
            full_name="Officer B",
            role="nodal_officer",
            password="Password2026!",
            university=self.uni_b,
        )

        assess_a = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=user_a,
        )
        assess_b = UniversityAssessmentService.create_assessment(
            university_id=self.uni_b.id,
            academic_year="2025-26",
            created_by=user_b,
        )

        # Authenticate as User A
        self.client.force_authenticate(user=user_a)

        # User A can access own assessment
        res_own = self.client.get(f"/api/v1/university/university-assessments/{assess_a.assessment_id}/")
        self.assertEqual(res_own.status_code, status.HTTP_200_OK)

        # User A CANNOT access User B's assessment
        res_other = self.client.get(f"/api/v1/university/university-assessments/{assess_b.assessment_id}/")
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)

        # User A CANNOT access University B's institution record
        res_uni_b = self.client.get(f"/api/v1/university/universities/{self.uni_b.id}/")
        self.assertEqual(res_uni_b.status_code, status.HTTP_403_FORBIDDEN)

    def test_administrative_oversight_remains_functional(self):
        """State Admin retains access to view both universities and assessments."""
        user_a = User.objects.create_user(
            email="nodal.oversight@kuk.ac.in",
            full_name="Officer KUK",
            role="nodal_officer",
            password="Password2026!",
            university=self.uni_a,
        )
        assess_a = UniversityAssessmentService.create_assessment(
            university_id=self.uni_a.id,
            academic_year="2025-26",
            created_by=user_a,
        )

        self.client.force_authenticate(user=self.admin_user)
        res_uni = self.client.get(f"/api/v1/university/universities/{self.uni_a.id}/")
        self.assertEqual(res_uni.status_code, status.HTTP_200_OK)

        res_assess = self.client.get(f"/api/v1/university/university-assessments/{assess_a.assessment_id}/")
        self.assertEqual(res_assess.status_code, status.HTTP_200_OK)

    # =========================================================================
    # Phase 7: Unified Registration Contract & Mismatched Type Rejection
    # =========================================================================

    def test_successful_college_registration(self):
        """College applicant registers through general signup with role principal and collegeId."""
        payload = {
            "fullName": "Dr. Sunita Verma",
            "email": "principal.sunita@gcpanchkula.ac.in",
            "collegeId": self.college.id,
            "role": "principal",
            "institutionType": "COLLEGE",
            "password": "SecurePassword2026!",
        }
        payload = self._verified(payload, "9876500104")
        res = self.client.post("/api/auth/signup/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertNotIn("tokens", res.data)
        self.assertTrue(res.data.get("verification_sent"))
        self.assertFalse(res.data["user"]["is_email_verified"])
        self.assertEqual(res.data["user"]["role"], "principal")
        self.assertEqual(res.data["user"]["institution_status"], "PENDING")
        self.assertIsNone(res.data["user"]["college_id"])
        self.assertIsNone(res.data["user"]["university_id"])

        # Check DB record: the college is requested, not granted
        user = User.objects.get(email="principal.sunita@gcpanchkula.ac.in")
        self.assertIsNone(user.college)
        self.assertEqual(user.requested_college, self.college)
        self.assertIsNone(user.university)
        self.assertEqual(user.role, "principal")

    def test_college_registration_rejects_missing_or_invalid_college(self):
        """College principal registration without collegeId or with invalid ID is rejected."""
        # Missing collegeId
        payload_missing = {
            "fullName": "Missing College User",
            "email": "missing.college@edu.in",
            "role": "principal",
            "institutionType": "COLLEGE",
            "password": "SecurePassword2026!",
        }
        res_missing = self.client.post("/api/auth/signup/", payload_missing, format="json")
        self.assertEqual(res_missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("collegeId", res_missing.data)

        # Invalid non-existent collegeId
        payload_invalid = {
            "fullName": "Invalid College User",
            "email": "invalid.college@edu.in",
            "collegeId": 999999,
            "role": "principal",
            "institutionType": "COLLEGE",
            "password": "SecurePassword2026!",
        }
        res_invalid = self.client.post("/api/auth/signup/", payload_invalid, format="json")
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("collegeId", res_invalid.data)

    def test_college_applicant_cannot_access_university_apis(self):
        """A registered College Principal cannot access University workspaces or records."""
        college_user = User.objects.create_user(
            email="principal.panchkula@gc.ac.in",
            full_name="Panchkula Principal",
            role="principal",
            password="Password2026!",
            college=self.college,
        )
        self.client.force_authenticate(user=college_user)

        res_uni = self.client.get(f"/api/v1/university/universities/{self.uni_a.id}/")
        self.assertEqual(res_uni.status_code, status.HTTP_403_FORBIDDEN)

        res_uni_assess = self.client.get(f"/api/v1/university/universities/{self.uni_a.id}/assessments/")
        self.assertEqual(res_uni_assess.status_code, status.HTTP_403_FORBIDDEN)

    # =========================================================================
    # Phase 8: College AISHE Code Lookup Endpoint Tests
    # =========================================================================

    def test_valid_college_aishe_lookup(self):
        """College AISHE lookup returns canonical College record metadata."""
        res = self.client.get("/api/auth/college/lookup/", {"aishe_code": "C-10001"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["verified"])
        inst = res.data["institution"]
        self.assertEqual(inst["id"], self.college.id)
        self.assertEqual(inst["name"], self.college.name)
        self.assertEqual(inst["aishe_code"], "C-10001")

        # Case normalization with spaces
        res_norm = self.client.get("/api/auth/college/lookup/", {"code": "  c-10001  "})
        self.assertEqual(res_norm.status_code, status.HTTP_200_OK)
        self.assertEqual(res_norm.data["institution"]["aishe_code"], "C-10001")

    def test_university_code_in_college_lookup_rejected(self):
        """Entering a University AISHE code (U-*) in College lookup is rejected with HTTP 400."""
        res = self.client.get("/api/auth/college/lookup/", {"aishe_code": "U-0160"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res.data.get("verified", True))
        self.assertIn("University", res.data.get("detail", ""))

    def test_unknown_college_aishe_code(self):
        """Unknown College AISHE code returns HTTP 404."""
        res = self.client.get("/api/auth/college/lookup/", {"aishe_code": "C-99999"})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(res.data["verified"])

    # =========================================================================
    # Phase 9: Mobile Phone Number & OTP Verification Tests
    # =========================================================================

    def test_send_otp_success(self):
        """Sending OTP to a valid 10-digit mobile number succeeds and stores record."""
        res = self.client.post("/api/auth/otp/send/", {"phone_number": "9876543210"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])
        # The code is delivered by SMS only, never echoed by the API, and stored only as a hash.
        self.assertNotIn("dev_otp", res.data)
        code = last_sms_code("9876543210")
        self.assertEqual(len(code), 6)

        from apps.authentication.models import OTPVerification
        record = OTPVerification.objects.filter(phone_number="9876543210").first()
        self.assertIsNotNone(record)
        self.assertNotIn(code, record.otp_hash)
        self.assertFalse(record.is_verified)

    def test_send_otp_invalid_phone(self):
        """Sending OTP with invalid phone length or non-digits returns HTTP 400."""
        # Empty
        res_empty = self.client.post("/api/auth/otp/send/", {}, format="json")
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid format
        res_short = self.client.post("/api/auth/otp/send/", {"phone_number": "12345"}, format="json")
        self.assertEqual(res_short.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_otp_rate_limiting(self):
        """Sending multiple OTP requests within the 30-second cooldown returns HTTP 429."""
        phone = "9876543211"
        res1 = self.client.post("/api/auth/otp/send/", {"phone_number": phone}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        res2 = self.client.post("/api/auth/otp/send/", {"phone_number": phone}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_verify_otp_invalid_code(self):
        """Submitting an invalid OTP code returns HTTP 400."""
        phone = "9876543214"
        self.client.post("/api/auth/otp/send/", {"phone_number": phone}, format="json")

        res_verify = self.client.post("/api/auth/otp/verify/", {"phone_number": phone, "otp": "000000"}, format="json")
        self.assertEqual(res_verify.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res_verify.data["verified"])

    def test_verify_otp_success_and_registration(self):
        """Applicant can register with phone number saved without phone OTP gating."""
        phone = "9876543212"
        # Standalone OTP endpoints still function
        send_res = self.client.post("/api/auth/otp/send/", {"phone_number": phone}, format="json")
        self.assertEqual(send_res.status_code, status.HTTP_200_OK)

        verify_res = self.client.post("/api/auth/otp/verify/", {"phone_number": phone, "otp": last_sms_code(phone)}, format="json")
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)
        self.assertTrue(verify_res.data["verified"])

        # Register University applicant with phone number (phone OTP is no longer mandatory for signup)
        payload = {
            "fullName": "Dr. Vikas Verma",
            "email": "vikas.verma@kuk.ac.in",
            "phoneNumber": phone,
            "aisheCode": "U-0160",
            "designation": "University Nodal Officer",
            "institutionType": "UNIVERSITY",
            "password": "SecurePassword2026!",
            "confirmPassword": "SecurePassword2026!",
        }
        reg_res = self.client.post("/api/auth/university/register/", payload, format="json")
        self.assertEqual(reg_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(reg_res.data["user"]["phone_number"], phone)
        self.assertEqual(reg_res.data["user"]["is_email_verified"], False)
        self.assertTrue(reg_res.data.get("verification_sent"))

        user = User.objects.get(email="vikas.verma@kuk.ac.in")
        self.assertEqual(user.phone_number, phone)
        self.assertFalse(user.is_email_verified)

    def test_registration_without_phone_otp_and_rejects_invalid_phone_format(self):
        """Phone OTP is not required for signup; invalid phone formats are rejected."""
        # 1. Valid 10-digit phone without OTP succeeds
        payload = {
            "fullName": "Unverified Phone Applicant",
            "email": "unverified@kuk.ac.in",
            "phoneNumber": "9876543299",
            "aisheCode": "U-0160",
            "password": "SecurePassword2026!",
        }
        res = self.client.post("/api/auth/university/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertFalse(res.data["user"]["is_email_verified"])

        # 2. Malformed phone number (non-10-digit) is rejected with 400
        payload_bad = {
            "fullName": "Bad Phone Applicant",
            "email": "badphone@kuk.ac.in",
            "phoneNumber": "12345",
            "aisheCode": "U-0160",
            "password": "SecurePassword2026!",
        }
        res_bad = self.client.post("/api/auth/university/register/", payload_bad, format="json")
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phoneNumber", res_bad.data)

    def test_public_universities_list_endpoint(self):
        """Public /api/auth/universities/ lists all active universities for registration selector."""
        res = self.client.get("/api/auth/universities/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        names = [u["name"] for u in res.data]
        self.assertIn(self.uni_a.name, names)
        self.assertIn(self.uni_b.name, names)
        # Inactive university should not be listed
        self.assertNotIn(self.uni_inactive.name, names)

    def test_lookup_university_by_name_without_aishe(self):
        """Lookup endpoint successfully resolves university by name when AISHE is not provided."""
        uni_no_aishe = University.objects.create(
            name="Ashoka University Sonepat (Campus)",
            aishe_code="",
            university_type="Private University",
            state="Haryana",
            is_active=True,
        )
        res = self.client.get("/api/auth/university/lookup/", {"name": "Ashoka University Sonepat (Campus)"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["verified"])
        self.assertEqual(res.data["institution"]["name"], uni_no_aishe.name)
        self.assertEqual(res.data["institution"]["aishe_code"], "")

    def test_registration_using_university_name_without_aishe(self):
        """Nodal officer can register using University name when university has no AISHE code."""
        uni_no_aishe = University.objects.create(
            name="Sports University of Haryana, Rai, Sonipat",
            aishe_code="",
            university_type="State Public University",
            state="Haryana",
            is_active=True,
        )
        phone = "9876543220"
        payload = self._verified({
            "fullName": "Dr. Sunil Narwal",
            "email": "nodal@sportsuni.ac.in",
            "universityName": "Sports University of Haryana, Rai, Sonipat",
            "universityId": uni_no_aishe.id,
            "aisheCode": "",
            "designation": "University Nodal Officer",
            "institutionType": "UNIVERSITY",
            "password": "SecurePassword2026!",
            "confirmPassword": "SecurePassword2026!",
        }, phone)
        res = self.client.post("/api/auth/university/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="nodal@sportsuni.ac.in")
        self.assertEqual(user.requested_university, uni_no_aishe)
        self.assertEqual(user.institution_status, "PENDING")




