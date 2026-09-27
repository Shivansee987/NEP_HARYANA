import React from "react";
import ParameterCompletionChart from "./ParameterCompletionChart";
import EvidenceCoverageChart from "./EvidenceCoverageChart";
import ParameterWiseProgress from "./ParameterWiseProgress";
import ScoreDistributionChart from "./ScoreDistributionChart";

export default function AssessmentAnalyticsSection({
  framework = "COLLEGE_2026",
  assessment = {},
  parameterCodes = [],
  parameterTitles = {},
  parameterStatusMap = {},
  evidenceAssociations = [],
  readiness = null,
  scoresData = null,
  onNavigateToParam = null,
}) {
  const totalCount = parameterCodes.length || 22;

  const completedCount = parameterCodes.filter(
    (code) => parameterStatusMap[code] === "COMPLETE"
  ).length;

  const inProgressCount = parameterCodes.filter(
    (code) => parameterStatusMap[code] === "IN_PROGRESS"
  ).length;

  const notStartedCount = totalCount - completedCount - inProgressCount;

  // Extract evidence summary
  const totalSubcriteria =
    readiness?.evidence_readiness_summary?.total_subcriteria ?? 45;
  const coveredSubcriteria =
    readiness?.evidence_readiness_summary?.covered_subcriteria ??
    (evidenceAssociations ? new Set(evidenceAssociations.map((a) => a.subcriterion_id)).size : 0);
  const verifiedSubcriteria =
    readiness?.evidence_readiness_summary?.verified_subcriteria ?? 0;
  const pendingSubcriteria =
    readiness?.evidence_readiness_summary?.pending_subcriteria ??
    Math.max(0, coveredSubcriteria - verifiedSubcriteria);
  const isReadyForScoring = readiness?.is_ready ?? false;

  // Check if scores data is available
  const hasScores =
    scoresData &&
    scoresData.parameter_scores &&
    scoresData.parameter_scores.length > 0 &&
    scoresData.scoring_status !== "NOT_EVALUATED";

  return (
    <div className="space-y-6 pt-2">
      <div className="border-t border-slate-200/80 pt-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full uppercase tracking-wider">
                Live Data Analytics
              </span>
              <span className="text-xs text-slate-400">•</span>
              <span className="text-xs font-mono text-slate-500">
                Authoritative Session: {assessment?.assessment_id || "Active"}
              </span>
            </div>
            <h2 className="text-base sm:text-lg font-extrabold text-slate-900 tracking-tight">
              Assessment Analytics & Visual Health
            </h2>
          </div>
        </div>

        {/* 2x2 or 1-col Layout */}
        <div className="space-y-6">
          {/* Row 1: Donut & Evidence bar */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ParameterCompletionChart
              completedCount={completedCount}
              inProgressCount={inProgressCount}
              notStartedCount={notStartedCount}
              totalCount={totalCount}
            />

            <EvidenceCoverageChart
              coveredCount={coveredSubcriteria}
              uncoveredCount={Math.max(0, totalSubcriteria - coveredSubcriteria)}
              verifiedCount={verifiedSubcriteria}
              pendingVerificationCount={pendingSubcriteria}
              totalSubcriteria={totalSubcriteria}
              isReadyForScoring={isReadyForScoring}
            />
          </div>

          {/* Row 2: Full-Width 22 Parameters Grid */}
          <ParameterWiseProgress
            parameterCodes={parameterCodes}
            parameterTitles={parameterTitles}
            parameterStatusMap={parameterStatusMap}
            evidenceAssociations={evidenceAssociations}
            onNavigateToParam={onNavigateToParam}
          />

          {/* Row 3: Score distribution (rendered only if score is evaluated by backend) */}
          {hasScores && (
            <div className="grid grid-cols-1 gap-6">
              <ScoreDistributionChart
                parameterScores={scoresData.parameter_scores}
                scoringStatus={scoresData.scoring_status}
                totalObtained={scoresData.final_certified_total || scoresData.raw_total}
                maxMarks={scoresData.max_marks || 100}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
