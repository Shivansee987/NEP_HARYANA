"""
NEP Excellence Awards 2026 - Controlled Reviewer Adjustment Engine
Guarantees full traceability and prevents unauthorized bypassing of evidence, maximums, or unresolved rules.
"""
from typing import Any, Dict, List, Optional, Tuple

from apps.scoring.domain import FrameworkResult, ParameterResult, ReviewerAdjustment, SubcriterionResult
from apps.scoring.enums import CertificationStatus, EvaluationType, GatingStatus, ResolutionStatus


class ReviewerAdjustmentService:
    """
    Validates and applies reviewer score adjustments strictly within legal framework bounds.
    """

    @staticmethod
    def _reject_adjustment(
        framework_result: FrameworkResult,
        error_msg: str,
        adjustment: Optional[ReviewerAdjustment] = None,
        found_sub_res: Optional[SubcriterionResult] = None,
        found_param_code: Optional[str] = None,
        found_param_res: Optional[ParameterResult] = None,
    ) -> Tuple[bool, str]:
        rejection_reason = f"Reviewer adjustment rejected: {error_msg}"
        if rejection_reason not in framework_result.blocking_reasons:
            framework_result.blocking_reasons.append(rejection_reason)
        framework_result.final_certified_total = None
        if framework_result.certification_status not in (
            CertificationStatus.BLOCKED_BY_SPECIFICATION,
            CertificationStatus.BLOCKED_BY_BOUNDARY,
        ):
            framework_result.certification_status = CertificationStatus.BLOCKED_BY_VALIDATION

        if adjustment:
            fw_history = framework_result.trace.setdefault("reviewer_adjustments", [])
            seq = len(fw_history) + 1

            prev_score = None
            prev_state = "UNKNOWN"
            if found_sub_res:
                prev_score = (
                    found_sub_res.review_adjusted_score
                    if found_sub_res.review_adjusted_score is not None
                    else found_sub_res.evidence_gated_score
                )
                prev_state = "FINALIZABLE" if found_sub_res.final_score is not None else found_sub_res.gating_status.value

            record = {
                "sequence": seq,
                "reviewer_id": adjustment.reviewer_id,
                "timestamp": adjustment.timestamp.isoformat() if hasattr(adjustment.timestamp, "isoformat") else str(adjustment.timestamp),
                "target_subcriterion": adjustment.subcriterion_code,
                "target_parameter": found_param_code,
                "previous_score": prev_score,
                "proposed_score": adjustment.adjusted_score,
                "adjusted_score": None,
                "validation_result": "INVALID",
                "status": "REJECTED",
                "rejection_reason": error_msg,
                "resulting_score": prev_score,
                "resulting_state": prev_state,
                "reason": adjustment.reason,
                "signature": adjustment.signature,
            }
            fw_history.append(record)
            if found_sub_res is not None:
                found_sub_res.trace.setdefault("reviewer_adjustments", []).append(record)
                found_sub_res.trace["reviewer_adjustment"] = record
            if found_param_res is not None:
                found_param_res.trace.setdefault("reviewer_adjustments", []).append(record)

        return False, error_msg

    @staticmethod
    def validate_and_apply_adjustment(
        framework_result: FrameworkResult,
        adjustment: ReviewerAdjustment
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates whether an adjustment is legally permissible and applies it to the framework result.
        
        Returns:
            (success, error_message)
        """
        target_sub_code = adjustment.subcriterion_code
        found_param_code: Optional[str] = None
        found_param_res: Optional[ParameterResult] = None
        found_sub_res: Optional[SubcriterionResult] = None

        # 1. Locate parameter and subcriterion
        for p_code, p_res in framework_result.parameter_results.items():
            if target_sub_code in p_res.subcriteria_results:
                found_param_code = p_code
                found_param_res = p_res
                found_sub_res = p_res.subcriteria_results[target_sub_code]
                break

        if not found_sub_res or not found_param_res:
            return ReviewerAdjustmentService._reject_adjustment(
                framework_result,
                f"Subcriterion {target_sub_code} not found in current framework evaluation.",
                adjustment=adjustment,
            )

        # 2. Invariant Check: Reviewer identity and reason must be present
        if not adjustment.reviewer_id or not adjustment.reviewer_id.strip():
            return ReviewerAdjustmentService._reject_adjustment(
                framework_result,
                "Reviewer ID is required for audit trail.",
                adjustment=adjustment,
                found_sub_res=found_sub_res,
                found_param_code=found_param_code,
                found_param_res=found_param_res,
            )
        if not adjustment.reason or len(adjustment.reason.strip()) < 10:
            return ReviewerAdjustmentService._reject_adjustment(
                framework_result,
                "A substantial reason (minimum 10 characters) is required for score adjustment.",
                adjustment=adjustment,
                found_sub_res=found_sub_res,
                found_param_code=found_param_code,
                found_param_res=found_param_res,
            )

        # 3. Maximum and Non-negativity Bounds Check
        if adjustment.adjusted_score < 0.0:
            return ReviewerAdjustmentService._reject_adjustment(
                framework_result,
                f"Adjusted score {adjustment.adjusted_score} cannot be negative.",
                adjustment=adjustment,
                found_sub_res=found_sub_res,
                found_param_code=found_param_code,
                found_param_res=found_param_res,
            )
        if adjustment.adjusted_score > found_sub_res.max_score:
            return ReviewerAdjustmentService._reject_adjustment(
                framework_result,
                (
                    f"Adjusted score {adjustment.adjusted_score} exceeds subcriterion maximum "
                    f"{found_sub_res.max_score} for {target_sub_code}."
                ),
                adjustment=adjustment,
                found_sub_res=found_sub_res,
                found_param_code=found_param_code,
                found_param_res=found_param_res,
            )

        # 4. Prohibited Action: Cannot bypass unresolved specification blocks
        if found_sub_res.resolution_status in (ResolutionStatus.UNRESOLVED_RULE, ResolutionStatus.BOUNDARY_UNRESOLVED):
            return ReviewerAdjustmentService._reject_adjustment(
                framework_result,
                (
                    f"Reviewer cannot adjust {target_sub_code}: Rule has status "
                    f"{found_sub_res.resolution_status.value}. Unresolved specifications require State Council ruling."
                ),
                adjustment=adjustment,
                found_sub_res=found_sub_res,
                found_param_code=found_param_code,
                found_param_res=found_param_res,
            )
        if found_param_res.resolution_status in (ResolutionStatus.UNRESOLVED_RULE, ResolutionStatus.SOURCE_INCONSISTENCY):
            return ReviewerAdjustmentService._reject_adjustment(
                framework_result,
                (
                    f"Reviewer cannot adjust parameter {found_param_code}: "
                    f"Status is {found_param_res.resolution_status.value}. Bypassing unresolved specification is forbidden."
                ),
                adjustment=adjustment,
                found_sub_res=found_sub_res,
                found_param_code=found_param_code,
                found_param_res=found_param_res,
            )

        # 5. Prohibited Action: Cannot bypass evidence requirements (zero earned score if evidence rejected or absent)
        if found_sub_res.gating_status in (GatingStatus.FAILED_EVIDENCE_ABSENT, GatingStatus.FAILED_EVIDENCE_REJECTED):
            if adjustment.adjusted_score > 0.0:
                return ReviewerAdjustmentService._reject_adjustment(
                    framework_result,
                    (
                        f"Cannot award positive score ({adjustment.adjusted_score}) for {target_sub_code}: "
                        f"Evidence gating status is {found_sub_res.gating_status.value}."
                    ),
                    adjustment=adjustment,
                    found_sub_res=found_sub_res,
                    found_param_code=found_param_code,
                    found_param_res=found_param_res,
                )

        previous_score = (
            found_sub_res.review_adjusted_score
            if found_sub_res.review_adjusted_score is not None
            else found_sub_res.evidence_gated_score
        )
        previous_state = "FINALIZABLE" if found_sub_res.final_score is not None else found_sub_res.gating_status.value

        # 6. Apply adjustment to SubcriterionResult
        adjustment.original_score = previous_score
        found_sub_res.review_adjusted_score = adjustment.adjusted_score
        if found_sub_res.gating_status == GatingStatus.PASSED_EVIDENCE_VERIFIED:
            found_sub_res.final_score = adjustment.adjusted_score
            resulting_state = "FINALIZABLE"
        else:
            found_sub_res.final_score = None  # Still blocked if not verified
            resulting_state = found_sub_res.gating_status.value

        fw_history = framework_result.trace.setdefault("reviewer_adjustments", [])
        seq = len(fw_history) + 1

        record = {
            "sequence": seq,
            "reviewer_id": adjustment.reviewer_id,
            "timestamp": adjustment.timestamp.isoformat() if hasattr(adjustment.timestamp, "isoformat") else str(adjustment.timestamp),
            "target_subcriterion": target_sub_code,
            "target_parameter": found_param_code,
            "previous_score": previous_score,
            "proposed_score": adjustment.adjusted_score,
            "adjusted_score": adjustment.adjusted_score,
            "validation_result": "VALID",
            "status": "ACCEPTED",
            "rejection_reason": None,
            "resulting_score": found_sub_res.review_adjusted_score,
            "resulting_state": resulting_state,
            "reason": adjustment.reason,
            "signature": adjustment.signature,
        }
        fw_history.append(record)
        found_sub_res.trace.setdefault("reviewer_adjustments", []).append(record)
        found_sub_res.trace["reviewer_adjustment"] = record
        found_param_res.trace.setdefault("reviewer_adjustments", []).append(record)

        # 7. Re-aggregate Parameter Score
        ReviewerAdjustmentService._recalculate_parameter(found_param_res)

        # 8. Re-aggregate Framework Total (Strict 100.00 ceiling)
        ReviewerAdjustmentService._recalculate_framework(framework_result)

        return True, None

    @staticmethod
    def _recalculate_parameter(param_res: ParameterResult) -> None:
        sub_results = param_res.subcriteria_results.values()
        
        # Calculate new parameter-level scores based on review_adjusted_score where available
        effective_scores = [
            r.review_adjusted_score if r.review_adjusted_score is not None else r.evidence_gated_score
            for r in sub_results
        ]
        
        raw_scores = [r.raw_score for r in sub_results]

        if param_res.aggregation_strategy in (EvaluationType.SUM, EvaluationType.FIXED_ITEM_SUM, EvaluationType.COMPOSITE):
            new_gated_sum = sum(effective_scores)
            new_raw_sum = sum(raw_scores)
        elif param_res.aggregation_strategy in (EvaluationType.MAX, EvaluationType.COUNT_TIER):
            new_gated_sum = max(effective_scores) if effective_scores else 0.0
            new_raw_sum = max(raw_scores) if raw_scores else 0.0
        else:
            new_gated_sum = sum(effective_scores)
            new_raw_sum = sum(raw_scores)

        # Clamp to parameter maximum
        param_res.evidence_gated_score = min(new_gated_sum, param_res.max_marks)
        param_res.raw_score = min(new_raw_sum, param_res.max_marks)
        param_res.review_adjusted_score = param_res.evidence_gated_score

        # Check if all subcriteria are finalizable
        all_final = all(r.final_score is not None for r in sub_results) and param_res.resolution_status == ResolutionStatus.CALCULABLE
        param_res.final_score = param_res.evidence_gated_score if all_final else None

    @staticmethod
    def _recalculate_framework(framework_result: FrameworkResult) -> None:
        param_scores = [p.evidence_gated_score for p in framework_result.parameter_results.values()]
        raw_scores = [p.raw_score for p in framework_result.parameter_results.values()]

        # Strictly enforce global 100.00 ceiling
        framework_result.evidence_gated_total = min(sum(param_scores), 100.00)
        framework_result.raw_total = min(sum(raw_scores), 100.00)

        all_params_final = all(p.final_score is not None for p in framework_result.parameter_results.values())
        if all_params_final and not framework_result.blocking_reasons:
            framework_result.final_certified_total = framework_result.evidence_gated_total
            framework_result.certification_status = CertificationStatus.FINALIZABLE
        else:
            framework_result.final_certified_total = None
            if any("BLOCKED: Source specification" in r or "contradicts declared maximum" in r for r in framework_result.blocking_reasons):
                framework_result.certification_status = CertificationStatus.BLOCKED_BY_SPECIFICATION
            elif any("BLOCKED: Input landed on an unresolved boundary" in r for r in framework_result.blocking_reasons):
                framework_result.certification_status = CertificationStatus.BLOCKED_BY_BOUNDARY
            elif any("Reviewer adjustment rejected" in r for r in framework_result.blocking_reasons):
                framework_result.certification_status = CertificationStatus.BLOCKED_BY_VALIDATION
            elif framework_result.blocking_reasons:
                framework_result.certification_status = CertificationStatus.BLOCKED_BY_VALIDATION
