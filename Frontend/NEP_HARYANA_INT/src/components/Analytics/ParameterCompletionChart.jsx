import React from "react";
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from "recharts";
import { CheckCircle2, Clock, Circle, Award } from "lucide-react";

const COLORS = {
  Completed: "#10b981", // Emerald 500
  "In Progress": "#3b82f6", // Blue 500
  "Not Started": "#94a3b8", // Slate 400
};

export default function ParameterCompletionChart({
  completedCount = 0,
  inProgressCount = 0,
  notStartedCount = 0,
  totalCount = 22,
}) {
  const data = [
    { name: "Completed", value: completedCount, color: COLORS.Completed },
    { name: "In Progress", value: inProgressCount, color: COLORS["In Progress"] },
    { name: "Not Started", value: notStartedCount, color: COLORS["Not Started"] },
  ].filter((item) => item.value > 0);

  const percentComplete = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const dataItem = payload[0];
      const pct = totalCount > 0 ? Math.round((dataItem.value / totalCount) * 100) : 0;
      return (
        <div className="bg-slate-900 text-white p-2.5 rounded-lg shadow-xl border border-slate-700 text-xs space-y-1">
          <p className="font-bold flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full inline-block"
              style={{ backgroundColor: dataItem.payload.color }}
            />
            {dataItem.name}
          </p>
          <p className="text-slate-300 font-mono">
            {dataItem.value} of {totalCount} parameters ({pct}%)
          </p>
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
            Parameter Completion Overview
          </h3>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 uppercase tracking-wider">
            {totalCount} Parameters
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Status distribution across statutory evaluation parameters.
        </p>
      </div>

      <div className="h-56 relative flex items-center justify-center my-auto">
        {data.length === 0 ? (
          <div className="text-center text-xs text-slate-400">
            No parameter data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip content={<CustomTooltip />} />
              <Pie
                data={data}
                innerRadius={55}
                outerRadius={80}
                paddingAngle={4}
                dataKey="value"
                stroke="none"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        )}

        {/* Center overlay label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl font-black text-slate-900 tracking-tight leading-none font-mono">
            {percentComplete}%
          </span>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-1">
            Complete
          </span>
        </div>
      </div>

      {/* Legend / Breakdown Pills */}
      <div className="pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center">
        <div className="p-2 rounded-lg bg-emerald-50/70 border border-emerald-100">
          <div className="flex items-center justify-center gap-1 text-emerald-800 text-[10px] font-bold uppercase">
            <CheckCircle2 size={11} className="text-emerald-600" />
            <span>Complete</span>
          </div>
          <p className="text-base font-extrabold text-emerald-950 font-mono mt-0.5">
            {completedCount}
          </p>
        </div>

        <div className="p-2 rounded-lg bg-blue-50/70 border border-blue-100">
          <div className="flex items-center justify-center gap-1 text-blue-800 text-[10px] font-bold uppercase">
            <Clock size={11} className="text-blue-600" />
            <span>In Progress</span>
          </div>
          <p className="text-base font-extrabold text-blue-950 font-mono mt-0.5">
            {inProgressCount}
          </p>
        </div>

        <div className="p-2 rounded-lg bg-slate-50 border border-slate-200/70">
          <div className="flex items-center justify-center gap-1 text-slate-600 text-[10px] font-bold uppercase">
            <Circle size={10} className="text-slate-400" />
            <span>Pending</span>
          </div>
          <p className="text-base font-extrabold text-slate-800 font-mono mt-0.5">
            {notStartedCount}
          </p>
        </div>
      </div>
    </div>
  );
}
