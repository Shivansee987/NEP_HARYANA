import React, { useState } from "react";
import { CheckCircle2, Clock, Circle, Filter } from "lucide-react";

export default function ParameterWiseProgress({
  parameterCodes = [],
  parameterTitles = {},
  parameterStatusMap = {},
  evidenceAssociations = [],
  onNavigateToParam = null,
}) {
  const [filter, setFilter] = useState("ALL"); // 'ALL' | 'COMPLETE' | 'IN_PROGRESS' | 'NOT_STARTED'

  // Pre-calculate evidence count map
  const evidenceCountByParam = {};
  (evidenceAssociations || []).forEach((assoc) => {
    const pCode = (assoc.parameter_id || "").toUpperCase();
    evidenceCountByParam[pCode] = (evidenceCountByParam[pCode] || 0) + 1;
  });

  const filteredCodes = parameterCodes.filter((code) => {
    const s = parameterStatusMap[code] || "NOT_STARTED";
    if (filter === "COMPLETE") return s === "COMPLETE";
    if (filter === "IN_PROGRESS") return s === "IN_PROGRESS";
    if (filter === "NOT_STARTED") return s === "NOT_STARTED";
    return true;
  });

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs">
      {/* Header with Filter Pills */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
        <div>
          <h3 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight">
            Parameter-wise Progress (C1–C22)
          </h3>
          <p className="text-xs text-slate-500">
            Granular breakdown of data entry completion and attached documentary evidence.
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-lg text-xs font-semibold text-slate-600 self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setFilter("ALL")}
            className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
              filter === "ALL" ? "bg-white text-slate-900 shadow-xs font-bold" : "hover:text-slate-900"
            }`}
          >
            All ({parameterCodes.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter("COMPLETE")}
            className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
              filter === "COMPLETE" ? "bg-emerald-600 text-white shadow-xs font-bold" : "hover:text-emerald-700"
            }`}
          >
            Complete ({parameterCodes.filter((c) => parameterStatusMap[c] === "COMPLETE").length})
          </button>
          <button
            type="button"
            onClick={() => setFilter("IN_PROGRESS")}
            className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
              filter === "IN_PROGRESS" ? "bg-blue-600 text-white shadow-xs font-bold" : "hover:text-blue-700"
            }`}
          >
            In Progress ({parameterCodes.filter((c) => parameterStatusMap[c] === "IN_PROGRESS").length})
          </button>
          <button
            type="button"
            onClick={() => setFilter("NOT_STARTED")}
            className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
              filter === "NOT_STARTED" ? "bg-slate-700 text-white shadow-xs font-bold" : "hover:text-slate-900"
            }`}
          >
            Pending ({parameterCodes.filter((c) => (parameterStatusMap[c] || "NOT_STARTED") === "NOT_STARTED").length})
          </button>
        </div>
      </div>

      {/* Grid of 22 parameter bars */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[460px] overflow-y-auto pr-1">
        {filteredCodes.map((code) => {
          const title = parameterTitles[code] || `Parameter ${code}`;
          const status = parameterStatusMap[code] || "NOT_STARTED";
          const evCount = evidenceCountByParam[code] || 0;

          const percent =
            status === "COMPLETE" ? 100 : status === "IN_PROGRESS" ? 50 : 0;

          const barColor =
            status === "COMPLETE"
              ? "bg-emerald-500"
              : status === "IN_PROGRESS"
              ? "bg-blue-500"
              : "bg-slate-200";

          return (
            <div
              key={code}
              onClick={() => onNavigateToParam && onNavigateToParam(code)}
              className={`p-3 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors ${
                onNavigateToParam ? "cursor-pointer group" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono font-extrabold text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 shrink-0">
                    {code}
                  </span>
                  <span
                    className="text-xs font-bold text-slate-900 truncate group-hover:text-blue-700 transition-colors"
                    title={title}
                  >
                    {title}
                  </span>
                </div>

                <div className="shrink-0 flex items-center gap-1.5">
                  {status === "COMPLETE" ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                      <CheckCircle2 size={11} className="text-emerald-600" />
                      <span>100%</span>
                    </span>
                  ) : status === "IN_PROGRESS" ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
                      <Clock size={11} className="text-blue-600" />
                      <span>Draft</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
                      <Circle size={9} className="text-slate-400" />
                      <span>0%</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Progress track */}
              <div className="w-full h-1.5 bg-slate-200/80 rounded-full overflow-hidden mb-2">
                <div
                  className={`h-full ${barColor} rounded-full transition-all duration-300`}
                  style={{ width: `${percent}%` }}
                />
              </div>

              {/* Sub-label for evidence attached */}
              <div className="flex items-center justify-between text-[11px] text-slate-500">
                <span className="italic">
                  {status === "COMPLETE"
                    ? "Required inputs completed"
                    : status === "IN_PROGRESS"
                    ? "Form inputs in progress"
                    : "Not yet started"}
                </span>
                <span
                  className={`font-semibold ${
                    evCount > 0 ? "text-purple-700" : "text-slate-400"
                  }`}
                >
                  {evCount} proof{evCount === 1 ? "" : "s"} attached
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
