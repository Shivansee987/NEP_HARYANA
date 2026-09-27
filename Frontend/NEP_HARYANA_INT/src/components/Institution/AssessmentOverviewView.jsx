import {
  Building2,
  ClipboardList,
  CheckCircle2,
  Clock,
  Circle,
  FileText,
  ChevronRight,
  ShieldCheck,
  Send,
  Calendar,
  AlertCircle,
  Award,
} from "lucide-react";
import { StatusBadge } from "../common";

export default function AssessmentOverviewView({
  framework = "COLLEGE_2026",
  assessment = {},
  parameterCodes = [],
  parameterTitles = {},
  parameterStatusMap = {},
  evidenceAssociations = [],
  onNavigateToParam = () => {},
  onNavigateToReview = () => {},
}) {
  const isCollege = framework.includes("COLLEGE") || parameterCodes[0]?.startsWith("C");
  const frameworkLabel = isCollege ? "College Appraisal" : "University Appraisal";
  const frameworkName = isCollege ? "COLLEGE_2026" : "UNIVERSITY_2026";
  const totalParams = parameterCodes.length;

  const completedCount = parameterCodes.filter(
    (code) => parameterStatusMap[code] === "COMPLETE"
  ).length;

  const inProgressCount = parameterCodes.filter(
    (code) => parameterStatusMap[code] === "IN_PROGRESS"
  ).length;

  const pendingCount = totalParams - completedCount;
  const percentComplete = totalParams > 0 ? Math.round((completedCount / totalParams) * 100) : 0;

  // First parameter that is pending or in progress
  const nextPendingParam =
    parameterCodes.find(
      (code) => parameterStatusMap[code] === "IN_PROGRESS" || parameterStatusMap[code] === "NOT_STARTED"
    ) || parameterCodes[0];

  // Count associations per parameter
  const evidenceCountByParam = {};
  evidenceAssociations.forEach((assoc) => {
    const pCode = (assoc.parameter_id || "").toUpperCase();
    evidenceCountByParam[pCode] = (evidenceCountByParam[pCode] || 0) + 1;
  });

  return (
    <div className="space-y-6">
      {/* Top Hero Banner */}
      <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-800 border border-blue-200 uppercase tracking-wider">
                {frameworkName}
              </span>
              <span className="text-slate-300">•</span>
              <span className="text-xs font-mono text-slate-500">
                Session: {assessment.assessment_id || "Active Session"}
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              NEP 2026 Institutional Self-Appraisal
            </h2>
            <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
              Complete inputs across all {totalParams} statutory parameters ({parameterCodes[0]}–
              {parameterCodes[parameterCodes.length - 1]}) and upload substantiating documentary evidence.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => onNavigateToParam(nextPendingParam)}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
            >
              <span>{completedCount === 0 ? "Start Assessment" : "Continue Assessment"}</span>
              <ChevronRight size={14} />
            </button>

            <button
              onClick={onNavigateToReview}
              className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
            >
              <Send size={13} />
              <span>Review & Submit</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 Summary Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Status */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Lifecycle State
              </span>
              <StatusBadge status={assessment.status || "DRAFT"} size="sm" />
            </div>
            <p className="text-xl font-extrabold text-slate-900 tracking-tight">
              {assessment.status || "DRAFT"}
            </p>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-1.5 text-xs text-slate-500">
            <ShieldCheck size={12} className="text-slate-400 shrink-0" />
            <span>Server Authoritative</span>
          </div>
        </div>

        {/* Metric 2: Parameters Completed */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Parameters Completed
              </span>
              <span className="text-[11px] font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                {percentComplete}%
              </span>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
                {completedCount}
              </span>
              <span className="text-xs font-semibold text-slate-400">/ {totalParams} parameters</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100">
            <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 rounded-full transition-all duration-300"
                style={{ width: `${percentComplete}%` }}
              />
            </div>
          </div>
        </div>

        {/* Metric 3: Evidence Attached */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Evidence Files Linked
              </span>
              <span className="text-[10px] font-bold text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-full">
                Phase 5B
              </span>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
                {evidenceAssociations.length}
              </span>
              <span className="text-xs font-semibold text-slate-400">proof associations</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-1.5 text-xs text-slate-500">
            <FileText size={12} className="text-slate-400 shrink-0" />
            <span>Subcriterion Level Proofs</span>
          </div>
        </div>

        {/* Metric 4: Statutory Window */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Academic Cycle
              </span>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                2025–26
              </span>
            </div>
            <p className="text-lg font-extrabold text-slate-900 tracking-tight">
              AY 2025–2026
            </p>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-1.5 text-xs text-slate-500">
            <Calendar size={12} className="text-slate-400 shrink-0" />
            <span>Valid: 2025-07-01 to 2026-06-30</span>
          </div>
        </div>
      </div>

      {/* Parameter Cards Grid */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/60">
          <div>
            <h3 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight">
              Statutory Parameter Index ({parameterCodes[0]}–{parameterCodes[parameterCodes.length - 1]})
            </h3>
            <p className="text-xs text-slate-500">
              Click any parameter to view requirements, record inputs, and associate evidence documents.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="flex items-center gap-1 text-emerald-700 font-semibold">
              <CheckCircle2 size={13} /> {completedCount} Complete
            </span>
            <span className="text-slate-300">•</span>
            <span className="flex items-center gap-1 text-blue-700 font-semibold">
              <Clock size={13} /> {inProgressCount} In Progress
            </span>
            <span className="text-slate-300">•</span>
            <span className="flex items-center gap-1 text-slate-500 font-semibold">
              <Circle size={11} /> {totalParams - completedCount - inProgressCount} Not Started
            </span>
          </div>
        </div>

        <div className="divide-y divide-slate-100">
          {parameterCodes.map((code, idx) => {
            const title = parameterTitles[code] || `Parameter ${code}`;
            const status = parameterStatusMap[code] || "NOT_STARTED";
            const evidenceCount = evidenceCountByParam[code] || 0;

            return (
              <div
                key={code}
                onClick={() => onNavigateToParam(code)}
                className="p-4 hover:bg-slate-50/80 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer group"
              >
                <div className="flex items-start gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-800 border border-blue-200 font-mono font-bold text-xs flex items-center justify-center shrink-0 mt-0.5 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                    {code}
                  </div>

                  <div className="min-w-0">
                    <h4 className="text-xs sm:text-sm font-bold text-slate-900 group-hover:text-blue-700 transition-colors">
                      {title}
                    </h4>
                    <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-500">
                      <span>Index #{idx + 1}</span>
                      <span>•</span>
                      <span>
                        {evidenceCount > 0 ? (
                          <span className="text-purple-700 font-semibold">
                            {evidenceCount} evidence document(s) linked
                          </span>
                        ) : (
                          <span className="text-slate-400">No evidence attached yet</span>
                        )}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                  {status === "COMPLETE" && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-800 border border-emerald-200">
                      <CheckCircle2 size={11} className="text-emerald-600" />
                      <span>Complete</span>
                    </span>
                  )}
                  {status === "IN_PROGRESS" && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-blue-800 border border-blue-200">
                      <Clock size={11} className="text-blue-600" />
                      <span>In Progress</span>
                    </span>
                  )}
                  {status === "NOT_STARTED" && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-600 border border-slate-200">
                      <Circle size={10} className="text-slate-400" />
                      <span>Not Started</span>
                    </span>
                  )}

                  <span className="text-slate-400 group-hover:text-blue-600 transition-colors">
                    <ChevronRight size={16} />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
