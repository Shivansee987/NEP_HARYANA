"""
NEP Excellence Awards 2026 - Authoritative University Framework Registry
Exposes exactly U1–U20 parameter definitions, maximum marks, subcriteria,
and evidence requirements directly from the approved parameter specification.
Scoring calculations remain strictly inside the frozen scoring engine.
"""
from typing import Any, Dict, List, Optional
from apps.scoring.enums import FrameworkType
from apps.scoring.rules.definitions import UNIVERSITY_PARAMETERS


UNIVERSITY_FRAMEWORK_CODE = "UNIVERSITY_2026"
UNIVERSITY_TOTAL_MARKS = 100.0
UNIVERSITY_PARAMETER_CODES = [f"U{i}" for i in range(1, 21)]


def get_university_framework_info() -> Dict[str, Any]:
    """Returns high-level metadata for the University framework."""
    return {
        "framework_code": UNIVERSITY_FRAMEWORK_CODE,
        "framework_name": "NEP Excellence Awards 2026 - University Framework",
        "total_maximum_marks": UNIVERSITY_TOTAL_MARKS,
        "parameter_count": len(UNIVERSITY_PARAMETER_CODES),
        "parameter_codes": list(UNIVERSITY_PARAMETER_CODES),
        "statutory_assessment_period": {
            "start_date": "2025-07-01",
            "end_date": "2026-06-30",
            "academic_year": "2025-26",
        },
    }


def get_university_parameters() -> Dict[str, Dict[str, Any]]:
    """
    Returns the authoritative registry of all 20 University parameters (U1–U20).
    Derived strictly from the frozen parameter definitions.
    """
    return UNIVERSITY_PARAMETERS


def get_university_parameter(parameter_code: str) -> Dict[str, Any]:
    """
    Retrieves metadata for a specific University parameter.
    Raises KeyError if parameter code is not in U1–U20.
    """
    clean_code = parameter_code.strip().upper()
    if clean_code not in UNIVERSITY_PARAMETERS:
        raise KeyError(
            f"Invalid University parameter code '{parameter_code}'. "
            f"Authoritative University framework accepts only U1 through U20."
        )
    return UNIVERSITY_PARAMETERS[clean_code]


def validate_university_parameter_code(parameter_code: str) -> bool:
    """Checks whether a parameter code belongs to U1–U20."""
    if not parameter_code or not isinstance(parameter_code, str):
        return False
    return parameter_code.strip().upper() in UNIVERSITY_PARAMETERS


def get_university_subcriteria(parameter_code: str) -> Dict[str, Dict[str, Any]]:
    """Returns all authoritative subcriteria belonging to the given University parameter."""
    param_def = get_university_parameter(parameter_code)
    return param_def.get("subcriteria", {})


def get_all_university_subcriteria() -> Dict[str, Dict[str, Any]]:
    """Returns a flattened map of all subcriteria codes across U1–U20."""
    subcriteria_map = {}
    for param_code, param_def in UNIVERSITY_PARAMETERS.items():
        for sub_code, sub_def in param_def.get("subcriteria", {}).items():
            subcriteria_map[sub_code] = {
                **sub_def,
                "parent_parameter": param_code,
            }
    return subcriteria_map


def get_parameter_evidence_requirements(parameter_code: str) -> Dict[str, List[str]]:
    """Returns mandatory and allowed evidence document types for a parameter."""
    param_def = get_university_parameter(parameter_code)
    return {
        "mandatory": param_def.get("mandatory_evidence", []),
        "allowed": param_def.get("allowed_evidence", []),
    }
