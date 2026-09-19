"""
NEP Excellence Awards 2026 - University Domain Validators
Enforces strict parameter boundaries, percentage ranges, count quantities,
and Phase 5D temporal period compliance without silent coercion.
"""
from datetime import date
from typing import Any, Dict, Optional

from apps.evidence.period_validator import AssessmentPeriodValidator
from apps.scoring.evaluators.counts import validate_count_quantity
from .registry import (
    UNIVERSITY_FRAMEWORK_CODE,
    get_university_parameter,
    get_university_subcriteria,
    validate_university_parameter_code,
)


class UniversityValidationError(Exception):
    """Base exception for University domain validation errors."""
    def __init__(self, message: str, code: str = "INVALID_PARAMETER_INPUT"):
        super().__init__(message)
        self.message = message
        self.code = code


class UniversityNotAuthorizedError(UniversityValidationError):
    """Raised when an actor lacks authority to access or mutate a university or assessment."""
    def __init__(self, message: str, code: str = "UNIVERSITY_NOT_AUTHORIZED"):
        super().__init__(message, code=code)


class InvalidStateTransitionError(UniversityValidationError):
    """Raised when an invalid lifecycle state transition is attempted."""
    def __init__(self, message: str, code: str = "INVALID_LIFECYCLE_TRANSITION"):
        super().__init__(message, code=code)


class ScoringBlockedError(UniversityValidationError):
    """Raised when scoring evaluation is blocked by unverified evidence or rule voids."""
    def __init__(self, message: str, code: str = "SCORING_BLOCKED"):
        super().__init__(message, code=code)


class EvidenceNotReadyError(UniversityValidationError):
    """Raised when submission or scoring requires evidence that is not ready."""
    def __init__(self, message: str, code: str = "EVIDENCE_NOT_READY"):
        super().__init__(message, code=code)


class ConcurrentUpdateError(UniversityValidationError):
    """Raised when concurrent mutation conflicts on an assessment."""
    def __init__(self, message: str, code: str = "CONCURRENT_UPDATE"):
        super().__init__(message, code=code)


class ReviewNotAuthorizedError(UniversityNotAuthorizedError):
    """Raised when an actor is not authorized to review a University assessment."""
    def __init__(self, message: str = "Reviewer is not authorized for this assessment.", code: str = "REVIEW_NOT_AUTHORIZED"):
        super().__init__(message, code=code)


class CertificationNotAuthorizedError(UniversityNotAuthorizedError):
    """Raised when an actor lacks authority to certify an assessment."""
    def __init__(self, message: str = "Actor lacks authority to certify University assessments.", code: str = "CERTIFICATION_NOT_AUTHORIZED"):
        super().__init__(message, code=code)


class InvalidReviewStateError(InvalidStateTransitionError):
    """Raised when a review action is attempted on an incompatible assessment lifecycle state."""
    def __init__(self, message: str, code: str = "INVALID_REVIEW_STATE"):
        super().__init__(message, code=code)


class AssessmentNotReadyError(UniversityValidationError):
    """Raised when an assessment does not meet criteria for review completion or submission."""
    def __init__(self, message: str, code: str = "ASSESSMENT_NOT_READY"):
        super().__init__(message, code=code)


class ScoringNotEvaluatedError(UniversityValidationError):
    """Raised when certification or review completion requires an authoritative scoring evaluation that has not yet occurred."""
    def __init__(self, message: str = "Scoring evaluation has not been performed.", code: str = "SCORING_NOT_EVALUATED"):
        super().__init__(message, code=code)


class CertificationBlockedError(UniversityValidationError):
    """Raised when certification cannot proceed due to statutory, evidence, or scoring validation blocks."""
    def __init__(self, message: str, code: str = "CERTIFICATION_BLOCKED"):
        super().__init__(message, code=code)


class AssessmentAlreadyCertifiedError(UniversityValidationError):
    """Raised when an assessment that has already been certified is targeted for duplicate certification or state modification."""
    def __init__(self, message: str = "Assessment is already certified and immutable.", code: str = "ASSESSMENT_ALREADY_CERTIFIED"):
        super().__init__(message, code=code)


class AssessmentLockedError(UniversityValidationError):
    """Raised when a mutation is attempted on an immutable/certified assessment."""
    def __init__(self, message: str = "Assessment is locked against modifications.", code: str = "ASSESSMENT_LOCKED"):
        super().__init__(message, code=code)


class ReviewConflictError(UniversityValidationError):
    """Raised when a reviewer has an institutional conflict of interest."""
    def __init__(self, message: str = "Conflict of interest: Reviewer cannot review their own institution.", code: str = "REVIEW_CONFLICT"):
        super().__init__(message, code=code)


class ConcurrentReviewConflictError(ConcurrentUpdateError):
    """Raised when concurrent review or certification transactions conflict."""
    def __init__(self, message: str = "Concurrent review action conflict detected.", code: str = "CONCURRENT_REVIEW_CONFLICT"):
        super().__init__(message, code=code)


class FrameworkMismatchError(UniversityValidationError):
    """Raised when an action or document violates University framework isolation."""
    def __init__(self, message: str, code: str = "FRAMEWORK_MISMATCH"):
        super().__init__(message, code=code)


def validate_framework_code(framework: str) -> str:
    """Validates that framework is strictly UNIVERSITY_2026."""
    if not framework or not isinstance(framework, str):
        raise UniversityValidationError("Framework identifier is required.", code="INVALID_FRAMEWORK")
    clean = framework.strip().upper()
    if clean not in (UNIVERSITY_FRAMEWORK_CODE, "UNIVERSITY"):
        raise UniversityValidationError(
            f"Framework mismatch: '{framework}' is not a valid University framework. "
            f"Expected '{UNIVERSITY_FRAMEWORK_CODE}'.",
            code="INVALID_FRAMEWORK"
        )
    return UNIVERSITY_FRAMEWORK_CODE


def validate_institution_type(institution_type: str) -> str:
    """Validates that institution type is strictly UNIVERSITY."""
    if not institution_type or not isinstance(institution_type, str):
        raise UniversityValidationError("Institution type is required.", code="INVALID_INSTITUTION_TYPE")
    clean = institution_type.strip().upper()
    if clean != "UNIVERSITY":
        raise UniversityValidationError(
            f"Institution type mismatch: '{institution_type}' cannot undergo University assessment. "
            f"Expected 'UNIVERSITY'.",
            code="INVALID_INSTITUTION_TYPE"
        )
    return "UNIVERSITY"


def validate_parameter(parameter_code: str) -> str:
    """Validates that parameter code belongs to U1–U20."""
    if not validate_university_parameter_code(parameter_code):
        raise UniversityValidationError(
            f"Parameter '{parameter_code}' is not a valid University parameter. "
            f"University framework only accepts U1 through U20.",
            code="INVALID_PARAMETER"
        )
    return parameter_code.strip().upper()


def validate_subcriterion(parameter_code: str, subcriterion_code: str) -> str:
    """Validates that subcriterion belongs to the specified University parameter."""
    param_clean = validate_parameter(parameter_code)
    if not subcriterion_code or not isinstance(subcriterion_code, str):
        raise UniversityValidationError("Subcriterion code is required.", code="INVALID_SUBCRITERION")
    sub_clean = subcriterion_code.strip().upper()
    valid_subcriteria = get_university_subcriteria(param_clean)
    if sub_clean not in valid_subcriteria:
        raise UniversityValidationError(
            f"Subcriterion '{subcriterion_code}' does not belong to University parameter '{param_clean}'. "
            f"Valid subcriteria: {list(valid_subcriteria.keys())}.",
            code="INVALID_SUBCRITERION"
        )
    return sub_clean


def validate_percentage(value: Any, field_name: str = "percentage") -> float:
    """Validates that value is a strictly valid percentage between 0.0 and 100.0."""
    if value is None:
        raise UniversityValidationError(f"Field '{field_name}' cannot be None.", code="INVALID_PARAMETER_INPUT")
    try:
        f_val = float(value)
    except (ValueError, TypeError):
        raise UniversityValidationError(f"Field '{field_name}' must be a numerical percentage, got '{value}'.", code="INVALID_PARAMETER_INPUT")
    if f_val < 0.0 or f_val > 100.0:
        raise UniversityValidationError(
            f"Field '{field_name}' value {f_val}% is outside allowable percentage bounds [0.0, 100.0].",
            code="INVALID_PARAMETER_INPUT"
        )
    return f_val


def validate_count(value: Any, field_name: str = "count") -> int:
    """Validates that value is a non-negative integer count."""
    if value is None:
        raise UniversityValidationError(f"Field '{field_name}' cannot be None.", code="INVALID_PARAMETER_INPUT")
    try:
        # Strict int check — avoid float truncation if string has decimals
        if isinstance(value, str) and '.' in value:
            raise ValueError()
        i_val = int(value)
    except (ValueError, TypeError):
        raise UniversityValidationError(f"Field '{field_name}' must be a whole non-negative integer, got '{value}'.", code="INVALID_PARAMETER_INPUT")
    if i_val < 0:
        raise UniversityValidationError(f"Field '{field_name}' cannot be negative, got {i_val}.", code="INVALID_PARAMETER_INPUT")
    return i_val


def validate_currency_amount(value: Any, field_name: str = "amount") -> float:
    """Validates that value is a non-negative monetary amount."""
    if value is None:
        raise UniversityValidationError(f"Field '{field_name}' cannot be None.", code="INVALID_PARAMETER_INPUT")
    try:
        f_val = float(value)
    except (ValueError, TypeError):
        raise UniversityValidationError(f"Field '{field_name}' must be a numerical amount, got '{value}'.", code="INVALID_PARAMETER_INPUT")
    if f_val < 0.0:
        raise UniversityValidationError(f"Field '{field_name}' cannot be negative, got {f_val}.", code="INVALID_PARAMETER_INPUT")
    return f_val


def validate_temporal_activity_date(
    activity_date: Optional[date],
    parameter_code: str,
) -> None:
    """
    Validates temporal compliance for date-sensitive parameters using Phase 5D AssessmentPeriodValidator.
    Strictly enforces 2025-07-01 to 2026-06-30 window.
    """
    param_def = get_university_parameter(parameter_code)
    period_rule = param_def.get("period_rule")
    is_sensitive = AssessmentPeriodValidator.is_period_sensitive(period_rule)

    valid, msg, code = AssessmentPeriodValidator.validate_activity_date(
        activity_date=activity_date,
        is_period_sensitive=is_sensitive,
    )
    if not valid:
        raise UniversityValidationError(
            f"Temporal validation failed for parameter {parameter_code}: {msg} (Deficiency: {code})",
            code="INVALID_ASSESSMENT_PERIOD"
        )
