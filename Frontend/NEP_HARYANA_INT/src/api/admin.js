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

/**
 * GET /api/v1/admin/institutions/
 * State Admin overview: every University and College with its latest assessment stage, score and reviewer,
 * state totals, committee workload and recent audit activity. Read-only; restricted to admin.
 */
export function fetchStateInstitutions() {
  return request("/v1/admin/institutions/");
}

// ─── Centralized User Management & Role Governance (api/v1/admin/users/) ───

/**
 * GET /api/v1/admin/users/
 * List and search users across the platform with filters.
 */
export function fetchAdminUsers(params = {}) {
  const q = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))
  ).toString();
  return request(`/v1/admin/users/${q ? "?" + q : ""}`);
}

/**
 * GET /api/v1/admin/users/<user_id>/
 * Retrieve user details, institution, and recent audit trail.
 */
export function fetchAdminUserDetail(userId) {
  return request(`/v1/admin/users/${userId}/`);
}

/**
 * POST /api/v1/admin/users/
 * Create or invite authorized user. Restricted to Head Admin for privileged roles.
 */
export function createAdminUser(payload) {
  return request("/v1/admin/users/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/**
 * PATCH /api/v1/admin/users/<user_id>/
 * Update user profile, role, or active status with Head Admin checks.
 */
export function updateAdminUser(userId, payload) {
  return request(`/v1/admin/users/${userId}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/**
 * DELETE /api/v1/admin/users/<user_id>/
 * Permanently remove user account. Restricted strictly to Head Administrator.
 */
export function deleteAdminUser(userId) {
  return request(`/v1/admin/users/${userId}/`, {
    method: "DELETE",
  });
}

/**
 * GET /api/v1/admin/users/<user_id>/audit/
 * Retrieve append-only audit trail for a specific user.
 */
export function fetchAdminUserAuditLogs(userId) {
  return request(`/v1/admin/users/${userId}/audit/`);
}

/**
 * GET /api/v1/admin/control-centre/summary/
 * Comprehensive governance, operational exceptions, and staffing metrics for the Head Admin Control Centre.
 */
export function fetchAdminControlCentreSummary() {
  return request("/v1/admin/control-centre/summary/");
}

/**
 * GET /api/v1/admin/users/audit-trail/
 * Retrieve global append-only user audit trail across all privileged actions.
 * Restricted strictly to Head Administrator.
 * @param {Object} params - Optional filters: action, search, target_role, page, page_size
 */
export function fetchGlobalUserAuditLogs(params = {}) {
  const q = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))
  ).toString();
  return request(`/v1/admin/users/audit-trail/${q ? "?" + q : ""}`);
}

/**
 * POST /api/v1/admin/users/<user_id>/reset-password/
 * Securely reset a user's password. Restricted strictly to Head Administrator.
 */
export function resetAdminUserPassword(userId, newPassword = null) {
  const payload = newPassword ? { password: newPassword } : {};
  return request(`/v1/admin/users/${userId}/reset-password/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/**
 * POST /api/v1/admin/users/<user_id>/committee/
 * Assign or remove committee framework authorization for a user.
 */
export function manageAdminUserCommittee(userId, { framework, action = "assign", institution_id = "" }) {
  return request(`/v1/admin/users/${userId}/committee/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ framework, action, institution_id }),
  });
}

/**
 * POST /api/v1/admin/users/<user_id>/resend-invitation/
 * Resend activation invitation with fresh single-use token.
 */
export function resendAdminUserInvitation(userId) {
  return request(`/v1/admin/users/${userId}/resend-invitation/`, {
    method: "POST",
  });
}

/**
 * POST /api/v1/admin/users/<user_id>/revoke-invitation/
 * Revoke pending activation invitation tokens.
 */
export function revokeAdminUserInvitation(userId) {
  return request(`/v1/admin/users/${userId}/revoke-invitation/`, {
    method: "POST",
  });
}

// ─── Formal Committee Management (api/v1/admin/committees/) ─────────────────

/**
 * GET /api/v1/admin/committees/
 * List committees with filters (framework, committee_type, is_active, search).
 */
export function fetchAdminCommittees(params = {}) {
  const q = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))
  ).toString();
  return request(`/v1/admin/committees/${q ? "?" + q : ""}`);
}

/**
 * GET /api/v1/admin/committees/<committee_id>/
 * Retrieve detailed committee record with members and chair.
 */
export function fetchAdminCommitteeDetail(committeeId) {
  return request(`/v1/admin/committees/${committeeId}/`);
}

/**
 * POST /api/v1/admin/committees/
 * Create a new committee.
 */
export function createAdminCommittee(payload) {
  return request("/v1/admin/committees/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/**
 * PATCH /api/v1/admin/committees/<committee_id>/
 * Update committee name, description, or active status.
 */
export function updateAdminCommittee(committeeId, payload) {
  return request(`/v1/admin/committees/${committeeId}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/**
 * POST /api/v1/admin/committees/<committee_id>/chair/
 * Assign or replace committee chair.
 */
export function assignAdminCommitteeChair(committeeId, chairId) {
  return request(`/v1/admin/committees/${committeeId}/chair/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chair_id: chairId }),
  });
}

/**
 * POST /api/v1/admin/committees/<committee_id>/members/
 * Add an authorized member to the committee.
 */
export function addAdminCommitteeMember(committeeId, payload) {
  return request(`/v1/admin/committees/${committeeId}/members/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/**
 * DELETE /api/v1/admin/committees/<committee_id>/members/<user_id>/
 * Remove a member from the committee.
 */
export function removeAdminCommitteeMember(committeeId, userId) {
  return request(`/v1/admin/committees/${committeeId}/members/${userId}/`, {
    method: "DELETE",
  });
}




