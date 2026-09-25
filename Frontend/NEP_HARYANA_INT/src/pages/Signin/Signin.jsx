import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getDashboardPathForUser } from "../../api/auth";
import { useAuth } from "../../context/AuthContext.jsx";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import styles from "../Signup/Signup.module.css";
import devStyles from "./Signin.module.css";
import {
  GraduationCap,
  Landmark,
  Building2,
  ShieldCheck,
  Award,
  Users,
  ArrowRight,
  Sparkles,
  Loader2,
} from "lucide-react";

const DEV_ACCOUNTS = [
  {
    key: "principal",
    role: "College Principal",
    badge: "College",
    description: "C1–C22 Institutional Forms & Nominations",
    email: "principal@dev.local",
    password: "DevPrincipal@123",
    icon: GraduationCap,
    themeClass: devStyles.themeAmber,
  },
  {
    key: "nodal",
    role: "University Nodal Officer",
    badge: "University",
    description: "U1–U20 Forms & College Oversight",
    email: "nodal@dev.local",
    password: "DevNodal@123",
    icon: Landmark,
    themeClass: devStyles.themeIndigo,
  },
  {
    key: "univadmin",
    role: "University Admin",
    badge: "Uni Admin",
    description: "University Console & Settings",
    email: "univadmin@dev.local",
    password: "DevUnivAdmin@123",
    icon: Building2,
    themeClass: devStyles.themeBlue,
  },
  {
    key: "admin",
    role: "State Admin",
    badge: "HSHEC State",
    description: "Council Control Plane & Reports",
    email: "admin@dev.local",
    password: "DevAdmin@123",
    icon: ShieldCheck,
    themeClass: devStyles.themeMaroon,
  },
  {
    key: "chair",
    role: "Committee Chair",
    badge: "Chairperson",
    description: "Screening Committee Certification",
    email: "chair@dev.local",
    password: "DevChair@123",
    icon: Award,
    themeClass: devStyles.themeEmerald,
  },
  {
    key: "committee",
    role: "Committee Member",
    badge: "Reviewer",
    description: "Evaluation, Verification & Scoring",
    email: "committee@dev.local",
    password: "DevCommittee@123",
    icon: Users,
    themeClass: devStyles.themePurple,
  },
];

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
      setStatus({
        type: "success",
        message: response.message || "Signed in successfully.",
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
            <span className={styles.formBadge}>Sign in</span>
            <h2 id="signin-title" className={styles.formTitle}>
              Access your portal dashboard using your registered credentials.
            </h2>
          </div>

          {status.message && (
            <div
              className={`${styles.statusMessage} ${status.type === "success" ? styles.statusSuccess : styles.statusError}`}
            >
              {status.message}
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

              <p className={styles.loginPrompt}>
                Don't have an account?{" "}
                <Link to="/auth/signup" className={styles.loginLink}>
                  Register here
                </Link>
              </p>
            </div>
          </form>

          {/* Quick Dev Login Buttons */}
          <div className={devStyles.devLoginSection}>
            <div className={devStyles.devHeader}>
              <span className={devStyles.devBadge}>
                <Sparkles size={13} className={devStyles.devBadgeIcon} />
                Quick Dev Login
              </span>
              <p className={devStyles.devSubtitle}>
                Click any role to sign in & enter instantly
              </p>
            </div>

            <div className={devStyles.devGrid}>
              {DEV_ACCOUNTS.map((account) => {
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

export default Signin;

