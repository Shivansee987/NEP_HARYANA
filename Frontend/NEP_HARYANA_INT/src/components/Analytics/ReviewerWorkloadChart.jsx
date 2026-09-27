import React from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { UserCheck, ShieldCheck, UserX } from "lucide-react";

export default function ReviewerWorkloadChart({ queueItems = [] }) {
  // Aggregate workload by reviewer
  const reviewerMap = {};
  let hasAssignedReviewers = false;

  queueItems.forEach((item) => {
    if (item.assigned_reviewer_name) {
      hasAssignedReviewers = true;
      const name = item.assigned_reviewer_name;
      reviewerMap[name] = (reviewerMap[name] || 0) + 1;
    } else {
      reviewerMap["Unassigned"] = (reviewerMap["Unassigned"] || 0) + 1;
    }
  });

  // If no assessments have been assigned to any reviewers, gracefully return null
  if (!hasAssignedReviewers) {
    return null;
  }

  const data = Object.entries(reviewerMap).map(([name, count]) => ({
    name,
    count,
    color: name === "Unassigned" ? "#94a3b8" : "#600b0b",
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const dataItem = payload[0].payload;
      return (
        <div className="bg-slate-900 text-white p-2.5 rounded-xl shadow-xl border border-slate-700 text-xs space-y-1">
          <p className="font-bold text-slate-200">{dataItem.name}</p>
          <p className="text-amber-400 font-mono">
            {dataItem.count} {dataItem.count === 1 ? "assessment" : "assessments"} assigned
          </p>
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
            Reviewer Workload
          </h3>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#fdfaf6] text-[#600b0b] border border-[#ebdcd0] font-mono uppercase tracking-wider">
            {data.length} Reviewers
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Assessments assigned per screening committee member.
        </p>
      </div>

      <div className="h-52 my-auto">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
          >
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 10, fill: "#64748b" }} />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11, fill: "#334155", fontWeight: 600 }}
              width={100}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="count" radius={[0, 6, 6, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
