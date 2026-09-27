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

  // Load Nomination Forms & Submissions
  const loadLegacyData = useCallback(async () => {
    setLegacyLoading(true);
    try {
      const data = await fetchMySubmissions();
      setLegacySubmissions(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load nomination submissions:", err);
    } finally {
      setLegacyLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLegacyData();
  }, [loadLegacyData]);

  useEffect(() => {
    if (activeSection === "legacy" || activeSection === "forms") {
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

  // Metrics (server-authoritative: strictly C1–C22 = 22 parameters)
  const completedParameters = parameters.filter((p) => p.submitted_input != null && Object.keys(p.submitted_input).length > 0).length;
  const totalParameters = 22;
  const coveredSubcriteria = readiness?.evidence_readiness_summary?.covered_subcriteria ?? 0;
  const totalSubcriteria = readiness?.evidence_readiness_summary?.total_subcriteria ?? 45;
  const isReadyForScoring = readiness?.is_ready ?? false;

  const handleOpenAssessment = (parameterCode = null) => {
    if (!activeAssessment) return;
    const collegeNameSlug = String(institutionName || college?.name || user?.college_name || "college").toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const collegeAisheSlug = String(institutionAisheCode || college?.aishe_code || user?.aishe_code || "code").toLowerCase().replace(/[^a-z0-9]+/g, "-");
    navigate(`/institution/${collegeNameSlug}/${collegeAisheSlug}/assessment/${activeAssessment.assessment_id}`);
  };

  const filteredParameters = parameters.filter((p) => {
    const isComplete = p.submitted_input != null && Object.keys(p.submitted_input).length > 0;
    const isUnresolved = Boolean(UNRESOLVED_SPEC_PARAMS[p.parameter_code]);
    if (paramFilter === "COMPLETED") return isComplete;
    if (paramFilter === "PENDING") return !isComplete;
    if (paramFilter === "BLOCKED") return isUnresolved;
    return true;
  });

  // Modern Workflow Isolation: Do not use NominationWorkspace for modern assessment
  if (formId && activeAssessment) {
    const collegeNameSlug = String(user?.college_name || "college").toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const collegeAisheSlug = String(user?.aishe_code || "code").toLowerCase().replace(/[^a-z0-9]+/g, "-");
    navigate(`/institution/${institutionName || collegeNameSlug}/${institutionAisheCode || collegeAisheSlug}/assessment/${activeAssessment.assessment_id}`);
    return null;
  }

  // Sidebar navigation items
  const navItems = [
    { id: "overview", label: "Dashboard Overview", icon: LayoutDashboard, badge: null },
    { id: "parameters", label: "Parameters (C1–C22)", icon: ClipboardList, badge: `${completedParameters}/${totalParameters}` },
    { id: "evidence", label: "Evidence Readiness", icon: CheckCircle2, badge: isReadyForScoring ? "Ready" : "Action" },
    { id: "forms", label: "Nomination Forms", icon: FileText, badge: legacySubmissions.length > 0 ? `${legacySubmissions.length}` : null },
    { id: "reports", label: "Audit Reports", icon: FileSpreadsheet, badge: null },
    { id: "legacy", label: "Historical Archive", icon: Archive, badge: null },
  ];

  return (
    <div className="min-h-screen bg-[#fdfaf6] flex font-sans antialiased text-slate-800">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-40 lg:hidden"
        />
      )}

      {/* Modern, Clean Institutional Sidebar with Hover-to-Expand Interaction */}
      <aside
        className={`fixed top-0 inset-y-0 left-0 z-50 flex flex-col justify-between transition-all duration-300 ease-in-out group overflow-hidden bg-white border-r border-[#ebdcd0] ${
          sidebarOpen
            ? "translate-x-0 w-64 shadow-2xl"
            : "-translate-x-full lg:translate-x-0 w-64 lg:w-20 lg:hover:w-64 lg:shadow-xs lg:hover:shadow-2xl"
        } h-screen`}
      >
        {/* Top: Branding & Logo */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="h-16 px-3.5 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-[#fdfaf6] border border-[#ebdcd0] p-1 flex items-center justify-center shrink-0 shadow-xs transition-transform duration-300 group-hover:scale-105">
                <img src={hshecLogo} alt="HSHEC" className="w-full h-full object-contain" />
              </div>
              <div className="min-w-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap hidden lg:block">
                <h1 className="text-xs font-bold text-slate-900 leading-tight">
                  NEP Excellence Awards
                </h1>
                <span className="text-[10px] font-bold text-[#600b0b] tracking-wider uppercase block">
                  Principal Portal
                </span>
              </div>
              <div className="min-w-0 block lg:hidden">
                <h1 className="text-xs font-bold text-slate-900 leading-tight">
                  NEP Excellence Awards
                </h1>
                <span className="text-[10px] font-bold text-[#600b0b] tracking-wider uppercase block">
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
          <div className="p-2.5 mx-2.5 my-2.5 bg-[#eaded2]/40 border border-[#ebdcd0] rounded-xl shrink-0 transition-all duration-300">
            {/* Collapsed Icon View on Desktop */}
            <div className="hidden lg:flex lg:group-hover:hidden items-center justify-center py-1">
              <div
                className="w-8 h-8 rounded-lg bg-white border border-[#ebdcd0] flex items-center justify-center text-[#600b0b] font-bold text-xs shadow-2xs"
                title={`${collegeName} (${aisheCode})`}
              >
                <Building2 size={16} />
              </div>
            </div>

            {/* Expanded Detailed View */}
            <div className="block lg:hidden lg:group-hover:block transition-opacity duration-300">
              <span className="text-[9px] font-bold text-[#600b0b] uppercase tracking-widest block mb-0.5">
                Affiliated Institution
              </span>
              <p className="text-xs font-bold text-slate-900 leading-snug line-clamp-2" title={collegeName}>
                {collegeName}
              </p>
              <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                <span className="text-[10px] font-mono font-bold bg-white px-2 py-0.5 rounded border border-[#ebdcd0] text-slate-700">
                  AISHE: {aisheCode}
                </span>
                <span className="text-[10px] font-bold text-[#600b0b] bg-[#eaded2] px-2 py-0.5 rounded border border-[#ebdcd0]">
                  COLLEGE_2026
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="px-2.5 space-y-1 overflow-y-auto flex-1 py-1">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-wider px-3 py-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap hidden lg:block">
              Assessment Modules
            </div>
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-wider px-3 py-1 block lg:hidden">
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
                  title={item.label}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all text-left cursor-pointer group/item relative ${
                    isActive
                      ? "bg-[#600b0b] text-white shadow-xs border-l-4 border-[#c29b68]"
                      : "text-slate-600 hover:bg-[#eaded2]/50 hover:text-slate-900"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon size={18} className={`shrink-0 transition-transform duration-200 group-hover/item:scale-110 ${isActive ? "text-white" : "text-slate-500"}`} />
                    <span className="truncate opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap hidden lg:inline">
                      {item.label}
                    </span>
                    <span className="truncate inline lg:hidden">
                      {item.label}
                    </span>
                  </div>
                  {item.badge && (
                    <>
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 hidden lg:inline ${
                          isActive
                            ? "bg-white/20 text-white"
                            : "bg-[#eaded2]/60 text-[#600b0b] border border-[#ebdcd0]"
                        }`}
                      >
                        {item.badge}
                      </span>
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 inline lg:hidden ${
                          isActive
                            ? "bg-white/20 text-white"
                            : "bg-[#eaded2]/60 text-[#600b0b] border border-[#ebdcd0]"
                        }`}
                      >
                        {item.badge}
                      </span>
                      {/* Collapsed dot indicator on desktop */}
                      <span className="hidden lg:block lg:group-hover:hidden absolute top-2.5 right-2 w-1.5 h-1.5 rounded-full bg-[#c29b68]" />
                    </>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom: Principal Profile & Sign Out */}
        <div className="p-2.5 border-t border-slate-100 bg-slate-50/50 shrink-0">
          <div
            className="flex items-center gap-2.5 p-2 rounded-xl bg-white border border-[#ebdcd0] mb-2"
            title={user?.full_name || "College Principal"}
          >
            <div className="w-8 h-8 rounded-lg bg-[#eaded2] border border-[#ebdcd0] flex items-center justify-center text-[#600b0b] shrink-0 font-bold text-xs shadow-2xs">
              <User size={15} />
            </div>
            <div className="min-w-0 flex-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap hidden lg:block">
              <p className="text-xs font-bold text-slate-800 truncate">
                {user?.full_name || "College Principal"}
              </p>
              <p className="text-[10px] text-slate-400 truncate">Principal Authority</p>
            </div>
            <div className="min-w-0 flex-1 block lg:hidden">
              <p className="text-xs font-bold text-slate-800 truncate">
                {user?.full_name || "College Principal"}
              </p>
              <p className="text-[10px] text-slate-400 truncate">Principal Authority</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            title="Sign Out"
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50 border border-transparent hover:border-red-100 rounded-xl transition-all cursor-pointer"
          >
            <LogOut size={15} className="shrink-0" />
            <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap hidden lg:inline">Sign Out</span>
            <span className="inline lg:hidden">Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen lg:pl-20 transition-all duration-300">
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
          <div className="bg-white rounded-xl border border-[#ebdcd0] p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#eaded2]/60 text-[#600b0b] border border-[#ebdcd0] uppercase tracking-wider">
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
                {activeSection === "forms" && "Institutional Nomination Forms"}
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
                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#600b0b] hover:bg-[#4a0707] text-white rounded-lg text-xs font-bold transition-colors shadow-xs cursor-pointer"
                      >
                        <PlusCircle size={14} />
                        <span>{creating ? "Initializing..." : "Start 2025-26 Assessment"}</span>
                      </button>
                    </div>
                  )}

                  {/* 4 Summary Metrics */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Status */}
                    <div className="bg-white rounded-xl border border-[#ebdcd0] p-5 shadow-xs flex flex-col justify-between">
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
                    <div className="bg-white rounded-xl border border-[#ebdcd0] p-5 shadow-xs flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                            Parameters Filled
                          </span>
                          <span className="text-[11px] font-bold text-[#600b0b] bg-[#eaded2]/60 border border-[#ebdcd0] px-2 py-0.5 rounded-full">
                            {Math.round((completedParameters / totalParameters) * 100)}%
                          </span>
                        </div>
                        <div className="flex items-baseline gap-1.5">
                          <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
                            {completedParameters}
                          </span>
                          <span className="text-xs font-semibold text-slate-400">
                            / 22 filled
                          </span>
                        </div>
                      </div>
                      <div className="mt-3 pt-3 border-t border-slate-100">
                        <div className="w-full h-1.5 bg-[#eaded2]/40 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#600b0b] rounded-full transition-all duration-300"
                            style={{ width: `${(completedParameters / totalParameters) * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Evidence Coverage */}
                    <div className="bg-white rounded-xl border border-[#ebdcd0] p-5 shadow-xs flex flex-col justify-between">
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
                    <div className="bg-white rounded-xl border border-[#ebdcd0] p-5 shadow-xs space-y-4">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-[11px] font-bold text-[#600b0b] uppercase tracking-wider bg-[#eaded2]/60 px-2 py-0.5 rounded border border-[#ebdcd0]">
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

                        <div className="flex items-center gap-3 shrink-0 flex-wrap">
                          <button
                            onClick={() => handleOpenAssessment()}
                            className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-[#600b0b] hover:bg-[#4a0707] text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
                          >
                            <span>Continue Assessment (C1–C22)</span>
                            <ChevronRight size={13} />
                          </button>

                          {activeAssessment.status === "DRAFT" && (
                            <button
                              onClick={handleSubmitAssessment}
                              disabled={submitting}
                              className="inline-flex items-center gap-2 px-3.5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                            >
                              <Send size={13} />
                              <span>{submitting ? "Submitting..." : "Submit"}</span>
                            </button>
                          )}

                          <button
                            onClick={() => setActiveSection("parameters")}
                            className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                          >
                            <span>View Parameters</span>
                            <ChevronRight size={13} />
                          </button>
                        </div>
                      </div>

                      {/* Unresolved Specifications Banner */}
                      <div className="p-3.5 bg-amber-50/80 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-start gap-3">
                        <AlertCircle size={16} className="text-amber-600 shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-amber-950 mb-0.5">Council Blocker Notice: Clarification Pending (C5, C7, C8, C16)</p>
                          <p className="text-amber-800 leading-relaxed">
                            Parameters C5 (Internship), C7 (Faculty Training), C8 (Credit Transfer), and C16 (Statutory Rule) have pending council clarifications. Review inputs carefully before final sign-off.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 4 NEP 2026 Core Institutional Pillars */}
                  {activeAssessment && (
                    <div className="bg-white rounded-xl border border-[#ebdcd0] p-5 shadow-xs">
                      <div className="flex items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
                        <div>
                          <span className="text-[10px] font-bold text-[#600b0b] uppercase tracking-wider bg-[#eaded2]/60 px-2 py-0.5 rounded border border-[#ebdcd0]">
                            NEP 2020 Dimensions
                          </span>
                          <h3 className="text-sm sm:text-base font-bold text-slate-900 mt-1">
                            Institutional Core Pillars & Milestone Progress
                          </h3>
                        </div>
                        <span className="text-xs font-mono font-semibold text-slate-500">
                          Target: Tier 1 Autonomous
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {/* Pillar 1: Multidisciplinary */}
                        <div className="p-4 rounded-xl bg-slate-50/70 border border-[#ebdcd0] flex flex-col justify-between">
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">Pillar 1</span>
                            <h4 className="text-xs font-bold text-slate-900 mt-1">Multidisciplinary & Holistic</h4>
                            <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                              FYUP structure, minor subjects & IKS integration (C1–C4, C6, C7).
                            </p>
                          </div>
                          <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center justify-between">
                            <span className="text-[11px] font-semibold text-slate-600">Compliance</span>
                            <span className="text-xs font-bold text-[#600b0b] font-mono">
                              {Math.round((parameters.filter(p => ['C1','C2','C3','C4','C6','C7'].includes(p.parameter_code) && p.submitted_input).length / 6) * 100)}%
                            </span>
                          </div>
                        </div>

                        {/* Pillar 2: ABC & Mobility */}
                        <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col justify-between">
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">Pillar 2</span>
                            <h4 className="text-xs font-bold text-slate-900 mt-1">ABC & Credit Mobility</h4>
                            <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                              DigiLocker APAAR sync and multiple entry/exit pathways (C8, C9).
                            </p>
                          </div>
                          <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center justify-between">
                            <span className="text-[11px] font-semibold text-slate-600">Compliance</span>
                            <span className="text-xs font-bold text-emerald-700 font-mono">
                              {Math.round((parameters.filter(p => ['C8','C9'].includes(p.parameter_code) && p.submitted_input).length / 2) * 100)}%
                            </span>
                          </div>
                        </div>

                        {/* Pillar 3: Research & Innovation */}
                        <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col justify-between">
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">Pillar 3</span>
                            <h4 className="text-xs font-bold text-slate-900 mt-1">Research & Incubation</h4>
                            <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                              College seed funding, patent index, and student startups (C10, C11, C14).
                            </p>
                          </div>
                          <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center justify-between">
                            <span className="text-[11px] font-semibold text-slate-600">Compliance</span>
                            <span className="text-xs font-bold text-purple-700 font-mono">
                              {Math.round((parameters.filter(p => ['C10','C11','C14','C16'].includes(p.parameter_code) && p.submitted_input).length / 4) * 100)}%
                            </span>
                          </div>
                        </div>

                        {/* Pillar 4: Skill & HKRN */}
                        <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col justify-between">
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">Pillar 4</span>
                            <h4 className="text-xs font-bold text-slate-900 mt-1">Skill & HKRN Internships</h4>
                            <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                              60-hr mandatory apprenticeship & digital smart classrooms (C5, C12, C13, C15).
                            </p>
                          </div>
                          <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center justify-between">
                            <span className="text-[11px] font-semibold text-slate-600">Compliance</span>
                            <span className="text-xs font-bold text-amber-700 font-mono">
                              {Math.round((parameters.filter(p => ['C5','C12','C13','C15'].includes(p.parameter_code) && p.submitted_input).length / 4) * 100)}%
                            </span>
                          </div>
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
                <div className="bg-white rounded-xl border border-[#ebdcd0] shadow-xs overflow-hidden">
                  <div className="p-4 sm:p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/60">
                    <div>
                      <h2 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight">
                        Statutory Parameters (C1–C22)
                      </h2>
                      <p className="text-xs text-slate-500">
                        Authoritative evaluation criteria registered under the COLLEGE_2026 framework
                      </p>
                    </div>

                    {/* Filter Tabs & Open Form Action */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <button
                        onClick={() => handleOpenAssessment()}
                        className="px-3 py-1 bg-[#600b0b] hover:bg-[#4a0707] text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer inline-flex items-center gap-1"
                      >
                        <span>Open Assessment Form</span>
                        <ChevronRight size={13} />
                      </button>

                      <div className="inline-flex rounded-lg border border-[#ebdcd0] bg-white p-1 text-xs font-semibold text-slate-600 shadow-2xs">
                        <button
                          onClick={() => setParamFilter("ALL")}
                          className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                            paramFilter === "ALL" ? "bg-[#600b0b] text-white shadow-xs" : "hover:text-slate-900"
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
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="bg-slate-50/80 border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                          <th className="py-3 px-4 w-16">Code</th>
                          <th className="py-3 px-4">Parameter Title</th>
                          <th className="py-3 px-4 text-center w-28">Max Marks</th>
                          <th className="py-3 px-4">Specification & Blocking Notice</th>
                          <th className="py-3 px-4 text-center w-32">Input Status</th>
                          <th className="py-3 px-4 text-center w-24">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {filteredParameters.map((param) => {
                          const isComplete = param.submitted_input != null && Object.keys(param.submitted_input).length > 0;
                          const unresolvedNotice = UNRESOLVED_SPEC_PARAMS[param.parameter_code];

                          return (
                            <tr key={param.parameter_code} className="hover:bg-slate-50/70 transition-colors">
                              <td className="py-3.5 px-4 font-mono font-bold text-[#600b0b] whitespace-nowrap">
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
                              <td className="py-3.5 px-4 text-center whitespace-nowrap">
                                <button
                                  onClick={() => handleOpenAssessment(param.parameter_code)}
                                  className="text-xs font-bold text-[#600b0b] hover:text-[#4a0707] hover:underline cursor-pointer"
                                >
                                  Open in Form
                                </button>
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
                          className="px-4 py-2 bg-[#600b0b] hover:bg-[#4a0707] text-white rounded-lg text-xs font-bold transition-colors cursor-pointer"
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

              {/* SECTION: NOMINATION FORMS DIRECT ACCESS */}
              {activeSection === "forms" && (
                <div className="space-y-6">
                  <div className="bg-white rounded-xl border border-[#ebdcd0] p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-bold text-[#600b0b] bg-[#eaded2]/60 px-2 py-0.5 rounded border border-[#ebdcd0] uppercase tracking-wider">
                          Nomination Workspace
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-slate-900">
                        Haryana State NEP Implementation Award — Institutional Nomination Form
                      </h3>
                      <p className="text-xs text-slate-500 mt-1">
                        Access and complete the 20 institutional performance indicator questionnaires and documentary submissions.
                      </p>
                    </div>

                    <button
                      onClick={() =>
                        navigate(
                          `/institution/${institutionName || "college"}/${institutionAisheCode || "aishe"}/dashboard/forms/nep-excellence-nomination-2025`
                        )
                      }
                      className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#600b0b] hover:bg-[#4a0707] text-white rounded-xl text-xs font-bold shadow-xs transition-all shrink-0 cursor-pointer"
                    >
                      <FileText size={15} />
                      <span>Open Nomination Form</span>
                    </button>
                  </div>

                  {/* Registered Form Instances */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                      Available Submissions & Drafts
                    </h4>
                    {legacyLoading ? (
                      <DashboardSkeleton />
                    ) : legacySubmissions.length === 0 ? (
                      <div className="bg-white rounded-xl border border-slate-200/90 p-6 text-center">
                        <FileText size={32} className="mx-auto text-slate-300 mb-2" />
                        <h4 className="text-sm font-bold text-slate-800">No Draft Forms Found</h4>
                        <p className="text-xs text-slate-500 mt-1 mb-4">
                          Click below to launch the nomination questionnaire workspace for your college.
                        </p>
                        <button
                          onClick={() =>
                            navigate(
                              `/institution/${institutionName || "college"}/${institutionAisheCode || "aishe"}/dashboard/forms/nep-excellence-nomination-2025`
                            )
                          }
                          className="px-4 py-2 bg-[#600b0b] hover:bg-[#4a0707] text-white rounded-lg text-xs font-bold inline-flex items-center gap-2 transition-colors cursor-pointer"
                        >
                          <PlusCircle size={14} />
                          <span>Start New Nomination</span>
                        </button>
                      </div>
                    ) : (
                      <div className="grid gap-4">
                        {legacySubmissions.map((sub) => (
                          <div
                            key={sub.id}
                            className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                          >
                            <div>
                              <div className="flex items-center gap-2 mb-1.5">
                                <span className="text-[10px] font-mono font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded uppercase">
                                  Form ID: {sub.form_id}
                                </span>
                                <StatusBadge status={sub.is_submitted ? "SUBMITTED" : "DRAFT"} size="sm" />
                              </div>
                              <h4 className="text-sm font-bold text-slate-900">
                                {sub.form_id === "nep-excellence-nomination-2025"
                                  ? "Haryana State NEP Implementation Award — Nomination Form"
                                  : "Institutional Nomination Record"}
                              </h4>
                              <p className="text-xs text-slate-500 mt-1">
                                Last Modified: {new Date(sub.updated_at).toLocaleDateString()} · Principal/Head: {sub.head_name || collegeName}
                              </p>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <button
                                onClick={() =>
                                  navigate(
                                    `/institution/${institutionName || "college"}/${institutionAisheCode || "aishe"}/dashboard/forms/${sub.form_id}`
                                  )
                                }
                                className="px-4 py-2 bg-[#600b0b] hover:bg-[#4a0707] text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer inline-flex items-center gap-1.5"
                              >
                                <span>{sub.is_submitted ? "View Submitted Form" : "Open & Continue Form"}</span>
                                <ChevronRight size={14} />
                              </button>
                            </div>
                          </div>
                        ))}
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
                              className="px-3.5 py-1.5 bg-[#eaded2]/60 hover:bg-[#eaded2] text-[#600b0b] border border-[#ebdcd0] rounded-lg text-xs font-bold transition-colors cursor-pointer"
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

        {/* Professional Clean White Institutional Footer */}
        <footer className="mt-auto bg-white border-t border-[#ebdcd0] py-6 px-4 sm:px-6 lg:px-8">
          <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 text-center md:text-left">
              <div className="w-8 h-8 rounded-lg bg-[#fdfaf6] border border-[#ebdcd0] p-1 flex items-center justify-center shrink-0">
                <img src={hshecLogo} alt="HSHEC" className="w-full h-full object-contain" />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-800">
                  Haryana State Higher Education Council (HSHEC)
                </p>
                <p className="text-[11px] text-slate-500">
                  NEP Excellence Awards 2026 · Authoritative Institutional Evaluation Platform
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-slate-500">
              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200/80 rounded-full px-3 py-1 text-[11px] font-medium text-slate-600">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span>Statutory Window: 2025–26</span>
              </div>
              <span className="text-slate-300 hidden sm:inline">•</span>
              <span className="text-[11px] text-slate-400">
                Logged in as <strong className="text-slate-700 font-semibold">{collegeName}</strong> (AISHE: {aisheCode})
              </span>
            </div>
          </div>
        </footer>
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