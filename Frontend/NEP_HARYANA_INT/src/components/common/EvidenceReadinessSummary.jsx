import React from "react";
import { CheckCircle2, Clock, AlertCircle, ShieldAlert, FileText } from "lucide-react";

/**
 * EvidenceReadinessSummary — Structured Institutional Evidence Breakdown
 *
 * Clearly communicates:
 * - Total Subcriteria requiring evidence
 * - Verified & Eligible
 * - Pending Reviewer Verification
 * - Rejected by Reviewer
 * - Missing / Uncovered
 * - Gating readiness status
 *
 * Consumes authoritative summary directly from /readiness/ API response.
 */
export default function EvidenceReadinessSummary({
  summary,
  isReady = false,
  className = "",
  onActionClick = null,
}) {
  const total = summary?.total_subcriteria ?? 0;
  const covered = summary?.covered_subcriteria ?? 0;
  const verified = summary?.verified_subcriteria ?? (isReady ? covered : 0);
  const pending = summary?.pending_subcriteria ?? 0;
  const rejected = summary?.rejected_subcriteria ?? 0;
  const uncovered = summary?.uncovered_subcriteria ?? (total - covered);

  const coveragePercent = total > 0 ? Math.round((covered / total) * 100) : 0;

  return (
    <div className={`bg-white rounded-xl border border-slate-200 p-5 shadow-sm ${className}`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">
              Evidence Readiness & Gating
            </h3>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                isReady
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                  : "bg-amber-100 text-amber-800 border border-amber-300"
              }`}
            >
              {isReady ? "Ready for Scoring" : "Gating Action Required"}
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Authoritative proof verification across statutory framework subcriteria.
          </p>
        </div>

        {onActionClick && (
          <button
            onClick={onActionClick}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-lg text-xs font-semibold transition-colors shrink-0"
          >
            <FileText size={13} />
            Manage Evidence
          </button>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-slate-600 mb-1.5">
          <span className="font-semibold">Subcriteria Coverage</span>
          <span className="font-bold text-slate-800">{covered} of {total} covered ({coveragePercent}%)</span>
        </div>
        <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden flex">
          <div
            style={{ width: `${total > 0 ? (verified / total) * 100 : 0}%` }}
            className="bg-emerald-600 transition-all duration-300"
            title={`${verified} Verified`}
          />
          <div
            style={{ width: `${total > 0 ? (pending / total) * 100 : 0}%` }}
            className="bg-amber-400 transition-all duration-300"
            title={`${pending} Pending`}
          />
          <div
            style={{ width: `${total > 0 ? (rejected / total) * 100 : 0}%` }}
            className="bg-red-500 transition-all duration-300"
            title={`${rejected} Rejected`}
          />
        </div>
      </div>

      {/* Breakdown Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-emerald-50/60 border border-emerald-200/80 rounded-lg">
          <div className="flex items-center gap-1.5 text-emerald-800 text-[11px] font-bold uppercase tracking-wider mb-1">
            <CheckCircle2 size={13} className="text-emerald-600" />
            Verified
          </div>
          <p className="text-lg font-extrabold text-emerald-900 leading-none">{verified}</p>
          <span className="text-[10px] text-emerald-700">Eligible for scoring</span>
        </div>

        <div className="p-3 bg-amber-50/60 border border-amber-200/80 rounded-lg">
          <div className="flex items-center gap-1.5 text-amber-800 text-[11px] font-bold uppercase tracking-wider mb-1">
            <Clock size={13} className="text-amber-600" />
            Pending
          </div>
          <p className="text-lg font-extrabold text-amber-900 leading-none">{pending}</p>
          <span className="text-[10px] text-amber-700">Awaiting review</span>
        </div>

        <div className="p-3 bg-red-50/60 border border-red-200/80 rounded-lg">
          <div className="flex items-center gap-1.5 text-red-800 text-[11px] font-bold uppercase tracking-wider mb-1">
            <AlertCircle size={13} className="text-red-600" />
            Rejected
          </div>
          <p className="text-lg font-extrabold text-red-900 leading-none">{rejected}</p>
          <span className="text-[10px] text-red-700">Requires correction</span>
        </div>

        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
          <div className="flex items-center gap-1.5 text-slate-700 text-[11px] font-bold uppercase tracking-wider mb-1">
            <ShieldAlert size={13} className="text-slate-500" />
            Uncovered
          </div>
          <p className="text-lg font-extrabold text-slate-900 leading-none">{uncovered}</p>
          <span className="text-[10px] text-slate-500">Missing documents</span>
        </div>
      </div>
    </div>
  );
}
