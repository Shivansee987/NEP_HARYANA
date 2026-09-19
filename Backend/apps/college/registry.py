"""
NEP Excellence Awards 2026 - Authoritative College Framework Registry
Exposes exactly C1–C22 parameter definitions, maximum marks, subcriteria,
and evidence requirements directly from the approved parameter specification.
Scoring calculations remain strictly inside the frozen scoring engine.
"""
from typing import Any, Dict, List, Optional
from apps.scoring.enums import FrameworkType
from apps.scoring.rules.definitions import COLLEGE_PARAMETERS


COLLEGE_FRAMEWORK_CODE = "COLLEGE_2026"
COLLEGE_TOTAL_MARKS = 100.0
COLLEGE_PARAMETER_CODES = [f"C{i}" for i in range(1, 23)]


def get_college_framework_info() -> Dict[str, Any]:
    """Returns high-level metadata for the College framework."""
    return {
        "framework_code": COLLEGE_FRAMEWORK_CODE,
        "framework_name": "NEP Excellence Awards 2026 - College Framework",
        "total_maximum_marks": COLLEGE_TOTAL_MARKS,
        "parameter_count": len(COLLEGE_PARAMETER_CODES),
        "parameter_codes": list(COLLEGE_PARAMETER_CODES),
        "statutory_assessment_period": {
            "start_date": "2025-07-01",
            "end_date": "2026-06-30",
            "academic_year": "2025-26",
        },
    }


def get_college_parameters() -> Dict[str, Dict[str, Any]]:
    """
    Returns the authoritative registry of all 22 College parameters (C1–C22).
    Derived strictly from the frozen parameter definitions.
    """
    return COLLEGE_PARAMETERS


def get_college_parameter(parameter_code: str) -> Dict[str, Any]:
    """
    Retrieves metadata for a specific College parameter.
    Raises KeyError if parameter code is not in C1–C22.
    """
    clean_code = parameter_code.strip().upper()
    if clean_code not in COLLEGE_PARAMETERS:
        raise KeyError(
            f"Invalid College parameter code '{parameter_code}'. "
            f"Authoritative College framework accepts only C1 through C22."
        )
    return COLLEGE_PARAMETERS[clean_code]


def validate_college_parameter_code(parameter_code: str) -> bool:
    """Checks whether a parameter code belongs to C1–C22."""
    if not parameter_code or not isinstance(parameter_code, str):
        return False
    return parameter_code.strip().upper() in COLLEGE_PARAMETERS


def get_college_subcriteria(parameter_code: str) -> Dict[str, Dict[str, Any]]:
    """Returns all authoritative subcriteria belonging to the given College parameter."""
    param_def = get_college_parameter(parameter_code)
    return param_def.get("subcriteria", {})


def get_all_college_subcriteria() -> Dict[str, Dict[str, Any]]:
    """Returns a flattened map of all subcriteria codes across C1–C22."""
    subcriteria_map = {}
    for param_code, param_def in COLLEGE_PARAMETERS.items():
        for sub_code, sub_def in param_def.get("subcriteria", {}).items():
            subcriteria_map[sub_code] = {
                **sub_def,
                "parent_parameter": param_code,
            }
    return subcriteria_map


def get_parameter_evidence_requirements(parameter_code: str) -> Dict[str, List[str]]:
    """Returns mandatory and allowed evidence document types for a parameter."""
    param_def = get_college_parameter(parameter_code)
    return {
        "mandatory": param_def.get("mandatory_evidence", []),
        "allowed": param_def.get("allowed_evidence", []),
    }
