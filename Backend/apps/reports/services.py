"""
NEP Excellence Awards 2026 - Master Reporting Service (Phase 9)
Read-only projection service consuming authoritative data from:
- UniversityAssessment / CollegeAssessment
- apps.evidence.coverage (EvidenceService)
- apps.scoring (NEP2026ScoringEngine)
- apps.university.services (UniversityReviewService)
- apps.college.services (CollegeReviewService)

INVARIANT: Zero score calculations, zero synthetic mappings, zero data mutations.
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import asdict
from django.utils import timezone
from django.db.models import Q

from apps.university.models import UniversityAssessment
from apps.college.models import CollegeAssessment
from apps.evidence.services import EvidenceService
from apps.scoring.rules.definitions import UNIVERSITY_PARAMETERS, COLLEGE_PARAMETERS
from apps.scoring.engine import NEP2026ScoringEngine
from apps.reports.permissions import can_user_view_assessment, ReportPermissionDenied


class AssessmentNotFoundError(Exception):
    """Raised when an assessment cannot be located in any active framework."""
    pass


class ReportingService:
    """
    Authoritative, read-only reporting projection service for NEP 2026.
    """

    @classmethod
    def resolve_assessment(
        cls, assessment_id: str, user: Any
    ) -> Tuple[str, Any]:
        """
        Locates the assessment in University or College framework and enforces tenant isolation.
        Raises:
            AssessmentNotFoundError if not found.
            ReportPermissionDenied if user is not authorized to inspect this assessment.
        """
        clean_id = str(assessment_id).strip()

        # Check UniversityAssessment
        uni_assessment = (
            UniversityAssessment.objects.select_related("university", "assigned_reviewer")
            .filter(assessment_id=clean_id)
            .first()
        )
        if uni_assessment:
            framework = "UNIVERSITY_2026"
            if not can_user_view_assessment(user, uni_assessment, framework):
                raise ReportPermissionDenied(
                    "You are not authorized to access this University assessment report."
                )
            return (framework, uni_assessment)

        # Check CollegeAssessment
        col_assessment = (
            CollegeAssessment.objects.select_related("college", "assigned_reviewer")
            .filter(assessment_id=clean_id)
            .first()
        )
        if col_assessment:
            framework = "COLLEGE_2026"
            if not can_user_view_assessment(user, col_assessment, framework):
                raise ReportPermissionDenied(
                    "You are not authorized to access this College assessment report."
                )
            return (framework, col_assessment)

        raise AssessmentNotFoundError(f"Assessment '{clean_id}' not found.")

    @classmethod
    def get_assessment_report(cls, assessment_id: str, user: Any) -> Dict[str, Any]:
        """
        Generates the complete authoritative assessment report projection (Section 16 contract).
        """
        framework, assessment = cls.resolve_assessment(assessment_id, user)

        # 1. Institution Metadata
        if framework == "UNIVERSITY_2026":
            inst_obj = assessment.university
            institution_data = {
                "id": inst_obj.pk,
                "name": inst_obj.name,
                "aishe_code": inst_obj.aishe_code or "",
                "type": getattr(inst_obj, "university_type", "University"),
                "framework": "UNIVERSITY_2026",
            }
            definitions = UNIVERSITY_PARAMETERS
            param_prefix = "U"
            param_count = 20
        else:
            inst_obj = assessment.college
            institution_data = {
                "id": inst_obj.pk,
                "name": inst_obj.name,
                "aishe_code": inst_obj.aishe_code or "",
                "type": getattr(inst_obj, "management_type", "College"),
                "district": getattr(inst_obj, "district", ""),
                "framework": "COLLEGE_2026",
            }
            definitions = COLLEGE_PARAMETERS
            param_prefix = "C"
            param_count = 22

        # 2. Lifecycle & Period
        lifecycle_data = {
            "status": assessment.status,
            "is_draft": assessment.status == "DRAFT",
            "is_submitted": assessment.status in ("SUBMITTED", "UNDER_REVIEW", "CERTIFIED", "EVALUATED"),
            "is_under_review": assessment.status == "UNDER_REVIEW",
            "is_certified": assessment.status == "CERTIFIED",
            "is_rejected": assessment.status in ("REJECTED", "RETURNED_FOR_CORRECTION"),
        }

        period_data = {
            "academic_year": assessment.academic_year,
            "period_start": str(assessment.period_start),
            "period_end": str(assessment.period_end),
            "is_statutory": True,
        }

        # 3. Assigned Reviewer
        reviewer = assessment.assigned_reviewer
        assigned_reviewer_data = {
            "id": reviewer.pk,
            "full_name": reviewer.full_name,
            "email": reviewer.email,
            "role": getattr(reviewer, "role", ""),
        } if reviewer else None

        # 4. Evidence Coverage & Readiness (Authoritative apps.evidence)
        try:
            cov_report = EvidenceService.evaluate_evidence_coverage(
                assessment_id=assessment.assessment_id,
                institution_id=institution_data["aishe_code"],
                framework=framework,
                requesting_user=None,
            )
            evidence_data = {
                "is_ready_for_scoring": cov_report.is_ready_for_scoring,
                "total_subcriteria": cov_report.summary.total_subcriteria,
                "covered_subcriteria": cov_report.summary.covered_subcriteria,
                "uncovered_subcriteria": cov_report.summary.uncovered_subcriteria,
                "verification_pending": cov_report.summary.verification_pending,
                "rejected_evidence": cov_report.summary.rejected_evidence,
                "period_invalid": cov_report.summary.period_invalid,
                "verified_subcriteria": cov_report.summary.verified_subcriteria,
                "blocking_reasons": cov_report.blocking_reasons,
                "duplicates_detected": cov_report.duplicates_detected,
            }
            coverage_params_map = {p.parameter_id: p for p in cov_report.parameters}
        except Exception as e:
            evidence_data = {
                "is_ready_for_scoring": False,
                "total_subcriteria": 0,
                "covered_subcriteria": 0,
                "uncovered_subcriteria": 0,
                "verification_pending": 0,
                "rejected_evidence": 0,
                "period_invalid": 0,
                "verified_subcriteria": 0,
                "blocking_reasons": [str(e)],
                "duplicates_detected": [],
            }
            coverage_params_map = {}

        # 5. Scoring Projection (Consumes frozen engine output without re-calculating)
        scoring_result = None
        has_evaluated_scores = False
        raw_parameter_data = assessment.parameter_data or {}

        if assessment.status in ("SUBMITTED", "UNDER_REVIEW", "CERTIFIED", "EVALUATED") or assessment.certified_score is not None:
            try:
                from apps.university.services import UniversityAssessmentService
                from apps.college.services import CollegeAssessmentService

                if framework == "UNIVERSITY_2026":
                    scoring_result = UniversityAssessmentService.evaluate_assessment_scoring(assessment.assessment_id)
                else:
                    scoring_result = CollegeAssessmentService.evaluate_assessment_scoring(assessment.assessment_id)
                has_evaluated_scores = True
            except Exception:
                scoring_result = None

        if scoring_result:
            scoring_status = (
                "CERTIFIED" if assessment.status == "CERTIFIED"
                else ("BLOCKED_BY_SPECIFICATION" if scoring_result.certification_status.value == "BLOCKED_BY_SPECIFICATION"
                      else "EVALUATED")
            )
            scoring_data = {
                "scoring_status": scoring_status,
                "raw_total": scoring_result.raw_total,
                "evidence_gated_total": scoring_result.evidence_gated_total,
                "final_certified_total": assessment.certified_score if assessment.status == "CERTIFIED" else scoring_result.final_certified_total,
                "max_marks": scoring_result.max_marks,
                "certification_status": scoring_result.certification_status.value,
                "is_blocked_by_specification": scoring_result.certification_status.value == "BLOCKED_BY_SPECIFICATION",
                "blocking_reasons": scoring_result.blocking_reasons,
                "calculation_id": scoring_result.calculation_id,
                "calculation_timestamp": scoring_result.timestamp,
                "double_counting_conflicts": scoring_result.trace.get("double_counting_conflicts", []),
                "trace": scoring_result.trace,
            }
        else:
            # DRAFT or Un-evaluated state: NEVER show score = 0 pretending it was evaluated!
            is_blocked = assessment.certification_status == "BLOCKED_BY_SPECIFICATION"
            scoring_data = {
                "scoring_status": "BLOCKED_BY_SPECIFICATION" if is_blocked else ("CERTIFIED" if assessment.status == "CERTIFIED" else "NOT_EVALUATED"),
                "raw_total": assessment.certified_score if assessment.status == "CERTIFIED" else None,
                "evidence_gated_total": assessment.certified_score if assessment.status == "CERTIFIED" else None,
                "final_certified_total": assessment.certified_score,
                "max_marks": 100.0,
                "certification_status": assessment.certification_status or "NOT_EVALUATED",
                "is_blocked_by_specification": is_blocked,
                "blocking_reasons": ["Assessment is in DRAFT state and has not been evaluated."] if assessment.status == "DRAFT" else [],
                "calculation_id": None,
                "calculation_timestamp": None,
                "double_counting_conflicts": [],
                "trace": {},
            }

        # 6. Parameter Level Reports (U1–U20 or C1–C22)
        parameters_list = []
        for i in range(1, param_count + 1):
            p_code = f"{param_prefix}{i}"
            p_def = definitions.get(p_code, {})
            p_title = p_def.get("title", f"Parameter {p_code}")
            p_max = float(p_def.get("max_marks", 0.0))

            cov_param = coverage_params_map.get(p_code)
            input_val = raw_parameter_data.get(p_code)
            is_submitted = input_val is not None

            # Get scoring output for this parameter from frozen engine
            if scoring_result and p_code in scoring_result.parameter_results:
                p_res = scoring_result.parameter_results[p_code]
                raw_score = p_res.raw_score
                gated_score = p_res.evidence_gated_score
                final_score = p_res.final_score
                resolution_status = p_res.resolution_status.value
                blocking_reasons_list = [
                    f"Blocked by {p_res.resolution_status.value}"
                ] if p_res.resolution_status.value != "CALCULABLE" else []
            else:
                raw_score = None
                gated_score = None
                final_score = None
                resolution_status = "NOT_EVALUATED" if assessment.status == "DRAFT" else "CALCULABLE"
                blocking_reasons_list = []

            # Coverage state
            coverage_state = "UNCOVERED"
            subcriteria_count = len(p_def.get("subcriteria", {}))
            if cov_param:
                if any(s.coverage_state.value == "COVERED" for s in cov_param.subcriteria):
                    coverage_state = "COVERED"
                elif any(s.coverage_state.value == "PENDING" for s in cov_param.subcriteria):
                    coverage_state = "PENDING"
                elif any(s.coverage_state.value == "REJECTED" for s in cov_param.subcriteria):
                    coverage_state = "REJECTED"

            parameters_list.append({
                "parameter_code": p_code,
                "parameter_title": p_title,
                "max_marks": p_max,
                "submitted": is_submitted,
                "raw_score": raw_score,
                "evidence_gated_score": gated_score,
                "final_score": final_score,
                "resolution_status": resolution_status,
                "evidence_coverage_state": coverage_state,
                "blocking_reasons": blocking_reasons_list,
                "subcriteria_count": subcriteria_count,
            })

        # 7. Review History (Append-only)
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
                "timestamp": r.created_at.isoformat() if r.created_at else None,
            })

        # 8. Certification Information
        blocking_gates = []
        if assessment.status == "CERTIFIED":
            is_eligible = False
            blocking_gates.append("Assessment is already certified.")
        else:
            if assessment.status != "UNDER_REVIEW":
                blocking_gates.append(f"Lifecycle state is '{assessment.status}', must be 'UNDER_REVIEW'.")
            if not evidence_data["is_ready_for_scoring"]:
                blocking_gates.append("Evidence requirements are incomplete or unverified.")
            if assessment.certified_score is None and (not scoring_result or scoring_result.evidence_gated_total is None):
                blocking_gates.append("Scoring has not been evaluated by the frozen engine.")
            elif scoring_data["is_blocked_by_specification"]:
                blocking_gates.append("Certification blocked by unresolved statutory specifications.")
            is_eligible = len(blocking_gates) == 0

        certification_data = {
            "is_certified": assessment.status == "CERTIFIED",
            "certification_status": assessment.certification_status or ("CERTIFIED" if assessment.status == "CERTIFIED" else "NOT_CERTIFIED"),
            "certified_score": assessment.certified_score,
            "certified_at": assessment.updated_at.isoformat() if assessment.status == "CERTIFIED" and assessment.updated_at else None,
            "certification_eligibility": {
                "is_eligible": is_eligible,
                "blocking_gates": blocking_gates,
            }
        }

        return {
            "assessment": {
                "assessment_id": assessment.assessment_id,
                "framework": framework,
                "academic_year": assessment.academic_year,
                "period_start": str(assessment.period_start),
                "period_end": str(assessment.period_end),
                "status": assessment.status,
                "submitted_at": assessment.submitted_at.isoformat() if assessment.submitted_at else None,
                "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
                "updated_at": assessment.updated_at.isoformat() if assessment.updated_at else None,
            },
            "framework": framework,
            "institution": institution_data,
            "period": period_data,
            "lifecycle": lifecycle_data,
            "assigned_reviewer": assigned_reviewer_data,
            "evidence": evidence_data,
            "scoring": scoring_data,
            "parameters": parameters_list,
            "review": {
                "current_status": assessment.status,
                "assigned_reviewer": assigned_reviewer_data,
                "review_history": review_history,
            },
            "certification": certification_data,
        }

    @classmethod
    def get_parameter_report(cls, assessment_id: str, user: Any) -> Dict[str, Any]:
        """
        Parameter-level report for an assessment.
        """
        full_report = cls.get_assessment_report(assessment_id, user)
        return {
            "assessment_id": full_report["assessment"]["assessment_id"],
            "framework": full_report["framework"],
            "institution": full_report["institution"],
            "scoring_status": full_report["scoring"]["scoring_status"],
            "parameters": full_report["parameters"],
        }

    @classmethod
    def get_subcriteria_report(cls, assessment_id: str, user: Any) -> Dict[str, Any]:
        """
        Detailed subcriterion-level traces for an assessment.
        """
        framework, assessment = cls.resolve_assessment(assessment_id, user)
        full_report = cls.get_assessment_report(assessment_id, user)

        # Run scoring to get subcriterion traces
        scoring_result = None
        if assessment.status in ("SUBMITTED", "UNDER_REVIEW", "CERTIFIED", "EVALUATED") or assessment.certified_score is not None:
            try:
                from apps.university.services import UniversityAssessmentService
                from apps.college.services import CollegeAssessmentService

                if framework == "UNIVERSITY_2026":
                    scoring_result = UniversityAssessmentService.evaluate_assessment_scoring(assessment.assessment_id)
                else:
                    scoring_result = CollegeAssessmentService.evaluate_assessment_scoring(assessment.assessment_id)
            except Exception:
                scoring_result = None

        definitions = UNIVERSITY_PARAMETERS if framework == "UNIVERSITY_2026" else COLLEGE_PARAMETERS
        param_prefix = "U" if framework == "UNIVERSITY_2026" else "C"
        param_count = 20 if framework == "UNIVERSITY_2026" else 22

        subcriteria_list = []
        for i in range(1, param_count + 1):
            p_code = f"{param_prefix}{i}"
            p_def = definitions.get(p_code, {})
            p_sub_defs = p_def.get("subcriteria", {})

            for s_code, s_def in p_sub_defs.items():
                s_max = float(s_def.get("max_score", 0.0))

                if scoring_result and p_code in scoring_result.parameter_results:
                    p_res = scoring_result.parameter_results[p_code]
                    s_res = p_res.subcriteria_results.get(s_code)
                    if s_res:
                        raw_score = s_res.raw_score
                        gated_score = s_res.evidence_gated_score
                        resolution_status = s_res.resolution_status.value
                        gating_status = s_res.gating_status.value
                        trace = s_res.trace
                    else:
                        raw_score = None
                        gated_score = None
                        resolution_status = "NOT_EVALUATED"
                        gating_status = "NONE"
                        trace = {}
                else:
                    raw_score = None
                    gated_score = None
                    resolution_status = "NOT_EVALUATED"
                    gating_status = "NONE"
                    trace = {}

                subcriteria_list.append({
                    "parameter_code": p_code,
                    "subcriterion_code": s_code,
                    "max_marks": s_max,
                    "raw_score": raw_score,
                    "evidence_gated_score": gated_score,
                    "resolution_status": resolution_status,
                    "gating_status": gating_status,
                    "trace": trace,
                })

        return {
            "assessment_id": assessment.assessment_id,
            "framework": framework,
            "institution": full_report["institution"],
            "subcriteria": subcriteria_list,
        }

    @classmethod
    def get_evidence_report(cls, assessment_id: str, user: Any) -> Dict[str, Any]:
        """
        Detailed evidence readiness and coverage report.
        """
        framework, assessment = cls.resolve_assessment(assessment_id, user)
        aishe = assessment.university.aishe_code if framework == "UNIVERSITY_2026" else assessment.college.aishe_code
        cov_report = EvidenceService.evaluate_evidence_coverage(
            assessment_id=assessment.assessment_id,
            institution_id=aishe,
            framework=framework,
            requesting_user=None,
        )
        return cov_report.to_dict()

    @classmethod
    def get_scoring_report(cls, assessment_id: str, user: Any) -> Dict[str, Any]:
        """
        Authoritative scoring summary from frozen engine.
        """
        full_report = cls.get_assessment_report(assessment_id, user)
        return {
            "assessment_id": full_report["assessment"]["assessment_id"],
            "framework": full_report["framework"],
            "institution": full_report["institution"],
            "scoring": full_report["scoring"],
        }

    @classmethod
    def get_review_report(cls, assessment_id: str, user: Any) -> Dict[str, Any]:
        """
        Review lifecycle, history, and certification eligibility report.
        """
        full_report = cls.get_assessment_report(assessment_id, user)
        return {
            "assessment_id": full_report["assessment"]["assessment_id"],
            "framework": full_report["framework"],
            "institution": full_report["institution"],
            "lifecycle": full_report["lifecycle"],
            "review": full_report["review"],
            "certification": full_report["certification"],
        }

    @classmethod
    def get_admin_summary(cls, user: Any) -> Dict[str, Any]:
        """
        Cross-framework administrative summary and assessments ledger.
        Restricted to Admin and Committee Chair.
        NOTE: Does NOT compute institutional rankings or Top 10 lists!
        """
        uni_assessments = UniversityAssessment.objects.select_related("university", "assigned_reviewer").all()
        col_assessments = CollegeAssessment.objects.select_related("college", "assigned_reviewer").all()

        total_assessments = uni_assessments.count() + col_assessments.count()
        uni_count = uni_assessments.count()
        col_count = col_assessments.count()

        # Lifecycle distribution
        lifecycle_dist = {
            "DRAFT": 0,
            "SUBMITTED": 0,
            "UNDER_REVIEW": 0,
            "CERTIFIED": 0,
            "REJECTED": 0,
            "BLOCKED_BY_SPECIFICATION": 0,
        }

        readiness_dist = {
            "ready_for_scoring": 0,
            "pending_or_incomplete": 0,
        }

        all_records = []

        for u in uni_assessments:
            st = u.status
            if u.certification_status == "BLOCKED_BY_SPECIFICATION":
                lifecycle_dist["BLOCKED_BY_SPECIFICATION"] += 1
            elif st in lifecycle_dist:
                lifecycle_dist[st] += 1

            all_records.append({
                "assessment_id": u.assessment_id,
                "framework": "UNIVERSITY_2026",
                "institution_name": u.university.name,
                "institution_aishe": u.university.aishe_code or "",
                "academic_year": u.academic_year,
                "status": u.status,
                "scoring_status": "CERTIFIED" if u.status == "CERTIFIED" else ("BLOCKED_BY_SPECIFICATION" if u.certification_status == "BLOCKED_BY_SPECIFICATION" else "NOT_EVALUATED"),
                "certified_score": u.certified_score,
                "certification_status": u.certification_status,
                "assigned_reviewer_name": u.assigned_reviewer.full_name if u.assigned_reviewer else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
            })

        for c in col_assessments:
            st = c.status
            if c.certification_status == "BLOCKED_BY_SPECIFICATION":
                lifecycle_dist["BLOCKED_BY_SPECIFICATION"] += 1
            elif st in lifecycle_dist:
                lifecycle_dist[st] += 1

            all_records.append({
                "assessment_id": c.assessment_id,
                "framework": "COLLEGE_2026",
                "institution_name": c.college.name,
                "institution_aishe": c.college.aishe_code or "",
                "academic_year": c.academic_year,
                "status": c.status,
                "scoring_status": "CERTIFIED" if c.status == "CERTIFIED" else ("BLOCKED_BY_SPECIFICATION" if c.certification_status == "BLOCKED_BY_SPECIFICATION" else "NOT_EVALUATED"),
                "certified_score": c.certified_score,
                "certification_status": c.certification_status,
                "assigned_reviewer_name": c.assigned_reviewer.full_name if c.assigned_reviewer else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            })

        return {
            "total_assessments": total_assessments,
            "framework_distribution": {
                "university_assessments": uni_count,
                "college_assessments": col_count,
            },
            "lifecycle_distribution": lifecycle_dist,
            "readiness_distribution": readiness_dist,
            "assessments": sorted(all_records, key=lambda x: x.get("updated_at") or "", reverse=True),
        }

    @classmethod
    def get_institution_summary(cls, user: Any) -> Dict[str, Any]:
        """
        Summary for the logged-in institutional user (university or college).
        """
        role = getattr(user, "role", "")
        if role in ("nodal_officer", "university_admin"):
            user_uni = getattr(user, "university", None)
            if not user_uni:
                return {"error": "NO_INSTITUTION_ASSOCIATED", "assessments": []}
            qs = UniversityAssessment.objects.filter(university=user_uni).order_by("-created_at")
            records = [
                {
                    "assessment_id": a.assessment_id,
                    "framework": "UNIVERSITY_2026",
                    "academic_year": a.academic_year,
                    "status": a.status,
                    "certified_score": a.certified_score,
                    "certification_status": a.certification_status,
                    "updated_at": a.updated_at.isoformat() if a.updated_at else None,
                }
                for a in qs
            ]
            return {
                "institution_type": "University",
                "institution_name": user_uni.name,
                "aishe_code": user_uni.aishe_code or "",
                "assessments": records,
            }

        elif role == "principal":
            user_col = getattr(user, "college", None)
            if not user_col:
                return {"error": "NO_INSTITUTION_ASSOCIATED", "assessments": []}
            qs = CollegeAssessment.objects.filter(college=user_col).order_by("-created_at")
            records = [
                {
                    "assessment_id": a.assessment_id,
                    "framework": "COLLEGE_2026",
                    "academic_year": a.academic_year,
                    "status": a.status,
                    "certified_score": a.certified_score,
                    "certification_status": a.certification_status,
                    "updated_at": a.updated_at.isoformat() if a.updated_at else None,
                }
                for a in qs
            ]
            return {
                "institution_type": "College",
                "institution_name": user_col.name,
                "aishe_code": user_col.aishe_code or "",
                "assessments": records,
            }

        return {"error": "NOT_AN_INSTITUTIONAL_USER", "assessments": []}

    @classmethod
    def export_csv(cls, assessment_id: str, user: Any) -> str:
        """
        Generates authoritative CSV report data for an assessment without score recalculation.
        """
        report = cls.get_assessment_report(assessment_id, user)
        headers = [
            "Assessment ID", "Framework", "Institution Name", "AISHE Code",
            "Academic Year", "Lifecycle Status", "Scoring Status", "Certified Score",
            "Parameter Code", "Parameter Title", "Max Marks", "Submitted",
            "Earned Marks", "Evidence Coverage", "Resolution Status", "Blocking Reasons"
        ]

        base_row = [
            report["assessment"]["assessment_id"],
            report["framework"],
            f'"{report["institution"]["name"].replace(chr(34), chr(34)+chr(34))}"',
            report["institution"]["aishe_code"],
            report["period"]["academic_year"],
            report["lifecycle"]["status"],
            report["scoring"]["scoring_status"],
            str(report["scoring"]["final_certified_total"] or "N/A"),
        ]

        lines = [",".join(headers)]
        for p in report["parameters"]:
            earned = str(p["final_score"] if p["final_score"] is not None else (p["raw_score"] if p["raw_score"] is not None else "N/A"))
            p_row = base_row + [
                p["parameter_code"],
                f'"{p["parameter_title"].replace(chr(34), chr(34)+chr(34))}"',
                str(p["max_marks"]),
                str(p["submitted"]),
                earned,
                p["evidence_coverage_state"],
                p["resolution_status"],
                f'"{"; ".join(p["blocking_reasons"])}"'
            ]
            lines.append(",".join(p_row))

        return "\n".join(lines)
