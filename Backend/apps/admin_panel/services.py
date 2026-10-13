from datetime import timedelta
from django.db import models
from django.utils import timezone
from apps.authentication.models import College, User, UserAuditLog
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
        if actor_role == "council_admin":
            raise AdminPermissionDenied(
                "Council Admin Overseer cannot assign reviewers.",
                code="ASSIGNMENT_NOT_AUTHORIZED"
            )

        is_admin = (
            getattr(actor, "is_superuser", False)
            or actor_role in ("admin", "state_admin", "head_admin", "sub_admin")
            or (getattr(actor, "is_staff", False) and actor_role not in ("council_admin", "committee"))
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


# Stage buckets used by the State Admin overview; every assessment status maps to exactly one.
STATE_STAGE_BY_STATUS = {
    "DRAFT": "IN_PROGRESS",
    "RETURNED": "RETURNED",
    "SUBMITTED": "SUBMITTED",
    "UNDER_REVIEW": "UNDER_REVIEW",
    "EVIDENCE_VERIFIED": "UNDER_REVIEW",
    "EVALUATED": "UNDER_REVIEW",
    "BLOCKED": "UNDER_REVIEW",
    "CERTIFICATION_PENDING": "AWAITING_CERTIFICATION",
    "CERTIFIED": "CERTIFIED",
    "REJECTED": "REJECTED",
}
STATE_STAGES = ["NOT_STARTED", "IN_PROGRESS", "RETURNED", "SUBMITTED", "UNDER_REVIEW",
                "AWAITING_CERTIFICATION", "CERTIFIED", "REJECTED"]
REVIEW_STAGES = {"SUBMITTED", "UNDER_REVIEW", "AWAITING_CERTIFICATION"}


class StateOverviewService:
    """Read-only, state-wide view of every institution and its latest NEP 2026 assessment (no state mutation)."""

    @classmethod
    def _rows(cls, institutions, assessments_by_inst, contacts, inst_type, framework):
        rows = []
        for inst in institutions:
            a = assessments_by_inst.get(inst.pk)
            stage = STATE_STAGE_BY_STATUS.get(a.status, "UNDER_REVIEW") if a else "NOT_STARTED"
            reviewer = a.assigned_reviewer if a else None
            contact = contacts.get(inst.pk)
            rows.append({
                "institution_type": inst_type,
                "framework": framework,
                "institution_id": str(inst.pk),
                "name": inst.name,
                "aishe_code": inst.aishe_code,
                "contact_name": contact.full_name if contact else "",
                "contact_email": contact.email if contact else "",
                "assessment_id": a.assessment_id if a else None,
                "academic_year": a.academic_year if a else None,
                "status": a.status if a else "NOT_STARTED",
                "stage": stage,
                "score": a.certified_score if a else None,
                "certification_status": (a.certification_status or "") if a else "",
                "assigned_reviewer_id": reviewer.pk if reviewer else None,
                "assigned_reviewer_name": reviewer.full_name if reviewer else None,
                "submitted_at": a.submitted_at if a else None,
                "updated_at": a.updated_at if a else None,
            })
        return rows

    @staticmethod
    def _latest_by(qs, key):
        latest = {}
        for a in qs.order_by("created_at"):
            latest[getattr(a, key)] = a
        return latest

    @classmethod
    def build(cls) -> Dict[str, Any]:
        from apps.university.models import University, UniversityAssessmentAuditLog
        from apps.college.models import CollegeAssessmentAuditLog

        uni_assess = cls._latest_by(UniversityAssessment.objects.select_related("assigned_reviewer"), "university_id")
        col_assess = cls._latest_by(CollegeAssessment.objects.select_related("assigned_reviewer"), "college_id")
        uni_contacts, col_contacts = {}, {}
        for u in User.objects.filter(role__in=("nodal_officer", "university_admin", "principal"), is_active=True).order_by("-role"):
            if u.university_id and (u.university_id not in uni_contacts or u.role == "nodal_officer"):
                uni_contacts[u.university_id] = u
            if u.college_id:
                col_contacts.setdefault(u.college_id, u)

        rows = (
            cls._rows(University.objects.order_by("name"), uni_assess, uni_contacts, "UNIVERSITY", UNIVERSITY_FRAMEWORK_CODE)
            + cls._rows(College.objects.order_by("name"), col_assess, col_contacts, "COLLEGE", COLLEGE_FRAMEWORK_CODE)
        )

        by_stage = {s: 0 for s in STATE_STAGES}
        for r in rows:
            by_stage[r["stage"]] += 1
        summary = {
            "universities": sum(r["institution_type"] == "UNIVERSITY" for r in rows),
            "colleges": sum(r["institution_type"] == "COLLEGE" for r in rows),
            "total": len(rows),
            "started": len(rows) - by_stage["NOT_STARTED"],
            "by_stage": by_stage,
        }

        in_review = [r for r in rows if r["stage"] in REVIEW_STAGES]
        workload = {}
        for r in in_review:
            if r["assigned_reviewer_id"]:
                workload[r["assigned_reviewer_id"]] = workload.get(r["assigned_reviewer_id"], 0) + 1
        reviewers = [
            {"id": u.pk, "full_name": u.full_name, "email": u.email, "role": u.role,
             "active_assignments": workload.get(u.pk, 0)}
            for u in User.objects.filter(role__in=("committee", "committee_chair"), is_active=True).order_by("role", "full_name")
        ]
        committee = {
            "reviewers": reviewers,
            "pending_reviews": len(in_review),
            "unassigned": sum(1 for r in in_review if not r["assigned_reviewer_id"]),
        }

        activity = []
        for log in CollegeAssessmentAuditLog.objects.select_related("actor", "assessment__college").order_by("-timestamp")[:15]:
            activity.append({
                "timestamp": log.timestamp, "action": log.action, "institution_type": "COLLEGE",
                "institution_name": log.assessment.college.name, "assessment_id": log.assessment.assessment_id,
                "actor": log.actor.full_name if log.actor else "System",
                "from_status": log.previous_state, "to_status": log.new_state,
            })
        for log in UniversityAssessmentAuditLog.objects.select_related("actor", "assessment__university").order_by("-timestamp")[:15]:
            activity.append({
                "timestamp": log.timestamp, "action": log.action, "institution_type": "UNIVERSITY",
                "institution_name": log.assessment.university.name, "assessment_id": log.assessment.assessment_id,
                "actor": log.actor.full_name if log.actor else "System",
                "from_status": log.previous_status, "to_status": log.new_status,
            })
        activity.sort(key=lambda x: x["timestamp"], reverse=True)

        return {"summary": summary, "committee": committee, "institutions": rows, "recent_activity": activity[:15]}


class AdminUserManagementService:
    """
    Centralized service for managing users, sub-admins, committee memberships,
    and institutional accounts with least privilege and audit logging.
    """
    PRIVILEGED_ROLES = frozenset([
        'head_admin',
        'state_admin',
        'sub_admin',
        'council_admin',
        'admin',
        'committee',
        'committee_chair',
        'empowered_committee',
        'empowered_committee_chair',
    ])

    @classmethod
    def list_users(cls, actor, filters=None, page=1, page_size=20):
        from .api_permissions import AdminPermissionDenied

        if not (getattr(actor, 'is_superuser', False) or getattr(actor, 'role', '') in ('head_admin', 'state_admin', 'sub_admin', 'admin', 'council_admin')):
            raise AdminPermissionDenied("Administrative authority required.", code="ADMIN_REQUIRED")

        filters = filters or {}
        qs = User.objects.select_related('college', 'university').all()

        q = filters.get('q')
        if q and q.strip():
            query = q.strip()
            qs = qs.filter(
                models.Q(email__icontains=query) |
                models.Q(full_name__icontains=query) |
                models.Q(phone_number__icontains=query) |
                models.Q(college__name__icontains=query) |
                models.Q(college__aishe_code__icontains=query) |
                models.Q(university__name__icontains=query) |
                models.Q(university__aishe_code__icontains=query)
            )

        role = filters.get('role')
        if role:
            qs = qs.filter(role=role)

        is_active = filters.get('is_active')
        if is_active is not None:
            if isinstance(is_active, str):
                is_active = is_active.lower() in ('true', '1', 'yes')
            qs = qs.filter(is_active=bool(is_active))

        inst_type = filters.get('institution_type')
        if inst_type:
            inst_type = inst_type.upper()
            if inst_type == 'COLLEGE':
                qs = qs.filter(college__isnull=False)
            elif inst_type == 'UNIVERSITY':
                qs = qs.filter(university__isnull=False)
            elif inst_type == 'NONE':
                qs = qs.filter(college__isnull=True, university__isnull=True)

        inst_id = filters.get('institution_id')
        if inst_id:
            qs = qs.filter(
                models.Q(college_id=inst_id) |
                models.Q(university_id=inst_id) |
                models.Q(college__aishe_code__iexact=str(inst_id)) |
                models.Q(university__aishe_code__iexact=str(inst_id))
            )

        ordering = filters.get('ordering', '-id')
        valid_orderings = ('id', '-id', 'email', '-email', 'full_name', '-full_name', 'role', '-role')
        if ordering not in valid_orderings:
            ordering = '-id'
        qs = qs.order_by(ordering)

        total_count = qs.count()
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        start = (page - 1) * page_size
        end = start + page_size
        users = list(qs[start:end])

        return {
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 1,
            "users": users,
        }

    @classmethod
    def get_user_detail(cls, actor, user_id):
        from .api_permissions import AdminPermissionDenied

        if not (getattr(actor, 'is_superuser', False) or getattr(actor, 'role', '') in ('head_admin', 'state_admin', 'sub_admin', 'admin', 'council_admin')):
            raise AdminPermissionDenied("Administrative authority required.", code="ADMIN_REQUIRED")

        try:
            target_user = User.objects.select_related('college', 'university').get(pk=user_id)
        except User.DoesNotExist:
            raise AdminValidationError(f"User with ID {user_id} does not exist.", code="USER_NOT_FOUND")

        audit_logs = list(UserAuditLog.objects.filter(target_user=target_user).select_related('actor')[:25])
        return target_user, audit_logs

    @classmethod
    def create_user(cls, actor, validated_data, ip_address=None):
        from .api_permissions import AdminPermissionDenied
        import secrets, string

        role = validated_data.get('role', 'principal')
        is_actor_head_admin = getattr(actor, 'is_superuser', False) or getattr(actor, 'role', '') == 'head_admin'

        if role in cls.PRIVILEGED_ROLES and not is_actor_head_admin:
            raise AdminPermissionDenied(
                f"Only the Head Administrator can create accounts with privileged role '{role}'.",
                code="HEAD_ADMIN_REQUIRED"
            )

        email = validated_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise AdminValidationError(f"A user with email '{email}' already exists.", code="USER_ALREADY_EXISTS")

        password = validated_data.get('password')
        send_invite = validated_data.get('send_invite', True)
        is_pending_activation = not bool(password)

        if not password:
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            password = "".join(secrets.choice(alphabet) for _ in range(16))

        full_name = validated_data.get('full_name', '').strip()
        phone_number = validated_data.get('phone_number', '').strip()
        college = validated_data.get('college')
        university = validated_data.get('university')

        new_user = User.objects.create_user(
            email=email,
            full_name=full_name,
            role=role,
            password=password,
            college=college,
            university=university,
            phone_number=phone_number,
            is_staff=bool(role in ('head_admin', 'state_admin', 'sub_admin', 'admin', 'council_admin')),
        )

        if is_pending_activation:
            new_user.is_active = False
            new_user.set_unusable_password()
            new_user.save(update_fields=['is_active', 'password'])

        UserAuditLog.objects.create(
            actor=actor,
            target_user=new_user,
            action="USER_CREATED",
            details={
                "role": role,
                "email": email,
                "created_by": actor.email if actor else "SYSTEM",
                "is_pending_activation": is_pending_activation,
                "institution": college.name if college else (university.name if university else None),
            },
            ip_address=ip_address,
        )

        # Issue invitation token & send email
        raw_token = None
        if send_invite or is_pending_activation:
            try:
                from apps.authentication.activation_service import AccountActivationService
                raw_token, token_obj = AccountActivationService.create_invitation(new_user, created_by=actor)
                AccountActivationService.send_invitation_email(new_user, raw_token)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error("Failed to dispatch invitation for user %s: %s", new_user.email, str(e))
        new_user._raw_activation_token = raw_token


        # Optional committee framework assignment
        committee_framework = validated_data.get('committee_framework')
        if committee_framework and role in ('committee', 'committee_chair', 'empowered_committee', 'empowered_committee_chair'):
            from apps.evidence.models import ReviewerAuthorization
            ReviewerAuthorization.objects.create(
                user=new_user,
                framework=committee_framework,
                is_active=True,
                granted_by=actor,
            )
            UserAuditLog.objects.create(
                actor=actor,
                target_user=new_user,
                action="COMMITTEE_ASSIGNED",
                details={
                    "framework": committee_framework,
                    "granted_by": actor.email if actor else "SYSTEM",
                },
                ip_address=ip_address,
            )

        return new_user

    @classmethod
    def update_user(cls, actor, user_id, validated_data, ip_address=None):
        from .api_permissions import AdminPermissionDenied

        try:
            target_user = User.objects.select_related('college', 'university').get(pk=user_id)
        except User.DoesNotExist:
            raise AdminValidationError(f"User with ID {user_id} does not exist.", code="USER_NOT_FOUND")

        is_actor_head_admin = getattr(actor, 'is_superuser', False) or getattr(actor, 'role', '') == 'head_admin'
        changes = []

        # 1. Role modification
        if 'role' in validated_data and validated_data['role'] != target_user.role:
            new_role = validated_data['role']
            if not is_actor_head_admin:
                raise AdminPermissionDenied(
                    "Only the Head Administrator can assign or modify user roles.",
                    code="HEAD_ADMIN_REQUIRED"
                )

            # Protect last active Head Admin
            if target_user.role == 'head_admin' and target_user.is_active:
                remaining = User.objects.filter(role='head_admin', is_active=True).exclude(pk=target_user.pk).count()
                if remaining == 0:
                    raise AdminValidationError(
                        "Cannot demote the last active Head Administrator.",
                        code="LAST_HEAD_ADMIN_PROTECTED"
                    )

            old_role = target_user.role
            target_user.role = new_role
            target_user.is_staff = bool(new_role in ('head_admin', 'state_admin', 'sub_admin', 'admin', 'council_admin'))
            changes.append(("ROLE_CHANGED", {"old_role": old_role, "new_role": new_role}))

        # 2. Status toggle (is_active)
        if 'is_active' in validated_data and validated_data['is_active'] != target_user.is_active:
            new_is_active = validated_data['is_active']
            if not is_actor_head_admin:
                raise AdminPermissionDenied(
                    "Only the Head Administrator can activate or deactivate accounts.",
                    code="HEAD_ADMIN_REQUIRED"
                )

            if target_user.role == 'head_admin' and not new_is_active:
                remaining = User.objects.filter(role='head_admin', is_active=True).exclude(pk=target_user.pk).count()
                if remaining == 0:
                    raise AdminValidationError(
                        "Cannot deactivate the last active Head Administrator.",
                        code="LAST_HEAD_ADMIN_PROTECTED"
                    )

            target_user.is_active = new_is_active
            action = "ACCOUNT_ACTIVATED" if new_is_active else "ACCOUNT_DEACTIVATED"
            changes.append((action, {"is_active": new_is_active}))

        # 3. Profile details
        profile_details = {}
        if 'full_name' in validated_data and validated_data['full_name'] != target_user.full_name:
            profile_details['old_full_name'] = target_user.full_name
            profile_details['new_full_name'] = validated_data['full_name']
            target_user.full_name = validated_data['full_name']

        if 'phone_number' in validated_data and validated_data['phone_number'] != target_user.phone_number:
            profile_details['old_phone'] = target_user.phone_number
            profile_details['new_phone'] = validated_data['phone_number']
            target_user.phone_number = validated_data['phone_number']

        if 'college' in validated_data:
            target_user.college = validated_data['college']
            profile_details['college_id'] = target_user.college.pk if target_user.college else None

        if 'university' in validated_data:
            target_user.university = validated_data['university']
            profile_details['university_id'] = target_user.university.pk if target_user.university else None

        if profile_details:
            changes.append(("PROFILE_UPDATED", profile_details))

        target_user.save()

        # 4. Committee framework update if supplied
        if 'committee_framework' in validated_data and target_user.role in ('committee', 'committee_chair', 'empowered_committee', 'empowered_committee_chair'):
            c_fw = validated_data['committee_framework']
            if c_fw:
                cls.manage_committee_assignment(actor, target_user.pk, framework=c_fw, action="assign", ip_address=ip_address)

        for action, details in changes:
            UserAuditLog.objects.create(
                actor=actor,
                target_user=target_user,
                action=action,
                details=details,
                ip_address=ip_address,
            )

        return target_user

    @classmethod
    def reset_password(cls, actor, user_id, new_password=None, ip_address=None):
        from .api_permissions import AdminPermissionDenied
        import secrets, string

        is_actor_head_admin = getattr(actor, 'is_superuser', False) or getattr(actor, 'role', '') == 'head_admin'
        if not is_actor_head_admin:
            raise AdminPermissionDenied("Only the Head Administrator can reset user account passwords.", code="HEAD_ADMIN_REQUIRED")

        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise AdminValidationError(f"User with ID {user_id} does not exist.", code="USER_NOT_FOUND")

        if not new_password:
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            new_password = "".join(secrets.choice(alphabet) for _ in range(14))

        target_user.set_password(new_password)
        target_user.save()

        UserAuditLog.objects.create(
            actor=actor,
            target_user=target_user,
            action="PASSWORD_RESET",
            details={
                "target_email": target_user.email,
                "reset_by": actor.email if actor else "SYSTEM",
            },
            ip_address=ip_address,
        )

        return target_user

    @classmethod
    def delete_user(cls, actor, user_id, ip_address=None):
        """
        Permanently remove a user account.
        Strictly restricted to the Head Administrator.
        Guards against deleting oneself or the last active Head Administrator.
        """
        from .api_permissions import AdminPermissionDenied

        is_actor_head_admin = getattr(actor, 'is_superuser', False) or getattr(actor, 'role', '') == 'head_admin'
        if not is_actor_head_admin:
            raise AdminPermissionDenied("Only the Head Administrator can remove user accounts.", code="HEAD_ADMIN_REQUIRED")

        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise AdminValidationError(f"User with ID {user_id} does not exist.", code="USER_NOT_FOUND")

        # Guard: cannot delete oneself
        if target_user.pk == actor.pk:
            raise AdminValidationError("You cannot remove your own administrator account.", code="CANNOT_DELETE_SELF")

        # Guard: cannot delete the last active head_admin
        if target_user.role == 'head_admin' and target_user.is_active:
            remaining = User.objects.filter(role='head_admin', is_active=True).exclude(pk=target_user.pk).count()
            if remaining == 0:
                raise AdminValidationError(
                    "Cannot remove the last active Head Administrator.",
                    code="LAST_HEAD_ADMIN_PROTECTED"
                )

        target_info = {
            "id": target_user.id,
            "email": target_user.email,
            "full_name": target_user.full_name,
            "role": target_user.role,
        }

        target_user.delete()
        return target_info

    @classmethod
    def manage_committee_assignment(cls, actor, user_id, framework, action="assign", institution_id="", ip_address=None):
        from .api_permissions import AdminPermissionDenied
        from apps.evidence.models import ReviewerAuthorization

        is_actor_head_admin = (
            getattr(actor, 'is_superuser', False)
            or getattr(actor, 'role', '') in ('head_admin', 'state_admin', 'sub_admin', 'admin')
        )
        if not is_actor_head_admin:
            raise AdminPermissionDenied("Administrative authority required to manage committee authorizations.", code="ADMIN_REQUIRED")

        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise AdminValidationError(f"User with ID {user_id} does not exist.", code="USER_NOT_FOUND")

        if action == "assign":
            auth, created = ReviewerAuthorization.objects.get_or_create(
                user=target_user,
                framework=framework,
                institution_id=institution_id or "",
                defaults={"is_active": True, "granted_by": actor}
            )
            if not created and not auth.is_active:
                auth.is_active = True
                auth.granted_by = actor
                auth.save()

            UserAuditLog.objects.create(
                actor=actor,
                target_user=target_user,
                action="COMMITTEE_ASSIGNED",
                details={
                    "framework": framework,
                    "institution_id": institution_id,
                    "assigned_by": actor.email if actor else "SYSTEM"
                },
                ip_address=ip_address,
            )
            return auth
        elif action == "remove":
            qs = ReviewerAuthorization.objects.filter(user=target_user, framework=framework)
            if institution_id:
                qs = qs.filter(institution_id=institution_id)
            for auth in qs:
                auth.is_active = False
                auth.save()

            UserAuditLog.objects.create(
                actor=actor,
                target_user=target_user,
                action="COMMITTEE_REMOVED",
                details={
                    "framework": framework,
                    "institution_id": institution_id,
                    "removed_by": actor.email if actor else "SYSTEM"
                },
                ip_address=ip_address,
            )
            return True
        else:
            raise AdminValidationError(f"Invalid committee action '{action}'. Must be 'assign' or 'remove'.")


def sanitize_audit_details(details):
    """
    Scrub any sensitive credentials, tokens, or hashes from audit log payloads.
    """
    if not isinstance(details, dict):
        return {}
    sanitized = {}
    sensitive_keys = {"password", "token", "otp", "secret", "salt", "hash", "temp_password", "temporary_password"}
    for k, v in details.items():
        if any(sens in k.lower() for sens in sensitive_keys):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_audit_details(v)
        else:
            sanitized[k] = v
    return sanitized


class HeadAdminControlCentreService:
    """
    Dedicated authoritative service for the Head Admin Control Centre.
    Aggregates:
    - Administrative staffing breakdown (Head Admins, Sub-Admins, Screening & Empowered Committees)
    - Institution counts and assessment workflow stage distribution
    - Operational exceptions and bottlenecks (statutory blocks, returned for correction, unassigned queues)
    - Real-time system health and governance warnings
    - Safe, sanitized privileged audit trail with least-privilege role segregation.
    """

    @classmethod
    def build_summary(cls, actor=None) -> Dict[str, Any]:
        from apps.university.models import University
        from apps.college.models import College

        is_head_admin = bool(
            getattr(actor, "is_superuser", False) or getattr(actor, "role", "") == "head_admin"
        )

        # 1. Registered Institutions
        colleges_count = College.objects.count()
        universities_count = University.objects.count()
        total_institutions = colleges_count + universities_count

        # 2. Latest Assessments by Institution (Zero duplicate scoring calculation)
        uni_assess = StateOverviewService._latest_by(
            UniversityAssessment.objects.select_related("assigned_reviewer", "university"),
            "university_id",
        )
        col_assess = StateOverviewService._latest_by(
            CollegeAssessment.objects.select_related("assigned_reviewer", "college"),
            "college_id",
        )

        by_stage = {s: 0 for s in STATE_STAGES}
        by_framework = {
            "UNIVERSITY_2026": {s: 0 for s in STATE_STAGES},
            "COLLEGE_2026": {s: 0 for s in STATE_STAGES},
        }

        unassigned_assessments = []
        blocked_assessments = []
        returned_assessments = []
        inactive_reviewer_assignments = []

        all_unis = list(University.objects.all())
        all_cols = list(College.objects.all())

        for u in all_unis:
            a = uni_assess.get(u.pk)
            stage = STATE_STAGE_BY_STATUS.get(a.status, "UNDER_REVIEW") if a else "NOT_STARTED"
            by_stage[stage] += 1
            by_framework["UNIVERSITY_2026"][stage] += 1

            if a:
                reviewer = a.assigned_reviewer
                if stage in REVIEW_STAGES and not reviewer:
                    unassigned_assessments.append({
                        "assessment_id": a.assessment_id,
                        "institution_name": u.name,
                        "aishe_code": u.aishe_code,
                        "framework": UNIVERSITY_FRAMEWORK_CODE,
                        "status": a.status,
                        "stage": stage,
                        "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                    })
                if getattr(a, "certification_status", "") == "BLOCKED_BY_SPECIFICATION" or a.status == "BLOCKED":
                    blocked_assessments.append({
                        "assessment_id": a.assessment_id,
                        "institution_name": u.name,
                        "aishe_code": u.aishe_code,
                        "framework": UNIVERSITY_FRAMEWORK_CODE,
                        "reason": "Statutory specifications blocked",
                        "status": a.status,
                    })
                if stage == "RETURNED" or a.status in ("RETURNED", "REJECTED"):
                    returned_assessments.append({
                        "assessment_id": a.assessment_id,
                        "institution_name": u.name,
                        "aishe_code": u.aishe_code,
                        "framework": UNIVERSITY_FRAMEWORK_CODE,
                        "status": a.status,
                        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
                    })
                if reviewer and not reviewer.is_active and stage in REVIEW_STAGES:
                    inactive_reviewer_assignments.append({
                        "assessment_id": a.assessment_id,
                        "institution_name": u.name,
                        "reviewer_name": reviewer.full_name,
                        "reviewer_email": reviewer.email,
                        "framework": UNIVERSITY_FRAMEWORK_CODE,
                    })

        for c in all_cols:
            a = col_assess.get(c.pk)
            stage = STATE_STAGE_BY_STATUS.get(a.status, "UNDER_REVIEW") if a else "NOT_STARTED"
            by_stage[stage] += 1
            by_framework["COLLEGE_2026"][stage] += 1

            if a:
                reviewer = a.assigned_reviewer
                if stage in REVIEW_STAGES and not reviewer:
                    unassigned_assessments.append({
                        "assessment_id": a.assessment_id,
                        "institution_name": c.name,
                        "aishe_code": c.aishe_code,
                        "framework": COLLEGE_FRAMEWORK_CODE,
                        "status": a.status,
                        "stage": stage,
                        "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                    })
                if getattr(a, "certification_status", "") == "BLOCKED_BY_SPECIFICATION" or a.status == "BLOCKED":
                    blocked_assessments.append({
                        "assessment_id": a.assessment_id,
                        "institution_name": c.name,
                        "aishe_code": c.aishe_code,
                        "framework": COLLEGE_FRAMEWORK_CODE,
                        "reason": "Statutory specifications blocked (Criteria C5, C7, C8, C16)",
                        "status": a.status,
                    })
                if stage == "RETURNED" or a.status in ("RETURNED", "REJECTED"):
                    returned_assessments.append({
                        "assessment_id": a.assessment_id,
                        "institution_name": c.name,
                        "aishe_code": c.aishe_code,
                        "framework": COLLEGE_FRAMEWORK_CODE,
                        "status": a.status,
                        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
                    })
                if reviewer and not reviewer.is_active and stage in REVIEW_STAGES:
                    inactive_reviewer_assignments.append({
                        "assessment_id": a.assessment_id,
                        "institution_name": c.name,
                        "reviewer_name": reviewer.full_name,
                        "reviewer_email": reviewer.email,
                        "framework": COLLEGE_FRAMEWORK_CODE,
                    })

        # 3. Governance Staffing Metrics (Real database aggregation)
        head_admin_total = User.objects.filter(role="head_admin").count()
        head_admin_active = User.objects.filter(role="head_admin", is_active=True).count()

        sub_admin_total = User.objects.filter(role__in=("sub_admin", "admin")).count()
        sub_admin_active = User.objects.filter(role__in=("sub_admin", "admin"), is_active=True).count()

        sc_chair_total = User.objects.filter(role="committee_chair").count()
        sc_chair_active = User.objects.filter(role="committee_chair", is_active=True).count()

        sc_member_total = User.objects.filter(role="committee").count()
        sc_member_active = User.objects.filter(role="committee", is_active=True).count()

        ec_chair_total = User.objects.filter(role="empowered_committee_chair").count()
        ec_chair_active = User.objects.filter(role="empowered_committee_chair", is_active=True).count()

        ec_member_total = User.objects.filter(role="empowered_committee").count()
        ec_member_active = User.objects.filter(role="empowered_committee", is_active=True).count()

        total_active_admins = head_admin_active + sub_admin_active

        # 4. Actionable Warnings
        warnings = []
        if head_admin_active == 1:
            warnings.append({
                "level": "WARNING",
                "code": "SINGLE_HEAD_ADMIN",
                "title": "Single Head Administrator",
                "message": "Only 1 active Head Administrator configured. Provision a backup Head Administrator for continuity.",
            })
        elif head_admin_active == 0:
            warnings.append({
                "level": "CRITICAL",
                "code": "NO_ACTIVE_HEAD_ADMIN",
                "title": "No Active Head Administrator",
                "message": "No active Head Administrator accounts exist. Immediate CLI provisioning required.",
            })

        if len(unassigned_assessments) > 0:
            warnings.append({
                "level": "URGENT",
                "code": "UNASSIGNED_SUBMISSIONS",
                "title": "Unassigned Assessments",
                "message": f"{len(unassigned_assessments)} submitted assessment(s) awaiting reviewer assignment.",
                "count": len(unassigned_assessments),
            })

        if len(blocked_assessments) > 0:
            warnings.append({
                "level": "INFO",
                "code": "SPECIFICATION_BLOCKS",
                "title": "Statutory Specification Blocks",
                "message": f"{len(blocked_assessments)} assessment(s) paused on statutory criteria ambiguities.",
                "count": len(blocked_assessments),
            })

        if len(returned_assessments) > 0:
            warnings.append({
                "level": "INFO",
                "code": "RETURNED_ASSESSMENTS",
                "title": "Returned Assessments",
                "message": f"{len(returned_assessments)} assessment(s) currently returned for correction.",
                "count": len(returned_assessments),
            })

        if len(inactive_reviewer_assignments) > 0:
            warnings.append({
                "level": "WARNING",
                "code": "INACTIVE_REVIEWER_ASSIGNMENT",
                "title": "Deactivated Reviewer Assigned",
                "message": f"{len(inactive_reviewer_assignments)} active assessment(s) are assigned to deactivated reviewers. Reassignment required.",
                "count": len(inactive_reviewer_assignments),
            })

        if sc_chair_active == 0:
            warnings.append({
                "level": "WARNING",
                "code": "NO_SCREENING_CHAIR",
                "title": "No Screening Committee Chair",
                "message": "No active Screening Committee Chair is registered. Certification cannot proceed without a Chair.",
            })

        if ec_chair_active == 0 and ec_member_active == 0:
            warnings.append({
                "level": "INFO",
                "code": "EMPOWERED_COMMITTEE_PENDING",
                "title": "Empowered Committee Unstaffed",
                "message": "Empowered Committee has no active members provisioned.",
            })

        # 5. Privileged Audit Trail (Least privilege: only Head Admin receives recent user audit records)
        recent_privileged_actions = []
        if is_head_admin:
            logs = UserAuditLog.objects.select_related("actor", "target_user").order_by("-timestamp")[:15]
            for log in logs:
                recent_privileged_actions.append({
                    "id": log.id,
                    "action": log.action,
                    "action_label": log.get_action_display(),
                    "actor_id": log.actor_id,
                    "actor_email": log.actor.email if log.actor else "System / CLI",
                    "actor_name": log.actor.full_name if log.actor else "System",
                    "target_user_id": log.target_user_id,
                    "target_user_email": log.target_user.email if log.target_user else "Unknown",
                    "target_user_name": log.target_user.full_name if log.target_user else "Unknown",
                    "target_user_role": log.target_user.role if log.target_user else "",
                    "details": sanitize_audit_details(log.details),
                    "ip_address": log.ip_address,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                })

        # Assemble responses
        governance_data = {
            "is_full_governance": is_head_admin,
            "administrators": {
                "head_admins": {
                    "total": head_admin_total,
                    "active": head_admin_active,
                    "inactive": head_admin_total - head_admin_active,
                },
                "sub_admins": {
                    "total": sub_admin_total,
                    "active": sub_admin_active,
                    "inactive": sub_admin_total - sub_admin_active,
                },
                "total_active": total_active_admins,
            },
            "screening_committee": {
                "chairs": {
                    "total": sc_chair_total,
                    "active": sc_chair_active,
                    "inactive": sc_chair_total - sc_chair_active,
                },
                "reviewers": {
                    "total": sc_member_total,
                    "active": sc_member_active,
                    "inactive": sc_member_total - sc_member_active,
                },
                "total_members": sc_chair_total + sc_member_total,
                "total_active": sc_chair_active + sc_member_active,
            },
            "empowered_committee": {
                "chairs": {
                    "total": ec_chair_total,
                    "active": ec_chair_active,
                    "inactive": ec_chair_total - ec_chair_active,
                },
                "reviewers": {
                    "total": ec_member_total,
                    "active": ec_member_active,
                    "inactive": ec_member_total - ec_member_active,
                },
                "total_members": ec_chair_total + ec_member_total,
                "total_active": ec_chair_active + ec_member_active,
            },
        }

        # If actor is not Head Admin, apply least-privilege redaction to sensitive admin internals
        if not is_head_admin:
            governance_data["administrators"] = {
                "total_active": total_active_admins,
            }

        institutions_data = {
            "total": total_institutions,
            "colleges": colleges_count,
            "universities": universities_count,
            "started": total_institutions - by_stage["NOT_STARTED"],
            "by_stage": by_stage,
            "by_framework": by_framework,
        }

        operations_data = {
            "unassigned_count": len(unassigned_assessments),
            "unassigned_items": unassigned_assessments[:10],
            "blocked_count": len(blocked_assessments),
            "blocked_items": blocked_assessments[:10],
            "returned_count": len(returned_assessments),
            "returned_items": returned_assessments[:10],
            "inactive_reviewer_assignments_count": len(inactive_reviewer_assignments),
            "inactive_reviewer_assignments_items": inactive_reviewer_assignments[:10],
        }

        return {
            "governance": governance_data,
            "institutions": institutions_data,
            "operations": operations_data,
            "warnings": warnings,
            "recent_privileged_actions": recent_privileged_actions,
        }

    @classmethod
    def list_audit_trail(cls, actor, filters=None, page=1, page_size=25) -> Dict[str, Any]:
        from .api_permissions import AdminPermissionDenied

        if not (getattr(actor, "is_superuser", False) or getattr(actor, "role", "") == "head_admin"):
            raise AdminPermissionDenied(
                "Only the Head Administrator can view the global audit trail.",
                code="HEAD_ADMIN_REQUIRED",
            )

        filters = filters or {}
        qs = UserAuditLog.objects.select_related("actor", "target_user").all()

        action = filters.get("action")
        if action:
            qs = qs.filter(action=action)

        target_role = filters.get("target_role")
        if target_role:
            qs = qs.filter(target_user__role=target_role)

        q = filters.get("q") or filters.get("search")
        if q and q.strip():
            query = q.strip()
            qs = qs.filter(
                models.Q(actor__email__icontains=query) |
                models.Q(actor__full_name__icontains=query) |
                models.Q(target_user__email__icontains=query) |
                models.Q(target_user__full_name__icontains=query) |
                models.Q(action__icontains=query)
            )

        qs = qs.order_by("-timestamp")
        total_count = qs.count()
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        start = (page - 1) * page_size
        end = start + page_size
        logs = list(qs[start:end])

        results = []
        for log in logs:
            results.append({
                "id": log.id,
                "action": log.action,
                "action_label": log.get_action_display(),
                "actor_id": log.actor_id,
                "actor_email": log.actor.email if log.actor else "System / CLI",
                "actor_name": log.actor.full_name if log.actor else "System",
                "target_user_id": log.target_user_id,
                "target_user_email": log.target_user.email if log.target_user else "Unknown",
                "target_user_name": log.target_user.full_name if log.target_user else "Unknown",
                "target_user_role": log.target_user.role if log.target_user else "",
                "details": sanitize_audit_details(log.details),
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            })

        return {
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 1,
            "results": results,
        }


class CommitteeService:
    """
    Committee Management Service.
    Enforces relational committee boundaries, framework isolation,
    chair eligibility, duplicate active membership prevention, and audit logging.
    """

    ELIGIBLE_CHAIR_ROLES = frozenset(['committee_chair', 'empowered_committee_chair'])
    ELIGIBLE_MEMBER_ROLES = frozenset(['committee', 'committee_chair', 'empowered_committee', 'empowered_committee_chair'])

    @classmethod
    def list_committees(cls, filters=None):
        from .models import Committee
        filters = filters or {}
        qs = Committee.objects.select_related('chair').prefetch_related('memberships__user')

        framework = filters.get('framework')
        if framework and framework != 'ALL':
            qs = qs.filter(framework__in=[framework, 'ALL'])

        committee_type = filters.get('committee_type')
        if committee_type:
            qs = qs.filter(committee_type=committee_type)

        is_active = filters.get('is_active')
        if is_active is not None and is_active != '':
            if isinstance(is_active, str):
                is_active_bool = is_active.lower() in ('true', '1')
            else:
                is_active_bool = bool(is_active)
            qs = qs.filter(is_active=is_active_bool)

        q = filters.get('q') or filters.get('search')
        if q and q.strip():
            query = q.strip()
            qs = qs.filter(
                models.Q(name__icontains=query) |
                models.Q(description__icontains=query) |
                models.Q(chair__full_name__icontains=query) |
                models.Q(chair__email__icontains=query)
            )

        return qs.order_by('-created_at')

    @classmethod
    def get_committee_detail(cls, committee_id):
        from .models import Committee
        try:
            return Committee.objects.select_related('chair').prefetch_related('memberships__user', 'memberships__assigned_by').get(pk=committee_id)
        except Committee.DoesNotExist:
            raise AdminValidationError(f"Committee with ID {committee_id} does not exist.", code="COMMITTEE_NOT_FOUND")

    @classmethod
    def create_committee(cls, actor, data, ip_address=None):
        from .models import Committee, CommitteeMember
        from apps.evidence.models import ReviewerAuthorization

        name = data['name'].strip()
        if Committee.objects.filter(name__iexact=name).exists():
            raise AdminValidationError(f"A committee named '{name}' already exists.", code="COMMITTEE_ALREADY_EXISTS")

        description = data.get('description', '').strip()
        committee_type = data.get('committee_type', 'SCREENING')
        framework = data.get('framework', 'COLLEGE_2026')
        is_active = data.get('is_active', True)
        chair_id = data.get('chair_id')

        chair = None
        if chair_id:
            try:
                chair = User.objects.get(pk=chair_id)
            except User.DoesNotExist:
                raise AdminValidationError(f"User with ID {chair_id} does not exist.", code="USER_NOT_FOUND")

            if chair.role not in cls.ELIGIBLE_CHAIR_ROLES:
                raise AdminValidationError(
                    f"User '{chair.email}' has role '{chair.role}'. Only users with role 'committee_chair' or 'empowered_committee_chair' can be appointed as Committee Chair.",
                    code="INVALID_CHAIR_ROLE"
                )

        committee = Committee.objects.create(
            name=name,
            description=description,
            committee_type=committee_type,
            framework=framework,
            chair=chair,
            is_active=is_active,
        )

        if chair:
            CommitteeMember.objects.create(
                committee=committee,
                user=chair,
                role_in_committee='chair',
                assigned_by=actor,
                is_active=True,
            )
            ReviewerAuthorization.objects.update_or_create(
                user=chair,
                framework=framework,
                defaults={'is_active': True, 'granted_by': actor}
            )

        UserAuditLog.objects.create(
            actor=actor,
            target_user=chair if chair else actor,
            action="COMMITTEE_CREATED",
            details={
                "committee_id": committee.id,
                "name": committee.name,
                "framework": committee.framework,
                "chair": chair.email if chair else None,
            },
            ip_address=ip_address,
        )

        return committee

    @classmethod
    def update_committee(cls, actor, committee_id, data, ip_address=None):
        committee = cls.get_committee_detail(committee_id)
        changes = {}

        if 'name' in data and data['name'].strip() != committee.name:
            new_name = data['name'].strip()
            from .models import Committee
            if Committee.objects.filter(name__iexact=new_name).exclude(pk=committee.pk).exists():
                raise AdminValidationError(f"A committee named '{new_name}' already exists.", code="COMMITTEE_ALREADY_EXISTS")
            changes['name'] = {'old': committee.name, 'new': new_name}
            committee.name = new_name

        if 'description' in data:
            committee.description = data['description'].strip()

        if 'is_active' in data and data['is_active'] != committee.is_active:
            changes['is_active'] = {'old': committee.is_active, 'new': data['is_active']}
            committee.is_active = data['is_active']

        committee.save()

        if changes:
            UserAuditLog.objects.create(
                actor=actor,
                target_user=committee.chair if committee.chair else actor,
                action="COMMITTEE_MODIFIED",
                details={
                    "committee_id": committee.id,
                    "changes": changes,
                },
                ip_address=ip_address,
            )

        return committee

    @classmethod
    def assign_chair(cls, actor, committee_id, chair_id, ip_address=None):
        from .models import CommitteeMember
        from apps.evidence.models import ReviewerAuthorization

        committee = cls.get_committee_detail(committee_id)

        try:
            new_chair = User.objects.get(pk=chair_id)
        except User.DoesNotExist:
            raise AdminValidationError(f"User with ID {chair_id} does not exist.", code="USER_NOT_FOUND")

        if new_chair.role not in cls.ELIGIBLE_CHAIR_ROLES:
            raise AdminValidationError(
                f"User '{new_chair.email}' has role '{new_chair.role}'. Only users with role 'committee_chair' can chair a committee.",
                code="INVALID_CHAIR_ROLE"
            )

        # Cross-framework check: verify chair does not have conflicting specific framework authorizations
        if committee.framework in ('COLLEGE_2026', 'UNIVERSITY_2026'):
            opposing = 'UNIVERSITY_2026' if committee.framework == 'COLLEGE_2026' else 'COLLEGE_2026'
            has_opposing = ReviewerAuthorization.objects.filter(
                user=new_chair, framework=opposing, is_active=True
            ).exists()
            has_unified = ReviewerAuthorization.objects.filter(
                user=new_chair, framework='ALL', is_active=True
            ).exists()
            if has_opposing and not has_unified:
                raise AdminValidationError(
                    f"User '{new_chair.email}' already holds active authorization for conflicting framework '{opposing}'. Cross-framework chair assignment requires unified authorization.",
                    code="CROSS_FRAMEWORK_CONFLICT"
                )

        old_chair = committee.chair
        committee.chair = new_chair
        committee.save()

        # Update previous chair membership to member or deactivate if desired
        if old_chair and old_chair != new_chair:
            CommitteeMember.objects.filter(
                committee=committee, user=old_chair, is_active=True
            ).update(role_in_committee='member')

        # Add or update new chair membership
        membership, created = CommitteeMember.objects.update_or_create(
            committee=committee,
            user=new_chair,
            defaults={
                'role_in_committee': 'chair',
                'is_active': True,
                'assigned_by': actor,
                'removed_at': None,
            }
        )

        # Reconcile ReviewerAuthorization
        ReviewerAuthorization.objects.update_or_create(
            user=new_chair,
            framework=committee.framework,
            defaults={'is_active': True, 'granted_by': actor}
        )

        UserAuditLog.objects.create(
            actor=actor,
            target_user=new_chair,
            action="COMMITTEE_CHAIR_ASSIGNED",
            details={
                "committee_id": committee.id,
                "committee_name": committee.name,
                "old_chair": old_chair.email if old_chair else None,
                "new_chair": new_chair.email,
                "framework": committee.framework,
            },
            ip_address=ip_address,
        )

        return committee

    @classmethod
    def add_member(cls, actor, committee_id, user_id, role_in_committee='member', ip_address=None):
        from .models import CommitteeMember
        from apps.evidence.models import ReviewerAuthorization

        committee = cls.get_committee_detail(committee_id)

        try:
            member_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise AdminValidationError(f"User with ID {user_id} does not exist.", code="USER_NOT_FOUND")

        if member_user.role not in cls.ELIGIBLE_MEMBER_ROLES:
            raise AdminValidationError(
                f"User '{member_user.email}' has role '{member_user.role}'. Only committee reviewers and chairs can be assigned to a committee.",
                code="INVALID_MEMBER_ROLE"
            )

        # Check duplicate active membership
        if CommitteeMember.objects.filter(committee=committee, user=member_user, is_active=True).exists():
            raise AdminValidationError(
                f"User '{member_user.email}' is already an active member of committee '{committee.name}'.",
                code="DUPLICATE_ACTIVE_MEMBERSHIP"
            )

        # Cross-framework check
        if committee.framework in ('COLLEGE_2026', 'UNIVERSITY_2026'):
            opposing = 'UNIVERSITY_2026' if committee.framework == 'COLLEGE_2026' else 'COLLEGE_2026'
            has_opposing = ReviewerAuthorization.objects.filter(
                user=member_user, framework=opposing, is_active=True
            ).exists()
            has_unified = ReviewerAuthorization.objects.filter(
                user=member_user, framework='ALL', is_active=True
            ).exists()
            if has_opposing and not has_unified:
                raise AdminValidationError(
                    f"User '{member_user.email}' already holds active authorization for conflicting framework '{opposing}'. Cross-framework reviewer assignment requires unified authorization.",
                    code="CROSS_FRAMEWORK_CONFLICT"
                )

        membership, created = CommitteeMember.objects.update_or_create(
            committee=committee,
            user=member_user,
            defaults={
                'role_in_committee': role_in_committee,
                'is_active': True,
                'assigned_by': actor,
                'removed_at': None,
            }
        )

        # Reconcile ReviewerAuthorization
        ReviewerAuthorization.objects.update_or_create(
            user=member_user,
            framework=committee.framework,
            defaults={'is_active': True, 'granted_by': actor}
        )

        UserAuditLog.objects.create(
            actor=actor,
            target_user=member_user,
            action="COMMITTEE_MEMBER_ADDED",
            details={
                "committee_id": committee.id,
                "committee_name": committee.name,
                "role_in_committee": role_in_committee,
                "framework": committee.framework,
            },
            ip_address=ip_address,
        )

        return membership

    @classmethod
    def remove_member(cls, actor, committee_id, user_id, ip_address=None):
        from .models import CommitteeMember
        from django.utils import timezone

        committee = cls.get_committee_detail(committee_id)

        try:
            membership = CommitteeMember.objects.get(committee=committee, user_id=user_id, is_active=True)
        except CommitteeMember.DoesNotExist:
            raise AdminValidationError(
                f"User with ID {user_id} is not an active member of committee '{committee.name}'.",
                code="MEMBERSHIP_NOT_FOUND"
            )

        member_user = membership.user
        membership.is_active = False
        membership.removed_at = timezone.now()
        membership.save()

        # If user was chair, remove chair reference
        if committee.chair_id == member_user.id:
            committee.chair = None
            committee.save()

        UserAuditLog.objects.create(
            actor=actor,
            target_user=member_user,
            action="COMMITTEE_MEMBER_REMOVED",
            details={
                "committee_id": committee.id,
                "committee_name": committee.name,
                "framework": committee.framework,
            },
            ip_address=ip_address,
        )

        return True



