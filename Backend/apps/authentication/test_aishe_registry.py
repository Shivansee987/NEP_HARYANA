import csv
import json
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import College
from apps.university.models import University

DATA_DIR = os.path.join(settings.BASE_DIR, "data", "aishe_import")


def load_registry():
    with open(os.path.join(DATA_DIR, "aishe_haryana_registry.json"), encoding="utf-8") as f:
        return json.load(f)


def quiet(*args, **kwargs):
    with open(os.devnull, "w") as devnull:
        call_command(*args, stdout=devnull, stderr=devnull, **kwargs)


class AisheRegistryDataTests(SimpleTestCase):
    """The committed registry matches the AISHE portal exports of 17-10-2026."""

    def test_registry_counts_and_codes(self):
        registry = load_registry()
        records = registry["institutions"]
        self.assertEqual(registry["counts"]["college"], 1241)
        self.assertEqual(registry["counts"]["standalone"], 382)
        self.assertEqual(registry["counts"]["university"], 60)
        self.assertEqual(len(records), 1683)
        self.assertEqual(len({r["aishe_code"] for r in records}), 1683, "AISHE codes are unique")
        prefix = {"college": "C", "standalone": "S", "university": "U"}
        for r in records:
            self.assertRegex(r["aishe_code"], rf"^{prefix[r['kind']]}-\d+$")
            self.assertTrue(r["name"] and r["district"], r)

    def test_confirmed_links_point_at_known_records(self):
        codes = {r["aishe_code"] for r in load_registry()["institutions"]}
        with open(os.path.join(DATA_DIR, "haryana_institutions_raw.json"), encoding="utf-8") as f:
            dhe = {r["institute_code"]: r for r in json.load(f)}
        with open(os.path.join(DATA_DIR, "aishe_dhe_links.csv"), encoding="utf-8", newline="") as f:
            confirmed = [r for r in csv.DictReader(f) if r["status"] == "confirmed"]
        self.assertTrue(confirmed)
        self.assertEqual(len({r["aishe_code"] for r in confirmed}), len(confirmed))
        for link in confirmed:
            self.assertIn(link["aishe_code"], codes)
            self.assertIn(link["institute_code"], dhe)
            self.assertEqual((dhe[link["institute_code"]]["aishe_code"] or ""), link["current_aishe_code"])


class AisheRegistryImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        quiet("import_haryana_institutions")
        cls.dhe_college_ids = set(College.objects.filter(institute_code__isnull=False).values_list("id", flat=True))
        quiet("import_aishe_registry")

    def setUp(self):
        self.client = APIClient()

    def lookup(self, kind, code):
        return self.client.get(f"/api/auth/{kind}/lookup/?aishe_code={code}", HTTP_HOST="localhost")

    def test_every_aishe_code_is_registered(self):
        for rec in load_registry()["institutions"]:
            model = University if rec["kind"] == "university" else College
            self.assertTrue(model.objects.filter(aishe_code__iexact=rec["aishe_code"]).exists(), rec["aishe_code"])

    def test_new_college_and_standalone_codes_verify(self):
        for code, name in [("C-75950", "YUVRAJ COLLEGE OF PHYSICAL EDUCATION BATTA"),
                           ("S-26178", "AADHAR HEALTH INSTITUTE")]:
            res = self.lookup("college", code)
            self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
            self.assertEqual(res.json()["institution"]["name"], name)
        college = College.objects.get(aishe_code="C-75950")
        self.assertIsNone(college.institute_code)
        self.assertEqual(college.institute_type, "Self Finance")
        self.assertEqual(college.affiliation_body_1, "Kurukshetra University, Kurukshetra")
        self.assertTrue(college.source_reference.startswith("AISHE college list as on 17-10-2026"))

    def test_new_university_code_verifies(self):
        res = self.lookup("university", "U-0936")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        self.assertEqual(res.json()["institution"]["name"], "Al-Falah University")

    def test_dhe_records_keep_their_identity(self):
        uni = University.objects.get(aishe_code="U-1021")
        self.assertEqual(uni.name, "Gurugram University, Gurugram (Campus)")
        self.assertEqual(uni.institute_code, "1951")
        remaining = set(College.objects.filter(institute_code__isnull=False).values_list("id", flat=True))
        self.assertEqual(remaining, self.dhe_college_ids)

    def test_confirmed_links_fill_dhe_codes(self):
        shivam = College.objects.get(institute_code="1371")
        self.assertEqual(shivam.aishe_code, "S-21671")
        self.assertEqual(College.objects.filter(aishe_code__iexact="S-21671").count(), 1)
        res = self.lookup("college", "S-21671")
        self.assertEqual(res.json()["institution"]["institute_code"], "1371")

        res = self.lookup("university", "U-0744")
        self.assertEqual(res.json()["institution"]["institute_code"], "1979")

    def test_hau_code_corrected_and_fisheries_college_added(self):
        self.assertEqual(University.objects.get(institute_code="1956").aishe_code, "U-0159")
        self.assertEqual(University.objects.filter(aishe_code="U-0159").count(), 1)
        res = self.lookup("college", "C-64938")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["institution"]["name"], "COLLEGE OF FISHERIES SCIENCE")

    def test_rerun_and_dry_run_change_nothing(self):
        before = (College.objects.count(), University.objects.count())
        quiet("import_aishe_registry")
        quiet("import_aishe_registry", dry_run=True)
        self.assertEqual((College.objects.count(), University.objects.count()), before)


class AisheRegistryOrderingTests(TestCase):
    def test_refuses_to_run_before_dhe_registry(self):
        with self.assertRaisesMessage(CommandError, "import_haryana_institutions first"):
            quiet("import_aishe_registry")

    def test_running_before_dhe_is_repaired_by_a_rerun(self):
        quiet("import_aishe_registry", allow_without_dhe=True)
        quiet("import_haryana_institutions")
        self.assertEqual(College.objects.filter(aishe_code__iexact="C-10590").count(), 2)

        quiet("import_aishe_registry")
        for code in ("C-10590", "S-21671"):
            rows = College.objects.filter(aishe_code__iexact=code)
            self.assertEqual(rows.count(), 1, code)
            self.assertIsNotNone(rows.get().institute_code)
        aishe_rows = College.objects.filter(source_reference__startswith="AISHE ")
        dhe_codes = College.objects.exclude(source_reference__startswith="AISHE ").exclude(aishe_code="")
        self.assertFalse(aishe_rows.filter(aishe_code__in=dhe_codes.values("aishe_code")).exists())
