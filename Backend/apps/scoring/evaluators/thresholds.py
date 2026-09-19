"""
NEP Excellence Awards 2026 - Exact Threshold Evaluator
Preserves source legal operators without normalization or boundary shifting.
"""
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal

from apps.scoring.enums import ThresholdOperator, ResolutionStatus


def evaluate_threshold(
    value: Any,
    thresholds: List[Dict[str, Any]],
    boundary_unresolved_conditions: Optional[List[Dict[str, Any]]] = None
) -> Tuple[Optional[float], Optional[ThresholdOperator], Dict[str, Any], ResolutionStatus]:
    """
    Evaluates a numerical or boolean value against an ordered list of thresholds.
    
    Returns:
        (score, matched_operator, trace, resolution_status)
    """
    trace: Dict[str, Any] = {
        "input_value": value,
        "evaluations": [],
        "matched": False,
    }

    if value is None:
        trace["error"] = "Input value is None"
        return 0.0, None, trace, ResolutionStatus.INVALID_INPUT

    # 1. Check known mathematical boundary voids first
    if boundary_unresolved_conditions:
        for void_cond in boundary_unresolved_conditions:
            exact_val = void_cond.get("exact_val")
            if exact_val is not None:
                # Compare numerically with high precision
                try:
                    diff = abs(Decimal(str(value)) - Decimal(str(exact_val)))
                    if diff < Decimal("1e-9"):
                        trace["boundary_unresolved"] = True
                        trace["unresolved_reason"] = void_cond.get("reason", "Exact boundary void in authoritative source rubric")
                        return None, ThresholdOperator.BOUNDARY_UNRESOLVED, trace, ResolutionStatus.BOUNDARY_UNRESOLVED
                except Exception:
                    pass

    # 2. Iterate through defined thresholds in order
    for idx, t in enumerate(thresholds):
        op = t.get("operator")
        tier_score = float(t.get("score", 0.0))
        min_val = t.get("min_val")
        max_val = t.get("max_val")
        target_val = t.get("target_val")

        matched = False
        eval_detail = {
            "tier_index": idx,
            "operator": op,
            "tier_score": tier_score,
            "min_val": min_val,
            "max_val": max_val,
        }

        try:
            val_num = float(value) if not isinstance(value, bool) else (1.0 if value else 0.0)
        except (ValueError, TypeError):
            val_num = None

        if op == ThresholdOperator.OP_BOOLEAN or op == "OP_BOOLEAN":
            matched = bool(value) is True
        elif op == ThresholdOperator.OP_EQ or op == "OP_EQ":
            if target_val is not None and val_num is not None:
                matched = abs(val_num - float(target_val)) < 1e-9
            else:
                matched = value == target_val
        elif val_num is not None:
            if op == ThresholdOperator.OP_GT or op == "OP_GT":
                matched = val_num > float(min_val)
            elif op == ThresholdOperator.OP_GTE or op == "OP_GTE":
                matched = val_num >= float(min_val)
            elif op == ThresholdOperator.OP_LT or op == "OP_LT":
                matched = val_num < float(max_val)
            elif op == ThresholdOperator.OP_LTE or op == "OP_LTE":
                matched = val_num <= float(max_val)
            elif op == ThresholdOperator.OP_GT_AND_LTE or op == "OP_GT_AND_LTE":
                matched = (val_num > float(min_val)) and (val_num <= float(max_val))
            elif op == ThresholdOperator.OP_GTE_AND_LTE or op == "OP_GTE_AND_LTE":
                matched = (val_num >= float(min_val)) and (val_num <= float(max_val))
            elif op == ThresholdOperator.OP_GT_AND_LT or op == "OP_GT_AND_LT":
                matched = (val_num > float(min_val)) and (val_num < float(max_val))
            elif op == ThresholdOperator.BOUNDARY_UNRESOLVED or op == "BOUNDARY_UNRESOLVED":
                trace["boundary_unresolved"] = True
                trace["unresolved_reason"] = t.get("reason", "Boundary unresolved")
                return None, ThresholdOperator.BOUNDARY_UNRESOLVED, trace, ResolutionStatus.BOUNDARY_UNRESOLVED

        eval_detail["matched"] = matched
        trace["evaluations"].append(eval_detail)

        if matched:
            trace["matched"] = True
            trace["matched_tier"] = eval_detail
            return tier_score, ThresholdOperator(op) if isinstance(op, str) and hasattr(ThresholdOperator, op) else op, trace, ResolutionStatus.CALCULABLE

    # No tier matched - default fallback to 0.0
    trace["matched"] = False
    trace["note"] = "Value did not match any positive threshold tier; default 0 marks applied"
    return 0.0, None, trace, ResolutionStatus.CALCULABLE
