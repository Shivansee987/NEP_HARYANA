"""
NEP Excellence Awards 2026 - Assessment Period Validation Service
Enforces strict temporal validity against the authoritative 2025-26 window:
July 1, 2025 through June 30, 2026 inclusive.
"""
from datetime import date
from typing import Optional, Tuple, Union, Dict, Any

from apps.scoring.domain import AssessmentPeriod
from apps.scoring.enums import PeriodRule
from .enums import CoverageDeficiencyCode


class AssessmentPeriodValidator:
    """
    Authoritative assessment period validator for NEP Excellence Awards 2026.
    Ensures documented activity dates fall within the statutory assessment window.
    """
    # Authoritative statutory boundaries for the 2026 awards
    DEFAULT_PERIOD = AssessmentPeriod()
    START_DATE: date = DEFAULT_PERIOD.start_date  # 2025-07-01
    END_DATE: date = DEFAULT_PERIOD.end_date      # 2026-06-30
    ACADEMIC_YEAR: str = DEFAULT_PERIOD.academic_year  # "2025-26"

    @classmethod
    def is_period_sensitive(cls, period_rule: Union[str, PeriodRule, None]) -> bool:
        """
        Determines whether a parameter/subcriterion is period-sensitive according
        to the frozen NEP scoring rules.
        """
        if period_rule is None:
            return True
        if isinstance(period_rule, PeriodRule):
            period_rule = period_rule.value
        return str(period_rule) != PeriodRule.PERIOD_INSENSITIVE.value

    @classmethod
    def validate_activity_date(
        cls,
        activity_date: Optional[date],
        is_period_sensitive: bool = True,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> Tuple[bool, Optional[str], Optional[CoverageDeficiencyCode]]:
        """
        Validates a single activity/document date against the assessment period.
        Returns (is_valid, human_reason, deficiency_code).

        Strict rules:
        - If NOT period-sensitive: Always valid (None date is accepted).
        - If period-sensitive:
          - None date is REJECTED with PERIOD_DATA_MISSING. Never falls back to HOI or upload timestamp!
          - activity_date < period_start: REJECTED with OUTSIDE_ASSESSMENT_PERIOD.
          - activity_date > period_end: REJECTED with OUTSIDE_ASSESSMENT_PERIOD.
          - period_start <= activity_date <= period_end: VALID.
        """
        if not is_period_sensitive:
            return True, None, None

        if activity_date is None:
            return (
                False,
                "Document activity date is missing for a period-sensitive criterion. "
                "Date cannot be inferred from upload or certification timestamps.",
                CoverageDeficiencyCode.PERIOD_DATA_MISSING,
            )

        start = period_start or cls.START_DATE
        end = period_end or cls.END_DATE

        if activity_date < start:
            return (
                False,
                f"Activity date {activity_date} is prior to assessment start {start}.",
                CoverageDeficiencyCode.OUTSIDE_ASSESSMENT_PERIOD,
            )

        if activity_date > end:
            return (
                False,
                f"Activity date {activity_date} is after assessment end {end}.",
                CoverageDeficiencyCode.OUTSIDE_ASSESSMENT_PERIOD,
            )

        return True, None, None

    @classmethod
    def validate_date_range(
        cls,
        start_date: Optional[date],
        end_date: Optional[date],
        is_period_sensitive: bool = True,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> Tuple[bool, Optional[str], Optional[CoverageDeficiencyCode]]:
        """
        Validates an activity date range (e.g., for multi-day workshops, programmes, MoUs).
        Enforces chronological consistency (start <= end) and window boundaries.
        """
        if start_date is not None and end_date is not None and start_date > end_date:
            return (
                False,
                f"Invalid date range: start date {start_date} cannot be after end date {end_date}.",
                CoverageDeficiencyCode.INVALID_DATE_RANGE,
            )

        if not is_period_sensitive:
            return True, None, None

        start = period_start or cls.START_DATE
        end = period_end or cls.END_DATE

        if start_date is None and end_date is None:
            return (
                False,
                "Required period date range is missing.",
                CoverageDeficiencyCode.PERIOD_DATA_MISSING,
            )

        # If start_date exists, it must fall within window
        if start_date is not None:
            if start_date < start or start_date > end:
                return (
                    False,
                    f"Range start date {start_date} falls outside assessment window {start} to {end}.",
                    CoverageDeficiencyCode.OUTSIDE_ASSESSMENT_PERIOD,
                )

        # If end_date exists, it must fall within window
        if end_date is not None:
            if end_date < start or end_date > end:
                return (
                    False,
                    f"Range end date {end_date} falls outside assessment window {start} to {end}.",
                    CoverageDeficiencyCode.OUTSIDE_ASSESSMENT_PERIOD,
                )

        return True, None, None

    @classmethod
    def validate_document_period(
        cls,
        document,
        is_period_sensitive: bool = True,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> Tuple[bool, Optional[str], Optional[CoverageDeficiencyCode]]:
        """
        Inspects an EvidenceDocument instance for period compliance.
        Checks document.document_date and any explicit range dates in metadata.
        Strictly does NOT inspect upload_timestamp or HOI dates.
        """
        # 1. Check if metadata contains a date range
        meta = getattr(document, 'metadata', {}) or {}
        raw_start = meta.get('start_date')
        raw_end = meta.get('end_date')

        range_start = None
        range_end = None
        if raw_start:
            try:
                range_start = date.fromisoformat(raw_start) if isinstance(raw_start, str) else raw_start
            except (ValueError, TypeError):
                pass
        if raw_end:
            try:
                range_end = date.fromisoformat(raw_end) if isinstance(raw_end, str) else raw_end
            except (ValueError, TypeError):
                pass

        if range_start is not None or range_end is not None:
            valid, reason, code = cls.validate_date_range(
                range_start, range_end, is_period_sensitive, period_start, period_end
            )
            if not valid:
                return valid, reason, code

        # 2. Check primary document_date
        doc_date = getattr(document, 'document_date', None)
        return cls.validate_activity_date(
            doc_date, is_period_sensitive, period_start, period_end
        )
