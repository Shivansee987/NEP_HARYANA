import { request } from "./auth";

/**
 * NEP Excellence Awards 2026 — University Institutional API Client (Phase 6B)
 *
 * All endpoints interact strictly with the University domain API (/api/v1/university/).
 * They DO NOT touch the Admin Control Plane (/api/v1/admin/) and adhere to
 * strict institutional tenant isolation enforced by the backend.
 */

/**
 * Fetch the authenticated user's university institution record.
 * GET /api/v1/university/universities/
 * Backend filters automatically based on user's university association.
 */
export async function fetchMyUniversities() {
  return request("/v1/university/universities/");
}

/**
 * Fetch a specific university record by ID or AISHE code.
 * GET /api/v1/university/universities/<id>/
 */
export async function fetchUniversityDetail(id) {
  return request(`/v1/university/universities/${id}/`);
}

/**
 * Fetch assessments belonging to a university.
 * GET /api/v1/university/universities/<universityId>/assessments/
 */
export async function fetchUniversityAssessments(universityId) {
  return request(`/v1/university/universities/${universityId}/assessments/`);
}

/**
 * Create a new assessment session for a university.
 * POST /api/v1/university/universities/<universityId>/assessments/
 * Restricted to institutional roles (nodal_officer, university_admin).
 */
export async function createUniversityAssessment(universityId, data = {}) {
  return request(`/v1/university/universities/${universityId}/assessments/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      academic_year: data.academic_year || "2025-26",
    }),
  });
}

/**
 * Fetch detailed state of a single UniversityAssessment.
 * GET /api/v1/university/university-assessments/<assessmentId>/
 */
export async function fetchUniversityAssessmentDetail(assessmentId) {
  return request(`/v1/university/university-assessments/${assessmentId}/`);
}

/**
 * Fetch all 20 parameters (U1–U20) metadata and submitted inputs for an assessment.
 * GET /api/v1/university/university-assessments/<assessmentId>/parameters/
 */
export async function fetchUniversityAssessmentParameters(assessmentId) {
  return request(`/v1/university/university-assessments/${assessmentId}/parameters/`);
}

/**
 * Fetch evidence readiness summary for an assessment.
 * GET /api/v1/university/university-assessments/<assessmentId>/readiness/
 */
export async function fetchUniversityAssessmentReadiness(assessmentId) {
  return request(`/v1/university/university-assessments/${assessmentId}/readiness/`);
}

export async function fetchUniversityAssessmentParameterDetail(assessmentId, parameterCode) {
  return request(`/v1/university/university-assessments/${assessmentId}/parameters/${parameterCode}/`);
}

/**
 * Update raw parameter input for a university assessment parameter (U1–U20).
 * PUT /api/v1/university/university-assessments/<assessmentId>/parameters/<parameterCode>/
 */
export async function updateUniversityAssessmentParameter(assessmentId, parameterCode, data) {
  return request(`/v1/university/university-assessments/${assessmentId}/parameters/${parameterCode}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

/**
 * Submit assessment formally to screening committee.
 * POST /api/v1/university/university-assessments/<assessmentId>/submit/
 */
export async function submitUniversityAssessment(assessmentId) {
  return request(`/v1/university/university-assessments/${assessmentId}/submit/`, {
    method: "POST",
  });
}
