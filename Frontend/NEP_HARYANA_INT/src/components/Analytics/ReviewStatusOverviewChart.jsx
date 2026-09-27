import React from "react";
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import { Clock, AlertCircle, CheckCircle2, RotateCcw, XCircle, HelpCircle } from "lucide-react";

const STATUS_CONFIG = {
  SUBMITTED: { label: "Pending Review", color: "#d97706", bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-200", icon: Clock },
  UNDER_REVIEW: { label: "Under Active Review", color: "#9333ea", bg: "bg-purple-50", text: "text-purple-800", border: "border-purple-200", icon: AlertCircle },
  CERTIFIED: { label: "Certified / Completed", color: "#059669", bg: "bg-emerald-50", text: "text-emerald-800", border: "border-emerald-200", icon: CheckCircle2 },
  RETURNED: { label: "Returned for Correction", color: "#ea580c", bg: "bg-orange-50", text: "text-orange-800", border: "border-orange-200", icon: RotateCcw },
  REJECTED: { label: "Rejected / Blocked", color: "#dc2626", bg: "bg-red-50", text: "text-red-800", border: "border-red-200", icon: XCircle },
};

export default function ReviewStatusOverviewChart({ queueItems = [], totalCount = 0 }) {
  const statusCounts = queueItems.reduce((acc, item) => {
    const s = (item.status || "SUBMITTED").toUpperCase();
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});

  const total = totalCount || queueItems.length;

  const data = Object.entries(statusCounts).map(([statusKey, count]) => {
    const conf = STATUS_CONFIG[statusKey] || {
      label: statusKey.replace(/_/g, " "),
      color: "#64748b",
      bg: "bg-slate-50",
      text: "text-slate-800",
      border: "border-slate-200",
      icon: HelpCircle,
    };
    return {
      key: statusKey,
      name: conf.label,
      value: count,
      color: conf.color,
      config: conf,
    };
  }).filter((item) => item.value > 0);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const dataItem = payload[0].payload;
      const pct = total > 0 ? Math.round((dataItem.value / total) * 100) : 0;
      return (
        <div className="bg-slate-900 text-white p-2.5 rounded-xl shadow-xl border border-slate-700 text-xs space-y-1">
          <p className="font-bold flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full inline-block"
              style={{ backgroundColor: dataItem.color }}
            />
            {dataItem.name}
          </p>
          <p className="text-slate-300 font-mono">
            {dataItem.value} of {total} assessments ({pct}%)
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
            Review Status Overview
          </h3>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#fdfaf6] text-[#600b0b] border border-[#ebdcd0] font-mono uppercase tracking-wider">
            {total} Total
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Lifecycle distribution of assessments currently in the committee queue.
        </p>
      </div>

      <div className="h-52 relative flex items-center justify-center my-auto">
        {data.length === 0 ? (
          <div className="text-center text-xs text-slate-400 py-8">
            No assessment status records available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip content={<CustomTooltip />} />
              <Pie
                data={data}
                innerRadius={50}
                outerRadius={75}
                paddingAngle={4}
                dataKey="value"
                stroke="none"
              >
                {data.map((entry, index) => (
                  <Cell key={`status-cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        )}

        {/* Center label */}
        {data.length > 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-black text-slate-900 tracking-tight leading-none font-mono">
              {total}
            </span>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-1 font-mono">
              Queue Total
            </span>
          </div>
        )}
      </div>

      {/* Legend / Breakdown Pills */}
      <div className="pt-3 border-t border-slate-100 flex flex-wrap gap-2">
        {data.map((item) => {
          const IconComponent = item.config.icon || HelpCircle;
          return (
            <div
              key={item.key}
              className={`flex-1 min-w-[110px] p-2 rounded-xl border ${item.config.bg} ${item.config.border} flex flex-col justify-between`}
            >
              <div className={`flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider ${item.config.text}`}>
                <IconComponent className="w-3 h-3 shrink-0" />
                <span className="truncate">{item.name}</span>
              </div>
              <p className="text-base font-extrabold text-slate-900 font-mono mt-1">
                {item.value}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
