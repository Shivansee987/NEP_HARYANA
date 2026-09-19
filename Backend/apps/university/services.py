"""
NEP Excellence Awards 2026 - University Assessment Orchestration Service
Coordinates University assessments, evidence associations, and scoring execution
through the frozen server-authoritative scoring engine and Phase 5 evidence subsystem.
"""
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import uuid

from django.db import transaction
from django.utils import timezone

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
)
from .models import (
    University,
    UniversityAssessment,
    UniversityAssessmentAuditLog,
    UniversityReviewAction,
    UniversityReviewRecord,
)
from .registry import (
    UNIVERSITY_FRAMEWORK_CODE,
    UNIVERSITY_PARAMETER_CODES,
    get_university_parameters,
    validate_university_parameter_code,
)
from .validators import (
    AssessmentAlreadyCertifiedError,
    AssessmentLockedError,
    AssessmentNotReadyError,
    CertificationBlockedError,
    CertificationNotAuthorizedError,
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
    UniversityNotAuthorizedError,
    UniversityValidationError,
    validate_framework_code,
    validate_institution_type,
    validate_parameter,
    validate_temporal_activity_date,
)


class UniversityAssessmentService:
    """
    Primary service layer for University assessments.
    Enforces framework isolation, strictly delegates scoring to the frozen engine,
    and bridges University evidence to the Phase 5 infrastructure.
    """

    @classmethod
    @transaction.atomic
    def create_assessment(
        cls,
        university_id: Any,
        assessment_id: Optional[str] = None,
        academic_year: str = "2025-26",
        created_by: Any = None,
    ) -> UniversityAssessment:
        """
        Initializes a new University assessment session.
        Guarantees distinct University institution context.
        """
        if isinstance(university_id, University):
            university = university_id
        else:
            try:
                if str(university_id).isdigit():
                    university = University.objects.get(pk=int(university_id))
                else:
                    university = University.objects.get(aishe_code=str(university_id))
            except University.DoesNotExist:
                raise UniversityValidationError(f"University '{university_id}' not found.")

        if not university.is_active:
            raise UniversityValidationError(f"University '{university.name}' is not active.")

        if not assessment_id:
            assessment_id = f"ASSESS-2026-UNI-{university.aishe_code}-{uuid.uuid4().hex[:8].upper()}"

        assessment = UniversityAssessment.objects.create(
            assessment_id=assessment_id,
            university=university,
            framework=UNIVERSITY_FRAMEWORK_CODE,
            academic_year=academic_year,
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            status="DRAFT",
            parameter_data={},
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
    ) -> UniversityAssessment:
        """
        Validates and records parameter data for a specific University parameter (U1–U20).
        """
        param_clean = validate_parameter(parameter_code)
        try:
            assessment = UniversityAssessment.objects.select_for_update().get(assessment_id=assessment_id)
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.")

        if assessment.status in ("FINALIZED", "CERTIFIED"):
            raise UniversityValidationError(f"Assessment '{assessment_id}' is finalized and cannot be modified.")

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
        return assessment

    @classmethod
    def build_assessment_input(cls, assessment_id: str) -> AssessmentInput:
        """
        Assembles the authoritative domain AssessmentInput for the frozen scoring engine.
        Gathers raw parameter inputs and active verified/pending evidence associations.
        """
        try:
            assessment = UniversityAssessment.objects.select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.")

        # 1. Assessment Context
        context = AssessmentContext(
            assessment_id=assessment.assessment_id,
            institution_id=assessment.university.aishe_code,
            institution_type=InstitutionType.UNIVERSITY,
            framework=FrameworkType.UNIVERSITY_2026,
            assessment_period=AssessmentPeriod(
                start_date=assessment.period_start,
                end_date=assessment.period_end,
                academic_year=assessment.academic_year,
            ),
            is_active=assessment.university.is_active,
            lifecycle_status=assessment.status,
        )

        # 2. Gather Evidence Associations for this assessment
        # Framework and institution isolation check
        associations = EvidenceSubcriterionAssociation.objects.filter(
            evidence__assessment_id=assessment.assessment_id,
            is_active=True,
        ).select_related("evidence")

        # Map evidence docs to scoring domain objects by subcriterion
        subcrit_evidence_map: Dict[str, List[ScoringEvidenceDoc]] = {}
        for assoc in associations:
            doc = assoc.evidence
            # Framework isolation: University assessment cannot accept non-University evidence
            if doc.framework != UNIVERSITY_FRAMEWORK_CODE:
                continue

            scoring_state = EvidenceState.EVIDENCE_PENDING
            if doc.status == EvidenceLifecycleState.EVIDENCE_VERIFIED:
                scoring_state = EvidenceState.EVIDENCE_VERIFIED
            elif doc.status == EvidenceLifecycleState.EVIDENCE_REJECTED:
                scoring_state = EvidenceState.EVIDENCE_REJECTED
            elif doc.status == EvidenceLifecycleState.EVIDENCE_PRESENT:
                scoring_state = EvidenceState.EVIDENCE_PRESENT

            scoring_doc = ScoringEvidenceDoc(
                document_id=str(doc.document_id),
                document_type=doc.evidence_type,
                status=scoring_state,
                verified_by=str(doc.assigned_reviewer.pk) if doc.assigned_reviewer else None,
                file_checksum=doc.file_checksum,
                academic_year=assoc.academic_year,
            )
            subcrit_evidence_map.setdefault(assoc.subcriterion_id, []).append(scoring_doc)

        # 3. Build ParameterInput for all U1–U20 parameters
        parameters_input: Dict[str, ParameterInput] = {}
        param_data = assessment.parameter_data or {}
        registered_params = get_university_parameters()

        for param_code in UNIVERSITY_PARAMETER_CODES:
            param_conf = registered_params[param_code]
            stored_param = param_data.get(param_code, {})
            stored_raw = stored_param.get("raw_inputs", {})
            stored_entities = stored_param.get("entities", [])
            act_date = date.fromisoformat(stored_param["activity_date"]) if stored_param.get("activity_date") else None

            # Subcriteria inputs
            sub_inputs: Dict[str, SubcriterionInput] = {}
            for sub_code in param_conf.get("subcriteria", {}).keys():
                evid_docs = subcrit_evidence_map.get(sub_code, [])

                # Map entity models if present
                asset_entities = [
                    AssetEntity(
                        entity_id=e.get("entity_id", str(uuid.uuid4())),
                        entity_type=e.get("entity_type", "PROGRAMME"),
                        identifier_key=e.get("identifier_key", ""),
                        date_of_record=date.fromisoformat(e["date_of_record"]) if e.get("date_of_record") else None,
                        title=e.get("title", ""),
                    )
                    for e in stored_entities
                ]

                sub_inputs[sub_code] = SubcriterionInput(
                    subcriterion_code=sub_code,
                    raw_inputs=stored_raw.get(sub_code, stored_raw),
                    evidence_docs=evid_docs,
                    entities=asset_entities,
                    activity_date=act_date,
                )

            parameters_input[param_code] = ParameterInput(
                parameter_code=param_code,
                subcriteria_inputs=sub_inputs,
                raw_inputs=stored_raw,
                evidence_docs=[d for docs in sub_inputs.values() for d in docs.evidence_docs],
            )

        return AssessmentInput(context=context, parameters=parameters_input)

    @classmethod
    def evaluate_assessment_scoring(
        cls,
        assessment_id: str,
        reviewer_adjustments: Optional[List[ReviewerAdjustment]] = None,
    ) -> FrameworkResult:
        """
        Executes scoring exclusively via the frozen NEP2026ScoringEngine.
        Does NOT recalculate or synthesize scores in this service layer.
        """
        assessment_input = cls.build_assessment_input(assessment_id)
        engine = NEP2026ScoringEngine()
        result = engine.score_assessment(
            assessment_input=assessment_input,
            reviewer_adjustments=reviewer_adjustments,
        )

        # Cache certified score summary on the assessment instance
        UniversityAssessment.objects.filter(assessment_id=assessment_id).update(
            certified_score=result.evidence_gated_total,
            certification_status=result.certification_status.value,
            updated_at=timezone.now(),
        )

        return result

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
            assessment = UniversityAssessment.objects.select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.")

        return EvidenceService.evaluate_evidence_coverage(
            assessment_id=assessment.assessment_id,
            institution_id=assessment.university.aishe_code,
            framework=UNIVERSITY_FRAMEWORK_CODE,
            requesting_user=user,
        )

    @classmethod
    def check_assessment_readiness(
        cls,
        assessment_id: str,
        user: Any = None,
    ) -> Tuple[bool, List[str], CoverageSummary]:
        """
        Checks whether University assessment evidence is complete and ready for scoring review.
        """
        try:
            assessment = UniversityAssessment.objects.select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.")

        eval_user = user
        if user and (
            getattr(user, "is_superuser", False)
            or getattr(user, "role", "") in ("state_admin", "committee")
        ):
            eval_user = user
        else:
            # Pass None for internal service invocation when user is admin, committee_chair, or other authorized service actor
            eval_user = None

        return EvidenceService.is_assessment_evidence_ready(
            assessment_id=assessment.assessment_id,
            institution_id=assessment.university.aishe_code,
            framework=UNIVERSITY_FRAMEWORK_CODE,
            requesting_user=eval_user,
        )

    @classmethod
    @transaction.atomic
    def submit_assessment(
        cls,
        assessment_id: str,
        submitting_user: Any = None,
    ) -> UniversityAssessment:
        """
        Submits a University assessment for review.
        Validates ownership, state (must be DRAFT), required parameter inputs,
        and evidence readiness via Phase 5D.
        """
        try:
            assessment = UniversityAssessment.objects.select_for_update().select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        # Ownership validation
        if submitting_user and not (
            getattr(submitting_user, "is_superuser", False)
            or getattr(submitting_user, "role", "") in ("admin", "state_admin")
        ):
            user_uni = getattr(submitting_user, "university", None)
            if not user_uni or user_uni.pk != assessment.university_id:
                raise UniversityNotAuthorizedError(
                    f"User '{getattr(submitting_user, 'email', '')}' is not authorized to submit assessment for '{assessment.university.name}'.",
                    code="ASSESSMENT_NOT_AUTHORIZED"
                )

        if assessment.status != "DRAFT":
            raise InvalidStateTransitionError(
                f"Cannot submit assessment in '{assessment.status}' status. Only DRAFT assessments can be submitted."
            )

        if not assessment.parameter_data:
            raise UniversityValidationError(
                "Cannot submit assessment: No parameter data inputs recorded.",
                code="INVALID_PARAMETER_INPUT"
            )

        is_ready, blocking_reasons, summary = cls.check_assessment_readiness(
            assessment_id, user=submitting_user
        )
        if not is_ready or blocking_reasons:
            reasons_str = "; ".join(blocking_reasons) if blocking_reasons else "Evidence requirements incomplete"
            raise EvidenceNotReadyError(
                f"Cannot submit assessment: Evidence is not ready. {reasons_str}"
            )

        assessment.status = "SUBMITTED"
        assessment.submitted_at = timezone.now()
        assessment.save(update_fields=["status", "submitted_at", "updated_at"])
        return assessment

    @classmethod
    @transaction.atomic
    def transition_status(
        cls,
        assessment_id: str,
        target_status: str,
        actor: Any = None,
    ) -> UniversityAssessment:
        """
        Safely transitions assessment lifecycle state.
        Permitted transitions:
        - DRAFT -> SUBMITTED (Institutional user / Admin)
        - SUBMITTED -> UNDER_REVIEW (Reviewer / Admin)
        - UNDER_REVIEW -> FINALIZED (Reviewer / Admin)
        - FINALIZED is terminal.
        """
        clean_target = target_status.strip().upper()
        try:
            assessment = UniversityAssessment.objects.select_for_update().select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        current = assessment.status

        # If already in target status, return cleanly
        if current == clean_target:
            return assessment

        valid_transitions = {
            "DRAFT": {"SUBMITTED"},
            "SUBMITTED": {"UNDER_REVIEW", "RETURNED", "BLOCKED"},
            "UNDER_REVIEW": {"EVALUATED", "CERTIFICATION_PENDING", "RETURNED", "BLOCKED", "FINALIZED"},
            "EVALUATED": {"CERTIFICATION_PENDING", "RETURNED", "BLOCKED", "UNDER_REVIEW", "CERTIFIED"},
            "CERTIFICATION_PENDING": {"CERTIFIED", "RETURNED", "BLOCKED"},
            "RETURNED": {"SUBMITTED", "UNDER_REVIEW", "BLOCKED"},
            "FINALIZED": {"CERTIFIED"},
            "BLOCKED": set(),
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
        if clean_target in ("UNDER_REVIEW", "EVALUATED", "CERTIFICATION_PENDING", "FINALIZED", "BLOCKED"):
            if not is_admin and actor_role not in ("committee", "committee_chair"):
                raise UniversityNotAuthorizedError(
                    f"Only committee reviewers and administrators can transition assessment to '{clean_target}'.",
                    code="ASSESSMENT_NOT_AUTHORIZED"
                )

        if clean_target == "SUBMITTED":
            return cls.submit_assessment(assessment_id, submitting_user=actor)

        assessment.status = clean_target
        assessment.save(update_fields=["status", "updated_at"])
        return assessment


class UniversityReviewService:
    """
    Authoritative domain service orchestrating the University Assessment review
    and certification lifecycle for the Screening Committee and DHE Admins.
    """

    @classmethod
    def validate_reviewer_authorization(cls, reviewer: Any, assessment: UniversityAssessment) -> bool:
        """
        Validates that a reviewer possesses the required committee role,
        has active framework authorization, and does not have an institutional conflict of interest.
        """
        if not reviewer or not getattr(reviewer, "is_authenticated", False):
            raise ReviewNotAuthorizedError("Authentication required to review assessments.")

        role = getattr(reviewer, "role", "")
        is_admin = getattr(reviewer, "is_superuser", False) or getattr(reviewer, "is_staff", False) or role in ("admin", "state_admin")

        if not is_admin and role not in ("committee", "committee_chair"):
            raise ReviewNotAuthorizedError("Only Screening Committee members and Administrators can review University assessments.")

        # Institutional conflict of interest check
        reviewer_uni = getattr(reviewer, "university", None)
        if reviewer_uni:
            if reviewer_uni.aishe_code == assessment.university.aishe_code or str(reviewer_uni.pk) == str(assessment.university_id):
                raise ReviewConflictError(
                    f"Conflict of interest: Reviewer is affiliated with institution '{assessment.university.name}'."
                )

        # College Principal cannot act as University reviewer
        if getattr(reviewer, "college", None) and role == "principal":
            raise ReviewNotAuthorizedError("College principals cannot review University assessments.")

        # Check explicit ReviewerAuthorization
        if not is_admin:
            user_auths = ReviewerAuthorization.objects.filter(user=reviewer, is_active=True)
            if user_auths.exists():
                fw_matching = user_auths.filter(framework__in=[UNIVERSITY_FRAMEWORK_CODE, "ALL"])
                if not fw_matching.exists():
                    raise FrameworkMismatchError(
                        f"Reviewer is not authorized for framework '{assessment.framework}'."
                    )
                inst_matching = fw_matching.filter(
                    institution_id__in=["", assessment.university.aishe_code, str(assessment.university.pk)]
                )
                if not inst_matching.exists():
                    raise ReviewNotAuthorizedError(
                        f"Reviewer is not authorized for institution '{assessment.university.aishe_code}'."
                    )

        return True

    @classmethod
    def validate_certification_authority(cls, actor: Any, assessment: UniversityAssessment) -> bool:
        """
        Validates that an actor has explicit certification authority.
        Only DHE Admins, Superusers, and Screening Committee Chairs can certify assessments.
        Standard committee reviewers and institutional users are blocked.
        """
        if not actor or not getattr(actor, "is_authenticated", False):
            raise CertificationNotAuthorizedError("Authentication required to certify assessments.")

        role = getattr(actor, "role", "")
        is_admin = getattr(actor, "is_superuser", False) or getattr(actor, "is_staff", False) or role in ("admin", "state_admin")
        is_chair = role == "committee_chair"

        if not (is_admin or is_chair):
            raise CertificationNotAuthorizedError(
                "Certification authority required. Only DHE Administrators and Committee Chairs can certify assessments."
            )

        # Institutional conflict of interest check
        actor_uni = getattr(actor, "university", None)
        if actor_uni:
            if actor_uni.aishe_code == assessment.university.aishe_code or str(actor_uni.pk) == str(assessment.university_id):
                raise ReviewConflictError(
                    f"Conflict of interest: Certification authority is affiliated with institution '{assessment.university.name}'."
                )

        return True

    @classmethod
    def record_audit(
        cls,
        assessment: UniversityAssessment,
        actor: Any,
        action: str,
        previous_status: str,
        new_status: str,
        outcome: str = "SUCCESS",
        reason: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> UniversityAssessmentAuditLog:
        """Creates an append-only audit log entry."""
        return UniversityAssessmentAuditLog.objects.create(
            assessment=assessment,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            outcome=outcome,
            reason=reason,
            payload=payload or {},
        )

    @classmethod
    @transaction.atomic
    def start_review(
        cls,
        assessment_id: str,
        reviewer: Any,
        comments: str = "",
    ) -> Tuple[UniversityAssessment, UniversityReviewRecord]:
        """
        Begins committee review on a submitted University assessment.
        Transitions state: SUBMITTED / RETURNED -> UNDER_REVIEW.
        """
        try:
            assessment = UniversityAssessment.objects.select_for_update().select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        cls.validate_reviewer_authorization(reviewer, assessment)

        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is already certified and immutable.")
        if assessment.status in ("FINALIZED",):
            raise AssessmentLockedError("Assessment is finalized and locked.")

        if assessment.status not in ("SUBMITTED", "RETURNED", "UNDER_REVIEW"):
            raise InvalidReviewStateError(
                f"Cannot start review on assessment in '{assessment.status}' status. Must be 'SUBMITTED' or 'RETURNED'."
            )

        prev_status = assessment.status
        assessment.status = "UNDER_REVIEW"
        assessment.assigned_reviewer = reviewer
        assessment.save(update_fields=["status", "assigned_reviewer", "updated_at"])

        review_rec = UniversityReviewRecord.objects.create(
            assessment=assessment,
            reviewer=reviewer,
            action=UniversityReviewAction.START_REVIEW,
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
    ) -> Tuple[UniversityAssessment, FrameworkResult, UniversityReviewRecord]:
        """
        Executes scoring evaluation via the frozen engine and logs review audit.
        """
        try:
            assessment = UniversityAssessment.objects.select_for_update().select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        cls.validate_reviewer_authorization(actor, assessment)

        if assessment.status == "DRAFT":
            raise ScoringBlockedError("Cannot evaluate scoring on DRAFT assessment. Assessment must be submitted first.")
        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is certified and immutable.")

        prev_status = assessment.status
        result = UniversityAssessmentService.evaluate_assessment_scoring(
            assessment_id=assessment.assessment_id,
            reviewer_adjustments=reviewer_adjustments,
        )
        assessment.refresh_from_db()

        if assessment.status == "UNDER_REVIEW":
            assessment.status = "EVALUATED"
            assessment.save(update_fields=["status", "updated_at"])

        snapshot = {
            "calculation_id": result.calculation_id,
            "raw_total": result.raw_total,
            "evidence_gated_total": result.evidence_gated_total,
            "final_certified_total": result.final_certified_total,
            "certification_status": result.certification_status.value,
            "blocking_reasons": result.blocking_reasons,
        }

        review_rec = UniversityReviewRecord.objects.create(
            assessment=assessment,
            reviewer=actor,
            action=UniversityReviewAction.EVALUATE,
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
            payload=snapshot,
        )

        return assessment, result, review_rec

    @classmethod
    @transaction.atomic
    def complete_review(
        cls,
        assessment_id: str,
        reviewer: Any,
        comments: str = "",
    ) -> Tuple[UniversityAssessment, UniversityReviewRecord]:
        """
        Completes committee review.
        Verifies evidence readiness and scoring evaluation before transitioning to CERTIFICATION_PENDING.
        """
        try:
            assessment = UniversityAssessment.objects.select_for_update().select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        cls.validate_reviewer_authorization(reviewer, assessment)

        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is already certified and immutable.")

        if assessment.status not in ("UNDER_REVIEW", "EVALUATED"):
            raise InvalidReviewStateError(
                f"Cannot complete review on assessment in '{assessment.status}' status. Assessment must be in 'UNDER_REVIEW' or 'EVALUATED' status."
            )

        # Gate: Evidence readiness check via Phase 5D
        is_ready, blocking_reasons, summary = UniversityAssessmentService.check_assessment_readiness(
            assessment.assessment_id, user=reviewer
        )
        if not is_ready or blocking_reasons:
            reasons_str = "; ".join(blocking_reasons) if blocking_reasons else "Evidence requirements incomplete"
            raise EvidenceNotReadyError(
                f"Cannot complete review: Evidence requirements incomplete. {reasons_str}"
            )

        # Gate: Scoring evaluation check
        if assessment.certified_score is None:
            UniversityAssessmentService.evaluate_assessment_scoring(assessment.assessment_id)
            assessment.refresh_from_db()

        if assessment.certification_status in ("BLOCKED_BY_SPECIFICATION", "BLOCKED_BY_EVIDENCE", "BLOCKED_BY_VALIDATION", "BLOCKED_BY_BOUNDARY"):
            raise CertificationBlockedError(
                f"Cannot complete review: Scoring is blocked ({assessment.certification_status})."
            )

        prev_status = assessment.status
        assessment.status = "CERTIFICATION_PENDING"
        assessment.save(update_fields=["status", "updated_at"])

        evid_snapshot = {
            "is_ready": is_ready,
            "blocking_reasons": blocking_reasons,
            "total_evaluated": getattr(summary, "total_evaluated", 0) if summary else 0,
            "total_covered": getattr(summary, "total_covered", 0) if summary else 0,
        }

        review_rec = UniversityReviewRecord.objects.create(
            assessment=assessment,
            reviewer=reviewer,
            action=UniversityReviewAction.COMPLETE_REVIEW,
            status_before=prev_status,
            status_after="CERTIFICATION_PENDING",
            comments=comments,
            evidence_readiness_snapshot=evid_snapshot,
            scoring_snapshot={"certified_score": assessment.certified_score, "status": assessment.certification_status},
        )

        cls.record_audit(
            assessment=assessment,
            actor=reviewer,
            action="REVIEW_COMPLETED",
            previous_status=prev_status,
            new_status="CERTIFICATION_PENDING",
            reason=comments,
            payload=evid_snapshot,
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
    ) -> Tuple[UniversityAssessment, UniversityReviewRecord]:
        """
        Returns assessment to institution for correction. Requires meaningful reason.
        Transitions state to RETURNED.
        """
        try:
            assessment = UniversityAssessment.objects.select_for_update().select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        cls.validate_reviewer_authorization(reviewer, assessment)

        if not reason or not reason.strip():
            raise UniversityValidationError(
                "A meaningful reason is mandatory when returning an assessment for correction.",
                code="REASON_REQUIRED"
            )

        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is already certified and immutable.")

        if assessment.status not in ("SUBMITTED", "UNDER_REVIEW", "EVALUATED", "CERTIFICATION_PENDING"):
            raise InvalidReviewStateError(
                f"Cannot return assessment in '{assessment.status}' status for correction."
            )

        prev_status = assessment.status
        assessment.status = "RETURNED"
        assessment.save(update_fields=["status", "updated_at"])

        review_rec = UniversityReviewRecord.objects.create(
            assessment=assessment,
            reviewer=reviewer,
            action=UniversityReviewAction.RETURN_FOR_CORRECTION,
            status_before=prev_status,
            status_after="RETURNED",
            reason=reason.strip(),
            comments=comments,
        )

        cls.record_audit(
            assessment=assessment,
            actor=reviewer,
            action="RETURNED_FOR_CORRECTION",
            previous_status=prev_status,
            new_status="RETURNED",
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
    ) -> Tuple[UniversityAssessment, UniversityReviewRecord]:
        """
        Blocks review on an assessment due to policy or irremediable violations.
        Requires meaningful reason. Transitions state to BLOCKED.
        """
        try:
            assessment = UniversityAssessment.objects.select_for_update().select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        cls.validate_reviewer_authorization(reviewer, assessment)

        if not reason or not reason.strip():
            raise UniversityValidationError(
                "A meaningful reason is mandatory when blocking an assessment review.",
                code="REASON_REQUIRED"
            )

        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is already certified and immutable.")

        prev_status = assessment.status
        assessment.status = "BLOCKED"
        assessment.save(update_fields=["status", "updated_at"])

        review_rec = UniversityReviewRecord.objects.create(
            assessment=assessment,
            reviewer=reviewer,
            action=UniversityReviewAction.BLOCK_REVIEW,
            status_before=prev_status,
            status_after="BLOCKED",
            reason=reason.strip(),
            comments=comments,
        )

        cls.record_audit(
            assessment=assessment,
            actor=reviewer,
            action="REVIEW_BLOCKED",
            previous_status=prev_status,
            new_status="BLOCKED",
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
    ) -> Tuple[UniversityAssessment, UniversityReviewRecord]:
        """
        Certifies a University assessment after strictly verifying all 11 Statutory Gates.
        Locks the assessment against further modifications.
        """
        try:
            assessment = UniversityAssessment.objects.select_for_update().select_related("university").get(
                assessment_id=assessment_id
            )
        except UniversityAssessment.DoesNotExist:
            raise UniversityValidationError(f"Assessment '{assessment_id}' not found.", code="NOT_FOUND")

        # Gate 3 & 9: Authorized certification actor and conflict-of-interest check
        cls.validate_certification_authority(actor, assessment)

        # Immutability check
        if assessment.status == "CERTIFIED":
            raise AssessmentAlreadyCertifiedError("Assessment is already certified and immutable.")
        if assessment.status in ("BLOCKED",):
            raise AssessmentLockedError("Cannot certify an assessment in BLOCKED status.")

        # Gate 1: Framework check
        if assessment.framework != UNIVERSITY_FRAMEWORK_CODE:
            raise FrameworkMismatchError(
                f"Assessment framework mismatch: '{assessment.framework}' is not '{UNIVERSITY_FRAMEWORK_CODE}'."
            )

        # Gate 2: Assessment period statutory check
        if (
            assessment.academic_year != "2025-26"
            or assessment.period_start > date(2025, 7, 1)
            or assessment.period_end < date(2026, 6, 30)
        ):
            raise UniversityValidationError(
                "Invalid assessment period for 2026 statutory cycle.",
                code="INVALID_ASSESSMENT_PERIOD"
            )

        # Gate 4: Valid lifecycle state
        if assessment.status not in ("CERTIFICATION_PENDING", "EVALUATED", "UNDER_REVIEW", "FINALIZED"):
            raise InvalidReviewStateError(
                f"Cannot certify assessment in '{assessment.status}' status. Assessment must be in 'CERTIFICATION_PENDING' or 'EVALUATED' status."
            )

        # Gate 10: Framework Isolation Gate - No invalid or cross-framework evidence
        foreign_assocs = EvidenceSubcriterionAssociation.objects.filter(
            evidence__assessment_id=assessment.assessment_id,
            is_active=True,
        ).exclude(evidence__framework=UNIVERSITY_FRAMEWORK_CODE)
        if foreign_assocs.exists():
            raise FrameworkMismatchError("Certification blocked: Found active evidence associated with non-University framework.")

        # Gate 5: Evidence readiness gate via Phase 5D
        is_ready, blocking_reasons, summary = UniversityAssessmentService.check_assessment_readiness(
            assessment.assessment_id, user=actor
        )
        if not is_ready or blocking_reasons:
            reasons_str = "; ".join(blocking_reasons) if blocking_reasons else "Evidence requirements incomplete"
            raise CertificationBlockedError(f"Certification blocked by evidence: {reasons_str}")

        # Gate 6 & 7: Scoring evaluation completed & valid via frozen scoring engine
        result = UniversityAssessmentService.evaluate_assessment_scoring(assessment.assessment_id)
        assessment.refresh_from_db()

        if assessment.certified_score is None or result.evidence_gated_total is None:
            raise CertificationBlockedError("Certification blocked: Scoring engine did not produce a certified total.")

        # Gate 8 & 11: No unresolved blocking specification or validation
        if result.certification_status in (
            "BLOCKED_BY_SPECIFICATION",
            "BLOCKED_BY_EVIDENCE",
            "BLOCKED_BY_VALIDATION",
            "BLOCKED_BY_BOUNDARY",
        ) or assessment.certification_status in (
            "BLOCKED_BY_SPECIFICATION",
            "BLOCKED_BY_EVIDENCE",
            "BLOCKED_BY_VALIDATION",
            "BLOCKED_BY_BOUNDARY",
        ):
            raise CertificationBlockedError(
                f"Certification blocked by scoring engine rules ({result.certification_status.value if hasattr(result.certification_status, 'value') else result.certification_status})."
            )

        # ALL 11 GATES PASSED: Transition to CERTIFIED and lock
        prev_status = assessment.status
        assessment.status = "CERTIFIED"
        assessment.certification_status = "CERTIFIED"
        assessment.save(update_fields=["status", "certification_status", "certified_score", "updated_at"])

        scoring_snap = {
            "certified_total": assessment.certified_score,
            "raw_total": result.raw_total,
            "evidence_gated_total": result.evidence_gated_total,
            "certification_status": "CERTIFIED",
            "calculation_id": result.calculation_id,
        }

        review_rec = UniversityReviewRecord.objects.create(
            assessment=assessment,
            reviewer=actor,
            action=UniversityReviewAction.CERTIFY,
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
            payload=scoring_snap,
        )

        return assessment, review_rec

    @classmethod
    def get_review_queue(cls, user: Any, filters: Optional[Dict[str, Any]] = None):
        """
        Retrieves the University assessment review queue for authorized committee reviewers and admins.
        Excludes assessments with institutional conflict of interest.
        """
        if not user or not getattr(user, "is_authenticated", False):
            raise ReviewNotAuthorizedError("Authentication required to access review queue.")

        role = getattr(user, "role", "")
        is_admin = getattr(user, "is_superuser", False) or getattr(user, "is_staff", False) or role in ("admin", "state_admin")

        if not is_admin and role not in ("committee", "committee_chair"):
            raise ReviewNotAuthorizedError("Only committee reviewers and administrators can access the review queue.")

        qs = UniversityAssessment.objects.filter(
            framework=UNIVERSITY_FRAMEWORK_CODE
        ).exclude(status="DRAFT").select_related("university", "assigned_reviewer")

        # Conflict-of-interest exclusion: Exclude reviewer's own university
        user_uni = getattr(user, "university", None)
        if user_uni:
            qs = qs.exclude(university_id=user_uni.pk)

        # Scoped ReviewerAuthorization check
        if not is_admin:
            user_auths = ReviewerAuthorization.objects.filter(user=user, is_active=True)
            if user_auths.exists():
                fw_matching = user_auths.filter(framework__in=[UNIVERSITY_FRAMEWORK_CODE, "ALL"])
                if not fw_matching.exists():
                    return UniversityAssessment.objects.none()
                scoped_insts = [a.institution_id for a in fw_matching if a.institution_id]
                if scoped_insts:
                    qs = qs.filter(university__aishe_code__in=scoped_insts)

        # Filters
        if filters:
            if filters.get("status"):
                qs = qs.filter(status=filters["status"].strip().upper())
            if filters.get("university"):
                u_val = str(filters["university"]).strip()
                if u_val.isdigit():
                    qs = qs.filter(university_id=int(u_val))
                else:
                    qs = qs.filter(university__aishe_code=u_val)
            if filters.get("academic_year"):
                qs = qs.filter(academic_year=filters["academic_year"].strip())
            if filters.get("assigned_reviewer"):
                qs = qs.filter(assigned_reviewer_id=filters["assigned_reviewer"])

        return qs.order_by("-created_at")

