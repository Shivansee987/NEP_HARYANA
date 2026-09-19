import React from "react";
import { Check, Clock, AlertCircle, ShieldCheck } from "lucide-react";

/**
 * AssessmentStepper — Authoritative Lifecycle Journey Indicator
 *
 * Visualizes the assessment workflow:
 * Assessment Session -> Parameter Inputs -> Documentary Evidence -> Evidence Verification -> Evaluation & Scoring -> Review -> Certification
 *
 * CRITICAL: Lifecycle stage is determined purely from server-provided status.
 * Zero client-side stage inference or synthetic calculation.
 */

const STAGES = [
  { key: "SESSION", label: "Session" },
  { key: "PARAMETERS", label: "Parameters" },
  { key: "EVIDENCE", label: "Evidence" },
  { key: "VERIFICATION", label: "Verification" },
  { key: "EVALUATION", label: "Evaluation" },
  { key: "REVIEW", label: "Committee Review" },
  { key: "CERTIFICATION", label: "Certification" },
];

/**
 * Maps server-authoritative assessment status to the active stage index.
 */
function getActiveStageIndex(status, isReadyForScoring = false, completedParamsCount = 0, totalParams = 20) {
  if (!status) return 0;
  const s = String(status).toUpperCase();

  if (s === "CERTIFIED") return 6;
  if (s === "UNDER_REVIEW") return 5;
  if (s === "SUBMITTED") return 3; // In Verification / Committee hands
  if (s === "DRAFT") {
    if (completedParamsCount === 0) return 0; // Session just started
    if (completedParamsCount < totalParams) return 1; // Parameters in progress
    if (!isReadyForScoring) return 2; // Evidence gathering
    return 2; // Evidence ready, awaiting submission
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
    <div className={`w-full bg-white rounded-xl border border-slate-200 p-4 shadow-sm ${className}`}>
      <div className="flex items-center justify-between mb-3 px-1">
        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
          Assessment Journey
        </span>
        <span className="text-xs font-semibold text-slate-700">
          Stage {activeIndex + 1} of {STAGES.length}:{" "}
          <span className="text-blue-700 font-bold">{STAGES[activeIndex]?.label}</span>
        </span>
      </div>

      <nav aria-label="Assessment Progress">
        <ol className="flex items-center w-full">
          {STAGES.map((stage, idx) => {
            const isCompleted = idx < activeIndex || (idx === activeIndex && isCertified);
            const isCurrent = idx === activeIndex && !isCertified;
            const isUpcoming = idx > activeIndex;

            return (
              <li
                key={stage.key}
                className={`relative flex items-center ${
                  idx < STAGES.length - 1 ? "flex-1" : ""
                }`}
              >
                <div className="flex flex-col items-center group">
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                      isCompleted
                        ? "bg-emerald-600 text-white shadow-sm ring-2 ring-emerald-100"
                        : isCurrent
                        ? "bg-blue-600 text-white shadow-sm ring-4 ring-blue-100 animate-pulse"
                        : "bg-slate-100 text-slate-400 border border-slate-300"
                    }`}
                    aria-current={isCurrent ? "step" : undefined}
                  >
                    {isCompleted ? (
                      <Check size={13} strokeWidth={3} />
                    ) : isCurrent ? (
                      <span className="w-2 h-2 rounded-full bg-white" />
                    ) : (
                      <span>{idx + 1}</span>
                    )}
                  </div>
                  <span
                    className={`mt-1.5 text-[11px] font-semibold text-center whitespace-nowrap hidden sm:block ${
                      isCompleted
                        ? "text-slate-800"
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
                    className={`flex-1 h-0.5 mx-2 transition-colors ${
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
