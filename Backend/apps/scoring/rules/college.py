"""
NEP Excellence Awards 2026 - College Parameter Evaluators (C1–C22)
Deterministic rule evaluators anchored strictly to authoritative specifications.
"""
from typing import Any, Callable, Dict, List, Optional, Tuple

from apps.scoring.domain import (
    AssessmentContext,
    ParameterInput,
    ParameterResult,
    SubcriterionInput,
    SubcriterionResult,
)
from apps.scoring.enums import (
    DoubleCountingRule,
    EvaluationType,
    GatingStatus,
    ResolutionStatus,
    ThresholdOperator,
)
from apps.scoring.evaluators.counts import validate_count_quantity
from apps.scoring.evaluators.double_counting import DoubleCountingValidator
from apps.scoring.evaluators.evidence_gating import evaluate_evidence
from apps.scoring.evaluators.percentages import calculate_percentage
from apps.scoring.evaluators.periods import validate_period
from apps.scoring.evaluators.thresholds import evaluate_threshold
from .definitions import COLLEGE_PARAMETERS

COUNT_FIELDS = {
    "programmes_count", "startups_count", "activities_count", "tools_count",
    "patents_filed", "patents_granted", "heis_mentored", "schools_mentored",
    "sdg_activities", "initiatives_count", "events_count", "ventures_count",
    "active_mous_count"
}


def _evaluate_standard_college_subcriterion(
    param_def: Dict[str, Any],
    sub_code: str,
    sub_input: Optional[SubcriterionInput],
    raw_val: Any,
    validator: DoubleCountingValidator,
    context: AssessmentContext,
    target_academic_year: Optional[str] = None,
    is_count: bool = False,
) -> SubcriterionResult:
    sub_def = param_def["subcriteria"][sub_code]
    max_score = float(sub_def["max_score"])
    thresholds = sub_def.get("thresholds", [])
    boundary_voids = sub_def.get("boundary_voids", [])
    mandatory_docs = sub_def.get("mandatory_evidence") if "mandatory_evidence" in sub_def else param_def.get("mandatory_evidence", [])

    trace: Dict[str, Any] = {"subcriterion_code": sub_code, "raw_val": raw_val}

    # If subcriterion is explicitly marked UNRESOLVED in spec
    if sub_def.get("resolution_status") == ResolutionStatus.UNRESOLVED_RULE:
        return SubcriterionResult(
            subcriterion_code=sub_code,
            raw_score=0.0,
            evidence_gated_score=0.0,
            review_adjusted_score=None,
            final_score=None,
            max_score=max_score,
            resolution_status=ResolutionStatus.UNRESOLVED_RULE,
            gating_status=GatingStatus.NO_EVIDENCE_REQUIRED,
            trace={"unresolved_reason": sub_def.get("unresolved_reason", "Unresolved in framework specification")},
        )

    # 0. Count validation (P2-05)
    if sub_input and sub_input.raw_inputs:
        for k, v in sub_input.raw_inputs.items():
            if k in COUNT_FIELDS:
                ok, valid_cnt, err = validate_count_quantity(v, field_name=k)
                if not ok:
                    return SubcriterionResult(
                        subcriterion_code=sub_code,
                        raw_score=0.0,
                        evidence_gated_score=0.0,
                        review_adjusted_score=None,
                        final_score=None,
                        max_score=max_score,
                        resolution_status=ResolutionStatus.INVALID_INPUT,
                        gating_status=GatingStatus.PROVISIONAL_PENDING_VERIFICATION,
                        trace={**trace, "validation_error": err},
                    )

    if is_count:
        ok, valid_val, err = validate_count_quantity(raw_val, field_name=sub_code)
        if not ok:
            return SubcriterionResult(
                subcriterion_code=sub_code,
                raw_score=0.0,
                evidence_gated_score=0.0,
                review_adjusted_score=None,
                final_score=None,
                max_score=max_score,
                resolution_status=ResolutionStatus.INVALID_INPUT,
                gating_status=GatingStatus.PROVISIONAL_PENDING_VERIFICATION,
                trace={**trace, "validation_error": err},
            )
        raw_val = valid_val

    # 1. Period check
    act_date = sub_input.activity_date if sub_input else None
    if not act_date and sub_input and hasattr(sub_input, "raw_inputs") and "activity_date" in sub_input.raw_inputs:
        act_date = sub_input.raw_inputs.get("activity_date")
    hoi_date = sub_input.raw_inputs.get("hoi_certification_date") if (sub_input and hasattr(sub_input, "raw_inputs")) else None

    if act_date or hoi_date:
        p_ok, p_reason = validate_period(
            act_date,
            param_def["period_rule"],
            context.assessment_period,
            target_academic_year=target_academic_year,
            hoi_certification_date=hoi_date,
        )
        trace["period_validation"] = {"valid": p_ok, "reason": p_reason}
        if not p_ok:
            raw_val = 0.0

    # 2. Double-counting check (P2-04 & P2-05)
    v_ents, r_ents, dc_trace = validator.validate_subcriterion_input(
        sub_code,
        sub_input,
        param_def.get("double_counting_rule", DoubleCountingRule.FORBIDDEN_REUSE)
    )
    if dc_trace.get("total_entities_submitted", 0) > 0:
        trace["double_counting"] = dc_trace
    # If raw_val depends on count of entities, adjust by valid count
    if isinstance(raw_val, (int, float)) and r_ents:
        raw_val = len(v_ents)

    # 3. Threshold calculation (RAW SCORE)
    if thresholds:
        score_calc, matched_op, th_trace, res_status = evaluate_threshold(
            raw_val, thresholds, boundary_unresolved_conditions=boundary_voids
        )
        trace["threshold_trace"] = th_trace
        raw_score = score_calc if score_calc is not None else 0.0
    else:
        res_status = ResolutionStatus.CALCULABLE
        matched_op = ThresholdOperator.OP_BOOLEAN
        if isinstance(raw_val, bool):
            raw_score = max_score if raw_val else 0.0
        elif isinstance(raw_val, (int, float)):
            raw_score = min(float(raw_val), max_score)
        else:
            raw_score = 0.0

    if res_status == ResolutionStatus.BOUNDARY_UNRESOLVED:
        return SubcriterionResult(
            subcriterion_code=sub_code,
            raw_score=0.0,
            evidence_gated_score=0.0,
            review_adjusted_score=None,
            final_score=None,
            max_score=max_score,
            resolution_status=ResolutionStatus.BOUNDARY_UNRESOLVED,
            gating_status=GatingStatus.PROVISIONAL_PENDING_VERIFICATION,
            trace=trace,
        )

    # 4. Evidence Gating
    uploaded_docs = sub_input.evidence_docs if sub_input else []
    for doc in uploaded_docs:
        validator.record_document_reference(doc.document_id, sub_code)

    # Filter out documents with explicit mismatched academic year
    valid_docs_for_sub = []
    for doc in uploaded_docs:
        doc_yr = getattr(doc, "academic_year", None)
        if not doc_yr and hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
            doc_yr = doc.metadata.get("academic_year")
        if target_academic_year and doc_yr and doc_yr != target_academic_year:
            continue
        valid_docs_for_sub.append(doc)

    gating_status, multiplier, eg_trace = evaluate_evidence(mandatory_docs, valid_docs_for_sub)
    trace["evidence_gating"] = eg_trace

    # EVIDENCE_GATED_SCORE: must be 0 if pending, rejected, or absent
    gated_score = raw_score * multiplier

    return SubcriterionResult(
        subcriterion_code=sub_code,
        raw_score=min(raw_score, max_score),
        evidence_gated_score=min(gated_score, max_score),
        review_adjusted_score=None,
        final_score=min(gated_score, max_score) if gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED else None,
        max_score=max_score,
        resolution_status=res_status,
        gating_status=gating_status,
        matched_threshold={"operator": matched_op, "score": raw_score},
        trace=trace,
    )


# --- INDIVIDUAL COLLEGE EVALUATORS ---

def eval_c1(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C1"]
    sub_in = param_input.subcriteria_inputs.get("C1.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    pct, pct_trace, valid = calculate_percentage(
        raw_inputs.get("achieved_targets_2024_25", 0),
        raw_inputs.get("fixed_targets_2024_25", 0),
        metric_label="C1.1 IDP 2024-25 Targets %"
    )
    sub_res = _evaluate_standard_college_subcriterion(
        p_def, "C1.1", sub_in, pct if valid else 0.0, validator, context, target_academic_year="2024-25"
    )
    sub_res.trace["percentage_trace"] = pct_trace

    return ParameterResult(
        parameter_code="C1",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"C1.1": sub_res},
    )


def eval_c2(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C2"]
    sub_in = param_input.subcriteria_inputs.get("C2.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    pct, pct_trace, valid = calculate_percentage(
        raw_inputs.get("students_completed", 0),
        raw_inputs.get("eligible_students", 0),
        metric_label="C2.1 Apprenticeship/Internship %"
    )
    sub_res = _evaluate_standard_college_subcriterion(
        p_def, "C2.1", sub_in, pct if valid else 0.0, validator, context
    )
    sub_res.trace["percentage_trace"] = pct_trace

    return ParameterResult(
        parameter_code="C2",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"C2.1": sub_res},
    )


def eval_c3(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C3"]
    sub_in = param_input.subcriteria_inputs.get("C3.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    pct, pct_trace, valid = calculate_percentage(
        raw_inputs.get("abc_registered_students", 0),
        raw_inputs.get("total_enrolled_students", 0),
        metric_label="C3.1 ABC Registration %"
    )
    sub_res = _evaluate_standard_college_subcriterion(
        p_def, "C3.1", sub_in, pct if valid else 0.0, validator, context
    )
    sub_res.trace["percentage_trace"] = pct_trace

    return ParameterResult(
        parameter_code="C3",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"C3.1": sub_res},
    )


def eval_c4(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C4"]
    in_a = param_input.subcriteria_inputs.get("C4.A")
    raw_heis = in_a.raw_inputs.get("heis_mentored", 0) if in_a else param_input.raw_inputs.get("heis_mentored", 0)
    score_heis = min(float(raw_heis), 2.0)
    res_a = _evaluate_standard_college_subcriterion(p_def, "C4.A", in_a, score_heis, validator, context)

    in_b = param_input.subcriteria_inputs.get("C4.B")
    raw_sch = in_b.raw_inputs.get("schools_mentored", 0) if in_b else param_input.raw_inputs.get("schools_mentored", 0)
    score_sch = 2.0 if raw_sch >= 5 else 0.0
    res_b = _evaluate_standard_college_subcriterion(p_def, "C4.B", in_b, score_sch, validator, context)

    raw_tot = min(res_a.raw_score + res_b.raw_score, p_def["max_marks"])
    gated_tot = min(res_a.evidence_gated_score + res_b.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_a.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_b.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="C4",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"C4.A": res_a, "C4.B": res_b},
    )


def eval_c5(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C5"]
    sub_in = param_input.subcriteria_inputs.get("C5.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    # C5 permits >100% under supernumerary order
    pct, pct_trace, valid = calculate_percentage(
        raw_inputs.get("admitted_students", 0),
        raw_inputs.get("sanctioned_intake", 0),
        allow_over_enrollment=True,
        metric_label="C5.1 Sanctioned Seat Enrollment %"
    )
    sub_res = _evaluate_standard_college_subcriterion(
        p_def, "C5.1", sub_in, pct if valid else 0.0, validator, context
    )
    sub_res.trace["percentage_trace"] = pct_trace

    is_unresolved = sub_res.resolution_status == ResolutionStatus.BOUNDARY_UNRESOLVED

    return ParameterResult(
        parameter_code="C5",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=None if is_unresolved else sub_res.final_score,
        resolution_status=ResolutionStatus.BOUNDARY_UNRESOLVED if is_unresolved else ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"C5.1": sub_res},
        trace={"boundary_unresolved": is_unresolved},
    )


def eval_c6(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C6"]
    sub_in = param_input.subcriteria_inputs.get("C6.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    pct, pct_trace, valid = calculate_percentage(
        raw_inputs.get("certified_students", 0),
        raw_inputs.get("total_enrolled_students", 0),
        metric_label="C6.1 NSQF/VAC Certified %"
    )
    sub_res = _evaluate_standard_college_subcriterion(
        p_def, "C6.1", sub_in, pct if valid else 0.0, validator, context
    )
    sub_res.trace["percentage_trace"] = pct_trace

    return ParameterResult(
        parameter_code="C6",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"C6.1": sub_res},
    )


def eval_c7(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C7"]
    sub_in = param_input.subcriteria_inputs.get("C7.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    pct, pct_trace, valid = calculate_percentage(
        raw_inputs.get("sedg_bridge_students", 0),
        raw_inputs.get("total_sedg_students", 0),
        metric_label="C7.1 SEDG Bridge Course %"
    )
    # Tiers top out at 3 marks in source text, while max is declared as 6 marks!
    sub_res = _evaluate_standard_college_subcriterion(
        p_def, "C7.1", sub_in, pct if valid else 0.0, validator, context
    )
    sub_res.trace["percentage_trace"] = pct_trace

    return ParameterResult(
        parameter_code="C7",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=None,  # Blocked by C7 unresolved contradiction (-3 marks deficit)
        resolution_status=ResolutionStatus.UNRESOLVED_RULE,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"C7.1": sub_res},
        trace={"unresolved_reason": p_def["unresolved_reason"]},
    )


def eval_c8(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C8"]
    sub_in = param_input.subcriteria_inputs.get("C8.1")
    # Single unquantified line in source: UNRESOLVED_RULE
    sub_res = SubcriterionResult(
        subcriterion_code="C8.1",
        raw_score=0.0,
        evidence_gated_score=0.0,
        review_adjusted_score=None,
        final_score=None,
        max_score=2.0,
        resolution_status=ResolutionStatus.UNRESOLVED_RULE,
        gating_status=GatingStatus.PROVISIONAL_PENDING_VERIFICATION,
        trace={"unresolved_reason": p_def["unresolved_reason"]},
    )

    return ParameterResult(
        parameter_code="C8",
        max_marks=p_def["max_marks"],
        raw_score=0.0,
        evidence_gated_score=0.0,
        review_adjusted_score=None,
        final_score=None,  # Blocked by C8 unresolved line
        resolution_status=ResolutionStatus.UNRESOLVED_RULE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"C8.1": sub_res},
        trace={"unresolved_reason": p_def["unresolved_reason"]},
    )


def eval_c9(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C9"]
    in_1 = param_input.subcriteria_inputs.get("C9.I")
    raw_1 = in_1.raw_inputs if in_1 else param_input.raw_inputs.get("C9.I", {})
    pct_1, trace_1, val_1 = calculate_percentage(
        raw_1.get("participating_students", 0),
        raw_1.get("eligible_students", 0),
        metric_label="C9.I Fair Participation %"
    )
    res_1 = _evaluate_standard_college_subcriterion(p_def, "C9.I", in_1, pct_1 if val_1 else 0.0, validator, context)
    res_1.trace["percentage_trace"] = trace_1

    in_2 = param_input.subcriteria_inputs.get("C9.II")
    raw_2 = in_2.raw_inputs if in_2 else param_input.raw_inputs.get("C9.II", {})
    pct_2, trace_2, val_2 = calculate_percentage(
        raw_2.get("placed_students", 0),
        raw_1.get("participating_students", 0),  # denominator is participating students
        metric_label="C9.II Placement Conversion %"
    )
    res_2 = _evaluate_standard_college_subcriterion(p_def, "C9.II", in_2, pct_2 if val_2 else 0.0, validator, context)
    res_2.trace["percentage_trace"] = trace_2

    raw_tot = min(res_1.raw_score + res_2.raw_score, p_def["max_marks"])
    gated_tot = min(res_1.evidence_gated_score + res_2.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_1.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_2.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="C9",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"C9.I": res_1, "C9.II": res_2},
    )


def eval_c10(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C10"]
    sub_in = param_input.subcriteria_inputs.get("C10.1")
    count_val = sub_in.raw_inputs.get("active_mous_count", 0) if sub_in else param_input.raw_inputs.get("active_mous_count", 0)
    sub_res = _evaluate_standard_college_subcriterion(p_def, "C10.1", sub_in, count_val, validator, context)

    return ParameterResult(
        parameter_code="C10",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"C10.1": sub_res},
    )


def eval_c11(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C11"]
    in_1 = param_input.subcriteria_inputs.get("C11.I")
    cnt_val = in_1.raw_inputs.get("ventures_count", 0) if in_1 else param_input.raw_inputs.get("ventures_count", 0)
    res_1 = _evaluate_standard_college_subcriterion(p_def, "C11.I", in_1, cnt_val, validator, context)

    in_2a = param_input.subcriteria_inputs.get("C11.II.a")
    cell_val = in_2a.raw_inputs.get("cell_functional", False) if in_2a else param_input.raw_inputs.get("cell_functional", False)
    res_2a = _evaluate_standard_college_subcriterion(p_def, "C11.II.a", in_2a, cell_val, validator, context)

    in_2b = param_input.subcriteria_inputs.get("C11.II.b")
    raw_2b = in_2b.raw_inputs if in_2b else param_input.raw_inputs.get("C11.II.b", {})
    pct_2b, trace_2b, val_2b = calculate_percentage(
        raw_2b.get("monetized_count", 0),
        cnt_val,
        metric_label="C11.II.b Venture Monetization %"
    )
    res_2b = _evaluate_standard_college_subcriterion(p_def, "C11.II.b", in_2b, pct_2b if val_2b else 0.0, validator, context)
    res_2b.trace["percentage_trace"] = trace_2b

    raw_tot = min(res_1.raw_score + res_2a.raw_score + res_2b.raw_score, p_def["max_marks"])
    gated_tot = min(res_1.evidence_gated_score + res_2a.evidence_gated_score + res_2b.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_1.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_2a.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and
                    res_2b.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="C11",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"C11.I": res_1, "C11.II.a": res_2a, "C11.II.b": res_2b},
    )


def eval_c12(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C12"]
    sub_results = {}
    for code in ["C12.1", "C12.2", "C12.3", "C12.4", "C12.5"]:
        sub_in = param_input.subcriteria_inputs.get(code)
        val = sub_in.raw_inputs.get("verified", False) if sub_in else param_input.raw_inputs.get(code, False)
        sub_results[code] = _evaluate_standard_college_subcriterion(p_def, code, sub_in, val, validator, context)

    raw_tot = min(sum(r.raw_score for r in sub_results.values()), p_def["max_marks"])
    gated_tot = min(sum(r.evidence_gated_score for r in sub_results.values()), p_def["max_marks"])
    all_verified = all(r.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED for r in sub_results.values())

    return ParameterResult(
        parameter_code="C12",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.FIXED_ITEM_SUM,
        subcriteria_results=sub_results,
    )


def eval_c13(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C13"]
    sub_in = param_input.subcriteria_inputs.get("C13.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    pct, pct_trace, valid = calculate_percentage(
        raw_inputs.get("trained_faculty", 0),
        raw_inputs.get("total_fulltime_faculty", 0),
        metric_label="C13.1 Faculty FDP Trained %"
    )
    sub_res = _evaluate_standard_college_subcriterion(
        p_def, "C13.1", sub_in, pct if valid else 0.0, validator, context
    )
    sub_res.trace["percentage_trace"] = pct_trace

    return ParameterResult(
        parameter_code="C13",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"C13.1": sub_res},
    )


def eval_c14(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C14"]
    in_a = param_input.subcriteria_inputs.get("C14.A")
    items_cnt = in_a.raw_inputs.get("content_items", 0) if in_a else param_input.raw_inputs.get("content_items", 0)
    score_a = min(float(items_cnt) * 0.5, 2.0)
    res_a = _evaluate_standard_college_subcriterion(p_def, "C14.A", in_a, score_a, validator, context)

    in_b = param_input.subcriteria_inputs.get("C14.B")
    act_cnt = in_b.raw_inputs.get("iks_activities", 0) if in_b else param_input.raw_inputs.get("iks_activities", 0)
    score_b = 2.0 if act_cnt >= 5 else 0.0
    res_b = _evaluate_standard_college_subcriterion(p_def, "C14.B", in_b, score_b, validator, context)

    raw_tot = min(res_a.raw_score + res_b.raw_score, p_def["max_marks"])
    gated_tot = min(res_a.evidence_gated_score + res_b.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_a.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_b.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="C14",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"C14.A": res_a, "C14.B": res_b},
    )


def eval_c15(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C15"]
    sub_results = {}
    for code in ["C15.1", "C15.2", "C15.3", "C15.4", "C15.5", "C15.6"]:
        sub_in = param_input.subcriteria_inputs.get(code)
        val = sub_in.raw_inputs.get("verified", False) if sub_in else param_input.raw_inputs.get(code, False)
        sub_results[code] = _evaluate_standard_college_subcriterion(p_def, code, sub_in, val, validator, context)

    raw_tot = min(sum(r.raw_score for r in sub_results.values()), p_def["max_marks"])
    gated_tot = min(sum(r.evidence_gated_score for r in sub_results.values()), p_def["max_marks"])
    all_verified = all(r.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED for r in sub_results.values())

    return ParameterResult(
        parameter_code="C15",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.FIXED_ITEM_SUM,
        subcriteria_results=sub_results,
    )


def eval_c16(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C16"]
    sub_results = {}
    for code in ["C16.1", "C16.2", "C16.3", "C16.4", "C16.5"]:
        sub_in = param_input.subcriteria_inputs.get(code)
        val = sub_in.raw_inputs.get("verified", False) if sub_in else param_input.raw_inputs.get(code, False)
        sub_results[code] = _evaluate_standard_college_subcriterion(p_def, code, sub_in, val, validator, context)

    # C16 has 5 items @ 1 mark each totaling 5 marks against declared max 4: UNRESOLVED_RULE
    raw_tot = sum(r.raw_score for r in sub_results.values())
    gated_tot = sum(r.evidence_gated_score for r in sub_results.values())

    return ParameterResult(
        parameter_code="C16",
        max_marks=p_def["max_marks"],
        raw_score=min(raw_tot, 4.0),
        evidence_gated_score=min(gated_tot, 4.0),
        review_adjusted_score=None,
        final_score=None,  # Blocked by C16 unresolved contradiction (5 items vs max 4)
        resolution_status=ResolutionStatus.UNRESOLVED_RULE,
        aggregation_strategy=EvaluationType.FIXED_ITEM_SUM,
        subcriteria_results=sub_results,
        trace={"unresolved_reason": p_def["unresolved_reason"]},
    )


def eval_c17(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C17"]
    sub_in = param_input.subcriteria_inputs.get("C17.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    pct, pct_trace, valid = calculate_percentage(
        raw_inputs.get("participating_students", 0),
        raw_inputs.get("total_enrolled_students", 0),
        metric_label="C17.1 Outreach Participation %"
    )
    sub_res = _evaluate_standard_college_subcriterion(
        p_def, "C17.1", sub_in, pct if valid else 0.0, validator, context
    )
    sub_res.trace["percentage_trace"] = pct_trace

    return ParameterResult(
        parameter_code="C17",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"C17.1": sub_res},
    )


def eval_c18(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C18"]
    in_1 = param_input.subcriteria_inputs.get("C18.1")
    act_cnt = in_1.raw_inputs.get("sdg_activities", 0) if in_1 else param_input.raw_inputs.get("sdg_activities", 0)
    score_1 = 2.0 if act_cnt >= 5 else 0.0
    res_1 = _evaluate_standard_college_subcriterion(p_def, "C18.1", in_1, score_1, validator, context)

    in_2 = param_input.subcriteria_inputs.get("C18.2")
    val_2 = in_2.raw_inputs.get("verified", False) if in_2 else param_input.raw_inputs.get("C18.2", False)
    res_2 = _evaluate_standard_college_subcriterion(p_def, "C18.2", in_2, val_2, validator, context)

    in_3 = param_input.subcriteria_inputs.get("C18.3")
    val_3 = in_3.raw_inputs.get("verified", False) if in_3 else param_input.raw_inputs.get("C18.3", False)
    res_3 = _evaluate_standard_college_subcriterion(p_def, "C18.3", in_3, val_3, validator, context)

    in_4 = param_input.subcriteria_inputs.get("C18.4")
    val_4 = in_4.raw_inputs.get("verified", False) if in_4 else param_input.raw_inputs.get("C18.4", False)
    res_4 = _evaluate_standard_college_subcriterion(p_def, "C18.4", in_4, val_4, validator, context)

    raw_tot = min(res_1.raw_score + res_2.raw_score + res_3.raw_score + res_4.raw_score, p_def["max_marks"])
    gated_tot = min(res_1.evidence_gated_score + res_2.evidence_gated_score + res_3.evidence_gated_score + res_4.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_1.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_2.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and
                    res_3.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and
                    res_4.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="C18",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"C18.1": res_1, "C18.2": res_2, "C18.3": res_3, "C18.4": res_4},
    )


def eval_c19(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C19"]
    # C19.I: Patents filed (1 mark per 2, max 2)
    in_1 = param_input.subcriteria_inputs.get("C19.I")
    cnt_filed = in_1.raw_inputs.get("patents_filed", 0) if in_1 else param_input.raw_inputs.get("patents_filed", 0)
    res_1 = _evaluate_standard_college_subcriterion(p_def, "C19.I", in_1, cnt_filed, validator, context, is_count=True)

    # C19.II: Patents granted (1 mark for each patent granted, max 2)
    in_2 = param_input.subcriteria_inputs.get("C19.II")
    cnt_granted = in_2.raw_inputs.get("patents_granted", 0) if in_2 else param_input.raw_inputs.get("patents_granted", 0)
    res_2 = _evaluate_standard_college_subcriterion(p_def, "C19.II", in_2, cnt_granted, validator, context, is_count=True)

    # C19.III: Scopus Index -> UNRESOLVED_RULE!
    in_3 = param_input.subcriteria_inputs.get("C19.III")
    res_3 = _evaluate_standard_college_subcriterion(p_def, "C19.III", in_3, 0.0, validator, context)

    raw_tot = min(res_1.raw_score + res_2.raw_score, p_def["max_marks"])
    gated_tot = min(res_1.evidence_gated_score + res_2.evidence_gated_score, p_def["max_marks"])

    return ParameterResult(
        parameter_code="C19",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=None,  # Blocked by C19.III Scopus Index
        resolution_status=ResolutionStatus.UNRESOLVED_RULE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"C19.I": res_1, "C19.II": res_2, "C19.III": res_3},
        trace={"unresolved_subcriterion": "C19.III"},
    )


def _normalize_and_evaluate_naac(
    in_1: Optional[SubcriterionInput],
    param_input: ParameterInput,
    sub_def: Dict[str, Any]
) -> Tuple[float, ResolutionStatus, Dict[str, Any]]:
    """
    Deterministically normalizes and evaluates NAAC grade string and numeric metadata inputs for C20.1.
    Traps contradictions, malformed inputs, and preserves certification safety.
    """
    raw_dict = {}
    if in_1 and hasattr(in_1, "raw_inputs") and in_1.raw_inputs:
        raw_dict.update(in_1.raw_inputs)
    if hasattr(param_input, "raw_inputs") and param_input.raw_inputs:
        for k, v in param_input.raw_inputs.items():
            if k not in raw_dict:
                raw_dict[k] = v

    # 1. Extract raw grade string
    raw_grade = None
    for k in ["naac_grade", "grade", "accreditation_grade"]:
        if k in raw_dict and raw_dict[k] is not None:
            raw_grade = raw_dict[k]
            break

    # 2. Extract raw numeric metadata
    raw_numeric = None
    for k in ["naac_score", "score", "naac_points", "points", "numeric_score"]:
        if k in raw_dict and raw_dict[k] is not None:
            raw_numeric = raw_dict[k]
            break

    tier_1 = sub_def.get("tier_1_grades", ["A++", "A+", "A", "B++"])
    tier_2 = sub_def.get("tier_2_grades", ["B+", "B"])
    unaccredited = ["C", "D", "UNACCREDITED", "NONE", "NO", "NOT_ACCREDITED"]

    grade_str: Optional[str] = None
    grade_score: Optional[float] = None
    grade_malformed = False

    if raw_grade is not None:
        if isinstance(raw_grade, str):
            g_clean = raw_grade.strip().upper()
            if g_clean:
                grade_str = g_clean
                if grade_str in tier_1:
                    grade_score = 2.0
                elif grade_str in tier_2:
                    grade_score = 1.0
                elif grade_str in unaccredited:
                    grade_score = 0.0
                else:
                    grade_malformed = True
        else:
            grade_malformed = True

    num_score: Optional[float] = None
    num_malformed = False

    if raw_numeric is not None:
        if isinstance(raw_numeric, bool):
            num_malformed = True
        else:
            try:
                val_f = float(raw_numeric)
                if val_f in [2.0, 1.0, 0.0]:
                    num_score = val_f
                else:
                    num_malformed = True
            except (ValueError, TypeError):
                num_malformed = True

    # Case A: Neither provided -> Missing NAAC value
    if raw_grade is None and raw_numeric is None:
        return 0.0, ResolutionStatus.CALCULABLE, {
            "status": "MISSING_VALUE",
            "score": 0.0,
            "reason": "No NAAC grade string or numeric metadata supplied.",
        }

    # Case B: Malformed input detected
    if grade_malformed or num_malformed:
        err_parts = []
        if grade_malformed:
            err_parts.append(f"malformed grade string '{raw_grade}'")
        if num_malformed:
            err_parts.append(f"malformed numeric metadata '{raw_numeric}'")
        return 0.0, ResolutionStatus.INVALID_INPUT, {
            "status": "MALFORMED_INPUT",
            "score": 0.0,
            "reason": f"Unsupported or invalid NAAC representation: {', '.join(err_parts)}",
        }

    # Case C: Only grade string provided
    if grade_score is not None and num_score is None:
        return grade_score, ResolutionStatus.CALCULABLE, {
            "status": "VALID_STRING",
            "grade_string": grade_str,
            "score": grade_score,
        }

    # Case D: Only numeric metadata provided
    if num_score is not None and grade_score is None:
        return num_score, ResolutionStatus.CALCULABLE, {
            "status": "VALID_NUMERIC",
            "numeric_score": num_score,
            "score": num_score,
        }

    # Case E: Both string grade and numeric metadata provided
    if grade_score is not None and num_score is not None:
        if grade_score == num_score:
            return grade_score, ResolutionStatus.CALCULABLE, {
                "status": "EQUIVALENT",
                "grade_string": grade_str,
                "numeric_score": num_score,
                "score": grade_score,
            }
        else:
            contradiction_msg = (
                f"Contradictory NAAC representations: grade string '{grade_str}' maps to {grade_score} marks, "
                f"but numeric metadata specifies {num_score} marks."
            )
            return 0.0, ResolutionStatus.INVALID_INPUT, {
                "status": "CONTRADICTORY",
                "grade_string": grade_str,
                "grade_score": grade_score,
                "numeric_score": num_score,
                "score": 0.0,
                "reason": contradiction_msg,
            }

    return 0.0, ResolutionStatus.CALCULABLE, {"status": "UNRESOLVED", "score": 0.0}


def eval_c20(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C20"]
    c20_1_def = p_def["subcriteria"]["C20.1"]
    in_1 = param_input.subcriteria_inputs.get("C20.1")

    score_naac, naac_status, naac_trace = _normalize_and_evaluate_naac(in_1, param_input, c20_1_def)

    if naac_status == ResolutionStatus.INVALID_INPUT:
        res_1 = SubcriterionResult(
            subcriterion_code="C20.1",
            raw_score=0.0,
            evidence_gated_score=0.0,
            review_adjusted_score=None,
            final_score=None,
            max_score=c20_1_def["max_score"],
            resolution_status=ResolutionStatus.INVALID_INPUT,
            gating_status=GatingStatus.PROVISIONAL_PENDING_VERIFICATION,
            trace={
                "subcriterion_code": "C20.1",
                "naac_evaluation": naac_trace,
                "validation_error": naac_trace.get("reason", "Invalid NAAC input"),
            },
        )
    else:
        res_1 = _evaluate_standard_college_subcriterion(p_def, "C20.1", in_1, score_naac, validator, context)
        res_1.trace["naac_evaluation"] = naac_trace

    in_2 = param_input.subcriteria_inputs.get("C20.2")
    val_2 = in_2.raw_inputs.get("verified", False) if in_2 else param_input.raw_inputs.get("C20.2", False)
    res_2 = _evaluate_standard_college_subcriterion(p_def, "C20.2", in_2, val_2, validator, context)

    in_3 = param_input.subcriteria_inputs.get("C20.3")
    val_3 = in_3.raw_inputs.get("verified", False) if in_3 else param_input.raw_inputs.get("C20.3", False)
    res_3 = _evaluate_standard_college_subcriterion(p_def, "C20.3", in_3, val_3, validator, context)

    in_4 = param_input.subcriteria_inputs.get("C20.4")
    val_4 = in_4.raw_inputs.get("verified", False) if in_4 else param_input.raw_inputs.get("C20.4", False)
    res_4 = _evaluate_standard_college_subcriterion(p_def, "C20.4", in_4, val_4, validator, context)

    raw_tot = min(res_1.raw_score + res_2.raw_score + res_3.raw_score + res_4.raw_score, p_def["max_marks"])
    gated_tot = min(res_1.evidence_gated_score + res_2.evidence_gated_score + res_3.evidence_gated_score + res_4.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_1.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_2.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and
                    res_3.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and
                    res_4.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    param_resolution_status = (
        ResolutionStatus.INVALID_INPUT
        if res_1.resolution_status == ResolutionStatus.INVALID_INPUT
        else ResolutionStatus.CALCULABLE
    )

    p_trace: Dict[str, Any] = {"evaluated_subcriteria": ["C20.1", "C20.2", "C20.3", "C20.4"]}
    if res_1.resolution_status == ResolutionStatus.INVALID_INPUT:
        p_trace["naac_contradiction"] = res_1.trace.get("validation_error")

    return ParameterResult(
        parameter_code="C20",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if (all_verified and param_resolution_status == ResolutionStatus.CALCULABLE) else None,
        resolution_status=param_resolution_status,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"C20.1": res_1, "C20.2": res_2, "C20.3": res_3, "C20.4": res_4},
        trace=p_trace,
    )


def eval_c21(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C21"]
    in_1 = param_input.subcriteria_inputs.get("C21.1")
    act_cnt = in_1.raw_inputs.get("activities_count", 0) if in_1 else param_input.raw_inputs.get("activities_count", 0)
    res_1 = _evaluate_standard_college_subcriterion(p_def, "C21.1", in_1, act_cnt, validator, context)

    in_2 = param_input.subcriteria_inputs.get("C21.2")
    val_2 = in_2.raw_inputs.get("verified", False) if in_2 else param_input.raw_inputs.get("C21.2", False)
    res_2 = _evaluate_standard_college_subcriterion(p_def, "C21.2", in_2, val_2, validator, context)

    # C21 items sum to 3 marks against declared maximum of 4 marks (SOURCE_INCONSISTENCY)
    items_sum_raw = res_1.raw_score + res_2.raw_score
    items_sum_gated = res_1.evidence_gated_score + res_2.evidence_gated_score

    return ParameterResult(
        parameter_code="C21",
        max_marks=p_def["max_marks"],
        raw_score=min(items_sum_raw, p_def["max_marks"]),
        evidence_gated_score=min(items_sum_gated, p_def["max_marks"]),
        review_adjusted_score=None,
        final_score=None,  # Blocked by source arithmetic inconsistency
        resolution_status=ResolutionStatus.SOURCE_INCONSISTENCY,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"C21.1": res_1, "C21.2": res_2},
        trace={"discrepancy": "Criteria sum to 3.0 vs Max 4.0; final certification blocked"},
    )


def eval_c22(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = COLLEGE_PARAMETERS["C22"]
    in_1 = param_input.subcriteria_inputs.get("C22.1")
    val_1 = in_1.raw_inputs.get("verified", False) if in_1 else param_input.raw_inputs.get("C22.1", False)
    res_1 = _evaluate_standard_college_subcriterion(p_def, "C22.1", in_1, val_1, validator, context)

    in_2 = param_input.subcriteria_inputs.get("C22.2")
    val_2 = in_2.raw_inputs.get("verified", False) if in_2 else param_input.raw_inputs.get("C22.2", False)
    res_2 = _evaluate_standard_college_subcriterion(p_def, "C22.2", in_2, val_2, validator, context)

    raw_tot = min(res_1.raw_score + res_2.raw_score, p_def["max_marks"])
    gated_tot = min(res_1.evidence_gated_score + res_2.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_1.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_2.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="C22",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"C22.1": res_1, "C22.2": res_2},
    )


COLLEGE_EVALUATORS: Dict[str, Callable[[ParameterInput, AssessmentContext, DoubleCountingValidator], ParameterResult]] = {
    "C1": eval_c1,
    "C2": eval_c2,
    "C3": eval_c3,
    "C4": eval_c4,
    "C5": eval_c5,
    "C6": eval_c6,
    "C7": eval_c7,
    "C8": eval_c8,
    "C9": eval_c9,
    "C10": eval_c10,
    "C11": eval_c11,
    "C12": eval_c12,
    "C13": eval_c13,
    "C14": eval_c14,
    "C15": eval_c15,
    "C16": eval_c16,
    "C17": eval_c17,
    "C18": eval_c18,
    "C19": eval_c19,
    "C20": eval_c20,
    "C21": eval_c21,
    "C22": eval_c22,
}
