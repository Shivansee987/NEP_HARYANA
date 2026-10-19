"""
Loads the official AISHE master list for Haryana (data/aishe_import/aishe_haryana_registry.json,
built from the AISHE portal exports by `build_aishe_registry`) into College and University, so that
every AISHE-registered Haryana institution can be found by the registration AISHE lookup.

Run it after `import_haryana_institutions` (the DHE registry), and again after any re-run of that command:

    python manage.py import_haryana_institutions
    python manage.py import_aishe_registry [--dry-run]

Rules:
- Rows from the DHE registry are never renamed or removed. The only change made to them is the AISHE
  code assignment listed as `confirmed` in data/aishe_import/aishe_dhe_links.csv (DHE records whose
  AISHE code was blank or wrong in the DHE source).
- An AISHE code already held by any row of the same table is not created again.
- Rows created by this command (source_reference starting with "AISHE ") are refreshed from the list.
- Codes in the DHE registry that are absent from the AISHE list are reported, not changed.
"""

import csv
import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.authentication.models import College
from apps.university.models import University

AISHE_SOURCE_PREFIX = "AISHE "

# AISHE management labels mapped to the DHE registry's vocabulary for College.institute_type.
MANAGEMENT_TO_INSTITUTE_TYPE = {
    "State Government": "Govt",
    "Private Aided (Government Aided)": "Aided",
    "Private Un-Aided": "Self Finance",
}
# PM Vidyalaxmi management type, used only when no colleges name the university's type.
MANAGEMENT_TO_UNIVERSITY_TYPE = {
    "Central Government": "Central Government Institution",
    "State Government": "State Public University",
    "Private": "Private University",
}


def model_for_code(code):
    return University if code.upper().startswith("U-") else College


class Command(BaseCommand):
    help = "Imports the AISHE master list of Haryana colleges, standalone institutions and universities."

    def add_arguments(self, parser):
        data_dir = os.path.join(settings.BASE_DIR, "data", "aishe_import")
        parser.add_argument("--source", default=os.path.join(data_dir, "aishe_haryana_registry.json"))
        parser.add_argument("--links", default=os.path.join(data_dir, "aishe_dhe_links.csv"))
        parser.add_argument("--dry-run", action="store_true", help="Report what would change and roll back.")
        parser.add_argument(
            "--allow-without-dhe",
            action="store_true",
            help="Run even though the DHE registry (import_haryana_institutions) has not been loaded.",
        )

    def handle(self, *args, **options):
        if not os.path.exists(options["source"]):
            raise CommandError(f"AISHE registry not found: {options['source']} (run build_aishe_registry)")
        with open(options["source"], encoding="utf-8") as f:
            registry = json.load(f)
        records = registry["institutions"]
        as_on = {kind: sheet.get("as_on", "") for kind, sheet in registry.get("sheets", {}).items()}

        dhe_loaded = (
            College.objects.filter(institute_code__isnull=False).exists()
            or University.objects.filter(institute_code__isnull=False).exists()
        )
        if not dhe_loaded and not options["allow_without_dhe"]:
            raise CommandError(
                "The DHE registry is not loaded. Run import_haryana_institutions first "
                "(or pass --allow-without-dhe), otherwise DHE records would later duplicate AISHE ones."
            )

        self.stats = dict.fromkeys(
            [
                "links_applied", "links_unchanged", "links_conflict", "links_missing_target", "duplicates_removed",
                "colleges_created", "colleges_updated", "universities_created", "universities_updated",
                "already_registered", "unchanged",
            ],
            0,
        )
        dry_run = options["dry_run"]
        with transaction.atomic():
            self._apply_links(options["links"])
            for rec in records:
                self._import_record(rec, as_on.get(rec["kind"], ""))
            stale = self._dhe_codes_missing_from_aishe({r["aishe_code"] for r in records})
            if dry_run:
                transaction.set_rollback(True)

        s = self.stats
        self.stdout.write(self.style.SUCCESS(f"AISHE registry import ({'DRY RUN, rolled back' if dry_run else 'committed'})"))
        self.stdout.write(f"  Records in AISHE list:          {len(records)} {registry.get('counts', {})}")
        self.stdout.write(f"  DHE links applied/unchanged:    {s['links_applied']}/{s['links_unchanged']}"
                          f" (duplicates removed: {s['duplicates_removed']}, conflicts: {s['links_conflict']},"
                          f" missing DHE row: {s['links_missing_target']})")
        self.stdout.write(f"  Already in DHE registry:        {s['already_registered']}")
        self.stdout.write(f"  Colleges created/updated:       {s['colleges_created']}/{s['colleges_updated']}")
        self.stdout.write(f"  Universities created/updated:   {s['universities_created']}/{s['universities_updated']}")
        self.stdout.write(f"  AISHE rows unchanged:           {s['unchanged']}")
        self.stdout.write(f"  DHE AISHE codes not in AISHE list (left as is): {len(stale)}")
        for line in stale if options["verbosity"] > 1 else []:
            self.stdout.write(f"    {line}")

    # -- DHE record corrections -------------------------------------------------------------------

    def _apply_links(self, links_path):
        if not os.path.exists(links_path):
            return
        with open(links_path, encoding="utf-8", newline="") as f:
            links = [row for row in csv.DictReader(f) if row["status"].strip().lower() == "confirmed"]
        for link in links:
            code = link["aishe_code"].strip().upper()
            current = link["current_aishe_code"].strip().upper()
            model = model_for_code(code)
            target = model.objects.filter(institute_code=link["institute_code"].strip()).first()
            if target is None:
                self.stats["links_missing_target"] += 1
                continue
            if target.aishe_code.upper() == code:
                self.stats["links_unchanged"] += 1
                continue
            if target.aishe_code.upper() != current:
                self.stderr.write(self.style.WARNING(
                    f"Link skipped: {model.__name__} {target.institute_code} has AISHE '{target.aishe_code}',"
                    f" expected '{current}' before assigning {code}."
                ))
                self.stats["links_conflict"] += 1
                continue
            # A row created by an earlier run of this command for the same code is the same institution.
            duplicate = model.objects.filter(aishe_code__iexact=code, source_reference__startswith=AISHE_SOURCE_PREFIX)
            for row in duplicate:
                if self._is_referenced(row):
                    self.stderr.write(self.style.WARNING(
                        f"Link skipped: {code} is already used by {model.__name__} id={row.id}, which has dependent records."
                    ))
                    self.stats["links_conflict"] += 1
                    break
            else:
                self.stats["duplicates_removed"] += duplicate.count()
                duplicate.delete()
                target.aishe_code = code
                target.save(update_fields=["aishe_code"])
                self.stats["links_applied"] += 1

    @staticmethod
    def _is_referenced(obj):
        for rel in obj._meta.related_objects:
            if rel.related_model.objects.filter(**{rel.field.name: obj}).exists():
                return True
        return False

    # -- AISHE records ----------------------------------------------------------------------------

    def _import_record(self, rec, as_on):
        code = rec["aishe_code"]
        model = University if rec["kind"] == "university" else College
        fields = self._university_fields(rec) if model is University else self._college_fields(rec)
        fields["source_reference"] = f"{AISHE_SOURCE_PREFIX}{rec['kind']} list as on {as_on}".strip()

        existing = list(model.objects.filter(aishe_code__iexact=code))
        if not existing:
            model.objects.create(aishe_code=code, **fields)
            self.stats[f"{'universities' if model is University else 'colleges'}_created"] += 1
            return
        owned = [row for row in existing if row.source_reference.startswith(AISHE_SOURCE_PREFIX)]
        if len(owned) < len(existing):
            # The DHE registry holds this code. A row this command created earlier (before the DHE row
            # existed) is a duplicate of it; drop it unless something already refers to it.
            for row in owned:
                if self._is_referenced(row):
                    self.stderr.write(self.style.WARNING(
                        f"{code}: {model.__name__} id={row.id} duplicates a DHE record but has dependent records; left in place."
                    ))
                else:
                    row.delete()
                    self.stats["duplicates_removed"] += 1
            self.stats["already_registered"] += 1
            return
        for row in owned:
            changed = [name for name, value in fields.items() if getattr(row, name) != value]
            if changed:
                for name in changed:
                    setattr(row, name, fields[name])
                row.save(update_fields=changed)
                self.stats[f"{'universities' if model is University else 'colleges'}_updated"] += 1
            else:
                self.stats["unchanged"] += 1

    @staticmethod
    def _college_fields(rec):
        management = rec["management"]
        return {
            "name": rec["name"],
            "department": "",
            "district": rec["district"],
            "institute_type": MANAGEMENT_TO_INSTITUTE_TYPE.get(management, management),
            "institute_category": rec["institution_type"],
            "affiliation_body_1": rec["university_name"],
            "affiliation_body_2": "",
            "is_verified": True,
        }

    @staticmethod
    def _university_fields(rec):
        return {
            "name": rec["name"],
            "district": rec["district"],
            "state": "Haryana",
            "university_type": (
                rec["university_type"]
                or MANAGEMENT_TO_UNIVERSITY_TYPE.get(rec["management"])
                or "Not specified in AISHE list"
            ),
            "is_active": True,
        }

    # -- Reporting ----------------------------------------------------------------------------------

    @staticmethod
    def _dhe_codes_missing_from_aishe(aishe_codes):
        missing = []
        for model in (College, University):
            rows = (
                model.objects.exclude(aishe_code="")
                .exclude(source_reference__startswith=AISHE_SOURCE_PREFIX)
                .order_by("aishe_code")
            )
            for row in rows:
                if row.aishe_code.upper() not in aishe_codes:
                    missing.append(f"{row.aishe_code}  {model.__name__} {row.institute_code or row.id}  {row.name}")
        return missing
