"""
NEP Excellence Awards 2026 - Parameter & Subcriterion Definitions

Scoring rules transcribed from the source PDFs:
  University Parameters - NEP Excellence Awards 2026.pdf (U1–U20, 100 marks)
  College Parameters - NEP Excellence Awards 2026.pdf (C1–C22, 100 marks)

Each subcriterion carries a `metric` describing how its value is derived from the canonical inputs
(apps.scoring.field_schema) and, where applicable, the source `thresholds`.

Metric kinds:
  ratio       numerator/denominator percentage (denominator may come from a sibling subcriterion)
  count       non-negative integer compared with thresholds
  per_unit    unit_score per unit, capped at max_score
  boolean     criterion met -> max_score
  grade       enum value mapped to a score
  currency    INR amount compared with thresholds
  average     numerator / sibling denominator, tiered (fractional tiering is policy U9B_FRACTIONAL_AVERAGE)
  areas       0.5 per distinct area listed, capped (optionally gated on a minimum count)
  policy_metric  thresholds apply only once the named policy defines the metric (SCOPUS_METRIC)

Items the source leaves open are NOT decided here; see apps.scoring.policy.
"""
from typing import Any, Dict

from apps.scoring.enums import (
    DoubleCountingRule,
    EvaluationType,
    FrameworkType,
    PeriodRule,
    ResolutionStatus,
    ThresholdOperator as Op,
)
from apps.scoring.field_schema import COLLEGE_FIELD_SCHEMA, UNIVERSITY_FIELD_SCHEMA

CALC = ResolutionStatus.CALCULABLE
FORBID = DoubleCountingRule.FORBIDDEN_REUSE


def _gt(v, s): return {"operator": Op.OP_GT, "min_val": float(v), "score": float(s)}
def _gte(v, s): return {"operator": Op.OP_GTE, "min_val": float(v), "score": float(s)}
def _lt(v, s): return {"operator": Op.OP_LT, "max_val": float(v), "score": float(s)}
def _lte(v, s): return {"operator": Op.OP_LTE, "max_val": float(v), "score": float(s)}
def _eq(v, s): return {"operator": Op.OP_EQ, "target_val": float(v), "score": float(s)}
def _gt_lte(a, b, s): return {"operator": Op.OP_GT_AND_LTE, "min_val": float(a), "max_val": float(b), "score": float(s)}
def _gte_lte(a, b, s): return {"operator": Op.OP_GTE_AND_LTE, "min_val": float(a), "max_val": float(b), "score": float(s)}
def _gt_lt(a, b, s): return {"operator": Op.OP_GT_AND_LT, "min_val": float(a), "max_val": float(b), "score": float(s)}


def ratio(num, den, den_from=None, allow_over=False):
    return {"kind": "ratio", "num": num, "den": den, "den_from": den_from, "allow_over": allow_over}


def count(key): return {"kind": "count", "key": key}
def boolean(key="verified"): return {"kind": "boolean", "key": key}
def per_unit(key, unit): return {"kind": "per_unit", "key": key, "unit": float(unit)}


def _param(framework, code, title, max_marks, period_rule, strategy, subcriteria, mandatory_evidence,
           dc_rule=FORBID, **extra) -> Dict[str, Any]:
    return {
        "framework": framework,
        "parameter_code": code,
        "code": code,
        "title": title,
        "max_marks": float(max_marks),
        "period_rule": period_rule,
        "aggregation_strategy": strategy,
        "double_counting_rule": dc_rule,
        "resolution_status": CALC,
        "mandatory_evidence": mandatory_evidence,
        "subcriteria": {s["subcriterion_code"]: s for s in subcriteria},
        **extra,
    }


def _s(code, max_score, metric, thresholds=None, **extra) -> Dict[str, Any]:
    d = {"subcriterion_code": code, "max_score": float(max_score), "metric": metric}
    if thresholds is not None:
        d["thresholds"] = thresholds
    d.update(extra)
    return d


U = FrameworkType.UNIVERSITY_2026
C = FrameworkType.COLLEGE_2026
PS = PeriodRule.PERIOD_SENSITIVE
PI = PeriodRule.PERIOD_INSENSITIVE

# Standard percentage tier sets
_PCT_90_75_50_25 = [_gt(90, 4), _gt_lte(75, 90, 3), _gt_lte(50, 75, 2), _gt_lte(25, 50, 1), _lte(25, 0)]

UNIVERSITY_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "U1": _param(U, "U1", "Apprenticeship Embedded Degree Programmes", 4, PI, EvaluationType.MAX, [
        _s("U1.1", 4, count("programmes_count"),
           [_gt(10, 4), _gt_lte(7, 10, 3), _gt_lte(4, 7, 2), _gt_lte(0, 4, 1), _eq(0, 0)]),
    ], ["EVID_U1_APPROVAL"]),
    "U2": _param(U, "U2", "Courses Offered in Indian Languages", 4, PI, EvaluationType.MAX, [
        _s("U2.1", 4, ratio("indian_lang_programmes", "total_degree_programmes"),
           [_gt(75, 4), _gt_lte(50, 75, 3), _gt_lte(25, 50, 2), _gt_lte(0, 25, 1), _eq(0, 0)]),
    ], ["EVID_U2_COURSE_LIST"]),
    "U3": _param(U, "U3", "Integration of Indian Knowledge Systems (IKS)", 4, PI, EvaluationType.MAX, [
        _s("U3.1", 4, ratio("iks_programmes", "total_degree_programmes"),
           [_gt(25, 4), _gt_lte(15, 25, 3), _gt_lte(5, 15, 2), _gt_lte(0, 5, 1), _eq(0, 0)]),
    ], ["EVID_U3_SYLLABUS"]),
    "U4": _param(U, "U4", "Targets Achieved under Institutional Development Plan (IDP)", 6, PeriodRule.MULTI_PERIOD, EvaluationType.SUM, [
        _s("U4.A", 3, ratio("achieved_targets_2024_25", "total_targets_2024_25"),
           [_gt(90, 3), _gt_lte(75, 90, 2), _gt_lte(50, 75, 1), _lte(50, 0)],
           mandatory_evidence=["EVID_U4_PROGRESS_REPORT"],
           allowed_evidence=["EVID_U4_IDP", "EVID_U4_TARGET_SHEET", "EVID_U4_PROGRESS_REPORT"],
           evidence_academic_year="2024-25"),
        _s("U4.B", 3, ratio("achieved_targets_2025_26", "total_targets_2025_26"),
           [_gt(90, 3), _gt_lte(75, 90, 2), _gt_lte(50, 75, 1), _lte(50, 0)],
           mandatory_evidence=["EVID_U4_PROGRESS_REPORT"],
           allowed_evidence=["EVID_U4_IDP", "EVID_U4_TARGET_SHEET", "EVID_U4_PROGRESS_REPORT"],
           evidence_academic_year="2025-26"),
    ], ["EVID_U4_PROGRESS_REPORT"], allowed_evidence=["EVID_U4_IDP", "EVID_U4_TARGET_SHEET", "EVID_U4_PROGRESS_REPORT"]),
    "U5": _param(U, "U5", "Percentage of Students Who Received Placement / Pre-Placement Offers", 4, PS, EvaluationType.SUM, [
        _s("U5.A", 2, ratio("eligible_students", "total_final_year_students"),
           [_gt(75, 2), _gt_lte(50, 75, 1), _lt(50, 0)],
           boundary_voids=[{"exact_val": 50.0, "policy_id": "BOUNDARY_U5A_50"}]),
        _s("U5.B", 2, ratio("placed_students", None, den_from=("U5.A", "eligible_students")),
           [_gt(75, 2), _gt_lte(50, 75, 1), _gt_lte(25, 50, 0.5), _lte(25, 0)]),
    ], ["EVID_U5_HOI_CERT"]),
    "U6": _param(U, "U6", "Academic Reforms", 8, PS, EvaluationType.SUM, [
        _s("U6.A", 4, boolean("ordinance_notified")),
        _s("U6.B", 4, per_unit("tools_count", 1)),
    ], ["EVID_U6_ORDINANCE_GAZETTE"]),
    "U7": _param(U, "U7", "Professor of Practice (PoP) Engagement", 4, PS, EvaluationType.FIXED_ITEM_SUM, [
        _s(f"U7.{i}", 1, boolean()) for i in range(1, 5)
    ], ["EVID_U7_APPOINTMENT"]),
    "U8": _param(U, "U8", "Incubation / Startup Cell Performance as per NISP", 6, PS, EvaluationType.COMPOSITE, [
        _s("U8.A", 4, count("startups_count"),
           [_gt(10, 4), _gte_lte(6, 10, 3), _gte_lte(1, 5, 2), _eq(0, 0)]),
        _s("U8.B", 2, ratio("monetized_count", None, den_from=("U8.A", "startups_count")),
           [_gte(50, 2), _lt(50, 0)]),
    ], ["EVID_U8_INCUBATION_REG"], advisory_policy="U8A_COMPONENT_HEADER"),
    "U9": _param(U, "U9", "Academic / Research Collaboration with Foreign HEIs", 6, PS, EvaluationType.COMPOSITE, [
        _s("U9.A", 1, ratio("active_mous", "total_mous"), [_gt(75, 1), _lte(75, 0)]),
        _s("U9.B", 5, {"kind": "average", "num": "activities_count", "den_from": ("U9.A", "active_mous"),
                       "policy_id": "U9B_FRACTIONAL_AVERAGE"},
           [_gte(5, 5), _eq(4, 4), _eq(3, 3), _eq(2, 2), _eq(1, 1), _eq(0, 0)]),
    ], ["EVID_U9_MOU"]),
    "U10": _param(U, "U10", "Functional Alumni Connect Cell", 5, PS, EvaluationType.SUM, [
        _s("U10.1", 1, boolean()),
        _s("U10.2", 1, boolean()),
        _s("U10.3", 2, {"kind": "currency", "key": "funding_amount"},
           [_eq(0, 0), _gt(10000000, 2), _gt_lt(0, 10000000, 1)],
           boundary_voids=[{"exact_val": 10000000.0, "policy_id": "BOUNDARY_U10_3_1CR"}]),
        _s("U10.4", 1, boolean()),
    ], ["EVID_U10_REG_CERT"]),
    "U11": _param(U, "U11", "Gender Parity Initiatives", 4, PS, EvaluationType.FIXED_ITEM_SUM, [
        _s(f"U11.{i}", 1, boolean()) for i in range(1, 5)
    ], ["EVID_U11_BOARDS"]),
    "U12": _param(U, "U12", "Physical Fitness, Sports, Yoga, Students Health, Welfare, Psychological and Emotional Well-being", 5, PS,
                  EvaluationType.FIXED_ITEM_SUM, [
        _s(f"U12.{i}", 1, boolean()) for i in range(1, 6)
    ], ["EVID_U12_CENTRE_NOTIF"]),
    "U13": _param(U, "U13", "Online Courses / MOOCs Policy and Adoption", 6, PS, EvaluationType.MAX, [
        _s("U13.1", 6, ratio("regular_mooc_learners", "total_regular_learners"),
           [_gt(75, 6), _gt_lte(50, 75, 5), _gt_lte(25, 50, 3), _gt_lte(0, 25, 2), _eq(0, 0)]),
    ], ["EVID_U13_POLICY"]),
    "U14": _param(U, "U14", "Multidisciplinary Education", 6, PI, EvaluationType.SUM, [
        _s("U14.A", 4, ratio("multidisciplinary_programmes", "total_degree_programmes"),
           [_gt(90, 4), _gt_lte(75, 90, 3), _gt_lte(50, 75, 2), _gt_lte(25, 50, 1), _lte(25, 0)]),
        _s("U14.B", 1, boolean()),
        _s("U14.C", 1, boolean()),
    ], ["EVID_U14_CURRICULUM"], dc_rule=DoubleCountingRule.REQUIRES_FRAMEWORK_EXCEPTION),
    "U15": _param(U, "U15", "Multiple Entry-Exit Operationalized", 2, PI, EvaluationType.SUM, [
        _s("U15.1", 1, boolean()),
        _s("U15.2", 1, boolean()),
    ], ["EVID_U15_ORDINANCE"]),
    "U16": _param(U, "U16", "Research Outcome: Patents Filed and Granted", 8, PS, EvaluationType.SUM, [
        _s("U16.I", 2, count("patents_filed"), [_gte(10, 2), _gte(5, 1), _lt(5, 0)]),
        _s("U16.II", 2, count("patents_granted"), [_gte(2, 2), _gte(1, 1), _lt(1, 0)]),
        _s("U16.III", 4, {"kind": "policy_metric", "key": "scopus_index", "policy_id": "SCOPUS_METRIC"},
           [_gte(400, 4), _gte(300, 3), _gte(200, 2), _gte(100, 1), _lt(100, 0)]),
    ], ["EVID_U16_FILING"], sibling_entity_reuse=True),
    "U17": _param(U, "U17", "Registration and Performance in NIRF", 2, PeriodRule.REFERENCE_YEAR_DEPENDENT, EvaluationType.SUM, [
        _s("U17.1", 1, boolean()),
        _s("U17.2", 1, boolean()),
    ], ["EVID_U17_NIRF_2026_PROOF"]),
    "U18": _param(U, "U18", "Recognition of Prior Learning (RPL) Adoption and Implementation", 4, PS, EvaluationType.SUM, [
        _s("U18.1", 1, boolean()),
        _s("U18.2", 1, boolean()),
        _s("U18.3", 2, boolean()),
    ], ["EVID_U18_POLICY"]),
    "U19": _param(U, "U19", "Adoption of Outcome-Based Education (OBE)", 8, PS, EvaluationType.SUM, [
        _s("U19.A", 6, ratio("obe_programmes", "total_degree_programmes"),
           [_gt(90, 6), _gt_lte(80, 90, 5), _gt_lte(70, 80, 4), _gt_lte(60, 70, 3), _gt_lte(50, 60, 2),
            _gt_lte(25, 50, 1), _lte(25, 0)]),
        _s("U19.B", 2, boolean()),
    ], ["EVID_U19_OBE_FRAMEWORK"]),
    "U20": _param(U, "U20", "Activities Aligned with Sustainable Development Goals (SDGs)", 4, PS, EvaluationType.SUM, [
        _s("U20.1", 2, count("activities_count"), [_gte(10, 2), _gte_lte(5, 9, 1), _lt(5, 0)]),
        _s("U20.2", 2, boolean()),
        _s("U20.3", 1, boolean()),
    ], ["EVID_U20_ACTIVITY_REPORTS"], advisory_policy="U20_ITEMS_EXCEED_MAXIMUM"),
}

_NAAC_MAP = {"A++": 2.0, "A+": 2.0, "A": 2.0, "B++": 1.0, "B+": 1.0, "B": 1.0, "C": 0.0, "NOT_ACCREDITED": 0.0}

COLLEGE_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "C1": _param(C, "C1", "Institutional Development Plan (IDP) and NEP Implementation Targets", 6,
                 PeriodRule.REFERENCE_YEAR_DEPENDENT, EvaluationType.MAX, [
        _s("C1.1", 6, ratio("achieved_targets_2024_25", "fixed_targets_2024_25"),
           [_gt(90, 6), _gt_lte(75, 90, 4), _gt_lte(50, 75, 2), _lte(50, 1)],
           evidence_academic_year="2024-25"),
    ], ["EVID_C1_APPROVED_IDP"]),
    "C2": _param(C, "C2", "Apprenticeship / Internships", 4, PS, EvaluationType.MAX, [
        _s("C2.1", 4, ratio("students_completed", "eligible_students"), _PCT_90_75_50_25),
    ], ["EVID_C2_HOI_CERT"]),
    "C3": _param(C, "C3", "Academic Bank of Credits (ABC) Registration", 4, PI, EvaluationType.MAX, [
        _s("C3.1", 4, ratio("abc_registered_students", "total_enrolled_students"),
           [_gt(90, 4), _gt_lte(75, 90, 3), _gt_lte(60, 75, 2), _gt_lte(50, 60, 1), _lte(50, 0)]),
    ], ["EVID_C3_ABC_DASHBOARD"]),
    "C4": _param(C, "C4", "Supporting Other Institutes and Schools in Their Development", 4, PS, EvaluationType.SUM, [
        _s("C4.A", 2, {"kind": "areas", "list_keys": ["support_areas", "other_support_areas"], "unit": 0.5}),
        _s("C4.B", 2, {"kind": "areas", "list_keys": ["school_support_areas", "other_school_support_areas"], "unit": 0.5,
                       "gate": {"key": "schools_covered", "min": 5}}),
    ], ["EVID_C4_INSTITUTE_CERTS"]),
    "C5": _param(C, "C5", "Student Enrollment against Sanctioned Seats", 2, PS, EvaluationType.MAX, [
        _s("C5.1", 2, ratio("admitted_students", "sanctioned_intake", allow_over=True),
           [_gte(90, 2), _gt_lt(75, 90, 1), _lt(75, 0)],
           boundary_voids=[{"exact_val": 75.0, "policy_id": "BOUNDARY_C5_75"}]),
    ], ["EVID_C5_SANCTION_LETTER"]),
    "C6": _param(C, "C6", "VAC, AEC, SEC, NSQF-Aligned Courses and Short-Term Certifications", 6, PS, EvaluationType.MAX, [
        _s("C6.1", 6, ratio("certified_students", "total_enrolled_students"),
           [_gt(90, 6), _gt_lte(80, 90, 5), _gt_lte(70, 80, 4), _gt_lte(60, 70, 3), _gt_lte(50, 60, 2), _lte(50, 1)]),
    ], ["EVID_C6_COURSE_APPROVAL"]),
    "C7": _param(C, "C7", "Bridge Courses for SEDGs", 6, PS, EvaluationType.MAX, [
        _s("C7.1", 3, ratio("sedg_bridge_students", "total_sedg_students"),
           [_eq(100, 3), _gte(75, 2), _gte(50, 1), _lt(50, 0)]),
    ], ["EVID_C7_OFFICE_ORDERS"], advisory_policy="C7_MAXIMUM"),
    "C8": _param(C, "C8", "Nomination of NEP-SARTHI", 2, PS, EvaluationType.SUM, [
        _s("C8.1", 2, boolean()),
    ], ["EVID_C8_OFFICE_ORDERS"], advisory_policy="C8_BINARY"),
    "C9": _param(C, "C9", "Student Career Orientation and Placements", 6, PS, EvaluationType.SUM, [
        _s("C9.I", 3, ratio("participating_students", "eligible_students"),
           [_eq(100, 3), _gte(75, 2), _gte(50, 1), _lt(50, 0)]),
        _s("C9.II", 3, ratio("placed_students", None, den_from=("C9.I", "participating_students")),
           [_eq(100, 3), _gte(75, 2), _gte(50, 1), _lt(50, 0)]),
    ], ["EVID_C9_FAIR_REGISTER"]),
    "C10": _param(C, "C10", "Industry Collaboration, MoUs and Industry-Aligned Academic Activities", 5, PS, EvaluationType.MAX, [
        _s("C10.1", 5, count("active_mous_count"),
           [_gte(5, 5), _eq(4, 4), _eq(3, 3), _eq(2, 2), _eq(1, 1), _eq(0, 0)]),
    ], ["EVID_C10_MOU_DOCS"]),
    "C11": _param(C, "C11", "Incubation, Startup Cell and Entrepreneurship Promotion", 5, PS, EvaluationType.SUM, [
        _s("C11.I", 3, count("ventures_count"), [_gt(10, 3), _gte_lte(6, 10, 2), _gte_lte(1, 5, 1), _eq(0, 0)]),
        _s("C11.II.a", 1, boolean("cell_functional")),
        _s("C11.II.b", 1, ratio("monetized_count", None, den_from=("C11.I", "ventures_count")), [_gte(50, 1), _lt(50, 0)]),
    ], ["EVID_C11_REGISTRATION"]),
    "C12": _param(C, "C12", "Alumni Connect and External Expert Engagement", 5, PS, EvaluationType.FIXED_ITEM_SUM, [
        _s(f"C12.{i}", 1, boolean()) for i in range(1, 6)
    ], ["EVID_C12_DATABASE"]),
    "C13": _param(C, "C13", "Faculty Development and NEP Orientation", 4, PS, EvaluationType.MAX, [
        _s("C13.1", 4, ratio("trained_faculty", "total_fulltime_faculty"),
           [_gt(80, 4), _gt_lte(60, 80, 3), _gt_lte(40, 60, 2), _gt_lte(20, 40, 1), _lte(20, 0)]),
    ], ["EVID_C13_FDP_CERTS"]),
    "C14": _param(C, "C14", "Indian Languages and Indian Knowledge System (IKS)", 4, PS, EvaluationType.SUM, [
        _s("C14.A", 2, per_unit("content_items", 0.5)),
        _s("C14.B", 2, count("iks_activities"), [_gte(5, 2), _lt(5, 0)]),
    ], ["EVID_C14_MATERIAL_CERT"]),
    "C15": _param(C, "C15", "Student Well-being, Physical Fitness, Yoga and Sports", 6, PS, EvaluationType.FIXED_ITEM_SUM, [
        _s(f"C15.{i}", 1, boolean()) for i in range(1, 7)
    ], ["EVID_C15_CENTRE_ORDER"]),
    "C16": _param(C, "C16", "Gender Parity, Safety and Inclusion Initiatives", 4, PS, EvaluationType.FIXED_ITEM_SUM, [
        _s(f"C16.{i}", 1, boolean()) for i in range(1, 6)
    ], ["EVID_C16_ICC_ORDERS"], advisory_policy="C16_ITEMS_EXCEED_MAXIMUM"),
    "C17": _param(C, "C17", "Outreach, Community Engagement and Social Responsibility", 5, PS, EvaluationType.MAX, [
        _s("C17.1", 5, ratio("participating_students", "total_enrolled_students"),
           [_gt(90, 5), _gt_lte(75, 90, 4), _gt_lte(60, 75, 3), _gt_lte(50, 60, 2), _gt_lte(0, 50, 1), _eq(0, 0)]),
    ], ["EVID_C17_STUDENT_LIST"]),
    "C18": _param(C, "C18", "Sustainable Development Goals (SDGs), Green Campus and Environmental Practices", 5, PS,
                  EvaluationType.SUM, [
        _s("C18.1", 2, count("sdg_activities"), [_gte(5, 2), _lt(5, 0)]),
        _s("C18.2", 1, boolean()),
        _s("C18.3", 1, boolean()),
        _s("C18.4", 1, boolean()),
    ], ["EVID_C18_ACTIVITY_REPORTS"]),
    "C19": _param(C, "C19", "Research, Innovation and Patents", 6, PS, EvaluationType.SUM, [
        _s("C19.I", 2, count("patents_filed"), [_gte(4, 2), _gte(2, 1), _lt(2, 0)]),
        _s("C19.II", 2, count("patents_granted"), [_gte(2, 2), _gte(1, 1), _lt(1, 0)]),
        _s("C19.III", 2, {"kind": "policy_metric", "key": "scopus_index", "policy_id": "SCOPUS_METRIC"},
           [_gte(100, 2), _gte(50, 1), _lt(50, 0)]),
    ], ["EVID_C19_FILING_CERTS"], sibling_entity_reuse=True),
    "C20": _param(C, "C20", "Quality Assurance, NAAC/NIRF/AISHE and Institutional Reporting", 5, PS, EvaluationType.SUM, [
        _s("C20.1", 2, {"kind": "grade", "key": "naac_grade", "map": _NAAC_MAP},
           tier_1_grades=["A++", "A+", "A"], tier_2_grades=["B++", "B+", "B"]),
        _s("C20.2", 1, boolean()),
        _s("C20.3", 1, boolean()),
        _s("C20.4", 1, boolean()),
    ], ["EVID_C20_NAAC_CERT"]),
    "C21": _param(C, "C21", "Cultural Activities, Constitutional Values and Holistic Development", 4, PS, EvaluationType.SUM, [
        _s("C21.1", 2, count("activities_count"), [_gte(5, 2), _gte_lte(2, 4, 1), _eq(0, 0)],
           boundary_voids=[{"exact_val": 1.0, "policy_id": "BOUNDARY_C21_1_ACTIVITY"}]),
        _s("C21.2", 1, boolean()),
    ], ["EVID_C21_ACTIVITY_REPORTS"], advisory_policy="C21_MAXIMUM"),
    "C22": _param(C, "C22", "Governance, Student Feedback and Evidence-Based Improvement", 2, PS, EvaluationType.SUM, [
        _s("C22.1", 1, boolean()),
        _s("C22.2", 1, boolean()),
    ], ["EVID_C22_NODAL_ORDER"]),
}


def _attach_source_titles(defs: Dict[str, Dict[str, Any]], schema: Dict[str, Dict[str, Any]]) -> None:
    for p_code, p_def in defs.items():
        for s_code, s_def in p_def["subcriteria"].items():
            s_schema = schema[p_code]["subcriteria"][s_code]
            s_def["title"] = s_schema["title"]
            assert float(s_schema["max_score"]) == s_def["max_score"], (s_code, s_schema["max_score"], s_def["max_score"])


_attach_source_titles(UNIVERSITY_PARAMETERS, UNIVERSITY_FIELD_SCHEMA)
_attach_source_titles(COLLEGE_PARAMETERS, COLLEGE_FIELD_SCHEMA)

assert sum(p["max_marks"] for p in UNIVERSITY_PARAMETERS.values()) == 100.0
assert sum(p["max_marks"] for p in COLLEGE_PARAMETERS.values()) == 100.0
