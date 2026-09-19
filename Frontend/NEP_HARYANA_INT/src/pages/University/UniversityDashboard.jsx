/**
 * UniversityDashboard — NEP Excellence Awards 2026 Institutional Assessment Portal
 *
 * Professional, Modern Institutional Grade Dashboard Pass
 * Strictly adheres to server-authoritative scoring, RBAC, tenant isolation, and statutory definitions.
 * Zero client-side score computation.
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
  AlertTriangle,
  ArrowRight,
  Filter,
  Check,
  Calendar,
  Layers,
} from "lucide-react";
import { downloadAssessmentReportCSV } from "../../api/reports";
import AssessmentReportModal from "../../components/Reports/AssessmentReportModal";
import {
  StatusBadge,
  AssessmentStepper,
  EvidenceReadinessSummary,
  BlockingNotice,
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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* 1. Page Header (Clean, Institutional, High-contrast, Uncluttered) */}
      <div className="bg-white rounded-xl border border-slate-200/90 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 uppercase tracking-wider">
              {roleLabel}
            </span>
            <span className="text-xs text-slate-500 font-mono">
              AISHE: {university?.aishe_code || "Registered"}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {university ? university.name : "University Assessment Workspace"}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl leading-relaxed">
            Statutory NEP self-appraisal parameters (U1–U20), documentary evidence verification gating, and formal certification ledger.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold transition-colors shadow-xs disabled:opacity-50"
            title="Refresh authoritative server data"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>

          {activeAssessment && (
            <>
              <button
                onClick={() => setShowReportModal(true)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 text-xs font-bold transition-colors shadow-xs"
              >
                <Eye size={13} className="text-slate-600" />
                <span>Audit Preview</span>
              </button>

              <button
                onClick={() => downloadAssessmentReportCSV(activeAssessment.assessment_id)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-bold transition-colors shadow-xs"
                title="Export official CSV ledger"
              >
                <FileSpreadsheet size={13} />
                <span>Export CSV</span>
              </button>
            </>
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
          {/* 2. Assessment Journey Stepper */}
          {activeAssessment ? (
            <AssessmentStepper
              status={activeAssessment.status}
              isReadyForScoring={isReadyForScoring}
              completedParameters={completedParameters}
              totalParameters={totalParameters}
            />
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-xs">
              <h3 className="text-base font-bold text-slate-900 mb-1">
                No Active Assessment Session for Academic Year 2025-26
              </h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto mb-5 leading-relaxed">
                Initialize your university’s self-appraisal workspace to record parameter inputs U1–U20 and link documentary evidence.
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

          {/* 3. Key Assessment Summary (Unified 4-Metric Grid with consistent typography and badges) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Metric 1: Lifecycle Status */}
            <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Assessment Status
                  </span>
                  <StatusBadge status={activeAssessment?.status || "DRAFT"} size="sm" />
                </div>
                <p className="text-xl font-extrabold text-slate-900 tracking-tight">
                  {activeAssessment?.status || "NOT_STARTED"}
                </p>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-1.5 text-xs text-slate-500 font-mono truncate">
                <Clock size={12} className="text-slate-400 shrink-0" />
                <span className="truncate">{activeAssessment ? activeAssessment.assessment_id : "No Session Active"}</span>
              </div>
            </div>

            {/* Metric 2: Parameters Completed */}
            <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Parameters Filled
                  </span>
                  <span className="text-[11px] font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                    {Math.round((completedParameters / totalParameters) * 100)}%
                  </span>
                </div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
                    {completedParameters}
                  </span>
                  <span className="text-xs font-semibold text-slate-400">
                    / {totalParameters} parameters
                  </span>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-100">
                <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-600 rounded-full transition-all duration-300"
                    style={{ width: `${(completedParameters / totalParameters) * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Metric 3: Evidence Coverage */}
            <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Evidence Coverage
                  </span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${
                      isReadyForScoring
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : "bg-amber-50 text-amber-800 border-amber-200"
                    }`}
                  >
                    {isReadyForScoring ? "Eligible" : "Gating Action"}
                  </span>
                </div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
                    {coveredSubcriteria}
                  </span>
                  <span className="text-xs font-semibold text-slate-400">
                    / {totalSubcriteria} subcriteria
                  </span>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-1.5 text-xs text-slate-500">
                <CheckCircle2 size={12} className={isReadyForScoring ? "text-emerald-600" : "text-amber-500"} />
                <span>{isReadyForScoring ? "Gating thresholds satisfied" : `${totalSubcriteria - coveredSubcriteria} pending proof`}</span>
              </div>
            </div>

            {/* Metric 4: Statutory Framework */}
            <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Statutory Framework
                  </span>
                  <span className="text-[10px] font-bold text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-full">
                    Gated
                  </span>
                </div>
                <p className="text-lg font-extrabold text-slate-900 tracking-tight">
                  {activeAssessment?.framework || "UNIVERSITY_2026"}
                </p>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-1.5 text-xs text-slate-500">
                <Building2 size={12} className="text-slate-400" />
                <span>Academic Period 2025–2026</span>
              </div>
            </div>
          </div>

          {/* 4. Attention & Action Banner (Unified card connecting blocking reasons with next steps) */}
          {activeAssessment && (
            <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[11px] font-bold text-blue-700 uppercase tracking-wider bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                      Recommended Action
                    </span>
                    <span className="text-xs font-semibold text-slate-600">
                      Phase: {activeAssessment.status}
                    </span>
                  </div>
                  {activeAssessment.status === "DRAFT" ? (
                    <h3 className="text-sm sm:text-base font-bold text-slate-900">
                      Complete Parameter Inputs and Submit for Screening
                    </h3>
                  ) : (
                    <h3 className="text-sm sm:text-base font-bold text-slate-900">
                      Assessment Locked for Official Committee Evaluation
                    </h3>
                  )}
                  <p className="text-xs text-slate-500 mt-0.5 max-w-2xl leading-relaxed">
                    {activeAssessment.status === "DRAFT"
                      ? "Ensure all 20 parameter values are recorded and required evidence documents are attached prior to formal submission."
                      : "Independent verification of your documentary evidence is underway by the Screening Committee."}
                  </p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {activeAssessment.status === "DRAFT" && (
                    <button
                      onClick={handleSubmitAssessment}
                      disabled={submitting}
                      className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs disabled:opacity-50"
                    >
                      <Send size={13} />
                      <span>{submitting ? "Submitting..." : "Submit to Committee"}</span>
                    </button>
                  )}

                  <button
                    onClick={() => setShowReportModal(true)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold transition-colors"
                  >
                    <Eye size={13} />
                    <span>View Inspection Report</span>
                  </button>
                </div>
              </div>

              {/* Conditional Alert Inside the Action Card if Gating Requirements Unmet */}
              {activeAssessment.status === "DRAFT" && readiness && !readiness.is_ready && (
                <div className="flex items-start gap-3 p-3.5 bg-amber-50/80 border border-amber-200 rounded-lg text-xs text-amber-900">
                  <AlertTriangle size={16} className="text-amber-600 shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-amber-950 mb-0.5">Evidence Gating Requirements Unmet</p>
                    <p className="text-amber-800 leading-relaxed">
                      {readiness.evidence_readiness_summary?.uncovered_subcriteria ?? 51} subcriteria still require documentary evidence before the evaluation engine will unlock earned marks.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 5. Evidence Readiness Breakdown */}
          {activeAssessment && readiness && (
            <EvidenceReadinessSummary
              summary={readiness.evidence_readiness_summary}
              isReady={readiness.is_ready}
              onActionClick={() => setShowReportModal(true)}
            />
          )}

          {/* 6. Statutory Parameters Table (U1–U20) */}
          {parameters.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
              <div className="p-4 sm:p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/60">
                <div>
                  <h2 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight">
                    Statutory Parameters (U1–U20)
                  </h2>
                  <p className="text-xs text-slate-500">
                    Authoritative parameters under the UNIVERSITY_2026 framework
                    {lastRefreshed && ` · Last verified ${lastRefreshed.toLocaleTimeString()}`}
                  </p>
                </div>

                {/* Filter Tabs */}
                <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 text-xs font-semibold text-slate-600 shadow-2xs">
                  <button
                    onClick={() => setParamFilter("ALL")}
                    className={`px-3 py-1 rounded-md transition-all ${
                      paramFilter === "ALL" ? "bg-slate-900 text-white shadow-xs" : "hover:text-slate-900"
                    }`}
                  >
                    All ({parameters.length})
                  </button>
                  <button
                    onClick={() => setParamFilter("COMPLETED")}
                    className={`px-3 py-1 rounded-md transition-all ${
                      paramFilter === "COMPLETED" ? "bg-slate-900 text-white shadow-xs" : "hover:text-slate-900"
                    }`}
                  >
                    Completed ({completedParameters})
                  </button>
                  <button
                    onClick={() => setParamFilter("PENDING")}
                    className={`px-3 py-1 rounded-md transition-all ${
                      paramFilter === "PENDING" ? "bg-slate-900 text-white shadow-xs" : "hover:text-slate-900"
                    }`}
                  >
                    Pending ({totalParameters - completedParameters})
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      <th className="py-3 px-4 w-16">Code</th>
                      <th className="py-3 px-4">Parameter Title</th>
                      <th className="py-3 px-4 text-center w-28">Max Marks</th>
                      <th className="py-3 px-4">Mandatory Evidence Types</th>
                      <th className="py-3 px-4 text-center w-36">Input Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredParameters.map((param) => {
                      const isComplete = param.submitted_input != null;
                      return (
                        <tr
                          key={param.code}
                          className="hover:bg-slate-50/70 transition-colors"
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
