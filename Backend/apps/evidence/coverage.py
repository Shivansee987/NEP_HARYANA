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
    AssociationVerificationDecision,
    CoverageDeficiencyCode,
    CoverageState,
    EvidenceLifecycleState,
    VerificationDecision,
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
from .taxonomy import (
    ContractStatus,
    get_subcriterion_contract,
    LEGACY_COARSE_EVIDENCE_TYPES,
    MULTI_SUBCRITERION_PARAMETERS,
    SINGLE_SUBCRITERION_PARAMETERS,
    SOURCE_SILENT_PARAMETERS,
)



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
    SOURCE_SILENT and UNRESOLVED subcriteria are excluded from documentary coverage counts.
    """
    total_subcriteria: int = 0
    covered_subcriteria: int = 0
    uncovered_subcriteria: int = 0
    verification_pending: int = 0
    rejected_evidence: int = 0
    period_invalid: int = 0
    verified_subcriteria: int = 0
    # Subcriteria exempt from documentary evidence requirement
    source_silent_subcriteria: int = 0
    # Subcriteria with unresolved governance/source contracts
    unresolved_subcriteria: int = 0
    # Active subcriteria that require documentary evidence (excludes silent/unresolved)
    active_documentary_subcriteria: int = 0
    is_ready_for_scoring: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewReadinessReport:
    """
    Deterministic reviewer-facing readiness classification.

    Distinguishes three categories of deficiency so the review workflow
    can route correctly without conflating them:

    - blocking_reasons: ACTIVE subcriteria with MISSING or PENDING evidence.
      These prevent "Complete Review" and prevent scoring.

    - correction_required_reasons: ACTIVE subcriteria with REJECTED evidence.
      The reviewer should use "Return to Institution" rather than completing.

    - governance_reasons: UNRESOLVED contract subcriteria.
      These are source/governance issues, not missing documents.
      They block certification per policy but do NOT represent institution failure.

    - source_silent_subcriteria: Informational. No documentary requirement; not blocking.
    """
    is_complete_review_allowed: bool = False
    blocking_reasons: List[str] = field(default_factory=list)       # MISSING/PENDING
    correction_required_reasons: List[str] = field(default_factory=list)  # REJECTED
    governance_reasons: List[str] = field(default_factory=list)     # UNRESOLVED
    source_silent_subcriteria: List[str] = field(default_factory=list)  # informational
    all_blocking_reasons: List[str] = field(default_factory=list)   # combined for backwards compat

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
    # Reviewer-facing structured readiness classification
    review_readiness: Optional[ReviewReadinessReport] = None

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
            "review_readiness": self.review_readiness.to_dict() if self.review_readiness else None,
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
        ).select_related('evidence').prefetch_related('verifications')

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
            param_key = (assoc.parameter_id or "").strip().upper()
            sub_key = (assoc.subcriterion_id or "").strip().upper()
            key = (param_key, sub_key)
            sub_assocs.setdefault(key, []).append(assoc)
            if not sub_key and param_key:
                sub_assocs.setdefault((param_key, ""), []).append(assoc)

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

                p_clean = param_id.strip().upper()
                s_clean = sub_id.strip().upper()
                matching_assocs = list(sub_assocs.get((p_clean, s_clean), []))

                # Parameter-level associations without subcriterion_id
                for pa in sub_assocs.get((p_clean, ""), []):
                    if pa not in matching_assocs:
                        matching_assocs.append(pa)

                # Check aliases if contract defines them
                c_temp = get_subcriterion_contract(resolved_framework, p_clean, s_clean)
                if c_temp and hasattr(c_temp, 'aliases'):
                    for al in getattr(c_temp, 'aliases', ()):
                        for aa in sub_assocs.get((p_clean, al.upper()), []):
                            if aa not in matching_assocs:
                                matching_assocs.append(aa)

                sub_result = cls._evaluate_subcriterion(
                    framework=resolved_framework,
                    parameter_id=param_id,
                    subcriterion_id=sub_id,
                    sub_def=sub_def,
                    is_period_sensitive=is_param_period_sensitive,
                    associations=matching_assocs,
                    reused_doc_ids=reused_doc_ids,
                    institution_id=resolved_institution_id,
                    param_def=param_def,
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
        # -------------------------------------------------------------------
        # CRITICAL CLASSIFICATION RULES:
        # SOURCE_SILENT  → No documentary requirement. NEVER a blocking deficiency.
        # UNRESOLVED     → Governance/source issue. NOT a missing-document deficiency.
        # REJECTED       → Correction required. NOT a completion blocker (use Return).
        # PENDING        → Blocking completion. Institution must wait for review.
        # MISSING/NO_EV  → Hard blocking. Institution must upload.
        # -------------------------------------------------------------------
        total_subcriteria = len(all_sub_results)

        # Subcriteria with no documentary evidence requirement (SOURCE_SILENT)
        source_silent_subs = [s for s in all_sub_results if s.coverage_state == CoverageState.SOURCE_SILENT]
        # Subcriteria with unresolved governance contracts (UNRESOLVED)
        unresolved_subs = [s for s in all_sub_results if s.coverage_state == CoverageState.UNRESOLVED]
        # Active documentary subcriteria: exclude SOURCE_SILENT and UNRESOLVED
        active_doc_subs = [
            s for s in all_sub_results
            if s.coverage_state not in (CoverageState.SOURCE_SILENT, CoverageState.UNRESOLVED)
        ]

        covered_subcriteria = sum(1 for s in active_doc_subs if s.evidence_count > 0)
        uncovered_subcriteria = len(active_doc_subs) - covered_subcriteria
        verified_subcriteria = sum(1 for s in active_doc_subs if s.coverage_state == CoverageState.EVIDENCE_VERIFIED)
        verification_pending = sum(
            1 for s in active_doc_subs
            if s.pending_count > 0 or s.coverage_state == CoverageState.EVIDENCE_PENDING
        )
        rejected_evidence = sum(1 for s in active_doc_subs if s.rejected_count > 0)
        period_invalid = sum(
            1 for s in active_doc_subs
            if s.period_invalid_count > 0 or s.coverage_state == CoverageState.EVIDENCE_INVALID_PERIOD
        )

        # Build reviewer-facing readiness classification
        # Separate global_blocking_reasons by deficiency category
        blocking_reasons_missing: List[str] = []    # MISSING or NO_EVIDENCE
        blocking_reasons_pending: List[str] = []    # PENDING
        correction_required_reasons: List[str] = []  # REJECTED
        governance_reasons: List[str] = []           # UNRESOLVED
        source_silent_ids: List[str] = []

        for s in all_sub_results:
            if s.coverage_state == CoverageState.SOURCE_SILENT:
                source_silent_ids.append(s.subcriterion_id)
            elif s.coverage_state == CoverageState.UNRESOLVED:
                for br in s.blocking_reasons:
                    msg = f"[{s.subcriterion_id}] {br}"
                    if msg not in governance_reasons:
                        governance_reasons.append(msg)
            elif s.coverage_state == CoverageState.EVIDENCE_REJECTED:
                for br in s.blocking_reasons:
                    msg = f"[{s.subcriterion_id}] {br}"
                    if msg not in correction_required_reasons:
                        correction_required_reasons.append(msg)
            elif s.coverage_state in (
                CoverageState.NO_EVIDENCE,
                CoverageState.EVIDENCE_PRESENT,
            ):
                for br in s.blocking_reasons:
                    msg = f"[{s.subcriterion_id}] {br}"
                    if msg not in blocking_reasons_missing:
                        blocking_reasons_missing.append(msg)
            elif s.coverage_state in (
                CoverageState.EVIDENCE_PENDING,
                CoverageState.EVIDENCE_INVALID_PERIOD,
            ):
                for br in s.blocking_reasons:
                    msg = f"[{s.subcriterion_id}] {br}"
                    if msg not in blocking_reasons_pending:
                        blocking_reasons_pending.append(msg)

        all_hard_blocking = blocking_reasons_missing + blocking_reasons_pending

        # is_ready_for_scoring: all ACTIVE documentary subcriteria must be VERIFIED.
        # SOURCE_SILENT and UNRESOLVED do NOT count as missing evidence.
        # REJECTED evidence triggers correction required, not completion readiness.
        is_ready = (
            len(active_doc_subs) > 0 and
            verified_subcriteria == len(active_doc_subs) and
            uncovered_subcriteria == 0 and
            verification_pending == 0 and
            period_invalid == 0 and
            rejected_evidence == 0 and
            len(all_hard_blocking) == 0
        )

        # Complete review is allowed when all ACTIVE subcriteria are verified.
        # Rejected evidence is a correction-required state, not a blocking state.
        # Governance issues (UNRESOLVED) do not block review completion per current policy.
        is_complete_review_allowed = (
            len(active_doc_subs) > 0 and
            verified_subcriteria == len(active_doc_subs) and
            uncovered_subcriteria == 0 and
            verification_pending == 0 and
            period_invalid == 0 and
            len(blocking_reasons_missing) == 0 and
            len(blocking_reasons_pending) == 0
        )

        review_readiness = ReviewReadinessReport(
            is_complete_review_allowed=is_complete_review_allowed,
            blocking_reasons=all_hard_blocking,
            correction_required_reasons=correction_required_reasons,
            governance_reasons=governance_reasons,
            source_silent_subcriteria=source_silent_ids,
            all_blocking_reasons=all_hard_blocking + correction_required_reasons + governance_reasons,
        )

        summary = CoverageSummary(
            total_subcriteria=total_subcriteria,
            covered_subcriteria=covered_subcriteria,
            uncovered_subcriteria=uncovered_subcriteria,
            verification_pending=verification_pending,
            rejected_evidence=rejected_evidence,
            period_invalid=period_invalid,
            verified_subcriteria=verified_subcriteria,
            source_silent_subcriteria=len(source_silent_subs),
            unresolved_subcriteria=len(unresolved_subs),
            active_documentary_subcriteria=len(active_doc_subs),
            is_ready_for_scoring=is_ready,
        )

        # Backwards-compatible global_blocking_reasons:
        # Only includes ACTIVE documentary deficiencies (missing + pending).
        # SOURCE_SILENT and UNRESOLVED are excluded from hard blocking.
        compatible_blocking_reasons = all_hard_blocking

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
            blocking_reasons=compatible_blocking_reasons,
            review_readiness=review_readiness,
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

        NOTE: blocking_reasons only includes ACTIVE documentary deficiencies
        (MISSING + PENDING). SOURCE_SILENT and UNRESOLVED are excluded.
        REJECTED evidence is returned via report.review_readiness.correction_required_reasons.
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
    def get_review_readiness(
        cls,
        assessment_id: Optional[str] = None,
        nomination=None,
        institution_id: Optional[str] = None,
        framework: Optional[str] = None,
        requesting_user=None,
    ) -> Tuple[bool, "ReviewReadinessReport", CoverageSummary]:
        """
        Returns the structured ReviewReadinessReport for the reviewer workflow gate.

        Distinguishes:
          - is_complete_review_allowed: True only if all ACTIVE documentary subcriteria are VERIFIED.
          - blocking_reasons: MISSING/PENDING \u2014 hard blockers for completion.
          - correction_required_reasons: REJECTED evidence \u2014 reviewer should Return to Institution.
          - governance_reasons: UNRESOLVED contracts \u2014 governance/source issues, not institution failure.
          - source_silent_subcriteria: Informational. No documentary requirement.

        Returns (is_complete_review_allowed, review_readiness, summary).
        """
        report = cls.evaluate_evidence_coverage(
            assessment_id=assessment_id,
            nomination=nomination,
            institution_id=institution_id,
            framework=framework,
            requesting_user=requesting_user,
        )
        rr = report.review_readiness
        if rr is None:
            # Fallback: build a minimal report from is_ready_for_scoring
            rr = ReviewReadinessReport(
                is_complete_review_allowed=report.is_ready_for_scoring,
                blocking_reasons=report.blocking_reasons,
            )
        return rr.is_complete_review_allowed, rr, report.summary

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
        institution_id: Optional[str] = None,
        param_def: Optional[Dict[str, Any]] = None,
    ) -> SubcriterionCoverageResult:
        """
        Evaluates a single subcriterion against its associated documents and Step 4C contracts.
        Ensures exact subcriterion-level contract satisfaction and association verification.
        """
        clean_fw = "UNIVERSITY_2026" if "UNIVERSITY" in str(framework).upper() else "COLLEGE_2026"
        param_clean = (parameter_id or "").strip().upper()
        sub_clean = (subcriterion_id or "").strip().upper()
        max_marks = float(sub_def.get("max_score", sub_def.get("max_marks", 0.0)))

        evidence_items: List[Dict[str, Any]] = []
        deficiency_codes: List[str] = []
        blocking_reasons: List[str] = []

        is_multi = param_clean in MULTI_SUBCRITERION_PARAMETERS
        is_single = param_clean in SINGLE_SUBCRITERION_PARAMETERS

        # 1. Resolve exact subcriterion contract
        contract = get_subcriterion_contract(clean_fw, param_clean, sub_clean)

        # 2. Check UNRESOLVED_MISSING contract
        # UNRESOLVED is a GOVERNANCE/SOURCE issue, NOT a missing-document deficiency.
        # It is represented as a governance_reason in ReviewReadinessReport, not a hard blocker.
        if contract and contract.status == ContractStatus.UNRESOLVED_MISSING:
            def_code = CoverageDeficiencyCode.CONTRACT_UNRESOLVED.value
            deficiency_codes.append(def_code)
            blocking_reasons.append(
                f"Subcriterion '{sub_clean}' has an unresolved evidence contract "
                f"(Authoritative PDF specifies Scopus metric but documentary evidence table is silent on documentation. "
                f"Fails closed.). Cannot be marked covered until authoritative resolution."
            )
            return SubcriterionCoverageResult(
                framework=clean_fw,
                parameter_id=param_clean,
                subcriterion_id=sub_clean,
                max_marks=max_marks,
                coverage_state=CoverageState.UNRESOLVED,
                evidence_count=len(associations),
                verified_count=0,
                pending_count=0,
                rejected_count=0,
                period_valid_count=0,
                period_invalid_count=0,
                is_period_sensitive=is_period_sensitive,
                evidence_items=[],
                deficiency_codes=deficiency_codes,
                blocking_reasons=blocking_reasons,
            )

        # 3. Check SOURCE_SILENT contract
        # SOURCE_SILENT means: "The authoritative source specifies no documentary requirement."
        # This is NOT missing evidence. It must NEVER appear as a hard blocker.
        # It applies regardless of whether there are associations or not.
        if (contract and contract.status == ContractStatus.SOURCE_SILENT) or param_clean in SOURCE_SILENT_PARAMETERS:
            # SOURCE_SILENT subcriteria are exempt from documentary evidence requirements.
            # Any uploaded associations are informational only.
            def_code = CoverageDeficiencyCode.CONTRACT_SOURCE_SILENT.value
            if def_code not in deficiency_codes:
                deficiency_codes.append(def_code)
            # No blocking_reasons — SOURCE_SILENT is never a hard blocker.
            return SubcriterionCoverageResult(
                framework=clean_fw,
                parameter_id=param_clean,
                subcriterion_id=sub_clean,
                max_marks=max_marks,
                coverage_state=CoverageState.SOURCE_SILENT,
                evidence_count=len(associations),
                verified_count=0,
                pending_count=0,
                rejected_count=0,
                period_valid_count=0,
                period_invalid_count=0,
                is_period_sensitive=is_period_sensitive,
                evidence_items=[],
                deficiency_codes=deficiency_codes,
                blocking_reasons=[],  # SOURCE_SILENT: no blocking reasons
            )

        # 4. Resolve allowed and quarantined evidence types
        if contract:
            allowed_types = list(contract.allowed_evidence_types)
            if contract.canonical_evidence_type and contract.canonical_evidence_type not in allowed_types:
                allowed_types.append(contract.canonical_evidence_type)
            quarantined_types = list(contract.quarantined_types)
            aliases = [a.upper() for a in getattr(contract, "aliases", ())]
        else:
            allowed_types = (
                sub_def.get("mandatory_evidence")
                if (sub_def and "mandatory_evidence" in sub_def)
                else (param_def.get("mandatory_evidence", []) if param_def else [])
            )
            quarantined_types = []
            aliases = []

        if is_single and "EVID_GENERAL" not in allowed_types:
            allowed_types.append("EVID_GENERAL")

        verified_valid_assocs = []
        verified_invalid_assocs = []
        pending_assocs = []
        rejected_assocs = []
        present_assocs = []
        period_valid_count = 0
        period_invalid_count = 0

        # Evaluate each associated document
        for assoc in associations:
            doc = assoc.evidence
            doc_id = str(doc.document_id)
            item_deficiencies: List[str] = []
            is_valid_assoc = True

            # Framework match verification
            if doc.framework != clean_fw:
                item_deficiencies.append(CoverageDeficiencyCode.FRAMEWORK_MISMATCH.value)
                if CoverageDeficiencyCode.FRAMEWORK_MISMATCH.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.FRAMEWORK_MISMATCH.value)
                blocking_reasons.append(f"Evidence {doc_id} framework '{doc.framework}' does not match assessment '{clean_fw}'.")
                is_valid_assoc = False

            # Institution isolation check
            if institution_id and doc.institution_id and doc.institution_id != institution_id:
                item_deficiencies.append(CoverageDeficiencyCode.INSTITUTION_MISMATCH.value)
                if CoverageDeficiencyCode.INSTITUTION_MISMATCH.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.INSTITUTION_MISMATCH.value)
                blocking_reasons.append(f"Evidence {doc_id} belongs to institution '{doc.institution_id}', does not match assessment institution '{institution_id}'.")
                is_valid_assoc = False

            # Association status integrity
            if not doc.is_active or doc.status in (EvidenceLifecycleState.EVIDENCE_SUPERSEDED, EvidenceLifecycleState.EVIDENCE_WITHDRAWN):
                item_deficiencies.append(CoverageDeficiencyCode.INVALID_ASSOCIATION.value)
                if CoverageDeficiencyCode.INVALID_ASSOCIATION.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.INVALID_ASSOCIATION.value)
                blocking_reasons.append(f"Evidence {doc_id} is inactive or has been superseded/withdrawn.")
                is_valid_assoc = False

            # Parameter isolation check
            if assoc.parameter_id:
                assoc_param = assoc.parameter_id.strip().upper()
                if assoc_param != param_clean:
                    is_valid_assoc = False
                    blocking_reasons.append(f"Evidence association parameter '{assoc_param}' does not match '{param_clean}'.")

            # Multi-subcriterion association identity checks
            if is_multi:
                # Disallow parameter-level evidence without subcriterion association
                if assoc.parameter_id and not assoc.subcriterion_id:
                    is_valid_assoc = False
                    blocking_reasons.append(f"Parameter-level evidence without exact subcriterion association cannot satisfy multi-subcriterion '{param_clean}'.")

                # Disallow sibling subcriterion evidence
                if assoc.subcriterion_id:
                    assoc_sub = assoc.subcriterion_id.strip().upper()
                    if assoc_sub != sub_clean and assoc_sub not in aliases:
                        is_valid_assoc = False
                        blocking_reasons.append(f"Sibling association mismatch: '{assoc_sub}' cannot satisfy '{sub_clean}'.")

            # Evidence type validation
            cand_type = (assoc.subcriterion_evidence_type or doc.evidence_type or "").strip()
            if cand_type in quarantined_types or (
                cand_type in LEGACY_COARSE_EVIDENCE_TYPES and cand_type not in allowed_types
            ):
                item_deficiencies.append(CoverageDeficiencyCode.QUARANTINED_EVIDENCE.value)
                if CoverageDeficiencyCode.QUARANTINED_EVIDENCE.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.QUARANTINED_EVIDENCE.value)
                blocking_reasons.append(f"Evidence type '{cand_type}' is quarantined from satisfying '{sub_clean}'.")
                is_valid_assoc = False
            elif allowed_types and cand_type not in allowed_types:
                item_deficiencies.append(CoverageDeficiencyCode.EVIDENCE_TYPE_MISMATCH.value)
                if CoverageDeficiencyCode.EVIDENCE_TYPE_MISMATCH.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.EVIDENCE_TYPE_MISMATCH.value)
                blocking_reasons.append(f"Evidence type '{cand_type}' does not satisfy subcriterion contract for '{sub_clean}'. Allowed: {allowed_types}.")
                is_valid_assoc = False

            if not is_valid_assoc:
                evidence_items.append({
                    "document_id": doc_id,
                    "association_id": str(assoc.association_id),
                    "filename": doc.original_filename,
                    "status": doc.status,
                    "document_date": doc.document_date.isoformat() if doc.document_date else None,
                    "period_valid": False,
                    "deficiency_codes": item_deficiencies,
                })
                continue

            # Period validation
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

            # Duplicate usage detection
            if doc_id in reused_doc_ids:
                if CoverageDeficiencyCode.DUPLICATE_EVIDENCE_DETECTED.value not in item_deficiencies:
                    item_deficiencies.append(CoverageDeficiencyCode.DUPLICATE_EVIDENCE_DETECTED.value)

            # Association-level Verification Determination
            assoc_status = assoc.verification_status

            # Priority 1: Rejection
            if (
                assoc_status in (VerificationDecision.REJECTED, AssociationVerificationDecision.REJECTED, "REJECTED")
                or doc.status == EvidenceLifecycleState.EVIDENCE_REJECTED
            ):
                rejected_assocs.append(assoc)
                if CoverageDeficiencyCode.EVIDENCE_REJECTED.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.EVIDENCE_REJECTED.value)
            elif is_multi:
                # Multi-subcriterion: strictly requires association-level verification
                if assoc_status in (VerificationDecision.VERIFIED, AssociationVerificationDecision.VERIFIED, "VERIFIED"):
                    if period_valid or not is_period_sensitive:
                        verified_valid_assocs.append(assoc)
                    else:
                        verified_invalid_assocs.append(assoc)
                else:
                    pending_assocs.append(assoc)
                    if CoverageDeficiencyCode.VERIFICATION_PENDING.value not in deficiency_codes:
                        deficiency_codes.append(CoverageDeficiencyCode.VERIFICATION_PENDING.value)
            else:
                # Single subcriterion: inherits document-level verification if unreviewed
                if (
                    assoc_status in (VerificationDecision.VERIFIED, AssociationVerificationDecision.VERIFIED, "VERIFIED")
                    or (assoc_status is None and doc.status == EvidenceLifecycleState.EVIDENCE_VERIFIED)
                ):
                    if period_valid or not is_period_sensitive:
                        verified_valid_assocs.append(assoc)
                    else:
                        verified_invalid_assocs.append(assoc)
                elif doc.status == EvidenceLifecycleState.EVIDENCE_PENDING or assoc_status in (VerificationDecision.PENDING, AssociationVerificationDecision.PENDING, "PENDING"):
                    pending_assocs.append(assoc)
                    if CoverageDeficiencyCode.VERIFICATION_PENDING.value not in deficiency_codes:
                        deficiency_codes.append(CoverageDeficiencyCode.VERIFICATION_PENDING.value)
                elif doc.status == EvidenceLifecycleState.EVIDENCE_PRESENT:
                    present_assocs.append(assoc)
                    if CoverageDeficiencyCode.UNVERIFIED_EVIDENCE.value not in deficiency_codes:
                        deficiency_codes.append(CoverageDeficiencyCode.UNVERIFIED_EVIDENCE.value)
                else:
                    pending_assocs.append(assoc)

            evidence_items.append({
                "document_id": doc_id,
                "association_id": str(assoc.association_id),
                "filename": doc.original_filename,
                "status": doc.status,
                "association_status": str(assoc_status) if assoc_status else None,
                "document_date": doc.document_date.isoformat() if doc.document_date else None,
                "period_valid": period_valid,
                "deficiency_codes": item_deficiencies,
            })

        evidence_count = len(evidence_items)
        verified_count = len(verified_valid_assocs) + len(verified_invalid_assocs)
        pending_count = len(pending_assocs)
        rejected_count = len(rejected_assocs)

        # 6. Determine overall subcriterion coverage_state
        if evidence_count == 0:
            if contract and contract.status == ContractStatus.SOURCE_SILENT:
                coverage_state = CoverageState.SOURCE_SILENT
                if CoverageDeficiencyCode.CONTRACT_SOURCE_SILENT.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.CONTRACT_SOURCE_SILENT.value)
            elif contract and contract.status == ContractStatus.UNRESOLVED_MISSING:
                coverage_state = CoverageState.UNRESOLVED
                if CoverageDeficiencyCode.CONTRACT_UNRESOLVED.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.CONTRACT_UNRESOLVED.value)
            else:
                coverage_state = CoverageState.NO_EVIDENCE
                if CoverageDeficiencyCode.NO_ASSOCIATED_EVIDENCE.value not in deficiency_codes:
                    deficiency_codes.append(CoverageDeficiencyCode.NO_ASSOCIATED_EVIDENCE.value)
                blocking_reasons.append("No associated evidence.")
        elif verified_valid_assocs:
            coverage_state = CoverageState.EVIDENCE_VERIFIED
        elif verified_invalid_assocs:
            coverage_state = CoverageState.EVIDENCE_INVALID_PERIOD
            blocking_reasons.append("Evidence is verified but outside the authoritative assessment period (2025-07-01 to 2026-06-30).")
        elif period_invalid_count > 0 and not pending_assocs and not present_assocs and not rejected_assocs:
            coverage_state = CoverageState.EVIDENCE_INVALID_PERIOD
            blocking_reasons.append("Evidence activity date falls outside the assessment period.")
        elif pending_assocs:
            coverage_state = CoverageState.EVIDENCE_PENDING
            blocking_reasons.append("Evidence is pending verification by the screening committee.")
        elif rejected_assocs and not present_assocs:
            coverage_state = CoverageState.EVIDENCE_REJECTED
            blocking_reasons.append("All associated evidence was rejected by the reviewer.")
        elif present_assocs:
            coverage_state = CoverageState.EVIDENCE_PRESENT
            blocking_reasons.append("Evidence is uploaded but has not been submitted or verified.")
        elif contract and contract.status == ContractStatus.SOURCE_SILENT:
            coverage_state = CoverageState.SOURCE_SILENT
        elif contract and contract.status == ContractStatus.UNRESOLVED_MISSING:
            coverage_state = CoverageState.UNRESOLVED
        else:
            coverage_state = CoverageState.NO_EVIDENCE
            blocking_reasons.append("No valid contract-compliant evidence associated with subcriterion.")

        return SubcriterionCoverageResult(
            framework=clean_fw,
            parameter_id=param_clean,
            subcriterion_id=sub_clean,
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
