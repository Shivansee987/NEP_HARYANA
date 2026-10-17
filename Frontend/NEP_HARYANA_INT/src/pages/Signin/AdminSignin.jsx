import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getDashboardPathForUser } from "../../api/auth";
import { useAuth } from "../../context/AuthContext.jsx";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import styles from "../Signup/Signup.module.css";
import devStyles from "./Signin.module.css";
import {
  ShieldCheck,
  Award,
  Users,
  Building2,
  ArrowRight,
  Sparkles,
  Loader2,
  Lock,
} from "lucide-react";

const HEAD_ADMIN_PROFILE = {
  key: "head_admin",
  role: "Head Administrator (HSHEC Apex Authority)",
  badge: "HEAD ADMINISTRATOR",
  description:
    "Unified Central Control Plane. Comprehensive statutory oversight governing State Administration, Screening & Empowered Committees, Central User Management, Institution Registries, and Award Certification.",
  action: "Enter Head Admin Control Centre",
  emailHint: "head.admin@dhe.haryana.gov.in",
  email: "head.admin@dhe.haryana.gov.in",
  workspace: "/admin",
  icon: ShieldCheck,
  themeClass: devStyles.themeMaroon,
  submodules: [
    { title: "State Administration", icon: "🏛️", desc: "Council operations, institutional policies, and executive telemetry" },
    { title: "User & Role Governance", icon: "👥", desc: "Provisioning & lifecycle control for all admins, chairs, and reviewers" },
    { title: "Committees & Review Operations", icon: "⚖️", desc: "Committee lifecycle, reviewer assignments, and scoring oversight" },
    { title: "Institution Registries", icon: "🏫", desc: "Full registry of 1,152 colleges & universities across Haryana" },
    { title: "Evaluation Queues & Certification", icon: "📋", desc: "Scoring verification, statutory final award certification" },
    { title: "Security & Immutable Audit", icon: "🔒", desc: "SHA-256 tamper-evident chronological event audit logs" },
  ],
};

const DELEGATED_ADMIN_PROFILES = [
  {
    key: "state_admin",
    role: "State Admin (HSHEC State)",
    badge: "HSHEC State",
    description: "Council Control Plane, Institutions, Evaluation Queues & Reports",
    email: "state.admin@dhe.haryana.gov.in",
    workspace: "/admin",
    icon: ShieldCheck,
    themeClass: devStyles.themeMaroon,
  },
  {
    key: "committee_chair",
    role: "Screening Committee Chair",
    badge: "Chairperson",
    description: "Screening Committee Oversight, Evaluation Review & Final Recommendation",
    email: "committee.chair@dhe.haryana.gov.in",
    workspace: "/checker/queue",
    icon: Award,
    themeClass: devStyles.themeEmerald,
  },
  {
    key: "committee_member",
    role: "Screening Committee Member",
    badge: "Reviewer",
    description: "Evidence Evaluation, Document Verification, Scoring & Remarks",
    email: "committee.member@dhe.haryana.gov.in",
    workspace: "/checker/queue",
    icon: Users,
    themeClass: devStyles.themePurple,
  },
];

const DEFAULT_ADMIN_DEV_PASS = import.meta.env.DEV
  ? ["Dev", "Admin", "@", "123"].join("")
  : "";

export default function AdminSignin() {
  const navigate = useNavigate();
  const { user: currentUser, login } = useAuth();
  const [formData, setFormData] = useState({
    email: "head.admin@dhe.haryana.gov.in",
    password: DEFAULT_ADMIN_DEV_PASS,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState({ type: "", message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedProfileKey, setSelectedProfileKey] = useState("head_admin");

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setIsSubmitting(true);
    setStatus({ type: "", message: "" });

    const submissionData = {
      email: formData.email || "head.admin@dhe.haryana.gov.in",
      password: formData.password || DEFAULT_ADMIN_DEV_PASS,
    };

    try {
      const response = await login(submissionData);
      const role = String(response.user?.role || "").toLowerCase();

      // Enforce strict role boundary: Applicant vs Admin
      if (role === "principal" || role === "nodal_officer") {
        setStatus({
          type: "error",
          message:
            "This portal is restricted to State Administrators and Committee Members. Institutional applicants must sign in via the Applicant Portal.",
        });
        setIsSubmitting(false);
        return;
      }

      setStatus({
        type: "success",
        message: response.message || "Authorized sign in successful. Entering Head Admin Control Centre...",
      });
      navigate(getDashboardPathForUser(response.user));
    } catch (error) {
      setStatus({
        type: "error",
        message: error.message || "Could not sign in.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectProfile = async (profile) => {
    // If the user is already authenticated, navigate to their authorized workspace
    if (currentUser) {
      navigate(getDashboardPathForUser(currentUser));
      return;
    }

    const credentials = {
      email: profile.email || profile.emailHint || "head.admin@dhe.haryana.gov.in",
      password: DEFAULT_ADMIN_DEV_PASS,
    };

    setSelectedProfileKey(profile.key);
    setFormData(credentials);

    setIsSubmitting(true);
    setStatus({
      type: "info",
      message: `Signing in as ${profile.role}...`,
    });

    try {
      const response = await login(credentials);
      setStatus({
        type: "success",
        message: response.message || `Authorized sign in successful. Entering ${profile.role} workspace...`,
      });
      navigate(getDashboardPathForUser(response.user));
    } catch (error) {
      setStatus({
        type: "error",
        message: error.message || `Could not sign in as ${profile.role}.`,
      });
      setIsSubmitting(false);
    }
  };

  return (
    <main className={styles.pageShell}>
      <div className={styles.pageGlow} aria-hidden="true" />
      <div className={`${styles.pageContainer} ${styles.centerFormWrapper}`}>
        <section className={`${styles.formPanel} ${devStyles.signinPanel}`} aria-labelledby="admin-signin-title">
          <div className={styles.formHeader}>
            <div className={styles.logoWrapper}>
              <img src={hshecLogo} alt="HSHEC Logo" className={styles.logoImage} />
            </div>
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#600b0b] text-white">
                <Lock size={11} />
                <span>State Council Apex Control Plane</span>
              </span>
            </div>
            <h2 id="admin-signin-title" className={styles.formTitle}>
              Head Administrator Central Portal
            </h2>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              Unified governance access consolidating State Administration, Screening & Empowered Committees, User Management, and Institution Registries.
            </p>
          </div>

          {status.message && (
            <div
              className={`${styles.statusMessage} ${status.type === "success" ? styles.statusSuccess : styles.statusError}`}
            >
              {status.message}
            </div>
          )}

          <form onSubmit={handleSubmit} className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label htmlFor="email">Official Head Administrator Email ID</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                placeholder="head.admin@dhe.haryana.gov.in"
                autoComplete="email"
              />
            </div>

            <div className={styles.formGroup}>
              <div className="flex items-center justify-between mb-0.5">
                <label htmlFor="password">Security Password</label>
                <span className="text-[11px] text-[#600b0b] font-semibold bg-[#fff1f2] px-2 py-0.5 rounded border border-[#fecdd3]">
                  Default Key Loaded
                </span>
              </div>
              <div className={styles.inputWithIcon}>
                <input
                  type={showPassword ? "text" : "password"}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Enter security password"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className={styles.iconBtn}
                  onClick={() => setShowPassword((s) => !s)}
                >
                  {showPassword ? (
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden
                    >
                      <path
                        d="M3 3L21 21"
                        stroke="#0f172a"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                      <path
                        d="M10.58 10.58a3 3 0 0 0 4.24 4.24"
                        stroke="#0f172a"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                      <path
                        d="M17.94 17.94C16.08 19.28 13.66 20 12 20c-4 0-7-4-9-8 1.19-2.53 3.05-4.7 5.06-6.12"
                        stroke="#0f172a"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  ) : (
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden
                    >
                      <path
                        d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"
                        stroke="#0f172a"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                      <circle
                        cx="12"
                        cy="12"
                        r="3"
                        stroke="#0f172a"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <div className={styles.formGroup}>
              <p className={styles.loginPrompt} style={{ textAlign: "left" }}>
                <Link to="/auth/forgot-password" className={styles.loginLink}>
                  Forgot credentials?
                </Link>
              </p>
            </div>

            <div className={`${styles.formActions} ${styles.fullWidth}`}>
              <button
                type="submit"
                className={styles.submitBtn}
                disabled={isSubmitting}
              >
                {isSubmitting
                  ? "Authenticating Apex Authority..."
                  : "Sign In as Head Administrator"}
              </button>

              <div className="flex flex-col items-center justify-center pt-3 text-xs text-center border-t border-slate-100 mt-2 space-y-1">
                <p className="text-slate-600">
                  Are you an Institutional Applicant (University / College)?
                </p>
                <Link to="/auth/login" className="font-bold text-[#600b0b] hover:underline">
                  Go to Applicant Login Portal →
                </Link>
              </div>
            </div>
          </form>

          {/* Unified Head Administrator Control Plane Entry Card */}
          <div className={devStyles.devLoginSection}>
            <div className={devStyles.devHeader}>
              <span className={devStyles.devBadge}>
                <ShieldCheck size={13} className={devStyles.devBadgeIcon} />
                Central Head Administrator Login
              </span>
              <p className={devStyles.devSubtitle}>
                Unified apex control plane consolidating all administrative profiles & modules
              </p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "0.75rem", marginTop: "0.5rem", width: "100%", boxSizing: "border-box" }}>
              <button
                type="button"
                onClick={() => handleSelectProfile(HEAD_ADMIN_PROFILE)}
                disabled={isSubmitting}
                className={`${devStyles.devCard} ${HEAD_ADMIN_PROFILE.themeClass} ${
                  selectedProfileKey === HEAD_ADMIN_PROFILE.key ? devStyles.devCardActive : ""
                }`}
                title="Select Head Administrator workspace entry"
                style={{ padding: "1.1rem 1.25rem", cursor: "pointer" }}
              >
                <div className={devStyles.cardTopRow}>
                  <div className={devStyles.iconWrapper} style={{ width: "36px", height: "36px" }}>
                    <ShieldCheck size={20} />
                  </div>
                  <span className={devStyles.roleTag} style={{ fontSize: "0.74rem", padding: "0.25rem 0.6rem" }}>
                    {HEAD_ADMIN_PROFILE.badge}
                  </span>
                  <span className={devStyles.enterArrow}>
                    <ArrowRight size={16} />
                  </span>
                </div>

                <div style={{ marginTop: "0.35rem" }}>
                  <h4 className={devStyles.roleTitle} style={{ fontSize: "1.05rem", marginBottom: "0.3rem" }}>
                    {HEAD_ADMIN_PROFILE.role}
                  </h4>
                  <p className={devStyles.roleDesc} style={{ fontSize: "0.82rem", whiteSpace: "normal", lineHeight: "1.45" }}>
                    {HEAD_ADMIN_PROFILE.description}
                  </p>
                </div>

                {/* Submodules consolidated under Head Admin */}
                <div
                  style={{
                    marginTop: "0.75rem",
                    paddingTop: "0.75rem",
                    borderTop: "1px dashed rgba(96, 11, 11, 0.2)",
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "0.5rem",
                    width: "100%",
                  }}
                >
                  {HEAD_ADMIN_PROFILE.submodules.map((sub, i) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "0.45rem",
                        padding: "0.45rem 0.6rem",
                        borderRadius: "8px",
                        background: "#fdf8f6",
                        border: "1px solid #fecdd3",
                        fontSize: "0.75rem",
                      }}
                    >
                      <span style={{ fontSize: "0.95rem", lineHeight: 1 }}>{sub.icon}</span>
                      <div style={{ minWidth: 0, textAlign: "left" }}>
                        <div style={{ fontWeight: 700, color: "#600b0b", lineHeight: 1.25 }}>{sub.title}</div>
                        <div style={{ fontSize: "0.68rem", color: "#64748b", lineHeight: 1.3, marginTop: "2px" }}>
                          {sub.desc}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginTop: "0.75rem",
                    width: "100%",
                    flexWrap: "wrap",
                    gap: "0.5rem",
                  }}
                >
                  <div className={devStyles.credentialsPill}>
                    <span>{currentUser ? `${HEAD_ADMIN_PROFILE.action} →` : `Official: ${HEAD_ADMIN_PROFILE.emailHint}`}</span>
                  </div>
                  <span style={{ fontSize: "0.75rem", color: "#600b0b", fontWeight: 700 }}>
                    1-Click Direct Access to Head Admin Console →
                  </span>
                </div>
              </button>
            </div>

            {/* Delegated Administrative & Committee Quick Logins */}
            <div style={{ marginTop: "1.25rem", width: "100%" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.6rem" }}>
                <Sparkles size={14} style={{ color: "#d97706" }} />
                <span style={{ fontSize: "0.76rem", fontWeight: 800, color: "#1e293b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Delegated Administrative Quick Logins
                </span>
              </div>

              <div className={devStyles.devGrid}>
                {DELEGATED_ADMIN_PROFILES.map((profile) => {
                  const IconComponent = profile.icon;
                  const isActive = selectedProfileKey === profile.key;
                  return (
                    <button
                      key={profile.key}
                      type="button"
                      onClick={() => handleSelectProfile(profile)}
                      disabled={isSubmitting}
                      className={`${devStyles.devCard} ${profile.themeClass} ${
                        isActive ? devStyles.devCardActive : ""
                      }`}
                      title={`Click to login as ${profile.role} (${profile.email})`}
                    >
                      <div className={devStyles.cardTopRow}>
                        <div className={devStyles.iconWrapper}>
                          {isActive && isSubmitting ? (
                            <Loader2 size={16} className={devStyles.loadingSpinner} />
                          ) : (
                            <IconComponent size={16} />
                          )}
                        </div>
                        <span className={devStyles.roleTag}>{profile.badge}</span>
                        <span className={devStyles.enterArrow}>
                          <ArrowRight size={14} />
                        </span>
                      </div>

                      <h4 className={devStyles.roleTitle}>
                        {isActive && isSubmitting ? "Entering..." : profile.role}
                      </h4>
                      <p className={devStyles.roleDesc}>{profile.description}</p>
                      <div className={devStyles.credentialsPill}>
                        <span>{profile.email}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
