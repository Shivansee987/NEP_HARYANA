import {
  LayoutDashboard,
  CheckCircle2,
  Clock,
  Circle,
  Send,
  ArrowLeft,
  X,
  Building2,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import hshecLogo from "../../assets/hshec_logo.jpeg";

export default function AssessmentStepperSidebar({
  framework = "COLLEGE_2026",
  institutionName = "",
  assessmentId = "",
  parameterCodes = [],
  parameterTitles = {},
  parameterStatusMap = {},
  activeStep = "overview",
  onSelectStep = () => {},
  onBackToDashboard = () => {},
  sidebarOpen = false,
  setSidebarOpen = () => {},
  status = "DRAFT",
}) {
  const isCollege = framework.includes("COLLEGE") || parameterCodes[0]?.startsWith("C");
  const frameworkLabel = isCollege ? "College Assessment" : "University Assessment";
  const frameworkBadge = isCollege ? "COLLEGE_2026" : "UNIVERSITY_2026";
  const totalCount = parameterCodes.length;

  const completedCount = parameterCodes.filter(
    (code) => parameterStatusMap[code] === "COMPLETE"
  ).length;

  const inProgressCount = parameterCodes.filter(
    (code) => parameterStatusMap[code] === "IN_PROGRESS"
  ).length;

  const percentComplete = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const renderStatusIcon = (code) => {
    const s = parameterStatusMap[code] || "NOT_STARTED";
    if (s === "COMPLETE") {
      return (
        <span
          className="w-4 h-4 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0"
          title="Complete"
        >
          <CheckCircle2 size={12} className="stroke-[2.5]" />
        </span>
      );
    }
    if (s === "IN_PROGRESS") {
      return (
        <span
          className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center shrink-0 font-bold text-[10px]"
          title="In progress"
        >
          ◐
        </span>
      );
    }
    return (
      <span
        className="w-4 h-4 rounded-full border border-slate-300 bg-white text-slate-300 flex items-center justify-center shrink-0"
        title="Not started"
      >
        <Circle size={8} />
      </span>
    );
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-40 lg:hidden"
        />
      )}

      <aside
        className={`fixed lg:sticky top-0 inset-y-0 left-0 w-72 bg-white border-r border-slate-200/90 z-50 flex flex-col justify-between transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full lg:shadow-none"
        } h-screen`}
      >
        {/* Header Branding */}
        <div className="flex flex-col min-h-0 flex-1">
          <div className="h-16 px-4 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-slate-50 border border-slate-200 p-1 flex items-center justify-center shrink-0">
                <img src={hshecLogo} alt="HSHEC" className="w-full h-full object-contain" />
              </div>
              <div className="min-w-0">
                <h1 className="text-xs font-bold text-slate-900 leading-tight truncate">
                  NEP Excellence 2026
                </h1>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider">
                    {frameworkLabel}
                  </span>
                  <span className="text-slate-300 text-[10px]">•</span>
                  <span className="text-[9px] font-mono font-bold text-slate-500 bg-slate-100 px-1 py-0.2 rounded">
                    {frameworkBadge}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-slate-400 hover:text-slate-600 p-1 rounded-md"
            >
              <X size={18} />
            </button>
          </div>

          {/* Institution Context & Overall Progress */}
          <div className="p-3.5 bg-slate-50/80 border-b border-slate-200/70 shrink-0">
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider truncate">
                {institutionName || "Institution Workspace"}
              </span>
              <span
                className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider border ${
                  status === "SUBMITTED"
                    ? "bg-purple-50 text-purple-800 border-purple-200"
                    : "bg-blue-50 text-blue-800 border-blue-200"
                }`}
              >
                {status}
              </span>
            </div>

            <div className="flex items-baseline justify-between mb-1.5">
              <span className="text-xs font-bold text-slate-900">
                {completedCount} / {totalCount} completed
              </span>
              <span className="text-xs font-mono font-bold text-blue-700">{percentComplete}%</span>
            </div>

            <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 rounded-full transition-all duration-300"
                style={{ width: `${percentComplete}%` }}
              />
            </div>
          </div>

          {/* Stepper Navigation List */}
          <div className="flex-1 overflow-y-auto p-2.5 space-y-1">
            {/* Step: Overview */}
            <button
              onClick={() => {
                onSelectStep("overview");
                setSidebarOpen(false);
              }}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                activeStep === "overview"
                  ? "bg-blue-50 text-blue-900 font-bold border border-blue-200"
                  : "text-slate-700 hover:bg-slate-100/80"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <LayoutDashboard size={14} className={activeStep === "overview" ? "text-blue-600" : "text-slate-400"} />
                <span>Assessment Overview</span>
              </div>
            </button>

            {/* Parameter Section Header */}
            <div className="pt-2.5 pb-1 px-3 flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              <span>Parameters ({totalCount})</span>
              <span className="text-slate-400 font-mono text-[9px]">
                {completedCount}/{totalCount}
              </span>
            </div>

            {/* List of Parameters */}
            <div className="space-y-0.5">
              {parameterCodes.map((code) => {
                const title = parameterTitles[code] || `Parameter ${code}`;
                const isActive = activeStep === code;

                return (
                  <button
                    key={code}
                    onClick={() => {
                      onSelectStep(code);
                      setSidebarOpen(false);
                    }}
                    className={`w-full flex items-center justify-between gap-2 px-3 py-1.5 rounded-lg text-xs transition-colors cursor-pointer text-left ${
                      isActive
                        ? "bg-slate-900 text-white font-bold shadow-xs"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span
                        className={`font-mono text-[11px] font-bold shrink-0 ${
                          isActive ? "text-blue-300" : "text-blue-700"
                        }`}
                      >
                        {code}
                      </span>
                      <span className="truncate text-[11px] leading-tight" title={title}>
                        {title}
                      </span>
                    </div>

                    <div className="shrink-0">{renderStatusIcon(code)}</div>
                  </button>
                );
              })}
            </div>

            {/* Step: Review & Submit */}
            <div className="pt-2.5">
              <button
                onClick={() => {
                  onSelectStep("review");
                  setSidebarOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                  activeStep === "review"
                    ? "bg-emerald-50 text-emerald-900 font-bold border border-emerald-200"
                    : "text-slate-700 hover:bg-slate-100/80"
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <Send size={14} className={activeStep === "review" ? "text-emerald-600" : "text-slate-400"} />
                  <span>Review & Submit</span>
                </div>
                {completedCount === totalCount ? (
                  <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.2 rounded">
                    Ready
                  </span>
                ) : (
                  <span className="text-[10px] font-bold text-slate-500 font-mono">
                    {totalCount - completedCount} pending
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Footer / Return to Dashboard */}
        <div className="p-3 border-t border-slate-200/90 bg-white shrink-0">
          <button
            onClick={onBackToDashboard}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold transition-colors cursor-pointer"
          >
            <ArrowLeft size={13} />
            <span>Return to Dashboard</span>
          </button>
        </div>
      </aside>
    </>
  );
}
