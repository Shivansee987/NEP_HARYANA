"""
NEP Excellence Awards 2026 - Scoring & Evaluation Formatters
Produces human-readable scoring basis, subcriterion breakdown, and audit traceability.
"""
from typing import Any, Dict, Optional
from apps.scoring.domain import ParameterResult, SubcriterionResult
from apps.scoring.enums import GatingStatus, ResolutionStatus, ThresholdOperator


def format_subcriterion_scoring_basis(sub_res: SubcriterionResult) -> str:
    """
    Returns a concise, human-readable scoring basis for a subcriterion,
    e.g. '>7 and up to 10', '>=90%', 'Affirmative compliance verified'.
    """
    if sub_res.resolution_status in (ResolutionStatus.UNRESOLVED_RULE, ResolutionStatus.SOURCE_INCONSISTENCY):
        return "Maximum unresolved — source clarification required"
    if sub_res.resolution_status == ResolutionStatus.BOUNDARY_UNRESOLVED:
        return "Boundary void in rubric — unresolved"
    if sub_res.gating_status == GatingStatus.FAILED_EVIDENCE_REJECTED:
        return "Evidence rejected — 0 marks awarded"
    if sub_res.gating_status == GatingStatus.FAILED_EVIDENCE_ABSENT:
        return "Mandatory evidence absent — 0 marks awarded"
    if sub_res.gating_status == GatingStatus.PROVISIONAL_PENDING_VERIFICATION:
        return "Evidence pending verification — provisional"

    # Inspect trace for matched tier
    matched_tier = sub_res.trace.get("matched_tier") or sub_res.matched_threshold
    if not matched_tier and "threshold_eval" in sub_res.trace:
        matched_tier = sub_res.trace["threshold_eval"].get("matched_tier")

    if matched_tier:
        op = matched_tier.get("operator")
        min_v = matched_tier.get("min_val")
        max_v = matched_tier.get("max_val")
        target_v = matched_tier.get("target_val")

        def _fmt(val):
            if val is None:
                return ""
            if isinstance(val, float) and val.is_integer():
                return str(int(val))
            return str(val)

        if op in (ThresholdOperator.OP_GT, "OP_GT"):
            return f">{_fmt(min_v)}"
        elif op in (ThresholdOperator.OP_GTE, "OP_GTE"):
            return f">={_fmt(min_v)}"
        elif op in (ThresholdOperator.OP_GT_AND_LTE, "OP_GT_AND_LTE"):
            return f">{_fmt(min_v)} and up to {_fmt(max_v)}"
        elif op in (ThresholdOperator.OP_GTE_AND_LTE, "OP_GTE_AND_LTE"):
            return f">={_fmt(min_v)} and up to {_fmt(max_v)}"
        elif op in (ThresholdOperator.OP_GT_AND_LT, "OP_GT_AND_LT"):
            return f">{_fmt(min_v)} and <{_fmt(max_v)}"
        elif op in (ThresholdOperator.OP_LT, "OP_LT"):
            return f"<{_fmt(max_v)}"
        elif op in (ThresholdOperator.OP_LTE, "OP_LTE"):
            return f"<={_fmt(max_v)}"
        elif op in (ThresholdOperator.OP_EQ, "OP_EQ"):
            return f"Equals {_fmt(target_v)}"
        elif op in (ThresholdOperator.OP_BOOLEAN, "OP_BOOLEAN"):
            return "Affirmative compliance verified"

    if sub_res.raw_score > 0:
        return f"Satisfied criteria ({_fmt(sub_res.raw_score)} / {_fmt(sub_res.max_score)})"
    return "Criteria not met (0 marks)"


def format_parameter_scoring_basis(param_res: ParameterResult) -> str:
    """
    Returns a unified human-readable scoring basis for an entire parameter.
    """
    if param_res.resolution_status in (ResolutionStatus.UNRESOLVED_RULE, ResolutionStatus.SOURCE_INCONSISTENCY):
        return "Maximum unresolved — source clarification required"
    if param_res.resolution_status == ResolutionStatus.BOUNDARY_UNRESOLVED:
        return "Boundary void in rubric — unresolved"

    sub_bases = [
        format_subcriterion_scoring_basis(sub)
        for sub in param_res.subcriteria_results.values()
    ]
    if len(sub_bases) == 1:
        return sub_bases[0]
    return " | ".join(sub_bases[:3])
