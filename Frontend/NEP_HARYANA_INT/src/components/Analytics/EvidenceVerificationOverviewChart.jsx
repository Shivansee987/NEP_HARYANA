import React, { useState, useEffect } from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from "recharts";
import { ShieldCheck, FileCheck, AlertTriangle, FileText, Loader2 } from "lucide-react";
import { request } from "../../api/auth";

export default function EvidenceVerificationOverviewChart({ queueItems = [] }) {
  const [loading, setLoading] = useState(false);
  const [evidenceStats, setEvidenceStats] = useState({
    verified: 0,
    pending: 0,
    rejected: 0,
    present: 0,
    total: 0,
  });

  useEffect(() => {
    let isMounted = true;
    async function loadEvidenceStats() {
      if (!queueItems || queueItems.length === 0) return;
      setLoading(true);
      try {
        // Fetch evidence associations from backend for active assessments
        const res = await request("/evidence/associations/");
        const items = res?.results || (Array.isArray(res) ? res : []);
        
        let verified = 0;
        let pending = 0;
        let rejected = 0;
        let present = 0;

        items.forEach((assoc) => {
          const status = (assoc.verification_status || "PENDING").toUpperCase();
          if (status === "VERIFIED") verified += 1;
          else if (status === "REJECTED") rejected += 1;
          else if (status === "PENDING" || status === "PROVISIONAL_PENDING_VERIFICATION") pending += 1;
          else present += 1;
        });

        if (isMounted) {
          setEvidenceStats({
            verified,
            pending,
            rejected,
            present,
            total: items.length,
          });
        }
      } catch (err) {
        console.warn("Could not load global evidence stats:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadEvidenceStats();
    return () => {
      isMounted = false;
    };
  }, [queueItems]);

  const data = [
    {
      name: "Evidence Status",
      Verified: evidenceStats.verified,
      "Pending Review": evidenceStats.pending,
      Rejected: evidenceStats.rejected,
    },
  ];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900 text-white p-3 rounded-xl shadow-xl border border-slate-700 text-xs space-y-1.5">
          <p className="font-bold text-slate-200">Evidence Verification Distribution</p>
          {payload.map((entry, idx) => (
            <div key={`ev-${idx}`} className="flex items-center justify-between gap-4">
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
            Total Uploaded Proofs: {evidenceStats.total}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-2xl border border-[#ebdcd0] p-5 shadow-xs flex flex-col justify-between h-full hover:border-[#c29b68] transition-all">
      <div>
        <div className="flex items-center justify-between gap-2 mb-1">
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">
            Evidence & Verification Overview
          </h3>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#fdfaf6] text-[#600b0b] border border-[#ebdcd0] font-mono uppercase tracking-wider">
            {evidenceStats.total} Proofs Attached
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Substantiating documentary proofs verification status across queue.
        </p>
      </div>

      <div className="h-52 my-auto flex flex-col justify-center">
        {loading ? (
          <div className="flex items-center justify-center gap-2 text-xs text-slate-400 py-8">
            <Loader2 className="w-4 h-4 animate-spin text-amber-600" />
            <span>Loading evidence statistics...</span>
          </div>
        ) : evidenceStats.total === 0 ? (
          <div className="text-center text-xs text-slate-400 py-8">
            No documentary proofs uploaded in queue
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 10, right: 20, left: 10, bottom: 10 }}
            >
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 10, fill: "#64748b" }} />
              <YAxis type="category" dataKey="name" hide />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                iconType="circle"
                wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
              />
              <Bar dataKey="Verified" stackId="ev" fill="#10b981" radius={[4, 0, 0, 4]} />
              <Bar dataKey="Pending Review" stackId="ev" fill="#a855f7" />
              <Bar dataKey="Rejected" stackId="ev" fill="#ef4444" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Metric Breakdown Cards */}
      <div className="pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center">
        <div className="p-2 rounded-xl bg-emerald-50/70 border border-emerald-100">
          <span className="text-[10px] font-bold text-emerald-800 uppercase block truncate">
            Verified
          </span>
          <p className="text-base font-extrabold text-emerald-950 font-mono mt-0.5">
            {evidenceStats.verified}
          </p>
        </div>

        <div className="p-2 rounded-xl bg-purple-50/70 border border-purple-100">
          <span className="text-[10px] font-bold text-purple-800 uppercase block truncate">
            Pending
          </span>
          <p className="text-base font-extrabold text-purple-950 font-mono mt-0.5">
            {evidenceStats.pending}
          </p>
        </div>

        <div className="p-2 rounded-xl bg-red-50/70 border border-red-100">
          <span className="text-[10px] font-bold text-red-800 uppercase block truncate">
            Rejected
          </span>
          <p className="text-base font-extrabold text-red-950 font-mono mt-0.5">
            {evidenceStats.rejected}
          </p>
        </div>
      </div>
    </div>
  );
}
