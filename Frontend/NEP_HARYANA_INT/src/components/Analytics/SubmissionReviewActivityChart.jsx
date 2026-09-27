import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { Calendar, Activity } from "lucide-react";

export default function SubmissionReviewActivityChart({ queueItems = [] }) {
  // Aggregate real timestamps by date (YYYY-MM-DD)
  const activityMap = {};

  queueItems.forEach((item) => {
    if (item.submitted_at) {
      const dateStr = new Date(item.submitted_at).toISOString().split("T")[0];
      if (!activityMap[dateStr]) {
        activityMap[dateStr] = { date: dateStr, submitted: 0, underReview: 0, certified: 0 };
      }
      activityMap[dateStr].submitted += 1;
    } else if (item.created_at) {
      const dateStr = new Date(item.created_at).toISOString().split("T")[0];
      if (!activityMap[dateStr]) {
        activityMap[dateStr] = { date: dateStr, submitted: 0, underReview: 0, certified: 0 };
      }
      activityMap[dateStr].submitted += 1;
    }

    if (item.status === "UNDER_REVIEW") {
      const dateStr = (item.submitted_at || item.created_at || "").split("T")[0];
      if (dateStr) {
        if (!activityMap[dateStr]) {
          activityMap[dateStr] = { date: dateStr, submitted: 0, underReview: 0, certified: 0 };
        }
        activityMap[dateStr].underReview += 1;
      }
    }

    if (item.status === "CERTIFIED" || item.is_certified) {
      const dateStr = (item.submitted_at || item.created_at || "").split("T")[0];
      if (dateStr) {
        if (!activityMap[dateStr]) {
          activityMap[dateStr] = { date: dateStr, submitted: 0, underReview: 0, certified: 0 };
        }
        activityMap[dateStr].certified += 1;
      }
    }
  });

  const data = Object.values(activityMap).sort((a, b) => a.date.localeCompare(b.date));

  // Only render if we have actual timestamp data
  if (data.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-[#ebdcd0] p-5 shadow-xs flex flex-col justify-between h-full">
        <div>
          <div className="flex items-center justify-between gap-2 mb-1">
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">
              Submission & Review Activity
            </h3>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
              Temporal Timeline
            </span>
          </div>
          <p className="text-xs text-slate-500 mb-3">
            Assessments entering the review pipeline over time.
          </p>
        </div>
        <div className="h-52 flex flex-col items-center justify-center text-center p-4">
          <Calendar className="w-8 h-8 text-slate-300 mb-2" />
          <p className="text-xs font-semibold text-slate-600">No submission activity records</p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Timestamped submissions will appear here as institutions submit assessments.
          </p>
        </div>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const formattedDate = new Date(label).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
      return (
        <div className="bg-slate-900 text-white p-3 rounded-xl shadow-xl border border-slate-700 text-xs space-y-1.5">
          <p className="font-bold text-slate-200 flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-amber-400" />
            <span>{formattedDate}</span>
          </p>
          {payload.map((entry, idx) => (
            <div key={`entry-${idx}`} className="flex items-center justify-between gap-4">
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
            Submission & Review Activity
          </h3>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#fdfaf6] text-[#600b0b] border border-[#ebdcd0] font-mono uppercase tracking-wider">
            {data.length} {data.length === 1 ? "Date" : "Dates"}
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Chronological intake and review velocity across Haryana HEIs.
        </p>
      </div>

      <div className="h-52 my-auto">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 20, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: "#64748b" }}
              tickFormatter={(d) => {
                const dateObj = new Date(d);
                return `${dateObj.getDate()} ${dateObj.toLocaleDateString("en-IN", { month: "short" })}`;
              }}
            />
            <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#64748b" }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              iconType="circle"
              wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
            />
            <Line
              type="monotone"
              dataKey="submitted"
              name="Submitted"
              stroke="#d97706"
              strokeWidth={2}
              dot={{ r: 4, fill: "#d97706" }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="underReview"
              name="Under Review"
              stroke="#9333ea"
              strokeWidth={2}
              dot={{ r: 4, fill: "#9333ea" }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="certified"
              name="Certified"
              stroke="#059669"
              strokeWidth={2}
              dot={{ r: 4, fill: "#059669" }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-amber-700" />
          <span>Real-time intake tracking</span>
        </span>
        <span className="font-mono text-slate-700 font-semibold">
          {queueItems.length} total records logged
        </span>
      </div>
    </div>
  );
}
