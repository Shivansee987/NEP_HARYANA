"""
Management command to import and reconcile the complete Haryana Higher Education
Institution Registry from the extracted DHE scholarship dataset into College and
University models.

Supports idempotent execution, dry-run simulation, and in-place reconciliation
of existing demo institutions to protect foreign-key relationships and assessments.
"""

import json
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from apps.authentication.models import College
from apps.university.models import University


class Command(BaseCommand):
    help = "Imports and reconciles the 1,152 Haryana Higher Education institutions from DHE JSON registry."

    DEMO_COLLEGE_RECONCILIATION = {
        "1034": ("C-DEMO-01", "Government College, Sector 9, Gurugram", "C-28137"),
        "1191": ("C-DEMO-02", "Dayanand College, Hisar", "C-10646"),
        "1128": ("C-DEMO-03", "Government College for Women, Rohtak", "C-28212"),
        "1243": ("C-DEMO-04", "Hindu College, Sonepat", "C-28123"),
        "1207": ("C-DEMO-05", "Dyal Singh College, Karnal", "C-10569"),
    }

    DEMO_UNIVERSITY_RECONCILIATION = {
        "1943": ("U-DEMO-01", "Kurukshetra University, Kurukshetra", "U-0164"),
        "1944": ("U-DEMO-02", "Maharshi Dayanand University, Rohtak", "U-0167"),
        "1954": ("U-DEMO-03", "Guru Jambheshwar University of Science & Technology, Hisar", "U-0162"),
    }

    def add_arguments(self, parser):
        default_json = os.path.join(settings.BASE_DIR, "data", "aishe_import", "haryana_institutions_raw.json")
        parser.add_argument(
            "--source",
            type=str,
            default=default_json,
            help="Path to the haryana_institutions_raw.json file.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the import and report reconciliation metrics without committing database changes.",
        )
        parser.add_argument(
            "--reconcile-demo",
            action="store_true",
            default=True,
            help="Safely reconcile pre-existing demo records in place (default: True).",
        )
        parser.add_argument(
            "--no-reconcile",
            action="store_true",
            help="Disable demo reconciliation; import or match solely by institute_code.",
        )

    def handle(self, *args, **options):
        source_path = options["source"]
        dry_run = options["dry_run"]
        no_reconcile = options["no_reconcile"]
        reconcile_demo = options["reconcile_demo"] and not no_reconcile

        if not os.path.exists(source_path):
            self.stderr.write(self.style.ERROR(f"Source file not found: {source_path}"))
            return

        with open(source_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        self.stdout.write(self.style.NOTICE(f"Loaded {len(records)} records from {source_path}."))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN ENABLED - No changes will be written to the database."))

        stats = {
            "total_processed": 0,
            "colleges_created": 0,
            "colleges_updated": 0,
            "colleges_unchanged": 0,
            "colleges_reconciled": 0,
            "universities_created": 0,
            "universities_updated": 0,
            "universities_unchanged": 0,
            "universities_reconciled": 0,
            "skipped": 0,
            "flagged_missing_aishe": 0,
            "flagged_shared_aishe": 0,
            "flagged_other": 0,
            "errors": 0,
        }

        # Track AISHE frequencies to audit shared codes
        aishe_counts = {}
        for r in records:
            c = (r.get("aishe_code") or "").strip()
            if c:
                aishe_counts[c] = aishe_counts.get(c, 0) + 1

        with transaction.atomic():
            for rec in records:
                stats["total_processed"] += 1
                inst_code = str(rec.get("institute_code") or "").strip()
                name = (rec.get("institute_name") or "").strip()
                aishe = (rec.get("aishe_code") or "").strip()
                dept = (rec.get("department") or "Directorate of Higher Education").strip()
                dist = (rec.get("district") or "").strip()
                itype = (rec.get("institute_type") or "").strip()
                icat = (rec.get("institute_category") or "").strip()
                aff1 = (rec.get("affiliation_body_1") or "").strip()
                aff2 = (rec.get("affiliation_body_2") or "").strip()
                page_no = rec.get("page_number", "")
                sr_no = rec.get("serial_number", "")

                source_ref = f"DHE Portal PDF 2026, Page {page_no}, Sr {sr_no}"

                # Audit flags
                if not aishe:
                    stats["flagged_missing_aishe"] += 1
                elif aishe_counts.get(aishe, 0) > 1:
                    stats["flagged_shared_aishe"] += 1

                # Routing decision: True universities have institute_category in ('University', 'University Campus')
                is_university = icat in ("University", "University Campus")

                if is_university:
                    self._process_university(
                        rec=rec,
                        inst_code=inst_code,
                        name=name,
                        aishe=aishe,
                        dist=dist,
                        itype=itype,
                        source_ref=source_ref,
                        stats=stats,
                        dry_run=dry_run,
                        reconcile_demo=reconcile_demo,
                    )
                else:
                    self._process_college(
                        rec=rec,
                        inst_code=inst_code,
                        name=name,
                        aishe=aishe,
                        dept=dept,
                        dist=dist,
                        itype=itype,
                        icat=icat,
                        aff1=aff1,
                        aff2=aff2,
                        source_ref=source_ref,
                        stats=stats,
                        dry_run=dry_run,
                        reconcile_demo=reconcile_demo,
                    )

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry run simulation complete. Transaction rolled back successfully."))

        # Summary output
        self.stdout.write(self.style.SUCCESS("\n======================================================="))
        self.stdout.write(self.style.SUCCESS("  HARYANA INSTITUTION REGISTRY IMPORT & AUDIT REPORT   "))
        self.stdout.write(self.style.SUCCESS("======================================================="))
        self.stdout.write(f"  Execution Mode:         {'DRY RUN (Simulation)' if dry_run else 'LIVE DATABASE COMMIT'}")
        self.stdout.write(f"  Total Records Processed:{stats['total_processed']}")
        self.stdout.write("-------------------------------------------------------")
        self.stdout.write("  COLLEGES:")
        self.stdout.write(f"    Created:              {stats['colleges_created']}")
        self.stdout.write(f"    Updated:              {stats['colleges_updated']}")
        self.stdout.write(f"    Unchanged:            {stats['colleges_unchanged']}")
        self.stdout.write(f"    Reconciled from Demo: {stats['colleges_reconciled']}")
        self.stdout.write("-------------------------------------------------------")
        self.stdout.write("  UNIVERSITIES:")
        self.stdout.write(f"    Created:              {stats['universities_created']}")
        self.stdout.write(f"    Updated:              {stats['universities_updated']}")
        self.stdout.write(f"    Unchanged:            {stats['universities_unchanged']}")
        self.stdout.write(f"    Reconciled from Demo: {stats['universities_reconciled']}")
        self.stdout.write("-------------------------------------------------------")
        self.stdout.write("  AUDIT & PROVENANCE FLAGS:")
        self.stdout.write(f"    Missing AISHE Codes:  {stats['flagged_missing_aishe']} (retained with DHE institute code)")
        self.stdout.write(f"    Shared AISHE Codes:   {stats['flagged_shared_aishe']} (multi-institute shared identifiers)")
        self.stdout.write(f"    Total Skipped:        {stats['skipped']}")
        self.stdout.write(f"    Total Errors:         {stats['errors']}")
        self.stdout.write(self.style.SUCCESS("=======================================================\n"))

    def _process_university(self, rec, inst_code, name, aishe, dist, itype, source_ref, stats, dry_run, reconcile_demo):
        # 1. Matching by official DHE institute code first
        uni = University.objects.filter(institute_code=inst_code).first()
        if uni:
            # Check if any field differs
            uni_type = "State Public University" if itype == "Govt" else (itype or "State Public University")
            has_changes = (
                uni.name != name
                or uni.aishe_code != aishe
                or uni.district != dist
                or uni.university_type != uni_type
                or uni.source_reference != source_ref
            )
            if has_changes:
                if not dry_run:
                    uni.name = name
                    uni.aishe_code = aishe
                    uni.district = dist
                    uni.university_type = uni_type
                    uni.source_reference = source_ref
                    uni.is_active = True
                    uni.save()
                stats["universities_updated"] += 1
            else:
                stats["universities_unchanged"] += 1
            return

        # 2. Reconcile pre-existing demo university record in-place
        if reconcile_demo and inst_code in self.DEMO_UNIVERSITY_RECONCILIATION:
            demo_aishe, demo_name, official_aishe = self.DEMO_UNIVERSITY_RECONCILIATION[inst_code]
            uni = University.objects.filter(aishe_code=demo_aishe).first()
            if not uni:
                uni = University.objects.filter(name__icontains=demo_name[:20], institute_code__isnull=True).first()
            if uni:
                if not dry_run:
                    uni.name = name
                    uni.institute_code = inst_code
                    uni.aishe_code = aishe or official_aishe
                    uni.district = dist
                    uni.university_type = "State Public University" if itype == "Govt" else (itype or "State Public University")
                    uni.source_reference = source_ref
                    uni.is_active = True
                    uni.save()
                stats["universities_reconciled"] += 1
                stats["universities_updated"] += 1
                return

        # 3. Create new University entity
        if not dry_run:
            University.objects.create(
                name=name,
                institute_code=inst_code,
                aishe_code=aishe,
                district=dist,
                university_type="State Public University" if itype == "Govt" else (itype or "State Public University"),
                state="Haryana",
                source_reference=source_ref,
                is_active=True,
            )
        stats["universities_created"] += 1

    def _process_college(self, rec, inst_code, name, aishe, dept, dist, itype, icat, aff1, aff2, source_ref, stats, dry_run, reconcile_demo):
        # 1. Matching by official DHE institute code first
        college = College.objects.filter(institute_code=inst_code).first()
        if college:
            has_changes = (
                college.name != name
                or college.aishe_code != aishe
                or college.department != dept
                or college.district != dist
                or college.institute_type != itype
                or college.institute_category != icat
                or college.affiliation_body_1 != aff1
                or college.affiliation_body_2 != aff2
                or college.source_reference != source_ref
            )
            if has_changes:
                if not dry_run:
                    college.name = name
                    college.aishe_code = aishe
                    college.department = dept
                    college.district = dist
                    college.institute_type = itype
                    college.institute_category = icat
                    college.affiliation_body_1 = aff1
                    college.affiliation_body_2 = aff2
                    college.source_reference = source_ref
                    college.is_verified = True
                    college.save()
                stats["colleges_updated"] += 1
            else:
                stats["colleges_unchanged"] += 1
            return

        # 2. Reconcile pre-existing demo college record in-place
        if reconcile_demo and inst_code in self.DEMO_COLLEGE_RECONCILIATION:
            demo_aishe, demo_name, official_aishe = self.DEMO_COLLEGE_RECONCILIATION[inst_code]
            college = College.objects.filter(aishe_code=demo_aishe).first()
            if not college:
                college = College.objects.filter(name__icontains=demo_name[:15], institute_code__isnull=True).first()
            if college:
                if not dry_run:
                    college.name = name
                    college.institute_code = inst_code
                    college.aishe_code = aishe or official_aishe
                    college.department = dept
                    college.district = dist
                    college.institute_type = itype
                    college.institute_category = icat
                    college.affiliation_body_1 = aff1
                    college.affiliation_body_2 = aff2
                    college.source_reference = source_ref
                    college.is_verified = True
                    college.save()
                stats["colleges_reconciled"] += 1
                stats["colleges_updated"] += 1
                return

        # 3. Create new College entity
        if not dry_run:
            College.objects.create(
                name=name,
                institute_code=inst_code,
                aishe_code=aishe,
                department=dept,
                district=dist,
                institute_type=itype,
                institute_category=icat,
                affiliation_body_1=aff1,
                affiliation_body_2=aff2,
                source_reference=source_ref,
                is_verified=True,
            )
        stats["colleges_created"] += 1
