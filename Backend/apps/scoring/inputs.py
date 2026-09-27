"""
NEP Excellence Awards 2026 - Canonical input normalisation.

Converts a subcriterion's raw_inputs into typed values according to apps.scoring.field_schema, returning
structured errors instead of raising. Used by the API serializers (strict) and by the scoring engine.

Conventions:
  * missing key, None or "" (a cleared form field)  -> value not provided (never an error, never a crash)
  * anything else that does not satisfy the field type -> structured error, value treated as not provided
"""
import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from .field_schema import (
    ASSESSMENT_PERIOD_END,
    ASSESSMENT_PERIOD_START,
    PERIOD_END_KEY,
    PERIOD_START_KEY,
    get_subcriterion_schema,
)

PERIOD_START = date.fromisoformat(ASSESSMENT_PERIOD_START)
PERIOD_END = date.fromisoformat(ASSESSMENT_PERIOD_END)

# Error codes
INVALID_TYPE = "INVALID_TYPE"
NEGATIVE_VALUE = "NEGATIVE_VALUE"
NOT_INTEGER = "NOT_INTEGER"
NOT_FINITE = "NOT_FINITE"
INVALID_OPTION = "INVALID_OPTION"
DUPLICATE_OPTION = "DUPLICATE_OPTION"
EXCEEDS_FIELD = "EXCEEDS_FIELD"
UNKNOWN_FIELD = "UNKNOWN_FIELD"
INVALID_DATE = "INVALID_DATE"
PERIOD_DATE_REQUIRED = "PERIOD_DATE_REQUIRED"
PERIOD_ORDER = "PERIOD_ORDER"
OUT_OF_PERIOD = "OUT_OF_PERIOD"
REQUIRED_FIELD = "REQUIRED_FIELD"


@dataclass
class NormalizedInput:
    values: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    positive_claim: bool = False
    period: Optional[Dict[str, Any]] = None
    out_of_period: bool = False

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add(self, key: str, code: str, message: str) -> None:
        self.errors.append({"field": key, "code": code, "message": message})


def _is_blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _to_decimal(v: Any) -> Optional[Decimal]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, Decimal)):
        return Decimal(v)
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return Decimal("NaN")
        return Decimal(repr(v))
    if isinstance(v, str):
        try:
            return Decimal(v.strip())
        except InvalidOperation:
            return None
    return None


def _coerce_number(key: str, v: Any, integer: bool, out: NormalizedInput) -> Optional[Any]:
    d = _to_decimal(v)
    if d is None:
        out.add(key, INVALID_TYPE, f"'{key}' must be a number, got {v!r}.")
        return None
    if d.is_nan() or d.is_infinite():
        out.add(key, NOT_FINITE, f"'{key}' must be a finite number, got {v!r}.")
        return None
    if d < 0:
        out.add(key, NEGATIVE_VALUE, f"'{key}' cannot be negative, got {v!r}.")
        return None
    if integer:
        if d != d.to_integral_value():
            out.add(key, NOT_INTEGER, f"'{key}' must be a whole number, got {v!r}.")
            return None
        return int(d)
    return float(d)


def _coerce_date(key: str, v: Any, out: NormalizedInput) -> Optional[date]:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            pass
    out.add(key, INVALID_DATE, f"'{key}' must be an ISO date (YYYY-MM-DD), got {v!r}.")
    return None


def _coerce_field(f: Dict[str, Any], v: Any, out: NormalizedInput) -> Any:
    key, ftype = f["key"], f["type"]
    if ftype == "integer":
        return _coerce_number(key, v, True, out)
    if ftype == "currency":
        return _coerce_number(key, v, False, out)
    if ftype == "boolean":
        if isinstance(v, bool):
            return v
        out.add(key, INVALID_TYPE, f"'{key}' must be true or false, got {v!r}.")
        return None
    if ftype == "enum":
        allowed = [o["value"] for o in f["options"]]
        val = v.strip().upper() if isinstance(v, str) else v
        allowed_upper = {a.upper(): a for a in allowed}
        if isinstance(val, str) and val in allowed_upper:
            return allowed_upper[val]
        out.add(key, INVALID_OPTION, f"'{key}' must be one of {allowed}, got {v!r}.")
        return None
    if ftype == "multi_enum":
        allowed = {o["value"] for o in f["options"]}
        if not isinstance(v, list):
            out.add(key, INVALID_TYPE, f"'{key}' must be a list of options, got {v!r}.")
            return None
        seen: List[str] = []
        for item in v:
            if not isinstance(item, str) or item not in allowed:
                out.add(key, INVALID_OPTION, f"'{key}' contains an invalid option {item!r}; allowed {sorted(allowed)}.")
                return None
            if item in seen:
                out.add(key, DUPLICATE_OPTION, f"'{key}' lists {item!r} more than once.")
                return None
            seen.append(item)
        return seen
    if ftype == "text_list":
        items = v.splitlines() if isinstance(v, str) else v
        if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
            out.add(key, INVALID_TYPE, f"'{key}' must be a list of text entries, got {v!r}.")
            return None
        cleaned: List[str] = []
        lowered = set()
        for i in items:
            s = " ".join(i.split())
            if s and s.lower() not in lowered:
                lowered.add(s.lower())
                cleaned.append(s)
        return cleaned
    if ftype == "date":
        return _coerce_date(key, v, out)
    out.add(key, INVALID_TYPE, f"Unsupported field type {ftype!r} for '{key}'.")
    return None


def _is_positive(ftype: str, value: Any) -> bool:
    if value is None:
        return False
    if ftype in ("integer", "currency"):
        return value > 0
    if ftype == "boolean":
        return value is True
    if ftype == "enum":
        return value not in ("NOT_ACCREDITED",)
    if ftype in ("multi_enum", "text_list"):
        return len(value) > 0
    return False


def normalize_subcriterion(
    parameter_code: str,
    subcriterion_code: str,
    raw: Any,
    strict: bool = False,
    fallback_activity_date: Optional[date] = None,
) -> NormalizedInput:
    """
    Normalises raw subcriterion inputs.

    strict=True  -> unknown keys are errors (API writes).
    strict=False -> unknown keys are ignored (engine reads of historical data).
    fallback_activity_date -> single-date claim used when the period fields are absent
                              (legacy parameter-level activity_date).
    """
    out = NormalizedInput()
    schema = get_subcriterion_schema(parameter_code, subcriterion_code)
    if schema is None:
        out.add(subcriterion_code, UNKNOWN_FIELD, f"Unknown subcriterion {subcriterion_code} for {parameter_code}.")
        return out
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        out.add(subcriterion_code, INVALID_TYPE, f"Inputs for {subcriterion_code} must be an object, got {type(raw).__name__}.")
        return out

    fields = {f["key"]: f for f in schema["fields"]}
    if strict:
        for k in raw:
            if k not in fields:
                out.add(k, UNKNOWN_FIELD, f"'{k}' is not a field of {subcriterion_code}. Allowed: {sorted(fields)}.")

    for key, f in fields.items():
        v = raw.get(key)
        if _is_blank(v) or (f["type"] in ("multi_enum", "text_list") and v == []):
            out.values[key] = [] if f["type"] in ("multi_enum", "text_list") else None
            continue
        out.values[key] = _coerce_field(f, v, out)

    # Cross-field bound: numerator must not exceed its denominator
    for key, f in fields.items():
        other = f.get("max_field")
        if other and out.values.get(key) is not None and out.values.get(other) is not None:
            if out.values[key] > out.values[other]:
                out.add(key, EXCEEDS_FIELD, f"'{key}' ({out.values[key]}) cannot exceed '{other}' ({out.values[other]}).")
                out.values[key] = None

    out.positive_claim = any(
        _is_positive(f["type"], out.values.get(k)) for k, f in fields.items() if f["type"] != "date"
    )

    if schema.get("period_bound"):
        start = out.values.get(PERIOD_START_KEY)
        end = out.values.get(PERIOD_END_KEY)
        if start is None and end is None and fallback_activity_date is not None:
            start = end = fallback_activity_date
        if out.positive_claim:
            if start is None or end is None:
                missing = [k for k, v in ((PERIOD_START_KEY, start), (PERIOD_END_KEY, end)) if v is None]
                if not any(e["field"] in missing and e["code"] == INVALID_DATE for e in out.errors):
                    for k in missing:
                        out.add(k, PERIOD_DATE_REQUIRED,
                                f"{subcriterion_code} claims activity bounded to the assessment period; '{k}' is required.")
            elif start > end:
                out.add(PERIOD_START_KEY, PERIOD_ORDER, f"'{PERIOD_START_KEY}' ({start}) is after '{PERIOD_END_KEY}' ({end}).")
            else:
                out.period = {"start": start.isoformat(), "end": end.isoformat()}
                if start < PERIOD_START or end > PERIOD_END:
                    out.out_of_period = True
                    out.period["eligible"] = False
                    out.period["reason"] = (
                        f"Claimed activity dates {start}..{end} fall outside the assessment period "
                        f"{ASSESSMENT_PERIOD_START}..{ASSESSMENT_PERIOD_END}."
                    )
                else:
                    out.period["eligible"] = True
    return out


def period_errors_for_api(norm: NormalizedInput) -> List[Dict[str, Any]]:
    """For API writes an out-of-period date is a validation error (the engine treats it as ineligible)."""
    errors = list(norm.errors)
    if norm.out_of_period:
        errors.append({"field": PERIOD_START_KEY, "code": OUT_OF_PERIOD, "message": norm.period["reason"]})
    return errors


def required_field_errors(parameter_code: str, subcriterion_code: str, raw: Any) -> List[Dict[str, Any]]:
    """Completeness check used at submission: every non-boolean, non-date field must be answered."""
    schema = get_subcriterion_schema(parameter_code, subcriterion_code) or {"fields": []}
    raw = raw if isinstance(raw, dict) else {}
    errs = []
    for f in schema["fields"]:
        if f["type"] in ("boolean", "date", "multi_enum", "text_list"):
            continue
        if _is_blank(raw.get(f["key"])):
            errs.append({"field": f["key"], "code": REQUIRED_FIELD,
                         "message": f"{subcriterion_code}: '{f['label']}' must be answered before submission (enter 0 if none)."})
    return errs
