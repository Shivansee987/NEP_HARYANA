"""
NEP Excellence Awards 2026 - Scoring Domain Models & Execution Types
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid

from .enums import (
    CertificationStatus,
    DoubleCountingRule,
    EvaluationType,
    EvidenceState,
    FrameworkType,
    GatingStatus,
    InstitutionType,
    PeriodRule,
    ResolutionStatus,
    ThresholdOperator,
)


@dataclass
class AssessmentPeriod:
    start_date: date = field(default_factory=lambda: date(2025, 7, 1))
    end_date: date = field(default_factory=lambda: date(2026, 6, 30))
    academic_year: str = "2025-26"


@dataclass
class AssessmentContext:
    assessment_id: str
    institution_id: str
    institution_type: InstitutionType
    framework: FrameworkType
    assessment_period: AssessmentPeriod = field(default_factory=AssessmentPeriod)
    is_active: bool = True
    lifecycle_status: str = "SUBMITTED"  # SUBMITTED, UNDER_REVIEW, RECALCULATION_REQUESTED, etc.


@dataclass
class EvidenceDocument:
    document_id: str
    document_type: str
    status: EvidenceState = EvidenceState.EVIDENCE_PENDING
    verified_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    file_checksum: Optional[str] = None
    academic_year: Optional[str] = None
    framework: Optional[str] = None
    parameter_id: Optional[str] = None
    subcriterion_id: Optional[str] = None
    association_verified: Optional[bool] = None


@dataclass
class AssetEntity:
    entity_id: str
    entity_type: str  # PATENT, STARTUP, MOU, WORKSHOP, EVENT, PROGRAMME
    identifier_key: str  # e.g., patent app number, startup CIN, MOU partner+date
    date_of_record: Optional[date] = None
    title: Optional[str] = None


@dataclass
class SubcriterionInput:
    subcriterion_code: str
    raw_inputs: Dict[str, Any] = field(default_factory=dict)
    evidence_docs: List[EvidenceDocument] = field(default_factory=list)
    entities: List[AssetEntity] = field(default_factory=list)
    activity_date: Optional[date] = None


@dataclass
class ParameterInput:
    parameter_code: str
    subcriteria_inputs: Dict[str, SubcriterionInput] = field(default_factory=dict)
    raw_inputs: Dict[str, Any] = field(default_factory=dict)
    evidence_docs: List[EvidenceDocument] = field(default_factory=list)


@dataclass
class AssessmentInput:
    context: AssessmentContext
    parameters: Dict[str, ParameterInput] = field(default_factory=dict)


@dataclass
class ReviewerAdjustment:
    subcriterion_code: str
    reviewer_id: str
    original_score: float
    adjusted_score: float
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    signature: Optional[str] = None


@dataclass
class SubcriterionResult:
    subcriterion_code: str
    raw_score: float
    evidence_gated_score: float
    review_adjusted_score: Optional[float]
    final_score: Optional[float]
    max_score: float
    resolution_status: ResolutionStatus
    gating_status: GatingStatus
    matched_threshold: Optional[Dict[str, Any]] = None
    trace: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParameterResult:
    parameter_code: str
    max_marks: float
    raw_score: float
    evidence_gated_score: float
    review_adjusted_score: Optional[float]
    final_score: Optional[float]
    resolution_status: ResolutionStatus
    aggregation_strategy: EvaluationType
    subcriteria_results: Dict[str, SubcriterionResult] = field(default_factory=dict)
    trace: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        conflicts = []
        for sub_res in self.subcriteria_results.values():
            dc = sub_res.trace.get("double_counting", {})
            for d in dc.get("duplicates_detected", []):
                if d not in conflicts:
                    conflicts.append(d)
        if conflicts:
            self.trace["duplicates_detected"] = conflicts
            self.trace["double_counting_conflicts"] = conflicts


@dataclass
class FrameworkResult:
    framework: FrameworkType
    assessment_id: str
    institution_id: str
    calculation_id: str
    version_index: int
    timestamp: str
    raw_total: float
    evidence_gated_total: float
    final_certified_total: Optional[float]
    max_marks: float = 100.00
    certification_status: CertificationStatus = CertificationStatus.FINALIZABLE
    blocking_reasons: List[str] = field(default_factory=list)
    parameter_results: Dict[str, ParameterResult] = field(default_factory=dict)
    trace: Dict[str, Any] = field(default_factory=dict)
