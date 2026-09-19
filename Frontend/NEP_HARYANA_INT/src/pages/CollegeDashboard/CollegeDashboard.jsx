/**
 * CollegeDashboard — NEP Excellence Awards 2026 Institutional Assessment Portal
 *
 * Clean Full-Height Dashboard with Persistent Sidebar Navigation.
 * Top dark header removed in favor of integrated sidebar branding and user profile.
 * Proper visual hierarchy, crisp layout, and human-friendly spacing.
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
import { fetchMySubmissions } from "../../api/nomination";
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
  LayoutDashboard,
  LogOut,
  Ban,
  AlertCircle,
  Archive,
  Menu,
  X,
  ChevronRight,
  AlertTriangle,
  User,
} from "lucide-react";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import {
  StatusBadge,
  AssessmentStepper,
  EvidenceReadinessSummary,
  BlockingNotice,
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

  // Navigation & View state
  const [activeSection, setActiveSection] = useState("overview"); // 'overview' | 'parameters' | 'evidence' | 'reports' | 'legacy'
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Data state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const [college, setCollege] = useState(null);
  const [assessments, setAssessments] = useState([]);
  const [activeAssessment, setActiveAssessment] = useState(null);
  const [parameters, setParameters] = useState([]);
  const [readiness, setReadiness] = useState(null);
  const [reportsSummary, setReportsSummary] = useState(null);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState(null);
  const [paramFilter, setParamFilter] = useState("ALL"); // 'ALL' | 'COMPLETED' | 'PENDING' | 'BLOCKED'

  // Legacy Nominations State
  const [legacySubmissions, setLegacySubmissions] = useState([]);
  const [legacyLoading, setLegacyLoading] = useState(false);

  const collegeName = college?.name || user?.college_name || "Government College, Sector 14, Gurugram";
  const aisheCode = college?.aishe_code || user?.aishe_code || "C-23456";

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

  // Load Legacy Submissions when legacy section selected
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
    if (activeSection === "legacy") {
      loadLegacyData();
    }
  }, [activeSection, loadLegacyData]);

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

  // Sidebar navigation items
  const navItems = [
    { id: "overview", label: "Dashboard Overview", icon: LayoutDashboard, badge: null },
    { id: "parameters", label: "Parameters (C1–C22)", icon: ClipboardList, badge: `${completedParameters}/${totalParameters}` },
    { id: "evidence", label: "Evidence Readiness", icon: CheckCircle2, badge: isReadyForScoring ? "Ready" : "Action" },
    { id: "reports", label: "Audit Reports", icon: FileSpreadsheet, badge: null },
    { id: "legacy", label: "Historical Archive", icon: Archive, badge: null },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex font-sans antialiased text-slate-800">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-40 lg:hidden"
        />
      )}

      {/* Modern, Clean Institutional Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 inset-y-0 left-0 w-64 bg-white border-r border-slate-200/90 z-50 flex flex-col justify-between transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full lg:shadow-none"
        } h-screen`}
      >
        {/* Top: Branding & Logo */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="h-16 px-4 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-slate-50 border border-slate-200/80 p-1 flex items-center justify-center shrink-0">
                <img src={hshecLogo} alt="HSHEC" className="w-full h-full object-contain" />
              </div>
              <div className="min-w-0">
                <h1 className="text-xs font-bold text-slate-900 leading-tight truncate">
                  NEP Excellence Awards
                </h1>
                <span className="text-[10px] font-bold text-blue-600 tracking-wider uppercase block">
                  Principal Portal
                </span>
              </div>
            </div>

            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-slate-400 hover:text-slate-600 p-1 rounded-md"
            >
              <X size={18} />
            </button>
          </div>

          {/* Logged Institution Profile Badge */}
          <div className="p-3 mx-3 my-3 bg-slate-50/80 border border-slate-200/70 rounded-xl shrink-0">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest block mb-1">
              Affiliated Institution
            </span>
            <p className="text-xs font-bold text-slate-900 leading-snug line-clamp-2" title={collegeName}>
              {collegeName}
            </p>
            <div className="flex items-center gap-1.5 mt-2 flex-wrap">
              <span className="text-[10px] font-mono font-bold bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">
                AISHE: {aisheCode}
              </span>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                COLLEGE_2026
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="px-3 space-y-1 overflow-y-auto flex-1 py-1">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-wider px-3 py-1">
              Assessment Modules
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveSection(item.id);
                    setSidebarOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold transition-all text-left cursor-pointer ${
                    isActive
                      ? "bg-blue-600 text-white shadow-xs"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Icon size={15} className={isActive ? "text-white" : "text-slate-400 shrink-0"} />
                    <span className="truncate">{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                        isActive
                          ? "bg-white/20 text-white"
                          : "bg-slate-100 text-slate-600 border border-slate-200/60"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom: Principal Profile & Sign Out */}
        <div className="p-3 border-t border-slate-100 bg-slate-50/50 shrink-0">
          <div className="flex items-center gap-2 p-2 rounded-lg bg-white border border-slate-200/70 mb-2">
            <div className="w-7 h-7 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700 shrink-0 font-bold text-xs">
              <User size={14} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold text-slate-800 truncate">
                {user?.full_name || "College Principal"}
              </p>
              <p className="text-[10px] text-slate-400 truncate">Principal Authority</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 border border-transparent hover:border-red-100 rounded-lg transition-colors cursor-pointer"
          >
            <LogOut size={13} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Mobile Header Bar */}
        <div className="lg:hidden h-14 bg-white border-b border-slate-200 px-4 flex items-center justify-between sticky top-0 z-30 shadow-xs">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-1.5 rounded-lg text-slate-600 hover:bg-slate-100"
              aria-label="Open sidebar"
            >
              <Menu size={20} />
            </button>
            <span className="text-xs font-bold text-slate-800 truncate">
              {collegeName}
            </span>
          </div>

          <button
            onClick={handleLogout}
            className="text-xs text-red-600 font-semibold p-1.5"
          >
            Sign Out
          </button>
        </div>

        {/* Inner Content Body */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-6xl w-full mx-auto space-y-6">
          {/* Top Page Summary Bar with Context Actions */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 uppercase tracking-wider">
                  College Principal Workspace
                </span>
                <span className="text-slate-300">•</span>
                <span className="text-xs text-slate-500 font-mono">
                  Session: {activeAssessment ? activeAssessment.assessment_id : "No Session"}
                </span>
              </div>
              <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                {activeSection === "overview" && "Assessment Overview & Health"}
                {activeSection === "parameters" && "Statutory Parameters (C1–C22)"}
                {activeSection === "evidence" && "Documentary Evidence Readiness"}
                {activeSection === "reports" && "Official Audit & Assessment Reports"}
                {activeSection === "legacy" && "Historical Submissions Archive"}
              </h1>
              <p className="text-xs text-slate-500 mt-1">
                Haryana State Higher Education Council — Authoritative Institutional Evaluation
              </p>
            </div>

            <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
              <button
                onClick={loadCollegeData}
                disabled={loading}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
                title="Refresh authoritative server state"
              >
                <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
                <span>Refresh</span>
              </button>

              {activeAssessment && (
                <>
                  <button
                    onClick={() => setSelectedAssessmentId(activeAssessment.assessment_id)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 text-xs font-bold transition-colors shadow-xs cursor-pointer"
                  >
                    <Eye size={13} className="text-slate-600" />
                    <span>Audit Preview</span>
                  </button>

                  <button
                    onClick={() => downloadAssessmentReportCSV(activeAssessment.assessment_id)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-bold transition-colors shadow-xs cursor-pointer"
                    title="Export official CSV audit report"
                  >
                    <FileSpreadsheet size={13} />
                    <span>Export CSV</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Global Error Notice */}
          {error && (
            <ErrorState
              title="College Portal Notice"
              message={error}
              onRetry={loadCollegeData}
            />
          )}

          {/* Loading Shimmer */}
          {loading && !college ? (
            <DashboardSkeleton />
          ) : !college ? (
            <EmptyState
              icon={School}
              title="No College Record Assigned"
              description="Your account is not currently linked to an approved college institution record in the database. Please contact your State DHE Administrator."
            />
          ) : (
            <>
              {/* SECTION 1: OVERVIEW */}
              {activeSection === "overview" && (
                <div className="space-y-6">
                  {/* Assessment Journey Stepper */}
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
                        Initialize your college’s appraisal workspace to record inputs for C1–C22 and submit documentary evidence.
                      </p>
                      <button
                        onClick={handleCreateAssessment}
                        disabled={creating}
                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-colors shadow-xs cursor-pointer"
                      >
                        <PlusCircle size={14} />
                        <span>{creating ? "Initializing..." : "Start 2025-26 Assessment"}</span>
                      </button>
                    </div>
                  )}

                  {/* 4 Summary Metrics */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Status */}
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
                        <span className="truncate">{activeAssessment ? activeAssessment.assessment_id : "No Session"}</span>
                      </div>
                    </div>

                    {/* Parameters */}
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

                    {/* Evidence Coverage */}
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

                    {/* Framework */}
                    <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                            Statutory Framework
                          </span>
                          <span className="text-[10px] font-bold text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-full">
                            College
                          </span>
                        </div>
                        <p className="text-lg font-extrabold text-slate-900 tracking-tight">
                          {activeAssessment?.framework || "COLLEGE_2026"}
                        </p>
                      </div>
                      <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-1.5 text-xs text-slate-500">
                        <Building2 size={12} className="text-slate-400" />
                        <span>Academic Period 2025–2026</span>
                      </div>
                    </div>
                  </div>

                  {/* Primary Attention & Next Action */}
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
                              Assessment Locked for Official Screening Committee Review
                            </h3>
                          )}
                          <p className="text-xs text-slate-500 mt-0.5 max-w-2xl leading-relaxed">
                            {activeAssessment.status === "DRAFT"
                              ? "Record inputs for parameters C1–C22 and attach required documentary evidence before submitting."
                              : "Assigned committee reviewers are independently inspecting your documentary evidence."}
                          </p>
                        </div>

                        <div className="flex items-center gap-3 shrink-0">
                          {activeAssessment.status === "DRAFT" && (
                            <button
                              onClick={handleSubmitAssessment}
                              disabled={submitting}
                              className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                            >
                              <Send size={13} />
                              <span>{submitting ? "Submitting..." : "Submit to Committee"}</span>
                            </button>
                          )}

                          <button
                            onClick={() => setActiveSection("parameters")}
                            className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                          >
                            <span>Manage Parameters</span>
                            <ChevronRight size={13} />
                          </button>
                        </div>
                      </div>

                      {/* Unresolved Specifications Banner */}
                      <div className="p-3.5 bg-purple-50/80 border border-purple-200 rounded-lg text-xs text-purple-900 flex items-start gap-3">
                        <Ban size={16} className="text-purple-600 shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-purple-950 mb-0.5">Council Notice: Unresolved Specifications (C5, C7, C8, C16)</p>
                          <p className="text-purple-800 leading-relaxed">
                            Parameters C5 (IDP), C7 (NAAC), C8 (NCrF), and C16 (Gender Parity) are governed by pending council specifications and will not be evaluated until formally notified.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Evidence Readiness Summary Component */}
                  {activeAssessment && readiness && (
                    <EvidenceReadinessSummary
                      summary={readiness.evidence_readiness_summary}
                      isReady={readiness.is_ready}
                      onActionClick={() => setActiveSection("evidence")}
                    />
                  )}
                </div>
              )}

              {/* SECTION 2: PARAMETERS (C1–C22) */}
              {activeSection === "parameters" && (
                <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
                  <div className="p-4 sm:p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/60">
                    <div>
                      <h2 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight">
                        Statutory Parameters (C1–C22)
                      </h2>
                      <p className="text-xs text-slate-500">
                        Authoritative evaluation criteria registered under the COLLEGE_2026 framework
                      </p>
                    </div>

                    {/* Filter Tabs */}
                    <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 text-xs font-semibold text-slate-600 shadow-2xs">
                      <button
                        onClick={() => setParamFilter("ALL")}
                        className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                          paramFilter === "ALL" ? "bg-slate-900 text-white shadow-xs" : "hover:text-slate-900"
                        }`}
                      >
                        All ({parameters.length})
                      </button>
                      <button
                        onClick={() => setParamFilter("COMPLETED")}
                        className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                          paramFilter === "COMPLETED" ? "bg-slate-900 text-white shadow-xs" : "hover:text-slate-900"
                        }`}
                      >
                        Completed ({completedParameters})
                      </button>
                      <button
                        onClick={() => setParamFilter("PENDING")}
                        className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                          paramFilter === "PENDING" ? "bg-slate-900 text-white shadow-xs" : "hover:text-slate-900"
                        }`}
                      >
                        Pending ({totalParameters - completedParameters})
                      </button>
                      <button
                        onClick={() => setParamFilter("BLOCKED")}
                        className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
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
                        <tr className="bg-slate-50/80 border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                          <th className="py-3 px-4 w-16">Code</th>
                          <th className="py-3 px-4">Parameter Title</th>
                          <th className="py-3 px-4 text-center w-28">Max Marks</th>
                          <th className="py-3 px-4">Specification & Blocking Notice</th>
                          <th className="py-3 px-4 text-center w-36">Input Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {filteredParameters.map((param) => {
                          const isComplete = param.submitted_input != null && Object.keys(param.submitted_input).length > 0;
                          const unresolvedNotice = UNRESOLVED_SPEC_PARAMS[param.parameter_code];

                          return (
                            <tr key={param.parameter_code} className="hover:bg-slate-50/70 transition-colors">
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
                                  <span className="text-slate-400 italic text-[11px]">Standard evaluation rule</span>
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

              {/* SECTION 3: EVIDENCE READINESS */}
              {activeSection === "evidence" && (
                <div className="space-y-6">
                  {readiness && (
                    <EvidenceReadinessSummary
                      summary={readiness.evidence_readiness_summary}
                      isReady={readiness.is_ready}
                      onActionClick={() => setSelectedAssessmentId(activeAssessment.assessment_id)}
                    />
                  )}

                  <div className="bg-white rounded-xl border border-slate-200/90 p-6 shadow-xs">
                    <h3 className="text-sm font-bold text-slate-900 mb-2">Evidence Submission Guidelines</h3>
                    <ul className="text-xs text-slate-600 space-y-2 list-disc pl-5">
                      <li>All documentary evidence must fall within the statutory window (2025-07-01 to 2026-06-30).</li>
                      <li>Documents must be in PDF or standard image format, signed and sealed by the competent authority.</li>
                      <li>Subcriteria lacking required evidence are automatically gated and will yield 0 marks during scoring.</li>
                    </ul>
                  </div>
                </div>
              )}

              {/* SECTION 4: AUDIT REPORTS */}
              {activeSection === "reports" && (
                <div className="space-y-6">
                  <div className="bg-white rounded-xl border border-slate-200/90 p-6 shadow-xs flex items-center justify-between gap-4">
                    <div>
                      <h3 className="text-base font-bold text-slate-900">Authoritative Assessment Audit Ledger</h3>
                      <p className="text-xs text-slate-500 mt-1">
                        Inspect complete statutory evaluation reports, subcriteria gating traces, and verification logs.
                      </p>
                    </div>

                    {activeAssessment && (
                      <div className="flex items-center gap-2.5 shrink-0">
                        <button
                          onClick={() => setSelectedAssessmentId(activeAssessment.assessment_id)}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer"
                        >
                          Open Audit Inspector
                        </button>
                        <button
                          onClick={() => downloadAssessmentReportCSV(activeAssessment.assessment_id)}
                          className="px-3.5 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-bold transition-colors cursor-pointer"
                        >
                          Export CSV
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* SECTION 5: HISTORICAL SUBMISSIONS ARCHIVE */}
              {activeSection === "legacy" && (
                <div className="space-y-4">
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900">
                    <div className="flex items-center gap-2 font-bold mb-1 text-sm text-amber-950">
                      <AlertCircle size={15} />
                      <span>Historical Submissions Archive</span>
                    </div>
                    <p>
                      These nomination records belong to previous cycles. They are preserved for historical reference and are strictly isolated from the NEP Excellence Awards 2026 framework.
                    </p>
                  </div>

                  {legacyLoading ? (
                    <DashboardSkeleton />
                  ) : legacySubmissions.length === 0 ? (
                    <EmptyState
                      icon={Archive}
                      title="No Historical Nominations Found"
                      description="There are no past nomination records registered for your institution in the archive."
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
                              className="px-3.5 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-lg text-xs font-bold transition-colors cursor-pointer"
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
            </>
          )}
        </main>
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