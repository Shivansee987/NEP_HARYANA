import React from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from "recharts";
import { Award, AlertCircle } from "lucide-react";

export default function ScoreDistributionChart({
  parameterScores = [],
  scoringStatus = "NOT_EVALUATED",
  totalObtained = null,
  maxMarks = 100,
}) {
  // If scoring has not been evaluated by backend, gracefully return null
  if (!parameterScores || parameterScores.length === 0 || scoringStatus === "NOT_EVALUATED") {
    return null;
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const dataItem = payload[0].payload;
      return (
        <div className="bg-slate-900 text-white p-3 rounded-lg shadow-xl border border-slate-700 text-xs space-y-1">
          <p className="font-bold text-slate-200">{label}: {dataItem.title}</p>
          <div className="flex items-center justify-between gap-4 text-emerald-400 font-mono">
            <span>Obtained Score:</span>
            <span className="font-bold">{dataItem.obtained_score} pts</span>
          </div>
          <div className="flex items-center justify-between gap-4 text-slate-300 font-mono">
            <span>Maximum Marks:</span>
            <span>{dataItem.max_marks} pts</span>
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
            Authoritative Score & Marks Distribution
          </h3>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 uppercase tracking-wider font-mono">
            {totalObtained !== null ? `${totalObtained} / ${maxMarks} pts` : "Evaluated"}
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Authoritative scoring evaluated by the statutory evaluation engine.
        </p>
      </div>

      <div className="h-64 my-auto">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={parameterScores}
            margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
          >
            <XAxis
              dataKey="parameter_code"
              interval={0}
              angle={-45}
              textAnchor="end"
              tick={{ fontSize: 10, fill: "#64748b" }}
            />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
            <Bar dataKey="max_marks" name="Max Possible Marks" fill="#cbd5e1" radius={[3, 3, 0, 0]} />
            <Bar dataKey="obtained_score" name="Certified/Obtained" fill="#10b981" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
