import { request, getAccessToken } from "./auth.js";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  `http://${window.location.hostname}:8000/api`
).replace(/\/$/, "");

/**
 * Fetch binary document with authenticated JWT header.
 * Returns a Blob object suitable for URL.createObjectURL.
 */
export async function requestBlob(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const accessToken = getAccessToken();
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = `Document request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      errorMsg = errorJson.detail || errorJson.error || errorMsg;
    } catch {
      // Non-JSON response
    }
    const err = new Error(errorMsg);
    err.status = response.status;
    throw err;
  }

  return response.blob();
}

/**
 * Unified Modern Review Queue
 * GET /api/v1/admin/review-queue/
 * Supports filtering by framework (UNIVERSITY_2026, COLLEGE_2026), status, search query.
 */
export function fetchReviewQueue(params = {}) {
  const q = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))
  ).toString();
  return request(`/v1/admin/review-queue/${q ? "?" + q : ""}`);
}

/**
 * Assessment Inspection & Review Detail
 * GET /api/v1/admin/assessments/<assessment_id>/inspect/
 * Returns complete assessment context, parameter_data, evidence_associations, coverage, and review_history.
 */
export function fetchAssessmentReviewDetail(assessmentId) {
  return request(`/v1/admin/assessments/${assessmentId}/inspect/`);
}

/**
 * Fetch a specific evidence association detail
 * GET /api/evidence/associations/<id>/
 */
export function fetchAssociationDetail(associationId) {
  return request(`/evidence/associations/${associationId}/`);
}

/**
 * Verify a specific evidence association independently
 * POST /api/evidence/associations/<id>/verify/
 */
export function verifyEvidenceAssociation(associationId, { reason = "", metadata = {} } = {}) {
  return request(`/evidence/associations/${associationId}/verify/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason, metadata }),
  });
}

/**
 * Reject a specific evidence association independently with mandatory reason and rejection code
 * POST /api/evidence/associations/<id>/reject/
 */
export function rejectEvidenceAssociation(associationId, { reason, rejection_code = "OTHER", metadata = {} }) {
  return request(`/evidence/associations/${associationId}/reject/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason, rejection_code, metadata }),
  });
}

/**
 * Fetch immutable verification audit history for an association
 * GET /api/evidence/associations/<id>/history/
 */
export function fetchAssociationHistory(associationId) {
  return request(`/evidence/associations/${associationId}/history/`);
}

/**
 * Fetch secure document blob for an evidence association
 * GET /api/evidence/associations/<id>/document/
 */
export function fetchAssociationDocumentBlob(associationId) {
  return requestBlob(`/evidence/associations/${associationId}/document/`);
}

/**
 * Fetch secure document blob for an evidence document ID directly
 * GET /api/evidence/<id>/document/
 */
export function fetchDocumentBlob(evidenceDocId) {
  return requestBlob(`/evidence/${evidenceDocId}/document/`);
}

/**
 * Begins committee review on a submitted assessment
 * Transitions SUBMITTED -> UNDER_REVIEW
 */
export function startAssessmentReview(framework, assessmentId, comments = "") {
  const isCollege = String(framework).toUpperCase().includes("COLLEGE");
  const path = isCollege
    ? `/v1/college/college-assessments/${assessmentId}/start-review/`
    : `/v1/university/university-assessments/${assessmentId}/start-review/`;

  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comments }),
  });
}

/**
 * Completes committee review on an assessment
 * Validates readiness and transitions to CERTIFICATION_PENDING
 */
export function completeAssessmentReview(framework, assessmentId, remarks = "") {
  const isCollege = String(framework).toUpperCase().includes("COLLEGE");
  const path = isCollege
    ? `/v1/college/college-assessments/${assessmentId}/complete-review/`
    : `/v1/university/university-assessments/${assessmentId}/complete-review/`;

  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ remarks }),
  });
}
