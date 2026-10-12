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

const ADMIN_DEV_ACCOUNTS = [
  {
    key: "admin",
    role: "State Admin",
    badge: "HSHEC State",
    description: "Council Control Plane, Institutions, Committees & Reports",
    email: "admin@dev.local",
    password: "DevAdmin@123",
    icon: ShieldCheck,
    themeClass: devStyles.themeMaroon,
  },
  {
    key: "chair",
    role: "Screening Committee Chair",
    badge: "Chairperson",
    description: "Screening Committee Oversight & Final Decision",
    email: "chair@dev.local",
    password: "DevChair@123",
    icon: Award,
    themeClass: devStyles.themeEmerald,
  },
  {
    key: "committee",
    role: "Screening Committee Member",
    badge: "Reviewer",
    description: "Evaluation, Verification & Scoring Review",
    email: "committee@dev.local",
    password: "DevCommittee@123",
    icon: Users,
    themeClass: devStyles.themePurple,
  },
  {
    key: "univadmin",
    role: "Council Admin Overseer",
    badge: "Administration",
    description: "State Council Administration Console",
    email: "univadmin@dev.local",
    password: "DevUnivAdmin@123",
    icon: Building2,
    themeClass: devStyles.themeBlue,
  },
];

export default function AdminSignin() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState({ type: "", message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeDevRole, setActiveDevRole] = useState(null);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatus({ type: "", message: "" });

    try {
      const response = await login(formData);
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
        message: response.message || "Authorized sign in successful.",
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

  const handleDevLogin = async (account) => {
    if (isSubmitting) return;

    setFormData({
      email: account.email,
      password: account.password,
    });
    setActiveDevRole(account.key);
    setIsSubmitting(true);
    setStatus({
      type: "success",
      message: `Signing in as ${account.role}...`,
    });

    try {
      const response = await login({
        email: account.email,
        password: account.password,
      });
      setStatus({
        type: "success",
        message: response.message || `Signed in as ${account.role}. Entering console...`,
      });
      navigate(getDashboardPathForUser(response.user));
    } catch (error) {
      setStatus({
        type: "error",
        message: error.message || `Could not sign in as ${account.role}. Ensure backend server is running.`,
      });
      setActiveDevRole(null);
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
                <span>State Council & Committee Portal</span>
              </span>
            </div>
            <h2 id="admin-signin-title" className={styles.formTitle}>
              Authorized Administration & Committee Review Login
            </h2>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              Secure access for HSHEC State Administrators, Screening Committee members, and Empowered Committee authorities.
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
              <label htmlFor="email">Official Administrative Email ID</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                placeholder="admin@hshec.gov.in"
                autoComplete="email"
              />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="password">Security Password</label>
              <div className={styles.inputWithIcon}>
                <input
                  type={showPassword ? "text" : "password"}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  placeholder="Enter your security password"
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
                {isSubmitting && !activeDevRole ? "Authenticating Authority..." : "Sign In to Council Console"}
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

          {/* Quick Dev Login Buttons */}
          <div className={devStyles.devLoginSection}>
            <div className={devStyles.devHeader}>
              <span className={devStyles.devBadge}>
                <Sparkles size={13} className={devStyles.devBadgeIcon} />
                Quick Dev Admin Login
              </span>
              <p className={devStyles.devSubtitle}>
                Pre-configured administrative and committee roles
              </p>
            </div>

            <div className={devStyles.devGrid}>
              {ADMIN_DEV_ACCOUNTS.map((account) => {
                const IconComponent = account.icon;
                const isActive = activeDevRole === account.key;
                return (
                  <button
                    key={account.key}
                    type="button"
                    onClick={() => handleDevLogin(account)}
                    disabled={isSubmitting}
                    className={`${devStyles.devCard} ${account.themeClass} ${
                      isActive ? devStyles.devCardActive : ""
                    }`}
                    title={`Click to login as ${account.role} (${account.email})`}
                  >
                    <div className={devStyles.cardTopRow}>
                      <div className={devStyles.iconWrapper}>
                        {isActive ? (
                          <Loader2 size={16} className={devStyles.loadingSpinner} />
                        ) : (
                          <IconComponent size={16} />
                        )}
                      </div>
                      <span className={devStyles.roleTag}>{account.badge}</span>
                      <span className={devStyles.enterArrow}>
                        <ArrowRight size={14} />
                      </span>
                    </div>

                    <h4 className={devStyles.roleTitle}>
                      {isActive ? "Entering..." : account.role}
                    </h4>
                    <p className={devStyles.roleDesc}>{account.description}</p>
                    <div className={devStyles.credentialsPill}>
                      <span>{account.email}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
