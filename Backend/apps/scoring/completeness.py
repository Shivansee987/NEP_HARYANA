"""
Submission completeness: every number and single-choice field of every subcriterion must be answered
(institutions enter 0 when they have nothing to claim). Checkboxes and lists are optional because "no" / "none"
is a valid answer, and activity dates are enforced separately by the period checks when a claim is positive.

This is the rule the institution workspace already applies (frontend utils/nepTaxonomy.js isFieldRequired);
enforcing it here stops a partial assessment from being submitted through the API.
"""
from typing import Any, Dict, List

REQUIRED_TYPES = ("integer", "currency", "enum")


def _blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "") or (isinstance(value, (list, tuple)) and not value)


def completeness_errors(param_data: Dict[str, Any], field_schema: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    for p_code, p_schema in field_schema.items():
        stored = (param_data or {}).get(p_code) or {}
        raw = stored.get("raw_inputs", {}) if isinstance(stored, dict) else {}
        for s_code, sub in p_schema.get("subcriteria", {}).items():
            values = raw.get(s_code) if isinstance(raw, dict) else None
            values = values if isinstance(values, dict) else {}
            for field in sub.get("fields", []):
                if field.get("type") in REQUIRED_TYPES and _blank(values.get(field["key"])):
                    errors.append({
                        "parameter": p_code,
                        "subcriterion": s_code,
                        "field": field["key"],
                        "code": "REQUIRED",
                        "message": f"'{field.get('label') or field['key']}' must be answered (enter 0 if not applicable).",
                    })
    return errors


def summarize(errors: List[Dict[str, Any]], limit: int = 5) -> str:
    params = sorted({e["parameter"] for e in errors}, key=lambda c: (c[0], int("".join(ch for ch in c[1:] if ch.isdigit()) or 0)))
    shown = ", ".join(params[:limit]) + (f" and {len(params) - limit} more" if len(params) > limit else "")
    return f"Submission blocked: {len(errors)} required answer(s) missing in {shown}."
