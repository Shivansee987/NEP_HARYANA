import { Send, RotateCcw, Lock, Award, Ban, ChevronRight, CheckCircle2 } from "lucide-react";
import BlockingNotice from "../common/BlockingNotice";

/**
 * SubmissionStatusPanel — the Nodal Officer's view of where the assessment stands and what to do next.
 *
 * Every state shown here comes from the backend: lifecycle status, submission readiness
 * (readiness.submission_ready / submission_issues), committee review history and the scoring evaluation.
 */

const EDITABLE = ["DRAFT", "RETURNED"];

const REVIEW_STAGES = {
  SUBMITTED: "Submitted — awaiting Screening Committee review",
  UNDER_REVIEW: "Under Screening Committee review",
  EVALUATED: "Evaluated — committee review in progress",
  CERTIFICATION_PENDING: "Review complete — awaiting certification",
  FINALIZED: "Review finalized — awaiting certification",
};

const formatIssue = (issue) =>
  `${issue.subcriterion || issue.parameter || "Assessment"}${issue.field ? ` · ${issue.field}` : ""}: ${issue.message}`;

const formatDate = (value) => (value ? new Date(value).toLocaleString() : "");

const latestAction = (history, action) => (history || []).find((rec) => rec.action === action) || null;

function ReviewerRemark({ record, tone }) {
  if (!record) return null;
  return (
    <div className={`rounded-lg border p-3 text-xs space-y-1 ${tone}`}>
      <p className="font-bold">{record.reason || "No reason recorded."}</p>
      {record.comments && <p className="leading-relaxed">{record.comments}</p>}
      <p className="opacity-70 font-mono text-[11px]">
        {record.reviewer_name || "Screening Committee"} · {formatDate(record.created_at)}
      </p>
    </div>
  );
}

export default function SubmissionStatusPanel({
  status,
  readiness,
  scoring,
  reviewHistory,
  submitting = false,
  onSubmit,
  onOpenWorkspace,
  compact = false,
}) {
  const isEditable = EDITABLE.includes(status);
  const isReturned = status === "RETURNED";
  const issues = readiness?.submission_issues || [];
  const canSubmit = isEditable && readiness?.submission_ready === true;

  // --- Certified: frozen final result ---------------------------------------------------------
  if (status === "CERTIFIED") {
    const award = scoring?.award_classification;
    return (
      <div className="bg-white rounded-xl border border-emerald-200 p-5 shadow-xs space-y-3">
        <div className="flex items-center gap-2">
          <Award size={18} className="text-emerald-700" />
          <h3 className="text-sm sm:text-base font-bold text-slate-900">Assessment Certified — Final Result</h3>
        </div>
        {scoring ? (
          <div className="flex flex-wrap items-end gap-6">
            <div>
              <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Certified Score</p>
              <p className="text-3xl font-extrabold text-slate-900 font-mono">
                {scoring.final_certified_total ?? scoring.authoritative_total}
                <span className="text-sm font-semibold text-slate-400"> / {scoring.max_marks}</span>
              </p>
            </div>
            <div>
              <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Award</p>
              <p className="text-sm font-bold text-emerald-800">
                {award?.award_level || award?.message || "—"}
              </p>
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-500">The certified result could not be loaded. Use Refresh to retry.</p>
        )}
        <p className="text-xs text-slate-500">This result is frozen and can no longer be changed.</p>
      </div>
    );
  }

  // --- Blocked ----------------------------------------------------------------------------------
  if (status === "BLOCKED") {
    return (
      <div className="bg-white rounded-xl border border-red-200 p-5 shadow-xs space-y-3">
        <div className="flex items-center gap-2">
          <Ban size={18} className="text-red-700" />
          <h3 className="text-sm sm:text-base font-bold text-slate-900">Review Blocked by the Screening Committee</h3>
        </div>
        <ReviewerRemark record={latestAction(reviewHistory, "REVIEW_BLOCKED")} tone="bg-red-50 border-red-200 text-red-900" />
        <p className="text-xs text-slate-500">Contact the State DHE administrator to resolve this assessment.</p>
      </div>
    );
  }

  // --- Under review (locked) --------------------------------------------------------------------
  if (!isEditable) {
    return (
      <div className="bg-white rounded-xl border border-[#ebdcd0] p-5 shadow-xs space-y-2">
        <div className="flex items-center gap-2">
          <Lock size={16} className="text-[#600b0b]" />
          <h3 className="text-sm sm:text-base font-bold text-slate-900">{REVIEW_STAGES[status] || status}</h3>
        </div>
        <p className="text-xs text-slate-500 leading-relaxed">
          Inputs and evidence are locked while the Screening Committee reviews your submission. If the committee
          returns the assessment for correction, its remarks will appear here and editing will reopen.
        </p>
        {onOpenWorkspace && (
          <button
            onClick={onOpenWorkspace}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-[#600b0b] hover:underline cursor-pointer"
          >
            <span>View submitted assessment</span>
            <ChevronRight size={13} />
          </button>
        )}
      </div>
    );
  }

  // --- Draft / Returned: prepare and (re)submit ------------------------------------------------
  return (
    <div className={`bg-white rounded-xl border p-5 shadow-xs space-y-4 ${isReturned ? "border-amber-300" : "border-[#ebdcd0]"}`}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            {isReturned ? <RotateCcw size={16} className="text-amber-700" /> : <Send size={16} className="text-[#600b0b]" />}
            <h3 className="text-sm sm:text-base font-bold text-slate-900">
              {isReturned ? "Returned for Correction — Fix and Resubmit" : "Complete U1–U20 and Submit for Screening"}
            </h3>
          </div>
          <p className="text-xs text-slate-500 max-w-2xl leading-relaxed">
            {isReturned
              ? "Address the committee's remarks below, correct the affected parameters or evidence, then resubmit."
              : "Record all parameter values and attach the required evidence. Submission locks inputs for committee review."}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          {onOpenWorkspace && (
            <button
              onClick={onOpenWorkspace}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-[#600b0b] hover:bg-[#4a0707] text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
            >
              <span>{isReturned ? "Open Assessment to Correct" : "Continue Assessment (U1–U20)"}</span>
              <ChevronRight size={13} />
            </button>
          )}
          {onSubmit && (
            <button
              onClick={onSubmit}
              disabled={!canSubmit || submitting}
              title={canSubmit ? "" : "Resolve the listed issues before submitting"}
              className="inline-flex items-center gap-2 px-3.5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-all shadow-xs disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <Send size={13} />
              <span>{submitting ? "Submitting..." : isReturned ? "Resubmit Assessment" : "Submit Assessment"}</span>
            </button>
          )}
        </div>
      </div>

      {isReturned && (
        <ReviewerRemark
          record={latestAction(reviewHistory, "RETURNED_FOR_CORRECTION")}
          tone="bg-amber-50 border-amber-200 text-amber-900"
        />
      )}

      {!readiness ? null : issues.length > 0 ? (
        <BlockingNotice
          type="warning"
          title={`Submission blocked: ${issues.length} input issue${issues.length === 1 ? "" : "s"} to correct`}
          reasons={(compact ? issues.slice(0, 3) : issues).map(formatIssue).concat(
            compact && issues.length > 3 ? [`…and ${issues.length - 3} more`] : []
          )}
          actionLabel={onOpenWorkspace ? "Fix in assessment form" : null}
          onAction={onOpenWorkspace}
        />
      ) : (
        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
          <CheckCircle2 size={14} />
          <span>All recorded inputs pass validation — the assessment is ready to {isReturned ? "resubmit" : "submit"}.</span>
        </div>
      )}

      {!compact && readiness && !readiness.is_ready && (
        <p className="text-xs text-slate-500 leading-relaxed">
          Evidence is verified by the Screening Committee after submission. Subcriteria without the required
          documentary evidence score 0 — check <strong>Evidence Readiness</strong> before submitting.
        </p>
      )}
    </div>
  );
}
