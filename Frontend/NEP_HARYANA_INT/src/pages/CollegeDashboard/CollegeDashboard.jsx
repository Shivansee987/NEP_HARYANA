/**
 * CollegeDashboard — NEP Excellence Awards 2026 Institutional Assessment Portal
 *
 * Professional, modern, calm institutional UX pass.
 * Harmonized visually with UniversityDashboard using shared design primitives.
 * Provides dual-access:
 * 1. Statutory NEP 2026 Assessment (C1–C22) consuming /api/v1/college/ and /api/v1/reports/.
 * 2. Legacy Institutional Submissions viewable cleanly without synthetic mappings.
 * Clearly surfaces intentionally unresolved specifications (C5, C7, C8, C16).
 * Zero client-side scoring or synthetic thresholds.
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import {
  fetchMyColleges,
  fetchCollegeAssessments,
  createCollegeAssessment,
  fetchCollegeAssessmentParameters,
  fetchCollegeAssessmentReadiness,
  submitCollegeAssessment,
} from "../../api/college";
import { fetchMySubmissions, fetchNominationDetails } from "../../api/nomination";
import {
  fetchInstitutionReportingSummary,
  downloadAssessmentReportCSV,
} from "../../api/reports";
import AssessmentReportModal from "../../components/Reports/AssessmentReportModal";
import NominationWorkspace from "./NominationWorkspace";
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
  School,
  Award,
  Layers,
  LayoutDashboard,
  CheckSquare,
  LogOut,
  Ban,
  AlertCircle,
  Archive,
} from "lucide-react";
import hshecLogo from "../../assets/hshec_logo.jpeg";
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

const UNRESOLVED_SPEC_PARAMS = {
  C5: "BOUNDARY_UNRESOLVED: Parameter boundary definitions are pending council clarification.",
  C7: "UNRESOLVED_RULE: Applicable statutory evaluation rule is pending resolution.",
  C8: "UNRESOLVED_RULE: Applicable statutory evaluation rule is pending resolution.",
  C16: "UNRESOLVED_RULE: Applicable statutory evaluation rule is pending resolution.",
};

export default function CollegeDashboard() {
  const navigate = useNavigate();
  const { institutionName, institutionAisheCode, formId } = useParams();
  const { user, logout } = useAuth();

  const [activeTab, setActiveTab] = useState("ASSESSMENT"); // 'ASSESSMENT' | 'LEGACY_SUBMISSIONS'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // College Domain Data
  const [college, setCollege] = useState(null);
  const [assessments, setAssessments] = useState([]);
  const [activeAssessment, setActiveAssessment] = useState(null);
  const [parameters, setParameters] = useState([]);
  const [readiness, setReadiness] = useState(null);
  const [reportsSummary, setReportsSummary] = useState(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState(null);
  const [paramFilter, setParamFilter] = useState("ALL"); // 'ALL' | 'COMPLETED' | 'PENDING' | 'BLOCKED'

  // Legacy Nominations State
  const [legacySubmissions, setLegacySubmissions] = useState([]);
  const [legacyLoading, setLegacyLoading] = useState(false);

  const collegeName = college?.name || user?.college_name || "Institutional College";
  const aisheCode = college?.aishe_code || user?.aishe_code || "C-AISHE";

  const loadCollegeData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch authorized college record
      const colResponse = await fetchMyColleges();
      const colList = colResponse?.results || (Array.isArray(colResponse) ? colResponse : []);
      const myCol = colList.length > 0 ? colList[0] : null;

      if (!myCol) {
        setCollege(null);
        setAssessments([]);
        setActiveAssessment(null);
        setParameters([]);
        setReadiness(null);
        return;
      }
      setCollege(myCol);

      // 2. Fetch assessments for this college
      const assessResponse = await fetchCollegeAssessments(myCol.id);
      const assessList = assessResponse?.results || (Array.isArray(assessResponse) ? assessResponse : []);
      setAssessments(assessList);

      if (assessList.length > 0) {
        const latest = assessList[0];
        setActiveAssessment(latest);

        // 3. Fetch parameter metadata and readiness for the active assessment
        const [paramsData, readyData, reportsData] = await Promise.all([
          fetchCollegeAssessmentParameters(latest.assessment_id).catch(() => []),
          fetchCollegeAssessmentReadiness(latest.assessment_id).catch(() => null),
          fetchInstitutionReportingSummary().catch(() => null),
        ]);

        setParameters(Array.isArray(paramsData) ? paramsData : []);
        setReadiness(readyData);
        setReportsSummary(reportsData);
      } else {
        setActiveAssessment(null);
        setParameters([]);
        setReadiness(null);
      }

      setLastRefreshed(new Date());
    } catch (err) {
      console.error("College dashboard data load failed:", err);
      setError(err?.message || "Failed to load institutional college data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCollegeData();
  }, [loadCollegeData]);

  // Load Legacy Submissions when tab selected
  const loadLegacyData = useCallback(async () => {
    setLegacyLoading(true);
    try {
      const data = await fetchMySubmissions();
      setLegacySubmissions(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load legacy submissions:", err);
    } finally {
      setLegacyLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "LEGACY_SUBMISSIONS") {
      loadLegacyData();
    }
  }, [activeTab, loadLegacyData]);

  const handleCreateAssessment = async () => {
    if (!college) return;
    setCreating(true);
    setError(null);
    try {
      await createCollegeAssessment(college.id, { academic_year: "2025-26" });
      await loadCollegeData();
    } catch (err) {
      console.error("Failed to create college assessment:", err);
      setError(err?.message || "Failed to initialize new assessment.");
    } finally {
      setCreating(false);
    }
  };

  const handleSubmitAssessment = async () => {
    if (!activeAssessment) return;
    if (
      !window.confirm(
        "Are you sure you want to formally submit this assessment for Screening Committee evaluation? Once submitted, parameter inputs are locked."
      )
    ) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await submitCollegeAssessment(activeAssessment.assessment_id);
      await loadCollegeData();
    } catch (err) {
      console.error("Submission failed:", err);
      setError(err?.message || "College assessment submission rejected by validation rules.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/auth/login");
  };

  // Metrics (server-authoritative)
  const completedParameters = parameters.filter((p) => p.submitted_input != null && Object.keys(p.submitted_input).length > 0).length;
  const totalParameters = parameters.length || 22;
  const coveredSubcriteria = readiness?.evidence_readiness_summary?.covered_subcriteria ?? 0;
  const totalSubcriteria = readiness?.evidence_readiness_summary?.total_subcriteria ?? 45;
  const isReadyForScoring = readiness?.is_ready ?? false;

  const filteredParameters = parameters.filter((p) => {
    const isComplete = p.submitted_input != null && Object.keys(p.submitted_input).length > 0;
    const isUnresolved = Boolean(UNRESOLVED_SPEC_PARAMS[p.parameter_code]);
    if (paramFilter === "COMPLETED") return isComplete;
    if (paramFilter === "PENDING") return !isComplete;
    if (paramFilter === "BLOCKED") return isUnresolved;
    return true;
  });

  // Render Legacy Nomination Workspace if route has formId
  if (formId) {
    const collegeNameSlug = String(user?.college_name || "college").toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const collegeAisheSlug = String(user?.aishe_code || "code").toLowerCase().replace(/[^a-z0-9]+/g, "-");
    return (
      <NominationWorkspace
        formId={formId}
        onBack={() => navigate(`/institution/${institutionName || collegeNameSlug}/${institutionAisheCode || collegeAisheSlug}/dashboard`)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Application Bar */}
      <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-40 px-4 sm:px-6 h-14 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <img src={hshecLogo} alt="HSHEC" className="w-8 h-8 rounded object-contain bg-white p-0.5" />
          <div>
            <span className="text-xs font-bold tracking-tight text-white block leading-none">
              NEP Excellence Awards 2026
            </span>
            <span className="text-[10px] text-blue-400 font-semibold uppercase tracking-wider">
              College Principal Portal
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <p className="text-xs font-bold text-slate-200 leading-none">{collegeName}</p>
            <p className="text-[10px] text-slate-400 font-mono">AISHE: {aisheCode}</p>
          </div>
          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-xs font-semibold transition-colors"
          >
            <LogOut size={13} />
            <span className="hidden sm:inline">Sign Out</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 flex-1">
        {/* Navigation Tabs (Authoritative Assessment vs Legacy Nominations) */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-3 flex-wrap gap-3">
          <div className="inline-flex rounded-xl bg-slate-200/80 p-1 text-xs font-bold text-slate-600">
            <button
              onClick={() => setActiveTab("ASSESSMENT")}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                activeTab === "ASSESSMENT"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "hover:text-slate-900"
              }`}
            >
              <Award size={14} className={activeTab === "ASSESSMENT" ? "text-blue-600" : ""} />
              <span>NEP 2026 Assessment (C1–C22)</span>
            </button>
            <button
              onClick={() => setActiveTab("LEGACY_SUBMISSIONS")}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                activeTab === "LEGACY_SUBMISSIONS"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "hover:text-slate-900"
              }`}
            >
              <Archive size={14} className={activeTab === "LEGACY_SUBMISSIONS" ? "text-blue-600" : ""} />
              <span>Legacy Submissions Archive</span>
            </button>
          </div>

          <button
            onClick={loadCollegeData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>Refresh Data</span>
          </button>
        </div>

        {/* Global Error Notice */}
        {error && (
          <ErrorState
            title="College Portal Notice"
            message={error}
            onRetry={loadCollegeData}
          />
        )}

        {/* TAB 1: AUTHORITATIVE NEP 2026 ASSESSMENT (C1–C22) */}
        {activeTab === "ASSESSMENT" && (
          <>
            {loading && !college ? (
              <DashboardSkeleton />
            ) : !college ? (
              <EmptyState
                icon={School}
                title="No College Profile Assigned"
                description="Your account is not currently linked to an approved college record in the database. Please contact your State DHE Administrator."
              />
            ) : (
              <>
                {/* Institution Identity Banner */}
                <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-blue-950 rounded-2xl p-6 sm:p-8 text-white shadow-lg border border-slate-700/60 flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div>
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-400/30 uppercase tracking-wide">
                        College Principal
                      </span>
                      <span className="text-xs text-slate-300 font-medium">
                        AISHE: {aisheCode}
                      </span>
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-1">
                      {collegeName}
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
                      NEP Excellence Awards 2026 — Statutory self-appraisal parameters (C1–C22), evidence verification gating, and audit ledger.
                    </p>
                  </div>

                  {activeAssessment && (
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => setSelectedAssessmentId(activeAssessment.assessment_id)}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-sm"
                      >
                        <Eye size={13} />
                        <span>Audit Report</span>
                      </button>
                      <button
                        onClick={() => downloadAssessmentReportCSV(activeAssessment.assessment_id)}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-bold transition-all shadow-sm"
                        title="Download authoritative CSV report"
                      >
                        <FileSpreadsheet size={13} />
                        <span>Export CSV</span>
                      </button>
                    </div>
                  )}
                </div>

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
                      No Active College Assessment Session for 2025-26
                    </h3>
                    <p className="text-xs text-slate-500 max-w-md mx-auto mb-4">
                      Initialize your college’s appraisal workspace to record inputs for C1–C22 and submit documentary evidence.
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
                    value={activeAssessment?.framework || "COLLEGE_2026"}
                    sublabel={`AY ${activeAssessment?.academic_year || "2025-26"}`}
                    icon={School}
                    variant="purple"
                  />
                </div>

                {/* Unresolved College Specifications Notice */}
                <BlockingNotice
                  type="spec_blocked"
                  title="Statutory Notice: Pending Council Specifications (C5, C7, C8, C16)"
                  reasons={[
                    "C5 (Institutional Development Plan) has an unresolved boundary rule awaiting council notification.",
                    "C7 (NAAC Accreditation), C8 (National Credit Framework), and C16 (Gender Parity) criteria rules are pending resolution.",
                    "These specific parameters cannot be evaluated until the applicable specifications are finalized by the council.",
                  ]}
                />

                {/* Primary Next Action Banner */}
                {activeAssessment && (
                  <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                        Primary Next Action
                      </span>
                      {activeAssessment.status === "DRAFT" ? (
                        <div>
                          <h4 className="text-sm font-bold text-slate-900">
                            Complete Parameter Inputs and Submit Assessment
                          </h4>
                          <p className="text-xs text-slate-500">
                            Submit your self-appraisal to the Screening Committee for independent evidence verification and scoring.
                          </p>
                        </div>
                      ) : activeAssessment.status === "SUBMITTED" ? (
                        <div>
                          <h4 className="text-sm font-bold text-blue-950 flex items-center gap-1.5">
                            <Clock size={14} className="text-blue-600" />
                            Submitted for Screening Committee Evaluation
                          </h4>
                          <p className="text-xs text-slate-500">
                            Inputs are locked. Assigned committee reviewers are evaluating documentary evidence.
                          </p>
                        </div>
                      ) : (
                        <div>
                          <h4 className="text-sm font-bold text-emerald-950 flex items-center gap-1.5">
                            <ShieldCheck size={14} className="text-emerald-600" />
                            Assessment Certified
                          </h4>
                          <p className="text-xs text-slate-500">
                            Official evaluation and score certification finalized.
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
                          <span>{submitting ? "Submitting..." : "Submit Assessment"}</span>
                        </button>
                      )}

                      <button
                        onClick={() => setSelectedAssessmentId(activeAssessment.assessment_id)}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold transition-colors shadow-xs"
                      >
                        <Eye size={13} />
                        <span>Audit Preview</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* Evidence Readiness Summary */}
                {activeAssessment && readiness && (
                  <EvidenceReadinessSummary
                    summary={readiness.evidence_readiness_summary}
                    isReady={readiness.is_ready}
                    onActionClick={() => setSelectedAssessmentId(activeAssessment.assessment_id)}
                  />
                )}

                {/* Statutory Parameters Table (C1–C22) */}
                {parameters.length > 0 && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
                    <div className="p-4 sm:p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
                      <div>
                        <h2 className="text-sm font-bold text-slate-900 tracking-tight">
                          Statutory Parameters (C1–C22)
                        </h2>
                        <p className="text-xs text-slate-500">
                          Authoritative parameters registered under COLLEGE_2026 framework
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
                        <button
                          onClick={() => setParamFilter("BLOCKED")}
                          className={`px-3 py-1 rounded-md transition-all ${
                            paramFilter === "BLOCKED" ? "bg-purple-600 text-white shadow-xs" : "hover:text-slate-900"
                          }`}
                        >
                          Spec Blocked (4)
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
                            <th className="py-3 px-4">Specification & Blocking Notice</th>
                            <th className="py-3 px-4 text-center">Input Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {filteredParameters.map((param) => {
                            const isComplete = param.submitted_input != null && Object.keys(param.submitted_input).length > 0;
                            const unresolvedNotice = UNRESOLVED_SPEC_PARAMS[param.parameter_code];

                            return (
                              <tr
                                key={param.parameter_code}
                                className="hover:bg-slate-50/80 transition-colors"
                              >
                                <td className="py-3.5 px-4 font-mono font-bold text-blue-700 whitespace-nowrap">
                                  {param.parameter_code}
                                </td>
                                <td className="py-3.5 px-4 font-medium text-slate-900 max-w-sm">
                                  {param.title}
                                </td>
                                <td className="py-3.5 px-4 text-center font-bold text-slate-700 whitespace-nowrap">
                                  {param.max_marks} pts
                                </td>
                                <td className="py-3.5 px-4 text-slate-600 max-w-md">
                                  {unresolvedNotice ? (
                                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-purple-50 text-purple-800 border border-purple-200 text-[11px] font-medium">
                                      <Ban size={12} className="text-purple-600 shrink-0" />
                                      <span>{unresolvedNotice}</span>
                                    </div>
                                  ) : param.mandatory_evidence && param.mandatory_evidence.length > 0 ? (
                                    <span className="text-[11px] text-slate-600">
                                      Requires {param.mandatory_evidence.length} documentary evidence type(s)
                                    </span>
                                  ) : (
                                    <span className="text-slate-400 italic text-[11px]">No special blocker</span>
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
          </>
        )}

        {/* TAB 2: LEGACY SUBMISSIONS ARCHIVE */}
        {activeTab === "LEGACY_SUBMISSIONS" && (
          <div className="space-y-4">
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900">
              <div className="flex items-center gap-2 font-bold mb-1 text-sm text-amber-950">
                <AlertCircle size={15} />
                <span>Historical Submissions Archive</span>
              </div>
              <p>
                These records belong to the previous institutional nomination portal. They are preserved for historical audit purposes and are strictly isolated from the NEP Excellence Awards 2026 scoring framework.
              </p>
            </div>

            {legacyLoading ? (
              <DashboardSkeleton />
            ) : legacySubmissions.length === 0 ? (
              <EmptyState
                icon={Archive}
                title="No Historical Nominations"
                description="No historical submissions exist for your institution in the archive."
              />
            ) : (
              <div className="grid gap-4">
                {legacySubmissions.map((sub) => (
                  <div
                    key={sub.id}
                    className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-[10px] font-mono font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded uppercase">
                          ID: {sub.form_id}
                        </span>
                        <StatusBadge status={sub.is_submitted ? "SUBMITTED" : "DRAFT"} size="sm" />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">
                        {sub.form_id === "nep-excellence-nomination-2025"
                          ? "Haryana State NEP Implementation Award — Nomination Form 2025"
                          : "Institutional Nomination Record"}
                      </h4>
                      <p className="text-xs text-slate-500 mt-1">
                        Updated: {new Date(sub.updated_at).toLocaleDateString()} · Head: {sub.head_name || "N/A"}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() =>
                          navigate(
                            `/institution/${institutionName || "college"}/${institutionAisheCode || "aishe"}/dashboard/forms/${sub.form_id}`
                          )
                        }
                        className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-xs font-semibold transition-colors"
                      >
                        {sub.is_submitted ? "View Record" : "Continue Form"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Authoritative Assessment Report Modal */}
      {selectedAssessmentId && (
        <AssessmentReportModal
          assessmentId={selectedAssessmentId}
          onClose={() => setSelectedAssessmentId(null)}
        />
      )}
    </div>
  );
}