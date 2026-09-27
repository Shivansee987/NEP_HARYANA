import React from "react";
import ReviewStatusOverviewChart from "./ReviewStatusOverviewChart";
import InstitutionsByFrameworkChart from "./InstitutionsByFrameworkChart";
import AssessmentProgressDistribution from "./AssessmentProgressDistribution";
import SubmissionReviewActivityChart from "./SubmissionReviewActivityChart";
import EvidenceVerificationOverviewChart from "./EvidenceVerificationOverviewChart";
import ReviewerWorkloadChart from "./ReviewerWorkloadChart";

export default function CheckerQueueAnalyticsSection({
  queueItems = [],
  totalCount = 0,
}) {
  const total = totalCount || queueItems.length;

  // Check if reviewer assignments exist
  const hasReviewerAssignments = queueItems.some((i) => Boolean(i.assigned_reviewer_name));

  return (
    <div className="space-y-6 pt-2">
      <div className="border-t border-[#ebdcd0] pt-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold text-[#600b0b] bg-[#eaded2] border border-[#ebdcd0] px-2.5 py-0.5 rounded-full uppercase tracking-wider font-mono">
                Statutory Intelligence
              </span>
              <span className="text-xs text-slate-300">•</span>
              <span className="text-xs font-mono text-slate-500">
                Live Queue Metrics ({total} total HEIs)
              </span>
            </div>
            <h2 className="text-base sm:text-lg font-extrabold text-slate-900 tracking-tight">
              Screening Committee Queue Analytics & Audit Visuals
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Live aggregated telemetry derived directly from authoritative review queue and evidence verification records.
            </p>
          </div>
        </div>

        {/* Section Layout */}
        <div className="space-y-6">
          {/* Row 1: Review Status Overview & Institutions by Framework */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ReviewStatusOverviewChart
              queueItems={queueItems}
              totalCount={total}
            />
            <InstitutionsByFrameworkChart
              queueItems={queueItems}
              totalCount={total}
            />
          </div>

          {/* Row 2: Assessment Progress / Lifecycle Distribution */}
          <AssessmentProgressDistribution
            queueItems={queueItems}
            totalCount={total}
          />

          {/* Row 3: Evidence Verification & Review Activity / Workload */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <EvidenceVerificationOverviewChart
              queueItems={queueItems}
            />
            <SubmissionReviewActivityChart
              queueItems={queueItems}
            />
          </div>

          {/* Row 4: Reviewer Workload (Rendered only if assignments are present) */}
          {hasReviewerAssignments && (
            <div className="grid grid-cols-1 gap-6">
              <ReviewerWorkloadChart
                queueItems={queueItems}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
