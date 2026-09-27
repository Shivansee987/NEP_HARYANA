import React from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from "recharts";
import { ShieldCheck, CheckCircle2, Clock, AlertTriangle } from "lucide-react";

export default function EvidenceCoverageChart({
  coveredCount = 0,
  uncoveredCount = 0,
  verifiedCount = 0,
  pendingVerificationCount = 0,
  rejectedCount = 0,
  totalSubcriteria = 45,
  isReadyForScoring = false,
}) {
  const coveragePercent =
    totalSubcriteria > 0 ? Math.round((coveredCount / totalSubcriteria) * 100) : 0;

  // Breakdown bar data
  const data = [
    {
      name: "Subcriteria",
      Verified: verifiedCount,
      "Pending Review": pendingVerificationCount,
      "Missing Evidence": Math.max(0, totalSubcriteria - coveredCount),
    },
  ];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900 text-white p-3 rounded-lg shadow-xl border border-slate-700 text-xs space-y-1.5">
          <p className="font-bold text-slate-200">Documentary Proof Status</p>
          {payload.map((entry, idx) => (
            <div key={`item-${idx}`} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span
                  className="w-2.5 h-2.5 rounded-full inline-block"
                  style={{ backgroundColor: entry.color }}
                />
                {entry.name}:
              </span>
              <span className="font-bold font-mono text-white">{entry.value}</span>
            </div>
          ))}
          <div className="pt-1 border-t border-slate-700 text-[11px] text-slate-400">
            Total Requirements: {totalSubcriteria}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between gap-2 mb-1">
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">
            Evidence Coverage & Proof Gating
          </h3>
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${
              isReadyForScoring
                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                : "bg-amber-50 text-amber-800 border-amber-200"
            }`}
          >
            {isReadyForScoring ? "Threshold Met" : "Gating Action Required"}
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Substantiating proofs attached across subcriteria vs statutory requirements.
        </p>
      </div>

      {/* Progress & Bar visual */}
      <div className="my-auto py-2 space-y-4">
        <div>
          <div className="flex items-baseline justify-between mb-1.5">
            <span className="text-xs font-bold text-slate-700">Overall Proof Coverage</span>
            <span className="text-xs font-mono font-bold text-purple-700">
              {coveredCount} / {totalSubcriteria} ({coveragePercent}%)
            </span>
          </div>

          <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden flex">
            {/* Verified segment */}
            <div
              style={{
                width: `${totalSubcriteria > 0 ? (verifiedCount / totalSubcriteria) * 100 : 0}%`,
              }}
              className="bg-emerald-500 transition-all duration-500"
              title={`Verified: ${verifiedCount}`}
            />
            {/* Attached / Pending Review segment */}
            <div
              style={{
                width: `${
                  totalSubcriteria > 0
                    ? ((coveredCount - verifiedCount) / totalSubcriteria) * 100
                    : 0
                }%`,
              }}
              className="bg-purple-500 transition-all duration-500"
              title={`Attached (Pending Review): ${coveredCount - verifiedCount}`}
            />
            {/* Missing segment */}
            <div
              style={{
                width: `${
                  totalSubcriteria > 0
                    ? (Math.max(0, totalSubcriteria - coveredCount) / totalSubcriteria) * 100
                    : 0
                }%`,
              }}
              className="bg-slate-200 transition-all duration-500"
              title={`Missing: ${totalSubcriteria - coveredCount}`}
            />
          </div>
        </div>

        {/* Stacked Chart Visualizer */}
        <div className="h-28 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <XAxis type="number" domain={[0, totalSubcriteria]} hide />
              <YAxis type="category" dataKey="name" hide />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                iconType="circle"
                wrapperStyle={{ fontSize: "11px", paddingTop: "6px" }}
              />
              <Bar dataKey="Verified" stackId="a" fill="#10b981" radius={[4, 0, 0, 4]} />
              <Bar dataKey="Pending Review" stackId="a" fill="#a855f7" />
              <Bar dataKey="Missing Evidence" stackId="a" fill="#cbd5e1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Metric Breakdown Cards */}
      <div className="pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center">
        <div className="p-2 rounded-lg bg-purple-50/70 border border-purple-100">
          <span className="text-[10px] font-bold text-purple-800 uppercase block truncate">
            Proofs Attached
          </span>
          <p className="text-base font-extrabold text-purple-950 font-mono mt-0.5">
            {coveredCount}
          </p>
        </div>

        <div className="p-2 rounded-lg bg-emerald-50/70 border border-emerald-100">
          <span className="text-[10px] font-bold text-emerald-800 uppercase block truncate">
            Verified
          </span>
          <p className="text-base font-extrabold text-emerald-950 font-mono mt-0.5">
            {verifiedCount}
          </p>
        </div>

        <div className="p-2 rounded-lg bg-amber-50/70 border border-amber-100">
          <span className="text-[10px] font-bold text-amber-800 uppercase block truncate">
            Pending Proof
          </span>
          <p className="text-base font-extrabold text-amber-950 font-mono mt-0.5">
            {Math.max(0, totalSubcriteria - coveredCount)}
          </p>
        </div>
      </div>
    </div>
  );
}
