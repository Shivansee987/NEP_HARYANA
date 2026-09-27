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
  // Evidence and Gating Statuses (Authoritative Enums)
  EVIDENCE_PRESENT: {
    label: "Evidence Available",
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
    label: "Evidence Verified",
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
    label: "Evidence Missing",
    icon: AlertCircle,
    badgeClass: "bg-rose-50 text-rose-700 border-rose-200",
    iconColor: "text-rose-500",
  },
  PENDING_REVIEW: {
    label: "Pending Review",
    icon: Clock,
    badgeClass: "bg-amber-50 text-amber-800 border-amber-200",
    iconColor: "text-amber-600",
  },
  PASSED_EVIDENCE_VERIFIED: {
    label: "Evidence Verified",
    icon: CheckCircle2,
    badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-200",
    iconColor: "text-emerald-600",
  },
  PROVISIONAL_PENDING_VERIFICATION: {
    label: "Pending Verification",
    icon: Clock,
    badgeClass: "bg-amber-50 text-amber-800 border-amber-200",
    iconColor: "text-amber-600",
  },
  FAILED_EVIDENCE_ABSENT: {
    label: "Evidence Missing",
    icon: AlertCircle,
    badgeClass: "bg-rose-50 text-rose-700 border-rose-200",
    iconColor: "text-rose-500",
  },
  FAILED_EVIDENCE_REJECTED: {
    label: "Evidence Rejected",
    icon: AlertCircle,
    badgeClass: "bg-red-50 text-red-800 border-red-200",
    iconColor: "text-red-600",
  },
  NO_EVIDENCE_REQUIRED: {
    label: "Source Silent (No Evidence Required)",
    icon: CheckCircle2,
    badgeClass: "bg-slate-100 text-slate-700 border-slate-200",
    iconColor: "text-slate-500",
  },
};

export const formatGatingStatus = (status) => {
  const norm = String(status || "").toUpperCase().trim();
  const map = {
    PASSED_EVIDENCE_VERIFIED: "Evidence Verified",
    PROVISIONAL_PENDING_VERIFICATION: "Pending Verification",
    FAILED_EVIDENCE_ABSENT: "Evidence Missing",
    FAILED_EVIDENCE_REJECTED: "Evidence Rejected",
    NO_EVIDENCE_REQUIRED: "No Evidence Required",
    EVIDENCE_PRESENT: "Evidence Available",
    EVIDENCE_VERIFIED: "Evidence Verified",
    EVIDENCE_REJECTED: "Evidence Rejected",
    EVIDENCE_PENDING: "Pending Review",
    PENDING_REVIEW: "Pending Review",
    NOT_UPLOADED: "Not Uploaded",
  };
  return map[norm] || norm.replace(/_/g, " ");
};

export const getGatingStatusExplanation = (status) => {
  const norm = String(status || "").toUpperCase().trim();
  switch (norm) {
    case "PASSED_EVIDENCE_VERIFIED":
    case "EVIDENCE_VERIFIED":
      return "Supporting evidence has been verified by the screening committee.";
    case "PROVISIONAL_PENDING_VERIFICATION":
    case "EVIDENCE_PENDING":
    case "PENDING_REVIEW":
    case "EVIDENCE_PRESENT":
      return "Supporting evidence uploaded and awaiting committee verification.";
    case "FAILED_EVIDENCE_ABSENT":
    case "NO_EVIDENCE":
    case "NOT_UPLOADED":
      return "Supporting evidence has not been uploaded for this subcriterion.";
    case "FAILED_EVIDENCE_REJECTED":
    case "EVIDENCE_REJECTED":
      return "Uploaded supporting evidence was inspected and rejected by the reviewer.";
    case "NO_EVIDENCE_REQUIRED":
      return "This subcriterion does not require statutory documentary evidence.";
    default:
      return "";
  }
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
