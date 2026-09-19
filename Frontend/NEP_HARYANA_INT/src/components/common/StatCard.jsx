import React from "react";

export default function StatCard({
  title,
  value,
  sublabel,
  icon: Icon,
  badge = null,
  trend = null,
  variant = "default", // 'default' | 'blue' | 'emerald' | 'amber' | 'purple'
  className = "",
  onClick = null,
}) {
  const variants = {
    default: {
      bg: "bg-white",
      border: "border-slate-200",
      iconBg: "bg-slate-50 text-slate-600 border-slate-200",
      valColor: "text-slate-900",
    },
    blue: {
      bg: "bg-white",
      border: "border-blue-200",
      iconBg: "bg-blue-50 text-blue-700 border-blue-200",
      valColor: "text-blue-900",
    },
    emerald: {
      bg: "bg-white",
      border: "border-emerald-200",
      iconBg: "bg-emerald-50 text-emerald-700 border-emerald-200",
      valColor: "text-emerald-900",
    },
    amber: {
      bg: "bg-white",
      border: "border-amber-200",
      iconBg: "bg-amber-50 text-amber-700 border-amber-200",
      valColor: "text-amber-900",
    },
    purple: {
      bg: "bg-white",
      border: "border-purple-200",
      iconBg: "bg-purple-50 text-purple-700 border-purple-200",
      valColor: "text-purple-900",
    },
  }[variant] || variants.default;

  const Wrapper = onClick ? "button" : "div";

  return (
    <Wrapper
      onClick={onClick}
      className={`rounded-xl border p-5 text-left shadow-xs transition-all hover:shadow-sm ${variants.bg} ${variants.border} ${
        onClick ? "cursor-pointer hover:border-blue-400" : ""
      } ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider truncate">
              {title}
            </span>
            {badge && <span>{badge}</span>}
          </div>

          <p className={`text-2xl font-extrabold tracking-tight truncate ${variants.valColor}`}>
            {value}
          </p>

          {sublabel && (
            <p className="text-xs text-slate-500 mt-1 truncate">
              {sublabel}
            </p>
          )}

          {trend && (
            <div className="mt-2 text-[11px] font-semibold text-slate-600">
              {trend}
            </div>
          )}
        </div>

        {Icon && (
          <div className={`p-2.5 rounded-lg border shrink-0 ${variants.iconBg}`}>
            <Icon size={20} />
          </div>
        )}
      </div>
    </Wrapper>
  );
}
