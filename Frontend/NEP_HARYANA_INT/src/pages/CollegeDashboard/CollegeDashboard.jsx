import { useState, useEffect, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import styles from "../Dashboard/Dashboard.module.css";
import pageStyles from "./CollegeDashboard.module.css";
import { useAuth } from "../../context/AuthContext.jsx";
import { fetchNominationDetails, fetchMySubmissions } from "../../api/nomination";
import NominationWorkspace from "./NominationWorkspace";
import { LayoutDashboard, CheckSquare, School } from "lucide-react";
import hshecLogo from "../../assets/hshec_logo.jpeg";

function formatRole(role) {
  if (role === "principal") {
    return "College Principal";
  }
  if (role === "admin") {
    return "DHE Admin";
  }
  if (role === "committee") {
    return "Screening Committee";
  }
  return "Principal";
}

function CollegeDashboard() {
  const navigate = useNavigate();
  const { institutionName, institutionAisheCode, formId } = useParams();
  const [activeMenu, setActiveMenu] = useState("Dashboard");
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);

  const { user: savedUser, logout } = useAuth();
  const collegeName = savedUser?.college_name || "Govt College Example";
  const principalName = savedUser?.full_name || "Dr. Rajesh Kumar";
  const principalRole = formatRole(savedUser?.role);
  const aisheCode = savedUser?.aishe_code || "C-12345";
  
  // Nomination Details State
  const [nomination, setNomination] = useState(null);
  const [nominationLoading, setNominationLoading] = useState(false);
  const [nominationError, setNominationError] = useState("");
  
  const [selectedFormId, setSelectedFormId] = useState(null);

  // Submissions loading state
  const [submissionsList, setSubmissionsList] = useState([]);
  const [submissionsLoading, setSubmissionsLoading] = useState(false);
  const [submissionsError, setSubmissionsError] = useState("");

  const collegeNameSlug = String(savedUser?.college_name || "college")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)+/g, "");
  const collegeAisheSlug = String(savedUser?.aishe_code || "code")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)+/g, "");

  const instName = institutionName || collegeNameSlug;
  const instAishe = institutionAisheCode || collegeAisheSlug;

  useEffect(() => {
    if (formId) {
      setSelectedFormId(formId);
    } else {
      setSelectedFormId(null);
    }
  }, [formId]);

  const loadSubmissionsList = useCallback(async () => {
    setSubmissionsLoading(true);
    setSubmissionsError("");
    try {
      const data = await fetchMySubmissions();
      setSubmissionsList(data);
    } catch (err) {
      console.error("Failed to load submissions list:", err);
      setSubmissionsError(err.message || "Failed to load submissions.");
    } finally {
      setSubmissionsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeMenu === "My Submissions") {
      loadSubmissionsList();
    }
  }, [activeMenu, loadSubmissionsList]);

  const loadNomination = useCallback(async () => {
    setNominationLoading(true);
    setNominationError("");
    try {
      const data = await fetchNominationDetails("nep-excellence-nomination-2025");
      setNomination(data);
    } catch (err) {
      console.error("Failed to load nomination:", err);
      setNominationError(err.message || "Failed to load nomination details.");
    } finally {
      setNominationLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeMenu === "Dashboard") {
      loadNomination();
    }
  }, [activeMenu, loadNomination]);

  const handleLogout = async () => {
    await logout();
    setShowProfileDropdown(false);
    navigate("/auth/login");
  };

  const menuItems = [
    { title: "Dashboard", icon: LayoutDashboard },
    { title: "My Submissions", icon: CheckSquare },
  ];

  return (
    <div className={styles.dashboardLayout}>
      <aside className="peer fixed inset-y-0 left-0 w-20 hover:w-64 bg-white text-slate-800 flex flex-col z-20 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border-r border-slate-100 transition-all duration-300 ease-in-out group overflow-hidden">
        {/* Brand Header */}
        <div className="h-16 flex items-center px-4 border-b border-slate-100 bg-slate-50/30">
          <div className="flex items-center space-x-3 w-full">
            <div className="w-10 h-10 rounded-xl bg-white border border-slate-200/60 flex items-center justify-center shadow-sm shrink-0 overflow-hidden p-1 transition-transform duration-300 group-hover:scale-105">
              <img src={hshecLogo} alt="HSHEC Logo" className="w-full h-full object-contain" />
            </div>
            <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap min-w-0">
              <h1 className="text-xs font-bold tracking-tight text-slate-800 leading-none">HSHEC</h1>
              <span className="text-[9px] text-blue-600 font-bold uppercase tracking-wider block mt-0.5">Principal Portal</span>
            </div>
          </div>
        </div>

        {/* Nav Menu */}
        <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1.5">
          <span className="px-3.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-2.5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
            Principal Portal
          </span>
          <ul className="space-y-1">
            {menuItems.map((item, index) => {
              const Icon = item.icon;
              const isActive = activeMenu === item.title;
              return (
                <li key={index}>
                  <button
                    type="button"
                    className={`w-full flex items-center gap-3 px-3.5 py-3 rounded-xl transition-all duration-300 text-sm font-medium relative group/item ${isActive
                        ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/20 font-semibold'
                        : 'text-slate-600 hover:bg-blue-50/50 hover:text-blue-600'
                      }`}
                    onClick={() => {
                      setActiveMenu(item.title);
                      if (formId) {
                        navigate(`/institution/${instName}/${instAishe}/dashboard`);
                      }
                    }}
                  >
                    <Icon className={`w-5 h-5 shrink-0 transition-transform duration-300 group-hover/item:scale-110 ${isActive ? 'text-white' : 'text-slate-400 group-hover/item:text-blue-600'
                      }`} />
                    <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
                      {item.title}
                    </span>
                    {/* Subtle hover/active indicator */}
                    {isActive && (
                      <span className="absolute right-3 w-1.5 h-1.5 rounded-full bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Institution Profile Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/40 backdrop-blur-md">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-100 to-indigo-50 border border-blue-200/50 flex items-center justify-center text-blue-600 font-bold shadow-sm shrink-0">
              <School className="w-5 h-5 text-blue-600" />
            </div>
            <div className="min-w-0 flex-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
              <p className="text-xs font-semibold text-slate-800 truncate" title={collegeName}>{collegeName}</p>
              <p className="text-[10px] text-blue-600 font-semibold truncate">AISHE: {aisheCode}</p>
            </div>
          </div>
        </div>
      </aside>

      <div className={styles.mainContent}>
        <header className={styles.topNavbar}>
          <div className={styles.headerTitle}>
            <div className={styles.breadcrumbs}>
              <span>Home</span>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M9 5l7 7-7 7" />
              </svg>
              <span className={styles.breadcrumbActive}>{activeMenu}</span>
            </div>
            <h2>{activeMenu}</h2>
            <p>NEP Excellence Awards Evaluation Portal.</p>
          </div>

          <div className={styles.headerActions}>
            <div className={styles.profileWrapper}>
              <div
                className={styles.userProfile}
                onClick={() => setShowProfileDropdown(!showProfileDropdown)}
              >
                <div className={styles.avatar}>PP</div>
                <div>
                  <h4>{principalName}</h4>
                  <span>{principalRole}</span>
                </div>
              </div>

              {showProfileDropdown && (
                <div className={styles.dropdownMenu}>
                  <button
                    type="button"
                    className={styles.dropdownItemButton}
                    onClick={handleLogout}
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>

            <button
              type="button"
              className={styles.logoutButton}
              onClick={handleLogout}
            >
              Logout
            </button>
          </div>
        </header>

        {selectedFormId ? (
          <NominationWorkspace formId={selectedFormId} onBack={() => navigate(`/institution/${instName}/${instAishe}/dashboard`)} />
        ) : activeMenu === "Dashboard" ? (
          <div style={{ padding: "24px" }}>
            {nominationError && (
              <div style={{ backgroundColor: "#fee2e2", borderLeft: "4px solid #ef4444", color: "#b91c1c", padding: "12px", borderRadius: "8px", fontSize: "0.875rem", marginBottom: "24px" }}>
                {nominationError}
              </div>
            )}

            {nominationLoading ? (
              <div className={pageStyles.loadingContainer}>
                <div className={pageStyles.spinner}></div>
                <p style={{ color: "#64748b", fontSize: "0.875rem" }}>Loading dashboard details...</p>
              </div>
            ) : (
              <>
              
                <div className={pageStyles.overviewGrid}>
                  <section className={pageStyles.welcomeCard}>
                    <h3>HSHEC Principal Portal</h3>
                    <p>
                      Welcome to the Haryana State Higher Education Council portal.
                      Review your metrics, fill indicators, and submit the institutional nomination form.
                    </p>
                    <button
                      type="button"
                      className={pageStyles.startBtn}
                      onClick={() => navigate(`/institution/${instName}/${instAishe}/dashboard/forms/nep-excellence-nomination-2025`)}
                    >
                      {nomination?.is_submitted ? "View Nomination" : nomination?.answers && Object.keys(nomination.answers).length > 0 ? "Continue Form" : "Start Nomination"}
                    </button>
                  </section>

                  <section className={pageStyles.infoCard}>
                    <h3>Institution Profile</h3>
                    <div className={pageStyles.infoDetails}>
                      <div className={pageStyles.infoRow}>
                        <span>College Name:</span>
                        <strong>{collegeName}</strong>
                      </div>
                      <div className={pageStyles.infoRow}>
                        <span>AISHE Code:</span>
                        <strong>{aisheCode}</strong>
                      </div>
                      <div className={pageStyles.infoRow}>
                        <span>Principal:</span>
                        <strong>{principalName}</strong>
                      </div>
                      <div className={pageStyles.infoRow}>
                        <span>Role:</span>
                        <strong>{principalRole}</strong>
                      </div>
                    </div>
                  </section>

                  <section className={pageStyles.statusCard}>
                    <div className={pageStyles.statusHeader}>
                      <h3>Nomination Status</h3>
                      <span className={`${pageStyles.statusBadge} ${nomination?.is_submitted ? pageStyles.submitted : pageStyles.draft}`}>
                        {nomination?.is_submitted ? "Submitted" : "Draft Mode"}
                      </span>
                    </div>
                    <div className={pageStyles.statusContent}>
                      <p>
                        {nomination?.is_submitted
                          ? "Your institutional nomination form has been locked and submitted to the screening committee."
                          : "Your nomination form is in draft mode. You can edit answers and submit once all sections are complete."}
                      </p>
                      <div style={{ marginBottom: "16px", fontSize: "0.85rem", color: "#64748b" }}>
                        <strong>Progress: </strong> 
                        {(() => {
                          const ans = nomination?.answers || {};
                          let count = 0;
                          for (let i = 1; i <= 20; i++) {
                            const val = ans[`indicator_${i}`];
                            if (val?.value || (i === 20 && val?.percentage !== undefined && val?.percentage !== "")) count++;
                          }
                          return `${count} of 20 indicators completed (${Math.round((count/20)*100)}%)`;
                        })()}
                      </div>
                      <div className={pageStyles.actionButtonGroup}>
                        <button
                          type="button"
                          className={pageStyles.primaryActionBtn}
                          onClick={() => navigate(`/institution/${instName}/${instAishe}/dashboard/forms/nep-excellence-nomination-2025`)}
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: "4px" }}>
                            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 113 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                          {nomination?.is_submitted ? "View Answers" : "Edit Application"}
                        </button>
                      </div>
                    </div>
                  </section>
                </div>

              </>
            )}
          </div>
        ) : activeMenu === "My Submissions" ? (
          <div style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "1.25rem", fontWeight: "700", marginBottom: "18px", color: "#1e293b" }}>My Submissions</h3>
            {submissionsError && (
              <div style={{ backgroundColor: "#fee2e2", borderLeft: "4px solid #ef4444", color: "#b91c1c", padding: "12px", borderRadius: "8px", fontSize: "0.875rem", marginBottom: "16px" }}>
                {submissionsError}
              </div>
            )}
            {submissionsLoading ? (
              <div className={pageStyles.loadingContainer}>
                <div className={pageStyles.spinner}></div>
                <p style={{ color: "#64748b", fontSize: "0.875rem" }}>Loading submissions...</p>
              </div>
            ) : submissionsList.length === 0 ? (
              <p style={{ color: "#64748b", fontSize: "0.875rem" }}>No submissions found for your institution.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                {submissionsList.map((sub) => (
                  <div key={sub.id} style={{ backgroundColor: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "16px", padding: "24px", boxShadow: "0 4px 20px rgba(0,0,0,0.02)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "20px" }}>
                    <div style={{ flex: "1", minWidth: "280px" }}>
                      <span style={{ fontSize: "0.6875rem", backgroundColor: "#f1f5f9", padding: "4px 10px", borderRadius: "9999px", textTransform: "uppercase", fontWeight: "700", color: "#64748b" }}>Form ID: {sub.form_id}</span>
                      <h4 style={{ fontSize: "1.1rem", fontWeight: "700", marginTop: "12px", marginBottom: "8px", color: "#0f172a" }}>
                        {sub.form_id === "nep-excellence-nomination-2025" 
                          ? "Haryana State NEP 2020 Implementation Excellence Award — Nomination Form 2025" 
                          : "Institutional Nomination Form"}
                      </h4>
                      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", fontSize: "0.85rem", color: "#64748b", marginTop: "12px" }}>
                        <span><strong>Head:</strong> {sub.head_name || "N/A"}</span>
                        <span><strong>Contact:</strong> {sub.head_contact || "N/A"}</span>
                        <span><strong>Updated:</strong> {new Date(sub.updated_at).toLocaleDateString()}</span>
                        {sub.submitted_at && <span><strong>Submitted:</strong> {new Date(sub.submitted_at).toLocaleDateString()}</span>}
                      </div>
                    </div>
                    
                    <div style={{ display: "flex", alignItems: "center", gap: "24px", flexWrap: "wrap" }}>
                      <div style={{ textAlign: "center" }}>
                        <span style={{ display: "block", fontSize: "0.75rem", color: "#64748b", fontWeight: "600", textTransform: "uppercase", marginBottom: "4px" }}>Status</span>
                        <span style={{
                          fontSize: "0.75rem",
                          fontWeight: "700",
                          padding: "6px 14px",
                          borderRadius: "9999px",
                          textTransform: "uppercase",
                          backgroundColor: sub.status === "Clarification Requested" 
                            ? "#fee2e2" 
                            : sub.is_submitted 
                              ? "#d1fae5" 
                              : "#fef3c7",
                          color: sub.status === "Clarification Requested"
                            ? "#ef4444"
                            : sub.is_submitted
                              ? "#065f46"
                              : "#78350f"
                        }}>{sub.status === "Clarification Requested" ? "Clarification Requested" : sub.is_submitted ? "Submitted" : "Draft"}</span>
                      </div>

                      <div>
                        <button
                          type="button"
                          className={styles.secondaryBtn}
                          style={{ padding: "10px 20px", fontSize: "0.875rem", fontWeight: "600", borderColor: "#e8791d", color: "#e8791d", cursor: "pointer" }}
                          onClick={() => navigate(`/institution/${instName}/${instAishe}/dashboard/forms/${sub.form_id}`)}
                        >
                          {sub.is_submitted ? "View Answers" : "Continue Editing"}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default CollegeDashboard;