import React from "react";
import { AlertTriangle, Ban, AlertCircle, Info, ChevronRight } from "lucide-react";

/**
 * BlockingNotice — Prominent Institutional Alert Component
 *
 * Clearly communicates:
 * - WHY am I blocked?
 * - WHAT do I need to do?
 *
 * Supports blocking conditions such as:
 * - Evidence Missing / Unverified
 * - Specification Unresolved (C5, C7, C8, C16)
 * - Certification Blocked
 * - Review Required
 */
export default function BlockingNotice({
  type = "warning", // 'warning' | 'error' | 'info' | 'spec_blocked'
  title,
  reasons = [],
  actionLabel = null,
  onAction = null,
  className = "",
}) {
  const isSpecBlocked = type === "spec_blocked";

  const styles = {
    warning: {
      bg: "bg-amber-50/90 border-amber-300 text-amber-900",
      icon: AlertTriangle,
      iconColor: "text-amber-600",
      badge: "bg-amber-100 text-amber-900 border-amber-300",
    },
    error: {
      bg: "bg-red-50/90 border-red-300 text-red-900",
      icon: AlertCircle,
      iconColor: "text-red-600",
      badge: "bg-red-100 text-red-900 border-red-300",
    },
    spec_blocked: {
      bg: "bg-purple-50/90 border-purple-300 text-purple-900",
      icon: Ban,
      iconColor: "text-purple-600",
      badge: "bg-purple-100 text-purple-900 border-purple-300",
    },
    info: {
      bg: "bg-blue-50/90 border-blue-300 text-blue-900",
      icon: Info,
      iconColor: "text-blue-600",
      badge: "bg-blue-100 text-blue-900 border-blue-300",
    },
  }[type] || {
    bg: "bg-amber-50 border-amber-300 text-amber-900",
    icon: AlertTriangle,
    iconColor: "text-amber-600",
    badge: "bg-amber-100 text-amber-900 border-amber-300",
  };

  const Icon = styles.icon;
  const reasonList = Array.isArray(reasons) ? reasons : [reasons].filter(Boolean);

  return (
    <div
      role="alert"
      className={`rounded-xl border p-4 shadow-sm transition-all ${styles.bg} ${className}`}
    >
      <div className="flex items-start gap-3">
        <div className="p-1 rounded-md shrink-0 mt-0.5">
          <Icon size={18} className={styles.iconColor} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h4 className="text-sm font-bold tracking-tight">{title}</h4>
            {isSpecBlocked && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${styles.badge}`}>
                Specification Unresolved
              </span>
            )}
          </div>

          {reasonList.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs">
              {reasonList.map((reason, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="opacity-60">•</span>
                  <span className="leading-relaxed">{reason}</span>
                </li>
              ))}
            </ul>
          )}

          {actionLabel && onAction && (
            <div className="mt-3">
              <button
                type="button"
                onClick={onAction}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-current rounded-lg text-xs font-bold hover:bg-slate-50 transition-colors shadow-xs"
              >
                <span>{actionLabel}</span>
                <ChevronRight size={13} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
