import React from "react";
import {
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Calendar,
  Layers,
  Sparkles,
} from "lucide-react";
import {
  COLLEGE_FRAMEWORK_DATA,
  UNIVERSITY_FRAMEWORK_DATA,
  getSubcriterionTitle,
} from "../../utils/nepTaxonomy";

/**
 * Format timestamp nicely (e.g., "27 Sep 2026, 7:03 PM")
 */
function formatHumanTimestamp(dateStr) {
  if (!dateStr) return null;
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return String(dateStr);
    return d.toLocaleString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return String(dateStr);
  }
}

/**
 * Clean field key into readable label if definition is missing
 */
function humanizeKey(key) {
  if (!key) return "";
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/2024 25/g, "(2024–25)")
    .replace(/2025 26/g, "(2025–26)")
    .replace(/2023 24/g, "(2023–24)");
}

/**
 * Render single value cleanly
 */
function renderCleanValue(val, fieldType) {
  if (val === null || val === undefined || val === "") {
    return <span className="text-slate-400 font-medium italic">Not provided</span>;
  }

  if (typeof val === "boolean" || fieldType === "checkbox") {
    const isTrue = Boolean(val);
    return (
      <span
        className={`inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-md border ${
          isTrue
            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
            : "bg-slate-100 text-slate-600 border-slate-200"
        }`}
      >
        {isTrue ? (
          <>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>Yes / Compliant & Certified</span>
          </>
        ) : (
          <span>No / Not Applicable</span>
        )}
      </span>
    );
  }

  if (typeof val === "number") {
    return <span className="font-mono font-bold text-slate-900 text-sm">{val.toLocaleString()}</span>;
  }

  if (Array.isArray(val)) {
    if (val.length === 0) {
      return null;
    }
    return (
      <ul className="list-disc list-inside space-y-1 text-xs text-slate-700">
        {val.map((item, idx) => (
          <li key={idx}>{typeof item === "object" ? JSON.stringify(item) : String(item)}</li>
        ))}
      </ul>
    );
  }

  if (typeof val === "object") {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
        {Object.entries(val).map(([k, v]) => {
          if (v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0)) return null;
          return (
            <div key={k} className="p-2 bg-white rounded border border-slate-200">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">{humanizeKey(k)}</span>
              <span className="text-xs font-bold text-slate-800">{String(v)}</span>
            </div>
          );
        })}
      </div>
    );
  }

  return <span className="text-xs font-bold text-slate-800">{String(val)}</span>;
}

/**
 * ParameterSubmittedDataViewer
 * Reusable component to present submitted institutional data categorized by subcriteria
 * with human-readable labels, clean cards, and metadata.
 */
export default function ParameterSubmittedDataViewer({
  parameterCode,
  framework = "COLLEGE_2026",
  submittedData = {},
}) {
  const isCollege = String(framework).toUpperCase().includes("COLLEGE") || String(parameterCode).startsWith("C");
  const fwData = isCollege ? COLLEGE_FRAMEWORK_DATA : UNIVERSITY_FRAMEWORK_DATA;
  const paramDef = fwData?.[parameterCode];

  // Extract raw_inputs or direct data
  const rawInputs = submittedData?.raw_inputs || submittedData || {};
  const updatedAt = submittedData?.updated_at;

  const subcriteriaDefs = paramDef?.subcriteria || [];

  // Check if anything was submitted across all subcriteria
  const hasAnyData =
    rawInputs &&
    typeof rawInputs === "object" &&
    Object.keys(rawInputs).length > 0 &&
    Object.values(rawInputs).some((v) => {
      if (v === null || v === undefined || v === "") return false;
      if (typeof v === "object") {
        return Object.values(v).some((fv) => fv !== null && fv !== undefined && fv !== "");
      }
      return true;
    });

  if (!hasAnyData) {
    return (
      <div className="p-8 text-center bg-slate-50/60 rounded-2xl border border-dashed border-slate-200">
        <FileSpreadsheet className="w-8 h-8 text-slate-300 mx-auto mb-2" />
        <p className="text-xs text-slate-600 font-bold uppercase tracking-wider">
          No institutional parameter data submitted for {parameterCode}
        </p>
        <p className="text-[11px] text-slate-400 mt-1">
          The college has not entered form inputs for this criteria.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Subcriteria Sections */}
      {subcriteriaDefs.length > 0 ? (
        subcriteriaDefs.map((sub) => {
          const subCode = sub.code;
          const subTitle = sub.title || getSubcriterionTitle(subCode);
          const fields = sub.fields || [];

          // Retrieve inputs for this subcriterion
          const subRawInputs = rawInputs?.[subCode] || rawInputs || {};

          // Check if this subcriterion has data
          const subHasData =
            subRawInputs &&
            typeof subRawInputs === "object" &&
            Object.keys(subRawInputs).length > 0 &&
            Object.values(subRawInputs).some((val) => val !== null && val !== undefined && val !== "");

          return (
            <div
              key={subCode}
              className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden"
            >
              {/* Subcriterion Card Header */}
              <div className="px-4 py-3 bg-slate-50/80 border-b border-slate-100 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono text-[11px] font-black px-2 py-0.5 rounded bg-[#eaded2] text-[#600b0b] border border-[#ebdcd0] shrink-0">
                    {subCode}
                  </span>
                  <h4 className="text-xs font-bold text-slate-800 truncate" title={subTitle}>
                    {subTitle}
                  </h4>
                </div>
                {sub.maxScore !== undefined && sub.maxScore !== null && (
                  <span className="text-[10px] font-bold text-slate-500 bg-white border border-slate-200 px-2 py-0.5 rounded-md shrink-0">
                    Max: {sub.maxScore} pts
                  </span>
                )}
              </div>

              {/* Subcriterion Fields Table/Grid */}
              <div className="p-4">
                {subHasData ? (
                  <div className="divide-y divide-slate-100">
                    {fields.length > 0 ? (
                      fields.map((f) => {
                        const val = subRawInputs?.[f.key];
                        if (val === undefined && !f.type) return null;

                        return (
                          <div
                            key={f.key}
                            className="py-2.5 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                          >
                            <span className="text-xs font-semibold text-slate-600 sm:max-w-[60%]">
                              {f.label || humanizeKey(f.key)}
                            </span>
                            <div className="sm:text-right">
                              {renderCleanValue(val, f.type)}
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      // Unstructured fields fallback with humanized labels
                      Object.entries(subRawInputs)
                        .filter(([k]) => !["updated_at", "activity_date", "entities", "raw_inputs"].includes(k))
                        .map(([k, v]) => (
                          <div
                            key={k}
                            className="py-2.5 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                          >
                            <span className="text-xs font-semibold text-slate-600 sm:max-w-[60%]">
                              {humanizeKey(k)}
                            </span>
                            <div className="sm:text-right">
                              {renderCleanValue(v)}
                            </div>
                          </div>
                        ))
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 font-medium italic">
                    No data submitted for this subcriterion.
                  </p>
                )}
              </div>
            </div>
          );
        })
      ) : (
        // Generic parameter without explicit subcriteria breakdown
        <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-2xs">
          <div className="divide-y divide-slate-100">
            {Object.entries(rawInputs)
              .filter(([k]) => !["updated_at", "activity_date", "entities", "raw_inputs"].includes(k))
              .map(([k, v]) => (
                <div
                  key={k}
                  className="py-2.5 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <span className="text-xs font-semibold text-slate-600">{humanizeKey(k)}</span>
                  <div className="sm:text-right">{renderCleanValue(v)}</div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Timestamp footer (if available) */}
      {updatedAt && (
        <div className="flex items-center justify-end gap-1 text-[11px] text-slate-400 font-medium pt-1">
          <Calendar className="w-3 h-3 text-slate-400" />
          <span>Last updated: {formatHumanTimestamp(updatedAt)}</span>
        </div>
      )}
    </div>
  );
}
