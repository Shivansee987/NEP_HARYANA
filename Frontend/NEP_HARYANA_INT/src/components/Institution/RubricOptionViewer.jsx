import React from "react";
import { Check, AlertCircle, Award } from "lucide-react";
import { RUBRIC_REGISTRY, getActiveRubricOptionId } from "../../utils/nepRubrics.js";

/**
 * RubricOptionViewer
 * 
 * Displays the authoritative scoring options from Haryana Higher Education Council source PDFs.
 * Renders:
 * - Mutually exclusive option cards (radio behavior) with threshold and exact marks
 * - Interactive count tier badges
 * - Cumulative checklist item cards
 * - Policy warnings for council-unresolved metrics (e.g. Scopus, boundary voids)
 * - Exact awarded marks for every rubric tier
 */
export default function RubricOptionViewer({
  parameterCode = "",
  subCode = "",
  subDef = {},
  subVals = {},
  allSubVals = {},
  isReadOnly = false,
  onFieldChange = () => {},
}) {
  const paramRubric = RUBRIC_REGISTRY[parameterCode];
  if (!paramRubric || !paramRubric.subcriteria) return null;

  const rubricSub = paramRubric.subcriteria[subCode];
  if (!rubricSub || !rubricSub.options || rubricSub.options.length === 0) return null;

  const activeOptionId = getActiveRubricOptionId(rubricSub, subVals, allSubVals);

  // Compute calculated ratio percentage if applicable
  let calcPct = null;
  if (rubricSub.type === "EXCLUSIVE_TIERS" && rubricSub.numKey) {
    const num = subVals[rubricSub.numKey];
    let den;
    if (rubricSub.denFromSibling) {
      den = (allSubVals[rubricSub.denFromSibling.subCode] || {})[rubricSub.denFromSibling.key];
    } else {
      den = subVals[rubricSub.denKey];
    }
    if (num !== undefined && num !== "" && den !== undefined && den !== "" && Number(den) > 0) {
      calcPct = Math.round((Number(num) / Number(den)) * 1000) / 10;
    }
  }

  const handleSelectOption = (opt) => {
    if (isReadOnly) return;

    if (rubricSub.type === "EXCLUSIVE_TIERS") {
      // If defaultNum and defaultDen exist, populate them when user selects tier
      if (opt.defaultNum !== undefined && opt.defaultDen !== undefined && rubricSub.numKey && rubricSub.denKey) {
        onFieldChange(subCode, rubricSub.numKey, opt.defaultNum, "number");
        onFieldChange(subCode, rubricSub.denKey, opt.defaultDen, "number");
      } else if (opt.defaultNum !== undefined && rubricSub.numKey && !rubricSub.denKey) {
        onFieldChange(subCode, rubricSub.numKey, opt.defaultNum, "number");
      }
    } else if (rubricSub.type === "COUNT_TIERS") {
      if (rubricSub.countKey) {
        const val = opt.minCount !== undefined ? opt.minCount : (opt.exactCount !== undefined ? opt.exactCount : 0);
        onFieldChange(subCode, rubricSub.countKey, val, "number");
      }
    } else if (rubricSub.type === "CHECKLIST_ITEM") {
      if (rubricSub.fieldKey) {
        const current = Boolean(subVals[rubricSub.fieldKey]);
        onFieldChange(subCode, rubricSub.fieldKey, !current, "checkbox");
      }
    } else if (rubricSub.type === "GRADE_SELECT") {
      if (rubricSub.fieldKey && opt.values && opt.values.length > 0) {
        onFieldChange(subCode, rubricSub.fieldKey, opt.values[0], "select");
      }
    } else if (rubricSub.type === "CURRENCY_TIERS") {
      if (rubricSub.fieldKey) {
        const val = opt.minVal !== undefined ? opt.minVal : (opt.exactVal !== undefined ? opt.exactVal : 0);
        onFieldChange(subCode, rubricSub.fieldKey, val, "number");
      }
    } else if (rubricSub.type === "PER_UNIT_AREAS") {
      if (rubricSub.gateKey && rubricSub.gateMin !== undefined) {
        onFieldChange(subCode, rubricSub.gateKey, rubricSub.gateMin, "number");
      }
      if (rubricSub.fieldKey) {
        const current = Array.isArray(subVals[rubricSub.fieldKey]) ? subVals[rubricSub.fieldKey] : [];
        if (opt.id.endsWith("_T1")) {
          onFieldChange(subCode, rubricSub.fieldKey, ["Curriculum", "Pedagogy", "Evaluation", "Administration"], "multiselect");
        } else if (opt.id.endsWith("_T2")) {
          onFieldChange(subCode, rubricSub.fieldKey, ["Curriculum", "Pedagogy", "Evaluation"], "multiselect");
        } else if (opt.id.endsWith("_T3")) {
          onFieldChange(subCode, rubricSub.fieldKey, ["Curriculum", "Pedagogy"], "multiselect");
        } else if (opt.id.endsWith("_T4")) {
          onFieldChange(subCode, rubricSub.fieldKey, ["Curriculum"], "multiselect");
        } else if (opt.id.endsWith("_T5")) {
          onFieldChange(subCode, rubricSub.fieldKey, [], "multiselect");
        }
      }
    }
  };

  const isChecklist = rubricSub.type === "CHECKLIST_ITEM";

  return (
    <div className="mt-4 pt-3 border-t border-slate-100">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2.5">
        <div className="flex items-center gap-2 flex-wrap">
          <Award size={15} className="text-[#600b0b]" />
          <h5 className="text-[11px] font-bold text-slate-800 uppercase tracking-wider">
            Official Scoring Options (Haryana Higher Education Council Rubric)
          </h5>
          {calcPct !== null && (
            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-[#600b0b]/10 text-[#600b0b] border border-[#600b0b]/20">
              Achieved: {calcPct}%
            </span>
          )}
          {rubricSub.countKey && subVals[rubricSub.countKey] !== undefined && subVals[rubricSub.countKey] !== "" && (
            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
              Current Count: {subVals[rubricSub.countKey]}
            </span>
          )}
        </div>
        <span className="text-[10px] font-semibold text-slate-500">
          Max for this section: <strong className="text-slate-800">{rubricSub.maxMarks} Marks</strong>
        </span>
      </div>

      {rubricSub.isPolicyNotice && (
        <div className="mb-3 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-start gap-2">
          <AlertCircle size={15} className="text-amber-600 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-relaxed">
            {rubricSub.policyNoticeText}
          </div>
        </div>
      )}

      {/* Grid of Official Rubric Cards */}
      <div className={`grid gap-2.5 ${
        rubricSub.options.length === 1
          ? "grid-cols-1"
          : rubricSub.options.length === 2
          ? "grid-cols-1 sm:grid-cols-2"
          : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
      }`}>
        {rubricSub.options.map((opt) => {
          const isActive = activeOptionId === opt.id;

          return (
            <div
              key={opt.id}
              role={isChecklist ? "checkbox" : "radio"}
              aria-checked={isActive}
              tabIndex={isReadOnly ? -1 : 0}
              onClick={() => handleSelectOption(opt)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleSelectOption(opt);
                }
              }}
              className={`p-3 rounded-lg border text-left transition-all relative flex flex-col justify-between ${
                isReadOnly ? "cursor-default" : "cursor-pointer"
              } ${
                isActive
                  ? "border-[#600b0b] bg-[#600b0b]/5 ring-1 ring-[#600b0b]/30 shadow-xs"
                  : "border-slate-200 bg-slate-50/50 hover:bg-slate-50 hover:border-slate-300"
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs font-bold text-slate-900 leading-snug">
                    {opt.label}
                  </span>
                  <div className="shrink-0 flex items-center gap-1">
                    <span
                      className={`text-[11px] font-extrabold px-2 py-0.5 rounded-full font-mono ${
                        opt.marks > 0
                          ? isActive
                            ? "bg-[#600b0b] text-white"
                            : "bg-emerald-50 text-emerald-800 border border-emerald-200"
                          : "bg-slate-100 text-slate-600 border border-slate-200"
                      }`}
                    >
                      {opt.marks} {opt.marks === 1 ? "Mark" : "Marks"}
                    </span>
                  </div>
                </div>

                <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-slate-600">
                  <span className="text-slate-400 font-mono">Condition:</span>
                  <code className="text-[10px] bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700 font-mono">
                    {opt.threshold}
                  </code>
                </div>
              </div>

              {/* Active Indicator Footer */}
              <div className="mt-2.5 pt-2 border-t border-slate-200/60 flex items-center justify-between text-[10px]">
                {isActive ? (
                  <span className="inline-flex items-center gap-1 font-bold text-[#600b0b]">
                    <Check size={12} className="stroke-[3]" />
                    <span>Active Qualified Tier</span>
                  </span>
                ) : (
                  <span className="text-slate-400 font-medium">
                    {isReadOnly ? "Not selected" : isChecklist ? "Click to toggle" : "Click to select tier"}
                  </span>
                )}
                {isActive && (
                  <span className="font-mono text-[#600b0b] font-bold">
                    +{opt.marks} pts
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
