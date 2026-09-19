"""
NEP Excellence Awards 2026 - Assessment Period & Temporal Evaluator
"""
from datetime import date
from typing import Optional, Tuple, Union

from apps.scoring.domain import AssessmentPeriod
from apps.scoring.enums import PeriodRule


def validate_period(
    record_date: Optional[Union[date, str]],
    period_rule: PeriodRule,
    assessment_period: AssessmentPeriod,
    target_academic_year: Optional[str] = None,
    hoi_certification_date: Optional[Union[date, str]] = None
) -> Tuple[bool, str]:
    """
    Validates whether a record date or claimed academic year falls within the permitted temporal window.
    
    Returns:
        (is_valid, reason)
    """
    # 1. PERIOD_INSENSITIVE: Persistent policy, notified ordinance, or current curriculum
    if period_rule == PeriodRule.PERIOD_INSENSITIVE:
        return True, "Criterion is PERIOD_INSENSITIVE; valid if in force during assessment cycle."

    # Parse date if provided as string
    dt: Optional[date] = None
    if isinstance(record_date, str) and record_date:
        try:
            dt = date.fromisoformat(record_date)
        except ValueError:
            return False, f"Unparseable date string: {record_date}"
    elif isinstance(record_date, date):
        dt = record_date

    # 2. PERIOD_SENSITIVE: Standard academic year window (1 July 2025 to 30 June 2026)
    if period_rule == PeriodRule.PERIOD_SENSITIVE:
        if dt is not None:
            if assessment_period.start_date <= dt <= assessment_period.end_date:
                return True, f"Date {dt} is within assessment period [{assessment_period.start_date} to {assessment_period.end_date}]."
            else:
                return False, f"Date {dt} is OUTSIDE assessment period [{assessment_period.start_date} to {assessment_period.end_date}]."
        if target_academic_year is not None:
            if target_academic_year == assessment_period.academic_year:
                return True, f"Academic year {target_academic_year} matches assessment period {assessment_period.academic_year}."
            else:
                return False, f"Academic year {target_academic_year} does not match {assessment_period.academic_year}."
        # Omitted required date cannot fall back to HOI certification or manufacture eligibility
        if hoi_certification_date is not None:
            return False, "Omitted required activity/document date; HOI certification date cannot substitute for missing activity/document date."
        return False, "Omitted required activity/document date for PERIOD_SENSITIVE evaluation; fallback to HOI certification date is not permitted."

    # 3. MULTI_PERIOD: Distinct academic years for subcriteria (e.g. U4: 2024-25 and 2025-26)
    if period_rule == PeriodRule.MULTI_PERIOD:
        if target_academic_year:
            if target_academic_year in ["2024-25", "2025-26"]:
                return True, f"Academic year {target_academic_year} is authorized under MULTI_PERIOD framework."
            return False, f"Academic year {target_academic_year} is not authorized for MULTI_PERIOD evaluation."
        if dt:
            # Check 2024-25 (2024-07-01 to 2025-06-30) or 2025-26 (2025-07-01 to 2026-06-30)
            if date(2024, 7, 1) <= dt <= date(2026, 6, 30):
                return True, f"Date {dt} falls within MULTI_PERIOD scope [2024-07-01 to 2026-06-30]."
            return False, f"Date {dt} falls outside MULTI_PERIOD scope."
        if hoi_certification_date is not None:
            return False, "Omitted required date or academic year; HOI certification date cannot substitute for MULTI_PERIOD evaluation."
        return False, "Omitted required date or academic year for MULTI_PERIOD evaluation."

    # 4. REFERENCE_YEAR_DEPENDENT: Historical reference (e.g., C1: 2024-25 targets; U17: NIRF 2025 rank)
    if period_rule == PeriodRule.REFERENCE_YEAR_DEPENDENT:
        if target_academic_year:
            return True, f"Reference year {target_academic_year} evaluated according to parameter-specific anchor."
        if dt:
            return True, f"Date {dt} evaluated according to parameter-specific reference anchor."

    return True, "Period validation passed."
