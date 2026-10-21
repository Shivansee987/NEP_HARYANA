import { useState, useEffect, useMemo } from "react";
import {
  X,
  Upload,
  FileText,
  AlertCircle,
  CheckCircle2,
  Info,
  ShieldAlert,
  Plus,
  Trash2,
  FileCheck,
  Loader2,
} from "lucide-react";
import { uploadEvidenceDocument, associateEvidenceToSubcriterion } from "../../api/evidence";
import { getSubcriterionContract } from "../../utils/nepTaxonomy";

/**
 * Parses documentary requirement text to determine how many and which documents are specified.
 */
function parseDocumentaryRequirement(reqText) {
  if (!reqText || typeof reqText !== "string") {
    return {
      items: [],
      count: 1,
      countText: "1 documentary proof required",
    };
  }

  const clean = reqText.trim().replace(/\.$/, "");
  const rawParts = clean
    .split(/[,;]|\b(?:and|or|as well as)\b/gi)
    .map((s) => s.trim().replace(/^[-•*]\s*/, ""))
    .filter((s) => s.length > 2 && !/^(etc|e\.g|etc\.|such as)$/i.test(s));

  // Deduplicate while preserving order and casing
  const seen = new Set();
  const items = [];
  rawParts.forEach((part) => {
    const formatted = part.charAt(0).toUpperCase() + part.slice(1);
    const lower = formatted.toLowerCase();
    if (!seen.has(lower)) {
      seen.add(lower);
      items.push(formatted);
    }
  });

  const count = items.length > 0 ? items.length : 1;
  const countText =
    count > 1
      ? `${count} documents specified in mandate (Minimum 1 required; upload additional as needed)`
      : "1 statutory document required";

  return { items, count, countText };
}

/**
 * Returns strictly the documents required for this specific parameter / subcriterion.
 * Does not pollute the dropdown with generic document types from other parameters.
 */
function getDocumentTypeOptions(contract, documentaryRequirement) {
  const { items } = parseDocumentaryRequirement(documentaryRequirement);

  // If specific statutory items exist for this parameter, return strictly those items
  if (items && items.length > 0) {
    return items;
  }

  // If requirement text is a single undivided description
  if (
    documentaryRequirement &&
    typeof documentaryRequirement === "string" &&
    documentaryRequirement.trim()
  ) {
    return [documentaryRequirement.trim().replace(/\.$/, "")];
  }

  // Canonical contract fallback only when requirement text is absent
  if (contract?.canonicalEvidenceType) {
    const humanized = contract.canonicalEvidenceType
      .replace(/^EVID_[A-Z0-9]+_/, "")
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(" ");
    return [humanized];
  }

  return ["Statutory Documentary Proof"];
}

export default function EvidenceUploadModal({
  isOpen = false,
  onClose = () => {},
  assessmentId = "",
  framework = "COLLEGE_2026",
  institutionType = "COLLEGE",
  parameterCode = "",
  subcriterionCode = "",
  subcriterionTitle = "",
  mandatoryEvidenceType = "",
  existingDocuments = [],
  onSuccess = () => {},
}) {
  const contract = getSubcriterionContract(framework, parameterCode, subcriterionCode);
  const isSourceSilent = Boolean(contract?.isSourceSilent || contract?.contractStatus === "SOURCE_SILENT");
  const isUnresolved = Boolean(contract?.isUnresolved || contract?.contractStatus === "UNRESOLVED_MISSING");

  const allowedEvidenceTypes =
    Array.isArray(contract?.allowedEvidenceTypes) && contract.allowedEvidenceTypes.length > 0
      ? contract.allowedEvidenceTypes
      : contract?.canonicalEvidenceType
      ? [contract.canonicalEvidenceType]
      : mandatoryEvidenceType
      ? [mandatoryEvidenceType]
      : [];

  const defaultEvidenceType =
    contract?.canonicalEvidenceType || allowedEvidenceTypes[0] || mandatoryEvidenceType || "";
  const documentaryReq = contract?.documentaryRequirement || "";

  const { items: requirementItems, count: requiredCount, countText } = useMemo(
    () => parseDocumentaryRequirement(documentaryReq),
    [documentaryReq]
  );

  const docOptions = useMemo(
    () => getDocumentTypeOptions(contract, documentaryReq),
    [contract, documentaryReq]
  );

  const defaultAcademicYear = contract?.evidenceAcademicYear || "2025-26";

  const allowedFormats = useMemo(() => {
    if (Array.isArray(contract?.allowedFileFormats) && contract.allowedFileFormats.length > 0) {
      return contract.allowedFileFormats.map((f) => f.toLowerCase());
    }
    return ["pdf", "png", "jpg", "jpeg", "webp", "docx", "xlsx"];
  }, [contract]);

  const isPdfOnly = allowedFormats.length === 1 && allowedFormats[0] === "pdf";

  const [activeTab, setActiveTab] = useState("upload"); // 'upload' | 'existing'

  // Multi-document state: each entry represents a document to be uploaded
  const [documents, setDocuments] = useState([
    {
      id: 1,
      file: null,
      docType: docOptions[0] || "Supporting Documentary Evidence",
    },
  ]);

  // Existing document selection
  const [selectedDocId, setSelectedDocId] = useState("");
  const [existingDocType, setExistingDocType] = useState(docOptions[0] || "");

  const [loading, setLoading] = useState(false);
  const [progressText, setProgressText] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setError(null);
      setProgressText("");
      setSelectedDocId("");
      setActiveTab("upload");
      const initialDocType = docOptions[0] || "Supporting Documentary Evidence";
      setDocuments([
        {
          id: 1,
          file: null,
          docType: initialDocType,
        },
      ]);
      setExistingDocType(initialDocType);
    }
  }, [isOpen, parameterCode, subcriterionCode, docOptions]);

  if (!isOpen) return null;

  const resolvedEvidenceType = defaultEvidenceType;
  const isBlocked = isSourceSilent || isUnresolved || !resolvedEvidenceType;

  /**
   * Validates file size, extension, and content signature for uploads.
   * Strictly enforces PDF header (%PDF-) and %%EOF termination for PDF-only criteria.
   */
  const validateFile = async (file) => {
    if (!file) {
      return "No file selected.";
    }
    if (file.size === 0) {
      return "The selected file is empty (0 bytes). Please upload a valid document.";
    }
    if (file.size > 5 * 1024 * 1024) {
      return `File exceeds maximum allowed limit of 5 MB (${(file.size / 1024 / 1024).toFixed(2)} MB).`;
    }
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    if (!allowedFormats.includes(ext)) {
      return `File format '.${ext}' is not permitted for this criterion. Allowed format(s): ${allowedFormats.map((f) => f.toUpperCase()).join(", ")}.`;
    }

    if (ext === "pdf" || isPdfOnly) {
      if (file.size < 20) {
        return "The file is too small to be a valid PDF document.";
      }
      try {
        const headerBuffer = await file.slice(0, 5).arrayBuffer();
        const headerStr = new TextDecoder("ascii").decode(headerBuffer);
        if (!headerStr.startsWith("%PDF-")) {
          return "Invalid file content: The file does not have a genuine PDF header signature (%PDF-). Renamed non-PDF files are strictly rejected.";
        }
        const tailSize = Math.min(file.size, 1024);
        const tailBuffer = await file.slice(file.size - tailSize, file.size).arrayBuffer();
        const tailStr = new TextDecoder("ascii").decode(tailBuffer);
        if (!tailStr.includes("%%EOF")) {
          return "Malformed PDF: The document is missing a valid %%EOF termination marker.";
        }
      } catch (err) {
        return "Unable to verify PDF file integrity. Please ensure the file is an uncorrupted PDF document.";
      }
    }
    return null;
  };

  // Add another document slot
  const handleAddDocument = () => {
    const nextIndex = documents.length;
    const suggestedType =
      requirementItems[nextIndex] ||
      docOptions[nextIndex % docOptions.length] ||
      docOptions[0] ||
      "Supporting Documentary Evidence";

    setDocuments((prev) => [
      ...prev,
      {
        id: Date.now() + Math.random(),
        file: null,
        docType: suggestedType,
      },
    ]);
  };

  // Remove a document slot
  const handleRemoveDocument = (idToRemove) => {
    if (documents.length <= 1) return;
    setDocuments((prev) => prev.filter((d) => d.id !== idToRemove));
  };

  // Update selected doc type for a slot
  const handleDocTypeChange = (id, newType) => {
    setDocuments((prev) =>
      prev.map((d) => (d.id === id ? { ...d, docType: newType } : d))
    );
  };

  // Update file for a slot with signature validation
  const handleDocFileChange = async (id, newFile) => {
    setError(null);
    if (!newFile) {
      setDocuments((prev) =>
        prev.map((d) => (d.id === id ? { ...d, file: null } : d))
      );
      return;
    }
    const valErr = await validateFile(newFile);
    if (valErr) {
      setError(valErr);
      setDocuments((prev) =>
        prev.map((d) => (d.id === id ? { ...d, file: null } : d))
      );
      return;
    }
    setDocuments((prev) =>
      prev.map((d) => (d.id === id ? { ...d, file: newFile } : d))
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (isSourceSilent) {
      setError(
        `Subcriterion ${subcriterionCode} is classified as SOURCE_SILENT under the official NEP 2026 framework specification. No documentary proof is mandated or accepted.`
      );
      return;
    }

    if (isUnresolved) {
      setError(
        `Subcriterion ${subcriterionCode} has an unresolved evidence contract in the official framework specification. Documentary evidence intake is not active.`
      );
      return;
    }

    if (!resolvedEvidenceType) {
      setError(`No canonical evidence type is defined for subcriterion ${subcriterionCode}.`);
      return;
    }

    setLoading(true);

    try {
      if (activeTab === "upload") {
        // Validate that each document slot has a valid file selected
        for (let i = 0; i < documents.length; i++) {
          if (!documents[i].file) {
            setError(
              `Please select a documentary file for Document #${i + 1} (${
                documents[i].docType || "Proof"
              }).`
            );
            setLoading(false);
            return;
          }
          const valErr = await validateFile(documents[i].file);
          if (valErr) {
            setError(`Document #${i + 1} (${documents[i].file.name}): ${valErr}`);
            setLoading(false);
            return;
          }
        }

        // Upload and associate each document
        for (let i = 0; i < documents.length; i++) {
          const docItem = documents[i];
          setProgressText(
            documents.length > 1
              ? `Uploading document ${i + 1} of ${documents.length}: ${docItem.docType}...`
              : "Uploading documentary proof..."
          );

          const formData = new FormData();
          formData.append("file", docItem.file);
          formData.append("assessment_id", assessmentId);
          formData.append("framework", framework);
          formData.append("institution_type", institutionType);
          formData.append("evidence_type", resolvedEvidenceType);
          formData.append("document_date", "2025-10-15");
          formData.append("academic_year", defaultAcademicYear);
          formData.append("parameter_id", parameterCode);
          formData.append("subcriterion_id", subcriterionCode);

          const uploadedDoc = await uploadEvidenceDocument(formData);
          const docId = uploadedDoc?.document_id || uploadedDoc?.id;

          if (docId) {
            try {
              await associateEvidenceToSubcriterion(docId, {
                parameter_id: parameterCode,
                subcriterion_id: subcriterionCode,
                academic_year: defaultAcademicYear,
                evidence_type: resolvedEvidenceType,
                subcriterion_evidence_type: resolvedEvidenceType,
                page_start: 1,
                page_end: 1,
                section_identifier: docItem.docType || `Document ${i + 1}`,
                claim_description: `Statutory Proof: ${docItem.docType || docItem.file.name}`,
              });
            } catch (assocErr) {
              console.warn("Association supplement note:", assocErr);
            }
          }
        }
      } else {
        // Associate existing document from repository
        if (!selectedDocId) {
          setError("Please select an existing document from the assessment repository.");
          setLoading(false);
          return;
        }

        const selectedDoc = existingDocuments.find(
          (d) => String(d.id || d.document_id) === String(selectedDocId)
        );
        if (isPdfOnly && selectedDoc) {
          const docName = (selectedDoc.original_filename || "").toLowerCase();
          const docMime = (selectedDoc.mime_type || "").toLowerCase();
          if (!docName.endsWith(".pdf") && docMime !== "application/pdf") {
            setError(
              "Invalid document selection: This criterion mandates an approved/signed PDF document only. Selected repository document is not a PDF."
            );
            setLoading(false);
            return;
          }
        }

        setProgressText("Associating document...");
        await associateEvidenceToSubcriterion(selectedDocId, {
          parameter_id: parameterCode,
          subcriterion_id: subcriterionCode,
          academic_year: defaultAcademicYear,
          evidence_type: resolvedEvidenceType,
          subcriterion_evidence_type: resolvedEvidenceType,
          page_start: 1,
          page_end: 1,
          section_identifier: existingDocType || "Statutory Proof",
          claim_description: `Statutory Proof: ${existingDocType || "Repository Document"}`,
        });
      }

      onSuccess();
      onClose();
    } catch (err) {
      console.error("Evidence upload/association failed:", err);
      setError(
        err?.message ||
          "Failed to upload or link evidence document. Please check file format and network connectivity."
      );
    } finally {
      setLoading(false);
      setProgressText("");
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-xl w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150 max-h-[92vh] flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/80 shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-xs text-[#600b0b] bg-[#600b0b]/10 border border-[#600b0b]/20 px-2.5 py-0.5 rounded-md">
                {subcriterionCode}
              </span>
              <h3 className="text-sm font-bold text-slate-900">Attach Documentary Proof</h3>
            </div>
            <p className="text-xs text-slate-500 mt-0.5 truncate max-w-md" title={subcriterionTitle}>
              {subcriterionTitle || `Proof for ${subcriterionCode}`}
            </p>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Scrollable Content */}
        <div className="overflow-y-auto p-6 space-y-4 text-xs">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 flex items-start gap-2">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          {/* Source Silent Notice */}
          {isSourceSilent && (
            <div className="p-4 bg-amber-50/90 border border-amber-200 rounded-xl flex items-start gap-3 text-xs text-amber-900">
              <Info size={18} className="text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-sm">SOURCE_SILENT Subcriterion</p>
                <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                  The authoritative NEP 2026 specification specifies <strong>zero mandatory documentary evidence</strong> for this subcriterion. Evidence upload is neither required nor accepted.
                </p>
              </div>
            </div>
          )}

          {/* Unresolved Requirement Notice */}
          {isUnresolved && (
            <div className="p-4 bg-amber-50/90 border border-amber-200 rounded-xl flex items-start gap-3 text-xs text-amber-900">
              <ShieldAlert size={18} className="text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-sm">UNRESOLVED Evidence Contract</p>
                <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                  The statutory evidence contract for <strong>{subcriterionCode}</strong> is currently pending council resolution. Upload is temporarily unavailable to preserve audit integrity.
                </p>
              </div>
            </div>
          )}

          {/* Prominent Statutory Proof Required & Documents Needed Card */}
          {!isSourceSilent && !isUnresolved && (
            <div className="bg-[#fbf7f4] border border-[#eaded2] rounded-xl p-4 space-y-3">
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-extrabold text-[#600b0b] uppercase tracking-wider flex items-center gap-1.5">
                    <FileCheck size={15} className="text-[#600b0b]" />
                    Statutory Proof Required
                  </span>
                  <span className="text-[10px] font-bold text-[#600b0b] bg-[#eaded2]/80 px-2.5 py-0.5 rounded-full border border-[#dfc9b3]">
                    NEP 2026 Mandate
                  </span>
                </div>
                <p className="text-xs font-semibold text-slate-800 mt-1.5 leading-relaxed bg-white p-2.5 rounded-lg border border-[#ebdcd0] shadow-2xs">
                  {documentaryReq || "Statutory documentary proof required under NEP 2026."}
                </p>
              </div>

              {/* Requirement Count & Items Overview */}
              <div className="pt-2 border-t border-[#ebdcd0] space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-800">Documents Needed:</span>
                  <span className="text-[11px] font-bold text-[#600b0b] bg-white px-2.5 py-0.5 rounded border border-[#ebdcd0] shadow-2xs">
                    {countText}
                  </span>
                </div>

                {requirementItems.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold text-slate-700 block">
                      Mandated Proof Documents Checklist:
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                      {requirementItems.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-1.5 text-[11px] text-slate-800 bg-white px-2.5 py-1.5 rounded-md border border-[#ebdcd0] shadow-2xs"
                        >
                          <CheckCircle2 size={13} className="text-emerald-600 shrink-0 mt-0.5" />
                          <span className="font-medium leading-snug">{item}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tab Switcher if Existing Documents Exist */}
          {!isBlocked && existingDocuments.length > 0 && (
            <div className="flex border-b border-slate-200 gap-6 text-xs font-semibold pt-1">
              <button
                type="button"
                onClick={() => setActiveTab("upload")}
                className={`pb-2.5 border-b-2 transition-colors cursor-pointer ${
                  activeTab === "upload"
                    ? "border-[#600b0b] text-[#600b0b] font-bold"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                Upload New Document{documents.length > 1 ? ` (${documents.length})` : ""}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("existing")}
                className={`pb-2.5 border-b-2 transition-colors cursor-pointer ${
                  activeTab === "existing"
                    ? "border-[#600b0b] text-[#600b0b] font-bold"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                Select Existing Document ({existingDocuments.length})
              </button>
            </div>
          )}

          {/* Form Content */}
          {!isBlocked && (
            <form id="evidence-upload-form" onSubmit={handleSubmit} className="space-y-4">
              {activeTab === "upload" ? (
                <>
                  {/* PDF Mandate Banner when criterion strictly requires PDF */}
                  {isPdfOnly && (
                    <div className="p-3 bg-blue-50/80 border border-blue-200/90 rounded-xl flex items-center gap-2.5 text-xs text-blue-900">
                      <FileCheck size={16} className="text-blue-700 shrink-0" />
                      <div>
                        <span className="font-bold">PDF Format Mandate: </span>
                        <span>This criterion accepts authentic, approved/signed PDF files only. Renamed or non-PDF files will be rejected.</span>
                      </div>
                    </div>
                  )}

                  {/* Dynamic Document Upload Cards */}
                  <div className="space-y-3">
                    {documents.map((doc, idx) => (
                      <div
                        key={doc.id}
                        className="bg-slate-50/80 border border-slate-200/90 rounded-xl p-4 space-y-3 relative group transition-all hover:border-slate-300"
                      >
                        {/* Slot Header */}
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                            <span className="w-5 h-5 rounded-full bg-[#600b0b]/10 text-[#600b0b] flex items-center justify-center text-[11px] font-extrabold">
                              {idx + 1}
                            </span>
                            Document {idx + 1}
                            {documents.length > 1 && (
                              <span className="text-[11px] text-slate-400 font-normal">
                                of {documents.length}
                              </span>
                            )}
                          </span>

                          {documents.length > 1 && (
                            <button
                              type="button"
                              onClick={() => handleRemoveDocument(doc.id)}
                              className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 px-2 py-1 rounded text-[11px] font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                              title="Remove this document slot"
                            >
                              <Trash2 size={13} />
                              <span>Remove</span>
                            </button>
                          )}
                        </div>

                        {/* Dropdown: Which document is uploaded */}
                        <div>
                          <label className="block font-bold text-slate-700 mb-1 text-xs">
                            Which document is uploaded? <span className="text-red-500">*</span>
                          </label>
                          <select
                            value={doc.docType}
                            onChange={(e) => handleDocTypeChange(doc.id, e.target.value)}
                            required
                            className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20 focus:border-[#600b0b] transition-shadow"
                          >
                            {docOptions.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* File Selector */}
                        <div>
                          <label className="block font-bold text-slate-700 mb-1 text-xs">
                            Documentary Evidence File <span className="text-red-500">*</span>
                          </label>
                          <div className="border border-dashed border-slate-300 rounded-lg p-3 text-center bg-white hover:border-[#600b0b]/60 hover:bg-[#fbf7f4]/40 transition-colors">
                            <input
                              type="file"
                              id={`evidence-file-${doc.id}`}
                              accept={isPdfOnly ? ".pdf,application/pdf" : ".pdf,.png,.jpg,.jpeg,.webp,.docx,.xlsx"}
                              onChange={(e) => {
                                if (e.target.files && e.target.files[0]) {
                                  handleDocFileChange(doc.id, e.target.files[0]);
                                }
                              }}
                              className="hidden"
                            />
                            <label
                              htmlFor={`evidence-file-${doc.id}`}
                              className="cursor-pointer block py-1"
                            >
                              {doc.file ? (
                                <div className="flex items-center justify-center gap-2 text-slate-800">
                                  <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                                  <span className="font-bold text-xs truncate max-w-xs text-slate-800">
                                    {doc.file.name}
                                  </span>
                                  <span className="text-[10px] text-slate-500 font-mono">
                                    ({(doc.file.size / 1024 / 1024).toFixed(2)} MB)
                                  </span>
                                  <span className="text-[11px] text-[#600b0b] font-bold underline ml-1 hover:text-[#4a0707]">
                                    Change
                                  </span>
                                </div>
                              ) : (
                                <div className="flex items-center justify-center gap-2 text-slate-600">
                                  <Upload size={16} className="text-[#600b0b]" />
                                  <span className="font-semibold text-xs text-slate-700">
                                    Click to choose file
                                  </span>
                                  <span className="text-[10px] text-slate-400">
                                    {isPdfOnly ? "(PDF only, up to 5MB)" : "(PDF, PNG, JPG up to 5MB)"}
                                  </span>
                                </div>
                              )}
                            </label>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Add Button to upload more than one document in Statutory Proof Required */}
                  <button
                    type="button"
                    onClick={handleAddDocument}
                    className="w-full py-2.5 px-3 border-2 border-dashed border-[#600b0b]/30 hover:border-[#600b0b] bg-[#600b0b]/5 hover:bg-[#600b0b]/10 text-[#600b0b] rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer shadow-2xs hover:shadow-xs"
                  >
                    <Plus size={15} />
                    <span>Add Another Document for Statutory Proof</span>
                  </button>
                </>
              ) : (
                /* Existing Document Tab */
                <div className="bg-slate-50/80 border border-slate-200 rounded-xl p-4 space-y-3">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1 text-xs">
                      Which document is uploaded? <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={existingDocType}
                      onChange={(e) => setExistingDocType(e.target.value)}
                      required
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20 focus:border-[#600b0b]"
                    >
                      {docOptions.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1 text-xs">
                      Select Existing Institutional Document <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={selectedDocId}
                      onChange={(e) => setSelectedDocId(e.target.value)}
                      required
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20 focus:border-[#600b0b]"
                    >
                      <option value="">-- Choose from uploaded repository --</option>
                      {existingDocuments
                        .filter(
                          (doc) =>
                            !isPdfOnly ||
                            (doc.original_filename || "").toLowerCase().endsWith(".pdf") ||
                            doc.mime_type === "application/pdf"
                        )
                        .map((doc) => (
                          <option
                            key={doc.id || doc.document_id}
                            value={doc.id || doc.document_id}
                          >
                            {doc.original_filename} (Uploaded:{" "}
                            {new Date(doc.upload_timestamp).toLocaleDateString()})
                          </option>
                        ))}
                    </select>
                  </div>
                </div>
              )}
            </form>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-end gap-3 bg-slate-50/80 shrink-0">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-xl bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-bold transition-colors cursor-pointer"
          >
            Cancel
          </button>

          {!isBlocked && (
            <button
              type="submit"
              form="evidence-upload-form"
              disabled={loading}
              className="px-5 py-2 rounded-xl bg-[#600b0b] hover:bg-[#4a0707] text-white text-xs font-bold transition-all shadow-xs hover:shadow-md disabled:opacity-50 cursor-pointer flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>{progressText || "Processing..."}</span>
                </>
              ) : activeTab === "upload" ? (
                documents.length > 1 ? (
                  `Upload & Associate All ${documents.length} Proofs`
                ) : (
                  "Upload & Associate Proof"
                )
              ) : (
                "Associate Document"
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
