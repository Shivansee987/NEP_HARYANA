import { request, getAccessToken } from "./auth";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  `http://${window.location.hostname}:8000/api`
).replace(/\/$/, "");

/**
 * Phase 9 — NEP Excellence Awards 2026 Reports & Analytics API Client
 * Strictly read-only projections. Zero client-side score calculations.
 */

/**
 * GET /api/v1/reports/admin/summary/
 * Cross-framework administrative analytics summary.
 * Restricted to Admin and Committee Chair.
 */
export function fetchAdminReportingSummary() {
  return request("/v1/reports/admin/summary/");
}

/**
 * GET /api/v1/reports/institution/summary/
 * Summary of assessments for the logged-in university or college user.
 */
export function fetchInstitutionReportingSummary() {
  return request("/v1/reports/institution/summary/");
}

/**
 * GET /api/v1/reports/assessments/<assessment_id>/
 * Comprehensive authoritative assessment report projection.
 */
export function fetchAssessmentReport(assessmentId) {
  return request(`/v1/reports/assessments/${assessmentId}/`);
}

/**
 * GET /api/v1/reports/assessments/<assessment_id>/parameters/
 * Statutory parameter report (U1–U20 or C1–C22).
 */
export function fetchAssessmentParametersReport(assessmentId) {
  return request(`/v1/reports/assessments/${assessmentId}/parameters/`);
}

/**
 * GET /api/v1/reports/assessments/<assessment_id>/subcriteria/
 * Subcriterion-level traces from the frozen scoring engine and evidence evaluator.
 */
export function fetchAssessmentSubcriteriaReport(assessmentId) {
  return request(`/v1/reports/assessments/${assessmentId}/subcriteria/`);
}

/**
 * GET /api/v1/reports/assessments/<assessment_id>/evidence-readiness/
 * Structured evidence coverage and readiness blockers.
 */
export function fetchAssessmentEvidenceReport(assessmentId) {
  return request(`/v1/reports/assessments/${assessmentId}/evidence-readiness/`);
}

/**
 * GET /api/v1/reports/assessments/<assessment_id>/scoring/
 * Authoritative scoring evaluation output from frozen engine.
 */
export function fetchAssessmentScoringReport(assessmentId) {
  return request(`/v1/reports/assessments/${assessmentId}/scoring/`);
}

/**
 * GET /api/v1/reports/assessments/<assessment_id>/review/
 * Append-only review history and certification eligibility gates.
 */
export function fetchAssessmentReviewReport(assessmentId) {
  return request(`/v1/reports/assessments/${assessmentId}/review/`);
}

/**
 * Download authoritative CSV export for an assessment.
 */
export async function downloadAssessmentReportCSV(assessmentId) {
  const token = getAccessToken();
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/v1/reports/assessments/${assessmentId}/export/`, {
    headers,
  });

  if (!response.ok) {
    throw new Error(`Failed to export report: ${response.statusText}`);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `NEP_2026_Report_${assessmentId}.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}
