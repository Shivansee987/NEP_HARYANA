import { useState } from "react";
import {
  Send,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Circle,
  FileText,
  ShieldCheck,
  ChevronRight,
  Lock,
  ArrowRight,
} from "lucide-react";
import { StatusBadge } from "../common";

export default function ReviewSubmitView({
  framework = "COLLEGE_2026",
  assessment = {},
  parameterCodes = [],
  parameterDefs = {},
  parameterStatusMap = {},
  rawInputsMap = {},
  evidenceAssociations = [],
  onNavigateToParam = () => {},
  onSubmitAssessment = async () => {},
  submitting = false,
}) {
  const [declared, setDeclared] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const isCollege = framework.includes("COLLEGE") || parameterCodes[0]?.startsWith("C");
  const frameworkName = isCollege ? "COLLEGE_2026" : "UNIVERSITY_2026";
  const totalCount = parameterCodes.length;

  const completedCodes = parameterCodes.filter((c) => parameterStatusMap[c] === "COMPLETE");
  const inProgressCodes = parameterCodes.filter((c) => parameterStatusMap[c] === "IN_PROGRESS");
  const notStartedCodes = parameterCodes.filter(
    (c) => !parameterStatusMap[c] || parameterStatusMap[c] === "NOT_STARTED"
  );

  const completedCount = completedCodes.length;
  const incompleteCount = totalCount - completedCount;
  const isSubmitted = assessment.status === "SUBMITTED";

  // Count evidence by parameter
  const evidenceCountByParam = {};
  evidenceAssociations.forEach((assoc) => {
    const pCode = (assoc.parameter_id || "").toUpperCase();
    evidenceCountByParam[pCode] = (evidenceCountByParam[pCode] || 0) + 1;
  });

  const handleSubmit = async () => {
    if (!declared && !isSubmitted) {
      alert("Please confirm the statutory declaration before submitting.");
      return;
    }
    setSubmitError(null);
    try {
      await onSubmitAssessment();
    } catch (err) {
      console.error("Submission failed:", err);
      setSubmitError(
        err?.message ||
          "Assessment submission failed. Please verify that all required inputs and statutory parameters are satisfied."
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-800 border border-blue-200 uppercase tracking-wider">
                {frameworkName}
              </span>
              <span className="text-slate-300">•</span>
              <span className="text-xs font-mono text-slate-500">
                Session: {assessment.assessment_id || "Active Session"}
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              Pre-Submission Institutional Review ({totalCount} Parameters)
            </h2>
            <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
              Verify all parameter inputs and documentary evidence associations before final submission
              to the Screening Committee.
            </p>
          </div>

          <div className="shrink-0">
            <StatusBadge status={assessment.status || "DRAFT"} size="md" />
          </div>
        </div>
      </div>

      {/* Submitted State Notice */}
      {isSubmitted && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 flex items-start gap-3 shadow-xs">
          <CheckCircle2 size={20} className="text-emerald-600 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold text-sm text-emerald-950">
              Assessment Successfully Submitted for Official Committee Review
            </h4>
            <p className="text-xs text-emerald-800 mt-0.5 leading-relaxed">
              This self-appraisal session is formally recorded and locked. Assigned screening committee
              reviewers are independently examining your documentary evidence.
            </p>
            {assessment.submitted_at && (
              <p className="text-[11px] font-mono font-semibold text-emerald-700 mt-1">
                Submitted At: {new Date(assessment.submitted_at).toLocaleString()}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Completion Metrics Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span className="font-bold uppercase tracking-wider text-[10px]">Completed Parameters</span>
            <CheckCircle2 size={14} className="text-emerald-600" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-extrabold text-slate-900">{completedCount}</span>
            <span className="text-xs font-semibold text-slate-400">/ {totalCount}</span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span className="font-bold uppercase tracking-wider text-[10px]">Incomplete Parameters</span>
            <Clock size={14} className="text-amber-500" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-extrabold text-slate-900">{incompleteCount}</span>
            <span className="text-xs font-semibold text-slate-400">pending completion</span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span className="font-bold uppercase tracking-wider text-[10px]">Evidence Proofs Linked</span>
            <FileText size={14} className="text-purple-600" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-extrabold text-slate-900">{evidenceAssociations.length}</span>
            <span className="text-xs font-semibold text-slate-400">subcriterion proofs</span>
          </div>
        </div>
      </div>

      {/* Incomplete Warning if not submitted and incompleteCount > 0 */}
      {!isSubmitted && incompleteCount > 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-amber-950">
              Notice: {incompleteCount} parameter(s) have not been marked complete.
            </p>
            <p className="text-amber-800 mt-0.5 leading-relaxed">
              You may submit now if your institution has recorded all applicable data, or return to
              parameters ({inProgressCodes.concat(notStartedCodes).slice(0, 5).join(", ")}
              {incompleteCount > 5 ? "..." : ""}) to complete missing entries.
            </p>
          </div>
        </div>
      )}

      {/* Error Notice */}
      {submitError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start gap-2">
          <AlertTriangle size={16} className="shrink-0 mt-0.5 text-red-600" />
          <span>{submitError}</span>
        </div>
      )}

      {/* Complete Parameters Breakdown Table */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
          <h3 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight">
            Parameter Completion Audit Ledger ({totalCount} Items)
          </h3>
          <span className="text-xs text-slate-500 font-mono">
            {completedCount}/{totalCount} Completed
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4 w-16">Code</th>
                <th className="py-3 px-4">Parameter Title</th>
                <th className="py-3 px-4 text-center w-24">Max Marks</th>
                <th className="py-3 px-4 text-center w-28">Status</th>
                <th className="py-3 px-4 text-center w-36">Evidence Proofs</th>
                <th className="py-3 px-4 text-center w-28">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {parameterCodes.map((code) => {
                const def = parameterDefs[code] || {};
                const status = parameterStatusMap[code] || "NOT_STARTED";
                const evCount = evidenceCountByParam[code] || 0;

                return (
                  <tr key={code} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-blue-700 whitespace-nowrap">
                      {code}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-900 max-w-xs sm:max-w-md">
                      {def.title || `Parameter ${code}`}
                    </td>
                    <td className="py-3 px-4 text-center font-bold text-slate-700 whitespace-nowrap">
                      {def.maxMarks ?? def.max_marks ?? 0} pts
                    </td>
                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      {status === "COMPLETE" ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-50 text-emerald-800 border border-emerald-200">
                          <CheckCircle2 size={10} className="text-emerald-600" />
                          <span>Complete</span>
                        </span>
                      ) : status === "IN_PROGRESS" ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-blue-50 text-blue-800 border border-blue-200">
                          <Clock size={10} className="text-blue-600" />
                          <span>In Progress</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-slate-100 text-slate-500 border border-slate-200">
                          <Circle size={9} className="text-slate-400" />
                          <span>Not Started</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      {evCount > 0 ? (
                        <span className="font-semibold text-purple-700">
                          {evCount} proof(s)
                        </span>
                      ) : (
                        <span className="text-slate-400 italic">None attached</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      <button
                        onClick={() => onNavigateToParam(code)}
                        className="text-xs font-bold text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                      >
                        {isSubmitted ? "View Data" : "Edit Inputs"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Submission Actions Box */}
      {!isSubmitted && (
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900">
            Institutional Submission Certification
          </h3>

          <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 space-y-2">
            <label className="flex items-start gap-2.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={declared}
                onChange={(e) => setDeclared(e.target.checked)}
                className="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
              />
              <span className="leading-relaxed">
                I hereby certify on behalf of the institution that all data submitted across parameters{" "}
                <strong className="font-mono">
                  {parameterCodes[0]}–{parameterCodes[parameterCodes.length - 1]}
                </strong>{" "}
                and all associated documentary proofs are genuine, officially approved, and substantiated
                by institutional records. I understand that submission locks these records for Screening
                Committee evaluation.
              </span>
            </label>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <ShieldCheck size={14} className="text-blue-600 shrink-0" />
              <span>Submission uses the modern Phase W2 direct submission pipeline.</span>
            </div>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting || !declared}
              className="inline-flex items-center justify-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <Send size={14} />
              <span>{submitting ? "Submitting Assessment..." : "Submit Assessment to Committee"}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
