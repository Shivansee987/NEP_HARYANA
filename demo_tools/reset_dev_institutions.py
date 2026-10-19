"""Replaces the dev institutions with fresh, blank ones and leaves the demo institutions and their data alone.

Removes "Dev Test College" / "Dev Test University" (and any earlier "Dev College" / "Dev University") with every
submission made for them: assessments, evidence files, reviews, nominations. Then runs `create_dev_users`, which
creates a blank "Dev College" and "Dev University" and points the dev logins (principal@dev.local, nodal@dev.local,
univadmin@dev.local) at them. Re-run it whenever the dev institutions need to be blank again.

    venv/Scripts/python.exe demo_tools/reset_dev_institutions.py   (from the repo root)
"""
import os
import sys

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Backend")
sys.path.insert(0, BACKEND)
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.development"
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import transaction  # noqa: E402

from apps.authentication.models import College, User  # noqa: E402
from apps.college.models import CollegeAssessment  # noqa: E402
from apps.evidence.models import (  # noqa: E402
    EvidenceAssociationVerification, EvidenceAuditLog, EvidenceDocument, EvidenceReviewAssignment,
    EvidenceSubcriterionAssociation, EvidenceVerification, ReviewerAuthorization,
)
from apps.university.models import University, UniversityAssessment  # noqa: E402

if not settings.DEBUG:
    raise SystemExit("Refusing to run: this script is for the local development database only (DEBUG=False).")

DEV_COLLEGE_CODES = ["DEV-COLLEGE-001", "DEV-COLLEGE-002"]
DEV_UNIVERSITY_NAMES = ["Dev Test University", "Dev University"]
DEV_EMAILS = ["principal@dev.local", "nodal@dev.local", "univadmin@dev.local"]

colleges = list(College.objects.filter(aishe_code__in=DEV_COLLEGE_CODES))
universities = list(University.objects.filter(name__in=DEV_UNIVERSITY_NAMES))
college_assessments = CollegeAssessment.objects.filter(college__in=colleges)
university_assessments = UniversityAssessment.objects.filter(university__in=universities)

# Evidence rows carry the institution's AISHE code and the assessment's public id as plain strings.
inst_codes = [c.aishe_code for c in colleges] + [u.aishe_code for u in universities if u.aishe_code]
assess_ids = [str(a) for a in college_assessments.values_list("assessment_id", flat=True)]
assess_ids += [str(a) for a in university_assessments.values_list("assessment_id", flat=True)]
docs = (EvidenceDocument.objects.filter(institution_id__in=inst_codes)
        | EvidenceDocument.objects.filter(assessment_id__in=assess_ids)
        | EvidenceDocument.objects.filter(uploader__email__in=DEV_EMAILS))
doc_ids = list(docs.values_list("id", flat=True).distinct())
files = [os.path.join(settings.EVIDENCE_STORAGE_VAULT, p) for p in
         EvidenceDocument.objects.filter(id__in=doc_ids).values_list("file_path", flat=True) if p]

with transaction.atomic():
    # QuerySet.delete() skips the models' delete() guards, which protect live records, not dev fixtures.
    assoc = EvidenceSubcriterionAssociation.objects.filter(evidence_id__in=doc_ids)
    print("evidence association checks:", EvidenceAssociationVerification.objects.filter(association__in=assoc).delete()[0])
    print("evidence associations:", assoc.delete()[0])
    print("evidence verifications:", EvidenceVerification.objects.filter(evidence_id__in=doc_ids).delete()[0])
    print("evidence review assignments:", EvidenceReviewAssignment.objects.filter(evidence_id__in=doc_ids).delete()[0])
    print("evidence audit log:", (EvidenceAuditLog.objects.filter(evidence_id__in=doc_ids)
                                  | EvidenceAuditLog.objects.filter(assessment_id__in=assess_ids)).delete()[0])
    EvidenceDocument.objects.filter(id__in=doc_ids).update(superseded_by=None)
    print("evidence documents:", EvidenceDocument.objects.filter(id__in=doc_ids).delete()[0])
    print("college assessments (+ reviews, logs):", college_assessments.delete()[0])
    print("university assessments (+ reviews, logs):", university_assessments.delete()[0])
    print("reviewer grants:", ReviewerAuthorization.objects.filter(user__email__in=DEV_EMAILS).delete()[0])
    User.objects.filter(email__in=DEV_EMAILS).update(college=None, university=None)
    print("old dev colleges (+ nominations):", College.objects.filter(id__in=[c.id for c in colleges]).delete()[0])
    print("old dev universities:", University.objects.filter(id__in=[u.id for u in universities]).delete()[0])
    call_command("create_dev_users")
    User.objects.filter(email__in=DEV_EMAILS).update(is_email_verified=True)

for path in files:
    try:
        os.remove(path)
    except OSError:
        pass
print(f"removed {len(files)} evidence file(s) from disk")
