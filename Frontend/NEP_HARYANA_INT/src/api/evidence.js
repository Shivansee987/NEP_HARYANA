import { request, API_BASE_URL, getAccessToken } from "./auth.js";

export { getAccessToken };

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

/**
 * Retrieve authenticated blob URL for an evidence document or association.
 * Uses /api/evidence/<documentId>/download/ or /api/evidence/associations/<associationId>/document/
 * @param {{ documentId?: string, associationId?: string }} params
 * @returns {Promise<string>} Blob URL created via URL.createObjectURL
 */
export async function getEvidenceDocumentBlobUrl({ documentId, associationId }) {
  const token = getAccessToken();
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let endpoint = "";
  if (documentId) {
    endpoint = `${API_BASE_URL}/evidence/${encodeURIComponent(documentId)}/download/`;
  } else if (associationId) {
    endpoint = `${API_BASE_URL}/evidence/associations/${encodeURIComponent(associationId)}/document/`;
  } else {
    throw new Error("Either documentId or associationId must be provided.");
  }

  const response = await fetch(endpoint, {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Failed to fetch document (status ${response.status})`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.error || errorDetail;
    } catch {
      // fallback to status text
    }
    throw new Error(errorDetail);
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
