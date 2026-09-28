"""Deletes every institution, assessment, evidence file, nomination and non-staff account from the dev DB.
Keeps the staff logins (admin / committee / chair / checker) and their ALL-framework reviewer grants."""
import os
import shutil
import sys

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Backend")
sys.path.insert(0, BACKEND)
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.development"
import django  # noqa: E402

django.setup()
from django.apps import apps  # noqa: E402
from django.conf import settings  # noqa: E402
from django.db import transaction  # noqa: E402

if not settings.DEBUG:
    raise SystemExit("Refusing to wipe: this script is for the local development database only (DEBUG=False).")

KEEP = {"admin@dev.local", "committee@dev.local", "chair@dev.local", "checker@dev.local"}
ORDER = [
    "evidence.EvidenceAuditLog", "evidence.EvidenceAssociationVerification", "evidence.EvidenceVerification",
    "evidence.EvidenceSubcriterionAssociation", "evidence.EvidenceDocument",
    "college.CollegeReviewRecord", "college.CollegeAssessmentAuditLog", "college.CollegeAssessment",
    "university.UniversityReviewRecord", "university.UniversityAssessmentAuditLog", "university.UniversityAssessment",
    "nominations.Nomination", "authentication.RefreshToken",
]
with transaction.atomic():
    for label in ORDER:
        n, _ = apps.get_model(label).objects.all().delete()
        print(f"{label}: {n}")
    for m in apps.get_app_config("nominations").get_models():
        m.objects.all().delete()
    for m in apps.get_app_config("reports").get_models():
        m.objects.all().delete()
    U = apps.get_model("authentication.User")
    apps.get_model("evidence.ReviewerAuthorization").objects.exclude(user__email__in=KEEP).delete()
    print("users:", U.objects.exclude(email__in=KEEP).delete()[0])
    print("colleges:", apps.get_model("authentication.College").objects.all().delete()[0])
    print("universities:", apps.get_model("university.University").objects.all().delete()[0])

vault = settings.EVIDENCE_STORAGE_VAULT
for sub in os.listdir(vault):
    shutil.rmtree(os.path.join(vault, sub))
    os.makedirs(os.path.join(vault, sub))
print("vault cleared:", vault)
