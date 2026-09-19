"""
NEP Excellence Awards 2026 - University Parameter Evaluators (U1–U20)
Deterministic rule evaluators anchored strictly to authoritative specifications.
"""
from typing import Any, Callable, Dict, List, Optional

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
from .definitions import UNIVERSITY_PARAMETERS

COUNT_FIELDS = {
    "programmes_count", "startups_count", "activities_count", "tools_count",
    "patents_filed", "patents_granted", "heis_mentored", "schools_mentored",
    "sdg_activities", "initiatives_count", "events_count"
}


def _evaluate_standard_subcriterion(
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
        # Boolean or direct scalar item
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


# --- INDIVIDUAL UNIVERSITY EVALUATORS ---

def eval_u1(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U1"]
    sub_in = param_input.subcriteria_inputs.get("U1.1")
    count_val = sub_in.raw_inputs.get("programmes_count", 0) if sub_in else param_input.raw_inputs.get("programmes_count", 0)
    sub_res = _evaluate_standard_subcriterion(p_def, "U1.1", sub_in, count_val, validator, context, is_count=True)
    
    return ParameterResult(
        parameter_code="U1",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"U1.1": sub_res},
        trace={"evaluated_subcriteria": ["U1.1"]},
    )


def eval_u2(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U2"]
    sub_in = param_input.subcriteria_inputs.get("U2.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    num = raw_inputs.get("indian_lang_programmes", 0)
    den = raw_inputs.get("total_degree_programmes", 0)

    pct, pct_trace, valid = calculate_percentage(num, den, metric_label="Indian Language Programmes %")
    if not valid:
        pct = 0.0

    sub_res = _evaluate_standard_subcriterion(p_def, "U2.1", sub_in, pct, validator, context)
    sub_res.trace["percentage_calculation"] = pct_trace

    return ParameterResult(
        parameter_code="U2",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"U2.1": sub_res},
        trace={"percentage_trace": pct_trace},
    )


def eval_u3(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U3"]
    sub_in = param_input.subcriteria_inputs.get("U3.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    num = raw_inputs.get("iks_programmes", 0)
    den = raw_inputs.get("total_degree_programmes", 0)

    pct, pct_trace, valid = calculate_percentage(num, den, metric_label="IKS Programmes %")
    if not valid:
        pct = 0.0

    sub_res = _evaluate_standard_subcriterion(p_def, "U3.1", sub_in, pct, validator, context)
    sub_res.trace["percentage_calculation"] = pct_trace

    return ParameterResult(
        parameter_code="U3",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"U3.1": sub_res},
        trace={"percentage_trace": pct_trace},
    )


def eval_u4(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U4"]
    # Support canonical (U4.A, U4.B) and common aliases (U4.1, U4.2)
    in_a = param_input.subcriteria_inputs.get("U4.A") or param_input.subcriteria_inputs.get("U4.1")
    in_b = param_input.subcriteria_inputs.get("U4.B") or param_input.subcriteria_inputs.get("U4.2")

    # If institutional IDP document is passed at parameter level, share it
    param_idp_docs = [d for d in param_input.evidence_docs if d.document_type in ("EVID_U4_IDP", "EVID_U4_TARGET_SHEET")]

    # Part A (2024-25)
    raw_a = in_a.raw_inputs if in_a else (param_input.raw_inputs.get("U4.A") or param_input.raw_inputs.get("U4.1", {}))
    num_a = raw_a.get("achieved_targets_2024_25", 0)
    den_a = raw_a.get("total_targets_2024_25", 0)
    pct_a, trace_a, val_a = calculate_percentage(
        num_a, den_a, metric_label="U4.A IDP 2024-25 %"
    )

    if in_a and param_idp_docs:
        existing_doc_ids = {d.document_id for d in in_a.evidence_docs}
        combined_docs = list(in_a.evidence_docs) + [d for d in param_idp_docs if d.document_id not in existing_doc_ids]
        sub_in_a = SubcriterionInput(
            subcriterion_code=in_a.subcriterion_code,
            raw_inputs=in_a.raw_inputs,
            evidence_docs=combined_docs,
            entities=in_a.entities,
            activity_date=in_a.activity_date,
        )
    elif not in_a and param_idp_docs:
        sub_in_a = SubcriterionInput(
            subcriterion_code="U4.A",
            raw_inputs=raw_a,
            evidence_docs=param_idp_docs,
        )
    else:
        sub_in_a = in_a

    res_a = _evaluate_standard_subcriterion(p_def, "U4.A", sub_in_a, pct_a if val_a else 0.0, validator, context, target_academic_year="2024-25")
    res_a.trace["percentage_trace"] = trace_a

    # Part B (2025-26)
    raw_b = in_b.raw_inputs if in_b else (param_input.raw_inputs.get("U4.B") or param_input.raw_inputs.get("U4.2", {}))
    num_b = raw_b.get("achieved_targets_2025_26", 0)
    den_b = raw_b.get("total_targets_2025_26", 0)
    pct_b, trace_b, val_b = calculate_percentage(
        num_b, den_b, metric_label="U4.B IDP 2025-26 %"
    )

    if in_b and param_idp_docs:
        existing_doc_ids = {d.document_id for d in in_b.evidence_docs}
        combined_docs = list(in_b.evidence_docs) + [d for d in param_idp_docs if d.document_id not in existing_doc_ids]
        sub_in_b = SubcriterionInput(
            subcriterion_code=in_b.subcriterion_code,
            raw_inputs=in_b.raw_inputs,
            evidence_docs=combined_docs,
            entities=in_b.entities,
            activity_date=in_b.activity_date,
        )
    elif not in_b and param_idp_docs:
        sub_in_b = SubcriterionInput(
            subcriterion_code="U4.B",
            raw_inputs=raw_b,
            evidence_docs=param_idp_docs,
        )
    else:
        sub_in_b = in_b

    res_b = _evaluate_standard_subcriterion(p_def, "U4.B", sub_in_b, pct_b if val_b else 0.0, validator, context, target_academic_year="2025-26")
    res_b.trace["percentage_trace"] = trace_b

    raw_tot = min(res_a.raw_score + res_b.raw_score, p_def["max_marks"])
    gated_tot = min(res_a.evidence_gated_score + res_b.evidence_gated_score, p_def["max_marks"])

    # Missing evidence on one component must not zero out the other verified component
    has_pending = (res_a.gating_status == GatingStatus.PROVISIONAL_PENDING_VERIFICATION or 
                   res_b.gating_status == GatingStatus.PROVISIONAL_PENDING_VERIFICATION)
    final_score = gated_tot if not has_pending else None

    trace = {
        "sum_parts": [res_a.raw_score, res_b.raw_score],
        "component_evidence_status": {
            "U4.A": res_a.gating_status.value,
            "U4.B": res_b.gating_status.value,
            "U4.1": res_a.gating_status.value,
            "U4.2": res_b.gating_status.value,
        },
        "component_gated_scores": {
            "U4.A": res_a.evidence_gated_score,
            "U4.B": res_b.evidence_gated_score,
            "U4.1": res_a.evidence_gated_score,
            "U4.2": res_b.evidence_gated_score,
        },
    }

    return ParameterResult(
        parameter_code="U4",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=final_score,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"U4.A": res_a, "U4.B": res_b, "U4.1": res_a, "U4.2": res_b},
        trace=trace,
    )


def eval_u5(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U5"]
    in_a = param_input.subcriteria_inputs.get("U5.A")
    raw_a = in_a.raw_inputs if in_a else param_input.raw_inputs.get("U5.A", {})
    pct_a, trace_a, val_a = calculate_percentage(
        raw_a.get("eligible_students", 0),
        raw_a.get("total_final_year_students", 0),
        metric_label="U5.A Eligibility %"
    )
    res_a = _evaluate_standard_subcriterion(p_def, "U5.A", in_a, pct_a if val_a else 0.0, validator, context)
    res_a.trace["percentage_trace"] = trace_a

    in_b = param_input.subcriteria_inputs.get("U5.B")
    raw_b = in_b.raw_inputs if in_b else param_input.raw_inputs.get("U5.B", {})
    pct_b, trace_b, val_b = calculate_percentage(
        raw_b.get("placed_students", 0),
        raw_b.get("eligible_students", 0),
        metric_label="U5.B Conversion %"
    )
    res_b = _evaluate_standard_subcriterion(p_def, "U5.B", in_b, pct_b if val_b else 0.0, validator, context)
    res_b.trace["percentage_trace"] = trace_b

    is_unresolved = (res_a.resolution_status == ResolutionStatus.BOUNDARY_UNRESOLVED or 
                     res_b.resolution_status == ResolutionStatus.BOUNDARY_UNRESOLVED)

    raw_tot = min(res_a.raw_score + res_b.raw_score, p_def["max_marks"])
    gated_tot = min(res_a.evidence_gated_score + res_b.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_a.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_b.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="U5",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=None if is_unresolved else (gated_tot if all_verified else None),
        resolution_status=ResolutionStatus.BOUNDARY_UNRESOLVED if is_unresolved else ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"U5.A": res_a, "U5.B": res_b},
        trace={"boundary_unresolved": is_unresolved},
    )


def eval_u6(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U6"]
    in_a = param_input.subcriteria_inputs.get("U6.A")
    ord_val = in_a.raw_inputs.get("ordinance_notified", False) if in_a else param_input.raw_inputs.get("ordinance_notified", False)
    res_a = _evaluate_standard_subcriterion(p_def, "U6.A", in_a, ord_val, validator, context)

    in_b = param_input.subcriteria_inputs.get("U6.B")
    tools_count = in_b.raw_inputs.get("tools_count", 0) if in_b else param_input.raw_inputs.get("tools_count", 0)
    res_b = _evaluate_standard_subcriterion(p_def, "U6.B", in_b, tools_count, validator, context, is_count=True)

    raw_tot = min(res_a.raw_score + res_b.raw_score, p_def["max_marks"])
    gated_tot = min(res_a.evidence_gated_score + res_b.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_a.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_b.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="U6",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"U6.A": res_a, "U6.B": res_b},
    )


def eval_u7(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U7"]
    sub_results = {}
    for code in ["U7.1", "U7.2", "U7.3", "U7.4"]:
        sub_in = param_input.subcriteria_inputs.get(code)
        val = sub_in.raw_inputs.get("verified", False) if sub_in else param_input.raw_inputs.get(code, False)
        sub_results[code] = _evaluate_standard_subcriterion(p_def, code, sub_in, val, validator, context)

    raw_tot = min(sum(r.raw_score for r in sub_results.values()), p_def["max_marks"])
    gated_tot = min(sum(r.evidence_gated_score for r in sub_results.values()), p_def["max_marks"])
    all_verified = all(r.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED for r in sub_results.values())

    return ParameterResult(
        parameter_code="U7",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.FIXED_ITEM_SUM,
        subcriteria_results=sub_results,
    )


def eval_u8(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U8"]
    in_a = param_input.subcriteria_inputs.get("U8.A")
    count_val = in_a.raw_inputs.get("startups_count", 0) if in_a else param_input.raw_inputs.get("startups_count", 0)
    res_a = _evaluate_standard_subcriterion(p_def, "U8.A", in_a, count_val, validator, context, is_count=True)

    in_b = param_input.subcriteria_inputs.get("U8.B")
    raw_b = in_b.raw_inputs if in_b else param_input.raw_inputs.get("U8.B", {})
    pct_b, trace_b, val_b = calculate_percentage(
        raw_b.get("monetized_count", 0),
        count_val,  # denominator is reported startups
        metric_label="U8.B Startup Monetization %"
    )
    res_b = _evaluate_standard_subcriterion(p_def, "U8.B", in_b, pct_b if val_b else 0.0, validator, context)
    res_b.trace["percentage_trace"] = trace_b

    raw_tot = min(res_a.raw_score + res_b.raw_score, p_def["max_marks"])
    gated_tot = min(res_a.evidence_gated_score + res_b.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_a.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_b.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="U8",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.COMPOSITE,
        subcriteria_results={"U8.A": res_a, "U8.B": res_b},
    )


def eval_u9(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U9"]
    in_a = param_input.subcriteria_inputs.get("U9.A")
    raw_a = in_a.raw_inputs if in_a else param_input.raw_inputs.get("U9.A", {})
    pct_a, trace_a, val_a = calculate_percentage(
        raw_a.get("active_mous", 0),
        raw_a.get("total_mous", 0),
        metric_label="U9.A Active Foreign MoUs %"
    )
    res_a = _evaluate_standard_subcriterion(p_def, "U9.A", in_a, pct_a if val_a else 0.0, validator, context)

    in_b = param_input.subcriteria_inputs.get("U9.B")
    act_count = in_b.raw_inputs.get("activities_count", 0) if in_b else param_input.raw_inputs.get("activities_count", 0)
    res_b = _evaluate_standard_subcriterion(p_def, "U9.B", in_b, act_count, validator, context, is_count=True)

    raw_tot = min(res_a.raw_score + res_b.raw_score, p_def["max_marks"])
    gated_tot = min(res_a.evidence_gated_score + res_b.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_a.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_b.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="U9",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.COMPOSITE,
        subcriteria_results={"U9.A": res_a, "U9.B": res_b},
    )


def eval_u10(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U10"]
    sub_results = {}
    for code in ["U10.1", "U10.2", "U10.4"]:
        sub_in = param_input.subcriteria_inputs.get(code)
        val = sub_in.raw_inputs.get("verified", False) if sub_in else param_input.raw_inputs.get(code, False)
        sub_results[code] = _evaluate_standard_subcriterion(p_def, code, sub_in, val, validator, context)

    # U10.3 Alumni Funding
    in_3 = param_input.subcriteria_inputs.get("U10.3")
    funds = in_3.raw_inputs.get("funding_amount", 0.0) if in_3 else param_input.raw_inputs.get("funding_amount", 0.0)
    sub_results["U10.3"] = _evaluate_standard_subcriterion(p_def, "U10.3", in_3, funds, validator, context)

    is_unresolved = sub_results["U10.3"].resolution_status == ResolutionStatus.BOUNDARY_UNRESOLVED
    raw_tot = min(sum(r.raw_score for r in sub_results.values()), p_def["max_marks"])
    gated_tot = min(sum(r.evidence_gated_score for r in sub_results.values()), p_def["max_marks"])
    all_verified = all(r.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED for r in sub_results.values())

    return ParameterResult(
        parameter_code="U10",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=None if is_unresolved else (gated_tot if all_verified else None),
        resolution_status=ResolutionStatus.BOUNDARY_UNRESOLVED if is_unresolved else ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results=sub_results,
    )


def eval_u11(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U11"]
    sub_results = {}
    for code in ["U11.1", "U11.2", "U11.3", "U11.4"]:
        sub_in = param_input.subcriteria_inputs.get(code)
        val = sub_in.raw_inputs.get("verified", False) if sub_in else param_input.raw_inputs.get(code, False)
        sub_results[code] = _evaluate_standard_subcriterion(p_def, code, sub_in, val, validator, context)

    raw_tot = min(sum(r.raw_score for r in sub_results.values()), p_def["max_marks"])
    gated_tot = min(sum(r.evidence_gated_score for r in sub_results.values()), p_def["max_marks"])
    all_verified = all(r.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED for r in sub_results.values())

    return ParameterResult(
        parameter_code="U11",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.FIXED_ITEM_SUM,
        subcriteria_results=sub_results,
    )


def eval_u12(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U12"]
    sub_results = {}
    for code in ["U12.1", "U12.2", "U12.3", "U12.4", "U12.5"]:
        sub_in = param_input.subcriteria_inputs.get(code)
        val = sub_in.raw_inputs.get("verified", False) if sub_in else param_input.raw_inputs.get(code, False)
        sub_results[code] = _evaluate_standard_subcriterion(p_def, code, sub_in, val, validator, context)

    raw_tot = min(sum(r.raw_score for r in sub_results.values()), p_def["max_marks"])
    gated_tot = min(sum(r.evidence_gated_score for r in sub_results.values()), p_def["max_marks"])
    all_verified = all(r.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED for r in sub_results.values())

    return ParameterResult(
        parameter_code="U12",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.FIXED_ITEM_SUM,
        subcriteria_results=sub_results,
    )


def eval_u13(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U13"]
    sub_in = param_input.subcriteria_inputs.get("U13.1")
    raw_inputs = sub_in.raw_inputs if sub_in else param_input.raw_inputs
    num = raw_inputs.get("regular_mooc_learners", 0)
    den = raw_inputs.get("total_regular_learners", 0)

    pct, pct_trace, valid = calculate_percentage(num, den, metric_label="MOOCs Adoption %")
    if not valid:
        pct = 0.0

    sub_res = _evaluate_standard_subcriterion(p_def, "U13.1", sub_in, pct, validator, context)
    sub_res.trace["percentage_trace"] = pct_trace

    return ParameterResult(
        parameter_code="U13",
        max_marks=p_def["max_marks"],
        raw_score=sub_res.raw_score,
        evidence_gated_score=sub_res.evidence_gated_score,
        review_adjusted_score=None,
        final_score=sub_res.final_score,
        resolution_status=sub_res.resolution_status,
        aggregation_strategy=EvaluationType.MAX,
        subcriteria_results={"U13.1": sub_res},
    )


def eval_u14(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U14"]
    in_a = param_input.subcriteria_inputs.get("U14.A")
    raw_a = in_a.raw_inputs if in_a else param_input.raw_inputs.get("U14.A", {})
    pct_a, trace_a, val_a = calculate_percentage(
        raw_a.get("multidisciplinary_programmes", 0),
        raw_a.get("total_degree_programmes", 0),
        metric_label="U14.A Multidisciplinary %"
    )
    res_a = _evaluate_standard_subcriterion(p_def, "U14.A", in_a, pct_a if val_a else 0.0, validator, context)

    in_b = param_input.subcriteria_inputs.get("U14.B")
    val_b = in_b.raw_inputs.get("verified", False) if in_b else param_input.raw_inputs.get("U14.B", False)
    res_b = _evaluate_standard_subcriterion(p_def, "U14.B", in_b, val_b, validator, context)

    in_c = param_input.subcriteria_inputs.get("U14.C")
    val_c = in_c.raw_inputs.get("verified", False) if in_c else param_input.raw_inputs.get("U14.C", False)
    res_c = _evaluate_standard_subcriterion(p_def, "U14.C", in_c, val_c, validator, context)

    raw_tot = min(res_a.raw_score + res_b.raw_score + res_c.raw_score, p_def["max_marks"])
    gated_tot = min(res_a.evidence_gated_score + res_b.evidence_gated_score + res_c.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_a.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_b.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_c.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="U14",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"U14.A": res_a, "U14.B": res_b, "U14.C": res_c},
    )


def eval_u15(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U15"]
    in_1 = param_input.subcriteria_inputs.get("U15.1")
    val_1 = in_1.raw_inputs.get("verified", False) if in_1 else param_input.raw_inputs.get("U15.1", False)
    res_1 = _evaluate_standard_subcriterion(p_def, "U15.1", in_1, val_1, validator, context)

    in_2 = param_input.subcriteria_inputs.get("U15.2")
    val_2 = in_2.raw_inputs.get("verified", False) if in_2 else param_input.raw_inputs.get("U15.2", False)
    res_2 = _evaluate_standard_subcriterion(p_def, "U15.2", in_2, val_2, validator, context)

    raw_tot = min(res_1.raw_score + res_2.raw_score, p_def["max_marks"])
    gated_tot = min(res_1.evidence_gated_score + res_2.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_1.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_2.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="U15",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"U15.1": res_1, "U15.2": res_2},
    )


def eval_u16(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U16"]
    # U16.I: Patents filed (1 mark per 5, max 2)
    in_1 = param_input.subcriteria_inputs.get("U16.I")
    cnt_filed = in_1.raw_inputs.get("patents_filed", 0) if in_1 else param_input.raw_inputs.get("patents_filed", 0)
    res_1 = _evaluate_standard_subcriterion(p_def, "U16.I", in_1, cnt_filed, validator, context, is_count=True)

    # U16.II: Patents granted/commercialised/licensed (1 mark for each patent granted, max 2)
    in_2 = param_input.subcriteria_inputs.get("U16.II")
    cnt_granted = in_2.raw_inputs.get("patents_granted", 0) if in_2 else param_input.raw_inputs.get("patents_granted", 0)
    res_2 = _evaluate_standard_subcriterion(p_def, "U16.II", in_2, cnt_granted, validator, context, is_count=True)

    # U16.III: Scopus Index -> UNRESOLVED_RULE!
    in_3 = param_input.subcriteria_inputs.get("U16.III")
    res_3 = _evaluate_standard_subcriterion(p_def, "U16.III", in_3, 0.0, validator, context)

    raw_tot = min(res_1.raw_score + res_2.raw_score, p_def["max_marks"])
    gated_tot = min(res_1.evidence_gated_score + res_2.evidence_gated_score, p_def["max_marks"])

    return ParameterResult(
        parameter_code="U16",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=None,  # BLOCKED by unresolved U16.III
        resolution_status=ResolutionStatus.UNRESOLVED_RULE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"U16.I": res_1, "U16.II": res_2, "U16.III": res_3},
        trace={"unresolved_subcriterion": "U16.III"},
    )


def eval_u17(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U17"]
    in_1 = param_input.subcriteria_inputs.get("U17.1")
    val_1 = in_1.raw_inputs.get("verified", False) if in_1 else param_input.raw_inputs.get("U17.1", False)
    res_1 = _evaluate_standard_subcriterion(p_def, "U17.1", in_1, val_1, validator, context)

    in_2 = param_input.subcriteria_inputs.get("U17.2")
    val_2 = in_2.raw_inputs.get("verified", False) if in_2 else param_input.raw_inputs.get("U17.2", False)
    res_2 = _evaluate_standard_subcriterion(p_def, "U17.2", in_2, val_2, validator, context)

    raw_tot = min(res_1.raw_score + res_2.raw_score, p_def["max_marks"])
    gated_tot = min(res_1.evidence_gated_score + res_2.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_1.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_2.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="U17",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"U17.1": res_1, "U17.2": res_2},
    )


def eval_u18(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U18"]
    in_1 = param_input.subcriteria_inputs.get("U18.1")
    val_1 = in_1.raw_inputs.get("verified", False) if in_1 else param_input.raw_inputs.get("U18.1", False)
    res_1 = _evaluate_standard_subcriterion(p_def, "U18.1", in_1, val_1, validator, context)

    in_2 = param_input.subcriteria_inputs.get("U18.2")
    val_2 = in_2.raw_inputs.get("verified", False) if in_2 else param_input.raw_inputs.get("U18.2", False)
    res_2 = _evaluate_standard_subcriterion(p_def, "U18.2", in_2, val_2, validator, context)

    in_3 = param_input.subcriteria_inputs.get("U18.3")
    val_3 = in_3.raw_inputs.get("verified", False) if in_3 else param_input.raw_inputs.get("U18.3", False)
    res_3 = _evaluate_standard_subcriterion(p_def, "U18.3", in_3, val_3, validator, context)

    raw_tot = min(res_1.raw_score + res_2.raw_score + res_3.raw_score, p_def["max_marks"])
    gated_tot = min(res_1.evidence_gated_score + res_2.evidence_gated_score + res_3.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_1.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_2.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and
                    res_3.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="U18",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"U18.1": res_1, "U18.2": res_2, "U18.3": res_3},
    )


def eval_u19(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U19"]
    in_a = param_input.subcriteria_inputs.get("U19.A")
    raw_a = in_a.raw_inputs if in_a else param_input.raw_inputs.get("U19.A", {})
    pct_a, trace_a, val_a = calculate_percentage(
        raw_a.get("obe_programmes", 0),
        raw_a.get("total_degree_programmes", 0),
        metric_label="U19.A OBE Adoption %"
    )
    res_a = _evaluate_standard_subcriterion(p_def, "U19.A", in_a, pct_a if val_a else 0.0, validator, context)

    in_b = param_input.subcriteria_inputs.get("U19.B")
    val_b = in_b.raw_inputs.get("verified", False) if in_b else param_input.raw_inputs.get("U19.B", False)
    res_b = _evaluate_standard_subcriterion(p_def, "U19.B", in_b, val_b, validator, context)

    raw_tot = min(res_a.raw_score + res_b.raw_score, p_def["max_marks"])
    gated_tot = min(res_a.evidence_gated_score + res_b.evidence_gated_score, p_def["max_marks"])
    all_verified = (res_a.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED and 
                    res_b.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED)

    return ParameterResult(
        parameter_code="U19",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=gated_tot if all_verified else None,
        resolution_status=ResolutionStatus.CALCULABLE,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"U19.A": res_a, "U19.B": res_b},
    )


def eval_u20(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
    p_def = UNIVERSITY_PARAMETERS["U20"]
    in_1 = param_input.subcriteria_inputs.get("U20.1")
    act_cnt = in_1.raw_inputs.get("activities_count", 0) if in_1 else param_input.raw_inputs.get("activities_count", 0)
    res_1 = _evaluate_standard_subcriterion(p_def, "U20.1", in_1, act_cnt, validator, context, is_count=True)

    in_2 = param_input.subcriteria_inputs.get("U20.2")
    val_2 = in_2.raw_inputs.get("verified", False) if in_2 else param_input.raw_inputs.get("U20.2", False)
    res_2 = _evaluate_standard_subcriterion(p_def, "U20.2", in_2, val_2, validator, context)

    in_3 = param_input.subcriteria_inputs.get("U20.3")
    val_3 = in_3.raw_inputs.get("verified", False) if in_3 else param_input.raw_inputs.get("U20.3", False)
    res_3 = _evaluate_standard_subcriterion(p_def, "U20.3", in_3, val_3, validator, context)

    # U20 items sum to 5 marks against declared maximum of 4 marks (SOURCE_INCONSISTENCY)
    items_sum_raw = res_1.raw_score + res_2.raw_score + res_3.raw_score
    items_sum_gated = res_1.evidence_gated_score + res_2.evidence_gated_score + res_3.evidence_gated_score
    raw_tot = min(items_sum_raw, p_def["max_marks"])
    gated_tot = min(items_sum_gated, p_def["max_marks"])

    return ParameterResult(
        parameter_code="U20",
        max_marks=p_def["max_marks"],
        raw_score=raw_tot,
        evidence_gated_score=gated_tot,
        review_adjusted_score=None,
        final_score=None,  # Blocked by source arithmetic inconsistency
        resolution_status=ResolutionStatus.SOURCE_INCONSISTENCY,
        aggregation_strategy=EvaluationType.SUM,
        subcriteria_results={"U20.1": res_1, "U20.2": res_2, "U20.3": res_3},
        trace={"discrepancy": "Criteria sum to 5.0 vs Max 4.0; final certification blocked"},
    )


UNIVERSITY_EVALUATORS: Dict[str, Callable[[ParameterInput, AssessmentContext, DoubleCountingValidator], ParameterResult]] = {
    "U1": eval_u1,
    "U2": eval_u2,
    "U3": eval_u3,
    "U4": eval_u4,
    "U5": eval_u5,
    "U6": eval_u6,
    "U7": eval_u7,
    "U8": eval_u8,
    "U9": eval_u9,
    "U10": eval_u10,
    "U11": eval_u11,
    "U12": eval_u12,
    "U13": eval_u13,
    "U14": eval_u14,
    "U15": eval_u15,
    "U16": eval_u16,
    "U17": eval_u17,
    "U18": eval_u18,
    "U19": eval_u19,
    "U20": eval_u20,
}
