import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  FileText,
  FileCheck2,
  ExternalLink,
  Download,
  History,
  Building2,
  GraduationCap,
  Calendar,
  ShieldCheck,
  ChevronRight,
  ChevronLeft,
  RotateCcw,
  Sparkles,
  Layers,
  ChevronDown,
  Info,
  Send,
  Loader2,
  Maximize2,
} from "lucide-react";
import {
  fetchAssessmentReviewDetail,
  verifyEvidenceAssociation,
  rejectEvidenceAssociation,
  fetchAssociationHistory,
  fetchAssociationDocumentBlob,
  startAssessmentReview,
  completeAssessmentReview,
} from "../../api/checker";
import { useAuth } from "../../context/AuthContext.jsx";
import { StatusBadge, DashboardSkeleton, EmptyState, ErrorState } from "../../components/common";
import {
  getParameterTitle,
  getSubcriterionTitle,
  REJECTION_REASON_CODES,
} from "../../utils/nepTaxonomy";

export default function CheckerAssessmentReview() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  // Primary Data State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [evidenceAssociations, setEvidenceAssociations] = useState([]);

  // Selected Evidence Association for inspection
  const [selectedAssocId, setSelectedAssocId] = useState(null);

  // Document Blob & Viewer State
  const [docBlobUrl, setDocBlobUrl] = useState(null);
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState(null);

  // Association History State
  const [historyList, setHistoryList] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  // Action / Feedback Modal State
  const [actionLoading, setActionLoading] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [rejectionCode, setRejectionCode] = useState("MISMATCHED_CRITERIA");
  const [actionFeedback, setActionFeedback] = useState(null); // { type: 'success'|'error', message }

  // Review Lifecycle State
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [completionRemarks, setCompletionRemarks] = useState("");
  const [completingReview, setCompletingReview] = useState(false);

  // Load Assessment Detail
  const loadAssessment = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAssessmentReviewDetail(assessmentId);
      setAssessment(data);
      const assocs = data.evidence_associations || [];
      setEvidenceAssociations(assocs);

      // Default to first association if none selected
      if (assocs.length > 0) {
        setSelectedAssocId((prev) => {
          if (prev && assocs.some((a) => a.id === prev || a.association_id === prev)) {
            return prev;
          }
          return assocs[0].id || assocs[0].association_id;
        });
      }
    } catch (err) {
      console.error("Failed to load assessment review detail:", err);
      setError(err.message || "Failed to load assessment details.");
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    loadAssessment();
  }, [loadAssessment]);

  // Current active association object
  const activeAssoc = useMemo(() => {
    if (!selectedAssocId || evidenceAssociations.length === 0) return null;
    return (
      evidenceAssociations.find(
        (a) => a.id === selectedAssocId || a.association_id === selectedAssocId
      ) || evidenceAssociations[0]
    );
  }, [selectedAssocId, evidenceAssociations]);

  // Load Document Blob whenever active association changes
  useEffect(() => {
    if (!activeAssoc) {
      setDocBlobUrl(null);
      return;
    }

    let isMounted = true;
    let createdUrl = null;

    const loadDoc = async () => {
      setDocLoading(true);
      setDocError(null);
      try {
        const lookupId = activeAssoc.id || activeAssoc.association_id;
        const blob = await fetchAssociationDocumentBlob(lookupId);
        if (!isMounted) return;
        createdUrl = URL.createObjectURL(blob);
        setDocBlobUrl(createdUrl);
      } catch (err) {
        if (!isMounted) return;
        console.error("Document streaming error:", err);
        setDocError(err.message || "Could not retrieve document stream.");
      } finally {
        if (isMounted) setDocLoading(false);
      }
    };

    loadDoc();

    return () => {
      isMounted = false;
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl);
      }
    };
  }, [activeAssoc]);

  // Load Association Verification History
  const loadHistory = useCallback(async () => {
    if (!activeAssoc) return;
    setHistoryLoading(true);
    try {
      const lookupId = activeAssoc.id || activeAssoc.association_id;
      const historyData = await fetchAssociationHistory(lookupId);
      setHistoryList(Array.isArray(historyData) ? historyData : []);
    } catch (err) {
      console.error("Error loading verification history:", err);
      setHistoryList([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [activeAssoc]);

  useEffect(() => {
    if (showHistory) {
      loadHistory();
    }
  }, [showHistory, loadHistory]);

  // Review Progress Metrics computed strictly from association list
  const metrics = useMemo(() => {
    const total = evidenceAssociations.length;
    const verified = evidenceAssociations.filter(
      (a) => a.verification_status === "VERIFIED"
    ).length;
    const rejected = evidenceAssociations.filter(
      (a) => a.verification_status === "REJECTED"
    ).length;
    const pending = total - (verified + rejected);
    const reviewed = verified + rejected;
    const percentReviewed = total > 0 ? Math.round((reviewed / total) * 100) : 0;
    return { total, verified, rejected, pending, reviewed, percentReviewed };
  }, [evidenceAssociations]);

  // Hierarchical Parameter -> Subcriterion grouping for left tree
  const parameterTree = useMemo(() => {
    const tree = {};
    evidenceAssociations.forEach((assoc) => {
      const pId = assoc.parameter_id;
      if (!tree[pId]) {
        tree[pId] = {
          parameterId: pId,
          title: getParameterTitle(assessment?.framework, pId),
          subcriteria: {},
        };
      }
      const sId = assoc.subcriterion_id;
      if (!tree[pId].subcriteria[sId]) {
        tree[pId].subcriteria[sId] = {
          subcriterionId: sId,
          title: getSubcriterionTitle(sId, tree[pId].title),
          associations: [],
        };
      }
      tree[pId].subcriteria[sId].associations.push(assoc);
    });
    return Object.values(tree);
  }, [evidenceAssociations, assessment?.framework]);

  // Navigation indices
  const currentAssocIndex = useMemo(() => {
    if (!activeAssoc) return -1;
    return evidenceAssociations.findIndex(
      (a) => (a.id || a.association_id) === (activeAssoc.id || activeAssoc.association_id)
    );
  }, [activeAssoc, evidenceAssociations]);

  const handleNextEvidence = () => {
    if (currentAssocIndex < evidenceAssociations.length - 1) {
      const nextAssoc = evidenceAssociations[currentAssocIndex + 1];
      setSelectedAssocId(nextAssoc.id || nextAssoc.association_id);
      setShowHistory(false);
      setActionFeedback(null);
    }
  };

  const handlePrevEvidence = () => {
    if (currentAssocIndex > 0) {
      const prevAssoc = evidenceAssociations[currentAssocIndex - 1];
      setSelectedAssocId(prevAssoc.id || prevAssoc.association_id);
      setShowHistory(false);
      setActionFeedback(null);
    }
  };

  // VERIFY ACTION
  const handleVerify = async () => {
    if (!activeAssoc) return;
    setActionLoading(true);
    setActionFeedback(null);
    try {
      const lookupId = activeAssoc.id || activeAssoc.association_id;
      const res = await verifyEvidenceAssociation(lookupId, {
        reason: `Subcriterion ${activeAssoc.subcriterion_id} substantiated and approved.`,
      });

      // Update state locally for this specific association only (strict sibling independence)
      setEvidenceAssociations((prev) =>
        prev.map((item) => {
          if ((item.id || item.association_id) === lookupId) {
            return {
              ...item,
              verification_status: "VERIFIED",
              latest_verification: {
                decision: "VERIFIED",
                verifier_email: user?.email || "Reviewer",
                reason: res.reason || "Approved",
                timestamp: new Date().toISOString(),
              },
            };
          }
          return item;
        })
      );

      setActionFeedback({
        type: "success",
        message: `Association ${activeAssoc.subcriterion_id} verified successfully.`,
      });

      // Reload history if currently open
      if (showHistory) loadHistory();
    } catch (err) {
      console.error("Verification failed:", err);
      setActionFeedback({
        type: "error",
        message: err.message || "Failed to verify association.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  // REJECT ACTION
  const handleConfirmReject = async () => {
    if (!activeAssoc || !rejectionReason.trim()) return;
    setActionLoading(true);
    try {
      const lookupId = activeAssoc.id || activeAssoc.association_id;
      const res = await rejectEvidenceAssociation(lookupId, {
        reason: rejectionReason.trim(),
        rejection_code: rejectionCode,
      });

      // Update state locally for this specific association only (strict sibling independence)
      setEvidenceAssociations((prev) =>
        prev.map((item) => {
          if ((item.id || item.association_id) === lookupId) {
            return {
              ...item,
              verification_status: "REJECTED",
              latest_verification: {
                decision: "REJECTED",
                verifier_email: user?.email || "Reviewer",
                reason: rejectionReason.trim(),
                rejection_code: rejectionCode,
                timestamp: new Date().toISOString(),
              },
            };
          }
          return item;
        })
      );

      setShowRejectModal(false);
      setRejectionReason("");
      setActionFeedback({
        type: "success",
        message: `Association ${activeAssoc.subcriterion_id} rejected with feedback.`,
      });

      // Reload history if currently open
      if (showHistory) loadHistory();
    } catch (err) {
      console.error("Rejection failed:", err);
      setActionFeedback({
        type: "error",
        message: err.message || "Failed to reject association.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  // START REVIEW ACTION
  const handleStartReview = async () => {
    setActionLoading(true);
    try {
      await startAssessmentReview(
        assessment?.framework,
        assessment?.assessment_id,
        "Screening committee commenced evaluation."
      );
      setAssessment((prev) => ({
        ...prev,
        status: "UNDER_REVIEW",
      }));
      setActionFeedback({
        type: "success",
        message: "Assessment lifecycle transitioned to UNDER_REVIEW.",
      });
    } catch (err) {
      console.error("Start review error:", err);
      setActionFeedback({
        type: "error",
        message: err.message || "Could not begin review.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  // COMPLETE REVIEW ACTION
  const handleCompleteReview = async () => {
    setCompletingReview(true);
    try {
      await completeAssessmentReview(
        assessment?.framework,
        assessment?.assessment_id,
        completionRemarks.trim() || "Screening committee review completed."
      );
      setShowCompleteModal(false);
      setAssessment((prev) => ({
        ...prev,
        status: "CERTIFICATION_PENDING",
      }));
      setActionFeedback({
        type: "success",
        message: "Assessment review successfully completed! Ready for certification.",
      });
    } catch (err) {
      console.error("Complete review error:", err);
      setActionFeedback({
        type: "error",
        message: err.message || "Could not complete review.",
      });
    } finally {
      setCompletingReview(false);
    }
  };

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (error || !assessment) {
    return (
      <ErrorState
        title="Assessment Not Found or Access Denied"
        message={error || "You do not have authorization to view this assessment or it does not exist."}
        onRetry={loadAssessment}
      />
    );
  }

  const isUniv = assessment.framework === "UNIVERSITY_2026";
  const canReview = assessment.status === "SUBMITTED" || assessment.status === "UNDER_REVIEW";

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Breadcrumb & Return Action */}
      <div className="flex items-center justify-between">
        <Link
          to="/checker/queue"
          className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-amber-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Review Queue</span>
        </Link>

        {assessment.status === "SUBMITTED" && (
          <button
            type="button"
            onClick={handleStartReview}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer disabled:opacity-50"
          >
            {actionLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PlayIcon />}
            <span>Start Active Review</span>
          </button>
        )}

        {assessment.status === "UNDER_REVIEW" && (
          <button
            type="button"
            onClick={() => setShowCompleteModal(true)}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Complete Review</span>
          </button>
        )}
      </div>

      {/* Assessment Header & Meta Box */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
                  isUniv
                    ? "bg-indigo-50 text-indigo-800 border-indigo-200"
                    : "bg-amber-50 text-amber-800 border-amber-200"
                }`}
              >
                {isUniv ? <Building2 className="w-3 h-3" /> : <GraduationCap className="w-3 h-3" />}
                <span>{isUniv ? "University Assessment" : "College Assessment"}</span>
              </span>
              <span className="text-xs font-mono text-slate-400">
                AISHE: {assessment.institution?.aishe_code || "—"}
              </span>
              <span className="text-xs text-slate-300">·</span>
              <span className="text-xs text-slate-500 font-medium">
                Cycle {assessment.academic_year || "2025–26"}
              </span>
            </div>

            <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
              {assessment.institution?.name}
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Assessment ID: <span className="font-mono font-medium">{assessment.assessment_id}</span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <div className="text-right">
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                Lifecycle Status
              </span>
              <div className="mt-1">
                <StatusBadge status={assessment.status} size="md" />
              </div>
            </div>

            <div className="text-right border-l border-slate-100 pl-4">
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                Submitted At
              </span>
              <span className="text-xs font-semibold text-slate-700 mt-1 block">
                {assessment.submitted_at
                  ? new Date(assessment.submitted_at).toLocaleDateString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })
                  : "Not yet submitted"}
              </span>
            </div>
          </div>
        </div>

        {/* Global Progress Bar */}
        <div className="mt-6 pt-5 border-t border-slate-100">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between text-xs mb-2 gap-2">
            <div className="flex items-center gap-2 font-bold text-slate-800">
              <Layers className="w-4 h-4 text-amber-600" />
              <span>Evidence Evaluation Progress:</span>
              <span className="text-slate-600 font-medium">
                {metrics.reviewed} of {metrics.total} reviewed ({metrics.percentReviewed}%)
              </span>
            </div>

            <div className="flex items-center gap-3 text-xs font-semibold">
              <span className="text-emerald-700 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                {metrics.verified} Verified
              </span>
              <span className="text-red-700 flex items-center gap-1">
                <XCircle className="w-3.5 h-3.5 text-red-600" />
                {metrics.rejected} Rejected
              </span>
              <span className="text-amber-700 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-amber-600" />
                {metrics.pending} Pending
              </span>
            </div>
          </div>

          {/* Segmented Progress Bar */}
          <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden flex">
            <div
              className="bg-emerald-500 h-full transition-all duration-300"
              style={{
                width: `${metrics.total > 0 ? (metrics.verified / metrics.total) * 100 : 0}%`,
              }}
              title={`${metrics.verified} Verified`}
            />
            <div
              className="bg-red-500 h-full transition-all duration-300"
              style={{
                width: `${metrics.total > 0 ? (metrics.rejected / metrics.total) * 100 : 0}%`,
              }}
              title={`${metrics.rejected} Rejected`}
            />
            <div
              className="bg-amber-400 h-full transition-all duration-300"
              style={{
                width: `${metrics.total > 0 ? (metrics.pending / metrics.total) * 100 : 0}%`,
              }}
              title={`${metrics.pending} Pending Review`}
            />
          </div>
        </div>

        {/* Global Feedback Banner */}
        {actionFeedback && (
          <div
            className={`mt-4 p-3.5 rounded-xl border flex items-center justify-between text-xs font-semibold ${
              actionFeedback.type === "success"
                ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                : "bg-red-50 border-red-200 text-red-800"
            }`}
          >
            <div className="flex items-center gap-2">
              {actionFeedback.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              )}
              <span>{actionFeedback.message}</span>
            </div>
            <button
              type="button"
              onClick={() => setActionFeedback(null)}
              className="text-slate-400 hover:text-slate-700 font-bold ml-4 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* Two-Column Review Workplace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Navigation Tree (4 cols on lg) */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden sticky top-20 max-h-[calc(100vh-6rem)] flex flex-col">
          <div className="p-4 border-b border-slate-100 bg-slate-50/80 flex items-center justify-between shrink-0">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Parameters & Subcriteria
              </h2>
              <span className="text-[11px] text-slate-400 font-medium">
                Select an evidence item to review
              </span>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 text-[10px] font-bold">
              {evidenceAssociations.length} Items
            </span>
          </div>

          <div className="divide-y divide-slate-100 overflow-y-auto p-2 space-y-2 flex-1">
            {parameterTree.map((param) => {
              const paramAssocs = Object.values(param.subcriteria).flatMap((s) => s.associations);
              const verifiedInParam = paramAssocs.filter(
                (a) => a.verification_status === "VERIFIED"
              ).length;
              const hasRejected = paramAssocs.some((a) => a.verification_status === "REJECTED");

              return (
                <div key={param.parameterId} className="rounded-xl border border-slate-100 bg-white">
                  <div className="p-3 bg-slate-50/50 rounded-t-xl flex items-center justify-between">
                    <div className="min-w-0 pr-2">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs font-black text-slate-800">
                          {param.parameterId}
                        </span>
                        <span className="text-xs font-bold text-slate-700 truncate">
                          {param.title}
                        </span>
                      </div>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                        hasRejected
                          ? "bg-red-50 text-red-700 border border-red-200"
                          : verifiedInParam === paramAssocs.length
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {verifiedInParam}/{paramAssocs.length} verified
                    </span>
                  </div>

                  {/* Subcriteria List */}
                  <div className="p-2 space-y-1.5">
                    {Object.values(param.subcriteria).map((sub) => (
                      <div key={sub.subcriterionId} className="space-y-1">
                        <div className="px-2 pt-1 text-[11px] font-bold text-slate-500">
                          {sub.subcriterionId}
                        </div>

                        {sub.associations.map((assoc) => {
                          const isSelected =
                            (assoc.id || assoc.association_id) ===
                            (activeAssoc?.id || activeAssoc?.association_id);
                          const isVerified = assoc.verification_status === "VERIFIED";
                          const isRejected = assoc.verification_status === "REJECTED";

                          return (
                            <button
                              key={assoc.id || assoc.association_id}
                              type="button"
                              onClick={() => {
                                setSelectedAssocId(assoc.id || assoc.association_id);
                                setShowHistory(false);
                                setActionFeedback(null);
                              }}
                              className={`w-full text-left p-2.5 rounded-lg text-xs transition-all flex items-start justify-between gap-2 cursor-pointer ${
                                isSelected
                                  ? "bg-amber-500/10 border-2 border-amber-600 text-amber-950 font-semibold shadow-2xs"
                                  : "hover:bg-slate-50 border border-transparent text-slate-700"
                              }`}
                            >
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-1.5 truncate">
                                  <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                  <span className="truncate font-medium">
                                    {assoc.original_filename || "Evidence Document"}
                                  </span>
                                </div>
                                <span className="text-[10px] text-slate-400 block truncate mt-0.5">
                                  {assoc.claim_description || assoc.subcriterion_evidence_type}
                                </span>
                              </div>

                              <div className="shrink-0 mt-0.5">
                                {isVerified ? (
                                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                                ) : isRejected ? (
                                  <XCircle className="w-4 h-4 text-red-600" />
                                ) : (
                                  <Clock className="w-4 h-4 text-amber-500" />
                                )}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Selected Evidence Inspection & Controls (8 cols on lg) */}
        <div className="lg:col-span-8 space-y-6">
          {activeAssoc ? (
            <div className="space-y-6">
              {/* Evidence Inspector Card */}
              <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6">
                {/* Header with Subcriterion, Status, Carousel Navigation */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-5 border-b border-slate-100 gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-sm font-black text-amber-800 bg-amber-50 px-2.5 py-0.5 rounded-md border border-amber-200">
                        {activeAssoc.subcriterion_id}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        Parameter {activeAssoc.parameter_id}
                      </span>
                      <span className="text-xs text-slate-300">·</span>
                      <span className="text-xs font-semibold text-slate-500">
                        Evidence {currentAssocIndex + 1} of {evidenceAssociations.length}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-slate-900 mt-1">
                      {getSubcriterionTitle(activeAssoc.subcriterion_id)}
                    </h3>
                  </div>

                  {/* Previous / Next Navigation Buttons */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handlePrevEvidence}
                      disabled={currentAssocIndex <= 0}
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors disabled:opacity-30 cursor-pointer"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                      <span>Previous</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleNextEvidence}
                      disabled={currentAssocIndex >= evidenceAssociations.length - 1}
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors disabled:opacity-30 cursor-pointer"
                    >
                      <span>Next</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Subcriterion & Association Metadata Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 my-5 bg-slate-50/60 p-4 rounded-xl border border-slate-100 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                      Original File
                    </span>
                    <span className="font-semibold text-slate-800 break-all mt-0.5 block">
                      {activeAssoc.original_filename}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                      Document Type
                    </span>
                    <span className="font-mono text-slate-700 mt-0.5 block">
                      {activeAssoc.subcriterion_evidence_type}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                      Page Reference
                    </span>
                    <span className="font-semibold text-slate-700 mt-0.5 block">
                      {activeAssoc.page_start && activeAssoc.page_end
                        ? `Pages ${activeAssoc.page_start}–${activeAssoc.page_end}`
                        : "Full document"}
                      {activeAssoc.section_identifier ? ` (${activeAssoc.section_identifier})` : ""}
                    </span>
                  </div>

                  <div className="sm:col-span-2">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                      Institution Claim / Description
                    </span>
                    <p className="text-slate-700 mt-0.5 font-medium leading-relaxed">
                      {activeAssoc.claim_description || "No specific claim text provided."}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                      Current Decision
                    </span>
                    <div className="mt-1">
                      {activeAssoc.verification_status === "VERIFIED" ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          <span>VERIFIED</span>
                        </span>
                      ) : activeAssoc.verification_status === "REJECTED" ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-50 text-red-800 border border-red-200">
                          <XCircle className="w-3.5 h-3.5 text-red-600" />
                          <span>REJECTED</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200">
                          <Clock className="w-3.5 h-3.5 text-amber-600" />
                          <span>PENDING REVIEW</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* If already rejected, show specific feedback reason box */}
                {activeAssoc.verification_status === "REJECTED" && activeAssoc.latest_verification && (
                  <div className="mb-5 p-4 rounded-xl bg-red-50/80 border border-red-200 text-xs">
                    <div className="flex items-center gap-2 font-bold text-red-900 mb-1">
                      <AlertCircle className="w-4 h-4 text-red-600" />
                      <span>Rejection Feedback:</span>
                      {activeAssoc.latest_verification.rejection_code && (
                        <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-red-100 text-red-800 border border-red-200">
                          {activeAssoc.latest_verification.rejection_code}
                        </span>
                      )}
                    </div>
                    <p className="text-red-800 leading-relaxed pl-6">
                      "{activeAssoc.latest_verification.reason}"
                    </p>
                    <div className="text-[10px] text-red-600/80 pl-6 mt-1.5">
                      Recorded by {activeAssoc.latest_verification.verifier_email} on{" "}
                      {new Date(activeAssoc.latest_verification.timestamp).toLocaleString("en-IN")}
                    </div>
                  </div>
                )}

                {/* Primary Review Action Buttons (Verify / Reject) */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100">
                  <div className="flex items-center gap-3 w-full sm:w-auto">
                    {/* VERIFY BUTTON */}
                    <button
                      type="button"
                      onClick={handleVerify}
                      disabled={actionLoading}
                      className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs hover:shadow-md transition-all cursor-pointer disabled:opacity-50"
                    >
                      {actionLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4" />
                      )}
                      <span>Verify Association</span>
                    </button>

                    {/* REJECT BUTTON */}
                    <button
                      type="button"
                      onClick={() => setShowRejectModal(true)}
                      disabled={actionLoading}
                      className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold shadow-xs hover:shadow-md transition-all cursor-pointer disabled:opacity-50"
                    >
                      <XCircle className="w-4 h-4" />
                      <span>Reject with Feedback</span>
                    </button>
                  </div>

                  {/* History Toggle Button */}
                  <button
                    type="button"
                    onClick={() => setShowHistory((prev) => !prev)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-semibold transition-colors cursor-pointer"
                  >
                    <History className="w-3.5 h-3.5 text-slate-500" />
                    <span>{showHistory ? "Hide Decision History" : "View Decision History"}</span>
                  </button>
                </div>
              </div>

              {/* Collapsible Append-Only Decision History Card */}
              {showHistory && (
                <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
                    <div className="flex items-center gap-2">
                      <History className="w-4 h-4 text-amber-700" />
                      <h4 className="text-sm font-bold text-slate-900">
                        Append-Only Verification Log ({activeAssoc.subcriterion_id})
                      </h4>
                    </div>
                    <span className="text-[11px] text-slate-400">
                      Immutable Historical Decisions
                    </span>
                  </div>

                  {historyLoading ? (
                    <div className="p-4 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-amber-600" />
                      <span>Loading historical audit trail...</span>
                    </div>
                  ) : historyList.length === 0 ? (
                    <p className="text-xs text-slate-400 italic text-center py-4">
                      No previous verification actions recorded on this subcriterion association.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {historyList.map((entry, idx) => (
                        <div
                          key={entry.verification_id || idx}
                          className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/50 text-xs flex flex-col gap-1"
                        >
                          <div className="flex items-center justify-between">
                            <span
                              className={`font-bold px-2 py-0.5 rounded-md text-[10px] ${
                                entry.decision === "VERIFIED"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "bg-red-100 text-red-800"
                              }`}
                            >
                              {entry.decision}
                            </span>
                            <span className="text-slate-400 font-mono text-[10px]">
                              {new Date(entry.timestamp).toLocaleString("en-IN")}
                            </span>
                          </div>
                          <p className="font-medium text-slate-800 mt-1">"{entry.reason}"</p>
                          <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                            <span>Reviewer: {entry.verifier_email}</span>
                            {entry.rejection_code && (
                              <span className="font-mono font-bold text-red-700">
                                Code: {entry.rejection_code}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Secure Integrated Document Viewer Card */}
              <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
                <div className="p-4 bg-slate-50/80 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-amber-700" />
                    <span className="text-xs font-bold text-slate-800">
                      Document Viewer: {activeAssoc.original_filename}
                    </span>
                  </div>

                  {docBlobUrl && (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => window.open(docBlobUrl, "_blank")}
                        className="inline-flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                      >
                        <Maximize2 className="w-3 h-3 text-slate-500" />
                        <span>Open in New Tab</span>
                      </button>
                      <a
                        href={docBlobUrl}
                        download={activeAssoc.original_filename || "evidence_document.pdf"}
                        className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                      >
                        <Download className="w-3 h-3" />
                        <span>Download</span>
                      </a>
                    </div>
                  )}
                </div>

                {/* PDF Viewer Body */}
                <div className="h-[600px] w-full bg-slate-100/60 relative flex items-center justify-center">
                  {docLoading ? (
                    <div className="flex flex-col items-center gap-3 text-slate-500 text-xs">
                      <Loader2 className="w-8 h-8 animate-spin text-amber-600" />
                      <span className="font-semibold">Streaming document securely...</span>
                    </div>
                  ) : docError ? (
                    <div className="p-6 text-center max-w-md">
                      <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
                      <h4 className="text-sm font-bold text-slate-800">Unable to Stream Document</h4>
                      <p className="text-xs text-slate-500 mt-1">{docError}</p>
                    </div>
                  ) : docBlobUrl ? (
                    <object
                      data={docBlobUrl}
                      type={activeAssoc.mime_type || "application/pdf"}
                      className="w-full h-full border-0"
                    >
                      <div className="p-8 text-center max-w-md">
                        <FileCheck2 className="w-10 h-10 text-amber-600 mx-auto mb-3" />
                        <h4 className="text-sm font-bold text-slate-800">Inline Preview Not Supported</h4>
                        <p className="text-xs text-slate-500 mt-1 mb-4">
                          Your browser cannot display this file type inline. Please open or download it using the actions above.
                        </p>
                        <a
                          href={docBlobUrl}
                          download={activeAssoc.original_filename || "evidence.pdf"}
                          className="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg text-xs font-bold shadow-xs hover:bg-amber-700"
                        >
                          <Download className="w-4 h-4" />
                          <span>Download File</span>
                        </a>
                      </div>
                    </object>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No document file available.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={FileText}
              title="No Evidence Item Selected"
              description="Please select an evidence item from the parameters tree on the left."
            />
          )}
        </div>
      </div>

      {/* REJECTION REASON MODAL */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2 text-red-600 font-bold text-sm">
                <XCircle className="w-5 h-5" />
                <span>Reject Evidence Association ({activeAssoc?.subcriterion_id})</span>
              </div>
              <button
                type="button"
                onClick={() => setShowRejectModal(false)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg leading-none cursor-pointer"
              >
                ×
              </button>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Rejection Category Code
              </label>
              <select
                value={rejectionCode}
                onChange={(e) => setRejectionCode(e.target.value)}
                className="w-full text-xs font-semibold text-slate-800 p-2.5 border border-slate-200 rounded-lg outline-none focus:border-red-500 focus:ring-2 focus:ring-red-500/20"
              >
                {REJECTION_REASON_CODES.map((codeItem) => (
                  <option key={codeItem.code} value={codeItem.code}>
                    {codeItem.label} — {codeItem.description}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Specific Reviewer Feedback & Justification <span className="text-red-500">*</span>
              </label>
              <textarea
                rows={4}
                required
                placeholder="Detail explicitly why this documentary evidence does not substantiate the required subcriterion..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className="w-full text-xs font-medium p-3 border border-slate-200 rounded-lg outline-none focus:border-red-500 focus:ring-2 focus:ring-red-500/20 leading-relaxed"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                This feedback is mandatory and will be attached strictly to association{" "}
                <span className="font-mono font-bold text-slate-600">{activeAssoc?.subcriterion_id}</span>.
                Sibling associations will remain untouched.
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmReject}
                disabled={!rejectionReason.trim() || actionLoading}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer disabled:opacity-40"
              >
                {actionLoading ? "Submitting..." : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* COMPLETE REVIEW CONFIRMATION MODAL */}
      {showCompleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2 text-emerald-700 font-bold text-sm">
                <ShieldCheck className="w-5 h-5 text-emerald-600" />
                <span>Complete Assessment Review</span>
              </div>
              <button
                type="button"
                onClick={() => setShowCompleteModal(false)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg leading-none cursor-pointer"
              >
                ×
              </button>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 text-xs space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500">Institution:</span>
                <span className="font-bold text-slate-800">{assessment.institution?.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Total Evidence Associations:</span>
                <span className="font-bold text-slate-800">{metrics.total}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-emerald-700 font-semibold">Verified Associations:</span>
                <span className="font-bold text-emerald-700">{metrics.verified}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-700 font-semibold">Rejected Associations:</span>
                <span className="font-bold text-red-700">{metrics.rejected}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-amber-700 font-semibold">Remaining Pending:</span>
                <span className="font-bold text-amber-700">{metrics.pending}</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Committee Final Remarks (Optional)
              </label>
              <textarea
                rows={3}
                placeholder="Enter summary remarks or final evaluation notes..."
                value={completionRemarks}
                onChange={(e) => setCompletionRemarks(e.target.value)}
                className="w-full text-xs font-medium p-3 border border-slate-200 rounded-lg outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowCompleteModal(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCompleteReview}
                disabled={completingReview}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
              >
                {completingReview && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Confirm & Complete Review</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PlayIcon() {
  return (
    <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}
