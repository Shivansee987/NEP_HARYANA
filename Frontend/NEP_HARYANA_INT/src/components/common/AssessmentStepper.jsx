import React from "react";
import { Check, Clock, AlertCircle, ShieldCheck } from "lucide-react";

/**
 * AssessmentStepper — Institutional Assessment Journey Tracker
 *
 * Clean, compact linear progress header that communicates the authoritative
 * lifecycle stage without excessive card height or disconnected floating badges.
 */

const STAGES = [
  { key: "SESSION", label: "Session" },
  { key: "PARAMETERS", label: "Parameters" },
  { key: "EVIDENCE", label: "Evidence" },
  { key: "VERIFICATION", label: "Verification" },
  { key: "EVALUATION", label: "Evaluation" },
  { key: "REVIEW", label: "Review" },
  { key: "CERTIFICATION", label: "Certification" },
];

function getActiveStageIndex(status, isReadyForScoring = false, completedParamsCount = 0, totalParams = 20) {
  if (!status) return 0;
  const s = String(status).toUpperCase();

  if (s === "CERTIFIED") return 6;
  if (s === "UNDER_REVIEW") return 5;
  if (s === "SUBMITTED") return 3;
  if (s === "DRAFT") {
    if (completedParamsCount === 0) return 0;
    if (completedParamsCount < totalParams) return 1;
    return 2;
  }
  return 1;
}

export default function AssessmentStepper({
  status = "DRAFT",
  isReadyForScoring = false,
  completedParameters = 0,
  totalParameters = 20,
  className = "",
}) {
  const activeIndex = getActiveStageIndex(status, isReadyForScoring, completedParameters, totalParameters);
  const isCertified = status === "CERTIFIED";

  return (
    <div className={`w-full bg-white rounded-xl border border-slate-200/90 px-6 py-4 shadow-xs ${className}`}>
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">
            Assessment Workflow
          </span>
          <span className="text-slate-300">•</span>
          <span className="text-xs font-semibold text-slate-700">
            Current: <strong className="text-blue-700 font-bold">{STAGES[activeIndex]?.label}</strong>
          </span>
        </div>
        <span className="text-xs font-semibold text-slate-400">
          Step {activeIndex + 1} of {STAGES.length}
        </span>
      </div>

      <nav aria-label="Assessment Journey Progress">
        <ol className="flex items-center w-full">
          {STAGES.map((stage, idx) => {
            const isCompleted = idx < activeIndex || (idx === activeIndex && isCertified);
            const isCurrent = idx === activeIndex && !isCertified;
            const isUpcoming = idx > activeIndex;

            return (
              <li
                key={stage.key}
                className={`relative flex items-center ${idx < STAGES.length - 1 ? "flex-1" : ""}`}
              >
                <div className="flex items-center gap-2 shrink-0">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold transition-all ${
                      isCompleted
                        ? "bg-emerald-600 text-white shadow-xs"
                        : isCurrent
                        ? "bg-blue-600 text-white ring-4 ring-blue-100 shadow-xs"
                        : "bg-slate-100 text-slate-400 border border-slate-200"
                    }`}
                    aria-current={isCurrent ? "step" : undefined}
                  >
                    {isCompleted ? (
                      <Check size={12} strokeWidth={3} />
                    ) : (
                      <span>{idx + 1}</span>
                    )}
                  </div>
                  <span
                    className={`text-xs font-medium whitespace-nowrap hidden md:inline ${
                      isCompleted
                        ? "text-slate-700 font-semibold"
                        : isCurrent
                        ? "text-blue-700 font-bold"
                        : "text-slate-400"
                    }`}
                  >
                    {stage.label}
                  </span>
                </div>

                {idx < STAGES.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-2.5 rounded-full transition-colors ${
                      idx < activeIndex ? "bg-emerald-500" : "bg-slate-200"
                    }`}
                    aria-hidden="true"
                  />
                )}
              </li>
            );
          })}
        </ol>
      </nav>
    </div>
  );
}
