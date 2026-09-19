/**
 * UniversityDashboard — Phase 8.5 UI Integration Forensic Correction
 *
 * Landing page for institutional roles: nodal_officer and university_admin.
 * Strictly consumes the Phase 6B University institutional API (/api/v1/university/).
 * Does NOT depend on or touch the Phase 8 Admin Control Plane review queue.
 * Does NOT calculate or modify scores client-side.
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
  AlertCircle,
  RefreshCw,
  FileText,
  ShieldCheck,
  Send,
  PlusCircle,
  FileSpreadsheet,
  Eye,
} from "lucide-react";
import { downloadAssessmentReportCSV } from "../../api/reports";
import AssessmentReportModal from "../../components/Reports/AssessmentReportModal";

const STATUS_CONFIG = {
  DRAFT: { bg: "#f8fafc", text: "#475569", border: "#cbd5e1", label: "Draft" },
  SUBMITTED: { bg: "#eff6ff", text: "#1d4ed8", border: "#bfdbfe", label: "Submitted" },
  UNDER_REVIEW: { bg: "#fefce8", text: "#a16207", border: "#fde68a", label: "Under Review" },
  CERTIFIED: { bg: "#f0fdf4", text: "#15803d", border: "#bbf7d0", label: "Certified" },
  REJECTED: { bg: "#fef2f2", text: "#b91c1c", border: "#fecaca", label: "Returned for Correction" },
};

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
    if (!window.confirm("Are you sure you want to formally submit this assessment for Screening Committee evaluation? Once submitted, inputs are locked.")) {
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

  const currentStatusStyle =
    STATUS_CONFIG[activeAssessment?.status] || STATUS_CONFIG.DRAFT;

  const kpis = [
    {
      label: "Assessment Status",
      value: activeAssessment ? currentStatusStyle.label : "Not Started",
      sublabel: activeAssessment ? activeAssessment.assessment_id : "No Session",
      icon: activeAssessment?.status === "CERTIFIED" ? ShieldCheck : Clock,
      color: activeAssessment ? currentStatusStyle.text : "#64748b",
      bg: activeAssessment ? currentStatusStyle.bg : "#f8fafc",
      border: activeAssessment ? currentStatusStyle.border : "#e2e8f0",
    },
    {
      label: "Parameters Completed",
      value: `${completedParameters} / ${totalParameters}`,
      sublabel: `${Math.round((completedParameters / totalParameters) * 100)}% parameters filled`,
      icon: ClipboardList,
      color: "#1d4ed8",
      bg: "#eff6ff",
      border: "#bfdbfe",
    },
    {
      label: "Evidence Coverage",
      value: `${coveredSubcriteria} / ${totalSubcriteria}`,
      sublabel: isReadyForScoring ? "Evidence Gating Passed" : "Action Required",
      icon: CheckCircle2,
      color: isReadyForScoring ? "#15803d" : "#b45309",
      bg: isReadyForScoring ? "#f0fdf4" : "#fffbeb",
      border: isReadyForScoring ? "#bbf7d0" : "#fde68a",
    },
    {
      label: "Statutory Framework",
      value: activeAssessment?.framework || "UNIVERSITY_2026",
      sublabel: activeAssessment?.academic_year || "Academic Year 2025-26",
      icon: Building2,
      color: "#4338ca",
      bg: "#eef2ff",
      border: "#c7d2fe",
    },
  ];

  return (
    <div
      style={{
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "32px 24px",
        fontFamily: "'Outfit', 'Inter', sans-serif",
      }}
    >
      {/* Page Header */}
      <div
        style={{
          background: "linear-gradient(135deg, #1e3a5f 0%, #1d4ed8 100%)",
          borderRadius: "16px",
          padding: "28px 32px",
          color: "#fff",
          marginBottom: "28px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
          boxShadow: "0 4px 20px -4px rgba(29, 78, 216, 0.25)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
            <span
              style={{
                background: "rgba(255,255,255,0.15)",
                border: "1px solid rgba(255,255,255,0.25)",
                borderRadius: "6px",
                padding: "3px 10px",
                fontSize: "11px",
                fontWeight: 700,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
              }}
            >
              {roleLabel}
            </span>
            <span style={{ fontSize: "12px", opacity: 0.8 }}>
              {university ? university.name : "Institutional Portal"}
            </span>
          </div>
          <h1 style={{ fontSize: "24px", fontWeight: 800, margin: "0 0 6px", letterSpacing: "-0.02em" }}>
            University Assessment Workspace
          </h1>
          <p style={{ fontSize: "13px", opacity: 0.85, margin: 0, maxWidth: "600px" }}>
            NEP Excellence Awards 2026 — Self-appraisal parameters (U1–U20), evidence readiness, and submission management.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={loadDashboardData}
            disabled={loading}
            style={{
              background: "rgba(255,255,255,0.12)",
              border: "1px solid rgba(255,255,255,0.2)",
              color: "#fff",
              borderRadius: "8px",
              padding: "8px 14px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              transition: "background 0.15s",
            }}
          >
            <RefreshCw size={13} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "12px",
            padding: "16px 20px",
            marginBottom: "24px",
            display: "flex",
            alignItems: "flex-start",
            gap: "12px",
          }}
        >
          <AlertCircle size={18} color="#b91c1c" style={{ marginTop: "1px", flexShrink: 0 }} />
          <div>
            <p style={{ fontWeight: 700, fontSize: "13px", margin: "0 0 4px", color: "#7f1d1d" }}>
              Action Failed
            </p>
            <p style={{ fontSize: "12px", color: "#991b1b", margin: 0 }}>
              {error}
            </p>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && !university && (
        <div style={{ textAlign: "center", padding: "60px 0" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              border: "3px solid #e2e8f0",
              borderTop: "3px solid #1d4ed8",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
              margin: "0 auto 16px",
            }}
          />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <p style={{ fontSize: "12px", color: "#94a3b8", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Loading institutional assessment...
          </p>
        </div>
      )}

      {/* Main Dashboard Content */}
      {!loading && university && (
        <>
          {/* KPI Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "16px",
              marginBottom: "28px",
            }}
          >
            {kpis.map(({ label, value, sublabel, icon: Icon, color, bg, border }) => (
              <div
                key={label}
                style={{
                  background: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "14px",
                  padding: "20px 24px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                }}
              >
                <div>
                  <p
                    style={{
                      fontSize: "10px",
                      fontWeight: 700,
                      color: "#94a3b8",
                      textTransform: "uppercase",
                      letterSpacing: "0.07em",
                      margin: "0 0 6px",
                    }}
                  >
                    {label}
                  </p>
                  <p
                    style={{
                      fontSize: "24px",
                      fontWeight: 800,
                      color: "#0f172a",
                      margin: "0 0 4px",
                      lineHeight: 1.1,
                    }}
                  >
                    {value}
                  </p>
                  <p style={{ fontSize: "11px", color: "#64748b", margin: 0 }}>
                    {sublabel}
                  </p>
                </div>
                <div
                  style={{
                    background: bg,
                    border: `1px solid ${border}`,
                    borderRadius: "10px",
                    padding: "10px",
                    flexShrink: 0,
                  }}
                >
                  <Icon size={18} color={color} />
                </div>
              </div>
            ))}
          </div>

          {/* Assessment Lifecycle Card */}
          {activeAssessment ? (
            <div
              style={{
                background: "#fff",
                border: "1px solid #e2e8f0",
                borderRadius: "16px",
                padding: "24px",
                marginBottom: "28px",
                boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "16px",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                    <span
                      style={{
                        background: currentStatusStyle.bg,
                        color: currentStatusStyle.text,
                        border: `1px solid ${currentStatusStyle.border}`,
                        borderRadius: "6px",
                        padding: "3px 8px",
                        fontSize: "10px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}
                    >
                      {currentStatusStyle.label}
                    </span>
                    <span style={{ fontSize: "12px", fontFamily: "monospace", color: "#475569", fontWeight: 600 }}>
                      {activeAssessment.assessment_id}
                    </span>
                  </div>
                  <p style={{ fontSize: "13px", color: "#64748b", margin: 0 }}>
                    Academic Period: {activeAssessment.period_start} to {activeAssessment.period_end} · Created on{" "}
                    {new Date(activeAssessment.created_at).toLocaleDateString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </p>
                </div>

                {activeAssessment.status === "DRAFT" && (
                  <button
                    onClick={handleSubmitAssessment}
                    disabled={submitting}
                    style={{
                      background: "#1d4ed8",
                      color: "#fff",
                      border: "none",
                      borderRadius: "8px",
                      padding: "10px 20px",
                      fontSize: "12px",
                      fontWeight: 700,
                      cursor: submitting ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      boxShadow: "0 2px 6px rgba(29, 78, 216, 0.25)",
                    }}
                  >
                    <Send size={13} />
                    {submitting ? "Submitting..." : "Submit to Screening Committee"}
                  </button>
                )}

                {activeAssessment.status !== "DRAFT" ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        fontSize: "12px",
                        color: "#059669",
                        fontWeight: 600,
                      }}
                    >
                      <ShieldCheck size={16} />
                      Submitted for Official Evaluation
                    </div>
                    <button
                      onClick={() => setShowReportModal(true)}
                      style={{
                        background: "#1d4ed8",
                        color: "#ffffff",
                        border: "1px solid #1d4ed8",
                        borderRadius: "8px",
                        padding: "8px 14px",
                        fontSize: "11px",
                        fontWeight: 700,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "5px",
                        boxShadow: "0 1px 3px rgba(29, 78, 216, 0.2)",
                      }}
                      title="Inspect authoritative assessment report and audit ledger"
                    >
                      <Eye size={13} color="#ffffff" />
                      Audit & Assessment Report
                    </button>
                    <button
                      onClick={() => downloadAssessmentReportCSV(activeAssessment.assessment_id)}
                      style={{
                        background: "#f8fafc",
                        color: "#0f172a",
                        border: "1px solid #cbd5e1",
                        borderRadius: "8px",
                        padding: "8px 14px",
                        fontSize: "11px",
                        fontWeight: 700,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "5px",
                      }}
                    >
                      <FileSpreadsheet size={13} color="#16a34a" />
                      Export Audit Report (CSV)
                    </button>
                  </div>
                ) : (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <button
                      onClick={() => setShowReportModal(true)}
                      style={{
                        background: "#f8fafc",
                        color: "#1d4ed8",
                        border: "1px solid #bfdbfe",
                        borderRadius: "8px",
                        padding: "8px 14px",
                        fontSize: "11px",
                        fontWeight: 700,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "5px",
                      }}
                      title="Inspect preliminary assessment report projection"
                    >
                      <Eye size={13} color="#1d4ed8" />
                      View Audit Preview
                    </button>
                  </div>
                )}
              </div>

              {/* Blocking reasons notification if in DRAFT and not ready */}
              {activeAssessment.status === "DRAFT" && readiness && !readiness.is_ready && (
                <div
                  style={{
                    marginTop: "16px",
                    background: "#fffbeb",
                    border: "1px solid #fde68a",
                    borderRadius: "10px",
                    padding: "12px 16px",
                    fontSize: "12px",
                    color: "#92400e",
                  }}
                >
                  <p style={{ fontWeight: 700, margin: "0 0 4px" }}>
                    Evidence Readiness Notice:
                  </p>
                  <p style={{ margin: 0 }}>
                    {readiness.evidence_readiness_summary?.uncovered_subcriteria ?? 51} subcriteria still require mandatory or supporting evidence association prior to final submission.
                  </p>
                </div>
              )}
            </div>
          ) : (
            /* Empty State: No assessment yet */
            <div
              style={{
                background: "#fff",
                border: "1px solid #e2e8f0",
                borderRadius: "16px",
                padding: "48px 24px",
                textAlign: "center",
                marginBottom: "28px",
              }}
            >
              <FileText size={40} color="#cbd5e1" style={{ margin: "0 auto 12px" }} />
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#0f172a", margin: "0 0 6px" }}>
                No Active Assessment Session
              </h3>
              <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 20px", maxWidth: "440px", marginLeft: "auto", marginRight: "auto" }}>
                Begin your institution’s self-appraisal for the NEP Excellence Awards 2026. This will initialize parameter values U1–U20.
              </p>
              <button
                onClick={handleCreateAssessment}
                disabled={creating}
                style={{
                  background: "#1d4ed8",
                  color: "#fff",
                  border: "none",
                  borderRadius: "8px",
                  padding: "10px 20px",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: creating ? "not-allowed" : "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <PlusCircle size={14} />
                {creating ? "Initializing..." : "Start 2025-26 Assessment"}
              </button>
            </div>
          )}

          {/* Parameters Overview Table */}
          {parameters.length > 0 && (
            <div
              style={{
                background: "#fff",
                border: "1px solid #e2e8f0",
                borderRadius: "16px",
                overflow: "hidden",
                boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
              }}
            >
              <div
                style={{
                  padding: "20px 24px",
                  borderBottom: "1px solid #f1f5f9",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", margin: "0 0 4px" }}>
                    Statutory Parameters (U1–U20)
                  </h2>
                  <p style={{ fontSize: "11px", color: "#94a3b8", margin: 0 }}>
                    Authoritative parameters registered under UNIVERSITY_2026 framework
                    {lastRefreshed && ` · Synced at ${lastRefreshed.toLocaleTimeString()}`}
                  </p>
                </div>
              </div>

              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                  <thead>
                    <tr style={{ background: "#f8fafc" }}>
                      {["Code", "Parameter Title", "Max Weight", "Mandatory Evidence", "Completion Status"].map((h) => (
                        <th
                          key={h}
                          style={{
                            padding: "10px 16px",
                            textAlign: "left",
                            fontSize: "10px",
                            fontWeight: 700,
                            color: "#64748b",
                            textTransform: "uppercase",
                            letterSpacing: "0.06em",
                            borderBottom: "1px solid #f1f5f9",
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {parameters.map((param, idx) => {
                      const isComplete = param.submitted_input != null;
                      return (
                        <tr
                          key={param.code}
                          style={{
                            borderBottom: idx < parameters.length - 1 ? "1px solid #f8fafc" : "none",
                            transition: "background 0.1s",
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = "#f8fafc")}
                          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                        >
                          <td style={{ padding: "12px 16px", fontFamily: "monospace", fontSize: "11px", color: "#1d4ed8", fontWeight: 700 }}>
                            {param.code}
                          </td>
                          <td style={{ padding: "12px 16px", fontWeight: 600, color: "#0f172a" }}>
                            {param.title}
                          </td>
                          <td style={{ padding: "12px 16px", color: "#64748b", fontWeight: 600 }}>
                            {param.max_marks} pts
                          </td>
                          <td style={{ padding: "12px 16px", color: "#64748b" }}>
                            {param.mandatory_evidence && param.mandatory_evidence.length > 0 ? (
                              <span style={{ fontSize: "11px", color: "#475569" }}>
                                {param.mandatory_evidence.length} document type{param.mandatory_evidence.length > 1 ? "s" : ""}
                              </span>
                            ) : (
                              <span style={{ fontSize: "11px", color: "#94a3b8", fontStyle: "italic" }}>None</span>
                            )}
                          </td>
                          <td style={{ padding: "12px 16px" }}>
                            <span
                              style={{
                                background: isComplete ? "#f0fdf4" : "#fefce8",
                                color: isComplete ? "#15803d" : "#a16207",
                                border: isComplete ? "1px solid #bbf7d0" : "1px solid #fde68a",
                                borderRadius: "6px",
                                padding: "3px 8px",
                                fontSize: "10px",
                                fontWeight: 700,
                                textTransform: "uppercase",
                                letterSpacing: "0.04em",
                              }}
                            >
                              {isComplete ? "Completed" : "Pending Data"}
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
