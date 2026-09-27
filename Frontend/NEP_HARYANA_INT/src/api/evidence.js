import { request } from "./auth.js";

/**
 * Upload an evidence file through the Phase 5B evidence pipeline.
 * POST /api/evidence/
 * @param {FormData} formData
 */
export async function uploadEvidenceDocument(formData) {
  return request("/evidence/", {
    method: "POST",
    body: formData,
  });
}

/**
 * Fetch evidence documents for a given assessment.
 * GET /api/evidence/?assessment_id=<assessmentId>
 */
export async function fetchAssessmentEvidenceDocuments(assessmentId) {
  return request(`/evidence/?assessment_id=${encodeURIComponent(assessmentId)}`);
}

/**
 * Fetch all subcriterion evidence associations for an assessment.
 * GET /api/evidence/associations/?assessment_id=<assessmentId>
 */
export async function fetchAssessmentEvidenceAssociations(assessmentId) {
  return request(`/evidence/associations/?assessment_id=${encodeURIComponent(assessmentId)}`);
}

/**
 * Explicitly associate an existing evidence document with a subcriterion.
 * POST /api/evidence/<documentId>/associate/
 */
export async function associateEvidenceToSubcriterion(documentId, data) {
  return request(`/evidence/${documentId}/associate/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
