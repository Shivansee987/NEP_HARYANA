"""Seeds fresh demo colleges/universities and drives their assessments through the live API (dev server on :8000)
so every stage of the workflow has an institution parked in it. Run after wipe_institutions.py.

    PYTHONPATH=demo_tools venv/Scripts/python.exe demo_tools/seed_demo.py   (from the repo root)
"""
import os
import sys

import requests

BASE = os.environ.get("NEP_BASE", "http://127.0.0.1:8000/api")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Backend"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.development"
import django  # noqa: E402

django.setup()
from apps.authentication.models import College, User  # noqa: E402
from apps.evidence.taxonomy import get_subcriterion_contract  # noqa: E402
from apps.scoring.field_schema import COLLEGE_FIELD_SCHEMA, UNIVERSITY_FIELD_SCHEMA  # noqa: E402
from apps.university.models import University  # noqa: E402

PASSWORD = "Demo@1234"

# stage: FRESH (no assessment) | DRAFT (filled + docs, not submitted) | SUBMITTED | IN_REVIEW (evidence verified,
# parameters not yet approved) | READY (all approved, chair only has to Complete -> Award -> Certify)
COLLEGES = [
    ("Government College, Sector 9, Gurugram", "C-DEMO-01", "principal.gurugram@demo.local", "FRESH", None),
    ("Dayanand College, Hisar", "C-DEMO-02", "principal.hisar@demo.local", "DRAFT", "strong"),
    ("Government College for Women, Rohtak", "C-DEMO-03", "principal.rohtak@demo.local", "SUBMITTED", "medium"),
    ("Hindu College, Sonepat", "C-DEMO-04", "principal.sonepat@demo.local", "IN_REVIEW", "medium"),
    ("Dyal Singh College, Karnal", "C-DEMO-05", "principal.karnal@demo.local", "READY", "strong"),
]
UNIVERSITIES = [
    ("Kurukshetra University, Kurukshetra", "U-DEMO-01", "nodal.kuk@demo.local", "FRESH", None),
    ("Maharshi Dayanand University, Rohtak", "U-DEMO-02", "nodal.mdu@demo.local", "SUBMITTED", "medium"),
    ("Guru Jambheshwar University of Science & Technology, Hisar", "U-DEMO-03", "nodal.gju@demo.local", "READY", "strong"),
]

KIND = {
    "COLLEGE": dict(schema=COLLEGE_FIELD_SCHEMA, framework="COLLEGE_2026", api="/v1/college", coll="colleges",
                    assess="college-assessments", role="principal"),
    "UNIVERSITY": dict(schema=UNIVERSITY_FIELD_SCHEMA, framework="UNIVERSITY_2026", api="/v1/university",
                       coll="universities", assess="university-assessments", role="nodal_officer"),
}

OVERRIDES = {
    "C4.A": {"support_areas": ["ACADEMIC_DEVELOPMENT", "FACULTY_DEVELOPMENT", "COMMUNITY_ENGAGEMENT_AND_SERVICE"],
             "other_support_areas": "Library digitisation support for a neighbouring Govt. College"},
    "C4.B": {"schools_covered": 6},
    "C9.II": {"placed_students": 150},
    "C11.II.b": {"monetized_count": 7},
    "C19.III": {"scopus_index": 0},
    "C20.1": {"naac_grade": "A+"},
    "U5.B": {"placed_students": 150},
    "U9.A": {"total_mous": 8, "active_mous": 7},
    "U9.B": {"activities_count": 42},
    "U16.III": {"scopus_index": 0},
}
MEDIUM_OVERRIDES = {"C9.II": {"placed_students": 80}, "U5.B": {"placed_students": 80},
                    "U9.A": {"total_mous": 8, "active_mous": 7}, "U9.B": {"activities_count": 21},
                    "C19.III": {"scopus_index": 0}, "U16.III": {"scopus_index": 0}}


def call(s, method, path, **kw):
    r = s.request(method, BASE + path, **kw)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text[:300]


def must(label, code, body, ok=(200, 201)):
    if code not in ok:
        raise SystemExit(f"FAILED {label}: {code} {str(body)[:800]}")
    return body


def login(email, pw):
    s = requests.Session()
    body = must(f"login {email}", *call(s, "POST", "/auth/login/", json={"email": email, "password": pw}))
    s.headers["Authorization"] = f"Bearer {body['tokens']['access']}"
    return s


def pick_date(f):
    d = "2025-08-01" if f["key"].endswith("start") else "2026-03-31"
    if f.get("min_date") and d < f["min_date"]:
        d = f["min_date"]
    if f.get("max_date") and d > f["max_date"]:
        d = f["max_date"]
    return d


def value_for(f, profile, i):
    t, medium = f["type"], profile == "medium"
    if t == "integer":
        v = 185 if f.get("max_field") else (200 if any(w in f["key"] for w in ("students", "targets", "total")) else 12)
        return max(1, v * 11 // 20) if medium else v
    if t == "currency":
        return 1200000 if medium else 2500000
    if t == "boolean":
        return not (medium and i % 3 == 2)
    if t == "enum":
        return f["options"][len(f["options"]) // 2 if medium else 0]["value"]
    if t == "multi_enum":
        return [o["value"] for o in f["options"][: 1 if medium else 2]]
    if t == "text_list":
        return "Activity report 2025-26"
    if t == "date":
        return pick_date(f)


def payload(schema, p_code, profile):
    out, i = {}, 0
    for s_code, sub in schema[p_code]["subcriteria"].items():
        vals = {}
        for f in sub["fields"]:
            vals[f["key"]] = value_for(f, profile, i)
            i += 1
        overrides = OVERRIDES if profile == "strong" else MEDIUM_OVERRIDES
        vals.update({k: v for k, v in overrides.get(s_code, {}).items() if k in vals})
        out[s_code] = vals
    return out


def pdf_for(title, line):
    text = f"BT /F1 16 Tf 40 760 Td ({title}) Tj 0 -28 Td /F1 11 Tf ({line}) Tj 0 -18 Td (Academic session 2025-26) Tj ET"
    objs = [
        "<</Type/Catalog/Pages 2 0 R>>",
        "<</Type/Pages/Kids[3 0 R]/Count 1>>",
        "<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        f"<</Length {len(text)}>>stream\n{text}\nendstream",
        "<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def pdf_safe(s):
    return "".join(ch for ch in s if 32 <= ord(ch) < 127 and ch not in "()\\")


def create_institution(kind, name, code, email):
    if kind == "COLLEGE":
        inst = College.objects.create(name=name, aishe_code=code)
        User.objects.create_user(email=email, password=PASSWORD, full_name=f"Principal, {name}", role="principal",
                                 college=inst)
    else:
        inst = University.objects.create(name=name, aishe_code=code, contact_email=email)
        User.objects.create_user(email=email, password=PASSWORD, full_name=f"Nodal Officer, {name}",
                                 role="nodal_officer", university=inst)
    return inst


def run(kind, name, code, email, stage, profile, staff):
    k = KIND[kind]
    inst = create_institution(kind, name, code, email)
    if stage == "FRESH":
        return name, stage, None, "-"
    owner = login(email, PASSWORD)
    body = must("create assessment", *call(owner, "POST", f"{k['api']}/{k['coll']}/{inst.pk}/assessments/",
                                           json={"academic_year": "2025-26"}))
    aid = body["assessment_id"]
    base = f"{k['api']}/{k['assess']}/{aid}"

    schema = k["schema"]
    for p_code in schema:
        must(f"save {p_code}", *call(owner, "PUT", f"{base}/parameters/{p_code}/",
                                     json={"raw_inputs": payload(schema, p_code, profile)}))
    for p_code, p_s in schema.items():
        for s_code, sub in p_s["subcriteria"].items():
            c = get_subcriterion_contract(k["framework"], p_code, s_code)
            if c is None or c.is_source_silent or c.is_unresolved or not c.canonical_evidence_type:
                continue
            doc = pdf_for(pdf_safe(f"{name} - {s_code}")[:70], pdf_safe(c.source_documentary_requirement or "")[:90])
            must(f"upload {s_code}", *call(owner, "POST", "/evidence/", files={
                "file": (f"{code}_{s_code}.pdf", doc, "application/pdf")}, data={
                "assessment_id": aid, "framework": k["framework"], "institution_type": kind,
                "evidence_type": c.canonical_evidence_type, "document_date": "2025-10-15",
                "academic_year": sub.get("evidence_academic_year") or "2025-26",
                "parameter_id": p_code, "subcriterion_id": s_code}))
    if stage == "DRAFT":
        return name, stage, aid, "-"

    must("submit", *call(owner, "POST", f"{base}/submit/"))
    if stage == "SUBMITTED":
        return name, stage, aid, "-"

    cm, ch = staff
    must("start review", *call(cm, "POST", f"{base}/start-review/", json={"comments": "Review started"}))
    detail = must("inspect", *call(cm, "GET", f"/v1/admin/assessments/{aid}/inspect/"))
    for a in detail.get("evidence_associations", []):
        must(f"verify {a.get('subcriterion_id')}", *call(
            cm, "POST", f"/evidence/associations/{a.get('association_id') or a.get('id')}/verify/",
            json={"reason": "Document checked against the claim", "metadata": {}}))
    if stage == "READY":
        for p_code in schema:
            must(f"accept {p_code}", *call(ch, "POST", f"{base}/parameters/{p_code}/accept-score/",
                                           json={"comments": "Approved"}))
    ev = must("evaluate", *call(ch, "GET", f"{base}/evaluate/"))
    return name, stage, aid, (f"{ev.get('expected_total_display')} | {ev.get('certification_status')} | "
                              f"approved {ev.get('parameters_reviewed_count')} | blocking {ev.get('blocking_reasons')}")


if __name__ == "__main__":
    staff = (login("committee@dev.local", "DevCommittee@123"), login("chair@dev.local", "DevChair@123"))
    rows = [run("COLLEGE", *c, staff) for c in COLLEGES] + [run("UNIVERSITY", *u, staff) for u in UNIVERSITIES]
    for r in rows:
        print(" | ".join(str(x) for x in r))
