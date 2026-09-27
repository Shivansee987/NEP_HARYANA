import { useState, useEffect } from "react";
import {
  X,
  Upload,
  FileText,
  AlertCircle,
  CheckCircle2,
  Calendar,
  Layers,
  BookOpen,
  Info,
  ShieldAlert,
} from "lucide-react";
import { uploadEvidenceDocument, associateEvidenceToSubcriterion } from "../../api/evidence";
import { getSubcriterionContract } from "../../utils/nepTaxonomy";

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

  const allowedEvidenceTypes = Array.isArray(contract?.allowedEvidenceTypes) && contract.allowedEvidenceTypes.length > 0
    ? contract.allowedEvidenceTypes
    : (contract?.canonicalEvidenceType ? [contract.canonicalEvidenceType] : (mandatoryEvidenceType ? [mandatoryEvidenceType] : []));

  const defaultEvidenceType = contract?.canonicalEvidenceType || allowedEvidenceTypes[0] || mandatoryEvidenceType || "";

  const [activeTab, setActiveTab] = useState("upload"); // 'upload' | 'existing'
  const [file, setFile] = useState(null);
  const [documentDate, setDocumentDate] = useState("2025-10-15");
  const [academicYear, setAcademicYear] = useState("2025-26");
  const [evidenceType, setEvidenceType] = useState(defaultEvidenceType);
  const [pageStart, setPageStart] = useState("");
  const [pageEnd, setPageEnd] = useState("");
  const [sectionIdentifier, setSectionIdentifier] = useState("");
  const [claimDescription, setClaimDescription] = useState("");

  const [selectedDocId, setSelectedDocId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setFile(null);
      setError(null);
      setPageStart("");
      setPageEnd("");
      setSectionIdentifier("");
      setClaimDescription("");
      setSelectedDocId("");
      setEvidenceType(defaultEvidenceType);
      setActiveTab("upload");
    }
  }, [isOpen, parameterCode, subcriterionCode, mandatoryEvidenceType, defaultEvidenceType]);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const resolvedEvidenceType = evidenceType || defaultEvidenceType;
  const isBlocked = isSourceSilent || isUnresolved || !resolvedEvidenceType;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    if (isSourceSilent) {
      setError(
        `Subcriterion ${subcriterionCode} is classified as SOURCE_SILENT under the official NEP 2026 framework specification. No documentary proof is mandated or accepted.`
      );
      setLoading(false);
      return;
    }

    if (isUnresolved) {
      setError(
        `Subcriterion ${subcriterionCode} has an unresolved evidence contract in the official framework specification. Documentary evidence intake is not active.`
      );
      setLoading(false);
      return;
    }

    if (!resolvedEvidenceType) {
      setError(`No canonical evidence type is defined for subcriterion ${subcriterionCode}.`);
      setLoading(false);
      return;
    }

    try {
      if (activeTab === "upload") {
        if (!file) {
          setError("Please select a valid documentary evidence file (PDF or image).");
          setLoading(false);
          return;
        }

        const formData = new FormData();
        formData.append("file", file);
        formData.append("assessment_id", assessmentId);
        formData.append("framework", framework);
        formData.append("institution_type", institutionType);
        formData.append("evidence_type", resolvedEvidenceType);
        formData.append("document_date", documentDate);
        formData.append("academic_year", academicYear);
        formData.append("parameter_id", parameterCode);
        formData.append("subcriterion_id", subcriterionCode);

        // Upload and create initial association
        const uploadedDoc = await uploadEvidenceDocument(formData);

        // If extra metadata provided (page numbers, section, claim description), update association
        const docId = uploadedDoc?.document_id || uploadedDoc?.id;
        if (
          docId &&
          (pageStart || pageEnd || sectionIdentifier || claimDescription)
        ) {
          try {
            await associateEvidenceToSubcriterion(docId, {
              parameter_id: parameterCode,
              subcriterion_id: subcriterionCode,
              academic_year: academicYear,
              evidence_type: resolvedEvidenceType,
              subcriterion_evidence_type: resolvedEvidenceType,
              page_start: pageStart ? parseInt(pageStart, 10) : null,
              page_end: pageEnd ? parseInt(pageEnd, 10) : null,
              section_identifier: sectionIdentifier,
              claim_description: claimDescription,
            });
          } catch (assocErr) {
            console.warn("Association metadata supplement note:", assocErr);
          }
        }
      } else {
        // Link existing document
        if (!selectedDocId) {
          setError("Please select an existing document from the assessment repository.");
          setLoading(false);
          return;
        }

        await associateEvidenceToSubcriterion(selectedDocId, {
          parameter_id: parameterCode,
          subcriterion_id: subcriterionCode,
          academic_year: academicYear,
          evidence_type: resolvedEvidenceType,
          subcriterion_evidence_type: resolvedEvidenceType,
          page_start: pageStart ? parseInt(pageStart, 10) : null,
          page_end: pageEnd ? parseInt(pageEnd, 10) : null,
          section_identifier: sectionIdentifier,
          claim_description: claimDescription,
        });
      }

      onSuccess();
      onClose();
    } catch (err) {
      console.error("Evidence upload/association failed:", err);
      setError(
        err?.message ||
          "Failed to upload or link evidence document. Please check file format and statutory dates."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-xs text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded">
                {subcriterionCode}
              </span>
              <h3 className="text-sm font-bold text-slate-900">Attach Documentary Proof</h3>
            </div>
            <p className="text-xs text-slate-500 mt-0.5 truncate max-w-sm" title={subcriterionTitle}>
              {subcriterionTitle || `Proof for ${subcriterionCode}`}
            </p>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Source Silent Notice */}
        {isSourceSilent && (
          <div className="px-5 py-3 bg-amber-50/90 border-b border-amber-200 flex items-start gap-2.5 text-xs text-amber-900">
            <Info size={16} className="text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">SOURCE_SILENT Subcriterion</p>
              <p className="text-[11px] text-amber-800 mt-0.5 leading-relaxed">
                The authoritative NEP 2026 specification specifies <strong>zero mandatory documentary evidence</strong> for this subcriterion. Evidence upload is neither required nor accepted.
              </p>
            </div>
          </div>
        )}

        {/* Unresolved Requirement Notice */}
        {isUnresolved && (
          <div className="px-5 py-3 bg-amber-50/90 border-b border-amber-200 flex items-start gap-2.5 text-xs text-amber-900">
            <ShieldAlert size={16} className="text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">UNRESOLVED Evidence Contract</p>
              <p className="text-[11px] text-amber-800 mt-0.5 leading-relaxed">
                The statutory evidence contract for <strong>{subcriterionCode}</strong> is currently pending council resolution. Upload is temporarily unavailable to preserve audit integrity.
              </p>
            </div>
          </div>
        )}

        {/* Authoritative Requirement Banner */}
        {!isSourceSilent && !isUnresolved && (
          <div className="px-5 py-2.5 bg-purple-50/80 border-b border-purple-100 flex items-start gap-2 text-xs text-purple-900">
            <Info size={14} className="text-purple-600 shrink-0 mt-0.5" />
            <div className="min-w-0">
              <p className="text-[11px] text-purple-800 leading-snug">
                <strong>Statutory Proof Required:</strong> {contract?.documentaryRequirement || "Statutory documentary proof under NEP 2026."}
              </p>
            </div>
          </div>
        )}

        {/* Tab Toggle if Existing Documents Exist & not blocked */}
        {!isBlocked && existingDocuments.length > 0 && (
          <div className="px-5 pt-3 border-b border-slate-100 flex gap-4 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setActiveTab("upload")}
              className={`pb-2 border-b-2 transition-colors cursor-pointer ${
                activeTab === "upload"
                  ? "border-blue-600 text-blue-700"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              Upload New Document
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("existing")}
              className={`pb-2 border-b-2 transition-colors cursor-pointer ${
                activeTab === "existing"
                  ? "border-blue-600 text-blue-700"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              Select Existing File ({existingDocuments.length})
            </button>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-start gap-2">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {isBlocked ? (
            <div className="py-6 text-center text-slate-500 space-y-2">
              <FileText size={32} className="mx-auto text-slate-300" />
              <p className="font-semibold text-slate-700">Documentary Evidence Not Applicable</p>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                {isSourceSilent
                  ? "This indicator is scored based on submitted institutional data only. No proof upload is required."
                  : "Council specification does not define an active evidence contract for this indicator."}
              </p>
            </div>
          ) : (
            <>
              {/* Canonical Evidence Type Selection / Read-Only Contract Display */}
              {allowedEvidenceTypes.length > 1 ? (
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Permitted Canonical Evidence Type <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={evidenceType || defaultEvidenceType}
                    onChange={(e) => setEvidenceType(e.target.value)}
                    required
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono text-xs font-semibold"
                  >
                    {allowedEvidenceTypes.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-slate-500 mt-1">
                    This subcriterion accepts multiple canonical evidence types specified by the council contract.
                  </p>
                </div>
              ) : (
                <div className="p-3 bg-purple-50/80 border border-purple-200 rounded-lg flex items-center justify-between text-xs">
                  <div>
                    <span className="text-[10px] font-bold text-purple-700 uppercase tracking-wider block">
                      Canonical Evidence Type
                    </span>
                    <span className="font-mono font-bold text-purple-900 text-xs">
                      {defaultEvidenceType || "CANONICAL_CONTRACT_PENDING"}
                    </span>
                  </div>
                  <span className="text-[10px] bg-purple-100 text-purple-800 font-bold px-2 py-0.5 rounded border border-purple-300">
                    NEP 2026 Contract
                  </span>
                </div>
              )}

              {activeTab === "upload" ? (
                <>
                  {/* File Selector */}
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">
                      Documentary Evidence File <span className="text-red-500">*</span>
                    </label>
                    <div className="border-2 border-dashed border-slate-200 rounded-lg p-4 text-center hover:border-blue-400 transition-colors bg-slate-50/50">
                      <input
                        type="file"
                        id="evidence-file-input"
                        accept=".pdf,.png,.jpg,.jpeg"
                        onChange={handleFileChange}
                        className="hidden"
                      />
                      <label htmlFor="evidence-file-input" className="cursor-pointer block">
                        <Upload size={20} className="mx-auto text-slate-400 mb-1" />
                        {file ? (
                          <p className="font-bold text-blue-700 truncate max-w-xs mx-auto">
                            {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                          </p>
                        ) : (
                          <>
                            <p className="font-semibold text-slate-700">Click to browse file</p>
                            <p className="text-[11px] text-slate-400 mt-0.5">
                              PDF, PNG, JPG accepted (Signed & stamped, max 25MB)
                            </p>
                          </>
                        )}
                      </label>
                    </div>
                  </div>

                  {/* Date & Academic Year Grid */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-bold text-slate-700 mb-1">
                        Document Date <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="date"
                        value={documentDate}
                        onChange={(e) => setDocumentDate(e.target.value)}
                        required
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs"
                      />
                    </div>

                    <div>
                      <label className="block font-bold text-slate-700 mb-1">Academic Year</label>
                      <input
                        type="text"
                        value={academicYear}
                        onChange={(e) => setAcademicYear(e.target.value)}
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 font-mono text-xs"
                        readOnly
                      />
                    </div>
                  </div>
                </>
              ) : (
                /* Existing Document Selector */
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Select Institutional Document <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={selectedDocId}
                    onChange={(e) => setSelectedDocId(e.target.value)}
                    required
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs"
                  >
                    <option value="">-- Choose from uploaded repository --</option>
                    {existingDocuments.map((doc) => (
                      <option key={doc.id || doc.document_id} value={doc.id || doc.document_id}>
                        {doc.original_filename} (Uploaded: {new Date(doc.upload_timestamp).toLocaleDateString()})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Subcriterion Citation Metadata: Pages, Section, Claim */}
              <div className="pt-2 border-t border-slate-100 space-y-3">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Subcriterion Citation Metadata
                </span>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-600 font-medium mb-1">Page Start</label>
                    <input
                      type="number"
                      min="1"
                      placeholder="e.g. 1"
                      value={pageStart}
                      onChange={(e) => setPageStart(e.target.value)}
                      className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-600 font-medium mb-1">Page End</label>
                    <input
                      type="number"
                      min="1"
                      placeholder="e.g. 4"
                      value={pageEnd}
                      onChange={(e) => setPageEnd(e.target.value)}
                      className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Section Identifier</label>
                  <input
                    type="text"
                    placeholder="e.g. Annexure 2, Clause 3.1"
                    value={sectionIdentifier}
                    onChange={(e) => setSectionIdentifier(e.target.value)}
                    className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Claim Description</label>
                  <textarea
                    rows={2}
                    placeholder="Brief justification stating what this document substantiates for this subcriterion..."
                    value={claimDescription}
                    onChange={(e) => setClaimDescription(e.target.value)}
                    className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>
            </>
          )}

          {/* Actions */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold cursor-pointer"
            >
              Cancel
            </button>

            {!isBlocked && (
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
              >
                {loading
                  ? "Linking Proof..."
                  : activeTab === "upload"
                  ? "Upload & Associate Proof"
                  : "Associate Document"}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
