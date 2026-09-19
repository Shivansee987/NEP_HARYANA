"""
NEP Excellence Awards 2026 - College Domain Validators
Enforces strict parameter boundaries, percentage ranges, count quantities,
and Phase 5D temporal period compliance without silent coercion.
"""
from datetime import date
from typing import Any, Dict, Optional

from apps.evidence.period_validator import AssessmentPeriodValidator
from apps.scoring.evaluators.counts import validate_count_quantity
from .registry import (
    COLLEGE_FRAMEWORK_CODE,
    get_college_parameter,
    get_college_subcriteria,
    validate_college_parameter_code,
)


class CollegeValidationError(Exception):
    """Base exception for College domain validation errors."""
    def __init__(self, message: str, code: str = "INVALID_PARAMETER_INPUT"):
        super().__init__(message)
        self.message = message
        self.code = code


class CollegeNotAuthorizedError(CollegeValidationError):
    """Raised when an actor lacks authority to access or mutate a college or assessment."""
    def __init__(self, message: str, code: str = "COLLEGE_NOT_AUTHORIZED"):
        super().__init__(message, code=code)


class InvalidStateTransitionError(CollegeValidationError):
    """Raised when an invalid lifecycle state transition is attempted."""
    def __init__(self, message: str, code: str = "INVALID_LIFECYCLE_TRANSITION"):
        super().__init__(message, code=code)


class ScoringBlockedError(CollegeValidationError):
    """Raised when scoring evaluation is blocked by unverified evidence or rule voids."""
    def __init__(self, message: str, code: str = "SCORING_BLOCKED"):
        super().__init__(message, code=code)


class EvidenceNotReadyError(CollegeValidationError):
    """Raised when submission or scoring requires evidence that is not ready."""
    def __init__(self, message: str, code: str = "EVIDENCE_NOT_READY"):
        super().__init__(message, code=code)


class ConcurrentUpdateError(CollegeValidationError):
    """Raised when concurrent mutation conflicts on an assessment."""
    def __init__(self, message: str, code: str = "CONCURRENT_UPDATE"):
        super().__init__(message, code=code)


class ReviewNotAuthorizedError(CollegeNotAuthorizedError):
    """Raised when an actor is not authorized to review a College assessment."""
    def __init__(self, message: str = "Reviewer is not authorized for this assessment.", code: str = "REVIEW_NOT_AUTHORIZED"):
        super().__init__(message, code=code)


class CertificationNotAuthorizedError(CollegeNotAuthorizedError):
    """Raised when an actor lacks authority to certify a College assessment."""
    def __init__(self, message: str = "Actor lacks authority to certify College assessments.", code: str = "CERTIFICATION_NOT_AUTHORIZED"):
        super().__init__(message, code=code)


class InvalidReviewStateError(InvalidStateTransitionError):
    """Raised when a review action is attempted on an incompatible assessment lifecycle state."""
    def __init__(self, message: str, code: str = "INVALID_REVIEW_STATE"):
        super().__init__(message, code=code)


class AssessmentNotReadyError(CollegeValidationError):
    """Raised when an assessment does not meet criteria for review completion or submission."""
    def __init__(self, message: str, code: str = "ASSESSMENT_NOT_READY"):
        super().__init__(message, code=code)


class ScoringNotEvaluatedError(CollegeValidationError):
    """Raised when certification requires an authoritative scoring evaluation that has not yet occurred."""
    def __init__(self, message: str = "Scoring evaluation has not been performed.", code: str = "SCORING_NOT_EVALUATED"):
        super().__init__(message, code=code)


class CertificationBlockedError(CollegeValidationError):
    """Raised when certification cannot proceed due to statutory, evidence, or scoring validation blocks."""
    def __init__(self, message: str, code: str = "CERTIFICATION_BLOCKED"):
        super().__init__(message, code=code)


class AssessmentAlreadyCertifiedError(CollegeValidationError):
    """Raised when an assessment that has already been certified is targeted for duplicate certification or state modification."""
    def __init__(self, message: str = "Assessment is already certified and immutable.", code: str = "ASSESSMENT_ALREADY_CERTIFIED"):
        super().__init__(message, code=code)


class AssessmentLockedError(CollegeValidationError):
    """Raised when a mutation is attempted on an immutable/certified assessment."""
    def __init__(self, message: str = "Assessment is locked against modifications.", code: str = "ASSESSMENT_LOCKED"):
        super().__init__(message, code=code)


class ReviewConflictError(CollegeValidationError):
    """Raised when a reviewer has an institutional conflict of interest."""
    def __init__(self, message: str = "Conflict of interest: Reviewer cannot review their own institution.", code: str = "REVIEW_CONFLICT"):
        super().__init__(message, code=code)


class ConcurrentReviewConflictError(ConcurrentUpdateError):
    """Raised when concurrent review or certification transactions conflict."""
    def __init__(self, message: str = "Concurrent review action conflict detected.", code: str = "CONCURRENT_REVIEW_CONFLICT"):
        super().__init__(message, code=code)


class FrameworkMismatchError(CollegeValidationError):
    """Raised when an action or document violates College framework isolation."""
    def __init__(self, message: str, code: str = "FRAMEWORK_MISMATCH"):
        super().__init__(message, code=code)


class InvalidFrameworkError(CollegeValidationError):
    """Raised when framework is not COLLEGE_2026."""
    def __init__(self, message: str, code: str = "INVALID_FRAMEWORK"):
        super().__init__(message, code=code)


class InvalidInstitutionTypeError(CollegeValidationError):
    """Raised when institution type is not COLLEGE."""
    def __init__(self, message: str, code: str = "INVALID_INSTITUTION_TYPE"):
        super().__init__(message, code=code)


class ParameterNotFoundError(CollegeValidationError):
    """Raised when parameter code does not belong to C1–C22."""
    def __init__(self, message: str, code: str = "INVALID_PARAMETER"):
        super().__init__(message, code=code)


class SubcriterionNotFoundError(CollegeValidationError):
    """Raised when subcriterion code does not belong to the parameter."""
    def __init__(self, message: str, code: str = "INVALID_SUBCRITERION"):
        super().__init__(message, code=code)


class TemporalWindowViolationError(CollegeValidationError):
    """Raised when an activity date violates the assessment period."""
    def __init__(self, message: str, code: str = "INVALID_ASSESSMENT_PERIOD"):
        super().__init__(message, code=code)


def validate_framework_code(framework: str) -> str:
    """Validates that framework is strictly COLLEGE_2026."""
    if not framework or not isinstance(framework, str):
        raise InvalidFrameworkError("Framework identifier is required.")
    clean = framework.strip().upper()
    if clean not in (COLLEGE_FRAMEWORK_CODE, "COLLEGE"):
        raise InvalidFrameworkError(
            f"Framework mismatch: '{framework}' is not a valid College framework. "
            f"Expected '{COLLEGE_FRAMEWORK_CODE}'."
        )
    return COLLEGE_FRAMEWORK_CODE


def validate_institution_type(institution_type: str) -> str:
    """Validates that institution type is strictly COLLEGE."""
    if not institution_type or not isinstance(institution_type, str):
        raise InvalidInstitutionTypeError("Institution type is required.")
    clean = institution_type.strip().upper()
    if clean != "COLLEGE":
        raise InvalidInstitutionTypeError(
            f"Institution type mismatch: '{institution_type}' cannot undergo College assessment. "
            f"Expected 'COLLEGE'."
        )
    return "COLLEGE"


def validate_parameter(parameter_code: str) -> str:
    """Validates that parameter code belongs to C1–C22."""
    if not validate_college_parameter_code(parameter_code):
        raise ParameterNotFoundError(
            f"Parameter '{parameter_code}' is not a valid College parameter. "
            f"College framework only accepts C1 through C22."
        )
    return parameter_code.strip().upper()


def validate_subcriterion(parameter_code: str, subcriterion_code: Optional[str] = None, expected_parameter: Optional[str] = None) -> str:
    """Validates that subcriterion belongs to the specified College parameter."""
    if expected_parameter is not None:
        param_clean = validate_parameter(expected_parameter)
        sub_code = parameter_code
    elif subcriterion_code is not None:
        param_clean = validate_parameter(parameter_code)
        sub_code = subcriterion_code
    else:
        raise SubcriterionNotFoundError("Subcriterion code is required.")

    if not sub_code or not isinstance(sub_code, str):
        raise SubcriterionNotFoundError("Subcriterion code is required.")
    sub_clean = sub_code.strip()
    valid_subcriteria = get_college_subcriteria(param_clean)
    canonical_map = {k.upper(): k for k in valid_subcriteria.keys()}
    if sub_clean.upper() not in canonical_map:
        raise SubcriterionNotFoundError(
            f"Subcriterion '{sub_code}' does not belong to College parameter '{param_clean}'. "
            f"Valid subcriteria: {list(valid_subcriteria.keys())}."
        )
    return canonical_map[sub_clean.upper()]


def validate_percentage(value: Any, field_name: str = "percentage", label: Optional[str] = None) -> float:
    """Validates that value is a strictly valid percentage between 0.0 and 100.0."""
    name = label or field_name
    if value is None:
        raise CollegeValidationError(f"Field '{name}' cannot be None.", code="INVALID_PARAMETER_INPUT")
    try:
        f_val = float(value)
    except (ValueError, TypeError):
        raise CollegeValidationError(f"Field '{name}' must be a numerical percentage, got '{value}'.", code="INVALID_PARAMETER_INPUT")
    if f_val < 0.0 or f_val > 100.0:
        raise CollegeValidationError(
            f"Field '{name}' value {f_val}% is outside allowable percentage bounds [0.0, 100.0].",
            code="INVALID_PARAMETER_INPUT"
        )
    return f_val


def validate_count(value: Any, field_name: str = "count", label: Optional[str] = None) -> int:
    """Validates that value is a non-negative integer count."""
    name = label or field_name
    if value is None:
        raise CollegeValidationError(f"Field '{name}' cannot be None.", code="INVALID_PARAMETER_INPUT")
    try:
        if isinstance(value, str) and '.' in value:
            raise ValueError()
        i_val = int(value)
    except (ValueError, TypeError):
        raise CollegeValidationError(f"Field '{name}' must be a whole non-negative integer, got '{value}'.", code="INVALID_PARAMETER_INPUT")
    if i_val < 0:
        raise CollegeValidationError(f"Field '{name}' cannot be negative, got {i_val}.", code="INVALID_PARAMETER_INPUT")
    return i_val


def validate_currency_amount(value: Any, field_name: str = "amount", label: Optional[str] = None) -> float:
    """Validates that value is a non-negative monetary amount."""
    name = label or field_name
    if value is None:
        raise CollegeValidationError(f"Field '{name}' cannot be None.", code="INVALID_PARAMETER_INPUT")
    try:
        f_val = float(value)
    except (ValueError, TypeError):
        raise CollegeValidationError(f"Field '{name}' must be a numerical amount, got '{value}'.", code="INVALID_PARAMETER_INPUT")
    if f_val < 0.0:
        raise CollegeValidationError(f"Field '{name}' cannot be negative, got {f_val}.", code="INVALID_PARAMETER_INPUT")
    return f_val


def validate_temporal_activity_date(
    activity_date: Optional[date],
    parameter_code: str,
) -> None:
    """
    Validates temporal compliance for date-sensitive parameters using Phase 5D AssessmentPeriodValidator.
    Strictly enforces 2025-07-01 to 2026-06-30 window.
    """
    param_def = get_college_parameter(parameter_code)
    period_rule = param_def.get("period_rule")
    is_sensitive = AssessmentPeriodValidator.is_period_sensitive(period_rule)

    valid, msg, code = AssessmentPeriodValidator.validate_activity_date(
        activity_date=activity_date,
        is_period_sensitive=is_sensitive,
    )
    if not valid:
        raise CollegeValidationError(
            f"Temporal validation failed for parameter {parameter_code}: {msg} (Deficiency: {code})",
            code="INVALID_ASSESSMENT_PERIOD"
        )
