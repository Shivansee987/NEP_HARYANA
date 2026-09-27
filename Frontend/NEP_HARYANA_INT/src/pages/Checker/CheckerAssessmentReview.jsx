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
  Award,
  Trophy,
  Table,
  Check,
  Edit3,
  AlertTriangle,
  Eye,
  FileSpreadsheet,
} from "lucide-react";
import {
  fetchAssessmentReviewDetail,
  verifyEvidenceAssociation,
  rejectEvidenceAssociation,
  fetchAssociationHistory,
  fetchAssociationDocumentBlob,
  startAssessmentReview,
  completeAssessmentReview,
  fetchAssessmentScoring,
  acceptParameterScore,
  adjustParameterScore,
  certifyAssessment,
} from "../../api/checker";
import { useAuth } from "../../context/AuthContext.jsx";
import { StatusBadge, DashboardSkeleton, EmptyState, ErrorState } from "../../components/common";
import { formatGatingStatus, getGatingStatusExplanation } from "../../components/common/StatusBadge";
import DocumentPreviewModal from "../../components/Institution/DocumentPreviewModal";
import {
  getParameterTitle,
  getSubcriterionTitle,
  REJECTION_REASON_CODES,
  UNIVERSITY_PARAMETER_CODES,
  COLLEGE_PARAMETER_CODES,
  COLLEGE_FRAMEWORK_DATA,
  UNIVERSITY_FRAMEWORK_DATA,
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

  // Scoring Evaluation State (Authoritative Server Truth)
  const [scoringEvaluation, setScoringEvaluation] = useState(null);
  const [scoringLoading, setScoringLoading] = useState(false);
  const [scoringError, setScoringError] = useState(null);

  // Selected Parameter Code for scoring review
  const [selectedParamCode, setSelectedParamCode] = useState(null);

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

  // Action / Feedback State
  const [actionLoading, setActionLoading] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [rejectionCode, setRejectionCode] = useState("MISMATCHED_CRITERIA");
  const [actionFeedback, setActionFeedback] = useState(null); // { type: 'success'|'error', message }

  // Review Lifecycle State
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [completionRemarks, setCompletionRemarks] = useState("");
  const [completingReview, setCompletingReview] = useState(false);

  // Score Acceptance State
  const [acceptingScore, setAcceptingScore] = useState(false);

  // Score Adjustment / Override Modal State
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [adjustSubCode, setAdjustSubCode] = useState("");
  const [adjustScoreValue, setAdjustScoreValue] = useState("");
  const [adjustReason, setAdjustReason] = useState("");
  const [adjustLoading, setAdjustLoading] = useState(false);

  // Modals for Score Summary Table & Final Award Result
  const [showScoreTableModal, setShowScoreTableModal] = useState(false);
  const [showFinalAwardModal, setShowFinalAwardModal] = useState(false);
  const [certifyingAssessment, setCertifyingAssessment] = useState(false);

  // Document Viewer Modal State
  const [previewModal, setPreviewModal] = useState({
    isOpen: false,
    documentId: "",
    associationId: "",
    filename: "",
    mimeType: "",
  });

  const handleOpenPreviewModal = (assoc) => {
    if (!assoc) return;
    const docId = assoc.evidence_id || assoc.evidence_document_id || assoc.document_id || "";
    const assocId = assoc.association_id || assoc.id || "";
    const name = assoc.original_filename || "Documentary Proof";
    const mime = assoc.mime_type || "";
    setPreviewModal({
      isOpen: true,
      documentId: docId ? String(docId) : "",
      associationId: assocId ? String(assocId) : "",
      filename: name,
      mimeType: mime,
    });
  };

  const handleClosePreviewModal = () => {
    setPreviewModal((prev) => ({ ...prev, isOpen: false }));
  };

  // Load Assessment Detail & Scoring Evaluation
  const loadAssessment = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAssessmentReviewDetail(assessmentId);
      setAssessment(data);
      const assocs = data.evidence_associations || [];
      setEvidenceAssociations(assocs);

      // Set initial selectedParamCode if none is set yet
      setSelectedParamCode((prev) => {
        if (prev) return prev;
        if (assocs.length > 0) return assocs[0].parameter_id;
        return null;
      });

      // Load authoritative scoring evaluation from frozen backend engine
      try {
        const scoring = await fetchAssessmentScoring(data.framework, assessmentId);
        setScoringEvaluation(scoring);
        setSelectedParamCode((prev) => {
          if (prev) return prev;
          if (scoring.parameter_results) {
            return Object.keys(scoring.parameter_results)[0];
          }
          if (assocs.length > 0) {
            return assocs[0].parameter_id;
          }
          return null;
        });
      } catch (sErr) {
        console.warn("Could not fetch initial scoring evaluation:", sErr);
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

  // Reload authoritative scoring evaluation helper
  const reloadScoring = useCallback(async () => {
    if (!assessment) return;
    try {
      const scoring = await fetchAssessmentScoring(assessment.framework, assessment.assessment_id);
      setScoringEvaluation(scoring);
    } catch (err) {
      console.error("Failed to reload scoring evaluation:", err);
    }
  }, [assessment]);

  // Current parameter's associations strictly scoped to selectedParamCode
  const currentParamAssocs = useMemo(() => {
    if (!selectedParamCode) return [];
    return evidenceAssociations.filter((a) => a.parameter_id === selectedParamCode);
  }, [evidenceAssociations, selectedParamCode]);

  // Current active association object strictly scoped to active parameter
  const activeAssoc = useMemo(() => {
    if (!selectedParamCode || currentParamAssocs.length === 0) return null;
    if (selectedAssocId) {
      const match = currentParamAssocs.find(
        (a) => (a.id || a.association_id) === selectedAssocId
      );
      if (match) return match;
    }
    // Default strictly to the first association OF THIS PARAMETER
    return currentParamAssocs[0] || null;
  }, [selectedParamCode, selectedAssocId, currentParamAssocs]);

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

  // Framework Parameter Codes
  const frameworkParamCodes = useMemo(() => {
    if (assessment?.framework === "COLLEGE_2026") {
      return COLLEGE_PARAMETER_CODES;
    }
    return UNIVERSITY_PARAMETER_CODES;
  }, [assessment?.framework]);

  // Complete Parameter List with authoritative scoring data & evidence groups
  const fullParameterList = useMemo(() => {
    const isCollege = assessment?.framework === "COLLEGE_2026";
    const fwData = isCollege ? COLLEGE_FRAMEWORK_DATA : UNIVERSITY_FRAMEWORK_DATA;

    return frameworkParamCodes.map((code) => {
      const scoring = scoringEvaluation?.parameter_results?.[code];
      const title = scoring?.parameter_title || getParameterTitle(assessment?.framework, code);
      const maxMarks = scoring?.max_marks ?? 0;
      const isApproved = scoring?.review_status === "APPROVED";
      const awardedScore = scoring?.awarded_score;
      const finalScore = scoring?.final_score ?? scoring?.evidence_gated_score ?? 0;
      const isUnresolved = scoring?.is_unresolved ?? false;
      const unresolvedReason = scoring?.unresolved_reason;
      const scoringBasis = scoring?.scoring_basis;
      const subcriteriaResults = scoring?.subcriteria_results || {};

      // Associations matching this parameter
      const assocs = evidenceAssociations.filter((a) => a.parameter_id === code);
      const verifiedAssocs = assocs.filter((a) => a.verification_status === "VERIFIED");
      const rejectedAssocs = assocs.filter((a) => a.verification_status === "REJECTED");
      const pendingAssocs = assocs.filter(
        (a) => a.verification_status !== "VERIFIED" && a.verification_status !== "REJECTED"
      );

      // Canonical subcriteria from framework definition
      const paramDef = fwData?.[code];
      const canonicalSubs = paramDef?.subcriteria || [];

      // Group associations by subcriterion (preserving canonical subcriteria order)
      const subcriteriaGroups = [];
      const handledSubIds = new Set();

      if (canonicalSubs.length > 0) {
        canonicalSubs.forEach((sub) => {
          handledSubIds.add(sub.code);
          const matchedAssocs = assocs.filter((a) => a.subcriterion_id === sub.code);
          subcriteriaGroups.push({
            subcriterionId: sub.code,
            title: sub.title || getSubcriterionTitle(sub.code, title),
            documentaryRequirement: sub.documentaryRequirement,
            canonicalEvidenceType: sub.canonicalEvidenceType,
            isSourceSilent: sub.isSourceSilent || false,
            maxScore: sub.maxScore,
            associations: matchedAssocs,
          });
        });
      }

      // Check if there are any associations whose subcriterion_id wasn't in canonicalSubs
      assocs.forEach((a) => {
        const sId = a.subcriterion_id || code;
        if (!handledSubIds.has(sId)) {
          handledSubIds.add(sId);
          subcriteriaGroups.push({
            subcriterionId: sId,
            title: getSubcriterionTitle(sId, title),
            documentaryRequirement: a.subcriterion_evidence_type,
            canonicalEvidenceType: a.subcriterion_evidence_type,
            isSourceSilent: false,
            maxScore: null,
            associations: assocs.filter((x) => (x.subcriterion_id || code) === sId),
          });
        }
      });

      // Also if canonicalSubs was empty, check subcriteriaResults
      if (subcriteriaGroups.length === 0 && Object.keys(subcriteriaResults).length > 0) {
        Object.entries(subcriteriaResults).forEach(([sCode, sRes]) => {
          subcriteriaGroups.push({
            subcriterionId: sCode,
            title: getSubcriterionTitle(sCode, title),
            documentaryRequirement: null,
            canonicalEvidenceType: null,
            isSourceSilent: sRes.gating_status === "NO_EVIDENCE_REQUIRED",
            maxScore: sRes.max_score,
            associations: assocs.filter((a) => a.subcriterion_id === sCode),
          });
        });
      }

      const isEntirelySourceSilent =
        subcriteriaGroups.length > 0 && subcriteriaGroups.every((s) => s.isSourceSilent);

      return {
        code,
        title,
        maxMarks,
        isApproved,
        awardedScore,
        finalScore,
        isUnresolved,
        unresolvedReason,
        scoringBasis,
        subcriteriaResults,
        associations: assocs,
        subcriteriaGroups,
        verifiedCount: verifiedAssocs.length,
        rejectedCount: rejectedAssocs.length,
        pendingCount: pendingAssocs.length,
        hasRejected: rejectedAssocs.length > 0,
        isEntirelySourceSilent,
      };
    });
  }, [frameworkParamCodes, scoringEvaluation, assessment?.framework, evidenceAssociations]);

  // Active Parameter Scoring Info
  const activeParamScoring = useMemo(() => {
    if (!selectedParamCode) return null;
    return fullParameterList.find((p) => p.code === selectedParamCode) || null;
  }, [selectedParamCode, fullParameterList]);

  // Ensure default selectedParamCode if null
  useEffect(() => {
    if (!selectedParamCode && frameworkParamCodes.length > 0) {
      setSelectedParamCode(frameworkParamCodes[0]);
    }
  }, [selectedParamCode, frameworkParamCodes]);

  // Handle selecting a parameter from left tree
  const handleSelectParameter = (pCode) => {
    setSelectedParamCode(pCode);
    const paramDocs = evidenceAssociations.filter((a) => a.parameter_id === pCode);
    if (paramDocs.length > 0) {
      setSelectedAssocId(paramDocs[0].id || paramDocs[0].association_id);
    } else {
      setSelectedAssocId(null);
    }
    setShowHistory(false);
    setActionFeedback(null);
  };

  // Navigation indices strictly scoped to the active parameter's associations
  const currentAssocIndex = useMemo(() => {
    if (!activeAssoc || currentParamAssocs.length === 0) return -1;
    return currentParamAssocs.findIndex(
      (a) => (a.id || a.association_id) === (activeAssoc.id || activeAssoc.association_id)
    );
  }, [activeAssoc, currentParamAssocs]);

  const handleNextEvidence = () => {
    if (currentAssocIndex < currentParamAssocs.length - 1) {
      const nextAssoc = currentParamAssocs[currentAssocIndex + 1];
      setSelectedAssocId(nextAssoc.id || nextAssoc.association_id);
      setShowHistory(false);
      setActionFeedback(null);
    }
  };

  const handlePrevEvidence = () => {
    if (currentAssocIndex > 0) {
      const prevAssoc = currentParamAssocs[currentAssocIndex - 1];
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
        message: `Association ${activeAssoc.subcriterion_id} verified successfully. Deterministic marks unlocked!`,
      });

      // Trigger authoritative server re-score
      await reloadScoring();

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

      // Trigger authoritative server re-score
      await reloadScoring();

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

  // ACCEPT CALCULATED SCORE ACTION
  const handleAcceptScore = async (paramCode) => {
    const code = paramCode || selectedParamCode;
    if (!code) return;
    setAcceptingScore(true);
    setActionFeedback(null);
    try {
      const res = await acceptParameterScore(
        assessment?.framework,
        assessment?.assessment_id,
        code,
        `Committee reviewer accepted calculated score for ${code}.`
      );
      if (res.evaluation) {
        setScoringEvaluation(res.evaluation);
      } else {
        await reloadScoring();
      }
      setActionFeedback({
        type: "success",
        message: `Calculated marks for ${code} accepted! Running expected total updated to ${res.evaluation?.expected_total_display || ""}.`,
      });
    } catch (err) {
      console.error("Accept score error:", err);
      setActionFeedback({
        type: "error",
        message: err.message || `Failed to accept score for ${code}.`,
      });
    } finally {
      setAcceptingScore(false);
    }
  };

  // ADJUST SCORE OVERRIDE ACTION
  const handleConfirmAdjustment = async () => {
    if (!selectedParamCode || !adjustSubCode || adjustScoreValue === "" || !adjustReason.trim()) return;
    if (adjustReason.trim().length < 10) {
      setActionFeedback({
        type: "error",
        message: "A substantial justification (minimum 10 characters) is mandatory for score adjustment.",
      });
      return;
    }
    setAdjustLoading(true);
    try {
      const res = await adjustParameterScore(
        assessment?.framework,
        assessment?.assessment_id,
        selectedParamCode,
        {
          subcriterion_code: adjustSubCode,
          adjusted_score: parseFloat(adjustScoreValue),
          reason: adjustReason.trim(),
        }
      );
      if (res.evaluation) {
        setScoringEvaluation(res.evaluation);
      } else {
        await reloadScoring();
      }
      setShowAdjustModal(false);
      setAdjustSubCode("");
      setAdjustScoreValue("");
      setAdjustReason("");
      setActionFeedback({
        type: "success",
        message: `Score adjusted for ${adjustSubCode} and audited. Expected Total updated!`,
      });
    } catch (err) {
      console.error("Adjustment error:", err);
      const errMsg = err.message || "Failed to adjust score.";
      const isEvidenceGating = errMsg.includes("FAILED_EVIDENCE_REJECTED") ||
        errMsg.includes("FAILED_EVIDENCE_ABSENT") ||
        errMsg.includes("Evidence gating status");
      setActionFeedback({
        type: "error",
        message: isEvidenceGating
          ? `${errMsg} — Statutory Audit Rule: Positive marks cannot be awarded while supporting evidence is rejected or absent. To award marks, inspect the evidence document below and click 'Verify Association' first.`
          : errMsg,
      });
    } finally {
      setAdjustLoading(false);
    }
  };

  // CERTIFY ASSESSMENT ACTION
  const handleCertifyAssessment = async () => {
    setCertifyingAssessment(true);
    try {
      await certifyAssessment(
        assessment?.framework,
        assessment?.assessment_id,
        { remarks: "Screening committee chair finalized and certified assessment." }
      );
      setAssessment((prev) => ({
        ...prev,
        status: "CERTIFIED",
      }));
      setShowFinalAwardModal(false);
      setActionFeedback({
        type: "success",
        message: "Assessment successfully certified! Statutory certificate is now available.",
      });
      await reloadScoring();
    } catch (err) {
      console.error("Certification error:", err);
      setActionFeedback({
        type: "error",
        message: err.message || "Failed to certify assessment.",
      });
    } finally {
      setCertifyingAssessment(false);
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

  const getGatingDotColor = (gatingStatus) => {
    const g = String(gatingStatus || "").toUpperCase();
    if (g.includes("VERIFIED") || g === "NO_EVIDENCE_REQUIRED") return "bg-emerald-500";
    if (g.includes("REJECTED")) return "bg-red-500";
    if (g.includes("ABSENT")) return "bg-rose-400";
    return "bg-amber-400";
  };

  const getActiveParamGatingAlert = () => {
    if (!activeParamScoring) return null;
    const subs = Object.entries(activeParamScoring.subcriteriaResults || {});
    const hasRejected = subs.some(([, s]) => String(s.gating_status || "").toUpperCase().includes("REJECTED"));
    const hasAbsent   = subs.some(([, s]) => String(s.gating_status || "").toUpperCase().includes("ABSENT"));
    const hasPending  = subs.some(([, s]) => String(s.gating_status || "").toUpperCase().includes("PENDING"));
    if (hasRejected) return (
      <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-900">
        <div className="font-bold flex items-center gap-1.5 mb-1">
          <XCircle className="w-3.5 h-3.5 text-red-600 shrink-0" /> Evidence Rejected
        </div>
        <p className="leading-relaxed text-red-800">Score is 0 while evidence is rejected. Verify the evidence in the centre panel to unlock marks.</p>
      </div>
    );
    if (hasAbsent && !activeParamScoring.isEntirelySourceSilent) return (
      <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900">
        <div className="font-bold flex items-center gap-1.5 mb-1">
          <AlertCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" /> Evidence Missing
        </div>
        <p className="leading-relaxed">No documents uploaded for some subcriteria. Score is restricted to 0.</p>
      </div>
    );
    if (hasPending) return (
      <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900">
        <div className="font-bold flex items-center gap-1.5 mb-1">
          <Clock className="w-3.5 h-3.5 text-amber-600 shrink-0" /> Pending Verification
        </div>
        <p className="leading-relaxed">Review the evidence in the centre panel and verify to unlock the full calculated score.</p>
      </div>
    );
    return null;
  };

  return (
    <div className="flex flex-col -mx-6 -mt-6" style={{ height: "calc(100vh - 0px)", minHeight: 600 }}>

      {/* TOP HEADER */}
      <header className="shrink-0 bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-4 z-20 shadow-xs">
        <Link to="/checker/queue" className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-amber-800 transition-colors shrink-0">
          <ArrowLeft className="w-3.5 h-3.5" /><span>Queue</span>
        </Link>
        <div className="w-px h-5 bg-slate-200 shrink-0" />
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {isUniv ? <Building2 className="w-4 h-4 text-indigo-600 shrink-0" /> : <GraduationCap className="w-4 h-4 text-amber-700 shrink-0" />}
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-sm font-black text-slate-900 truncate">{assessment.institution?.name}</h1>
              <StatusBadge status={assessment.status} size="sm" />
            </div>
            <p className="text-[10px] text-slate-400 font-mono truncate">{assessment.institution?.aishe_code} · {assessment.framework} · {assessment.assessment_id}</p>
          </div>
        </div>
        <div className="hidden lg:flex items-center gap-4 text-xs font-semibold shrink-0">
          <span className="flex items-center gap-1 text-emerald-700"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />{metrics.verified} Verified</span>
          <span className="flex items-center gap-1 text-red-700"><XCircle className="w-3.5 h-3.5 text-red-600" />{metrics.rejected} Rejected</span>
          <span className="flex items-center gap-1 text-amber-700"><Clock className="w-3.5 h-3.5 text-amber-500" />{metrics.pending} Pending</span>
        </div>
        <div className="w-px h-5 bg-slate-200 shrink-0 hidden lg:block" />
        <div className="flex items-center gap-2 shrink-0">
          {assessment.status === "SUBMITTED" && (
            <button type="button" onClick={handleStartReview} disabled={actionLoading}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold shadow-xs cursor-pointer disabled:opacity-50">
              {actionLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PlayIcon />}
              <span>Start Review</span>
            </button>
          )}
          {assessment.status === "UNDER_REVIEW" && (
            <button type="button" onClick={() => setShowCompleteModal(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-xs cursor-pointer">
              <ShieldCheck className="w-3.5 h-3.5" /><span>Complete Review</span>
            </button>
          )}
        </div>
      </header>

      {/* 3-PANEL WORKSPACE */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* LEFT: Parameter Nav */}
        <aside className="w-52 shrink-0 bg-white border-r border-slate-200 flex flex-col overflow-hidden">
          <div className="px-3 py-3 border-b border-slate-100 bg-slate-50/80 shrink-0">
            <span className="text-[9px] font-black uppercase tracking-widest text-slate-500 block">Parameters</span>
            <div className="flex items-center gap-2 mt-2">
              <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${metrics.percentReviewed}%` }} />
              </div>
              <span className="text-[10px] font-bold text-slate-500 shrink-0">{metrics.percentReviewed}%</span>
            </div>
          </div>
          <div className="overflow-y-auto flex-1 py-1">
            {fullParameterList.map((param) => {
              const isSelected = param.code === selectedParamCode;
              const hasEvidence = param.associations.length > 0;
              return (
                <button key={param.code} type="button" onClick={() => handleSelectParameter(param.code)}
                  className={`w-full text-left flex items-center gap-2 px-3 py-2.5 transition-all border-r-2 cursor-pointer group ${isSelected ? "bg-amber-50 border-r-amber-500 text-amber-900" : "border-r-transparent hover:bg-slate-50 text-slate-700"}`}>
                  <span className={`font-mono text-[10px] font-black px-1.5 py-0.5 rounded shrink-0 ${isSelected ? "bg-amber-100 text-amber-900 border border-amber-300" : "bg-slate-100 text-slate-600 group-hover:bg-slate-200"}`}>{param.code}</span>
                  <span className="text-[11px] font-medium leading-snug flex-1 min-w-0 line-clamp-2">{param.title}</span>
                  <div className="shrink-0">
                    {param.isApproved ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      : param.hasRejected ? <XCircle className="w-3.5 h-3.5 text-red-500" />
                      : hasEvidence ? <Clock className="w-3.5 h-3.5 text-amber-400" />
                      : <div className="w-3 h-3 rounded-full border-2 border-slate-200" />}
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        {/* CENTER: Evidence Inspector */}
        <main className="flex-1 min-w-0 bg-slate-50/60 flex flex-col overflow-hidden">
          {activeParamScoring ? (
            <>
              <div className="bg-white border-b border-slate-200 px-5 py-4 shrink-0 z-10">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-mono text-sm font-black text-amber-900 bg-amber-100/80 px-2.5 py-0.5 rounded-md border border-amber-300">{activeParamScoring.code}</span>
                      {activeParamScoring.isApproved && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Score Accepted
                        </span>
                      )}
                      {activeParamScoring.isUnresolved && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                          <AlertTriangle className="w-3 h-3" /> Source Unresolved
                        </span>
                      )}
                    </div>
                    <h2 className="text-sm font-black text-slate-900 leading-snug">{activeParamScoring.title}</h2>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-[9px] uppercase font-bold text-slate-400 block tracking-wider">Max Marks</span>
                    <span className="text-2xl font-black text-slate-900 font-mono">{activeParamScoring.maxMarks}</span>
                  </div>
                </div>
                {currentParamAssocs.length > 0 && (
                  <div className="flex items-center justify-between mt-2.5 pt-2.5 border-t border-slate-100">
                    <span className="text-xs text-slate-500">
                      Evidence <strong className="text-slate-800">{currentAssocIndex + 1}</strong> of <strong className="text-slate-800">{currentParamAssocs.length}</strong>
                      {activeAssoc && <span className="ml-2 font-mono text-amber-800 text-[11px]">{activeAssoc.subcriterion_id}</span>}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <button type="button" onClick={handlePrevEvidence} disabled={currentAssocIndex <= 0}
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-white border border-slate-200 rounded-lg text-[11px] font-semibold text-slate-600 disabled:opacity-30 hover:bg-slate-50 cursor-pointer">
                        <ChevronLeft className="w-3 h-3" /> Prev
                      </button>
                      <button type="button" onClick={handleNextEvidence} disabled={currentAssocIndex >= currentParamAssocs.length - 1}
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-white border border-slate-200 rounded-lg text-[11px] font-semibold text-slate-600 disabled:opacity-30 hover:bg-slate-50 cursor-pointer">
                        Next <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {actionFeedback && (
                  <div className={`p-3 rounded-xl border flex items-center justify-between text-xs font-semibold ${actionFeedback.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"}`}>
                    <div className="flex items-center gap-2">
                      {actionFeedback.type === "success" ? <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" /> : <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />}
                      <span>{actionFeedback.message}</span>
                    </div>
                    <button type="button" onClick={() => setActionFeedback(null)} className="text-slate-400 hover:text-slate-600 font-bold ml-4 cursor-pointer">✕</button>
                  </div>
                )}

                {activeParamScoring.isUnresolved && (
                  <div className="p-4 rounded-xl bg-amber-50 border-2 border-amber-300 text-xs">
                    <div className="flex items-center gap-2 font-bold text-amber-900 mb-1">
                      <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" /> Source Ambiguity — Clarification Required
                    </div>
                    <p className="text-amber-800 leading-relaxed pl-6">
                      {activeParamScoring.unresolvedReason || "The statutory source document contains conflicting tier totals. Per governance policy, this parameter is held neutral pending State Council clarification."}
                    </p>
                  </div>
                )}

                {/* Parameter Content Workspace */}
                {(() => {
                  const paramCode = activeParamScoring.code;
                  const isCollege = assessment?.framework === "COLLEGE_2026";
                  const fwData = isCollege ? COLLEGE_FRAMEWORK_DATA : UNIVERSITY_FRAMEWORK_DATA;
                  const paramDef = fwData?.[paramCode];
                  const subcriteriaDefs = paramDef?.subcriteria || activeParamScoring.subcriteriaGroups || [];

                  // Submitted institutional parameter data from backend inspection
                  const allSubmittedParamData = assessment?.parameter_data || {};
                  const rawParamData = allSubmittedParamData[paramCode] || {};
                  const rawInputs = rawParamData?.raw_inputs || rawParamData;

                  const hasAnySubmittedData =
                    rawInputs &&
                    typeof rawInputs === "object" &&
                    Object.keys(rawInputs).length > 0 &&
                    Object.values(rawInputs).some((v) => {
                      if (v === null || v === undefined || v === "") return false;
                      if (typeof v === "object") {
                        return Object.values(v).some(
                          (fv) => fv !== null && fv !== undefined && fv !== ""
                        );
                      }
                      return true;
                    });

                  return (
                    <div className="space-y-6">
                      {subcriteriaDefs.map((sub) => {
                        const subCode = sub.code || sub.subcriterionId;
                        const subTitle = sub.title || getSubcriterionTitle(subCode, activeParamScoring.title);
                        const subFields = sub.fields || [];
                        const subRawInputs = rawInputs?.[subCode] || {};

                        // Check if this subcriterion has submitted institutional inputs
                        const hasSubData =
                          subRawInputs &&
                          typeof subRawInputs === "object" &&
                          Object.keys(subRawInputs).length > 0 &&
                          Object.values(subRawInputs).some((val) => val !== null && val !== undefined && val !== "");

                        // Associations for this subcriterion
                        const subAssocs = evidenceAssociations.filter(
                          (a) =>
                            (a.parameter_id || "").toUpperCase() === paramCode.toUpperCase() &&
                            (a.subcriterion_id || "").toUpperCase() === subCode.toUpperCase()
                        );

                        // Gating status from scoring evaluation
                        const subScoring = activeParamScoring.subcriteriaResults?.[subCode];
                        const gatingStatus = subScoring?.gating_status || (subAssocs.length > 0 ? "PROVISIONAL_PENDING_VERIFICATION" : sub.isSourceSilent ? "NO_EVIDENCE_REQUIRED" : "FAILED_EVIDENCE_ABSENT");
                        const statusExplanation = getGatingStatusExplanation(gatingStatus);
                        const humanStatus = formatGatingStatus(gatingStatus);

                        return (
                          <div
                            key={subCode}
                            className="bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden"
                          >
                            {/* Subcriterion Header */}
                            <div className="p-4 sm:p-5 border-b border-slate-100 bg-slate-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                              <div className="flex items-center gap-2.5 min-w-0">
                                <span className="font-mono font-bold text-xs bg-amber-100 text-amber-900 border border-amber-300 px-2 py-0.5 rounded shrink-0">
                                  {subCode}
                                </span>
                                <h3 className="text-sm font-bold text-slate-900 tracking-tight leading-snug">
                                  {subTitle}
                                </h3>
                              </div>
                              <div className="flex items-center gap-2 shrink-0">
                                <StatusBadge status={gatingStatus} size="sm" />
                                {sub.maxScore !== undefined && sub.maxScore !== null && (
                                  <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                                    Max: {sub.maxScore}
                                  </span>
                                )}
                              </div>
                            </div>

                            <div className="p-5 sm:p-6 space-y-6">
                              {/* 1. INSTITUTIONAL PARAMETER DATA SECTION */}
                              <div>
                                <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
                                  <div className="flex items-center gap-2">
                                    <FileSpreadsheet className="w-4 h-4 text-amber-700" />
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                                      Submitted by Institution
                                    </h4>
                                  </div>
                                  <span className="text-[10px] text-slate-400 font-medium">Read-Only Institutional Record</span>
                                </div>

                                {hasSubData ? (
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 bg-slate-50/80 p-4 rounded-xl border border-slate-200/80">
                                    {subFields.length > 0 ? (
                                      subFields.map((f) => {
                                        const rawVal = subRawInputs[f.key];
                                        const displayVal =
                                          f.type === "checkbox"
                                            ? Boolean(rawVal)
                                              ? "Yes / Formally Approved & Certified"
                                              : "No / Not Certified"
                                            : rawVal !== undefined && rawVal !== null && rawVal !== ""
                                            ? String(rawVal)
                                            : "—";

                                        return (
                                          <div key={f.key} className={f.type === "checkbox" ? "sm:col-span-2" : ""}>
                                            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                                              {f.label}
                                            </span>
                                            <p className="text-xs font-bold text-slate-900 mt-1 font-mono bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-2xs">
                                              {displayVal}
                                            </p>
                                          </div>
                                        );
                                      })
                                    ) : (
                                      // Dynamic display for unstructured keys
                                      Object.entries(subRawInputs).map(([k, v]) => (
                                        <div key={k}>
                                          <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                                            {k.replace(/_/g, " ")}
                                          </span>
                                          <p className="text-xs font-bold text-slate-900 mt-1 font-mono bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-2xs">
                                            {typeof v === "boolean" ? (v ? "Yes" : "No") : String(v || "—")}
                                          </p>
                                        </div>
                                      ))
                                    )}
                                  </div>
                                ) : (
                                  <div className="p-4 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-center">
                                    <p className="text-xs text-slate-500 font-medium italic">
                                      No institutional data submitted for this subcriterion.
                                    </p>
                                  </div>
                                )}
                              </div>

                              {/* 2. SUPPORTING DOCUMENTARY EVIDENCE SECTION */}
                              <div className="pt-4 border-t border-slate-100">
                                <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
                                  <div className="flex items-center gap-2">
                                    <FileText className="w-4 h-4 text-amber-700" />
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                                      Supporting Evidence
                                    </h4>
                                  </div>
                                  <span className="text-[10px] text-slate-500 font-medium">
                                    Required: {sub.documentaryRequirement || sub.canonicalEvidenceType || "Documentary record"}
                                  </span>
                                </div>

                                {subAssocs.length > 0 ? (
                                  <div className="space-y-3">
                                    {subAssocs.map((assoc) => {
                                      const isVerified = assoc.verification_status === "VERIFIED";
                                      const isRejected = assoc.verification_status === "REJECTED";
                                      const lookupId = assoc.id || assoc.association_id;

                                      return (
                                        <div
                                          key={lookupId}
                                          className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-3"
                                        >
                                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                            <div className="flex items-center gap-2.5 min-w-0">
                                              <FileText className="w-4 h-4 text-amber-600 shrink-0" />
                                              <span className="text-xs font-bold text-slate-900 truncate max-w-sm">
                                                {assoc.original_filename || "Documentary Evidence File"}
                                              </span>
                                            </div>
                                            <div className="flex items-center gap-2 shrink-0">
                                              <StatusBadge status={assoc.verification_status || "PENDING"} size="sm" />
                                              <button
                                                type="button"
                                                onClick={() => handleOpenPreviewModal(assoc)}
                                                className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 rounded-lg text-xs font-semibold cursor-pointer transition-colors shadow-2xs"
                                              >
                                                <Eye className="w-3 h-3 text-amber-700" /> View Document
                                              </button>
                                            </div>
                                          </div>

                                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] bg-slate-50 p-3 rounded-lg border border-slate-100 text-slate-600">
                                            <div>
                                              <span className="font-semibold text-slate-400">Evidence Type: </span>
                                              <span className="font-mono text-slate-800">{assoc.subcriterion_evidence_type || "—"}</span>
                                            </div>
                                            {assoc.page_start && (
                                              <div>
                                                <span className="font-semibold text-slate-400">Pages: </span>
                                                <span className="text-slate-800 font-medium">
                                                  {assoc.page_start}–{assoc.page_end} {assoc.section_identifier ? `(${assoc.section_identifier})` : ""}
                                                </span>
                                              </div>
                                            )}
                                            {assoc.claim_description && (
                                              <div className="sm:col-span-2">
                                                <span className="font-semibold text-slate-400">Claim: </span>
                                                <span className="text-slate-800">{assoc.claim_description}</span>
                                              </div>
                                            )}
                                          </div>

                                          {/* Rejection Details Banner if Rejected */}
                                          {isRejected && assoc.latest_verification && (
                                            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs space-y-1">
                                              <div className="flex items-center gap-1.5 font-bold text-red-900">
                                                <AlertCircle className="w-3.5 h-3.5 text-red-600" />
                                                <span>Rejection Reason ({assoc.latest_verification.rejection_code || "MISMATCHED_CRITERIA"})</span>
                                              </div>
                                              <p className="text-red-800 pl-5">"{assoc.latest_verification.reason}"</p>
                                            </div>
                                          )}

                                          {/* Reviewer Actions */}
                                          <div className="flex items-center gap-2 pt-1">
                                            <button
                                              type="button"
                                              disabled={actionLoading}
                                              onClick={async () => {
                                                setActionLoading(true);
                                                try {
                                                  await verifyEvidenceAssociation(lookupId, {
                                                    reason: `Subcriterion ${subCode} substantiated and approved.`,
                                                  });
                                                  setEvidenceAssociations((prev) =>
                                                    prev.map((item) =>
                                                      (item.id || item.association_id) === lookupId
                                                        ? { ...item, verification_status: "VERIFIED" }
                                                        : item
                                                    )
                                                  );
                                                  await reloadScoring();
                                                  setActionFeedback({
                                                    type: "success",
                                                    message: `Evidence for ${subCode} verified successfully.`,
                                                  });
                                                } catch (err) {
                                                  setActionFeedback({ type: "error", message: err.message || "Failed to verify." });
                                                } finally {
                                                  setActionLoading(false);
                                                }
                                              }}
                                              className={`flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold cursor-pointer transition-colors shadow-2xs ${
                                                isVerified
                                                  ? "bg-emerald-100 text-emerald-900 border border-emerald-300"
                                                  : "bg-emerald-600 hover:bg-emerald-700 text-white"
                                              }`}
                                            >
                                              <CheckCircle2 className="w-3.5 h-3.5" />
                                              <span>{isVerified ? "Verified (Re-Verify)" : isRejected ? "Verify (Overturn Rejection)" : "Verify Evidence"}</span>
                                            </button>

                                            <button
                                              type="button"
                                              disabled={actionLoading}
                                              onClick={() => {
                                                setSelectedAssocId(lookupId);
                                                setShowRejectModal(true);
                                              }}
                                              className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold cursor-pointer transition-colors shadow-2xs"
                                            >
                                              <XCircle className="w-3.5 h-3.5" />
                                              <span>Reject with Feedback</span>
                                            </button>
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <div className="p-4 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center space-y-2">
                                    <div className="flex items-center justify-center gap-2">
                                      <StatusBadge status={gatingStatus} size="sm" />
                                    </div>
                                    <p className="text-xs text-slate-600 font-medium">
                                      {statusExplanation || "Supporting evidence has not been uploaded for this subcriterion."}
                                    </p>
                                    {sub.canonicalEvidenceType && (
                                      <span className="font-mono text-[10px] text-amber-900 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 inline-block mt-1">
                                        Expected Contract: {sub.canonicalEvidenceType}
                                      </span>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-xs text-slate-400 italic">
              Select a parameter from the left panel to begin review.
            </div>
          )}
        </main>

        {/* RIGHT: Score Summary */}
        <aside className="w-72 shrink-0 bg-white border-l border-slate-200 flex flex-col overflow-hidden">
          <div className="px-4 py-5 bg-amber-500/10 border-b border-amber-200 shrink-0">
            <span className="text-[9px] uppercase font-black text-amber-800 tracking-widest block">Live Expected Total</span>
            <div className="text-3xl font-black text-amber-950 font-mono tracking-tight mt-1">
              {scoringEvaluation?.expected_total_display || `${scoringEvaluation?.running_total ?? 0} / ${scoringEvaluation?.max_available ?? 100}`}
            </div>
            <div className="flex items-center gap-3 mt-2 text-[11px] font-semibold text-amber-900/70">
              <span>Awarded: <strong className="font-mono text-amber-950">{scoringEvaluation?.current_awarded ?? 0}</strong></span>
              <span>Max: <strong className="font-mono text-amber-950">{scoringEvaluation?.max_available ?? 100}</strong></span>
            </div>
            <div className="flex gap-2 mt-3">
              <button type="button" onClick={() => setShowScoreTableModal(true)}
                className="flex-1 inline-flex items-center justify-center gap-1 text-[11px] font-bold text-amber-900 bg-white hover:bg-amber-50 px-2.5 py-1.5 rounded-lg border border-amber-300 cursor-pointer">
                <Table className="w-3 h-3 text-amber-700" /> Score Table
              </button>
              <button type="button" onClick={() => setShowFinalAwardModal(true)}
                className="flex-1 inline-flex items-center justify-center gap-1 text-[11px] font-bold text-white bg-amber-700 hover:bg-amber-800 px-2.5 py-1.5 rounded-lg cursor-pointer shadow-xs">
                <Trophy className="w-3 h-3" /> Award Result
              </button>
            </div>
          </div>

          <div className="overflow-y-auto flex-1 p-4 space-y-4">
            {activeParamScoring ? (
              <>
                <div className={`rounded-xl p-4 border ${activeParamScoring.isApproved ? "bg-emerald-50 border-emerald-200" : "bg-slate-50 border-slate-200"}`}>
                  <span className="text-[9px] uppercase font-bold text-slate-500 block tracking-wider">
                    {activeParamScoring.isApproved ? "Awarded Marks" : "Calculated Marks"}
                  </span>
                  <div className="flex items-baseline gap-1.5 mt-1">
                    <span className={`text-3xl font-black font-mono ${activeParamScoring.isApproved ? "text-emerald-700" : "text-amber-800"}`}>
                      {activeParamScoring.isApproved ? activeParamScoring.awardedScore : activeParamScoring.finalScore}
                    </span>
                    <span className="text-sm font-bold text-slate-500">/ {activeParamScoring.maxMarks}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {activeParamScoring.isApproved ? "✓ Formally accepted by committee" : "Auto-calculated from verified evidence"}
                  </p>
                </div>

                {getActiveParamGatingAlert()}

                <button type="button" onClick={() => handleAcceptScore(activeParamScoring.code)}
                  disabled={acceptingScore || activeParamScoring.isUnresolved}
                  className={`w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-bold shadow-xs transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${activeParamScoring.isApproved ? "bg-emerald-100 hover:bg-emerald-200 text-emerald-900 border border-emerald-300" : "bg-emerald-600 hover:bg-emerald-700 text-white"}`}>
                  {acceptingScore ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  <span>{activeParamScoring.isApproved ? "Re-Accept Score" : "Accept Calculated Score"}</span>
                </button>

                {Object.keys(activeParamScoring.subcriteriaResults).length > 0 && (
                  <button type="button"
                    onClick={() => {
                      const subKeys = Object.keys(activeParamScoring.subcriteriaResults);
                      setAdjustSubCode(subKeys[0] || activeParamScoring.code);
                      setAdjustScoreValue(activeParamScoring.finalScore);
                      setAdjustReason("");
                      setShowAdjustModal(true);
                    }}
                    className="w-full text-xs text-slate-500 hover:text-amber-800 py-2.5 rounded-xl border border-dashed border-slate-200 hover:border-amber-300 hover:bg-amber-50/40 transition-all flex items-center justify-center gap-1.5 cursor-pointer">
                    <Edit3 className="w-3.5 h-3.5" /> Override Score (Documented)
                  </button>
                )}

                {Object.keys(activeParamScoring.subcriteriaResults).length > 0 && (
                  <div>
                    <span className="text-[9px] uppercase font-bold text-slate-400 block tracking-wider mb-2">Subcriteria Breakdown</span>
                    <div className="space-y-1.5">
                      {Object.entries(activeParamScoring.subcriteriaResults).map(([sCode, sRes]) => (
                        <button key={sCode} type="button"
                          onClick={() => { setAdjustSubCode(sCode); setAdjustScoreValue(sRes.final_score ?? ""); setAdjustReason(""); setShowAdjustModal(true); }}
                          className="w-full flex items-center justify-between text-xs bg-slate-50 hover:bg-amber-50/40 rounded-lg px-3 py-2 border border-slate-100 hover:border-amber-200 transition-all cursor-pointer group">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className={`w-2 h-2 rounded-full shrink-0 ${getGatingDotColor(sRes.gating_status)}`} />
                            <span className="font-mono font-bold text-slate-700 group-hover:text-amber-800 text-[11px]">{sCode}</span>
                          </div>
                          <span className="font-mono font-bold text-slate-800 shrink-0 text-[11px]">{sRes.final_score} / {sRes.max_score}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {(() => {
                  const currentIdx = frameworkParamCodes.indexOf(selectedParamCode);
                  if (currentIdx < 0 || currentIdx >= frameworkParamCodes.length - 1) return null;
                  const nextParam = fullParameterList[currentIdx + 1];
                  if (!nextParam) return null;
                  return (
                    <div className="pt-3 border-t border-slate-100">
                      <button type="button" onClick={() => handleSelectParameter(nextParam.code)}
                        className="w-full text-left px-3 py-2.5 rounded-xl border border-slate-200 hover:border-amber-300 hover:bg-amber-50/40 transition-all cursor-pointer">
                        <span className="text-[9px] text-slate-400 block uppercase tracking-wider">Next Parameter →</span>
                        <div className="flex items-center gap-1.5 mt-1 min-w-0">
                          <span className="font-mono font-bold text-amber-800 bg-amber-100 border border-amber-200 px-1.5 py-0.5 rounded text-[10px] shrink-0">{nextParam.code}</span>
                          <span className="text-xs text-slate-700 font-medium truncate">{nextParam.title}</span>
                        </div>
                      </button>
                    </div>
                  );
                })()}
              </>
            ) : (
              <div className="text-xs text-slate-400 italic text-center py-8">Select a parameter to see scoring details.</div>
            )}
          </div>
        </aside>
      </div>

      {/* MODALS */}

      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2 text-red-600 font-bold text-sm">
                <XCircle className="w-5 h-5" />
                <span>Reject Evidence ({activeAssoc?.subcriterion_id})</span>
              </div>
              <button type="button" onClick={() => setShowRejectModal(false)} className="text-slate-400 hover:text-slate-600 font-bold text-lg leading-none cursor-pointer">×</button>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Rejection Category</label>
              <select value={rejectionCode} onChange={(e) => setRejectionCode(e.target.value)}
                className="w-full text-xs font-semibold text-slate-800 p-2.5 border border-slate-200 rounded-lg outline-none focus:border-red-500 focus:ring-2 focus:ring-red-500/20">
                {REJECTION_REASON_CODES.map((codeItem) => (
                  <option key={codeItem.code} value={codeItem.code}>{codeItem.label} — {codeItem.description}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Specific Reviewer Feedback <span className="text-red-500">*</span></label>
              <textarea rows={4} required placeholder="Detail explicitly why this evidence does not substantiate the required subcriterion..."
                value={rejectionReason} onChange={(e) => setRejectionReason(e.target.value)}
                className="w-full text-xs font-medium p-3 border border-slate-200 rounded-lg outline-none focus:border-red-500 focus:ring-2 focus:ring-red-500/20 leading-relaxed" />
              <p className="text-[11px] text-slate-400 mt-1">
                Feedback is mandatory and will be attached strictly to association <span className="font-mono font-bold text-slate-600">{activeAssoc?.subcriterion_id}</span>.
              </p>
            </div>
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button type="button" onClick={() => setShowRejectModal(false)} className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer">Cancel</button>
              <button type="button" onClick={handleConfirmReject} disabled={!rejectionReason.trim() || actionLoading}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold shadow-xs cursor-pointer disabled:opacity-40">
                {actionLoading ? "Submitting..." : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showCompleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2 text-emerald-700 font-bold text-sm">
                <ShieldCheck className="w-5 h-5 text-emerald-600" /><span>Complete Assessment Review</span>
              </div>
              <button type="button" onClick={() => setShowCompleteModal(false)} className="text-slate-400 hover:text-slate-600 font-bold text-lg cursor-pointer">×</button>
            </div>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 text-xs space-y-2">
              <div className="flex justify-between"><span className="text-slate-500">Institution:</span><span className="font-bold text-slate-800">{assessment.institution?.name}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Total Associations:</span><span className="font-bold text-slate-800">{metrics.total}</span></div>
              <div className="flex justify-between"><span className="text-emerald-700 font-semibold">Verified:</span><span className="font-bold text-emerald-700">{metrics.verified}</span></div>
              <div className="flex justify-between"><span className="text-red-700 font-semibold">Rejected:</span><span className="font-bold text-red-700">{metrics.rejected}</span></div>
              <div className="flex justify-between"><span className="text-amber-700 font-semibold">Remaining Pending:</span><span className="font-bold text-amber-700">{metrics.pending}</span></div>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Committee Final Remarks (Optional)</label>
              <textarea rows={3} placeholder="Enter summary remarks or final evaluation notes..."
                value={completionRemarks} onChange={(e) => setCompletionRemarks(e.target.value)}
                className="w-full text-xs font-medium p-3 border border-slate-200 rounded-lg outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20" />
            </div>
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button type="button" onClick={() => setShowCompleteModal(false)} className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer">Cancel</button>
              <button type="button" onClick={handleCompleteReview} disabled={completingReview}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-xs cursor-pointer disabled:opacity-50 flex items-center gap-1.5">
                {completingReview && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Confirm &amp; Complete Review</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {showAdjustModal && (() => {
        const currentAdjustSubRes = activeParamScoring?.subcriteriaResults?.[adjustSubCode];
        const adjustMaxScore = currentAdjustSubRes?.max_score ?? activeParamScoring?.maxMarks ?? 100;
        const adjustGatingStatus = currentAdjustSubRes?.gating_status || "";
        const isEvidenceRejected = String(adjustGatingStatus).toUpperCase().includes("REJECTED");
        const isEvidenceAbsent   = String(adjustGatingStatus).toUpperCase().includes("ABSENT");
        const isGatingBlocked    = isEvidenceRejected || isEvidenceAbsent;
        const numericScore       = parseFloat(adjustScoreValue);
        const isPositiveOnBlocked = isGatingBlocked && !isNaN(numericScore) && numericScore > 0;
        const isExceedingMax      = !isNaN(numericScore) && numericScore > adjustMaxScore;
        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
                  <Edit3 className="w-5 h-5 text-amber-700" />
                  <span>Adjust Score ({adjustSubCode || selectedParamCode})</span>
                </div>
                <button type="button" onClick={() => setShowAdjustModal(false)} className="text-slate-400 hover:text-slate-600 font-bold text-lg cursor-pointer">×</button>
              </div>
              {isGatingBlocked && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2.5 text-xs text-red-900">
                  <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="font-bold text-red-800">Evidence Gating Restriction</p>
                    <p className="text-red-700 leading-relaxed text-[11px]">Evidence for <strong>{adjustSubCode}</strong> is <strong>{isEvidenceRejected ? "REJECTED" : "ABSENT / MISSING"}</strong>. Positive marks cannot be awarded while evidence is rejected or missing.</p>
                    <p className="text-red-800 font-semibold text-[11px]">👉 Close this modal, verify the evidence, then return to adjust.</p>
                  </div>
                </div>
              )}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Subcriterion Code</label>
                <input type="text" value={adjustSubCode} readOnly className="w-full text-xs font-mono font-bold text-slate-800 p-2.5 border border-slate-200 rounded-lg outline-none bg-slate-50" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">New Score <span className="text-red-500">*</span></label>
                <input type="number" step="0.1" min="0" max={adjustMaxScore} value={adjustScoreValue}
                  onChange={(e) => setAdjustScoreValue(e.target.value)} placeholder={`Enter marks ≤ ${adjustMaxScore}`}
                  className={`w-full text-xs font-bold p-2.5 border rounded-lg outline-none transition-colors ${isPositiveOnBlocked || isExceedingMax ? "border-red-400 focus:ring-2 focus:ring-red-400/20" : "border-slate-200 focus:border-amber-600 focus:ring-2 focus:ring-amber-500/20"}`} />
                {isPositiveOnBlocked
                  ? <p className="text-[11px] text-red-600 font-semibold mt-1">⚠️ Cannot award positive marks while evidence is {isEvidenceRejected ? "REJECTED" : "ABSENT"}.</p>
                  : isExceedingMax
                  ? <p className="text-[11px] text-red-600 font-semibold mt-1">⚠️ Score cannot exceed subcriterion maximum ({adjustMaxScore}).</p>
                  : <p className="text-[11px] text-slate-400 mt-1">Subcriterion maximum: {adjustMaxScore} marks. Hard cap enforced.</p>}
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Audited Justification <span className="text-red-500">*</span></label>
                <textarea rows={3} value={adjustReason} onChange={(e) => setAdjustReason(e.target.value)}
                  placeholder="Mandatory justification (minimum 10 characters)..."
                  className="w-full text-xs font-medium p-3 border border-slate-200 rounded-lg outline-none focus:border-amber-600 focus:ring-2 focus:ring-amber-500/20" />
              </div>
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setShowAdjustModal(false)} className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer">Cancel</button>
                <button type="button" onClick={handleConfirmAdjustment}
                  disabled={adjustLoading || !adjustReason.trim() || adjustScoreValue === "" || isPositiveOnBlocked || isExceedingMax}
                  className="px-4 py-2 bg-amber-700 hover:bg-amber-800 text-white rounded-lg text-xs font-bold shadow-xs cursor-pointer disabled:opacity-40 flex items-center gap-1.5">
                  {adjustLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Save Adjustment</span>
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {showScoreTableModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-3xl w-full p-6 space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2 text-slate-900 font-black text-base">
                <Table className="w-5 h-5 text-amber-700" /><span>Committee Running Score Table</span>
              </div>
              <button type="button" onClick={() => setShowScoreTableModal(false)} className="text-slate-400 hover:text-slate-600 font-bold text-xl cursor-pointer">×</button>
            </div>
            <div className="overflow-y-auto flex-1 border border-slate-200 rounded-xl">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-100 text-slate-600 font-bold uppercase text-[10px] tracking-wider sticky top-0">
                  <tr>
                    <th className="py-2.5 px-3">Parameter</th>
                    <th className="py-2.5 px-3">Title</th>
                    <th className="py-2.5 px-3 text-center">Max</th>
                    <th className="py-2.5 px-3 text-center">Awarded</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {fullParameterList.map((p) => (
                    <tr key={p.code} onClick={() => { handleSelectParameter(p.code); setShowScoreTableModal(false); }} className="hover:bg-amber-50/40 cursor-pointer">
                      <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{p.code}</td>
                      <td className="py-2.5 px-3 font-medium text-slate-800 truncate max-w-xs">{p.title}</td>
                      <td className="py-2.5 px-3 text-center font-mono font-bold text-slate-700">{p.maxMarks}</td>
                      <td className="py-2.5 px-3 text-center font-mono font-bold">
                        {p.isApproved ? <span className="text-emerald-700">{p.awardedScore}</span> : <span className="text-slate-400">—</span>}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        {p.isApproved ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Approved
                          </span>
                        ) : p.isUnresolved ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">Unresolved</span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600">Pending</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between pt-3 border-t border-slate-100 bg-slate-50 p-4 rounded-xl font-bold text-sm">
              <div>
                <span className="text-slate-500 uppercase text-[10px] block">Parameters Completed</span>
                <span className="text-slate-800">{scoringEvaluation?.parameters_reviewed_count ?? 0} of {scoringEvaluation?.total_parameters_count ?? fullParameterList.length}</span>
              </div>
              <div className="text-right">
                <span className="text-slate-500 uppercase text-[10px] block">Live Expected Total</span>
                <span className="text-xl font-mono font-black text-amber-950">
                  {scoringEvaluation?.expected_total_display || `${scoringEvaluation?.running_total ?? 0} / ${scoringEvaluation?.max_available ?? 100}`}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {showFinalAwardModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full p-6 space-y-5 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2 text-slate-900 font-black text-base">
                <Trophy className="w-5 h-5 text-amber-600" /><span>FINAL NEP EXCELLENCE AWARD RESULT</span>
              </div>
              <button type="button" onClick={() => setShowFinalAwardModal(false)} className="text-slate-400 hover:text-slate-600 font-bold text-xl cursor-pointer">×</button>
            </div>
            <div className="overflow-y-auto flex-1 space-y-4 pr-1">
              <div className="bg-slate-900 text-white p-6 rounded-2xl space-y-4">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">Institution Name</span>
                  <h3 className="text-xl font-black text-amber-400 mt-0.5">{assessment.institution?.name}</h3>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300 mt-1">
                    <span>Framework: <strong className="text-white">{assessment.framework}</strong></span>
                    <span>·</span>
                    <span>Period: <strong className="text-white">July 2025 – June 2026</strong></span>
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-3 border-t border-slate-800 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Parameters Reviewed</span>
                    <span className="text-base font-bold text-white mt-0.5 block">
                      {scoringEvaluation?.parameters_reviewed_count ?? 0} / {scoringEvaluation?.total_parameters_count ?? fullParameterList.length}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Final Total Score</span>
                    <span className="text-2xl font-black text-white font-mono mt-0.5 block">
                      {scoringEvaluation?.running_total ?? 0} / {scoringEvaluation?.max_available ?? 100}
                    </span>
                  </div>
                  <div className="sm:col-span-1 col-span-2">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Award Level</span>
                    {scoringEvaluation?.award_classification?.tier
                      ? <span className="text-xl font-black text-amber-400 tracking-wider block mt-0.5 uppercase">{scoringEvaluation.award_classification.tier}</span>
                      : <span className="text-xs font-semibold text-amber-200 block mt-0.5">Thresholds Unestablished</span>}
                  </div>
                </div>
                {scoringEvaluation?.award_classification?.thresholds_missing && (
                  <div className="p-3 bg-amber-950/60 border border-amber-500/40 rounded-xl text-amber-200 text-xs leading-relaxed">
                    <span className="font-bold block mb-1">State Council Policy Notice:</span>
                    {scoringEvaluation.award_classification.notice || "Authoritative award thresholds have not been established in statutory source rules. Per governance policy, thresholds cannot be inferred."}
                  </div>
                )}
              </div>
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Complete Parameter Score Breakdown</span>
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-100 text-slate-600 font-bold uppercase text-[10px] tracking-wider">
                      <tr>
                        <th className="py-2 px-3">Code</th>
                        <th className="py-2 px-3">Parameter Title</th>
                        <th className="py-2 px-3 text-center">Max</th>
                        <th className="py-2 px-3 text-center">Awarded</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {fullParameterList.map((p) => (
                        <tr key={p.code}>
                          <td className="py-2 px-3 font-mono font-bold text-slate-800">{p.code}</td>
                          <td className="py-2 px-3 text-slate-700 truncate max-w-xs">{p.title}</td>
                          <td className="py-2 px-3 text-center font-mono font-bold text-slate-600">{p.maxMarks}</td>
                          <td className="py-2 px-3 text-center font-mono font-bold text-slate-900">
                            {p.isApproved ? p.awardedScore : p.isUnresolved ? "Unres." : "Pending"}
                          </td>
                        </tr>
                      ))}
                      <tr className="bg-slate-50 font-bold border-t-2 border-slate-200">
                        <td colSpan={2} className="py-2.5 px-3 text-slate-900 uppercase">Total Final Score</td>
                        <td className="py-2.5 px-3 text-center font-mono">{scoringEvaluation?.max_available ?? 100}</td>
                        <td className="py-2.5 px-3 text-center font-mono text-amber-950 font-black text-sm">{scoringEvaluation?.running_total ?? 0}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <span className="text-xs text-slate-500 font-medium">
                {assessment.status === "CERTIFIED" ? "Assessment certified and sealed."
                  : scoringEvaluation?.all_parameters_reviewed ? "All parameters reviewed. Ready for certification."
                  : "Notice: Not all parameters have been reviewed yet."}
              </span>
              <div className="flex items-center gap-3">
                <button type="button" onClick={() => setShowFinalAwardModal(false)} className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer">Close</button>
                {assessment.status !== "CERTIFIED" && (
                  <button type="button" onClick={handleCertifyAssessment} disabled={certifyingAssessment}
                    className="inline-flex items-center gap-1.5 px-5 py-2 bg-amber-700 hover:bg-amber-800 text-white rounded-lg text-xs font-bold shadow-xs cursor-pointer disabled:opacity-50">
                    {certifyingAssessment && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    <span>Certify Assessment</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {previewModal.isOpen && (
        <DocumentPreviewModal
          isOpen={previewModal.isOpen}
          onClose={handleClosePreviewModal}
          documentId={previewModal.documentId}
          associationId={previewModal.associationId}
          filename={previewModal.filename}
          mimeType={previewModal.mimeType}
        />
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
