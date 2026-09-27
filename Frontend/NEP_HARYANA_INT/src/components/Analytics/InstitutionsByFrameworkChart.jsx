import React from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { Building2, GraduationCap, School } from "lucide-react";

export default function InstitutionsByFrameworkChart({ queueItems = [], totalCount = 0 }) {
  const univCount = queueItems.filter((i) => i.framework === "UNIVERSITY_2026").length;
  const colCount = queueItems.filter((i) => i.framework === "COLLEGE_2026").length;
  const otherCount = queueItems.filter(
    (i) => i.framework !== "UNIVERSITY_2026" && i.framework !== "COLLEGE_2026"
  ).length;

  const total = totalCount || queueItems.length;

  const data = [
    {
      frameworkKey: "UNIVERSITY_2026",
      name: "Universities",
      count: univCount,
      color: "#c29b68",
      bg: "bg-[#fbf5ee]",
      border: "border-[#dfb987]",
      text: "text-[#c29b68]",
      icon: Building2,
      label: "Universities (State & Private)",
    },
    {
      frameworkKey: "COLLEGE_2026",
      name: "Colleges",
      count: colCount,
      color: "#600b0b",
      bg: "bg-[#eaded2]",
      border: "border-[#ebdcd0]",
      text: "text-[#600b0b]",
      icon: GraduationCap,
      label: "Colleges (Govt, Aided, Self-Financing)",
    },
  ];

  if (otherCount > 0) {
    data.push({
      frameworkKey: "OTHER",
      name: "Other Frameworks",
      count: otherCount,
      color: "#64748b",
      bg: "bg-slate-50",
      border: "border-slate-200",
      text: "text-slate-700",
      icon: School,
      label: "Other Institutions",
    });
  }

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const dataItem = payload[0].payload;
      const pct = total > 0 ? Math.round((dataItem.count / total) * 100) : 0;
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
            {dataItem.count} institutions ({pct}% of queue)
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
            Institutions by Framework
          </h3>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#fdfaf6] text-[#600b0b] border border-[#ebdcd0] font-mono uppercase tracking-wider">
            {data.length} Frameworks
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Institutional representation grouped by statutory evaluation framework.
        </p>
      </div>

      <div className="h-52 my-auto flex flex-col justify-center">
        {data.every((d) => d.count === 0) ? (
          <div className="text-center text-xs text-slate-400 py-8">
            No institutional records available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
            >
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 12, fill: "#334155", fontWeight: 600 }}
                width={95}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" radius={[0, 8, 8, 0]}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Metric Breakdown Cards */}
      <div className="pt-3 border-t border-slate-100 grid grid-cols-2 gap-2">
        {data.map((item) => {
          const IconComp = item.icon;
          return (
            <div
              key={item.frameworkKey}
              className={`p-2.5 rounded-xl border ${item.bg} ${item.border} flex items-center justify-between`}
            >
              <div className="flex items-center gap-2">
                <div className={`p-1.5 rounded-lg bg-white/80 border ${item.border}`}>
                  <IconComp className={`w-4 h-4 ${item.text}`} />
                </div>
                <div>
                  <span className={`text-[10px] font-bold uppercase tracking-wider block ${item.text}`}>
                    {item.name}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    {total > 0 ? Math.round((item.count / total) * 100) : 0}% of queue
                  </span>
                </div>
              </div>
              <p className="text-xl font-black text-slate-900 font-mono">
                {item.count}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
