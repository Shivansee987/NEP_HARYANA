"""
NEP Excellence Awards 2026 - Shared subcriterion / parameter evaluator.

Every C1–C22 and U1–U20 parameter is evaluated by the same pipeline, driven by
apps.scoring.rules.definitions (metrics, thresholds) and apps.scoring.field_schema (inputs):

  1. normalise the canonical inputs (apps.scoring.inputs) -> structured INVALID_INPUT, never a crash
  2. period rule for period-bound claims -> out-of-period claims are explicitly ineligible (0), never
     turned into a numeric 0 that could fall into a positive tier
  3. metric value (ratio / count / per_unit / boolean / grade / currency / average / areas / policy_metric)
  4. double counting -> only a COUNT is reduced by rejected duplicate entities; percentages, grades and
     booleans keep their semantic value
  5. thresholds, boundary voids and policy items (apps.scoring.policy)
  6. evidence gating
"""
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from apps.scoring import policy as policy_registry
from apps.scoring.domain import (
    AssessmentContext,
    ParameterInput,
    ParameterResult,
    SubcriterionInput,
    SubcriterionResult,
)
from apps.scoring.enums import DoubleCountingRule, GatingStatus, ResolutionStatus, ThresholdOperator
from apps.scoring.evaluators.double_counting import DoubleCountingValidator
from apps.scoring.evaluators.evidence_gating import evaluate_subcriterion_contract_evidence
from apps.scoring.evaluators.thresholds import evaluate_threshold
from apps.scoring.inputs import NormalizedInput, normalize_subcriterion

# Status precedence when rolling subcriteria up to a parameter (most severe first)
_STATUS_ORDER = [
    ResolutionStatus.INVALID_INPUT,
    ResolutionStatus.POLICY_UNRESOLVED,
    ResolutionStatus.BOUNDARY_UNRESOLVED,
    ResolutionStatus.UNRESOLVED_RULE,
    ResolutionStatus.SOURCE_INCONSISTENCY,
    ResolutionStatus.CALCULABLE,
]

_COUNT_KINDS = ("count", "per_unit")


def _raw_for_sub(param_input: ParameterInput, param_def: Dict[str, Any], sub_code: str) -> Tuple[Optional[SubcriterionInput], Any]:
    sub_in = param_input.subcriteria_inputs.get(sub_code)
    if sub_in is not None:
        return sub_in, sub_in.raw_inputs
    raw = param_input.raw_inputs or {}
    if isinstance(raw.get(sub_code), dict):
        return None, raw[sub_code]
    # A flat, un-keyed payload is only unambiguous for single-subcriterion parameters
    if len(param_def["subcriteria"]) == 1:
        return None, {k: v for k, v in raw.items() if not isinstance(v, dict)}
    return None, {}


class _Value:
    """Outcome of the metric step."""

    def __init__(self, value=None, status=ResolutionStatus.CALCULABLE, provided=True, note=None,
                 policy_id=None, direct_score=None):
        self.value = value
        self.status = status
        self.provided = provided
        self.note = note
        self.policy_id = policy_id
        self.direct_score = direct_score


def _ratio(num, den, allow_over) -> _Value:
    if num is None and den is None:
        return _Value(provided=False, note="Not provided")
    num = num or 0
    den = den or 0
    if den == 0:
        if num == 0:
            return _Value(0.0, note="Zero base: 0 of 0 -> 0%")
        return _Value(status=ResolutionStatus.INVALID_INPUT, note=f"Numerator {num} with zero denominator")
    if num > den and not allow_over:
        return _Value(status=ResolutionStatus.INVALID_INPUT, note=f"Numerator {num} exceeds denominator {den}")
    return _Value(num * 100.0 / den)


def _metric_value(metric: Dict[str, Any], vals: Dict[str, Any], sibling_vals: Dict[str, Dict[str, Any]],
                  sub_def: Dict[str, Any]) -> _Value:
    kind = metric["kind"]
    if kind == "ratio":
        num = vals.get(metric["num"])
        if metric.get("den_from"):
            s_code, s_key = metric["den_from"]
            den = sibling_vals.get(s_code, {}).get(s_key)
        else:
            den = vals.get(metric["den"])
        if metric.get("den_from") and num is None:
            return _Value(provided=False, note="Not provided")
        return _ratio(num, den, metric.get("allow_over", False))
    if kind in ("count", "per_unit", "currency"):
        v = vals.get(metric["key"])
        return _Value(provided=False, note="Not provided") if v is None else _Value(v)
    if kind == "boolean":
        return _Value(1.0 if vals.get(metric["key"]) is True else 0.0, provided=vals.get(metric["key"]) is not None)
    if kind == "grade":
        g = vals.get(metric["key"])
        if g is None:
            return _Value(provided=False, note="Not provided")
        return _Value(g, direct_score=float(metric["map"][g]))
    if kind == "areas":
        areas = sum(len(vals.get(k) or []) for k in metric["list_keys"])
        gate = metric.get("gate")
        if gate is not None:
            gate_val = vals.get(gate["key"])
            if gate_val is None or gate_val < gate["min"]:
                return _Value(areas, direct_score=0.0, provided=gate_val is not None or areas > 0,
                              note=f"Applicable only when at least {gate['min']} are covered ({gate['key']}={gate_val})")
        return _Value(areas, direct_score=min(areas * metric["unit"], sub_def["max_score"]))
    if kind == "average":
        total = vals.get(metric["num"])
        s_code, s_key = metric["den_from"]
        active = sibling_vals.get(s_code, {}).get(s_key)
        if total is None:
            return _Value(provided=False, note="Not provided")
        if not active:
            if total == 0:
                return _Value(0.0, note="No activities and no active collaborations")
            return _Value(status=ResolutionStatus.INVALID_INPUT,
                          note=f"{total} activities reported but no active collaborations in {s_code}")
        avg = total / active
        if avg >= 5 or float(avg).is_integer():
            return _Value(avg, note=f"Average = {total} / {active} = {avg:g}")
        rule = policy_registry.u9b_fractional_rule()
        if rule is None:
            return _Value(avg, status=ResolutionStatus.POLICY_UNRESOLVED, policy_id=metric["policy_id"],
                          note=f"Average {total} / {active} = {avg:.4g} is fractional; tiering is not defined by the source")
        tiered = {"FLOOR": math.floor(avg), "CEIL": math.ceil(avg), "ROUND_HALF_UP": math.floor(avg + 0.5)}[rule]
        return _Value(float(tiered), policy_id=metric["policy_id"],
                      note=f"Average {avg:.4g} tiered as {tiered} by configured policy rule {rule}")
    if kind == "policy_metric":
        v = vals.get(metric["key"])
        if not v:
            return _Value(0.0 if v == 0 else None, provided=v is not None, note="No value claimed")
        if policy_registry.scopus_metric_resolution() is None:
            return _Value(v, status=ResolutionStatus.POLICY_UNRESOLVED, policy_id=metric["policy_id"],
                          note="Claimed value cannot be scored: the source does not define this metric")
        return _Value(v, policy_id=metric["policy_id"])
    raise ValueError(f"Unknown metric kind {kind}")


def _result(sub_code, max_score, raw_score, gated, status, gating, trace, matched=None) -> SubcriterionResult:
    raw_score = max(0.0, min(float(raw_score), max_score))
    gated = max(0.0, min(float(gated), max_score))
    final = gated if (status == ResolutionStatus.CALCULABLE and gating in (
        GatingStatus.PASSED_EVIDENCE_VERIFIED, GatingStatus.NO_EVIDENCE_REQUIRED)) else None
    return SubcriterionResult(
        subcriterion_code=sub_code, raw_score=raw_score, evidence_gated_score=gated, review_adjusted_score=None,
        final_score=final, max_score=max_score, resolution_status=status, gating_status=gating,
        matched_threshold=matched, trace=trace,
    )


def evaluate_subcriterion(
    param_def: Dict[str, Any],
    sub_code: str,
    param_input: ParameterInput,
    context: AssessmentContext,
    validator: DoubleCountingValidator,
    sibling_vals: Dict[str, Dict[str, Any]],
    policy_hits: List[Dict[str, Any]],
) -> Tuple[SubcriterionResult, NormalizedInput]:
    p_code = param_def["parameter_code"]
    sub_def = param_def["subcriteria"][sub_code]
    metric = sub_def["metric"]
    max_score = float(sub_def["max_score"])
    sub_in, raw = _raw_for_sub(param_input, param_def, sub_code)
    trace: Dict[str, Any] = {"subcriterion_code": sub_code, "metric": metric["kind"]}

    # 1. Canonical input normalisation
    norm = normalize_subcriterion(
        p_code, sub_code, raw, strict=False,
        fallback_activity_date=getattr(sub_in, "activity_date", None) if sub_in else None,
    )
    trace["inputs"] = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in norm.values.items()}
    sibling_vals[sub_code] = norm.values

    # Evidence gating is evaluated for every subcriterion so the reviewer sees its state
    uploaded_docs = list(sub_in.evidence_docs) if sub_in else []
    for doc in uploaded_docs:
        validator.record_document_reference(doc.document_id, sub_code)
    # Year-specific subcriteria (e.g. U4.A = 2024-25 targets) ignore evidence explicitly dated to another year
    target_year = sub_def.get("evidence_academic_year")
    if target_year:
        excluded = [d.document_id for d in uploaded_docs if getattr(d, "academic_year", None) not in (None, "", target_year)]
        if excluded:
            trace["evidence_excluded_wrong_academic_year"] = {"required": target_year, "documents": excluded}
        uploaded_docs = [d for d in uploaded_docs if getattr(d, "academic_year", None) in (None, "", target_year)]
    gating, multiplier, eg_trace = evaluate_subcriterion_contract_evidence(
        framework=getattr(context, "framework", param_def["framework"]),
        parameter_id=p_code,
        subcriterion_id=sub_code,
        uploaded_docs=uploaded_docs,
        param_def=param_def,
        sub_def=sub_def,
    )
    trace["evidence_gating"] = eg_trace

    if norm.errors:
        trace["validation_errors"] = norm.errors
        return _result(sub_code, max_score, 0.0, 0.0, ResolutionStatus.INVALID_INPUT, gating, trace), norm

    # 2. Period rule
    if norm.period is not None:
        trace["period_validation"] = norm.period
    if norm.out_of_period:
        trace["period_ineligible"] = True
        trace["scoring_note"] = "Claim is outside the assessment period and is not eligible for marks."
        return _result(sub_code, max_score, 0.0, 0.0, ResolutionStatus.CALCULABLE, gating, trace), norm

    # 3. Metric value
    mv = _metric_value(metric, norm.values, sibling_vals, sub_def)
    if mv.note:
        trace["value_note"] = mv.note
    trace["value"] = mv.value
    trace["value_provided"] = mv.provided
    if mv.status == ResolutionStatus.INVALID_INPUT:
        trace["validation_errors"] = [{"field": sub_code, "code": "INVALID_VALUE", "message": mv.note}]
        return _result(sub_code, max_score, 0.0, 0.0, ResolutionStatus.INVALID_INPUT, gating, trace), norm
    if mv.status == ResolutionStatus.POLICY_UNRESOLVED:
        hit = policy_registry.policy_notice(mv.policy_id, triggered=True)
        hit["subcriterion"] = sub_code
        policy_hits.append(hit)
        trace["policy"] = hit
        return _result(sub_code, max_score, 0.0, 0.0, ResolutionStatus.POLICY_UNRESOLVED, gating, trace), norm
    if mv.policy_id and mv.status == ResolutionStatus.CALCULABLE:
        trace["policy"] = policy_registry.policy_notice(mv.policy_id, triggered=True)

    value = mv.value

    # 4. Double counting — only a count is reduced by duplicate entities rejected in other parameters
    v_ents, r_ents, dc_trace = validator.validate_subcriterion_input(
        sub_code, sub_in, param_def.get("double_counting_rule", DoubleCountingRule.FORBIDDEN_REUSE),
        allow_sibling_reuse=bool(param_def.get("sibling_entity_reuse")),
    )
    if dc_trace.get("total_entities_submitted", 0) > 0:
        trace["double_counting"] = dc_trace
    if r_ents and metric["kind"] in _COUNT_KINDS and value is not None:
        adjusted = max(0, int(value) - len(r_ents))
        trace["double_counting_adjustment"] = {"declared": value, "rejected_duplicates": len(r_ents), "counted": adjusted}
        value = adjusted
    elif r_ents:
        trace["double_counting_adjustment"] = {
            "note": "Duplicate entities flagged for review; value kept (not a count).", "rejected_duplicates": len(r_ents)}

    # 5. Score
    matched = None
    if not mv.provided and value is None:
        raw_score = 0.0
    elif mv.direct_score is not None:
        raw_score = mv.direct_score
        matched = {"operator": ThresholdOperator.OP_EQ if metric["kind"] == "grade" else "AREA_COUNT", "score": raw_score}
    elif metric["kind"] == "boolean":
        raw_score = max_score if value == 1.0 else 0.0
        matched = {"operator": ThresholdOperator.OP_BOOLEAN, "score": raw_score}
    elif metric["kind"] == "per_unit":
        raw_score = min(float(value) * metric["unit"], max_score)
        matched = {"operator": "PER_UNIT", "unit": metric["unit"], "score": raw_score}
    else:
        for void in sub_def.get("boundary_voids", []):
            if value is not None and abs(float(value) - void["exact_val"]) < 1e-9:
                pid = void["policy_id"]
                resolved = policy_registry.boundary_resolution_score(pid)
                hit = policy_registry.policy_notice(pid, triggered=True)
                hit["subcriterion"] = sub_code
                trace["boundary"] = hit
                if resolved is None:
                    policy_hits.append(hit)
                    return _result(sub_code, max_score, 0.0, 0.0, ResolutionStatus.BOUNDARY_UNRESOLVED, gating, trace), norm
                trace["threshold_trace"] = {"boundary_resolved_by_policy": pid, "score": resolved}
                return _result(sub_code, max_score, resolved, resolved * multiplier, ResolutionStatus.CALCULABLE, gating,
                               trace, {"operator": "POLICY_BOUNDARY", "score": resolved}), norm
        score, op, th_trace, th_status = evaluate_threshold(value, sub_def["thresholds"])
        trace["threshold_trace"] = th_trace
        trace["matched_tier"] = th_trace.get("matched_tier")
        raw_score = score or 0.0
        matched = th_trace.get("matched_tier") or {"operator": op, "score": raw_score}

    # 6. Evidence gating applied to the raw score
    gated = raw_score * multiplier
    return _result(sub_code, max_score, raw_score, gated, ResolutionStatus.CALCULABLE, gating, trace, matched), norm


def evaluate_parameter(param_def: Dict[str, Any], param_input: ParameterInput, context: AssessmentContext,
                       validator: DoubleCountingValidator) -> ParameterResult:
    p_code = param_def["parameter_code"]
    sibling_vals: Dict[str, Dict[str, Any]] = {}
    policy_hits: List[Dict[str, Any]] = []
    sub_results: Dict[str, SubcriterionResult] = {}
    for sub_code in param_def["subcriteria"]:
        res, _ = evaluate_subcriterion(param_def, sub_code, param_input, context, validator, sibling_vals, policy_hits)
        sub_results[sub_code] = res

    max_marks = float(param_def["max_marks"])
    raw_sum = sum(r.raw_score for r in sub_results.values())
    gated_sum = sum(r.evidence_gated_score for r in sub_results.values())
    status = next(s for s in _STATUS_ORDER if s == ResolutionStatus.CALCULABLE or any(
        r.resolution_status == s for r in sub_results.values()))
    all_final = all(r.final_score is not None for r in sub_results.values()) and status == ResolutionStatus.CALCULABLE
    gated_total = min(gated_sum, max_marks)

    trace: Dict[str, Any] = {
        "evaluated_subcriteria": list(sub_results),
        "items_sum_raw": raw_sum,
        "items_sum_gated": gated_sum,
        "capped_at_maximum": gated_sum > max_marks or raw_sum > max_marks,
    }
    notices = []
    if param_def.get("advisory_policy"):
        notices.append(policy_registry.policy_notice(
            param_def["advisory_policy"], triggered=raw_sum > max_marks or param_def["advisory_policy"] in (
                "C7_MAXIMUM", "C21_MAXIMUM", "U8A_COMPONENT_HEADER", "C8_BINARY")))
    notices.extend(policy_hits)
    if notices:
        trace["policy_notices"] = notices
    errors = [dict(e, subcriterion=s) for s, r in sub_results.items() for e in r.trace.get("validation_errors", [])]
    if errors:
        trace["validation_errors"] = errors

    return ParameterResult(
        parameter_code=p_code,
        max_marks=max_marks,
        raw_score=min(raw_sum, max_marks),
        evidence_gated_score=gated_total,
        review_adjusted_score=None,
        final_score=gated_total if all_final else None,
        resolution_status=status,
        aggregation_strategy=param_def["aggregation_strategy"],
        subcriteria_results=sub_results,
        trace=trace,
    )


def build_evaluators(definitions: Dict[str, Dict[str, Any]]) -> Dict[str, Callable[..., ParameterResult]]:
    def _make(code: str):
        def _evaluate(param_input: ParameterInput, context: AssessmentContext, validator: DoubleCountingValidator) -> ParameterResult:
            return evaluate_parameter(definitions[code], param_input, context, validator)
        _evaluate.__name__ = f"eval_{code.lower()}"
        return _evaluate
    return {code: _make(code) for code in definitions}
