"""
UI <-> backend input contract.

The institution form renders its fields from the canonical schema (exported to the frontend by
`manage.py export_nep_schema`). These tests fill every field exactly as the form stores it, save each parameter
through the API, submit, and score, so a key or type drift between the form and the engine fails here.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import College
from apps.college.services import CollegeAssessmentService
from apps.scoring.field_schema import COLLEGE_FIELD_SCHEMA, UNIVERSITY_FIELD_SCHEMA
from apps.scoring.rules.definitions import COLLEGE_PARAMETERS, UNIVERSITY_PARAMETERS
from apps.university.models import University
from apps.university.services import UniversityAssessmentService

User = get_user_model()

# Subcriteria whose ratio base is a field of a sibling subcriterion, e.g. C9.II placed / C9.I participating
CROSS_SUBCRITERION_RATIOS = {
    s_code
    for defs in (COLLEGE_PARAMETERS, UNIVERSITY_PARAMETERS)
    for p_def in defs.values()
    for s_code, s_def in p_def["subcriteria"].items()
    if (s_def.get("metric") or {}).get("den_from")
}


def _form_value(f, s_code):
    """A positive, valid value in the shape the form stores for this field type."""
    t = f["type"]
    if t in ("integer", "currency"):
        # Bases (fields another field is bounded by) get the largest value, bounded counts a smaller one;
        # cross-subcriterion ratios (e.g. C9.II placed / C9.I participating) use the smallest.
        if f.get("max_field"):
            return 10
        return 5 if s_code in CROSS_SUBCRITERION_RATIOS else 20
    if t == "boolean":
        return True
    if t == "enum":
        return f["options"][0]["value"]
    if t == "multi_enum":
        return [f["options"][0]["value"]]
    if t == "text_list":
        return "First entry\nSecond entry"
    if t == "date":
        return "2025-09-01" if f["key"].endswith("start") else "2026-03-31"
    raise AssertionError(f"Unhandled field type {t}")


def _form_payload(param_schema):
    return {
        s_code: {f["key"]: _form_value(f, s_code) for f in sub["fields"]}
        for s_code, sub in param_schema["subcriteria"].items()
    }


class _ContractMixin:
    schema = None
    base_url = ""

    def _save_all_and_submit(self):
        for p_code, p_schema in self.schema.items():
            resp = self.client.put(
                f"{self.base_url}/{self.assessment.assessment_id}/parameters/{p_code}/",
                {"raw_inputs": _form_payload(p_schema)},
                format="json",
            )
            self.assertEqual(resp.status_code, status.HTTP_200_OK, f"{p_code}: {getattr(resp, 'data', resp)}")
        resp = self.client.post(f"{self.base_url}/{self.assessment.assessment_id}/submit/", {}, format="json")
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), getattr(resp, "data", resp))

    def _assert_scored_without_input_errors(self, evaluation):
        for p_code, p_res in evaluation["parameter_results"].items():
            for s_code, s_res in p_res["subcriteria_results"].items():
                errors = (s_res.get("trace") or {}).get("validation_errors") or []
                self.assertEqual(errors, [], f"{s_code} rejected form input: {errors}")
        self.assertGreater(evaluation["raw_total"], 0.0)


class CollegeUISchemaContractTests(_ContractMixin, TestCase):
    schema = COLLEGE_FIELD_SCHEMA
    base_url = "/api/college/assessments"

    def setUp(self):
        self.client = APIClient()
        college = College.objects.create(name="Contract Test College", aishe_code="C-CONTRACT")
        user = User.objects.create_user(
            email="principal.contract@haryana.gov.in", full_name="Principal", role="principal",
            college=college, password="ContractTest2026!",
        )
        self.assessment = CollegeAssessmentService.create_assessment(college_id=college.pk, created_by=user)
        self.client.force_authenticate(user=user)

    def test_every_form_field_is_accepted_submitted_and_scored(self):
        self._save_all_and_submit()
        evaluation = CollegeAssessmentService.get_assessment_scoring_evaluation(self.assessment.assessment_id)
        self._assert_scored_without_input_errors(evaluation)

    def test_submission_rejects_count_exceeding_sibling_base(self):
        """C9.II placed students cannot exceed C9.I participating students; caught at submission, not scored as 0."""
        for p_code, p_schema in self.schema.items():
            payload = _form_payload(p_schema)
            if p_code == "C9":
                payload["C9.II"]["placed_students"] = 50
            resp = self.client.put(
                f"{self.base_url}/{self.assessment.assessment_id}/parameters/{p_code}/",
                {"raw_inputs": payload}, format="json",
            )
            self.assertEqual(resp.status_code, status.HTTP_200_OK, p_code)
        resp = self.client.post(f"{self.base_url}/{self.assessment.assessment_id}/submit/", {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("C9.I", str(resp.data))


class UniversityUISchemaContractTests(_ContractMixin, TestCase):
    schema = UNIVERSITY_FIELD_SCHEMA
    base_url = "/api/university-assessments"

    def setUp(self):
        self.client = APIClient()
        uni = University.objects.create(name="Contract Test University", aishe_code="U-CONTRACT", state="Haryana")
        user = User.objects.create_user(
            email="nodal.contract@haryana.gov.in", full_name="Nodal", role="nodal_officer",
            university=uni, password="ContractTest2026!",
        )
        self.assessment = UniversityAssessmentService.create_assessment(
            university_id=uni.id, academic_year="2025-26", created_by=user,
        )
        self.client.force_authenticate(user=user)

    def test_every_form_field_is_accepted_submitted_and_scored(self):
        self._save_all_and_submit()
        evaluation = UniversityAssessmentService.get_assessment_scoring_evaluation(self.assessment.assessment_id)
        self._assert_scored_without_input_errors(evaluation)
