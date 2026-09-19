import { request } from "./auth";

// ─── Phase 8 Admin Control Plane (api/v1/admin/) ─────────────────────────────

/**
 * GET /api/v1/admin/review-queue/
 * Unified review queue across UNIVERSITY_2026 and COLLEGE_2026 frameworks.
 * Accessible by admin, committee, committee_chair.
 * @param {Object} params - Optional filters: framework, status, institution, academic_year,
 *                          assigned_reviewer, readiness, specification_blocked
 */
export function fetchAdminReviewQueue(params = {}) {
  const q = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))
  ).toString();
  return request(`/v1/admin/review-queue/${q ? "?" + q : ""}`);
}

/**
 * GET /api/v1/admin/assessments/<assessment_id>/inspect/
 * Read-only inspection of a single assessment (no state mutation).
 */
export function inspectAdminAssessment(assessmentId) {
  return request(`/v1/admin/assessments/${assessmentId}/inspect/`);
}

/**
 * POST /api/v1/admin/assessments/<assessment_id>/assign/
 * Assign or reassign a reviewer. Restricted to admin and committee_chair.
 * @param {string} assessmentId
 * @param {number} reviewerId - User primary key
 * @param {string} reason     - Required when reassigning; optional for first assignment
 */
export function assignAdminReviewer(assessmentId, reviewerId, reason = "") {
  return request(`/v1/admin/assessments/${assessmentId}/assign/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_id: reviewerId, reason }),
  });
}

/**
 * POST /api/v1/admin/assessments/<assessment_id>/certify/
 * Delegate certification to the domain service.
 * Restricted to committee_chair, admin, superuser.
 * Score injection is rejected server-side.
 */
export function certifyAdminAssessment(assessmentId, comments = "") {
  return request(`/v1/admin/assessments/${assessmentId}/certify/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comments }),
  });
}

/**
 * GET /api/v1/admin/authorizations/
 * List all active ReviewerAuthorization bindings. Restricted to admin.
 */
export function fetchAdminAuthorizations() {
  return request("/v1/admin/authorizations/");
}

/**
 * POST /api/v1/admin/authorizations/
 * Grant a ReviewerAuthorization to a user. Restricted to admin.
 * @param {{ user_id: number, framework: string, institution_id?: string, is_active?: boolean }} payload
 */
export function grantAdminAuthorization(payload) {
  return request("/v1/admin/authorizations/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// ─── Legacy Admin Panel (api/admin/) ─────────────────────────────────────────
// These endpoints exist in apps/admin_panel/urls.py and are still wired up.
// They serve the legacy nominations system and may return empty data
// if no nominations have been seeded.

export function fetchAdminDashboardStats() {
  return request("/admin/dashboard/stats/");
}

export function fetchAdminApplications() {
  return request("/admin/applications/");
}

export function fetchAdminInstitutions() {
  return request("/admin/institutions/");
}

export function fetchAdminAnalytics() {
  return request("/admin/analytics/");
}

export function reviewAdminNomination(collegeId, reviewData) {
  return request(`/admin/nominations/${collegeId}/review/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reviewData),
  });
}
