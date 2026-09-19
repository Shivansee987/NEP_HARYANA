"""
NEP Excellence Awards 2026 - Percentage Calculator & Denominator Integrity Evaluator
"""
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple


def calculate_percentage(
    numerator: Any,
    denominator: Any,
    allow_over_enrollment: bool = False,
    metric_label: str = "percentage"
) -> Tuple[Optional[float], Dict[str, Any], bool]:
    """
    Computes percentage = (numerator / denominator) * 100.
    
    Returns:
        (percentage_float, trace_dict, is_valid)
    """
    trace: Dict[str, Any] = {
        "metric_label": metric_label,
        "raw_numerator": numerator,
        "raw_denominator": denominator,
        "allow_over_enrollment": allow_over_enrollment,
    }

    if numerator is None or denominator is None:
        trace["error"] = "Numerator or Denominator is None"
        return None, trace, False

    try:
        num = Decimal(str(numerator))
        den = Decimal(str(denominator))
    except (InvalidOperation, ValueError, TypeError) as e:
        trace["error"] = f"Invalid numeric conversion: {str(e)}"
        return None, trace, False

    trace["decimal_numerator"] = str(num)
    trace["decimal_denominator"] = str(den)

    # 1. Non-negativity check
    if num < Decimal("0") or den < Decimal("0"):
        trace["error"] = "Negative numerator or denominator rejected"
        return None, trace, False

    # 2. Denominator check
    if den == Decimal("0"):
        if num == Decimal("0"):
            # Legitimate zero base (e.g. no programmes offered, no enrolled cohort)
            trace["note"] = "Zero baseline cohort: numerator=0 and denominator=0 -> 0.0%"
            trace["computed_percentage"] = 0.0
            return 0.0, trace, True
        else:
            # Mathematical contradiction: graduates without students, admissions without seats
            trace["error"] = "Zero denominator with non-zero numerator (division by zero)"
            return None, trace, False

    # 3. Numerator <= Denominator check
    if num > den and not allow_over_enrollment:
        trace["error"] = f"Numerator ({num}) exceeds denominator ({den}) for standard population"
        return None, trace, False

    # 4. Accurate percentage calculation
    pct = (num / den) * Decimal("100")
    pct_float = float(pct)
    trace["computed_percentage"] = pct_float
    trace["exact_decimal_percentage"] = str(pct)

    return pct_float, trace, True
