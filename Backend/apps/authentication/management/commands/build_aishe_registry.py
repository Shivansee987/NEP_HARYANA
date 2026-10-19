"""
Converts the AISHE portal Excel exports for Haryana into the JSON registry read by
`import_aishe_registry`.

Inputs (from the AISHE portal, "ALL COLLEGE", "ALL STANDALONE", "ALL UNIVERSITIES" and
"PM Vidyalaxmi Institutes (All)" reports):
    College-ALL COLLEGE.xlsx, Standalone-ALL STANDALONE.xlsx,
    University-ALL UNIVERSITIES.xlsx, vidya_lakshmiAll.xlsx (optional)

Output: data/aishe_import/aishe_haryana_registry.json

Needs openpyxl, which is a development-only dependency (`pip install openpyxl`).
"""

import json
import os
import re
from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

SHEETS = {
    "college": "College-ALL COLLEGE.xlsx",
    "standalone": "Standalone-ALL STANDALONE.xlsx",
    "university": "University-ALL UNIVERSITIES.xlsx",
}
VIDYALAXMI_SHEET = "vidya_lakshmiAll.xlsx"
CODE_PATTERN = {"college": r"C-\d+", "standalone": r"S-\d+", "university": r"U-\d+"}


def clean(value):
    """Collapses whitespace and line breaks; AISHE uses '-' for 'not reported'."""
    text = " ".join(str(value or "").split())
    return "" if text == "-" else text


def read_sheet(path):
    import openpyxl

    rows = list(openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))
    # Row 1 is the report title, row 2 "(As on Date: DD-MM-YYYY HH:MM:SS)", row 3 the header.
    as_on = re.search(r"\d{2}-\d{2}-\d{4}", str(rows[1][0] or ""))
    header = [clean(h) for h in rows[2]]
    records = [dict(zip(header, r)) for r in rows[3:] if any(clean(v) for v in r)]
    return (as_on.group(0) if as_on else ""), records


class Command(BaseCommand):
    help = "Builds data/aishe_import/aishe_haryana_registry.json from the AISHE portal Excel exports."

    def add_arguments(self, parser):
        parser.add_argument(
            "--xlsx-dir",
            default=os.path.join(os.path.dirname(settings.BASE_DIR), "docs"),
            help="Directory holding the AISHE Excel exports (default: <repo>/docs).",
        )
        parser.add_argument(
            "--output",
            default=os.path.join(settings.BASE_DIR, "data", "aishe_import", "aishe_haryana_registry.json"),
        )

    def handle(self, *args, **options):
        try:
            import openpyxl  # noqa: F401
        except ImportError as exc:
            raise CommandError("openpyxl is required to read the Excel exports: pip install openpyxl") from exc

        xlsx_dir = options["xlsx_dir"]
        institutions, sources = [], {}
        for kind, filename in SHEETS.items():
            path = os.path.join(xlsx_dir, filename)
            if not os.path.exists(path):
                raise CommandError(f"Missing AISHE export: {path}")
            as_on, rows = read_sheet(path)
            sources[kind] = {"file": filename, "as_on": as_on, "rows": len(rows)}
            for row in rows:
                code = clean(row.get("Aishe Code")).upper()
                if not re.fullmatch(CODE_PATTERN[kind], code):
                    raise CommandError(f"{filename}: unexpected AISHE code {code!r} for {clean(row.get('Name'))!r}")
                if clean(row.get("State")).lower() != "haryana":
                    continue
                institutions.append({
                    "aishe_code": code,
                    "kind": kind,
                    "name": clean(row.get("Name")),
                    "district": clean(row.get("District")),
                    "website": clean(row.get("Website")),
                    "year_of_establishment": clean(row.get("Year Of Establishment")),
                    "location": clean(row.get("Location")),
                    "institution_type": clean(row.get("College Type") or row.get("Standalone Type")),
                    "management": clean(row.get("Manegement")),
                    "university_aishe_code": clean(row.get("University Aishe Code")).upper(),
                    "university_name": clean(row.get("University Name")),
                    "university_type": clean(row.get("University Type")),
                    "pm_vidyalaxmi": False,
                })

        duplicates = [code for code, n in Counter(i["aishe_code"] for i in institutions).items() if n > 1]
        if duplicates:
            raise CommandError(f"AISHE codes repeated across the exports: {duplicates[:20]}")

        # University type is not in the university export; take it from the colleges'
        # affiliating-university columns, else from the PM Vidyalaxmi management type.
        affiliating_types = {
            i["university_aishe_code"]: i["university_type"] for i in institutions if i["university_aishe_code"]
        }
        vidyalaxmi = {}
        vl_path = os.path.join(xlsx_dir, VIDYALAXMI_SHEET)
        if os.path.exists(vl_path):
            as_on, rows = read_sheet(vl_path)
            vidyalaxmi = {clean(r.get("AISHE Code")).upper(): clean(r.get("Management Type")) for r in rows}
            sources["pm_vidyalaxmi"] = {"file": VIDYALAXMI_SHEET, "as_on": as_on, "rows": len(rows)}
        for inst in institutions:
            inst["pm_vidyalaxmi"] = inst["aishe_code"] in vidyalaxmi
            if inst["kind"] == "university":
                inst["university_type"] = affiliating_types.get(inst["aishe_code"], "")
                inst["management"] = vidyalaxmi.get(inst["aishe_code"], "")

        institutions.sort(key=lambda i: (list(SHEETS).index(i["kind"]), i["aishe_code"]))
        counts = dict(Counter(i["kind"] for i in institutions))
        counts["pm_vidyalaxmi"] = sum(i["pm_vidyalaxmi"] for i in institutions)
        payload = {"source": "AISHE portal exports (aishe.gov.in), State: Haryana", "sheets": sources,
                   "counts": counts, "institutions": institutions}

        os.makedirs(os.path.dirname(options["output"]), exist_ok=True)
        with open(options["output"], "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
            f.write("\n")
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(institutions)} institutions to {options['output']}: {counts}"))
