import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getDashboardPathForUser } from "../../api/auth";
import { useAuth } from "../../context/AuthContext.jsx";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import styles from "../Signup/Signup.module.css";
import devStyles from "./Signin.module.css";
import {
  School,
  Landmark,
  Building2,
  ShieldCheck,
  Award,
  Users,
  ArrowRight,
  Sparkles,
  Loader2,
} from "lucide-react";

// Development-only quick logins. `import.meta.env.DEV` is a build-time constant, so production builds drop this
// list (and its credentials) entirely and render no quick-login section (FIN-02).
const APPLICANT_DEV_ACCOUNTS = import.meta.env.DEV ? [
  {
    key: "demo_college",
    role: "Dyal Singh College, Karnal",
    badge: "College Applicant",
    description: "Full data · All 22 forms filled · C1–C22 Workspace",
    email: "principal.karnal@demo.local",
    password: "Demo@1234",
    icon: School,
    themeClass: devStyles.themeAmber,
  },
  {
    key: "demo_university",
    role: "GJU, Hisar",
    badge: "University Nodal Officer",
    description: "Full data · All 20 forms filled · U1–U20 Workspace",
    email: "nodal.gju@demo.local",
    password: "Demo@1234",
    icon: Landmark,
    themeClass: devStyles.themeIndigo,
  },
  {
    key: "principal",
    role: "Dev College",
    badge: "College · Blank",
    description: "Blank assessment · Show fresh C1–C22 forms",
    email: "principal@dev.local",
    password: "DevPrincipal@123",
    icon: School,
    themeClass: devStyles.themeSlate,
  },
  {
    key: "nodal",
    role: "Dev University",
    badge: "University · Blank",
    description: "Blank assessment · Show fresh U1–U20 forms",
    email: "nodal@dev.local",
    password: "DevNodal@123",
    icon: Landmark,
    themeClass: devStyles.themeSlate,
  },
] : [];

function Signin() {
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
      if (["admin", "committee", "committee_chair"].includes(role)) {
        setStatus({
          type: "error",
          message:
            "This portal is reserved for College and University applicants. Please use the State Admin & Committee Portal.",
        });
        setIsSubmitting(false);
        return;
      }

      setStatus({
        type: "success",
        message: response.message || "Signed in successfully.",
      });
      navigate(getDashboardPathForUser(response.user));
    } catch (error) {
      if (error.code === "EMAIL_NOT_VERIFIED") {
        setStatus({
          type: "error",
          message: error.message || "Please verify your email address before logging in.",
          needsEmailVerification: true,
          email: error.email || formData.email,
        });
      } else {
        setStatus({
          type: "error",
          message: error.message || "Could not sign in.",
        });
      }
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
        message: response.message || `Signed in as ${account.role}. Entering dashboard...`,
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
        <section className={`${styles.formPanel} ${devStyles.signinPanel}`} aria-labelledby="signin-title">
          <div className={styles.formHeader}>
            <div className={styles.logoWrapper}>
              <img src={hshecLogo} alt="HSHEC Logo" className={styles.logoImage} />
            </div>
            <span className={styles.formBadge}>Institutional Applicant Portal</span>
            <h2 id="signin-title" className={styles.formTitle}>
              University & College Applicant Workspace Login
            </h2>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              Sign in to manage your institutional submission for University (U1–U20) or College (C1–C22) NEP Awards.
            </p>
          </div>

          {status.message && (
            <div
              className={`${styles.statusMessage} ${status.type === "success" ? styles.statusSuccess : styles.statusError}`}
            >
              <div>{status.message}</div>
              {status.needsEmailVerification && (
                <div style={{ marginTop: "8px", fontSize: "12px" }}>
                  <Link
                    to={`/auth/verify-email/otp?email=${encodeURIComponent(status.email || formData.email)}`}
                    style={{ color: "#600b0b", fontWeight: "bold", textDecoration: "underline" }}
                  >
                    Enter 6-Digit Email Verification Code →
                  </Link>
                </div>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className={`${styles.formGrid}`}>
            <div className={styles.formGroup}>
              <label htmlFor="email">Email ID</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                placeholder="official@college.edu.in"
                autoComplete="email"
              />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="password">Password</label>
              <div className={styles.inputWithIcon}>
                <input
                  type={showPassword ? "text" : "password"}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  placeholder="Enter your password"
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
                  Forgot password?
                </Link>
              </p>
            </div>

            <div className={`${styles.formActions} ${styles.fullWidth}`}>
              <button
                type="submit"
                className={styles.submitBtn}
                disabled={isSubmitting}
              >
                {isSubmitting && !activeDevRole ? "Signing In..." : "Sign In"}
              </button>

              <div className="flex items-center justify-center pt-2 text-xs text-center">
                <p className={styles.loginPrompt}>
                  New Institutional Applicant?{" "}
                  <Link to="/auth/signup" className={styles.loginLink}>
                    Create Applicant Account (University / College) →
                  </Link>
                </p>
              </div>

              <div className="flex flex-col items-center justify-center pt-3 text-xs text-center border-t border-slate-100 mt-2 space-y-1">
                <p className="text-slate-600">
                  Are you a State Administrator or Committee Member?
                </p>
                <Link to="/auth/admin/login" className="font-bold text-[#600b0b] hover:underline">
                  Go to State Admin & Committee Portal →
                </Link>
              </div>
            </div>
          </form>

          {/* Quick Dev Login Buttons (development builds only) */}
          {import.meta.env.DEV && APPLICANT_DEV_ACCOUNTS.length > 0 && (
          <div className={devStyles.devLoginSection}>
            <div className={devStyles.devHeader}>
              <span className={devStyles.devBadge}>
                <Sparkles size={13} className={devStyles.devBadgeIcon} />
                Quick Applicant Dev Login
              </span>
              <p className={devStyles.devSubtitle}>
                Institutional applicant roles (University & College)
              </p>
            </div>

            <div className={devStyles.devGrid}>
              {APPLICANT_DEV_ACCOUNTS.map((account) => {
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
          )}
        </section>
      </div>
    </main>
  );
}

export default Signin;

