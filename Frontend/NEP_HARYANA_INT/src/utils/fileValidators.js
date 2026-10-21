/**
 * fileValidators.js
 * Centralized, production-grade file validation utilities for the NEP Portal.
 * Enforces strict 5 MB limit (5,242,880 bytes) on PDF uploads across all forms.
 */

export const MAX_PDF_SIZE_BYTES = 5 * 1024 * 1024; // 5,242,880 bytes strict
export const MAX_GENERAL_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB default for other formats
export const PDF_SIZE_LIMIT_ERROR_MESSAGE =
  "The PDF file must not exceed 5 MB. Please choose a smaller file.";

/**
 * Validates a file for type, genuine header signatures (%PDF-), %%EOF trailer, and size limits.
 *
 * @param {File} file - Browser File object
 * @param {Object} options
 * @param {Array<string>} [options.allowedFormats] - e.g. ['pdf', 'png', 'jpg', 'jpeg', 'webp', 'docx', 'xlsx']
 * @param {boolean} [options.isPdfOnly] - Whether this upload accepts only PDF documents
 * @returns {Promise<string|null>} - Returns null if valid, or a descriptive error message string if invalid.
 */
export async function validateUploadFile(file, { allowedFormats = ["pdf"], isPdfOnly = false } = {}) {
  if (!file) {
    return "No file selected.";
  }

  if (file.size === 0) {
    return "The selected file is empty (0 bytes). Please upload a valid document.";
  }

  const ext = (file.name.split(".").pop() || "").toLowerCase();
  const isPdf = ext === "pdf" || isPdfOnly;

  // 1. Strict Size Enforcement
  if (isPdf) {
    if (file.size > MAX_PDF_SIZE_BYTES) {
      return PDF_SIZE_LIMIT_ERROR_MESSAGE;
    }
  } else {
    if (file.size > MAX_GENERAL_FILE_SIZE_BYTES) {
      return `File exceeds maximum allowed limit of 25 MB (${(file.size / 1024 / 1024).toFixed(2)} MB).`;
    }
  }

  // 2. Extension & Format Whitelist Check
  const effectiveAllowed = allowedFormats.map((f) => f.toLowerCase());
  if (effectiveAllowed.length > 0 && !effectiveAllowed.includes(ext)) {
    return `File format '.${ext}' is not permitted. Allowed format(s): ${effectiveAllowed.map((f) => f.toUpperCase()).join(", ")}.`;
  }

  // 3. Deep Structural PDF Verification
  if (isPdf) {
    if (file.size < 20) {
      return "The file is too small to be a valid PDF document.";
    }

    try {
      // Magic Bytes Header Inspection (%PDF-)
      const headerBuffer = await file.slice(0, 5).arrayBuffer();
      const headerStr = new TextDecoder("ascii").decode(headerBuffer);
      if (!headerStr.startsWith("%PDF-")) {
        return "Invalid file content: The file does not have a genuine PDF header signature (%PDF-). Renamed non-PDF files are strictly rejected.";
      }

      // Terminal %%EOF trailer check
      const tailSize = Math.min(file.size, 1024);
      const tailBuffer = await file.slice(file.size - tailSize, file.size).arrayBuffer();
      const tailStr = new TextDecoder("ascii").decode(tailBuffer);
      if (!tailStr.includes("%%EOF")) {
        return "Malformed PDF: The document is missing a valid %%EOF termination marker.";
      }
    } catch {
      return "Unable to verify PDF file integrity. Please ensure the file is an uncorrupted PDF document.";
    }
  }

  return null;
}
