"""
NEP Excellence Awards 2026 - College Assessment Orchestration Service
Coordinates College assessments, evidence associations, and scoring execution
through the frozen server-authoritative scoring engine and Phase 5 evidence subsystem.
"""
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import uuid

from django.db import transaction
from django.utils import timezone

from apps.authentication.models import College
from apps.evidence.coverage import AssessmentCoverageReport, CoverageSummary
from apps.evidence.enums import EvidenceLifecycleState
from apps.evidence.models import (
    EvidenceDocument as DBEvidenceDocument,
    EvidenceSubcriterionAssociation,
    ReviewerAuthorization,
)
from apps.evidence.services import EvidenceService
from apps.scoring.domain import (
    AssessmentContext,
    AssessmentInput,
    AssessmentPeriod,
    AssetEntity,
    EvidenceDocument as ScoringEvidenceDoc,
    FrameworkResult,
    ParameterInput,
    ReviewerAdjustment,
    SubcriterionInput,
)
from apps.scoring.engine import NEP2026ScoringEngine
from apps.scoring.enums import (
    EvidenceState,
    FrameworkType,
    InstitutionType,
    ResolutionStatus,
)
from apps.scoring.inputs import normalize_subcriterion
from apps.scoring.rules.definitions import COLLEGE_PARAMETERS
from apps.scoring.orchestration import (
    claimed_subcriteria,
    submission_errors,
    REVIEWS_KEY,
    SNAPSHOT_KEY,
    approval_blockers,
    build_certified_snapshot,
    build_parameter_inputs,
    build_scoring_evaluation,
    certification_gate_errors,
    load_persisted_adjustments,
    persist_score_cache,
)
from .models import (
    CollegeAssessment,
    CollegeAssessmentAuditLog,
    CollegeReviewAction,
    CollegeReviewRecord,
)
from .registry import (
    COLLEGE_FRAMEWORK_CODE,
    COLLEGE_PARAMETER_CODES,
    get_college_parameters,
    validate_college_parameter_code,
)
from .validators import (
    AssessmentAlreadyCertifiedError,
    AssessmentLockedError,
    AssessmentNotReadyError,
    CertificationBlockedError,
    CertificationNotAuthorizedError,
    CollegeNotAuthorizedError,
    CollegeValidationError,
    ConcurrentReviewConflictError,
    ConcurrentUpdateError,
    EvidenceNotReadyError,
    FrameworkMismatchError,
    InvalidReviewStateError,
    InvalidStateTransitionError,
    ReviewConflictError,
    ReviewNotAuthorizedError,
    ScoringBlockedError,
    ScoringNotEvaluatedError,
    validate_framework_code,
    validate_institution_type,
    validate_parameter,
    validate_temporal_activity_date,
)


class CollegeAssessmentService:
    """
    Primary service layer for College assessments.
    Enforces framework isolation, strictly delegates scoring to the frozen engine,
    and bridges College evidence to the Phase 5 infrastructure.
    """

    @classmethod
    @transaction.atomic
    def create_assessment(
        cls,
        college_id: Any,
        assessment_id: Optional[str] = None,
        academic_year: str = "2025-26",
        created_by: Any = None,
    ) -> CollegeAssessment:
        """
        Initializes a new College assessment session.
        Guarantees distinct College institution context.
        """
        if isinstance(college_id, College):
            college = college_id
        else:
            try:
                if str(college_id).isdigit():
                    college = College.objects.get(pk=int(college_id))
                else:
                    college = College.objects.get(aishe_code=str(college_id))
            except College.DoesNotExist:
                raise CollegeValidationError(f"College '{college_id}' not found.")

        is_active = getattr(college, "is_active", True)
        if not is_active:
            raise CollegeValidationError(f"College '{college.name}' is not active.")

        if not assessment_id:
            assessment_id = f"ASSESS-2026-COL-{college.aishe_code}-{uuid.uuid4().hex[:8].upper()}"

        assessment = CollegeAssessment.objects.create(
            assessment_id=assessment_id,
            college=college,
            framework=COLLEGE_FRAMEWORK_CODE,
            academic_year=academic_year,
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="DRAFT",
            parameter_data={},
        )

        CollegeAssessmentAuditLog.objects.create(
            assessment=assessment,
            actor=created_by,
            action="CREATED",
            previous_state="",
            new_state="DRAFT",
            reason="Initial assessment creation",
        )

        return assessment

    @classmethod
    @transaction.atomic
    def update_parameter_inputs(
        cls,
        assessment_id: str,
        parameter_code: str,
        raw_inputs: Dict[str, Any],
        entities: Optional[List[Dict[str, Any]]] = None,
        activity_date: Optional[date] = None,
    ) -> CollegeAssessment:
        """
        Validates and records parameter data for a specific College parameter (C1–C22).
        """
        param_clean = validate_parameter(parameter_code)
        try:
            assessment = CollegeAssessment.objects.select_for_update().get(assessment_id=assessment_id)
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.")

        if assessment.status != "DRAFT":
            raise InvalidStateTransitionError(
                f"Assessment '{assessment_id}' is in '{assessment.status}' status and cannot be modified."
            )

        # Temporal check for date-sensitive parameters
        if activity_date:
            validate_temporal_activity_date(activity_date, param_clean)

        data = dict(assessment.parameter_data)
        data[param_clean] = {
            "raw_inputs": raw_inputs or {},
            "entities": entities or [],
            "activity_date": activity_date.isoformat() if activity_date else None,
            "updated_at": timezone.now().isoformat(),
        }
        assessment.parameter_data = data
        assessment.save(update_fields=["parameter_data", "updated_at"])

        CollegeAssessmentAuditLog.objects.create(
            assessment=assessment,
            actor=None,
            action="PARAMETER_UPDATED",
            previous_state=assessment.status,
            new_state=assessment.status,
            reason=f"Updated parameter {param_clean}",
        )

        return assessment

    @classmethod
    def build_assessment_input(cls, assessment_id: str) -> AssessmentInput:
        """
        Assembles the authoritative domain AssessmentInput for the frozen scoring engine.
        Gathers raw parameter inputs and active verified/pending evidence associations.
        """
        try:
            assessment = CollegeAssessment.objects.select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.")

        # 1. Assessment Context
        context = AssessmentContext(
            assessment_id=assessment.assessment_id,
            institution_id=assessment.college.aishe_code,
            institution_type=InstitutionType.COLLEGE,
            framework=FrameworkType.COLLEGE_2026,
            assessment_period=AssessmentPeriod(
                start_date=assessment.period_start,
                end_date=assessment.period_end,
                academic_year=assessment.academic_year,
            ),
            is_active=getattr(assessment.college, "is_active", True),
            lifecycle_status=assessment.status,
        )

        # 2. Gather Evidence Associations for this assessment
        associations = EvidenceSubcriterionAssociation.objects.filter(
            evidence__assessment_id=assessment.assessment_id,
            is_active=True,
        ).select_related("evidence")

        # Map evidence docs to scoring domain objects by subcriterion
        subcrit_evidence_map: Dict[str, List[ScoringEvidenceDoc]] = {}
        for assoc in associations:
            doc = assoc.evidence
            # Framework isolation: College assessment cannot accept non-College evidence
            if doc.framework != COLLEGE_FRAMEWORK_CODE:
                continue

            scoring_doc = EvidenceService.to_scoring_domain(assoc)
            subcrit_evidence_map.setdefault(assoc.subcriterion_id, []).append(scoring_doc)

        # 3. Build ParameterInput for all C1–C22 parameters (entities/raw inputs scoped per subcriterion)
        parameters_input = build_parameter_inputs(
            assessment.parameter_data or {}, get_college_parameters(), COLLEGE_PARAMETER_CODES, subcrit_evidence_map
        )
        return AssessmentInput(context=context, parameters=parameters_input)

    @classmethod
    def evaluate_assessment_scoring(
        cls,
        assessment_id: str,
        reviewer_adjustments: Optional[List[ReviewerAdjustment]] = None,
        persist: bool = True,
    ) -> FrameworkResult:
        """
        Executes scoring exclusively via the frozen NEP2026ScoringEngine.
        Does NOT recalculate or synthesize scores in this service layer.

        persist=True caches the authoritative total on the assessment (explicit recalculation actions only).
        A CERTIFIED assessment is never overwritten; read paths call this with persist=False.
        """
        if reviewer_adjustments is None:
            assessment_obj = CollegeAssessment.objects.filter(assessment_id=assessment_id).first()
            if assessment_obj is not None:
                reviewer_adjustments = load_persisted_adjustments(assessment_obj.parameter_data or {})

        assessment_input = cls.build_assessment_input(assessment_id)
        engine = NEP2026ScoringEngine()
        result = engine.score_assessment(
            assessment_input=assessment_input,
            reviewer_adjustments=reviewer_adjustments,
        )

        if persist:
            persist_score_cache(CollegeAssessment, assessment_id, result)

        return result

    @classmethod
    def get_assessment_scoring_evaluation(
        cls,
        assessment_id: str,
        user: Any = None,
        persist: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieves the complete server-authoritative scoring evaluation,
        parameter maximums, reviewer acceptance state, live running total,
        and award classification for a College assessment.
        """
        from apps.scoring.rules.definitions import COLLEGE_PARAMETERS

        try:
            assessment = CollegeAssessment.objects.select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        # A certified assessment is served from its frozen certification snapshot; the live engine
        # is only consulted (read-only) when an older certified record has no snapshot.
        result = None
        if assessment.status != "CERTIFIED" or SNAPSHOT_KEY not in (assessment.parameter_data or {}):
            result = cls.evaluate_assessment_scoring(assessment_id, persist=persist and assessment.status != "CERTIFIED")
            assessment.refresh_from_db()

        return build_scoring_evaluation(
            assessment=assessment,
            result=result,
            definitions=COLLEGE_PARAMETERS,
            param_codes=COLLEGE_PARAMETER_CODES,
            framework_code=COLLEGE_FRAMEWORK_CODE,
            institution_name=assessment.college.name,
        )

    @classmethod
    @transaction.atomic
    def accept_parameter_score(
        cls,
        assessment_id: str,
        parameter_code: str,
        reviewer: Any,
        comments: str = "",
    ) -> Dict[str, Any]:
        """
        Committee action: Approves the server-calculated score for a specific College parameter.
        Updates the running score immediately and logs an immutable audit trail.
        """
        from apps.scoring.rules.definitions import COLLEGE_PARAMETERS
        from apps.scoring.enums import ResolutionStatus

        param_clean = validate_parameter(parameter_code)
        try:
            assessment = CollegeAssessment.objects.select_for_update().select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        CollegeReviewService.validate_reviewer_authorization(reviewer, assessment)

        if assessment.status in ("CERTIFIED", "BLOCKED"):
            raise AssessmentLockedError(f"Assessment is {assessment.status} and cannot be modified.")

        # Evaluate current server-authoritative scoring (explicit action -> persisted)
        result = cls.evaluate_assessment_scoring(assessment_id, persist=True)
        param_res = result.parameter_results.get(param_clean)
        if not param_res:
            raise CollegeValidationError(f"Parameter '{param_clean}' not found in framework.", code="NOT_FOUND")

        param_def = COLLEGE_PARAMETERS[param_clean]
        blocker = approval_blockers(param_res)
        if blocker:
            raise CollegeValidationError(
                f"Parameter {param_clean} cannot be approved yet: {blocker['message']}",
                code=blocker["code"],
            )

        # Enforce server-side hard maximum cap
        max_marks = float(param_def["max_marks"])
        awarded_score = min(float(param_res.evidence_gated_score), max_marks)

        # Save review record in assessment JSON data
        data = dict(assessment.parameter_data or {})
        reviews = dict(data.get("_committee_reviews", {}))
        reviews[param_clean] = {
            "status": "APPROVED",
            "awarded_score": awarded_score,
            "calculated_score": float(param_res.evidence_gated_score),
            "max_marks": max_marks,
            "reviewer_id": str(reviewer.pk),
            "reviewer_email": getattr(reviewer, "email", "reviewer"),
            "reviewed_at": timezone.now().isoformat(),
            "comments": comments.strip(),
            "override": False,
            "override_reason": None,
        }
        data["_committee_reviews"] = reviews
        assessment.parameter_data = data
        assessment.save(update_fields=["parameter_data", "updated_at"])

        # Create immutable review record
        CollegeReviewRecord.objects.create(
            assessment=assessment,
            reviewer=reviewer,
            action=CollegeReviewAction.EVALUATE,
            status_before=assessment.status,
            status_after=assessment.status,
            comments=f"Accepted calculated score for {param_clean}: {awarded_score} / {max_marks}. {comments}".strip(),
            scoring_snapshot={
                "parameter_code": param_clean,
                "awarded_score": awarded_score,
                "calculated_score": float(param_res.evidence_gated_score),
                "max_marks": max_marks,
            },
        )

        CollegeAssessmentAuditLog.objects.create(
            assessment=assessment,
            actor=reviewer,
            action="PARAMETER_SCORE_ACCEPTED",
            previous_state=assessment.status,
            new_state=assessment.status,
            reason=f"Accepted score {awarded_score} / {max_marks} for {param_clean}",
        )

        return cls.get_assessment_scoring_evaluation(assessment_id, user=reviewer, persist=True)

    @classmethod
    @transaction.atomic
    def adjust_parameter_score(
        cls,
        assessment_id: str,
        parameter_code: str,
        subcriterion_code: str,
        adjusted_score: float,
        reason: str,
        reviewer: Any,
    ) -> Dict[str, Any]:
        """
        Controlled Reviewer Override: Adjusts a College subcriterion score with mandatory reason,
        strict maximum bounds validation, evidence gating compliance, and full audit trail.
        """
        from apps.scoring.rules.definitions import COLLEGE_PARAMETERS
        from apps.scoring.adjustments import ReviewerAdjustmentService

        param_clean = validate_parameter(parameter_code)
        try:
            assessment = CollegeAssessment.objects.select_for_update().select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        CollegeReviewService.validate_reviewer_authorization(reviewer, assessment)

        if assessment.status in ("CERTIFIED", "BLOCKED"):
            raise AssessmentLockedError(f"Assessment is {assessment.status} and cannot be modified.")

        # Validate reason and bounds
        if not reason or len(reason.strip()) < 10:
            raise CollegeValidationError(
                "A substantial justification (minimum 10 characters) is mandatory for score adjustment.",
                code="REASON_REQUIRED"
            )

        try:
            adj_score = float(adjusted_score)
        except (ValueError, TypeError):
            raise CollegeValidationError("Adjusted score must be a valid number.", code="INVALID_SCORE")

        if adj_score < 0.0:
            raise CollegeValidationError("Adjusted score cannot be negative.", code="INVALID_SCORE")

        param_def = COLLEGE_PARAMETERS.get(param_clean)
        if not param_def:
            raise CollegeValidationError(f"Parameter '{param_clean}' not found in framework.", code="NOT_FOUND")

        sub_def = param_def.get("subcriteria", {}).get(subcriterion_code)
        if not sub_def:
            raise CollegeValidationError(f"Subcriterion '{subcriterion_code}' not found under '{param_clean}'.", code="NOT_FOUND")

        sub_max = float(sub_def.get("max_score", param_def["max_marks"]))
        if adj_score > sub_max:
            raise CollegeValidationError(
                f"Adjusted score {adj_score} exceeds subcriterion maximum {sub_max} for {subcriterion_code}.",
                code="SCORE_EXCEEDS_MAXIMUM"
            )

        # Validate and apply adjustment via server-authoritative engine
        adjustment = ReviewerAdjustment(
            subcriterion_code=subcriterion_code,
            reviewer_id=str(reviewer.pk),
            original_score=0.0,
            adjusted_score=adj_score,
            reason=reason.strip(),
        )

        # Pre-flight validation against current scoring state
        curr_result = cls.evaluate_assessment_scoring(assessment_id)
        valid, err_msg = ReviewerAdjustmentService.validate_and_apply_adjustment(curr_result, adjustment)
        if not valid:
            raise CollegeValidationError(f"Adjustment rejected: {err_msg}", code="ADJUSTMENT_REJECTED")

        # Persist adjustment in assessment JSON data
        data = dict(assessment.parameter_data or {})
        adjs = list(data.get("_reviewer_adjustments", []))
        adjs = [a for a in adjs if a.get("subcriterion_code") != subcriterion_code]
        adjs.append({
            "subcriterion_code": subcriterion_code,
            "reviewer_id": str(reviewer.pk),
            "reviewer_email": getattr(reviewer, "email", "reviewer"),
            "original_score": adjustment.original_score,
            "adjusted_score": adj_score,
            "reason": reason.strip(),
            "timestamp": timezone.now().isoformat(),
        })
        data["_reviewer_adjustments"] = adjs

        # Re-score assessment with updated adjustments
        assessment.parameter_data = data
        assessment.save(update_fields=["parameter_data", "updated_at"])

        updated_result = cls.evaluate_assessment_scoring(assessment_id)
        updated_param = updated_result.parameter_results[param_clean]

        # Update approved parameter review with adjusted score
        reviews = dict(data.get("_committee_reviews", {}))
        reviews[param_clean] = {
            "status": "APPROVED",
            "awarded_score": min(float(updated_param.evidence_gated_score), float(param_def["max_marks"])),
            "calculated_score": float(updated_param.raw_score),
            "max_marks": float(param_def["max_marks"]),
            "reviewer_id": str(reviewer.pk),
            "reviewer_email": getattr(reviewer, "email", "reviewer"),
            "reviewed_at": timezone.now().isoformat(),
            "comments": reason.strip(),
            "override": True,
            "override_reason": reason.strip(),
        }
        data["_committee_reviews"] = reviews
        assessment.parameter_data = data
        assessment.save(update_fields=["parameter_data", "updated_at"])

        # Immutable review and audit logs
        CollegeReviewRecord.objects.create(
            assessment=assessment,
            reviewer=reviewer,
            action=CollegeReviewAction.EVALUATE,
            status_before=assessment.status,
            status_after=assessment.status,
            reason=reason.strip(),
            comments=f"Adjusted score for {subcriterion_code} to {adj_score}. Reason: {reason}".strip(),
            scoring_snapshot={
                "parameter_code": param_clean,
                "subcriterion_code": subcriterion_code,
                "adjusted_score": adj_score,
                "awarded_score": reviews[param_clean]["awarded_score"],
                "max_marks": reviews[param_clean]["max_marks"],
                "is_override": True,
            },
        )

        CollegeAssessmentAuditLog.objects.create(
            assessment=assessment,
            actor=reviewer,
            action="SCORE_ADJUSTED",
            previous_state=assessment.status,
            new_state=assessment.status,
            reason=reason.strip(),
        )

        return cls.get_assessment_scoring_evaluation(assessment_id, user=reviewer, persist=True)


    @classmethod
    def evaluate_assessment_coverage(
        cls,
        assessment_id: str,
        user: Any = None,
    ) -> AssessmentCoverageReport:
        """
        Evaluates subcriterion evidence coverage via Phase 5D EvidenceService.
        """
        try:
            assessment = CollegeAssessment.objects.select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.")

        eval_user = user
        if user and (
            getattr(user, "is_superuser", False)
            or getattr(user, "role", "") in ("state_admin", "committee")
        ):
            eval_user = user
        else:
            eval_user = None

        return EvidenceService.evaluate_evidence_coverage(
            assessment_id=assessment.assessment_id,
            institution_id=assessment.college.aishe_code,
            framework=COLLEGE_FRAMEWORK_CODE,
            requesting_user=eval_user,
        )

    @classmethod
    def check_assessment_readiness(
        cls,
        assessment_id: str,
        user: Any = None,
    ) -> Tuple[bool, List[str], CoverageSummary]:
        """
        Checks whether College assessment evidence is complete and ready for scoring review.
        """
        try:
            assessment = CollegeAssessment.objects.select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.")

        eval_user = user
        if user and (
            getattr(user, "is_superuser", False)
            or getattr(user, "role", "") in ("state_admin", "committee")
        ):
            eval_user = user
        else:
            eval_user = None

        return EvidenceService.is_assessment_evidence_ready(
            assessment_id=assessment.assessment_id,
            institution_id=assessment.college.aishe_code,
            framework=COLLEGE_FRAMEWORK_CODE,
            requesting_user=eval_user,
            # Only claimed subcriteria need documentary proof (unclaimed ones score 0)
            subcriterion_codes=claimed_subcriteria(assessment.parameter_data or {}, get_college_parameters(), COLLEGE_PARAMETER_CODES),
        )

    @classmethod
    def get_review_readiness(
        cls,
        assessment_id: str,
        user: Any = None,
    ):
        """
        Returns the structured ReviewReadinessReport for the complete_review gate.
        Distinguishes MISSING/PENDING (blockers), REJECTED (correction required),
        UNRESOLVED (governance), SOURCE_SILENT (not a requirement).
        Returns (is_complete_review_allowed, review_readiness, summary).
        """
        try:
            assessment = CollegeAssessment.objects.select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.")

        eval_user = user
        if user and (
            getattr(user, "is_superuser", False)
            or getattr(user, "role", "") in ("state_admin", "committee")
        ):
            eval_user = user
        else:
            eval_user = None

        return EvidenceService.get_review_readiness(
            assessment_id=assessment.assessment_id,
            institution_id=assessment.college.aishe_code,
            framework=COLLEGE_FRAMEWORK_CODE,
            requesting_user=eval_user,
            # Only claimed subcriteria need documentary proof (unclaimed ones score 0)
            subcriterion_codes=claimed_subcriteria(assessment.parameter_data or {}, get_college_parameters(), COLLEGE_PARAMETER_CODES),
        )


    @classmethod
    @transaction.atomic
    def submit_assessment(
        cls,
        assessment_id: str,
        submitting_user: Any = None,
    ) -> CollegeAssessment:
        """
        Submits a College assessment for review.
        Validates ownership, state (must be DRAFT), and parameter inputs.
        """
        try:
            assessment = CollegeAssessment.objects.select_for_update().get(assessment_id=assessment_id)
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.")

        if assessment.status != "DRAFT":
            raise InvalidStateTransitionError(
                f"Cannot submit assessment in '{assessment.status}' status. Only DRAFT assessments can be submitted."
            )

        if submitting_user and getattr(submitting_user, "is_authenticated", False):
            if not (
                getattr(submitting_user, "is_superuser", False)
                or getattr(submitting_user, "role", "") in ("admin", "state_admin")
            ):
                user_college = getattr(submitting_user, "college", None)
                if not user_college or user_college.pk != assessment.college_id:
                    raise CollegeNotAuthorizedError(
                        f"User '{getattr(submitting_user, 'email', '')}' is not authorized to submit assessment for '{assessment.college.name}'.",
                        code="ASSESSMENT_NOT_AUTHORIZED"
                    )

        # Ensure parameters have been populated
        if not assessment.parameter_data:
            raise CollegeValidationError(
                "Cannot submit assessment with empty parameter data. Complete parameter responses before submission.",
                code="PARAMETER_DATA_REQUIRED",
            )

        # Invalid values, period-bound claims without dates and out-of-period claims must be corrected first
        errors = submission_errors(assessment.parameter_data, get_college_parameters(), COLLEGE_PARAMETER_CODES)
        if errors:
            raise CollegeValidationError(
                f"Submission blocked: {len(errors)} input issue(s) must be corrected. " + "; ".join(
                    f"{e.get('subcriterion') or e.get('parameter')} {e['field']}: {e['message']}" for e in errors[:5]),
                code="SUBMISSION_VALIDATION_FAILED",
                details=errors,
            )

        prev_status = assessment.status
        assessment.status = "SUBMITTED"
        assessment.submitted_at = timezone.now()
        assessment.save(update_fields=["status", "submitted_at", "updated_at"])

        CollegeAssessmentAuditLog.objects.create(
            assessment=assessment,
            actor=submitting_user if submitting_user and getattr(submitting_user, "is_authenticated", False) else None,
            action="SUBMITTED",
            previous_state=prev_status,
            new_state="SUBMITTED",
            reason="Formal submission by institution",
        )

        return assessment

    @classmethod
    @transaction.atomic
    def transition_state(
        cls,
        assessment_id: str,
        target_status: str,
        actor: Any = None,
    ) -> CollegeAssessment:
        """
        Safely transitions assessment lifecycle state.
        Permitted transitions:
        - DRAFT -> SUBMITTED (Institutional user / Admin)
        - SUBMITTED -> UNDER_REVIEW, DRAFT, REJECTED
        - UNDER_REVIEW -> DRAFT, REJECTED, CERTIFIED
        - REJECTED is terminal.
        - CERTIFIED is terminal.
        """
        clean_target = target_status.strip().upper()
        try:
            assessment = CollegeAssessment.objects.select_for_update().select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        current = assessment.status

        # If already in target status, return cleanly
        if current == clean_target:
            return assessment

        valid_transitions = {
            "DRAFT": {"SUBMITTED"},
            "SUBMITTED": {"UNDER_REVIEW", "DRAFT", "REJECTED"},
            "UNDER_REVIEW": {"DRAFT", "REJECTED", "CERTIFIED"},
            "REJECTED": set(),
            "CERTIFIED": set(),
        }

        allowed = valid_transitions.get(current, set())
        if clean_target not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid assessment lifecycle transition: '{current}' -> '{clean_target}'."
            )

        actor_role = getattr(actor, "role", "")
        is_admin = getattr(actor, "is_superuser", False) or actor_role in ("admin", "state_admin")

        # Reviewer-only transitions check
        if clean_target in ("UNDER_REVIEW", "REJECTED", "CERTIFIED", "DRAFT"):
            if not is_admin and actor_role not in ("committee", "committee_chair"):
                raise CollegeNotAuthorizedError(
                    f"Only committee reviewers and administrators can transition assessment to '{clean_target}'.",
                    code="ASSESSMENT_NOT_AUTHORIZED"
                )

        if clean_target == "SUBMITTED":
            return cls.submit_assessment(assessment_id, submitting_user=actor)

        prev_status = assessment.status
        assessment.status = clean_target
        assessment.save(update_fields=["status", "updated_at"])

        CollegeAssessmentAuditLog.objects.create(
            assessment=assessment,
            actor=actor if actor and getattr(actor, "is_authenticated", False) else None,
            action=f"STATUS_TRANSITION_{clean_target}",
            previous_state=prev_status,
            new_state=clean_target,
            reason=f"Status transitioned to {clean_target}",
        )

        return assessment


class CollegeReviewService:
    """
    Authoritative domain service orchestrating the College Assessment review
    and certification lifecycle for the Screening Committee and DHE Admins.
    """

    @classmethod
    def validate_reviewer_authorization(cls, reviewer: Any, assessment: CollegeAssessment) -> bool:
        """
        Validates that a reviewer possesses the required committee role,
        has active framework authorization, and does not have an institutional conflict of interest.
        """
        if not reviewer or not getattr(reviewer, "is_authenticated", False):
            raise ReviewNotAuthorizedError("Authentication required to review assessments.")

        role = getattr(reviewer, "role", "")
        is_admin = (
            getattr(reviewer, "is_superuser", False)
            or getattr(reviewer, "is_staff", False)
            or role in ("admin", "state_admin")
        )

        if not is_admin and role not in ("committee", "committee_chair"):
            raise ReviewNotAuthorizedError("Only Screening Committee members and Administrators can review College assessments.")

        # Institutional conflict of interest check
        reviewer_college = getattr(reviewer, "college", None)
        if reviewer_college:
            if (
                getattr(reviewer_college, "aishe_code", "") == assessment.college.aishe_code
                or getattr(reviewer_college, "pk", None) == assessment.college_id
            ):
                raise ReviewConflictError(
                    f"Conflict of interest: Reviewer is affiliated with institution '{assessment.college.name}'."
                )

        # University Vice Chancellor / University user cannot act as College reviewer
        if role == "vice_chancellor" or (
            getattr(reviewer, "university", None)
            and not reviewer_college
            and role not in ("admin", "state_admin", "committee", "committee_chair")
        ):
            raise ReviewNotAuthorizedError("University officials cannot review College assessments.")

        # Check explicit ReviewerAuthorization
        if not is_admin:
            user_auths = ReviewerAuthorization.objects.filter(user=reviewer, is_active=True)
            if user_auths.exists():
                fw_matching = user_auths.filter(framework__in=[COLLEGE_FRAMEWORK_CODE, "ALL"])
                if not fw_matching.exists():
                    raise FrameworkMismatchError(
                        f"Reviewer is not authorized for framework '{assessment.framework}'."
                    )
                inst_matching = fw_matching.filter(
                    institution_id__in=["", assessment.college.aishe_code, str(assessment.college.pk)]
                )
                if not inst_matching.exists():
                    raise ReviewNotAuthorizedError(
                        f"Reviewer is not authorized for institution '{assessment.college.aishe_code}'."
                    )

        return True

    @classmethod
    def validate_certification_authority(cls, actor: Any, assessment: CollegeAssessment) -> bool:
        """
        Validates that an actor has explicit certification authority.
        Only the Screening Committee Chair can certify assessments.
        Standard committee reviewers and institutional users are blocked.
        """
        if not actor or not getattr(actor, "is_authenticated", False):
            raise CertificationNotAuthorizedError("Authentication required to certify assessments.")

        if getattr(actor, "role", "") != "committee_chair":
            raise CertificationNotAuthorizedError(
                "Certification authority required. Only the Screening Committee Chair can certify assessments."
            )

        # Institutional conflict of interest check
        actor_college = getattr(actor, "college", None)
        if actor_college:
            if (
                getattr(actor_college, "aishe_code", "") == assessment.college.aishe_code
                or getattr(actor_college, "pk", None) == assessment.college_id
            ):
                raise ReviewConflictError(
                    f"Conflict of interest: Certification authority is affiliated with institution '{assessment.college.name}'."
                )

        return True

    @classmethod
    def record_audit(
        cls,
        assessment: CollegeAssessment,
        actor: Any,
        action: str,
        previous_status: str,
        new_status: str,
        reason: str = "",
    ) -> CollegeAssessmentAuditLog:
        """Creates an append-only audit log entry."""
        return CollegeAssessmentAuditLog.objects.create(
            assessment=assessment,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=action,
            previous_state=previous_status,
            new_state=new_status,
            reason=reason,
        )

    @classmethod
    @transaction.atomic
    def start_review(
        cls,
        assessment_id: str,
        reviewer: Any,
        comments: str = "",
    ) -> Tuple[CollegeAssessment, CollegeReviewRecord]:
        """
        Begins committee review on a submitted College assessment.
        Transitions state: SUBMITTED -> UNDER_REVIEW.
        """
        try:
            assessment = CollegeAssessment.objects.select_for_update().select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        cls.validate_reviewer_authorization(reviewer, assessment)

        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is already certified and immutable.")
        if assessment.status in ("REJECTED", "BLOCKED"):
            raise AssessmentLockedError("Assessment is rejected/blocked and locked.")

        if assessment.status not in ("SUBMITTED", "UNDER_REVIEW"):
            raise InvalidReviewStateError(
                f"Cannot start review on assessment in '{assessment.status}' status. Must be 'SUBMITTED'."
            )

        prev_status = assessment.status
        assessment.status = "UNDER_REVIEW"
        assessment.assigned_reviewer = reviewer
        assessment.save(update_fields=["status", "assigned_reviewer", "updated_at"])

        review_rec = CollegeReviewRecord.objects.create(
            assessment=assessment,
            reviewer=reviewer,
            action=CollegeReviewAction.START_REVIEW,
            status_before=prev_status,
            status_after="UNDER_REVIEW",
            comments=comments,
        )

        cls.record_audit(
            assessment=assessment,
            actor=reviewer,
            action="REVIEW_STARTED",
            previous_status=prev_status,
            new_status="UNDER_REVIEW",
            reason=comments,
        )

        return assessment, review_rec

    @classmethod
    @transaction.atomic
    def evaluate_assessment(
        cls,
        assessment_id: str,
        actor: Any,
        reviewer_adjustments: Optional[List[ReviewerAdjustment]] = None,
    ) -> Tuple[CollegeAssessment, FrameworkResult, CollegeReviewRecord]:
        """
        Executes scoring evaluation via the frozen engine and logs review audit.
        Status remains UNDER_REVIEW; action is recorded in CollegeReviewRecord.
        """
        try:
            assessment = CollegeAssessment.objects.select_for_update().select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        cls.validate_reviewer_authorization(actor, assessment)

        if assessment.status == "DRAFT":
            raise ScoringBlockedError("Cannot evaluate scoring on DRAFT assessment. Assessment must be submitted first.")
        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is certified and immutable.")
        if assessment.status in ("REJECTED", "BLOCKED"):
            raise AssessmentLockedError("Assessment is rejected/blocked and locked.")

        prev_status = assessment.status
        result = CollegeAssessmentService.evaluate_assessment_scoring(
            assessment_id=assessment.assessment_id,
            reviewer_adjustments=reviewer_adjustments,
        )
        assessment.refresh_from_db()

        snapshot = {
            "calculation_id": result.calculation_id,
            "raw_total": result.raw_total,
            "evidence_gated_total": result.evidence_gated_total,
            "final_certified_total": result.final_certified_total,
            "certification_status": result.certification_status.value if hasattr(result.certification_status, "value") else str(result.certification_status),
            "blocking_reasons": result.blocking_reasons,
        }

        review_rec = CollegeReviewRecord.objects.create(
            assessment=assessment,
            reviewer=actor,
            action=CollegeReviewAction.EVALUATE,
            status_before=prev_status,
            status_after=assessment.status,
            scoring_snapshot=snapshot,
        )

        cls.record_audit(
            assessment=assessment,
            actor=actor,
            action="EVALUATION_TRIGGERED",
            previous_status=prev_status,
            new_status=assessment.status,
            reason=f"Scoring evaluated: {result.evidence_gated_total} marks",
        )

        return assessment, result, review_rec

    @classmethod
    @transaction.atomic
    def complete_review(
        cls,
        assessment_id: str,
        reviewer: Any,
        comments: str = "",
    ) -> Tuple[CollegeAssessment, CollegeReviewRecord]:
        """
        Completes committee review.
        Verifies evidence readiness and scoring evaluation.
        Status remains UNDER_REVIEW; action is recorded in CollegeReviewRecord.
        """
        try:
            assessment = CollegeAssessment.objects.select_for_update().select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        cls.validate_reviewer_authorization(reviewer, assessment)

        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is already certified and immutable.")
        if assessment.status in ("REJECTED", "BLOCKED"):
            raise AssessmentLockedError("Assessment is rejected/blocked and locked.")

        if assessment.status != "UNDER_REVIEW":
            raise InvalidReviewStateError(
                f"Cannot complete review on assessment in '{assessment.status}' status. Assessment must be in 'UNDER_REVIEW' status."
            )

        # Gate: Evidence readiness check via Phase 5D ReviewReadinessReport
        # Uses structured classification to distinguish:
        #   MISSING/PENDING  -> hard blockers (completion prevented)
        #   REJECTED         -> correction-required state (reviewer must Return to Institution)
        #   SOURCE_SILENT    -> not a documentary requirement, never blocks
        #   UNRESOLVED       -> governance issue, not institution failure
        is_complete_allowed, review_readiness, summary = CollegeAssessmentService.get_review_readiness(
            assessment.assessment_id, user=reviewer
        )

        if not is_complete_allowed:
            # Build a human-readable error distinguishing the deficiency categories
            error_parts = []

            if review_readiness.blocking_reasons:
                error_parts.append(
                    "Evidence requirements incomplete (missing or pending): "
                    + "; ".join(review_readiness.blocking_reasons)
                )

            if review_readiness.correction_required_reasons:
                error_parts.append(
                    "Rejected evidence found — use 'Return to Institution' to request correction: "
                    + "; ".join(review_readiness.correction_required_reasons)
                )

            if not error_parts:
                error_parts.append("Evidence requirements incomplete.")

            raise EvidenceNotReadyError(
                f"Cannot complete review: {' | '.join(error_parts)}"
            )

        # Gate: authoritative scoring is FINALIZABLE and every parameter is approved at its current score
        result = CollegeAssessmentService.evaluate_assessment_scoring(assessment.assessment_id, persist=True)
        assessment.refresh_from_db()
        gate_errors = certification_gate_errors(result, assessment.parameter_data or {}, COLLEGE_PARAMETER_CODES)
        if gate_errors:
            raise CertificationBlockedError("Cannot complete review: " + " | ".join(gate_errors))

        prev_status = assessment.status
        # Status remains UNDER_REVIEW; review action recorded in CollegeReviewRecord

        evid_snapshot = {
            "is_complete_allowed": is_complete_allowed,
            "blocking_reasons": review_readiness.blocking_reasons if review_readiness else [],
            "correction_required_reasons": review_readiness.correction_required_reasons if review_readiness else [],
            "governance_reasons": review_readiness.governance_reasons if review_readiness else [],
            "source_silent_subcriteria": review_readiness.source_silent_subcriteria if review_readiness else [],
            "total_evaluated": getattr(summary, "active_documentary_subcriteria", 0) if summary else 0,
            "total_covered": getattr(summary, "verified_subcriteria", 0) if summary else 0,
        }

        review_rec = CollegeReviewRecord.objects.create(
            assessment=assessment,
            reviewer=reviewer,
            action=CollegeReviewAction.COMPLETE_REVIEW,
            status_before=prev_status,
            status_after=assessment.status,
            comments=comments,
            evidence_readiness_snapshot=evid_snapshot,
            scoring_snapshot={"certified_score": assessment.certified_score, "status": assessment.certification_status},
        )

        cls.record_audit(
            assessment=assessment,
            actor=reviewer,
            action="REVIEW_COMPLETED",
            previous_status=prev_status,
            new_status=assessment.status,
            reason=comments,
        )

        return assessment, review_rec

    @classmethod
    @transaction.atomic
    def return_for_correction(
        cls,
        assessment_id: str,
        reviewer: Any,
        reason: str,
        comments: str = "",
    ) -> Tuple[CollegeAssessment, CollegeReviewRecord]:
        """
        Returns assessment to institution for correction. Requires meaningful reason.
        Transitions state to DRAFT (Phase 7A correction state).
        """
        try:
            assessment = CollegeAssessment.objects.select_for_update().select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        cls.validate_reviewer_authorization(reviewer, assessment)

        if not reason or not reason.strip():
            raise CollegeValidationError(
                "A meaningful reason is mandatory when returning an assessment for correction.",
                code="REASON_REQUIRED"
            )

        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is already certified and immutable.")
        if assessment.status in ("REJECTED", "BLOCKED"):
            raise AssessmentLockedError("Assessment is rejected/blocked and locked.")

        if assessment.status not in ("SUBMITTED", "UNDER_REVIEW"):
            raise InvalidReviewStateError(
                f"Cannot return assessment in '{assessment.status}' status for correction. Must be in 'SUBMITTED' or 'UNDER_REVIEW' status."
            )

        prev_status = assessment.status
        assessment.status = "DRAFT"
        assessment.save(update_fields=["status", "updated_at"])

        review_rec = CollegeReviewRecord.objects.create(
            assessment=assessment,
            reviewer=reviewer,
            action=CollegeReviewAction.RETURN_FOR_CORRECTION,
            status_before=prev_status,
            status_after="DRAFT",
            reason=reason.strip(),
            comments=comments,
        )

        cls.record_audit(
            assessment=assessment,
            actor=reviewer,
            action="RETURNED_FOR_CORRECTION",
            previous_status=prev_status,
            new_status="DRAFT",
            reason=reason.strip(),
        )

        return assessment, review_rec

    @classmethod
    @transaction.atomic
    def block_review(
        cls,
        assessment_id: str,
        reviewer: Any,
        reason: str,
        comments: str = "",
    ) -> Tuple[CollegeAssessment, CollegeReviewRecord]:
        """
        Blocks review on an assessment due to policy or irremediable violations.
        Requires meaningful reason. Transitions state to REJECTED.
        """
        try:
            assessment = CollegeAssessment.objects.select_for_update().select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        cls.validate_reviewer_authorization(reviewer, assessment)

        if not reason or not reason.strip():
            raise CollegeValidationError(
                "A meaningful reason is mandatory when blocking an assessment review.",
                code="REASON_REQUIRED"
            )

        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is already certified and immutable.")

        prev_status = assessment.status
        assessment.status = "REJECTED"
        assessment.save(update_fields=["status", "updated_at"])

        review_rec = CollegeReviewRecord.objects.create(
            assessment=assessment,
            reviewer=reviewer,
            action=CollegeReviewAction.BLOCK_REVIEW,
            status_before=prev_status,
            status_after="REJECTED",
            reason=reason.strip(),
            comments=comments,
        )

        cls.record_audit(
            assessment=assessment,
            actor=reviewer,
            action="REVIEW_BLOCKED",
            previous_status=prev_status,
            new_status="REJECTED",
            reason=reason.strip(),
        )

        return assessment, review_rec

    @classmethod
    @transaction.atomic
    def certify_assessment(
        cls,
        assessment_id: str,
        actor: Any,
        remarks: str = "",
    ) -> Tuple[CollegeAssessment, CollegeReviewRecord]:
        """
        Certifies a College assessment after strictly verifying all 11 Statutory Gates.
        Locks the assessment against further modifications.
        """
        try:
            assessment = CollegeAssessment.objects.select_for_update().select_related("college").get(
                assessment_id=assessment_id
            )
        except CollegeAssessment.DoesNotExist:
            raise CollegeValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        # Gate 3 & 9: Authorized certification actor and conflict-of-interest check
        cls.validate_certification_authority(actor, assessment)

        # Immutability check
        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is already certified and immutable.")
        if assessment.status in ("REJECTED", "BLOCKED"):
            raise AssessmentLockedError("Cannot certify an assessment in REJECTED status.")

        # Gate 1: Framework check
        if assessment.framework != COLLEGE_FRAMEWORK_CODE:
            raise FrameworkMismatchError(
                f"Assessment framework mismatch: '{assessment.framework}' is not '{COLLEGE_FRAMEWORK_CODE}'."
            )

        # Gate 2: Assessment period statutory check
        if (
            assessment.academic_year != "2025-26"
            or assessment.period_start > date(2025, 7, 1)
            or assessment.period_end < date(2026, 6, 30)
        ):
            raise CollegeValidationError(
                "Invalid assessment period for 2026 statutory cycle.",
                code="INVALID_ASSESSMENT_PERIOD"
            )

        # Gate 4: Valid lifecycle state (must be UNDER_REVIEW)
        if assessment.status != "UNDER_REVIEW":
            raise InvalidReviewStateError(
                f"Cannot certify assessment in '{assessment.status}' status. Assessment must be in 'UNDER_REVIEW' status."
            )

        # Gate 10: Framework Isolation Gate - No invalid or cross-framework evidence
        foreign_assocs = EvidenceSubcriterionAssociation.objects.filter(
            evidence__assessment_id=assessment.assessment_id,
            is_active=True,
        ).exclude(evidence__framework=COLLEGE_FRAMEWORK_CODE)
        if foreign_assocs.exists():
            raise FrameworkMismatchError("Certification blocked: Found active evidence associated with non-College framework.")

        # Gate 5: Evidence readiness gate via Phase 5D
        is_ready, blocking_reasons, summary = CollegeAssessmentService.check_assessment_readiness(
            assessment.assessment_id, user=actor
        )
        if not is_ready or blocking_reasons:
            reasons_str = "; ".join(blocking_reasons) if blocking_reasons else "Evidence requirements incomplete"
            raise CertificationBlockedError(f"Certification blocked by evidence: {reasons_str}")

        # Gate 6, 7, 8 & 11: authoritative scoring is FINALIZABLE and every parameter is approved
        # at its current backend score (committee total == certified total)
        result = CollegeAssessmentService.evaluate_assessment_scoring(assessment.assessment_id, persist=True)
        assessment.refresh_from_db()
        gate_errors = certification_gate_errors(result, assessment.parameter_data or {}, COLLEGE_PARAMETER_CODES)
        if gate_errors or result.final_certified_total is None:
            raise CertificationBlockedError(
                "Certification blocked: " + " | ".join(gate_errors or ["Scoring engine did not produce a certified total."])
            )

        # ALL 11 GATES PASSED: Transition to CERTIFIED and lock
        prev_status = assessment.status
        assessment.status = "CERTIFIED"
        assessment.certification_status = "CERTIFIED"
        assessment.certified_score = result.final_certified_total
        frozen = dict(assessment.parameter_data or {})
        frozen[SNAPSHOT_KEY] = build_certified_snapshot(result, COLLEGE_PARAMETERS)
        assessment.parameter_data = frozen
        assessment.save(update_fields=["status", "certification_status", "certified_score", "parameter_data", "updated_at"])

        scoring_snap = {
            "certified_total": assessment.certified_score,
            "raw_total": result.raw_total,
            "evidence_gated_total": result.evidence_gated_total,
            "certification_status": "CERTIFIED",
            "calculation_id": result.calculation_id,
        }

        review_rec = CollegeReviewRecord.objects.create(
            assessment=assessment,
            reviewer=actor,
            action=CollegeReviewAction.CERTIFY,
            status_before=prev_status,
            status_after="CERTIFIED",
            reason=remarks,
            scoring_snapshot=scoring_snap,
        )

        cls.record_audit(
            assessment=assessment,
            actor=actor,
            action="CERTIFICATION_SUCCEEDED",
            previous_status=prev_status,
            new_status="CERTIFIED",
            reason=remarks,
        )

        return assessment, review_rec

    @classmethod
    def get_review_queue(cls, user: Any, filters: Optional[Dict[str, Any]] = None):
        """
        Retrieves the College assessment review queue for authorized committee reviewers and admins.
        Excludes assessments with institutional conflict of interest.
        """
        if not user or not getattr(user, "is_authenticated", False):
            raise ReviewNotAuthorizedError("Authentication required to access review queue.")

        role = getattr(user, "role", "")
        is_admin = (
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or role in ("admin", "state_admin")
        )

        if not is_admin and role not in ("committee", "committee_chair"):
            raise ReviewNotAuthorizedError("Only committee reviewers and administrators can access the review queue.")

        qs = CollegeAssessment.objects.filter(
            framework=COLLEGE_FRAMEWORK_CODE
        ).exclude(status="DRAFT").select_related("college", "assigned_reviewer")

        # Conflict-of-interest exclusion: Exclude reviewer's own college
        user_college = getattr(user, "college", None)
        if user_college:
            qs = qs.exclude(college_id=user_college.pk)

        # Scoped ReviewerAuthorization check
        if not is_admin:
            user_auths = ReviewerAuthorization.objects.filter(user=user, is_active=True)
            if user_auths.exists():
                fw_matching = user_auths.filter(framework__in=[COLLEGE_FRAMEWORK_CODE, "ALL"])
                if not fw_matching.exists():
                    return CollegeAssessment.objects.none()

                scoped_insts = list(
                    fw_matching.exclude(institution_id="").values_list("institution_id", flat=True)
                )
                has_global = fw_matching.filter(institution_id="").exists()
                if not has_global:
                    if scoped_insts:
                        from django.db.models import Q
                        qs = qs.filter(
                            Q(college__aishe_code__in=scoped_insts) |
                            Q(college__id__in=[int(x) for x in scoped_insts if x.isdigit()])
                        )
                    else:
                        return CollegeAssessment.objects.none()

        # Apply optional filters
        if filters:
            if filters.get("status"):
                qs = qs.filter(status=filters["status"])
            if filters.get("college_id"):
                qs = qs.filter(college_id=filters["college_id"])
            if filters.get("aishe_code"):
                qs = qs.filter(college__aishe_code=filters["aishe_code"])

        return qs.order_by("-submitted_at", "-created_at")
