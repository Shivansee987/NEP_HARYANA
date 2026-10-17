"""
FIN-01 regression: the Django admin site must not be a path around committee-led evidence verification.

Before the fix a superuser (the Head Admin is provisioned as one) could open /admin/, set
EvidenceDocument.status = EVIDENCE_VERIFIED or create an EvidenceAssociationVerification naming any verifier,
and the evidence-gated score rose with no committee action.
"""
import importlib
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import Resolver404, clear_url_caches, resolve

from apps.admin_panel.tests.test_production_settings import load_production_settings
from apps.evidence.enums import EvidenceLifecycleState
from apps.evidence.models import EvidenceDocument

User = get_user_model()


def _doc(uploader):
    return EvidenceDocument.objects.create(
        uploader=uploader,
        assessment_id="ASSESS-ADMIN-LOCKDOWN", framework="COLLEGE_2026", institution_type="COLLEGE",
        institution_id="C-LOCK-1", file_path="evidence/x.pdf", original_filename="x.pdf", file_size=10,
        file_checksum="a" * 64, mime_type="application/pdf", status=EvidenceLifecycleState.EVIDENCE_PENDING,
    )


class DjangoAdminEvidenceLockdownTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_user(
            email="root@lockdown.test", full_name="Root", role="head_admin", password="x",
            is_staff=True, is_superuser=True)
        uploader = User.objects.create_user(email="p@lockdown.test", full_name="P", role="principal", password="x")
        self.doc = _doc(uploader)
        self.client.force_login(self.superuser)

    def test_superuser_cannot_change_evidence_status(self):
        url = f"/admin/evidence/evidencedocument/{self.doc.pk}/change/"
        page = self.client.get(url)
        self.assertNotIn(b'name="status"', page.content, "status is still an editable admin field")
        resp = self.client.post(url, {"status": EvidenceLifecycleState.EVIDENCE_VERIFIED})
        self.assertEqual(resp.status_code, 403)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, EvidenceLifecycleState.EVIDENCE_PENDING)

    def test_superuser_cannot_add_or_delete_evidence_records(self):
        for model in ("evidencedocument", "evidencesubcriterionassociation", "evidenceverification",
                      "evidenceassociationverification"):
            self.assertEqual(self.client.get(f"/admin/evidence/{model}/add/").status_code, 403, model)
        resp = self.client.post(f"/admin/evidence/evidencedocument/{self.doc.pk}/delete/", {"post": "yes"})
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(EvidenceDocument.objects.filter(pk=self.doc.pk).exists())


class ProductionUrlconfTests(TestCase):
    def tearDown(self):
        import config.urls
        importlib.reload(config.urls)
        clear_url_caches()

    def test_admin_not_mounted_when_disabled(self):
        import config.urls
        with override_settings(ENABLE_DJANGO_ADMIN=False):
            importlib.reload(config.urls)
            clear_url_caches()
            with self.assertRaises(Resolver404):
                resolve("/admin/")
            with self.assertRaises(Resolver404):
                resolve("/admin/login/")

    def test_production_settings_disable_admin(self):
        prod = load_production_settings(ENABLE_DJANGO_ADMIN="true")
        self.assertFalse(prod.ENABLE_DJANGO_ADMIN, "production must not mount /admin/, even if asked to by env")


class HeadAdminIsNotDjangoSuperuserTests(TestCase):
    def test_provisioned_head_admin_has_no_django_superuser_power(self):
        call_command("provision_head_admin", email="head@lockdown.test", name="Head",
                     password="Sufficiently-Long#Pass1", stdout=StringIO())
        user = User.objects.get(email="head@lockdown.test")
        self.assertEqual(user.role, "head_admin")
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_head_admin)
