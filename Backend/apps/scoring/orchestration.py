"""
NEP Excellence Awards 2026 - Shared assessment scoring orchestration (College & University services).

Single source of the authoritative assessment score:

    parameter inputs + evidence + persisted reviewer adjustments
        -> NEP2026ScoringEngine (evidence_gated_total)          == authoritative_total
        -> persisted cache (certified_score / certification_status), written only by
           explicit POST/recalculation actions and never for a CERTIFIED assessment
        -> API evaluation payload (committee UI displays these numbers, no client arithmetic)
        -> certification (final_certified_total == authoritative_total, frozen in a snapshot)
"""
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from apps.scoring.domain import AssetEntity, FrameworkResult, ParameterInput, ReviewerAdjustment, SubcriterionInput
from apps.scoring.enums import CertificationStatus, GatingStatus, ResolutionStatus

CERTIFIED = "CERTIFIED"
SNAPSHOT_KEY = "_certified_scoring"
REVIEWS_KEY = "_committee_reviews"
ADJUSTMENTS_KEY = "_reviewer_adjustments"

# Parameter review states exposed to the committee UI
REVIEW_APPROVED = "APPROVED"
REVIEW_STALE = "STALE"          # approved earlier, but the backend score has changed since
REVIEW_PENDING = "PENDING"


def _enum(v: Any) -> Any:
    return v.value if hasattr(v, "value") else v


def build_parameter_inputs(
    param_data: Dict[str, Any],
    definitions: Dict[str, Dict[str, Any]],
    param_codes: List[str],
    subcrit_evidence_map: Dict[str, List[Any]],
) -> Dict[str, ParameterInput]:
    """
    Converts stored parameter_data into engine inputs.

    * raw_inputs are keyed by subcriterion (canonical schema). A flat, un-keyed payload is only attached
      when the parameter has a single subcriterion — it is never copied into several subcriteria.
    * entities carry `subcriterion_code` and are attached ONLY to that subcriterion. Entities without a
      subcriterion are attached only for single-subcriterion parameters.
    """
    params: Dict[str, ParameterInput] = {}
    for p_code in param_codes:
        p_def = definitions[p_code]
        sub_codes = list(p_def["subcriteria"])
        single = len(sub_codes) == 1
        stored = param_data.get(p_code, {}) or {}
        stored_raw = stored.get("raw_inputs")
        if stored_raw is None:
            stored_raw = {k: v for k, v in stored.items() if not k.startswith("_")}
        stored_entities = stored.get("entities", []) or []
        act_date = date.fromisoformat(stored["activity_date"]) if stored.get("activity_date") else None
        keyed = isinstance(stored_raw, dict) and any(k in p_def["subcriteria"] for k in stored_raw)

        sub_inputs: Dict[str, SubcriterionInput] = {}
        for s_code in sub_codes:
            if keyed:
                raw = stored_raw.get(s_code, {})
            elif single:
                raw = stored_raw
            else:
                raw = {}
            ents = []
            for e in stored_entities:
                target = e.get("subcriterion_code")
                if target == s_code or (target is None and single):
                    ents.append(AssetEntity(
                        entity_id=e.get("entity_id", str(uuid.uuid4())),
                        entity_type=e.get("entity_type", "PROGRAMME"),
                        identifier_key=e.get("identifier_key", ""),
                        date_of_record=date.fromisoformat(e["date_of_record"]) if e.get("date_of_record") else None,
                        title=e.get("title", ""),
                    ))
            sub_inputs[s_code] = SubcriterionInput(
                subcriterion_code=s_code,
                raw_inputs=raw if isinstance(raw, dict) else {},
                evidence_docs=subcrit_evidence_map.get(s_code, []),
                entities=ents,
                activity_date=act_date,
            )
        params[p_code] = ParameterInput(
            parameter_code=p_code,
            subcriteria_inputs=sub_inputs,
            raw_inputs=stored_raw if isinstance(stored_raw, dict) else {},
            evidence_docs=[d for s in sub_inputs.values() for d in s.evidence_docs],
        )
    return params


def load_persisted_adjustments(param_data: Dict[str, Any]) -> Optional[List[ReviewerAdjustment]]:
    persisted = (param_data or {}).get(ADJUSTMENTS_KEY, [])
    if not persisted:
        return None
    return [
        ReviewerAdjustment(
            subcriterion_code=a["subcriterion_code"],
            reviewer_id=a["reviewer_id"],
            original_score=float(a.get("original_score", 0.0)),
            adjusted_score=float(a["adjusted_score"]),
            reason=a["reason"],
        )
        for a in persisted
    ]


def persist_score_cache(model_cls: Any, assessment_id: str, result: FrameworkResult) -> bool:
    """
    Writes the authoritative total and certification status. Never touches a CERTIFIED assessment.
    Returns True when a write happened.
    """
    from django.utils import timezone

    updated = model_cls.objects.filter(assessment_id=assessment_id).exclude(status=CERTIFIED).update(
        certified_score=result.evidence_gated_total,
        certification_status=_enum(result.certification_status),
        updated_at=timezone.now(),
    )
    return bool(updated)


def refresh_persisted_score(assessment_id: str) -> None:
    """
    Recalculates and caches the authoritative total after an evidence decision so the database matches what
    the committee sees. Best-effort: runs after commit and never alters a CERTIFIED assessment.
    """
    import logging

    from apps.college.models import CollegeAssessment
    from apps.university.models import UniversityAssessment

    try:
        if CollegeAssessment.objects.filter(assessment_id=assessment_id).exclude(status=CERTIFIED).exists():
            from apps.college.services import CollegeAssessmentService
            CollegeAssessmentService.evaluate_assessment_scoring(assessment_id, persist=True)
        elif UniversityAssessment.objects.filter(assessment_id=assessment_id).exclude(status=CERTIFIED).exists():
            from apps.university.services import UniversityAssessmentService
            UniversityAssessmentService.evaluate_assessment_scoring(assessment_id, persist=True)
    except Exception:  # the live evaluation surfaces scoring errors; the cache refresh must not break decisions
        logging.getLogger(__name__).exception("Score cache refresh failed for %s", assessment_id)


def schedule_score_refresh(assessment_id: Optional[str]) -> None:
    if not assessment_id:
        return
    from django.db import transaction

    transaction.on_commit(lambda: refresh_persisted_score(assessment_id))


def parameter_review_state(review: Dict[str, Any], current_score: float) -> str:
    if not review or review.get("status") != REVIEW_APPROVED:
        return REVIEW_PENDING
    try:
        approved = float(review.get("awarded_score"))
    except (TypeError, ValueError):
        return REVIEW_STALE
    return REVIEW_APPROVED if abs(approved - float(current_score)) < 1e-9 else REVIEW_STALE


def approval_blockers(param_res: Any) -> Optional[Dict[str, str]]:
    """Reasons a committee member cannot approve a parameter's calculated score yet."""
    status = param_res.resolution_status
    if status in (ResolutionStatus.UNRESOLVED_RULE, ResolutionStatus.SOURCE_INCONSISTENCY):
        return {"code": "UNRESOLVED_SPECIFICATION", "message": "Source specification unresolved for this parameter."}
    if status == ResolutionStatus.BOUNDARY_UNRESOLVED:
        return {"code": "BOUNDARY_UNRESOLVED", "message": "Submitted value lands on a rubric boundary the source does not define (policy decision required)."}
    if status == ResolutionStatus.POLICY_UNRESOLVED:
        return {"code": "POLICY_CONFIGURATION_REQUIRED", "message": "Submitted value requires a policy decision that has not been configured."}
    if status == ResolutionStatus.INVALID_INPUT:
        return {"code": "INVALID_INPUT", "message": "Submitted value is invalid and must be corrected by the institution."}
    pending = [s for s, r in param_res.subcriteria_results.items() if r.gating_status == GatingStatus.PROVISIONAL_PENDING_VERIFICATION]
    if pending:
        return {"code": "EVIDENCE_PENDING", "message": f"Evidence pending verification for {', '.join(pending)}; verify or reject it first."}
    return None


def review_progress(param_data: Dict[str, Any], result: FrameworkResult, param_codes: List[str]) -> Dict[str, Any]:
    reviews = dict((param_data or {}).get(REVIEWS_KEY, {}))
    states = {
        code: parameter_review_state(reviews.get(code, {}), result.parameter_results[code].evidence_gated_score)
        for code in param_codes if code in result.parameter_results
    }
    approved = [c for c, s in states.items() if s == REVIEW_APPROVED]
    return {
        "states": states,
        "approved": approved,
        "stale": [c for c, s in states.items() if s == REVIEW_STALE],
        "pending": [c for c, s in states.items() if s == REVIEW_PENDING],
        "all_reviewed": len(approved) == len(param_codes),
    }


def build_certified_snapshot(result: FrameworkResult, definitions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "calculation_id": result.calculation_id,
        "timestamp": result.timestamp,
        "certified_total": result.final_certified_total,
        "raw_total": result.raw_total,
        "evidence_gated_total": result.evidence_gated_total,
        "max_marks": result.max_marks,
        "parameters": {
            code: {
                "parameter_code": code,
                "parameter_title": definitions[code].get("title", code),
                "max_marks": float(definitions[code]["max_marks"]),
                "raw_score": p.raw_score,
                "evidence_gated_score": p.evidence_gated_score,
                "final_score": p.final_score,
            }
            for code, p in result.parameter_results.items()
        },
        "policy_notices": result.trace.get("policy_notices", []),
    }


def _fmt_total(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def build_scoring_evaluation(
    *,
    assessment: Any,
    result: Optional[FrameworkResult],
    definitions: Dict[str, Dict[str, Any]],
    param_codes: List[str],
    framework_code: str,
    institution_name: str,
) -> Dict[str, Any]:
    """
    Builds the API payload the committee UI renders. Every number shown to the committee comes from here.
    For a CERTIFIED assessment the frozen certification snapshot / stored certified score is returned.
    """
    from apps.scoring.awards import get_authoritative_award_classification
    from apps.scoring.formatters import format_parameter_scoring_basis, format_subcriterion_scoring_basis
    from apps.scoring.policy import get_policy_register

    param_data = assessment.parameter_data or {}
    reviews = dict(param_data.get(REVIEWS_KEY, {}))
    is_certified = assessment.status == CERTIFIED
    snapshot = param_data.get(SNAPSHOT_KEY) if is_certified else None

    if is_certified:
        authoritative_total = float(assessment.certified_score or 0.0)
        cert_status = CERTIFIED
        score_source = "CERTIFIED_SNAPSHOT" if snapshot else "CERTIFIED_STORED_SCORE"
    else:
        authoritative_total = float(result.evidence_gated_total)
        cert_status = _enum(result.certification_status)
        score_source = "LIVE_ENGINE"

    progress = review_progress(param_data, result, param_codes) if result is not None else {
        "states": {}, "approved": [], "stale": [], "pending": list(param_codes), "all_reviewed": False}

    param_results: Dict[str, Any] = {}
    for code in param_codes:
        p_def = definitions[code]
        max_marks = float(p_def["max_marks"])
        p_res = result.parameter_results.get(code) if result is not None else None
        snap = (snapshot or {}).get("parameters", {}).get(code)
        score = float(snap["evidence_gated_score"]) if snap else (float(p_res.evidence_gated_score) if p_res else 0.0)
        review_state = REVIEW_APPROVED if is_certified else progress["states"].get(code, REVIEW_PENDING)
        blocker = approval_blockers(p_res) if (p_res is not None and not is_certified) else None

        sub_dict = {}
        if p_res is not None:
            for s_code, s_res in p_res.subcriteria_results.items():
                sub_dict[s_code] = {
                    "subcriterion_code": s_code,
                    "title": p_def["subcriteria"].get(s_code, {}).get("title", s_code),
                    "raw_score": s_res.raw_score,
                    "evidence_gated_score": s_res.evidence_gated_score,
                    "final_score": s_res.final_score,
                    "max_score": float(p_def["subcriteria"].get(s_code, {}).get("max_score", s_res.max_score)),
                    "resolution_status": _enum(s_res.resolution_status),
                    "gating_status": _enum(s_res.gating_status),
                    "scoring_basis": format_subcriterion_scoring_basis(s_res),
                    "trace": s_res.trace,
                }
        resolution = _enum(p_res.resolution_status) if p_res is not None else "CALCULABLE"
        param_results[code] = {
            "parameter_code": code,
            "parameter_title": p_def.get("title", code),
            "max_marks": max_marks,
            "raw_score": p_res.raw_score if p_res is not None else (snap or {}).get("raw_score", 0.0),
            "evidence_gated_score": score,
            "calculated_score": score,
            "final_score": p_res.final_score if p_res is not None else (snap or {}).get("final_score"),
            # Backend score for this parameter; the committee displays it verbatim.
            "awarded_score": score,
            "resolution_status": resolution,
            "is_unresolved": resolution != "CALCULABLE",
            "unresolved_reason": blocker["message"] if blocker else None,
            "approval_blocker": blocker,
            "review_status": review_state,
            "scoring_basis": format_parameter_scoring_basis(p_res) if p_res is not None else "Certified snapshot",
            "subcriteria_results": sub_dict,
            "review_info": reviews.get(code, {}),
            "policy_notices": (p_res.trace.get("policy_notices", []) if p_res is not None else []),
            "trace": p_res.trace if p_res is not None else {},
        }

    return {
        "framework": framework_code,
        "assessment_id": assessment.assessment_id,
        "institution_id": getattr(result, "institution_id", None),
        "institution_name": institution_name,
        "calculation_id": (snapshot or {}).get("calculation_id") if is_certified else result.calculation_id,
        "score_source": score_source,
        "raw_total": (snapshot or {}).get("raw_total", authoritative_total) if is_certified else result.raw_total,
        "evidence_gated_total": authoritative_total,
        "authoritative_total": authoritative_total,
        "final_certified_total": authoritative_total if is_certified else result.final_certified_total,
        # Legacy field names kept for the committee UI; all equal the authoritative backend total.
        "running_total": authoritative_total,
        "current_awarded": authoritative_total,
        "expected_total_display": f"{_fmt_total(authoritative_total)} / 100",
        "max_available": 100.0,
        "max_marks": 100.0,
        "max_marks_by_parameter": {c: float(definitions[c]["max_marks"]) for c in param_codes},
        "certification_status": cert_status,
        "is_certified": is_certified,
        "blocking_reasons": [] if is_certified else list(result.blocking_reasons),
        "parameters_reviewed_count": len(param_codes) if is_certified else len(progress["approved"]),
        "stale_parameter_reviews": [] if is_certified else progress["stale"],
        "total_parameters_count": len(param_codes),
        "all_parameters_reviewed": True if is_certified else progress["all_reviewed"],
        "parameter_reviews": reviews,
        "parameter_results": param_results,
        "award_classification": get_authoritative_award_classification(score=authoritative_total, framework=framework_code),
        "policy_notices": (snapshot or {}).get("policy_notices", []) if is_certified else result.trace.get("policy_notices", []),
        "policy_register": get_policy_register(),
        "trace": {} if (is_certified and result is None) else (result.trace if result is not None else {}),
    }


def claimed_subcriteria(param_data: Dict[str, Any], definitions: Dict[str, Dict[str, Any]], param_codes: List[str]) -> List[str]:
    """
    Subcriteria for which the institution makes a positive claim. Only these need verified documentary
    evidence for review readiness — an unclaimed subcriterion scores 0 whatever evidence exists.
    """
    from apps.scoring.inputs import normalize_subcriterion

    claimed: List[str] = []
    for code in param_codes:
        stored = (param_data or {}).get(code) or {}
        raw = stored.get("raw_inputs", {}) if isinstance(stored, dict) else {}
        subs = list(definitions[code]["subcriteria"])
        for s_code in subs:
            s_raw = raw.get(s_code) if isinstance(raw, dict) and isinstance(raw.get(s_code), dict) else (
                raw if len(subs) == 1 and isinstance(raw, dict) else {})
            if normalize_subcriterion(code, s_code, s_raw).positive_claim:
                claimed.append(s_code)
    return claimed


def validate_parameter_payload(
    parameter_code: str,
    definitions: Dict[str, Dict[str, Any]],
    raw_inputs: Any,
    entities: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Strict, schema-driven validation of an institution's parameter write (#29).
    raw_inputs must be keyed by the parameter's canonical subcriterion codes; every field is checked
    against its declared type / bounds / options; period-bound claims must carry in-period dates.
    """
    from apps.scoring.inputs import normalize_subcriterion, period_errors_for_api

    p_def = definitions[parameter_code]
    sub_codes = list(p_def["subcriteria"])
    errors: List[Dict[str, Any]] = []
    if not isinstance(raw_inputs, dict):
        return [{"parameter": parameter_code, "subcriterion": None, "field": "raw_inputs", "code": "INVALID_TYPE",
                 "message": "raw_inputs must be an object keyed by subcriterion code."}]
    for key, value in raw_inputs.items():
        if key not in p_def["subcriteria"]:
            errors.append({"parameter": parameter_code, "subcriterion": key, "field": key, "code": "UNKNOWN_SUBCRITERION",
                           "message": f"'{key}' is not a subcriterion of {parameter_code}. Valid: {sub_codes}."})
            continue
        norm = normalize_subcriterion(parameter_code, key, value, strict=True)
        for e in period_errors_for_api(norm):
            errors.append(dict(e, parameter=parameter_code, subcriterion=key))
    for i, ent in enumerate(entities or []):
        target = ent.get("subcriterion_code") if isinstance(ent, dict) else None
        if len(sub_codes) > 1 and target not in p_def["subcriteria"]:
            errors.append({"parameter": parameter_code, "subcriterion": target, "field": f"entities[{i}].subcriterion_code",
                           "code": "ENTITY_SUBCRITERION_REQUIRED",
                           "message": f"Entities of multi-subcriterion parameter {parameter_code} must name one of {sub_codes}."})
        elif target is not None and target not in p_def["subcriteria"]:
            errors.append({"parameter": parameter_code, "subcriterion": target, "field": f"entities[{i}].subcriterion_code",
                           "code": "UNKNOWN_SUBCRITERION", "message": f"'{target}' is not a subcriterion of {parameter_code}."})
    return errors


def submission_errors(param_data: Dict[str, Any], definitions: Dict[str, Dict[str, Any]], param_codes: List[str]) -> List[Dict[str, Any]]:
    """
    Validity check of the stored submission (#18): invalid values, period-bound claims without dates and
    out-of-period claims must be corrected before the assessment can be submitted.
    """
    from apps.scoring.inputs import normalize_subcriterion, period_errors_for_api

    errors: List[Dict[str, Any]] = []
    for code in param_codes:
        stored = (param_data or {}).get(code) or {}
        raw = stored.get("raw_inputs", {}) if isinstance(stored, dict) else {}
        errors.extend(validate_parameter_payload(code, definitions, raw, stored.get("entities") if isinstance(stored, dict) else None))
    return errors


def certification_gate_errors(result: FrameworkResult, param_data: Dict[str, Any], param_codes: List[str]) -> List[str]:
    """Server-side preconditions shared by complete_review and certify."""
    errors: List[str] = []
    status = _enum(result.certification_status)
    if status != _enum(CertificationStatus.FINALIZABLE):
        errors.append(f"Scoring is blocked ({status}): " + "; ".join(result.blocking_reasons))
    progress = review_progress(param_data, result, param_codes)
    if progress["pending"]:
        errors.append(f"Parameters not yet approved by the committee: {', '.join(progress['pending'])}.")
    if progress["stale"]:
        errors.append(f"Approved scores changed since approval and must be re-approved: {', '.join(progress['stale'])}.")
    return errors
