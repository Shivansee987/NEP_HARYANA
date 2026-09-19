/**
 * UniversityDashboard — NEP Excellence Awards 2026 Institutional Assessment Portal
 *
 * Professional, modern, calm institutional UX pass.
 * Strictly consumes the Phase 6B University institutional API (/api/v1/university/).
 * Does NOT calculate or modify scores client-side.
 * Adheres strictly to tenant isolation and server-authoritative scoring.
 */
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext.jsx";
import {
  fetchMyUniversities,
  fetchUniversityAssessments,
  createUniversityAssessment,
  fetchUniversityAssessmentParameters,
  fetchUniversityAssessmentReadiness,
  submitUniversityAssessment,
} from "../../api/university";
import {
  Building2,
  ClipboardList,
  CheckCircle2,
  Clock,
  RefreshCw,
  FileText,
  ShieldCheck,
  Send,
  PlusCircle,
  FileSpreadsheet,
  Eye,
  Calendar,
  AlertTriangle,
  FileCheck2,
  ExternalLink,
} from "lucide-react";
import { downloadAssessmentReportCSV } from "../../api/reports";
import AssessmentReportModal from "../../components/Reports/AssessmentReportModal";
import {
  StatusBadge,
  AssessmentStepper,
  EvidenceReadinessSummary,
  BlockingNotice,
  StatCard,
  DashboardSkeleton,
  EmptyState,
  ErrorState,
} from "../../components/common";

const ROLE_LABELS = {
  nodal_officer: "University Nodal Officer",
  university_admin: "University Administrator",
};

export default function UniversityDashboard() {
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const [university, setUniversity] = useState(null);
  const [assessments, setAssessments] = useState([]);
  const [activeAssessment, setActiveAssessment] = useState(null);
  const [parameters, setParameters] = useState([]);
  const [readiness, setReadiness] = useState(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const [paramFilter, setParamFilter] = useState("ALL"); // 'ALL' | 'COMPLETED' | 'PENDING'

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch authorized university institution record
      const uniResponse = await fetchMyUniversities();
      const uniList = uniResponse?.results || (Array.isArray(uniResponse) ? uniResponse : []);
      const myUni = uniList.length > 0 ? uniList[0] : null;

      if (!myUni) {
        setUniversity(null);
        setAssessments([]);
        setActiveAssessment(null);
        setParameters([]);
        setReadiness(null);
        return;
      }
      setUniversity(myUni);

      // 2. Fetch assessments for this university
      const assessResponse = await fetchUniversityAssessments(myUni.id);
      const assessList = assessResponse?.results || (Array.isArray(assessResponse) ? assessResponse : []);
      setAssessments(assessList);

      if (assessList.length > 0) {
        const latest = assessList[0];
        setActiveAssessment(latest);

        // 3. Fetch parameter metadata and readiness for the active assessment
        const [paramsData, readyData] = await Promise.all([
          fetchUniversityAssessmentParameters(latest.assessment_id).catch(() => []),
          fetchUniversityAssessmentReadiness(latest.assessment_id).catch(() => null),
        ]);

        setParameters(Array.isArray(paramsData) ? paramsData : []);
        setReadiness(readyData);
      } else {
        setActiveAssessment(null);
        setParameters([]);
        setReadiness(null);
      }

      setLastRefreshed(new Date());
    } catch (err) {
      console.error("University dashboard data load failed:", err);
      setError(err?.message || "Failed to load institutional data. Please check your connection.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const handleCreateAssessment = async () => {
    if (!university) return;
    setCreating(true);
    setError(null);
    try {
      await createUniversityAssessment(university.id, { academic_year: "2025-26" });
      await loadDashboardData();
    } catch (err) {
      console.error("Failed to create assessment:", err);
      setError(err?.message || "Failed to initialize new assessment.");
    } finally {
      setCreating(false);
    }
  };

  const handleSubmitAssessment = async () => {
    if (!activeAssessment) return;
    if (
      !window.confirm(
        "Are you sure you want to formally submit this assessment for Screening Committee evaluation? Once submitted, inputs are locked."
      )
    ) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await submitUniversityAssessment(activeAssessment.assessment_id);
      await loadDashboardData();
    } catch (err) {
      console.error("Submission failed:", err);
      setError(err?.message || "Assessment submission rejected by validation rules.");
    } finally {
      setSubmitting(false);
    }
  };

  const roleLabel = ROLE_LABELS[user?.role] || "Institutional Representative";

  // Compute metrics from actual domain data (no client-side score computation)
  const completedParameters = parameters.filter((p) => p.submitted_input != null).length;
  const totalParameters = parameters.length || 20;
  const coveredSubcriteria = readiness?.evidence_readiness_summary?.covered_subcriteria ?? 0;
  const totalSubcriteria = readiness?.evidence_readiness_summary?.total_subcriteria ?? 51;
  const isReadyForScoring = readiness?.is_ready ?? false;

  const filteredParameters = parameters.filter((p) => {
    const isComplete = p.submitted_input != null;
    if (paramFilter === "COMPLETED") return isComplete;
    if (paramFilter === "PENDING") return !isComplete;
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Institution / Assessment Identity Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-blue-950 rounded-2xl p-6 sm:p-8 text-white shadow-lg border border-slate-700/60 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-400/30 uppercase tracking-wide">
              {roleLabel}
            </span>
            <span className="text-xs text-slate-300 font-medium">
              AISHE: {university?.aishe_code || "Registered"}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-1">
            {university ? university.name : "University Assessment Workspace"}
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
            NEP Excellence Awards 2026 — Self-appraisal parameters (U1–U20), documentary evidence readiness, and statutory certification pipeline.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white/10 hover:bg-white/15 border border-white/20 text-xs font-semibold text-white transition-all shadow-xs disabled:opacity-50"
            title="Refresh authoritative server data"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>

          {activeAssessment && (
            <button
              onClick={() => setShowReportModal(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-sm"
            >
              <Eye size={13} />
              <span>Audit Report</span>
            </button>
          )}
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <ErrorState
          title="Institutional Action Notice"
          message={error}
          onRetry={loadDashboardData}
        />
      )}

      {/* Loading State */}
      {loading && !university ? (
        <DashboardSkeleton />
      ) : !university ? (
        <EmptyState
          icon={Building2}
          title="No University Institution Linked"
          description="Your authenticated account does not currently have an assigned university institution record. Please contact your State DHE Administrator."
        />
      ) : (
        <>
          {/* Assessment Lifecycle Progress Stepper */}
          {activeAssessment ? (
            <AssessmentStepper
              status={activeAssessment.status}
              isReadyForScoring={isReadyForScoring}
              completedParameters={completedParameters}
              totalParameters={totalParameters}
            />
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-6 text-center shadow-xs">
              <h3 className="text-sm font-bold text-slate-900 mb-1">
                No Active Assessment Session for 2025-26
              </h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto mb-4">
                Initialize your university’s self-appraisal workspace to register parameter inputs U1–U20 and link documentary evidence.
              </p>
              <button
                onClick={handleCreateAssessment}
                disabled={creating}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-colors shadow-xs"
              >
                <PlusCircle size={14} />
                <span>{creating ? "Initializing..." : "Start 2025-26 Assessment"}</span>
              </button>
            </div>
          )}

          {/* Key Assessment Summary KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Assessment Status"
              value={activeAssessment ? activeAssessment.status : "NOT_STARTED"}
              sublabel={activeAssessment ? `Session: ${activeAssessment.assessment_id}` : "No active session"}
              badge={<StatusBadge status={activeAssessment?.status || "DRAFT"} size="sm" />}
              icon={activeAssessment?.status === "CERTIFIED" ? ShieldCheck : Clock}
              variant={activeAssessment?.status === "CERTIFIED" ? "emerald" : "blue"}
            />

            <StatCard
              title="Parameters Completed"
              value={`${completedParameters} / ${totalParameters}`}
              sublabel={`${Math.round((completedParameters / totalParameters) * 100)}% inputs recorded`}
              icon={ClipboardList}
              variant="blue"
            />

            <StatCard
              title="Evidence Coverage"
              value={`${coveredSubcriteria} / ${totalSubcriteria}`}
              sublabel={isReadyForScoring ? "Evidence Gating Passed" : "Action Required"}
              badge={
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    isReadyForScoring
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-amber-100 text-amber-800"
                  }`}
                >
                  {isReadyForScoring ? "Eligible" : "Blocked"}
                </span>
              }
              icon={CheckCircle2}
              variant={isReadyForScoring ? "emerald" : "amber"}
            />

            <StatCard
              title="Statutory Framework"
              value={activeAssessment?.framework || "UNIVERSITY_2026"}
              sublabel={`AY ${activeAssessment?.academic_year || "2025-26"}`}
              icon={Building2}
              variant="purple"
            />
          </div>

          {/* Needs Attention / Blocking Notices */}
          {activeAssessment && activeAssessment.status === "DRAFT" && readiness && !readiness.is_ready && (
            <BlockingNotice
              type="warning"
              title="Evidence Gating Requirements Unmet"
              reasons={[
                `${readiness.evidence_readiness_summary?.uncovered_subcriteria ?? 51} subcriteria require documentary evidence before the evaluation engine will unlock earned marks.`,
                "Institutional evidence must be in PDF/image format and fall within the statutory window (2025-07-01 to 2026-06-30).",
              ]}
              actionLabel="View Evidence Breakdown"
              onAction={() => setShowReportModal(true)}
            />
          )}

          {/* Primary Next Action Banner */}
          {activeAssessment && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  Primary Next Step
                </span>
                {activeAssessment.status === "DRAFT" ? (
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      Complete Parameter Inputs and Submit Assessment
                    </h4>
                    <p className="text-xs text-slate-500">
                      Once submitted to the Screening Committee, your appraisal is locked for independent reviewer evaluation.
                    </p>
                  </div>
                ) : activeAssessment.status === "SUBMITTED" ? (
                  <div>
                    <h4 className="text-sm font-bold text-blue-950 flex items-center gap-1.5">
                      <Clock size={14} className="text-blue-600" />
                      Submitted for Screening Committee Evaluation
                    </h4>
                    <p className="text-xs text-slate-500">
                      Inputs are locked. The designated reviewers are verifying documentary evidence.
                    </p>
                  </div>
                ) : (
                  <div>
                    <h4 className="text-sm font-bold text-emerald-950 flex items-center gap-1.5">
                      <ShieldCheck size={14} className="text-emerald-600" />
                      Assessment Evaluated & Certified
                    </h4>
                    <p className="text-xs text-slate-500">
                      Official scoring and audit reports are finalized.
                    </p>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2.5 shrink-0">
                {activeAssessment.status === "DRAFT" && (
                  <button
                    onClick={handleSubmitAssessment}
                    disabled={submitting}
                    className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm disabled:opacity-50"
                  >
                    <Send size={13} />
                    <span>{submitting ? "Submitting..." : "Submit to Screening Committee"}</span>
                  </button>
                )}

                <button
                  onClick={() => setShowReportModal(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold transition-colors shadow-xs"
                >
                  <Eye size={13} />
                  <span>Audit Preview</span>
                </button>

                <button
                  onClick={() => downloadAssessmentReportCSV(activeAssessment.assessment_id)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-bold transition-colors shadow-xs"
                  title="Export official CSV ledger"
                >
                  <FileSpreadsheet size={13} />
                  <span>Export CSV</span>
                </button>
              </div>
            </div>
          )}

          {/* Evidence Readiness Summary */}
          {activeAssessment && readiness && (
            <EvidenceReadinessSummary
              summary={readiness.evidence_readiness_summary}
              isReady={readiness.is_ready}
              onActionClick={() => setShowReportModal(true)}
            />
          )}

          {/* Statutory Parameters Table (U1–U20) */}
          {parameters.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="p-4 sm:p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 tracking-tight">
                    Statutory Parameters (U1–U20)
                  </h2>
                  <p className="text-xs text-slate-500">
                    Authoritative parameters registered under UNIVERSITY_2026 framework
                    {lastRefreshed && ` · Synced at ${lastRefreshed.toLocaleTimeString()}`}
                  </p>
                </div>

                {/* Filter Tabs */}
                <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 text-xs font-semibold text-slate-600">
                  <button
                    onClick={() => setParamFilter("ALL")}
                    className={`px-3 py-1 rounded-md transition-all ${
                      paramFilter === "ALL" ? "bg-blue-600 text-white shadow-xs" : "hover:text-slate-900"
                    }`}
                  >
                    All ({parameters.length})
                  </button>
                  <button
                    onClick={() => setParamFilter("COMPLETED")}
                    className={`px-3 py-1 rounded-md transition-all ${
                      paramFilter === "COMPLETED" ? "bg-blue-600 text-white shadow-xs" : "hover:text-slate-900"
                    }`}
                  >
                    Completed ({completedParameters})
                  </button>
                  <button
                    onClick={() => setParamFilter("PENDING")}
                    className={`px-3 py-1 rounded-md transition-all ${
                      paramFilter === "PENDING" ? "bg-blue-600 text-white shadow-xs" : "hover:text-slate-900"
                    }`}
                  >
                    Pending ({totalParameters - completedParameters})
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-100 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-3 px-4">Code</th>
                      <th className="py-3 px-4">Parameter Title</th>
                      <th className="py-3 px-4 text-center">Max Marks</th>
                      <th className="py-3 px-4">Mandatory Evidence Types</th>
                      <th className="py-3 px-4 text-center">Input Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredParameters.map((param) => {
                      const isComplete = param.submitted_input != null;
                      return (
                        <tr
                          key={param.code}
                          className="hover:bg-slate-50/80 transition-colors"
                        >
                          <td className="py-3.5 px-4 font-mono font-bold text-blue-700 whitespace-nowrap">
                            {param.code}
                          </td>
                          <td className="py-3.5 px-4 font-medium text-slate-900 max-w-md">
                            {param.title}
                          </td>
                          <td className="py-3.5 px-4 text-center font-bold text-slate-700 whitespace-nowrap">
                            {param.max_marks} pts
                          </td>
                          <td className="py-3.5 px-4 text-slate-600">
                            {param.mandatory_evidence && param.mandatory_evidence.length > 0 ? (
                              <div className="flex items-center gap-1.5 flex-wrap">
                                {param.mandatory_evidence.map((evType, idx) => (
                                  <span
                                    key={idx}
                                    className="text-[10px] font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200"
                                  >
                                    {evType}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-slate-400 italic">None specified</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-center whitespace-nowrap">
                            <span
                              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                                isComplete
                                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                  : "bg-amber-50 text-amber-800 border-amber-200"
                              }`}
                            >
                              {isComplete ? (
                                <>
                                  <CheckCircle2 size={11} className="text-emerald-600" />
                                  <span>Recorded</span>
                                </>
                              ) : (
                                <>
                                  <Clock size={11} className="text-amber-600" />
                                  <span>Pending Data</span>
                                </>
                              )}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Authoritative Assessment Report Modal */}
      {showReportModal && activeAssessment && (
        <AssessmentReportModal
          assessmentId={activeAssessment.assessment_id}
          onClose={() => setShowReportModal(false)}
        />
      )}
    </div>
  );
}
