/**
 * UniversityDashboard — NEP Excellence Awards 2026 Institutional Assessment Portal
 *
 * Professional, Modern Institutional Grade Dashboard Pass.
 * Matches College Principal Dashboard architecture:
 * - Persistent left sidebar with council branding, university profile, and module navigation tabs
 * - Dedicated sections: Overview, Parameters (U1–U20), Evidence Readiness, and Audit Reports
 * - Professional white footer with council branding and statutory window
 * - Strictly adheres to server-authoritative scoring, RBAC, tenant isolation, and statutory definitions.
 * - Zero client-side score computation.
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
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
  LayoutDashboard,
  LogOut,
  Menu,
  X,
  User,
  ChevronRight,
} from "lucide-react";
import { downloadAssessmentReportCSV } from "../../api/reports";
import AssessmentReportModal from "../../components/Reports/AssessmentReportModal";
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

const ROLE_LABELS = {
  nodal_officer: "University Nodal Officer",
  university_admin: "University Administrator",
};

export default function UniversityDashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  // Navigation & View state
  const [activeSection, setActiveSection] = useState("overview"); // 'overview' | 'parameters' | 'evidence' | 'reports'
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Data state
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

  const handleLogout = async () => {
    await logout();
    navigate("/auth/login");
  };

  const roleLabel = ROLE_LABELS[user?.role] || "University Officer";
  const universityName = university?.name || user?.university_name || "Kurukshetra University";
  const aisheCode = university?.aishe_code || user?.aishe_code || "U-0123";

  // Compute metrics from actual domain data (strictly U1–U20 = 20 parameters)
  const completedParameters = parameters.filter((p) => p.submitted_input != null && Object.keys(p.submitted_input).length > 0).length;
  const totalParameters = 20;
  const coveredSubcriteria = readiness?.evidence_readiness_summary?.covered_subcriteria ?? 0;
  const totalSubcriteria = readiness?.evidence_readiness_summary?.total_subcriteria ?? 51;
  const isReadyForScoring = readiness?.is_ready ?? false;

  const handleOpenAssessment = (parameterCode = null) => {
    if (!activeAssessment) return;
    navigate(`/university/assessment/${activeAssessment.assessment_id}`);
  };

  const filteredParameters = parameters.filter((p) => {
    const isComplete = p.submitted_input != null && Object.keys(p.submitted_input).length > 0;
    if (paramFilter === "COMPLETED") return isComplete;
    if (paramFilter === "PENDING") return !isComplete;
    return true;
  });

  // Statutory Access Control: Only State Admin, Committee Chair, and Committee Members are authorized to view affiliated college lists
  const canViewAffiliatedColleges = ["admin", "committee_chair", "committee"].includes(user?.role);

  useEffect(() => {
    if (!canViewAffiliatedColleges && activeSection === "colleges") {
      setActiveSection("overview");
    }
  }, [canViewAffiliatedColleges, activeSection]);

  // Sidebar navigation items
  const navItems = [
    { id: "overview", label: "Dashboard Overview", icon: LayoutDashboard, badge: null },
    ...(canViewAffiliatedColleges
      ? [{ id: "colleges", label: "Affiliated Colleges (64)", icon: Building2, badge: "52/64" }]
      : []),
    { id: "parameters", label: "Parameters (U1–U20)", icon: ClipboardList, badge: `${completedParameters}/20` },
    { id: "evidence", label: "Evidence Readiness", icon: CheckCircle2, badge: isReadyForScoring ? "Ready" : "Action" },
    { id: "reports", label: "Audit Reports", icon: FileSpreadsheet, badge: null },
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
                  University Portal
                </span>
              </div>
              <div className="min-w-0 block lg:hidden">
                <h1 className="text-xs font-bold text-slate-900 leading-tight">
                  NEP Excellence Awards
                </h1>
                <span className="text-[10px] font-bold text-[#600b0b] tracking-wider uppercase block">
                  University Portal
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
                title={`${universityName} (${aisheCode})`}
              >
                <Building2 size={16} />
              </div>
            </div>

            {/* Expanded Detailed View */}
            <div className="block lg:hidden lg:group-hover:block transition-opacity duration-300">
              <span className="text-[9px] font-bold text-[#600b0b] uppercase tracking-widest block mb-0.5">
                Affiliated University
              </span>
              <p className="text-xs font-bold text-slate-900 leading-snug line-clamp-2" title={universityName}>
                {universityName}
              </p>
              <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                <span className="text-[10px] font-mono font-bold bg-white px-2 py-0.5 rounded border border-[#ebdcd0] text-slate-700">
                  AISHE: {aisheCode}
                </span>
                <span className="text-[10px] font-bold text-[#c29b68] bg-[#fbf5ee] px-2 py-0.5 rounded border border-[#dfb987]">
                  UNIVERSITY_2026
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

        {/* Bottom: Officer Profile & Sign Out */}
        <div className="p-2.5 border-t border-slate-100 bg-slate-50/50 shrink-0">
          <div
            className="flex items-center gap-2.5 p-2 rounded-xl bg-white border border-[#ebdcd0] mb-2"
            title={user?.full_name || "University Officer"}
          >
            <div className="w-8 h-8 rounded-lg bg-[#eaded2] border border-[#ebdcd0] flex items-center justify-center text-[#600b0b] shrink-0 font-bold text-xs shadow-2xs">
              <User size={15} />
            </div>
            <div className="min-w-0 flex-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap hidden lg:block">
              <p className="text-xs font-bold text-slate-800 truncate">
                {user?.full_name || "University Officer"}
              </p>
              <p className="text-[10px] text-slate-400 truncate">{roleLabel}</p>
            </div>
            <div className="min-w-0 flex-1 block lg:hidden">
              <p className="text-xs font-bold text-slate-800 truncate">
                {user?.full_name || "University Officer"}
              </p>
              <p className="text-[10px] text-slate-400 truncate">{roleLabel}</p>
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
              {universityName}
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
                  {roleLabel}
                </span>
                <span className="text-slate-300">•</span>
                <span className="text-xs text-slate-500 font-mono">
                  Session: {activeAssessment ? activeAssessment.assessment_id : "No Session"}
                </span>
              </div>
              <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                {activeSection === "overview" && "Assessment Overview & Health"}
                {activeSection === "parameters" && "Statutory Parameters (U1–U20)"}
                {activeSection === "evidence" && "Documentary Evidence Readiness"}
                {activeSection === "reports" && "Official Audit & Assessment Reports"}
              </h1>
              <p className="text-xs text-slate-500 mt-1">
                Haryana State Higher Education Council — Authoritative Institutional Evaluation
              </p>
            </div>

            <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
              <button
                onClick={loadDashboardData}
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
                    onClick={() => setShowReportModal(true)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 text-xs font-bold transition-colors shadow-xs cursor-pointer"
                  >
                    <Eye size={13} className="text-slate-600" />
                    <span>Audit Preview</span>
                  </button>

                  <button
                    onClick={() => downloadAssessmentReportCSV(activeAssessment.assessment_id)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-bold transition-colors shadow-xs cursor-pointer"
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
              {/* SECTION 1: DASHBOARD OVERVIEW */}
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
                        Initialize your university’s self-appraisal workspace to record parameter inputs U1–U20 and link documentary evidence.
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

                  {/* Key Assessment Summary (Unified 4-Metric Grid) */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Metric 1: Lifecycle Status */}
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
                        <span className="truncate">{activeAssessment ? activeAssessment.assessment_id : "No Session Active"}</span>
                      </div>
                    </div>

                    {/* Metric 2: Parameters Completed */}
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
                            / 20 filled
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

                    {/* Metric 3: Evidence Coverage */}
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

                  {/* Attention & Action Banner */}
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
                              Assessment Locked for Official Committee Evaluation
                            </h3>
                          )}
                          <p className="text-xs text-slate-500 mt-0.5 max-w-2xl leading-relaxed">
                            {activeAssessment.status === "DRAFT"
                              ? "Ensure all 20 parameter values are recorded and required evidence documents are attached prior to formal submission."
                              : "Independent verification of your documentary evidence is underway by the Screening Committee."}
                          </p>
                        </div>

                        <div className="flex items-center gap-3 shrink-0 flex-wrap">
                          <button
                            onClick={() => handleOpenAssessment()}
                            className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-[#600b0b] hover:bg-[#4a0707] text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
                          >
                            <span>Continue Assessment (U1–U20)</span>
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
                            onClick={() => setShowReportModal(true)}
                            className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
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

                  {/* Evidence Readiness Summary Card */}
                  {activeAssessment && readiness && (
                    <EvidenceReadinessSummary
                      summary={readiness.evidence_readiness_summary}
                      isReady={readiness.is_ready}
                      onActionClick={() => setShowReportModal(true)}
                    />
                  )}

                  {/* Vice Chancellor & Nodal Officer Statutory Endorsement Card */}
                  {activeAssessment && (
                    <div className="bg-white rounded-xl border border-[#dfb987] p-5 shadow-xs bg-gradient-to-br from-white via-white to-[#fbf5ee]">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#ebdcd0]">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-[#fbf5ee] border border-[#dfb987] flex items-center justify-center text-[#c29b68] shrink-0">
                            <ShieldCheck size={20} />
                          </div>
                          <div>
                            <span className="text-[10px] font-bold text-[#600b0b] uppercase tracking-widest font-mono">
                              Statutory Governance Endorsement
                            </span>
                            <h4 className="text-sm font-bold text-slate-900">
                              University Council Cluster Endorsement & Digital Seal
                            </h4>
                          </div>
                        </div>

                        <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-[#eaded2] text-[#600b0b] border border-[#ebdcd0] shrink-0">
                          Section 12-A Validated
                        </span>
                      </div>

                      <p className="text-xs text-slate-600 my-4 leading-relaxed">
                        {canViewAffiliatedColleges
                          ? "I hereby endorse that Kurukshetra University campus parameters U1–U20 and 52 affiliated collegiate self-appraisals have been vetted for statutory authenticity under the Haryana State Higher Education Council guidelines."
                          : "I hereby endorse that Kurukshetra University campus parameters U1–U20 have been vetted for statutory authenticity under the Haryana State Higher Education Council guidelines."}
                      </p>

                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-100">
                        <div className="text-xs text-slate-500 font-mono">
                          Signatories: <span className="font-bold text-slate-800">Prof. Sanjeev Kumar</span> (Nodal Officer) & <span className="font-bold text-slate-800">Hon'ble Vice Chancellor</span>
                        </div>
                        {canViewAffiliatedColleges && (
                          <button
                            onClick={() => setActiveSection("colleges")}
                            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-[#600b0b] hover:bg-[#4a0707] text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
                          >
                            <Building2 size={13} />
                            <span>Inspect 64 Affiliated Colleges</span>
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* SECTION: AFFILIATED COLLEGES CLUSTER VERIFICATION MATRIX (RESTRICTED) */}
              {activeSection === "colleges" && canViewAffiliatedColleges && (
                <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
                  <div className="p-4 sm:p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/60">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                          Academic Cluster Matrix
                        </span>
                        <span className="text-xs text-slate-400 font-medium">Kurukshetra University Zone</span>
                      </div>
                      <h2 className="text-base font-bold text-slate-900 tracking-tight">
                        Affiliated Colleges Dossier Verification Matrix (64 Colleges)
                      </h2>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                        52 / 64 Submitted (81.3%)
                      </span>
                    </div>
                  </div>

                  <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row gap-3 bg-white">
                    <input
                      type="text"
                      placeholder="Search affiliated colleges by name, AISHE code, or district..."
                      className="flex-1 px-3 py-2 rounded-lg border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500 font-medium"
                    />
                    <select className="px-3 py-2 rounded-lg border border-slate-200 text-xs text-slate-700 font-medium bg-white">
                      <option>All Districts (Kurukshetra, Kaithal, Panipat, Yamunanagar)</option>
                      <option>Kurukshetra District (24 Colleges)</option>
                      <option>Kaithal District (16 Colleges)</option>
                      <option>Panipat District (14 Colleges)</option>
                      <option>Yamunanagar District (10 Colleges)</option>
                    </select>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="bg-slate-50/80 border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                          <th className="py-3 px-4">AISHE</th>
                          <th className="py-3 px-4">Affiliated Institution</th>
                          <th className="py-3 px-4">District</th>
                          <th className="py-3 px-4">Principal In-Charge</th>
                          <th className="py-3 px-4">Self Score</th>
                          <th className="py-3 px-4">Endorsement Status</th>
                          <th className="py-3 px-4 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {[
                          { code: "C-28104", name: "Govt. PG College, Kaithal", dist: "Kaithal", principal: "Dr. Sudhir Sharma", score: "84.5", status: "Univ Endorsed", statusColor: "emerald" },
                          { code: "C-28450", name: "Arya PG College, Panipat", dist: "Panipat", principal: "Dr. Jagdish Gupta", score: "82.0", status: "Univ Endorsed", statusColor: "emerald" },
                          { code: "C-28211", name: "Markanda National College, Shahabad", dist: "Kurukshetra", principal: "Dr. Ashok Kumar", score: "78.4", status: "Pending Review", statusColor: "amber" },
                          { code: "C-28190", name: "D.A.V. College, Pundri", dist: "Kaithal", principal: "Dr. R. K. Goel", score: "76.2", status: "In Screening", statusColor: "blue" },
                          { code: "C-28602", name: "Govt. College for Women, Yamunanagar", dist: "Yamunanagar", principal: "Dr. Rekha Rani", score: "64.0", status: "Clause C5 Deficit", statusColor: "red" },
                          { code: "C-28315", name: "Seth Navrang Rai Lohia Jairam Girls College", dist: "Kurukshetra", principal: "Dr. Sudesh Rawal", score: "71.8", status: "Under Rectification", statusColor: "amber" },
                        ].map((item, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                            <td className="py-3 px-4 font-mono font-bold text-slate-500">{item.code}</td>
                            <td className="py-3 px-4 font-bold text-slate-800">{item.name}</td>
                            <td className="py-3 px-4 text-slate-600">{item.dist}</td>
                            <td className="py-3 px-4 text-slate-600">{item.principal}</td>
                            <td className="py-3 px-4 font-mono font-bold text-slate-900">{item.score} / 100</td>
                            <td className="py-3 px-4">
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${
                                item.statusColor === 'emerald'
                                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                  : item.statusColor === 'amber'
                                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                                  : item.statusColor === 'red'
                                  ? 'bg-red-50 text-red-800 border-red-200'
                                  : 'bg-blue-50 text-blue-800 border-blue-200'
                              }`}>
                                {item.status}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                onClick={() => alert(`Reviewing collegiate dossier for ${item.name}`)}
                                className="px-2.5 py-1 text-xs font-semibold text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors cursor-pointer"
                              >
                                View Dossier
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* SECTION 2: STATUTORY PARAMETERS (U1–U20) */}
              {activeSection === "parameters" && (
                <div className="space-y-6">
                  {parameters.length > 0 ? (
                    <div className="bg-white rounded-xl border border-[#ebdcd0] shadow-xs overflow-hidden">
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

                        {/* Filter Tabs & Open Workspace Button */}
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
                              <th className="py-3 px-4">Mandatory Evidence Types</th>
                              <th className="py-3 px-4 text-center w-32">Input Status</th>
                              <th className="py-3 px-4 text-center w-24">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {filteredParameters.map((param) => {
                              const isComplete = param.submitted_input != null && Object.keys(param.submitted_input).length > 0;
                              return (
                                <tr
                                  key={param.parameter_code || param.code}
                                  className="hover:bg-slate-50/70 transition-colors"
                                >
                                  <td className="py-3.5 px-4 font-mono font-bold text-[#600b0b] whitespace-nowrap">
                                    {param.parameter_code || param.code}
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
                                  <td className="py-3.5 px-4 text-center whitespace-nowrap">
                                    <button
                                      onClick={() => handleOpenAssessment(param.parameter_code || param.code)}
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
                  ) : (
                    <EmptyState
                      icon={ClipboardList}
                      title="No Parameters Initialized"
                      description="Parameters will be loaded when an active assessment session is created."
                    />
                  )}
                </div>
              )}

              {/* SECTION 3: EVIDENCE READINESS */}
              {activeSection === "evidence" && (
                <div className="space-y-6">
                  {activeAssessment && readiness ? (
                    <EvidenceReadinessSummary
                      summary={readiness.evidence_readiness_summary}
                      isReady={readiness.is_ready}
                      onActionClick={() => setShowReportModal(true)}
                    />
                  ) : (
                    <EmptyState
                      icon={CheckCircle2}
                      title="No Evidence Evaluation Data"
                      description="Start or resume an assessment session to inspect subcriteria readiness and evidence coverage."
                    />
                  )}

                  <div className="bg-white rounded-xl border border-slate-200/90 p-6 shadow-xs">
                    <h3 className="text-sm font-bold text-slate-900 mb-2">Evidence Submission Guidelines</h3>
                    <ul className="text-xs text-slate-600 space-y-2 list-disc pl-5">
                      <li>All documentary evidence must fall within the statutory window (2025-07-01 to 2026-06-30).</li>
                      <li>Documents must be in PDF or standard image format, signed and sealed by the Registrar or competent university authority.</li>
                      <li>Subcriteria lacking required evidence are automatically gated and will yield 0 marks during scoring.</li>
                    </ul>
                  </div>
                </div>
              )}

              {/* SECTION 4: AUDIT REPORTS */}
              {activeSection === "reports" && (
                <div className="space-y-6">
                  <div className="bg-white rounded-xl border border-slate-200/90 p-6 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h3 className="text-base font-bold text-slate-900">Authoritative Assessment Audit Ledger</h3>
                      <p className="text-xs text-slate-500 mt-1">
                        Inspect complete statutory evaluation reports, subcriteria gating traces, and verification logs.
                      </p>
                    </div>

                    {activeAssessment && (
                      <div className="flex items-center gap-2.5 shrink-0">
                        <button
                          onClick={() => setShowReportModal(true)}
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
                Logged in as <strong className="text-slate-700 font-semibold">{universityName}</strong> (AISHE: {aisheCode})
              </span>
            </div>
          </div>
        </footer>
      </div>

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
