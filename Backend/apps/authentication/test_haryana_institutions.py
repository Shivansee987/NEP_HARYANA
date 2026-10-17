from django.test import TestCase
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import College, User
from apps.university.models import University, UniversityAssessment
from apps.college.models import CollegeAssessment


class HaryanaInstitutionImportTests(TestCase):
    """
    Automated test suite verifying the Haryana Institution Registry import,
    schema resilience, idempotent management command, dry-run simulation,
    and AISHE / DHE Institute-code lookup contracts.
    """

    def setUp(self):
        self.client = APIClient()

    def test_dry_run_makes_no_database_changes(self):
        """Dry run must simulate import without persisting any records to the database."""
        initial_colleges = College.objects.count()
        initial_unis = University.objects.count()

        call_command("import_haryana_institutions", dry_run=True)

        self.assertEqual(College.objects.count(), initial_colleges)
        self.assertEqual(University.objects.count(), initial_unis)

    def test_import_and_lookup_u1021_gurugram_university(self):
        """Verify that U-1021 Gurugram University is imported and returns HTTP 200 via lookup API."""
        call_command("import_haryana_institutions")

        # Verify in database
        uni = University.objects.filter(aishe_code__iexact="U-1021").first()
        self.assertIsNotNone(uni)
        self.assertEqual(uni.name, "Gurugram University, Gurugram (Campus)")
        self.assertEqual(uni.institute_code, "1951")
        self.assertEqual(uni.district, "Gurugram")
        self.assertTrue(uni.is_active)
        self.assertTrue(uni.source_reference.startswith("DHE Portal PDF 2026"))

        # Verify via Public University Lookup API
        res = self.client.get("/api/auth/university/lookup/?aishe_code=U-1021", HTTP_HOST="localhost")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertTrue(data.get("verified"))
        self.assertEqual(data["institution"]["name"], "Gurugram University, Gurugram (Campus)")
        self.assertEqual(data["institution"]["aishe_code"], "U-1021")
        self.assertEqual(data["institution"]["institute_code"], "1951")
        self.assertEqual(data["institution"]["district"], "Gurugram")

    def test_college_lookup_and_code_fallback(self):
        """Verify that College lookup works by both AISHE code and DHE institute code."""
        call_command("import_haryana_institutions")

        # By AISHE code
        res_aishe = self.client.get("/api/auth/college/lookup/?aishe_code=C-10590", HTTP_HOST="localhost")
        self.assertEqual(res_aishe.status_code, status.HTTP_200_OK)
        data_aishe = res_aishe.json()
        self.assertTrue(data_aishe.get("verified"))
        self.assertEqual(data_aishe["institution"]["name"], "Ambala College of Engineering and Applied Research")
        self.assertEqual(data_aishe["institution"]["institute_code"], "4281")

        # By Institute Code fallback (4281)
        res_code = self.client.get("/api/auth/college/lookup/?aishe_code=4281", HTTP_HOST="localhost")
        self.assertEqual(res_code.status_code, status.HTTP_200_OK)
        data_code = res_code.json()
        self.assertTrue(data_code.get("verified"))
        self.assertEqual(data_code["institution"]["name"], "Ambala College of Engineering and Applied Research")

    def test_duplicate_aishe_coexistence(self):
        """Verify that records legitimately sharing an AISHE code in DHE coexist without IntegrityError."""
        call_command("import_haryana_institutions")

        # C-34991 is shared by two institutions in Bhiwani and Charkhi Dadri
        shared = College.objects.filter(aishe_code="C-34991")
        self.assertEqual(shared.count(), 2)
        codes = set(shared.values_list("institute_code", flat=True))
        self.assertEqual(codes, {"1370", "1385"})

    def test_ambiguous_shared_aishe_lookup_requires_institute_code(self):
        """Lookup by a shared AISHE code returns HTTP 409 with ambiguous candidates unless disambiguated."""
        call_command("import_haryana_institutions")

        # Query shared AISHE code C-34991
        res = self.client.get("/api/auth/college/lookup/?aishe_code=C-34991", HTTP_HOST="localhost")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        data = res.json()
        self.assertFalse(data.get("verified"))
        self.assertTrue(data.get("ambiguous"))
        self.assertEqual(len(data.get("matches", [])), 2)

        # Disambiguate by providing institute_code 1370
        res_disambiguated = self.client.get(
            "/api/auth/college/lookup/?aishe_code=C-34991&institute_code=1370",
            HTTP_HOST="localhost"
        )
        self.assertEqual(res_disambiguated.status_code, status.HTTP_200_OK)
        self.assertTrue(res_disambiguated.json().get("verified"))
        self.assertEqual(res_disambiguated.json()["institution"]["institute_code"], "1370")

    def test_conflicting_identifiers_rejected(self):
        """Providing conflicting AISHE and institute_code is rejected with HTTP 400."""
        call_command("import_haryana_institutions")

        # Institute code 1370 belongs to AISHE C-34991, NOT C-10590
        res = self.client.get(
            "/api/auth/college/lookup/?aishe_code=C-10590&institute_code=1370",
            HTTP_HOST="localhost"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Conflicting identifiers", res.json().get("detail", ""))

    def test_missing_aishe_lookup_by_institute_code(self):
        """Institutions with missing AISHE in source PDF can be found by DHE institute code."""
        call_command("import_haryana_institutions")

        # Sports University of Haryana (Code 4333) has blank AISHE in source
        res = self.client.get("/api/auth/university/lookup/?institute_code=4333", HTTP_HOST="localhost")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertTrue(data.get("verified"))
        self.assertEqual(data["institution"]["name"], "Sports University of Haryana, Rai, Sonipat")
        self.assertEqual(data["institution"]["institute_code"], "4333")

    def test_demo_reconciliation_preserves_foreign_keys(self):
        """Verify that pre-existing demo institutions are reconciled in-place, preserving assessments and users."""
        # 1. College Demo
        demo_col = College.objects.create(name="Government College, Sector 9, Gurugram", aishe_code="C-DEMO-01")
        col_user = User.objects.create_user(
            email="principal.sec9@college.edu.in",
            full_name="Principal Sec 9",
            role="principal",
            college=demo_col,
            password="Password123!"
        )
        col_assess = CollegeAssessment.objects.create(
            assessment_id="ASSESS-DEMO-COL-01",
            college=demo_col,
            status="DRAFT"
        )

        # 2. University Demo
        demo_uni = University.objects.create(name="Kurukshetra University, Kurukshetra", aishe_code="U-DEMO-01")
        uni_user = User.objects.create_user(
            email="registrar@kuk.ac.in",
            full_name="Registrar KUK",
            role="university_nodal",
            university=demo_uni,
            password="Password123!"
        )
        uni_assess = UniversityAssessment.objects.create(
            university=demo_uni,
            status="DRAFT",
            academic_year="2025-26"
        )

        call_command("import_haryana_institutions")

        # Reload demo college
        demo_col.refresh_from_db()
        self.assertEqual(demo_col.institute_code, "1034")
        self.assertEqual(demo_col.aishe_code, "C-28137")
        self.assertEqual(demo_col.name, "GC Sector-9 Gurugram")
        col_user.refresh_from_db()
        self.assertEqual(col_user.college_id, demo_col.id)
        col_assess.refresh_from_db()
        self.assertEqual(col_assess.college_id, demo_col.id)

        # Reload demo university
        demo_uni.refresh_from_db()
        self.assertEqual(demo_uni.institute_code, "1943")
        self.assertEqual(demo_uni.aishe_code, "U-0164")
        self.assertEqual(demo_uni.name, "Kurukshetra University, Kurukshetra (Campus)")
        uni_user.refresh_from_db()
        self.assertEqual(uni_user.university_id, demo_uni.id)
        uni_assess.refresh_from_db()
        self.assertEqual(uni_assess.university_id, demo_uni.id)

    def test_importer_idempotency(self):
        """Running the importer multiple times must produce identical record counts with 0 errors."""
        call_command("import_haryana_institutions")
        initial_colleges = College.objects.count()
        initial_unis = University.objects.count()

        # Run again
        call_command("import_haryana_institutions")
        self.assertEqual(College.objects.count(), initial_colleges)
        self.assertEqual(University.objects.count(), initial_unis)
