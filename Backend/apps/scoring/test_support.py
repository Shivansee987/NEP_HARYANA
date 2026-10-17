"""
Shared fixtures for tests that drive assessments through the real workflow rules.

- grant_review_scope: reviewers act only inside an explicit review scope (apps.evidence.access_policy).
- complete_parameter_data: a full, valid answer set for every parameter, so submission completeness and the
  cross-subcriterion checks pass; tests then overlay the specific values they exercise.
"""
from copy import deepcopy

from apps.scoring.field_schema import COLLEGE_FIELD_SCHEMA, UNIVERSITY_FIELD_SCHEMA

_ACTIVITY_START, _ACTIVITY_END = "2025-08-01", "2026-03-31"
# Values that keep sibling-ratio rules valid (placed <= participating, monetised <= ventures, ...).
_OVERRIDES = {
    "C9.II": {"placed_students": 150},
    "C11.II.b": {"monetized_count": 7},
    "C19.III": {"scopus_index": 0},
    "U5.B": {"placed_students": 150},
    "U8.B": {"monetized_count": 4},
    "U9.A": {"total_mous": 8, "active_mous": 7},
    "U9.B": {"activities_count": 42},
    "U16.III": {"scopus_index": 0},
}


def grant_review_scope(user, framework="ALL", institution_id="", granted_by=None):
    """Gives a committee member / chair review scope for a framework (optionally one institution)."""
    from apps.evidence.models import ReviewerAuthorization
    auth, _ = ReviewerAuthorization.objects.update_or_create(
        user=user, framework=framework, institution_id=institution_id,
        defaults={"is_active": True, "granted_by": granted_by})
    return auth


def _value(field):
    t, key = field["type"], field["key"]
    if t == "integer":
        if field.get("max_field"):
            return 185
        return 200 if any(w in key for w in ("students", "targets", "total", "learners", "programmes")) else 12
    if t == "currency":
        return 2500000
    if t == "boolean":
        return True
    if t == "enum":
        return field["options"][0]["value"]
    if t == "multi_enum":
        return [o["value"] for o in field["options"][:2]]
    if t == "text_list":
        return "Activity report 2025-26"
    if t == "date":
        return _ACTIVITY_START if key.endswith("start") else _ACTIVITY_END
    return None


def complete_raw_inputs(framework, parameter_code):
    schema = UNIVERSITY_FIELD_SCHEMA if str(framework).upper().startswith("UNIVERSITY") else COLLEGE_FIELD_SCHEMA
    out = {}
    for s_code, sub in schema[parameter_code]["subcriteria"].items():
        vals = {f["key"]: _value(f) for f in sub["fields"]}
        vals.update({k: v for k, v in _OVERRIDES.get(s_code, {}).items() if k in vals})
        out[s_code] = vals
    return out


def complete_parameter_data(framework, overrides=None):
    """parameter_data for every parameter of the framework; `overrides` = {param: {sub: {field: value}}}."""
    schema = UNIVERSITY_FIELD_SCHEMA if str(framework).upper().startswith("UNIVERSITY") else COLLEGE_FIELD_SCHEMA
    data = {}
    for p_code in schema:
        raw = complete_raw_inputs(framework, p_code)
        for s_code, fields in ((overrides or {}).get(p_code) or {}).items():
            raw.setdefault(s_code, {}).update(fields)
        data[p_code] = {"raw_inputs": raw, "entities": [], "activity_date": None}
    return data


def fill_assessment(assessment, overrides=None):
    """
    Completes the answer set: every field the test already stored is kept exactly as stored; only missing
    fields/subcriteria/parameters are filled with valid defaults. Saves and returns the assessment.
    """
    data = complete_parameter_data(assessment.framework, overrides)
    for code, stored in (assessment.parameter_data or {}).items():
        if code.startswith("_") or code not in data or not isinstance(stored, dict):
            data[code] = deepcopy(stored)
            continue
        merged = data[code]
        for s_code, fields in (stored.get("raw_inputs") or {}).items():
            if isinstance(fields, dict):
                merged["raw_inputs"].setdefault(s_code, {}).update(deepcopy(fields))
            else:
                merged["raw_inputs"][s_code] = deepcopy(fields)
        for key in ("entities", "activity_date"):
            if stored.get(key):
                merged[key] = deepcopy(stored[key])
    assessment.parameter_data = data
    assessment.save(update_fields=["parameter_data"])
    return assessment


def submit_complete(service, assessment_id, *args, **kwargs):
    """Completes the stored answers (keeping the test's own values) and submits through the real service."""
    from apps.college.models import CollegeAssessment
    from apps.university.models import UniversityAssessment
    model = UniversityAssessment if "University" in service.__name__ else CollegeAssessment
    fill_assessment(model.objects.get(assessment_id=assessment_id))
    return service.submit_assessment(assessment_id, *args, **kwargs)


def record_complete_review(assessment, reviewer, remarks="Screening committee review completed."):
    """Records the committee's 'Complete Review' for the current submission (required before certification)."""
    from apps.college.models import CollegeAssessment, CollegeReviewAction, CollegeReviewRecord
    from apps.university.models import UniversityReviewAction, UniversityReviewRecord
    if isinstance(assessment, CollegeAssessment):
        record, action = CollegeReviewRecord, CollegeReviewAction.COMPLETE_REVIEW
    else:
        record, action = UniversityReviewRecord, UniversityReviewAction.COMPLETE_REVIEW
    return record.objects.create(assessment=assessment, reviewer=reviewer, action=action,
                                 status_before=assessment.status, status_after=assessment.status, reason=remarks)


def council_decision_resolved():
    """
    Simulates the evidence taxonomy after the council's U6 / U18.3 decision (FIN-03), so tests can exercise the
    rest of the University certification path. The real taxonomy is unchanged; outside this context official
    University certification stays on hold (apps.scoring.policy_gates).
    """
    from dataclasses import replace
    from unittest import mock

    from apps.evidence.taxonomy import ContractStatus, get_subcriterion_contract
    from apps.scoring.policy_gates import PENDING_COUNCIL_DECISIONS

    held = {s for items in PENDING_COUNCIL_DECISIONS.values() for item in items for s in item["subcriteria"]}

    def resolved(framework, parameter_id, subcriterion_id):
        contract = get_subcriterion_contract(framework, parameter_id, subcriterion_id)
        if contract is not None and subcriterion_id in held:
            return replace(contract, status=ContractStatus.ACTIVE,
                           canonical_evidence_type=f"EVID_{subcriterion_id.replace('.', '_')}_COUNCIL_DECIDED")
        return contract

    return mock.patch("apps.scoring.policy_gates.get_subcriterion_contract", side_effect=resolved)
