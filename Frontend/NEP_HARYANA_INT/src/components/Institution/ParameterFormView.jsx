import { useState, useEffect } from "react";
import {
  Save,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Clock,
  Circle,
  FileText,
  Upload,
  AlertTriangle,
  Info,
  Ban,
  ShieldCheck,
  Calendar,
  Layers,
} from "lucide-react";
import { StatusBadge } from "../common";
import { UNRESOLVED_SPEC_NOTICES } from "../../utils/nepTaxonomy.js";

export default function ParameterFormView({
  framework = "COLLEGE_2026",
  parameterCode = "",
  parameterDef = {},
  parameterDetail = {},
  evidenceAssociations = [],
  isReadOnly = false,
  onSaveDraft = async () => {},
  onOpenEvidenceModal = () => {},
  onPrevParam = () => {},
  onNextParam = () => {},
  isFirst = false,
  isLast = false,
}) {
  const [formData, setFormData] = useState({});
  const [isDirty, setIsDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState(null);

  // Sync initial inputs from backend
  useEffect(() => {
    const raw =
      parameterDetail?.submitted_input?.raw_inputs ||
      parameterDetail?.submitted_input ||
      {};
    setFormData(JSON.parse(JSON.stringify(raw)));
    setIsDirty(false);
    setSaveSuccess(false);
    setSaveError(null);
  }, [parameterCode, parameterDetail]);

  const subcriteria = parameterDef?.subcriteria || [];
  const mandatoryEvidence = parameterDef?.mandatoryEvidence || [];
  const maxMarks = parameterDef?.maxMarks ?? parameterDetail?.max_marks ?? 0;
  const unresolvedNotice = UNRESOLVED_SPEC_NOTICES[parameterCode];

  const handleInputChange = (subCode, fieldKey, value, type) => {
    let parsedVal = value;
    if (type === "number") {
      parsedVal = value === "" ? "" : Number(value);
    } else if (type === "checkbox") {
      parsedVal = Boolean(value);
    }
    setFormData((prev) => ({
      ...prev,
      [subCode]: {
        ...(prev[subCode] || {}),
        [fieldKey]: parsedVal,
      },
    }));
    setIsDirty(true);
    setSaveSuccess(false);
    setSaveError(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await onSaveDraft(parameterCode, formData);
      setIsDirty(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error("Draft save failed:", err);
      setSaveError(err?.message || "Failed to save parameter draft.");
    } finally {
      setSaving(false);
    }
  };

  // Determine completion of this specific parameter from current formData
  const isComplete =
    subcriteria.length > 0 &&
    subcriteria.every((sub) => {
      const subVals = formData[sub.code];
      if (!subVals || typeof subVals !== "object") return false;
      const fields = sub.fields || [];
      return (
        fields.length > 0 &&
        fields.every(
          (f) => subVals[f.key] !== undefined && subVals[f.key] !== "" && subVals[f.key] !== null
        )
      );
    });

  const hasAnyInput = Object.keys(formData).some((subCode) => {
    const vals = formData[subCode];
    return vals && Object.values(vals).some((v) => v !== "" && v !== null && v !== undefined);
  });

  return (
    <div className="space-y-6">
      {/* Parameter Header Card */}
      <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono font-extrabold text-sm px-2.5 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200">
                {parameterCode}
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 uppercase tracking-wider">
                {framework}
              </span>
              <span className="text-slate-300">•</span>
              <span className="text-xs font-bold text-slate-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full">
                Max Score: {maxMarks} pts
              </span>
            </div>

            <h2 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight">
              {parameterDef?.title || parameterDetail?.title || `Parameter ${parameterCode}`}
            </h2>

            {parameterDef?.description && (
              <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
                {parameterDef.description}
              </p>
            )}
          </div>

          {/* Current Parameter Status Badge */}
          <div className="shrink-0">
            {isComplete ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                <CheckCircle2 size={13} className="text-emerald-600" />
                <span>Input Complete</span>
              </span>
            ) : hasAnyInput ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-800 border border-blue-200">
                <Clock size={13} className="text-blue-600" />
                <span>Draft In Progress</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-600 border border-slate-200">
                <Circle size={12} className="text-slate-400" />
                <span>Not Started</span>
              </span>
            )}
          </div>
        </div>

        {/* Unresolved Specification Banner if applicable */}
        {unresolvedNotice && (
          <div className="mt-4 p-3.5 bg-purple-50/90 border border-purple-200 rounded-lg text-xs text-purple-900 flex items-start gap-3">
            <Ban size={16} className="text-purple-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-bold text-purple-950 mb-0.5">Council Notice: Statutory Clarification Pending</p>
              <p className="text-purple-800 leading-relaxed">{unresolvedNotice}</p>
            </div>
          </div>
        )}
      </div>

      {/* Save feedback banner */}
      {saveSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 size={14} className="text-emerald-600 shrink-0" />
          <span>Draft inputs saved successfully to the authoritative server.</span>
        </div>
      )}

      {saveError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center gap-2">
          <AlertTriangle size={14} className="text-red-600 shrink-0" />
          <span>{saveError}</span>
        </div>
      )}

      {/* Subcriteria Sections */}
      <div className="space-y-6">
        {subcriteria.map((sub, sIdx) => {
          const subVals = formData[sub.code] || {};
          const subAssocs = evidenceAssociations.filter(
            (a) =>
              (a.parameter_id || "").toUpperCase() === parameterCode.toUpperCase() &&
              (a.subcriterion_id || "").toUpperCase() === sub.code.toUpperCase()
          );

          return (
            <div
              key={sub.code}
              className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden"
            >
              {/* Subcriterion Card Header */}
              <div className="p-4 sm:p-5 border-b border-slate-100 bg-slate-50/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <span className="font-mono font-bold text-xs bg-slate-200 text-slate-800 px-2 py-0.5 rounded">
                    {sub.code}
                  </span>
                  <h3 className="text-sm font-bold text-slate-900 tracking-tight">
                    {sub.title}
                  </h3>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[11px] text-slate-500 font-medium">
                    Evidence Attached:{" "}
                    <strong className={subAssocs.length > 0 ? "text-purple-700" : "text-slate-600"}>
                      {subAssocs.length}
                    </strong>
                  </span>
                </div>
              </div>

              <div className="p-4 sm:p-6 space-y-5">
                {/* Form Input Fields */}
                <div>
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
                    Institutional Data Input
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {(sub.fields || []).map((f) => {
                      const val = subVals[f.key] !== undefined ? subVals[f.key] : "";

                      if (f.type === "checkbox") {
                        return (
                          <div key={f.key} className="sm:col-span-2">
                            <label className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50/70 hover:bg-slate-50 cursor-pointer transition-colors">
                              <input
                                type="checkbox"
                                checked={Boolean(val)}
                                disabled={isReadOnly}
                                onChange={(e) =>
                                  handleInputChange(sub.code, f.key, e.target.checked, "checkbox")
                                }
                                className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500 mt-0.5"
                              />
                              <div className="text-xs">
                                <span className="font-semibold text-slate-800">{f.label}</span>
                                <span className="text-red-500 font-bold ml-1">*</span>
                              </div>
                            </label>
                          </div>
                        );
                      }

                      return (
                        <div key={f.key} className="space-y-1">
                          <label className="block text-xs font-semibold text-slate-700">
                            {f.label}{" "}
                            <span className="text-red-500 font-bold">*</span>
                          </label>

                          <input
                            type={f.type === "number" ? "number" : "text"}
                            placeholder={f.placeholder || ""}
                            value={val}
                            disabled={isReadOnly}
                            onChange={(e) =>
                              handleInputChange(sub.code, f.key, e.target.value, f.type)
                            }
                            className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-500 shadow-2xs"
                          />
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Subcriterion Evidence Attachment Section */}
                <div className="pt-4 border-t border-slate-100 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                          Substantiating Documentary Evidence
                        </h4>
                        {sub.isSourceSilent && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                            Source Silent (Zero Mandatory Evidence)
                          </span>
                        )}
                        {sub.isUnresolved && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-800 border border-purple-200">
                            Council Metric Unresolved
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                        <strong>Authoritative Requirement:</strong> {sub.documentaryRequirement || "Documentary proof required as per guidelines."}
                      </p>
                    </div>

                    {!isReadOnly && !sub.isSourceSilent && !sub.isUnresolved && (
                      <button
                        type="button"
                        onClick={() => onOpenEvidenceModal(sub.code, sub.canonicalEvidenceType || mandatoryEvidence[0] || "")}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-lg text-xs font-bold transition-colors cursor-pointer shrink-0"
                      >
                        <Upload size={13} />
                        <span>Attach Evidence for {sub.code}</span>
                      </button>
                    )}
                  </div>

                  {/* Associated Evidence List */}
                  {subAssocs.length === 0 ? (
                    <div className="p-3.5 rounded-lg border border-dashed border-slate-200 bg-slate-50/50 text-center">
                      <p className="text-xs text-slate-500">
                        {sub.isSourceSilent
                          ? "This subcriterion is classified as SOURCE_SILENT under the official framework specification. No documentary proof is mandated."
                          : sub.isUnresolved
                          ? "This subcriterion has an unresolved evidence requirement in the statutory specification. Evidence intake is not active."
                          : `No documentary evidence linked to subcriterion ${sub.code} yet.`}
                      </p>
                      {sub.canonicalEvidenceType && (
                        <p className="text-[11px] text-purple-700 mt-0.5 font-medium font-mono">
                          Canonical Proof Type: {sub.canonicalEvidenceType}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {subAssocs.map((assoc) => {
                        const doc = assoc.evidence || {};

                        return (
                          <div
                            key={assoc.id || assoc.association_id}
                            className="p-3 rounded-lg border border-slate-200 bg-slate-50/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                          >
                            <div className="flex items-start gap-2.5 min-w-0">
                              <FileText size={16} className="text-purple-600 shrink-0 mt-0.5" />
                              <div className="min-w-0">
                                <p className="font-bold text-slate-900 truncate">
                                  {doc.original_filename || "Documentary Proof"}
                                </p>
                                <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-500 flex-wrap">
                                  <span className="font-mono font-semibold text-slate-700">
                                    Type: {assoc.subcriterion_evidence_type || doc.evidence_type || sub.canonicalEvidenceType || "CANONICAL_PROOF"}
                                  </span>
                                  {assoc.page_start && (
                                    <>
                                      <span>•</span>
                                      <span>Pages {assoc.page_start}–{assoc.page_end || assoc.page_start}</span>
                                    </>
                                  )}
                                  {assoc.section_identifier && (
                                    <>
                                      <span>•</span>
                                      <span className="italic">{assoc.section_identifier}</span>
                                    </>
                                  )}
                                </div>
                                {assoc.claim_description && (
                                  <p className="text-[11px] text-slate-600 mt-1 italic">
                                    "{assoc.claim_description}"
                                  </p>
                                )}
                              </div>
                            </div>

                            <div className="shrink-0 flex items-center gap-2">
                              <StatusBadge status={doc.status || "PRESENT"} size="sm" />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Sticky Bottom Action Bar */}
      <div className="sticky bottom-4 z-20 bg-white/95 backdrop-blur-md rounded-xl border border-slate-200 p-4 shadow-lg flex items-center justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={onPrevParam}
            disabled={isFirst}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
          >
            <ChevronLeft size={14} />
            <span>Previous</span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          {isDirty && (
            <span className="text-xs text-amber-700 font-semibold flex items-center gap-1">
              <Clock size={13} /> Unsaved changes
            </span>
          )}

          {!isReadOnly && (
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs disabled:opacity-50 cursor-pointer"
            >
              <Save size={13} />
              <span>{saving ? "Saving..." : "Save Draft"}</span>
            </button>
          )}

          <button
            type="button"
            onClick={onNextParam}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <span>{isLast ? "Review & Submit" : "Next Parameter"}</span>
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
