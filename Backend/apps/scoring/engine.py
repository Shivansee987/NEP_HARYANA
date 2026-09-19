"""
NEP Excellence Awards 2026 - Master Server-Authoritative Scoring Engine
Executes the approved 15-step scoring pipeline with strict framework isolation,
evidence gating, double-counting validation, and ambiguity blocking.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from apps.scoring.domain import (
    AssessmentContext,
    AssessmentInput,
    FrameworkResult,
    ParameterInput,
    ParameterResult,
    ReviewerAdjustment,
)
from apps.scoring.enums import (
    CertificationStatus,
    EvaluationType,
    FrameworkType,
    GatingStatus,
    InstitutionType,
    ResolutionStatus,
)
from apps.scoring.evaluators.double_counting import DoubleCountingValidator
from apps.scoring.rules.college import COLLEGE_EVALUATORS
from apps.scoring.rules.definitions import COLLEGE_PARAMETERS, UNIVERSITY_PARAMETERS
from apps.scoring.rules.university import UNIVERSITY_EVALUATORS
from apps.scoring.adjustments import ReviewerAdjustmentService


class FrameworkMismatchException(Exception):
    """Raised when an institution attempts to be scored against the wrong framework."""
    pass


class NEP2026ScoringEngine:
    """
    Server-authoritative scoring engine executing the 15-step scoring pipeline.
    """

    def __init__(self):
        self.version = "2026.1.0"

    def score_assessment(
        self,
        assessment_input: AssessmentInput,
        reviewer_adjustments: Optional[List[ReviewerAdjustment]] = None,
        calculation_version_index: int = 1
    ) -> FrameworkResult:
        """
        Executes the 15-step scoring pipeline for a University or College assessment.
        """
        ctx = assessment_input.context
        calc_id = str(uuid.uuid4())
        calc_timestamp = datetime.utcnow().isoformat() + "Z"

        # -------------------------------------------------------------
        # STEP 1 & 2: Load Assessment & Pre-flight Integrity Validation
        # -------------------------------------------------------------
        if not ctx.is_active:
            raise ValueError(f"Assessment {ctx.assessment_id} is inactive or archived. Scoring aborted.")

        # Strict Framework Isolation: Institution Type MUST match Framework
        if ctx.institution_type == InstitutionType.UNIVERSITY or ctx.institution_type == "UNIVERSITY":
            if ctx.framework != FrameworkType.UNIVERSITY_2026:
                raise FrameworkMismatchException(
                    f"Framework mismatch: University institution {ctx.institution_id} cannot be evaluated under {ctx.framework}."
                )
            target_evaluators = UNIVERSITY_EVALUATORS
            target_definitions = UNIVERSITY_PARAMETERS
            expected_param_keys = [f"U{i}" for i in range(1, 21)]
        elif ctx.institution_type == InstitutionType.COLLEGE or ctx.institution_type == "COLLEGE":
            if ctx.framework != FrameworkType.COLLEGE_2026:
                raise FrameworkMismatchException(
                    f"Framework mismatch: College institution {ctx.institution_id} cannot be evaluated under {ctx.framework}."
                )
            target_evaluators = COLLEGE_EVALUATORS
            target_definitions = COLLEGE_PARAMETERS
            expected_param_keys = [f"C{i}" for i in range(1, 23)]
        else:
            raise FrameworkMismatchException(f"Unknown institution type: {ctx.institution_type}")

        # -------------------------------------------------------------
        # STEP 3 & 4 & 5: Load Parameter Definitions & Validate Inputs
        # -------------------------------------------------------------
        validator = DoubleCountingValidator()
        parameter_results: Dict[str, ParameterResult] = {}
        blocking_reasons: List[str] = []

        # -------------------------------------------------------------
        # STEP 6 through 11: Evaluate Each Parameter in Framework Scope
        # -------------------------------------------------------------
        for param_code in expected_param_keys:
            param_def = target_definitions[param_code]
            evaluator_fn = target_evaluators[param_code]
            param_in = assessment_input.parameters.get(param_code)

            if param_in is None:
                # Institution submitted no responses for this parameter -> 0 marks
                param_in = ParameterInput(parameter_code=param_code)

            # Execute Step 6 (Period), Step 7 (Raw), Step 8 (Gating), Step 9 (Double Counting), Step 10 & 11 (Aggregation)
            param_res = evaluator_fn(param_in, ctx, validator)
            parameter_results[param_code] = param_res

            # Check for blocking conditions
            if param_res.resolution_status == ResolutionStatus.UNRESOLVED_RULE:
                blocking_reasons.append(
                    f"Parameter {param_code} is BLOCKED: Source specification is contradictory or underspecified."
                )
            elif param_res.resolution_status == ResolutionStatus.BOUNDARY_UNRESOLVED:
                blocking_reasons.append(
                    f"Parameter {param_code} is BLOCKED: Input landed on an unresolved boundary void in the rubric."
                )
            elif param_res.resolution_status == ResolutionStatus.SOURCE_INCONSISTENCY:
                blocking_reasons.append(
                    f"Parameter {param_code} is BLOCKED: Source rubric items sum contradicts declared maximum."
                )
            elif param_res.resolution_status == ResolutionStatus.INVALID_INPUT:
                blocking_reasons.append(
                    f"Parameter {param_code} is BLOCKED: Input data is invalid, contradictory, or malformed."
                )

        # Record any cross-parameter double-counting conflicts detected
        if validator.conflicts:
            for conf in validator.conflicts:
                blocking_reasons.append(f"Double-counting conflict: {conf['reason']}")

            # Elevate conflicts to parameter-level traces for affected parameters
            for p_code, p_res in parameter_results.items():
                p_conflicts = [c for c in validator.conflicts if c.get("affected_parameter") == p_code]
                if p_conflicts:
                    p_res.trace["duplicates_detected"] = p_conflicts
                    p_res.trace["double_counting_conflicts"] = p_conflicts

        # -------------------------------------------------------------
        # STEP 12: Framework Aggregation (Independent Caps & Global 100 Cap)
        # -------------------------------------------------------------
        raw_sum = sum(p.raw_score for p in parameter_results.values())
        gated_sum = sum(p.evidence_gated_score for p in parameter_results.values())

        raw_total = min(raw_sum, 100.00)
        evidence_gated_total = min(gated_sum, 100.00)

        # Check evidence gating at framework level
        has_pending_evidence = any(
            sub.gating_status == GatingStatus.PROVISIONAL_PENDING_VERIFICATION
            for p in parameter_results.values()
            for sub in p.subcriteria_results.values()
        )
        if has_pending_evidence:
            blocking_reasons.append("Evidence pending verification on one or more criteria.")

        has_failed_evidence = any(
            sub.gating_status in (GatingStatus.FAILED_EVIDENCE_ABSENT, GatingStatus.FAILED_EVIDENCE_REJECTED)
            for p in parameter_results.values()
            for sub in p.subcriteria_results.values()
        )

        # -------------------------------------------------------------
        # STEP 13: Generate Calculation Trace
        # -------------------------------------------------------------
        global_trace: Dict[str, Any] = {
            "engine_version": self.version,
            "calculation_id": calc_id,
            "version_index": calculation_version_index,
            "framework": ctx.framework.value,
            "institution_type": ctx.institution_type.value,
            "timestamp": calc_timestamp,
            "total_parameters_evaluated": len(parameter_results),
            "double_counting_conflicts_count": len(validator.conflicts),
            "double_counting_conflicts": validator.conflicts,
            "raw_total_before_cap": raw_sum,
            "raw_total_after_cap": raw_total,
            "evidence_gated_total_before_cap": gated_sum,
            "evidence_gated_total_after_cap": evidence_gated_total,
        }

        # -------------------------------------------------------------
        # STEP 14: Apply Reviewer Adjustments (if provided)
        # -------------------------------------------------------------
        if reviewer_adjustments:
            for adj in reviewer_adjustments:
                ok, err = ReviewerAdjustmentService.validate_and_apply_adjustment(
                    FrameworkResult(
                        framework=ctx.framework,
                        assessment_id=ctx.assessment_id,
                        institution_id=ctx.institution_id,
                        calculation_id=calc_id,
                        version_index=calculation_version_index,
                        timestamp=calc_timestamp,
                        raw_total=raw_total,
                        evidence_gated_total=evidence_gated_total,
                        final_certified_total=None,
                        max_marks=100.00,
                        certification_status=CertificationStatus.FINALIZABLE,
                        blocking_reasons=blocking_reasons,
                        parameter_results=parameter_results,
                        trace=global_trace,
                    ),
                    adj
                )
                if not ok:
                    rejection_msg = f"Reviewer adjustment rejected: {err}"
                    if rejection_msg not in blocking_reasons:
                        blocking_reasons.append(rejection_msg)

            # Re-read sums after adjustments
            evidence_gated_total = min(
                sum(p.evidence_gated_score for p in parameter_results.values()),
                100.00
            )

        # -------------------------------------------------------------
        # STEP 15: Final Certification Eligibility
        # -------------------------------------------------------------
        final_certified_total: Optional[float] = None
        if any("BLOCKED: Source specification" in r or "contradicts declared maximum" in r for r in blocking_reasons):
            cert_status = CertificationStatus.BLOCKED_BY_SPECIFICATION
        elif any("BLOCKED: Input landed on an unresolved boundary" in r for r in blocking_reasons):
            cert_status = CertificationStatus.BLOCKED_BY_BOUNDARY
        elif has_pending_evidence:
            cert_status = CertificationStatus.BLOCKED_BY_EVIDENCE
        elif any("Double-counting conflict" in r for r in blocking_reasons):
            cert_status = CertificationStatus.BLOCKED_BY_VALIDATION
        elif any("Reviewer adjustment rejected" in r for r in blocking_reasons):
            cert_status = CertificationStatus.BLOCKED_BY_VALIDATION
        elif blocking_reasons:
            cert_status = CertificationStatus.BLOCKED_BY_VALIDATION
        else:
            # All conditions met for finalization
            cert_status = CertificationStatus.FINALIZABLE
            final_certified_total = evidence_gated_total

        return FrameworkResult(
            framework=ctx.framework,
            assessment_id=ctx.assessment_id,
            institution_id=ctx.institution_id,
            calculation_id=calc_id,
            version_index=calculation_version_index,
            timestamp=calc_timestamp,
            raw_total=raw_total,
            evidence_gated_total=evidence_gated_total,
            final_certified_total=final_certified_total,
            max_marks=100.00,
            certification_status=cert_status,
            blocking_reasons=blocking_reasons,
            parameter_results=parameter_results,
            trace=global_trace,
        )
