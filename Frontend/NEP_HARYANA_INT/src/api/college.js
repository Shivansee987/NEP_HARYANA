import { request } from "./auth";

/**
 * NEP Excellence Awards 2026 — College Institutional API Client (Phase 7B/7C)
 *
 * All endpoints interact strictly with the College domain API (/api/v1/college/).
 * They DO NOT touch the Admin Control Plane (/api/v1/admin/) and adhere to
 * strict institutional tenant isolation enforced by the backend.
 * Scoring and evaluation remain strictly server-authoritative.
 */

/**
 * Fetch the authenticated user's college institution record.
 * GET /api/v1/college/colleges/
 */
export async function fetchMyColleges() {
  return request("/v1/college/colleges/");
}

/**
 * Fetch a specific college record by ID or AISHE code.
 * GET /api/v1/college/colleges/<id>/
 */
export async function fetchCollegeDetail(id) {
  return request(`/v1/college/colleges/${id}/`);
}

/**
 * Fetch assessments belonging to a college.
 * GET /api/v1/college/colleges/<collegeId>/assessments/
 */
export async function fetchCollegeAssessments(collegeId) {
  return request(`/v1/college/colleges/${collegeId}/assessments/`);
}

/**
 * Create a new assessment session for a college.
 * POST /api/v1/college/colleges/<collegeId>/assessments/
 * Restricted to institutional role: principal.
 */
export async function createCollegeAssessment(collegeId, data = {}) {
  return request(`/v1/college/colleges/${collegeId}/assessments/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      academic_year: data.academic_year || "2025-26",
    }),
  });
}

/**
 * Fetch detailed state of a single CollegeAssessment.
 * GET /api/v1/college/college-assessments/<assessmentId>/
 */
export async function fetchCollegeAssessmentDetail(assessmentId) {
  return request(`/v1/college/college-assessments/${assessmentId}/`);
}

/**
 * Fetch all 22 parameters (C1–C22) metadata and submitted inputs for a college assessment.
 * GET /api/v1/college/college-assessments/<assessmentId>/parameters/
 */
export async function fetchCollegeAssessmentParameters(assessmentId) {
  return request(`/v1/college/college-assessments/${assessmentId}/parameters/`);
}

/**
 * Retrieve metadata and current submitted input for a specific parameter (e.g. C1).
 * GET /api/v1/college/college-assessments/<assessmentId>/parameters/<parameterCode>/
 */
export async function fetchCollegeAssessmentParameterDetail(assessmentId, parameterCode) {
  return request(`/v1/college/college-assessments/${assessmentId}/parameters/${parameterCode}/`);
}

/**
 * Update raw parameter input for a specific parameter (C1–C22).
 * PUT /api/v1/college/college-assessments/<assessmentId>/parameters/<parameterCode>/
 */
export async function updateCollegeAssessmentParameter(assessmentId, parameterCode, data) {
  return request(`/v1/college/college-assessments/${assessmentId}/parameters/${parameterCode}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

/**
 * Fetch evidence coverage evaluation across C1–C22 subcriteria.
 * GET /api/v1/college/college-assessments/<assessmentId>/coverage/
 */
export async function fetchCollegeAssessmentCoverage(assessmentId) {
  return request(`/v1/college/college-assessments/${assessmentId}/coverage/`);
}

/**
 * Fetch evidence readiness summary for a college assessment.
 * GET /api/v1/college/college-assessments/<assessmentId>/readiness/
 */
export async function fetchCollegeAssessmentReadiness(assessmentId) {
  return request(`/v1/college/college-assessments/${assessmentId}/readiness/`);
}

/**
 * Submit college assessment formally to screening committee.
 * POST /api/v1/college/college-assessments/<assessmentId>/submit/
 */
export async function submitCollegeAssessment(assessmentId) {
  return request(`/v1/college/college-assessments/${assessmentId}/submit/`, {
    method: "POST",
  });
}
