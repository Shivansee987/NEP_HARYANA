import React from "react";
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  AlertTriangle,
  ShieldCheck,
  RotateCcw,
  Ban,
  FileEdit,
} from "lucide-react";

/**
 * Authoritative Status Configuration
 * Provides text, icon, and distinct semantic colors (both dark text and background/border)
 * so status is NEVER communicated by color alone.
 */
const STATUS_CONFIGS = {
  DRAFT: {
    label: "Draft",
    icon: FileEdit,
    badgeClass: "bg-slate-100 text-slate-700 border-slate-300",
    iconColor: "text-slate-500",
  },
  SUBMITTED: {
    label: "Submitted",
    icon: Clock,
    badgeClass: "bg-blue-50 text-blue-800 border-blue-200",
    iconColor: "text-blue-600",
  },
  UNDER_REVIEW: {
    label: "Under Review",
    icon: RotateCcw,
    badgeClass: "bg-amber-50 text-amber-800 border-amber-200",
    iconColor: "text-amber-600",
  },
  RETURNED: {
    label: "Returned for Correction",
    icon: AlertTriangle,
    badgeClass: "bg-orange-50 text-orange-800 border-orange-200",
    iconColor: "text-orange-600",
  },
  REJECTED: {
    label: "Rejected",
    icon: AlertCircle,
    badgeClass: "bg-red-50 text-red-800 border-red-200",
    iconColor: "text-red-600",
  },
  CERTIFIED: {
    label: "Certified",
    icon: ShieldCheck,
    badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-200",
    iconColor: "text-emerald-600",
  },
  BLOCKED: {
    label: "Blocked",
    icon: Ban,
    badgeClass: "bg-rose-50 text-rose-800 border-rose-200",
    iconColor: "text-rose-600",
  },
  BLOCKED_BY_SPECIFICATION: {
    label: "Blocked by Specification",
    icon: Ban,
    badgeClass: "bg-purple-50 text-purple-800 border-purple-200",
    iconColor: "text-purple-600",
  },
  // Evidence lifecycle specific statuses
  EVIDENCE_PRESENT: {
    label: "Evidence Uploaded",
    icon: Clock,
    badgeClass: "bg-slate-100 text-slate-700 border-slate-200",
    iconColor: "text-slate-500",
  },
  EVIDENCE_PENDING: {
    label: "Pending Verification",
    icon: Clock,
    badgeClass: "bg-amber-50 text-amber-800 border-amber-200",
    iconColor: "text-amber-600",
  },
  EVIDENCE_VERIFIED: {
    label: "Verified & Eligible",
    icon: CheckCircle2,
    badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-200",
    iconColor: "text-emerald-600",
  },
  EVIDENCE_REJECTED: {
    label: "Evidence Rejected",
    icon: AlertCircle,
    badgeClass: "bg-red-50 text-red-800 border-red-200",
    iconColor: "text-red-600",
  },
  NO_EVIDENCE: {
    label: "Missing Evidence",
    icon: AlertCircle,
    badgeClass: "bg-slate-50 text-slate-500 border-slate-200",
    iconColor: "text-slate-400",
  },
};

export default function StatusBadge({
  status,
  size = "md",
  className = "",
  showIcon = true,
  customLabel = null,
}) {
  const normStatus = String(status || "").toUpperCase().trim();
  const config = STATUS_CONFIGS[normStatus] || {
    label: status || "Unknown",
    icon: AlertCircle,
    badgeClass: "bg-slate-100 text-slate-700 border-slate-300",
    iconColor: "text-slate-500",
  };

  const Icon = config.icon;
  const displayText = customLabel || config.label;

  const sizeClasses = {
    sm: "text-[10px] px-2 py-0.5 gap-1",
    md: "text-xs px-2.5 py-1 gap-1.5",
    lg: "text-sm px-3.5 py-1.5 gap-2 font-semibold",
  };

  const iconSizes = {
    sm: 11,
    md: 13,
    lg: 16,
  };

  return (
    <span
      role="status"
      aria-label={`Status: ${displayText}`}
      className={`inline-flex items-center font-medium border rounded-full transition-colors whitespace-nowrap ${sizeClasses[size] || sizeClasses.md} ${config.badgeClass} ${className}`}
    >
      {showIcon && <Icon size={iconSizes[size] || 13} className={`shrink-0 ${config.iconColor}`} aria-hidden="true" />}
      <span>{displayText}</span>
    </span>
  );
}
