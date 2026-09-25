from datetime import timedelta
from django.utils import timezone
from apps.authentication.models import College, User
from apps.nominations.models import Nomination
from apps.nominations.scoring import get_individual_indicator_scores

def get_all_applications():
    nominations = Nomination.objects.all().order_by("-updated_at")
    apps = []
    for nom in nominations:
        status_str = nom.status or ("Pending Review" if nom.is_submitted else "Draft")
            
        apps.append({
            "id": nom.id,
            "college_id": nom.college.id,
            "college_name": nom.college.name,
            "aishe_code": nom.college.aishe_code,
            "score": nom.score,
            "award_category": nom.award_category,
            "is_submitted": nom.is_submitted,
            "status": status_str,
            "updated_at": nom.updated_at.strftime("%Y-%m-%d %H:%M") if nom.updated_at else None,
            "submitted_at": nom.submitted_at.strftime("%Y-%m-%d %H:%M") if nom.submitted_at else None,
        })
    return apps

def get_institutions_summary():
    colleges = College.objects.all().order_by("name")
    institutions = []

    for college in colleges:
        nom = Nomination.objects.filter(college=college).first()
        has_app = nom is not None
        is_sub = nom.is_submitted if has_app else False
        
        status_str = "not_started"
        score = 0
        award = "No Award"
        remarks_str = ""
        history_list = []
        
        # Derive type from nomination or default to Govt
        college_type = "Govt"
        district = "Haryana"
        
        if has_app:
            score = nom.score
            award = nom.award_category
            remarks_str = nom.remarks or ""
            history_list = nom.history or []
            
            # Map type
            inst_type = str(nom.institution_type or "").lower()
            if "aided" in inst_type:
                college_type = "Aided"
            elif "private" in inst_type:
                college_type = "Private"
            else:
                college_type = "Govt"
                
            # Parse district from address or name
            address_str = str(nom.address or "").lower()
            name_str = college.name.lower()
            for dist in ["rohtak", "panchkula", "ambala", "karnal", "gurugram", "hisar", "panipat", "kurukshetra", "faridabad", "yamunanagar", "sonipat", "kaithal"]:
                if dist in address_str or dist in name_str:
                    district = dist.capitalize()
                    break

            status_str = nom.status or ("Pending Review" if nom.is_submitted else "Draft")

        # Map parameter IDs to corresponding indicator evidence URLs
        docs_dict = {}
        if has_app:
            answers = nom.answers or {}
            param_to_indicator_map = {
                "p1": "indicator_2",
                "p2": "indicator_3",
                "p3": "indicator_4",
                "p4": "indicator_5",
                "p5": "indicator_7",
                "p6": "indicator_9",
                "p7": "indicator_11",
                "p8": "indicator_12",
                "p9": "indicator_14",
                "p10": "indicator_15",
                "p11": "indicator_16",
                "p12": "indicator_18",
                "p13": "indicator_19",
                "p14": "indicator_20",
                "p15": "indicator_1",
                "p16": "indicator_6",
                "p17": "indicator_8",
                "p18": "indicator_10",
                "p19": "indicator_13",
                "p20": "indicator_17"
            }
            for param_id, ind_key in param_to_indicator_map.items():
                ind_data = answers.get(ind_key, {})
                url = ind_data.get("evidence_url")
                if url:
                    docs_dict[param_id] = url
        else:
            docs_dict = {f"p{i}": "" for i in range(1, 21)}

        institutions.append(
            {
                "id": str(college.id),
                "college_id": college.id,
                "docs": docs_dict,
                "name": college.name,
                "aishe": college.aishe_code,
                "aishe_code": college.aishe_code,
                "type": college_type,
                "district": district,
                "has_application": has_app,
                "application_status": status_str,
                "status": status_str,
                "is_submitted": is_sub,
                "score": score,
                "scores": (
                    nom.reviewer_scores if (has_app and nom.reviewer_scores) else
                    get_individual_indicator_scores(nom.answers or {}) 
                    if has_app else 
                    {f"p{i}": 0 for i in range(1, 23)}
                ),
                "remarks": remarks_str,
                "history": history_list,
                "grand_total": score,
                "award_category": award,
                "classification": {
                    "name": award,
                    "color": "#7C3AED" if award == "Platinum" else "#D97706" if award == "Gold" else "#6B7280" if award == "Silver" else "#EF4444",
                    "bg": "bg-purple-100 text-purple-800 border-purple-300" if award == "Platinum" else "bg-amber-100 text-amber-800 border-amber-300" if award == "Gold" else "bg-slate-100 text-slate-800 border-slate-300" if award == "Silver" else "bg-red-100 text-red-800 border-red-300"
                },
                "updated_at": nom.updated_at.strftime("%Y-%m-%d %H:%M") if (has_app and nom.updated_at) else None,
            }
        )
    return institutions

def get_dashboard_stats():
    total_colleges = College.objects.count()
    registered_principals = User.objects.filter(role="principal").count()
    
    total_nominations = Nomination.objects.count()
    submitted_nominations = Nomination.objects.filter(is_submitted=True).count()
    
    approved_awards = 0
    pending_review = 0
    sent_back = 0
    rejected = 0
    
    colleges = get_institutions_summary()
    for col in colleges:
        status_str = col["status"]
        if status_str == "Approved":
            approved_awards += 1
        elif status_str == "Pending Review":
            pending_review += 1
        elif status_str == "Sent Back":
            sent_back += 1
        elif status_str == "Rejected":
            rejected += 1
            
    return {
        "total_colleges": total_colleges,
        "total_applications": total_nominations,
        "submitted_applications": submitted_nominations,
        "in_progress_applications": total_nominations - submitted_nominations,
        "approved_awards": approved_awards,
        "pending_review": pending_review,
        "sent_back": sent_back,
        "rejected": rejected,
        "registered_principals": registered_principals,
        "average_score_percentage": None,
        "award_distribution": {
            "Platinum": Nomination.objects.filter(award_category="Platinum").count(),
            "Gold": Nomination.objects.filter(award_category="Gold").count(),
            "Silver": Nomination.objects.filter(award_category="Silver").count(),
            "No Award": Nomination.objects.filter(award_category="No Award").count(),
        },
    }

def get_analytics():
    stats = get_dashboard_stats()
    now = timezone.now()

    trend_buckets = {}
    for i in range(5, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        key = month_start.strftime("%Y-%m")
        trend_buckets[key] = 0

    submission_trend = [
        {"month": month, "count": count} for month, count in sorted(trend_buckets.items())
    ]

    return {
        "stats": stats,
        "institution_counts": [],
        "score_distribution": [],
        "status_breakdown": [
            {"status": "submitted", "count": stats["submitted_applications"]},
            {"status": "in_progress", "count": stats["in_progress_applications"]},
            {"status": "approved", "count": stats["approved_awards"]},
            {"status": "pending_review", "count": stats["pending_review"]},
        ],
        "submission_trend": submission_trend,
        "recent_activity": [],
        "top_institutions": [],
        "award_distribution": stats["award_distribution"],
    }


# ==============================================================================
# PHASE 8: NEP EXCELLENCE AWARDS 2026 ADMIN CONTROL PLANE SERVICE
# ==============================================================================

from typing import Any, Dict, List, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.university.models import (
    UniversityAssessment,
    UniversityAssessmentAuditLog,
    UniversityReviewRecord,
)
from apps.university.services import (
    UniversityAssessmentService,
    UniversityReviewService,
    UNIVERSITY_FRAMEWORK_CODE,
)
from apps.college.models import (
    CollegeAssessment,
    CollegeAssessmentAuditLog,
    CollegeReviewRecord,
)
from apps.college.services import (
    CollegeAssessmentService,
    CollegeReviewService,
    COLLEGE_FRAMEWORK_CODE,
)
from apps.evidence.models import EvidenceSubcriterionAssociation, ReviewerAuthorization
from apps.evidence.services import EvidenceService
from .api_permissions import (
    AdminPermissionDenied,
    FrameworkMismatchError,
    ReviewConflictError,
    validate_reviewer_framework_and_coi,
)


class AdminValidationError(Exception):
    """Domain validation error within the admin control plane."""
    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class AdminControlPlaneService:
    """
    Unified Administrative and Reviewer Control Plane service for NEP Excellence Awards 2026.
    Enforces cross-framework isolation, strict institution tenancy, conflict of interest,
    explicit reviewer assignment with mandatory justification, read-only inspection,
    and delegation to existing domain scoring and certification services.
    """

    @classmethod
    def resolve_assessment(
        cls, assessment_id: str, for_update: bool = False
    ) -> Tuple[str, Any]:
        """
        Server-authoritative assessment resolution.
        Derives framework strictly from database records, never trusting client input.
        Returns: (framework_code, assessment_instance)
        Raises: AdminValidationError if assessment does not exist.
        """
        clean_id = str(assessment_id).strip()

        # Check UniversityAssessment
        uni_qs = UniversityAssessment.objects.select_related("university", "assigned_reviewer")
        if for_update:
            uni_qs = uni_qs.select_for_update()
        uni_assessment = uni_qs.filter(assessment_id=clean_id).first()
        if uni_assessment:
            return (UNIVERSITY_FRAMEWORK_CODE, uni_assessment)

        # Check CollegeAssessment
        col_qs = CollegeAssessment.objects.select_related("college", "assigned_reviewer")
        if for_update:
            col_qs = col_qs.select_for_update()
        col_assessment = col_qs.filter(assessment_id=clean_id).first()
        if col_assessment:
            return (COLLEGE_FRAMEWORK_CODE, col_assessment)

        raise AdminValidationError(
            f"Assessment '{clean_id}' not found in any active NEP 2026 framework.",
            code="ASSESSMENT_NOT_FOUND"
        )

    @classmethod
    def get_unified_queue(
        cls, user: Any, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves a consolidated, unified review queue across authorized frameworks.
        Enforces reviewer framework authorization, institutional scoping, and COI exclusion.
        Consumes existing assessment state, evidence readiness, and scoring snapshots
        without performing new scoring calculations.
        """
        if not user or not getattr(user, "is_authenticated", False):
            raise AdminPermissionDenied("Authentication required to access review queue.")

        role = getattr(user, "role", "")
        is_admin = (
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or role in ("admin", "state_admin")
        )

        if not is_admin and role not in ("committee", "committee_chair"):
            raise AdminPermissionDenied(
                "Review queue is restricted to screening committee reviewers and administrators.",
                code="QUEUE_NOT_AUTHORIZED"
            )

        filters = filters or {}
        requested_framework = filters.get("framework", "").strip().upper() if filters.get("framework") else None

        # Determine caller's authorized frameworks
        authorized_frameworks = set()
        if is_admin:
            authorized_frameworks = {UNIVERSITY_FRAMEWORK_CODE, COLLEGE_FRAMEWORK_CODE}
        else:
            user_auths = ReviewerAuthorization.objects.filter(user=user, is_active=True)
            if user_auths.exists():
                for auth in user_auths:
                    if auth.framework in (UNIVERSITY_FRAMEWORK_CODE, "ALL"):
                        authorized_frameworks.add(UNIVERSITY_FRAMEWORK_CODE)
                    if auth.framework in (COLLEGE_FRAMEWORK_CODE, "ALL"):
                        authorized_frameworks.add(COLLEGE_FRAMEWORK_CODE)
            else:
                # Default committee role has access to both if no explicit granular restrictions exist
                authorized_frameworks = {UNIVERSITY_FRAMEWORK_CODE, COLLEGE_FRAMEWORK_CODE}

        if requested_framework:
            if requested_framework not in authorized_frameworks:
                if not is_admin:
                    raise FrameworkMismatchError(
                        f"Reviewer is not authorized for requested framework '{requested_framework}'."
                    )
                return []
            frameworks_to_query = [requested_framework]
        else:
            frameworks_to_query = list(authorized_frameworks)

        queue_items = []

        # 1. Query University assessments if authorized
        if UNIVERSITY_FRAMEWORK_CODE in frameworks_to_query:
            uni_qs = UniversityReviewService.get_review_queue(user, filters=filters)
            for u in uni_qs:
                reviewer = u.assigned_reviewer
                queue_items.append({
                    "assessment_id": u.assessment_id,
                    "framework": u.framework,
                    "academic_year": u.academic_year,
                    "institution_id": str(u.university.pk),
                    "institution_name": u.university.name,
                    "institution_aishe": u.university.aishe_code or "",
                    "status": u.status,
                    "assigned_reviewer_id": reviewer.pk if reviewer else None,
                    "assigned_reviewer_name": reviewer.full_name if reviewer else None,
                    "assigned_reviewer_email": reviewer.email if reviewer else None,
                    "certified_score": u.certified_score,
                    "certification_status": u.certification_status or "",
                    "submitted_at": u.submitted_at,
                    "created_at": u.created_at,
                })

        # 2. Query College assessments if authorized
        if COLLEGE_FRAMEWORK_CODE in frameworks_to_query:
            col_qs = CollegeReviewService.get_review_queue(user, filters=filters)
            for c in col_qs:
                reviewer = c.assigned_reviewer
                queue_items.append({
                    "assessment_id": c.assessment_id,
                    "framework": c.framework,
                    "academic_year": c.academic_year,
                    "institution_id": str(c.college.pk),
                    "institution_name": c.college.name,
                    "institution_aishe": c.college.aishe_code or "",
                    "status": c.status,
                    "assigned_reviewer_id": reviewer.pk if reviewer else None,
                    "assigned_reviewer_name": reviewer.full_name if reviewer else None,
                    "assigned_reviewer_email": reviewer.email if reviewer else None,
                    "certified_score": c.certified_score,
                    "certification_status": c.certification_status or "",
                    "submitted_at": c.submitted_at,
                    "created_at": c.created_at,
                })

        # Additional cross-framework filters
        assigned_filter = filters.get("assigned_reviewer")
        if assigned_filter:
            assigned_val = str(assigned_filter).strip().lower()
            if assigned_val == "unassigned":
                queue_items = [item for item in queue_items if item["assigned_reviewer_id"] is None]
            elif assigned_val.isdigit():
                queue_items = [item for item in queue_items if item["assigned_reviewer_id"] == int(assigned_val)]

        status_filter = filters.get("status")
        if status_filter:
            s_clean = status_filter.strip().upper()
            queue_items = [item for item in queue_items if item["status"] == s_clean]

        institution_filter = filters.get("institution")
        if institution_filter:
            inst_clean = str(institution_filter).strip().lower()
            queue_items = [
                item for item in queue_items
                if inst_clean in item["institution_name"].lower()
                or inst_clean in item["institution_aishe"].lower()
                or inst_clean == item["institution_id"]
            ]

        # Order by submitted_at desc, then created_at desc
        queue_items.sort(
            key=lambda x: (x["submitted_at"] is not None, x["submitted_at"], x["created_at"]),
            reverse=True
        )

        return queue_items

    @classmethod
    def inspect_assessment(cls, assessment_id: str, user: Any) -> Dict[str, Any]:
        """
        Safe, read-only administrative inspection of an assessment.
        Returns detailed institutional, lifecycle, reviewer, scoring, readiness,
        certification eligibility, specification blocks, and complete audit history.
        Enforces tenant isolation and framework security. Zero state mutation.
        """
        if not user or not getattr(user, "is_authenticated", False):
            raise AdminPermissionDenied("Authentication required to inspect assessment.")

        framework, assessment = cls.resolve_assessment(assessment_id)

        role = getattr(user, "role", "")
        is_admin = (
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or role in ("admin", "state_admin")
        )

        # 1. Tenancy Enforcement for Institutional Users
        if role in ("principal", "nodal_officer", "university_admin"):
            if framework == UNIVERSITY_FRAMEWORK_CODE:
                user_uni = getattr(user, "university", None)
                if not user_uni or (user_uni.pk != assessment.university.pk and user_uni.aishe_code != assessment.university.aishe_code):
                    raise AdminPermissionDenied(
                        "Institution users cannot inspect assessments belonging to external institutions.",
                        code="TENANCY_VIOLATION"
                    )
            elif framework == COLLEGE_FRAMEWORK_CODE:
                user_col = getattr(user, "college", None)
                if not user_col or (user_col.pk != assessment.college.pk and user_col.aishe_code != assessment.college.aishe_code):
                    raise AdminPermissionDenied(
                        "Institution users cannot inspect assessments belonging to external institutions.",
                        code="TENANCY_VIOLATION"
                    )

        # 2. Framework & COI Enforcement for Committee Reviewers
        if role in ("committee", "committee_chair") and not is_admin:
            validate_reviewer_framework_and_coi(user, assessment)

        # 3. Assemble Institution Metadata
        if framework == UNIVERSITY_FRAMEWORK_CODE:
            institution_data = {
                "id": assessment.university.pk,
                "name": assessment.university.name,
                "aishe_code": assessment.university.aishe_code or "",
                "type": getattr(assessment.university, "university_type", "University"),
                "framework": UNIVERSITY_FRAMEWORK_CODE,
            }
        else:
            institution_data = {
                "id": assessment.college.pk,
                "name": assessment.college.name,
                "aishe_code": assessment.college.aishe_code or "",
                "type": "College",
                "framework": COLLEGE_FRAMEWORK_CODE,
            }

        # 4. Assigned Reviewer Metadata
        reviewer = assessment.assigned_reviewer
        assigned_reviewer_data = {
            "id": reviewer.pk,
            "full_name": reviewer.full_name,
            "email": reviewer.email,
            "role": getattr(reviewer, "role", ""),
        } if reviewer else None

        # 5. Evidence Readiness Evaluation (Delegated to existing service)
        try:
            if framework == UNIVERSITY_FRAMEWORK_CODE:
                is_ready, blocking_reasons, summary = UniversityAssessmentService.check_assessment_readiness(
                    assessment.assessment_id, user=user
                )
            else:
                is_ready, blocking_reasons, summary = CollegeAssessmentService.check_assessment_readiness(
                    assessment.assessment_id, user=user
                )
            evidence_readiness = {
                "is_ready": is_ready,
                "blocking_reasons": blocking_reasons,
                "total_evaluated": getattr(summary, "total_evaluated", 0) if summary else 0,
                "total_covered": getattr(summary, "total_covered", 0) if summary else 0,
            }
        except Exception as e:
            evidence_readiness = {
                "is_ready": False,
                "blocking_reasons": [str(e)],
                "total_evaluated": 0,
                "total_covered": 0,
            }

        # 6. Scoring Snapshot
        scoring_data = {
            "certified_score": assessment.certified_score,
            "certification_status": assessment.certification_status or "NOT_EVALUATED",
            "is_finalizable": assessment.certification_status == "FINALIZABLE",
            "is_blocked_by_specification": assessment.certification_status == "BLOCKED_BY_SPECIFICATION",
        }

        # 7. Specification Blocks (Preserving statutory ambiguities)
        specification_blocks = {
            "is_blocked": assessment.certification_status == "BLOCKED_BY_SPECIFICATION",
            "statutory_unresolved_criteria": ["C5", "C7", "C8", "C16"] if framework == COLLEGE_FRAMEWORK_CODE else [],
        }

        # 8. Certification Eligibility Gates Summary
        blocking_gates = []
        if assessment.status == "CERTIFIED":
            is_eligible = False
            blocking_gates.append("Assessment is already certified.")
        else:
            # Gate: Lifecycle
            if framework == COLLEGE_FRAMEWORK_CODE and assessment.status != "UNDER_REVIEW":
                blocking_gates.append(f"Lifecycle state is '{assessment.status}', must be 'UNDER_REVIEW'.")
            elif framework == UNIVERSITY_FRAMEWORK_CODE and assessment.status not in ("UNDER_REVIEW", "EVALUATED", "CERTIFICATION_PENDING"):
                blocking_gates.append(f"Lifecycle state is '{assessment.status}', must be in review state.")

            # Gate: Evidence
            if not evidence_readiness["is_ready"]:
                blocking_gates.append("Evidence requirements are incomplete or unverified.")

            # Gate: Scoring
            if assessment.certified_score is None:
                blocking_gates.append("Scoring has not been evaluated by the frozen engine.")
            elif assessment.certification_status == "BLOCKED_BY_SPECIFICATION":
                blocking_gates.append("Certification blocked by unresolved statutory specifications.")

            is_eligible = len(blocking_gates) == 0

        # 9. Review History Records (Append-only)
        review_history = []
        for r in assessment.review_records.select_related("reviewer").order_by("-created_at")[:50]:
            review_history.append({
                "action": r.action,
                "actor": r.reviewer.full_name if r.reviewer else "System",
                "actor_email": r.reviewer.email if r.reviewer else "",
                "status_before": r.status_before,
                "status_after": r.status_after,
                "reason": r.reason,
                "comments": r.comments,
                "timestamp": r.created_at,
            })

        # 10. Audit Trail Records (Append-only)
        audit_trail = []
        for a in assessment.audit_logs.select_related("actor").order_by("-timestamp")[:50]:
            prev_s = getattr(a, "previous_status", getattr(a, "previous_state", ""))
            new_s = getattr(a, "new_status", getattr(a, "new_state", ""))
            payload_data = getattr(a, "payload", {})
            audit_trail.append({
                "action": a.action,
                "actor": getattr(a.actor, "full_name", str(a.actor)) if a.actor else "System",
                "actor_email": a.actor.email if a.actor else "",
                "previous_status": prev_s,
                "new_status": new_s,
                "reason": a.reason,
                "payload": payload_data,
                "timestamp": a.timestamp,
            })

        # 11. Parameter Data
        param_data = getattr(assessment, "parameter_data", {}) or {}

        # 12. Evidence Associations & Coverage
        associations_qs = EvidenceSubcriterionAssociation.objects.filter(
            evidence__assessment_id=assessment.assessment_id,
            is_active=True,
        ).select_related('evidence', 'associated_by').prefetch_related('verifications__verifier')

        evidence_associations = []
        for assoc in associations_qs:
            latest_v = assoc.latest_verification
            v_data = None
            if latest_v:
                v_data = {
                    "verification_id": str(latest_v.verification_id),
                    "decision": latest_v.decision,
                    "verifier_id": latest_v.verifier_id,
                    "verifier_email": getattr(latest_v.verifier, 'email', str(latest_v.verifier_id)),
                    "reason": latest_v.reason,
                    "rejection_code": latest_v.rejection_code,
                    "inspected_checksum": latest_v.inspected_checksum,
                    "timestamp": latest_v.timestamp.isoformat(),
                }
            evidence_associations.append({
                "association_id": str(assoc.association_id),
                "id": assoc.pk,
                "evidence_id": str(assoc.evidence.document_id),
                "original_filename": assoc.evidence.original_filename,
                "file_checksum": assoc.evidence.file_checksum,
                "mime_type": assoc.evidence.mime_type,
                "file_size": assoc.evidence.file_size,
                "framework": assoc.evidence.framework,
                "institution_id": assoc.evidence.institution_id,
                "parameter_id": assoc.parameter_id,
                "subcriterion_id": assoc.subcriterion_id,
                "subcriterion_evidence_type": assoc.subcriterion_evidence_type,
                "page_start": assoc.page_start,
                "page_end": assoc.page_end,
                "section_identifier": assoc.section_identifier,
                "claim_description": assoc.claim_description,
                "verification_status": assoc.verification_status or "PENDING",
                "latest_verification": v_data,
                "associated_at": assoc.associated_at.isoformat() if assoc.associated_at else None,
                "is_active": assoc.is_active,
            })

        evidence_coverage_state = {}
        try:
            target_inst = institution_data.get("aishe_code") or str(institution_data.get("id"))
            cov_report = EvidenceService.evaluate_evidence_coverage(
                assessment_id=assessment.assessment_id,
                institution_id=target_inst,
                framework=framework,
                requesting_user=user,
            )
            evidence_coverage_state = cov_report.to_dict()
        except Exception:
            evidence_coverage_state = {}

        return {
            "assessment_id": assessment.assessment_id,
            "framework": framework,
            "academic_year": assessment.academic_year,
            "status": assessment.status,
            "period_start": assessment.period_start,
            "period_end": assessment.period_end,
            "submitted_at": assessment.submitted_at,
            "institution": institution_data,
            "assigned_reviewer": assigned_reviewer_data,
            "parameter_data": param_data,
            "evidence_associations": evidence_associations,
            "evidence_coverage": evidence_coverage_state,
            "scoring": scoring_data,
            "evidence_readiness": evidence_readiness,
            "specification_blocks": specification_blocks,
            "certification_eligibility": {
                "is_eligible": is_eligible,
                "blocking_gates": blocking_gates,
            },
            "review_history": review_history,
            "audit_trail": audit_trail,
        }

    @classmethod
    @transaction.atomic
    def assign_reviewer(
        cls,
        assessment_id: str,
        reviewer_id: int,
        actor: Any,
        reason: str = "",
    ) -> Tuple[Any, User]:
        """
        Explicit, auditable reviewer assignment and reassignment.
        Enforces:
        - Actor authority (Admin, State Admin, Committee Chair, Superuser).
        - Reviewer eligibility (Active, Reviewer/Admin role).
        - Framework scope matching via ReviewerAuthorization.
        - Institutional conflict of interest exclusion.
        - Assessment lifecycle check (Certified assessments are permanently locked).
        - Reassignment requires a mandatory justification reason.
        - Append-only audit history creation.
        """
        if not actor or not getattr(actor, "is_authenticated", False):
            raise AdminPermissionDenied("Authentication required to assign reviewers.")

        actor_role = getattr(actor, "role", "")
        is_admin = (
            getattr(actor, "is_superuser", False)
            or getattr(actor, "is_staff", False)
            or actor_role in ("admin", "state_admin")
        )
        is_chair = actor_role == "committee_chair"

        if not (is_admin or is_chair):
            raise AdminPermissionDenied(
                "Reviewer assignment is restricted to Committee Chairs and Administrators.",
                code="ASSIGNMENT_NOT_AUTHORIZED"
            )

        # Resolve assessment with row lock
        framework, assessment = cls.resolve_assessment(assessment_id, for_update=True)

        if assessment.status == "CERTIFIED":
            raise AdminValidationError(
                "Cannot assign or reassign reviewers to a CERTIFIED assessment. Assessment is permanently locked.",
                code="ASSESSMENT_CERTIFIED_LOCKED"
            )

        # Resolve target reviewer
        try:
            target_reviewer = User.objects.get(pk=reviewer_id)
        except User.DoesNotExist:
            raise AdminValidationError(
                f"Reviewer with ID {reviewer_id} does not exist.",
                code="REVIEWER_NOT_FOUND"
            )

        if not target_reviewer.is_active:
            raise AdminValidationError(
                f"Reviewer '{target_reviewer.email}' is inactive.",
                code="REVIEWER_INACTIVE"
            )

        target_role = getattr(target_reviewer, "role", "")
        if target_role not in ("committee", "committee_chair", "admin", "state_admin") and not getattr(target_reviewer, "is_staff", False):
            raise AdminValidationError(
                f"User '{target_reviewer.email}' does not possess a committee or administrator role.",
                code="INVALID_REVIEWER_ROLE"
            )

        # Conflict of interest check for target reviewer
        if framework == COLLEGE_FRAMEWORK_CODE:
            target_college = getattr(target_reviewer, "college", None)
            if target_college and (target_college.pk == assessment.college.pk or target_college.aishe_code == assessment.college.aishe_code):
                raise ReviewConflictError(
                    f"Conflict of interest: Target reviewer is affiliated with institution '{assessment.college.name}'."
                )
        elif framework == UNIVERSITY_FRAMEWORK_CODE:
            target_uni = getattr(target_reviewer, "university", None)
            if target_uni and (target_uni.pk == assessment.university.pk or target_uni.aishe_code == assessment.university.aishe_code):
                raise ReviewConflictError(
                    f"Conflict of interest: Target reviewer is affiliated with institution '{assessment.university.name}'."
                )

        # Framework authorization check for target reviewer (non-admin)
        target_is_admin = (
            getattr(target_reviewer, "is_superuser", False)
            or getattr(target_reviewer, "is_staff", False)
            or target_role in ("admin", "state_admin")
        )
        if not target_is_admin:
            auth_qs = ReviewerAuthorization.objects.filter(user=target_reviewer, is_active=True)
            if auth_qs.exists():
                fw_match = auth_qs.filter(framework__in=[framework, "ALL"])
                if not fw_match.exists():
                    raise FrameworkMismatchError(
                        f"Target reviewer '{target_reviewer.email}' is not authorized for framework '{framework}'."
                    )
                # Institutional scope check
                if framework == COLLEGE_FRAMEWORK_CODE and assessment.college.aishe_code:
                    inst_match = fw_match.filter(institution_id__in=["", assessment.college.aishe_code, str(assessment.college.pk)])
                    if not inst_match.exists():
                        raise AdminValidationError(
                            f"Target reviewer is not authorized for institution '{assessment.college.aishe_code}'.",
                            code="INSTITUTION_NOT_AUTHORIZED"
                        )
                elif framework == UNIVERSITY_FRAMEWORK_CODE and assessment.university.aishe_code:
                    inst_match = fw_match.filter(institution_id__in=["", assessment.university.aishe_code, str(assessment.university.pk)])
                    if not inst_match.exists():
                        raise AdminValidationError(
                            f"Target reviewer is not authorized for institution '{assessment.university.aishe_code}'.",
                            code="INSTITUTION_NOT_AUTHORIZED"
                        )

        # Check if already assigned to this exact reviewer
        prev_reviewer = assessment.assigned_reviewer
        if prev_reviewer and prev_reviewer.pk == target_reviewer.pk:
            return (assessment, target_reviewer)

        # Reassignment requires mandatory reason
        is_reassignment = prev_reviewer is not None
        if is_reassignment:
            if not reason or not reason.strip():
                raise AdminValidationError(
                    "A mandatory, non-empty reason is required when reassigning an assessment to a new reviewer.",
                    code="REASON_REQUIRED"
                )
            action_code = "REVIEWER_REASSIGNED"
        else:
            action_code = "REVIEWER_ASSIGNED"

        # Apply assignment
        assessment.assigned_reviewer = target_reviewer
        assessment.save(update_fields=["assigned_reviewer", "updated_at"])

        # Create append-only audit log
        audit_payload = {
            "previous_reviewer_id": prev_reviewer.pk if prev_reviewer else None,
            "previous_reviewer_email": prev_reviewer.email if prev_reviewer else None,
            "new_reviewer_id": target_reviewer.pk,
            "new_reviewer_email": target_reviewer.email,
            "assigned_by_id": actor.pk,
            "assigned_by_email": actor.email,
            "framework": framework,
            "is_reassignment": is_reassignment,
        }

        if framework == UNIVERSITY_FRAMEWORK_CODE:
            UniversityAssessmentAuditLog.objects.create(
                assessment=assessment,
                actor=actor,
                action=action_code,
                previous_status=assessment.status,
                new_status=assessment.status,
                reason=reason.strip() if reason else "Initial committee assignment",
                payload=audit_payload,
            )
        else:
            reason_text = reason.strip() if reason else "Initial committee assignment"
            if is_reassignment:
                reason_text = f"{reason_text} [Reassigned from {prev_reviewer.email if prev_reviewer else 'None'} to {target_reviewer.email}]"
            else:
                reason_text = f"{reason_text} [Assigned to {target_reviewer.email}]"
            CollegeAssessmentAuditLog.objects.create(
                assessment=assessment,
                actor=actor,
                action=action_code,
                previous_state=assessment.status,
                new_state=assessment.status,
                reason=reason_text,
            )

        return (assessment, target_reviewer)

    @classmethod
    @transaction.atomic
    def certify_assessment(
        cls, assessment_id: str, actor: Any, comments: str = ""
    ) -> Tuple[Any, Any]:
        """
        Delegates assessment certification to the respective domain service.
        Does NOT implement a secondary certification algorithm.
        Enforces all 11 certification gates: 2 source/framework requirements and 9 platform certification safeguards.
        Unresolved criteria ambiguities (C5, C7, C8, C16) strictly block certification under Gate 11.
        """
        framework, _ = cls.resolve_assessment(assessment_id)

        if framework == UNIVERSITY_FRAMEWORK_CODE:
            return UniversityReviewService.certify_assessment(
                assessment_id=assessment_id,
                actor=actor,
                remarks=comments,
            )
        elif framework == COLLEGE_FRAMEWORK_CODE:
            return CollegeReviewService.certify_assessment(
                assessment_id=assessment_id,
                actor=actor,
                remarks=comments,
            )
        else:
            raise AdminValidationError(
                f"Unknown framework '{framework}'. Cannot certify assessment.",
                code="UNKNOWN_FRAMEWORK"
            )
