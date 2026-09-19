import React from "react";
import { AlertCircle, RotateCcw } from "lucide-react";

export function EmptyState({
  icon: Icon = AlertCircle,
  title,
  description,
  actionLabel = null,
  onAction = null,
  className = "",
}) {
  return (
    <div className={`bg-white border border-slate-200 rounded-xl p-8 sm:p-12 text-center max-w-lg mx-auto ${className}`}>
      <div className="w-12 h-12 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center mx-auto mb-4 text-slate-500">
        <Icon size={24} />
      </div>
      <h4 className="text-base font-bold text-slate-800 mb-1.5">{title}</h4>
      <p className="text-xs text-slate-500 leading-relaxed max-w-sm mx-auto mb-5">{description}</p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-colors shadow-xs"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export function ErrorState({
  title = "Unable to load data",
  message = "An error occurred while communicating with the server. Please verify your connection or try again.",
  onRetry = null,
  className = "",
}) {
  return (
    <div
      role="alert"
      className={`bg-red-50 border border-red-200 rounded-xl p-6 text-center max-w-lg mx-auto ${className}`}
    >
      <div className="w-10 h-10 rounded-full bg-red-100 border border-red-200 flex items-center justify-center mx-auto mb-3 text-red-600">
        <AlertCircle size={20} />
      </div>
      <h4 className="text-sm font-bold text-red-900 mb-1">{title}</h4>
      <p className="text-xs text-red-700 leading-relaxed mb-4">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold transition-colors shadow-xs"
        >
          <RotateCcw size={13} />
          <span>Try Again</span>
        </button>
      )}
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header Skeleton */}
      <div className="h-32 bg-slate-200 rounded-2xl" />

      {/* Stepper Skeleton */}
      <div className="h-20 bg-slate-200 rounded-xl" />

      {/* KPI Grid Skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((n) => (
          <div key={n} className="h-28 bg-slate-200 rounded-xl" />
        ))}
      </div>

      {/* Main Table Skeleton */}
      <div className="h-80 bg-slate-200 rounded-xl" />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden animate-pulse">
      <div className="p-4 border-b border-slate-100 h-12 bg-slate-50" />
      <div className="divide-y divide-slate-100">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="p-4 flex items-center justify-between gap-4">
            <div className="h-4 bg-slate-200 rounded w-1/4" />
            <div className="h-4 bg-slate-200 rounded w-1/3" />
            <div className="h-4 bg-slate-200 rounded w-1/6" />
          </div>
        ))}
      </div>
    </div>
  );
}
