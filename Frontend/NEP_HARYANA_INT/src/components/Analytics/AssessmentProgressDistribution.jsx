import React from "react";
import { ArrowRight, CheckCircle2, Clock, ShieldCheck, Award, FileCheck2 } from "lucide-react";

const STAGES = [
  {
    key: "SUBMITTED",
    label: "Submitted",
    sublabel: "Awaiting Scrutiny",
    icon: Clock,
    color: "amber",
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-800",
    ring: "ring-amber-400",
  },
  {
    key: "UNDER_REVIEW",
    label: "Verification & Scrutiny",
    sublabel: "Evidence Scrutiny Active",
    icon: ShieldCheck,
    color: "purple",
    bg: "bg-purple-50",
    border: "border-purple-200",
    text: "text-purple-800",
    ring: "ring-purple-400",
  },
  {
    key: "EVALUATED",
    label: "Rubric Evaluation",
    sublabel: "Marks Evaluated",
    icon: FileCheck2,
    color: "blue",
    bg: "bg-blue-50",
    border: "border-blue-200",
    text: "text-blue-800",
    ring: "ring-blue-400",
  },
  {
    key: "CERTIFIED",
    label: "Certification",
    sublabel: "Final Seal Awarded",
    icon: Award,
    color: "emerald",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    text: "text-emerald-800",
    ring: "ring-emerald-400",
  },
];

export default function AssessmentProgressDistribution({ queueItems = [], totalCount = 0 }) {
  const total = totalCount || queueItems.length;

  const stageCounts = {
    SUBMITTED: queueItems.filter((i) => i.status === "SUBMITTED").length,
    UNDER_REVIEW: queueItems.filter((i) => i.status === "UNDER_REVIEW" && !i.certified_score).length,
    EVALUATED: queueItems.filter((i) => (i.status === "UNDER_REVIEW" || i.status === "EVALUATED") && i.certified_score !== null && !i.is_certified && i.status !== "CERTIFIED").length,
    CERTIFIED: queueItems.filter((i) => i.status === "CERTIFIED" || i.is_certified || i.certification_status === "FINALIZED").length,
  };

  return (
    <div className="bg-white rounded-2xl border border-[#ebdcd0] p-6 shadow-xs hover:border-[#c29b68] transition-all">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">
            Assessment Progress & Lifecycle Distribution
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Stage-by-stage progression of Haryana institutions through the statutory verification pipeline.
          </p>
        </div>
        <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-[#fdfaf6] text-[#600b0b] border border-[#ebdcd0] font-mono uppercase tracking-wider shrink-0 self-start sm:self-auto">
          {total} Active Assessments
        </span>
      </div>

      {/* Progress Bar / Funnel */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
        {STAGES.map((stage, idx) => {
          const count = stageCounts[stage.key] || 0;
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          const IconComp = stage.icon;

          return (
            <div
              key={stage.key}
              className={`p-4 rounded-xl border ${stage.bg} ${stage.border} relative flex flex-col justify-between transition-all hover:shadow-xs`}
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className={`p-2 rounded-lg bg-white border ${stage.border}`}>
                    <IconComp className={`w-4 h-4 ${stage.text}`} />
                  </div>
                  <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-md bg-white border ${stage.border} ${stage.text}`}>
                    Stage {idx + 1}
                  </span>
                </div>
                <h4 className="text-xs font-bold text-slate-900 leading-tight">
                  {stage.label}
                </h4>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {stage.sublabel}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-baseline justify-between">
                <div>
                  <span className="text-2xl font-black text-slate-900 font-mono">
                    {count}
                  </span>
                  <span className="text-xs text-slate-400 font-mono ml-1">
                    ({pct}%)
                  </span>
                </div>
                {idx < STAGES.length - 1 && (
                  <ArrowRight className="hidden md:block w-4 h-4 text-slate-300 absolute -right-3 top-1/2 -translate-y-1/2 z-10 bg-white rounded-full p-0.5" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
