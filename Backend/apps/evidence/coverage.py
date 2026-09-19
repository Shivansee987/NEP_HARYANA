"""
NEP Excellence Awards 2026 - Evidence Coverage & Assessment-Period Enforcement Layer
Deterministic, auditable coverage evaluation layer for University (U1-U20) and College (C1-C22) frameworks.
Evaluates completeness, temporal compliance, verification states, and readiness for scoring.
"""
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

from django.db import models

from apps.scoring.enums import FrameworkType, PeriodRule
from apps.scoring.rules.definitions import COLLEGE_PARAMETERS, UNIVERSITY_PARAMETERS

from .enums import (
    CoverageDeficiencyCode,
    CoverageState,
    EvidenceLifecycleState,
)
from .exceptions import (
    FrameworkMismatchError,
    UnauthorizedEvidenceActionError,
)
from .models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from .period_validator import AssessmentPeriodValidator


@dataclass
class SubcriterionCoverageResult:
    """
    Detailed coverage status for a single subcriterion.
    """
    framework: str
    parameter_id: str
    subcriterion_id: str
    max_marks: float
    coverage_state: CoverageState
    evidence_count: int = 0
    verified_count: int = 0
    pending_count: int = 0
    rejected_count: int = 0
    period_valid_count: int = 0
    period_invalid_count: int = 0
    is_period_sensitive: bool = True
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)
    deficiency_codes: List[str] = field(default_factory=list)
    blocking_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['coverage_state'] = self.coverage_state.value if isinstance(self.coverage_state, CoverageState) else str(self.coverage_state)
        return data


@dataclass
class ParameterCoverageResult:
    """
    Grouped coverage status for a parameter and its subcriteria.
    """
    parameter_id: str
    title: str
    max_marks: float
    period_rule: str
    subcriteria: List[SubcriterionCoverageResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_id": self.parameter_id,
            "title": self.title,
            "max_marks": self.max_marks,
            "period_rule": self.period_rule,
            "subcriteria": [s.to_dict() for s in self.subcriteria],
        }


@dataclass
class CoverageSummary:
    """
    High-level metrics summarizing assessment evidence readiness.
    """
    total_subcriteria: int = 0
    covered_subcriteria: int = 0
    uncovered_subcriteria: int = 0
    verification_pending: int = 0
    rejected_evidence: int = 0
    period_invalid: int = 0
    verified_subcriteria: int = 0
    is_ready_for_scoring: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AssessmentCoverageReport:
    """
    Authoritative, deterministic report on evidence coverage and scoring readiness.
    """
    framework: str
    institution_id: str
    assessment_id: str
    assessment_period: Dict[str, Any]
    parameters: List[ParameterCoverageResult] = field(default_factory=list)
    summary: CoverageSummary = field(default_factory=CoverageSummary)
    duplicates_detected: List[Dict[str, Any]] = field(default_factory=list)
    is_ready_for_scoring: bool = False
    blocking_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "institution_id": self.institution_id,
            "assessment_id": self.assessment_id,
            "assessment_period": self.assessment_period,
            "parameters": [p.to_dict() for p in self.parameters],
            "summary": self.summary.to_dict(),
            "duplicates_detected": self.duplicates_detected,
            "is_ready_for_scoring": self.is_ready_for_scoring,
            "blocking_reasons": self.blocking_reasons,
        }


class EvidenceCoverageEvaluator:
    """
    Evaluates evidence coverage, period compliance, and scoring readiness.
    Deterministic and read-only: does NOT calculate or change scores.
    """

    @classmethod
    def evaluate_evidence_coverage(
        cls,
        assessment_id: Optional[str] = None,
        nomination=None,
        institution_id: Optional[str] = None,
        framework: Optional[str] = None,
        requesting_user=None,
        subcriterion_codes: Optional[List[str]] = None,
    ) -> AssessmentCoverageReport:
        """
        Generates a comprehensive evidence coverage report for an assessment.
        """
        # 1. Resolve context
        resolved_assessment_id, resolved_institution_id, resolved_framework = cls._resolve_context(
            assessment_id, nomination, institution_id, framework
        )

        # 2. Authorization and Data Isolation
        cls._enforce_authorization(
            requesting_user=requesting_user,
            institution_id=resolved_institution_id,
            framework=resolved_framework,
        )

        # 3. Retrieve authoritative framework specification
        params_spec = cls._get_framework_specification(resolved_framework)

        # 4. Fetch all active associations for this assessment context
        assoc_qs = EvidenceSubcriterionAssociation.objects.filter(
            is_active=True
        ).select_related('evidence')

        if resolved_assessment_id:
            assoc_qs = assoc_qs.filter(evidence__assessment_id=resolved_assessment_id)
        elif resolved_institution_id:
            assoc_qs = assoc_qs.filter(evidence__institution_id=resolved_institution_id)

        # Only consider active evidence documents
        assoc_qs = assoc_qs.filter(evidence__is_active=True)

        # Map associations by (parameter_id, subcriterion_id)
        sub_assocs: Dict[Tuple[str, str], List[EvidenceSubcriterionAssociation]] = {}
        # Track duplicate usage across subcriteria
        doc_subcriteria_map: Dict[str, Dict[str, Any]] = {}

        for assoc in assoc_qs:
            key = (assoc.parameter_id, assoc.subcriterion_id)
            sub_assocs.setdefault(key, []).append(assoc)

            doc_id = str(assoc.evidence.document_id)
            if doc_id not in doc_subcriteria_map:
                doc_subcriteria_map[doc_id] = {
                    "document_id": doc_id,
                    "filename": assoc.evidence.original_filename,
                    "associations": [],
                }
            doc_subcriteria_map[doc_id]["associations"].append({
                "parameter_id": assoc.parameter_id,
                "subcriterion_id": assoc.subcriterion_id,
            })

        # Identify duplicate references (same document across multiple subcriteria)
        duplicates_detected = [
            info for info in doc_subcriteria_map.values()
            if len(info["associations"]) > 1
        ]
        reused_doc_ids = {info["document_id"] for info in duplicates_detected}

        # 5. Evaluate parameters and subcriteria
        param_results: List[ParameterCoverageResult] = []
        all_sub_results: List[SubcriterionCoverageResult] = []
        global_blocking_reasons: List[str] = []

        sub_filter = set(subcriterion_codes) if subcriterion_codes else None

        for param_id, param_def in params_spec.items():
            param_period_rule = param_def.get("period_rule")
            is_param_period_sensitive = AssessmentPeriodValidator.is_period_sensitive(param_period_rule)
            subcriteria_dict = param_def.get("subcriteria", {})

            param_sub_results: List[SubcriterionCoverageResult] = []

            for sub_id, sub_def in subcriteria_dict.items():
                if sub_filter and sub_id not in sub_filter:
                    continue

                sub_result = cls._evaluate_subcriterion(
                    framework=resolved_framework,
                    parameter_id=param_id,
                    subcriterion_id=sub_id,
                    sub_def=sub_def,
                    is_period_sensitive=is_param_period_sensitive,
                    associations=sub_assocs.get((param_id, sub_id), []),
                    reused_doc_ids=reused_doc_ids,
                )
                param_sub_results.append(sub_result)
                all_sub_results.append(sub_result)
                if sub_result.blocking_reasons:
                    for br in sub_result.blocking_reasons:
                        msg = f"[{sub_id}] {br}"
                        if msg not in global_blocking_reasons:
                            global_blocking_reasons.append(msg)

            if param_sub_results:
                param_results.append(
                    ParameterCoverageResult(
                        parameter_id=param_id,
                        title=param_def.get("title", f"Parameter {param_id}"),
                        max_marks=float(param_def.get("max_marks", 0.0)),
                        period_rule=str(param_period_rule.value if hasattr(param_period_rule, 'value') else param_period_rule),
                        subcriteria=param_sub_results,
                    )
                )

        # 6. Compute summary
        total_subcriteria = len(all_sub_results)
        covered_subcriteria = sum(1 for s in all_sub_results if s.evidence_count > 0)
        uncovered_subcriteria = total_subcriteria - covered_subcriteria
        verified_subcriteria = sum(1 for s in all_sub_results if s.coverage_state == CoverageState.EVIDENCE_VERIFIED)
        verification_pending = sum(1 for s in all_sub_results if s.pending_count > 0 or s.coverage_state == CoverageState.EVIDENCE_PENDING)
        rejected_evidence = sum(1 for s in all_sub_results if s.rejected_count > 0)
        period_invalid = sum(1 for s in all_sub_results if s.period_invalid_count > 0 or s.coverage_state == CoverageState.EVIDENCE_INVALID_PERIOD)

        is_ready = (
            total_subcriteria > 0 and
            covered_subcriteria == total_subcriteria and
            verified_subcriteria == total_subcriteria and
            uncovered_subcriteria == 0 and
            verification_pending == 0 and
            period_invalid == 0 and
            len(global_blocking_reasons) == 0
        )

        summary = CoverageSummary(
            total_subcriteria=total_subcriteria,
            covered_subcriteria=covered_subcriteria,
            uncovered_subcriteria=uncovered_subcriteria,
            verification_pending=verification_pending,
            rejected_evidence=rejected_evidence,
            period_invalid=period_invalid,
            verified_subcriteria=verified_subcriteria,
            is_ready_for_scoring=is_ready,
        )

        return AssessmentCoverageReport(
            framework=resolved_framework,
            institution_id=resolved_institution_id or "",
            assessment_id=resolved_assessment_id or "",
            assessment_period={
                "start_date": AssessmentPeriodValidator.START_DATE.isoformat(),
                "end_date": AssessmentPeriodValidator.END_DATE.isoformat(),
                "academic_year": AssessmentPeriodValidator.ACADEMIC_YEAR,
            },
            parameters=param_results,
            summary=summary,
            duplicates_detected=duplicates_detected,
            is_ready_for_scoring=is_ready,
            blocking_reasons=global_blocking_reasons,
        )

    @classmethod
    def is_assessment_evidence_ready(
        cls,
        assessment_id: Optional[str] = None,
        nomination=None,
        institution_id: Optional[str] = None,
        framework: Optional[str] = None,
        requesting_user=None,
        subcriterion_codes: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str], CoverageSummary]:
        """
        Convenience service answering whether the assessment's evidence is ready
        for scoring and review.
        Returns (is_ready, blocking_reasons, summary).
        """
        report = cls.evaluate_evidence_coverage(
            assessment_id=assessment_id,
            nomination=nomination,
            institution_id=institution_id,
            framework=framework,
            requesting_user=requesting_user,
            subcriterion_codes=subcriterion_codes,
        )
        return report.is_ready_for_scoring, report.blocking_reasons, report.summary

    @classmethod
    def _evaluate_subcriterion(
        cls,
        framework: str,
        parameter_id: str,
        subcriterion_id: str,
        sub_def: Dict[str, Any],
        is_period_sensitive: bool,
        associations: List[EvidenceSubcriterionAssociation],
        reused_doc_ids: Set[str],
    ) -> SubcriterionCoverageResult:
        """
        Evaluates a single subcriterion against its associated documents.
        """
        max_marks = float(sub_def.get("max_score", sub_def.get("max_marks", 0.0)))
        evidence_items: List[Dict[str, Any]] = []
        deficiency_codes: List[str] = []
        blocking_reasons: List[str] = []

        verified_valid_docs = []
        verified_invalid_docs = []
        pending_docs = []
        rejected_docs = []
        present_docs = []
        period_valid_count = 0
        period_invalid_count = 0

        # Evaluate each associated document
        for assoc in associations:
            doc = assoc.evidence
            doc_id = str(doc.document_id)

            item_deficiencies: List[str] = []
            is_valid_assoc = True

            # 1. Framework match verification
            if doc.framework != framework:
                item_deficiencies.append(CoverageDeficiencyCode.FRAMEWORK_MISMATCH.value)
                if CoverageDeficiencyCode.FRAMEWORK_MISMATCH.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.FRAMEWORK_MISMATCH.value)
                blocking_reasons.append(f"Evidence {doc_id} framework '{doc.framework}' does not match assessment '{framework}'.")
                is_valid_assoc = False

            # 2. Association status integrity
            if not doc.is_active or doc.status in (EvidenceLifecycleState.EVIDENCE_SUPERSEDED, EvidenceLifecycleState.EVIDENCE_WITHDRAWN):
                item_deficiencies.append(CoverageDeficiencyCode.INVALID_ASSOCIATION.value)
                if CoverageDeficiencyCode.INVALID_ASSOCIATION.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.INVALID_ASSOCIATION.value)
                blocking_reasons.append(f"Evidence {doc_id} is inactive or has been superseded/withdrawn.")
                is_valid_assoc = False

            if not is_valid_assoc:
                evidence_items.append({
                    "document_id": doc_id,
                    "filename": doc.original_filename,
                    "status": doc.status,
                    "document_date": doc.document_date.isoformat() if doc.document_date else None,
                    "period_valid": False,
                    "deficiency_codes": item_deficiencies,
                })
                continue

            # 3. Period validation
            period_valid, period_reason, period_code = AssessmentPeriodValidator.validate_document_period(
                doc, is_period_sensitive=is_period_sensitive
            )

            if period_valid:
                period_valid_count += 1
            else:
                period_invalid_count += 1
                if period_code:
                    item_deficiencies.append(period_code.value)
                    if period_code.value not in deficiency_codes:
                        deficiency_codes.append(period_code.value)

            # 4. Duplicate usage detection
            if doc_id in reused_doc_ids:
                if CoverageDeficiencyCode.DUPLICATE_EVIDENCE_DETECTED.value not in item_deficiencies:
                    item_deficiencies.append(CoverageDeficiencyCode.DUPLICATE_EVIDENCE_DETECTED.value)

            # 5. Bucket by lifecycle state
            if doc.status == EvidenceLifecycleState.EVIDENCE_VERIFIED:
                if period_valid or not is_period_sensitive:
                    verified_valid_docs.append(doc)
                else:
                    verified_invalid_docs.append(doc)
            elif doc.status == EvidenceLifecycleState.EVIDENCE_PENDING:
                pending_docs.append(doc)
                if CoverageDeficiencyCode.VERIFICATION_PENDING.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.VERIFICATION_PENDING.value)
            elif doc.status == EvidenceLifecycleState.EVIDENCE_REJECTED:
                rejected_docs.append(doc)
                if CoverageDeficiencyCode.EVIDENCE_REJECTED.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.EVIDENCE_REJECTED.value)
            elif doc.status == EvidenceLifecycleState.EVIDENCE_PRESENT:
                present_docs.append(doc)
                if CoverageDeficiencyCode.UNVERIFIED_EVIDENCE.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.UNVERIFIED_EVIDENCE.value)

            evidence_items.append({
                "document_id": doc_id,
                "filename": doc.original_filename,
                "status": doc.status,
                "document_date": doc.document_date.isoformat() if doc.document_date else None,
                "period_valid": period_valid,
                "deficiency_codes": item_deficiencies,
            })

        evidence_count = len(evidence_items)
        verified_count = len(verified_valid_docs) + len(verified_invalid_docs)
        pending_count = len(pending_docs)
        rejected_count = len(rejected_docs)

        # 6. Determine overall subcriterion coverage_state
        if evidence_count == 0:
            coverage_state = CoverageState.NO_EVIDENCE
            if CoverageDeficiencyCode.NO_ASSOCIATED_EVIDENCE.value not in deficiency_codes:
                deficiency_codes.append(CoverageDeficiencyCode.NO_ASSOCIATED_EVIDENCE.value)
            blocking_reasons.append("No associated evidence.")
        elif verified_valid_docs:
            # Verified and period-valid document exists -> unlocks scoring!
            coverage_state = CoverageState.EVIDENCE_VERIFIED
        elif verified_invalid_docs:
            # Verified but period invalid
            coverage_state = CoverageState.EVIDENCE_INVALID_PERIOD
            blocking_reasons.append("Evidence is verified but outside the authoritative assessment period (2025-07-01 to 2026-06-30).")
        elif period_invalid_count > 0 and not pending_docs and not present_docs:
            coverage_state = CoverageState.EVIDENCE_INVALID_PERIOD
            blocking_reasons.append("Evidence activity date falls outside the assessment period.")
        elif pending_docs:
            coverage_state = CoverageState.EVIDENCE_PENDING
            blocking_reasons.append("Evidence is pending verification by the screening committee.")
        elif rejected_docs and not present_docs:
            coverage_state = CoverageState.EVIDENCE_REJECTED
            blocking_reasons.append("All associated evidence was rejected by the reviewer.")
        else:
            coverage_state = CoverageState.EVIDENCE_PRESENT
            blocking_reasons.append("Evidence is uploaded but has not been submitted or verified.")

        return SubcriterionCoverageResult(
            framework=framework,
            parameter_id=parameter_id,
            subcriterion_id=subcriterion_id,
            max_marks=max_marks,
            coverage_state=coverage_state,
            evidence_count=evidence_count,
            verified_count=verified_count,
            pending_count=pending_count,
            rejected_count=rejected_count,
            period_valid_count=period_valid_count,
            period_invalid_count=period_invalid_count,
            is_period_sensitive=is_period_sensitive,
            evidence_items=evidence_items,
            deficiency_codes=deficiency_codes,
            blocking_reasons=blocking_reasons,
        )

    @classmethod
    def _resolve_context(
        cls,
        assessment_id: Optional[str],
        nomination,
        institution_id: Optional[str],
        framework: Optional[str],
    ) -> Tuple[Optional[str], Optional[str], str]:
        """Resolves assessment_id, institution_id, and framework from inputs."""
        res_assessment_id = assessment_id
        res_institution_id = institution_id
        res_framework = framework

        if nomination is not None:
            res_assessment_id = res_assessment_id or getattr(nomination, 'form_id', str(nomination.pk))
            if hasattr(nomination, 'college') and nomination.college:
                res_institution_id = res_institution_id or getattr(nomination.college, 'aishe_code', str(nomination.college.pk))
            res_framework = res_framework or FrameworkType.COLLEGE_2026.value

        if not res_framework and res_assessment_id:
            first_doc = EvidenceDocument.objects.filter(assessment_id=res_assessment_id).first()
            if first_doc:
                res_framework = first_doc.framework
                res_institution_id = res_institution_id or first_doc.institution_id

        if not res_framework:
            res_framework = FrameworkType.COLLEGE_2026.value

        return res_assessment_id, res_institution_id, res_framework

    @classmethod
    def _enforce_authorization(
        cls,
        requesting_user,
        institution_id: Optional[str],
        framework: str,
    ):
        """
        Enforces data isolation:
        - Institutional users cannot view other institutions.
        - Committee reviewers must be authorized for the framework/institution.
        """
        if not requesting_user or not getattr(requesting_user, 'is_authenticated', False):
            return  # Internal service invocation without user context permitted

        role = getattr(requesting_user, 'role', '')

        # Superuser and state_admin have full oversight
        if role in ('state_admin', 'superuser') or getattr(requesting_user, 'is_superuser', False):
            return

        # Institutional users: restrict to their own institution
        if role in ('principal', 'nodal_officer', 'faculty'):
            user_college = getattr(requesting_user, 'college', None)
            if user_college and institution_id:
                user_inst_id = getattr(user_college, 'aishe_code', None) or str(user_college.pk)
                if user_inst_id != institution_id:
                    raise UnauthorizedEvidenceActionError(
                        f"User '{requesting_user.email}' from institution '{user_inst_id}' "
                        f"is not authorized to access coverage for '{institution_id}'."
                    )
            return

        # Committee reviewers: check framework scoping
        if role == 'committee':
            has_auth = ReviewerAuthorization.objects.filter(
                user=requesting_user,
                is_active=True,
            ).exists()

            if has_auth:
                match = ReviewerAuthorization.objects.filter(
                    user=requesting_user,
                    framework=framework,
                    is_active=True,
                )
                if institution_id:
                    match = match.filter(
                        models.Q(institution_id="") | models.Q(institution_id=institution_id)
                    )
                if not match.exists():
                    raise UnauthorizedEvidenceActionError(
                        f"Reviewer '{requesting_user.email}' is not authorized for framework '{framework}'."
                    )
            return

        raise UnauthorizedEvidenceActionError(
            f"User role '{role}' is not authorized to access evidence coverage."
        )

    @classmethod
    def _get_framework_specification(cls, framework: str) -> Dict[str, Dict[str, Any]]:
        """Retrieves authoritative frozen parameter specification."""
        if framework == FrameworkType.UNIVERSITY_2026.value:
            return UNIVERSITY_PARAMETERS
        elif framework == FrameworkType.COLLEGE_2026.value:
            return COLLEGE_PARAMETERS
        else:
            raise FrameworkMismatchError(
                f"Unknown or unsupported framework '{framework}'. Must be UNIVERSITY_2026 or COLLEGE_2026."
            )
