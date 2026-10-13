import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { verifyAccountActivation, confirmAccountActivation } from "../../api/auth";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import styles from "./AuthRecovery.module.css";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Loader2,
  Building2,
  UserCheck,
} from "lucide-react";

export default function AccountActivation() {
  const navigate = useNavigate();
  const params = useParams();
  const [searchParams] = useSearchParams();

  // Support token from either path param (/auth/activate/:token) or query param (?token=...)
  const token = params.token || searchParams.get("token") || "";

  const [verifying, setVerifying] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [tokenError, setTokenError] = useState("");
  const [userData, setUserData] = useState(null);

  const [formData, setFormData] = useState({
    password: "",
    confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState({ type: "", message: "" });
  const [activatedSuccess, setActivatedSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setVerifying(false);
      setTokenValid(false);
      setTokenError("No activation token was provided. Please use the link sent to your official email.");
      return;
    }

    let isMounted = true;
    async function verify() {
      try {
        const response = await verifyAccountActivation(token);
        if (isMounted) {
          if (response.valid) {
            setTokenValid(true);
            setUserData(response);
          } else {
            setTokenValid(false);
            setTokenError(response.detail || "This activation link is invalid or has expired.");
          }
        }
      } catch (err) {
        if (isMounted) {
          setTokenValid(false);
          setTokenError(err.message || "Failed to verify activation link.");
        }
      } finally {
        if (isMounted) {
          setVerifying(false);
        }
      }
    }

    verify();
    return () => {
      isMounted = false;
    };
  }, [token]);

  const handleChange = (e) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.password.length < 8) {
      setSubmitStatus({
        type: "error",
        message: "Password must be at least 8 characters long.",
      });
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setSubmitStatus({
        type: "error",
        message: "Passwords do not match.",
      });
      return;
    }

    setSubmitting(true);
    setSubmitStatus({ type: "", message: "" });

    try {
      const response = await confirmAccountActivation({
        token,
        password: formData.password,
        confirmPassword: formData.confirmPassword,
      });

      setActivatedSuccess(true);
      setSubmitStatus({
        type: "success",
        message: response.message || "Account activated successfully!",
      });
    } catch (err) {
      setSubmitStatus({
        type: "error",
        message: err.message || "Could not complete account activation.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className={styles.pageShell}>
      <div className={styles.pageGlow} aria-hidden="true" />
      <div className={`${styles.pageContainer} ${styles.centerFormWrapper}`}>
        <section className={styles.recoveryCard} aria-labelledby="activation-title">
          <div className={styles.logoWrapper}>
            <img src={hshecLogo} alt="HSHEC Logo" className={styles.logoImage} />
          </div>

          <div className="flex justify-center mb-2">
            <span className={styles.badge}>Official Account Activation</span>
          </div>

          <h1 id="activation-title" className={styles.title} style={{ textAlign: "center" }}>
            {activatedSuccess
              ? "Account Activated Successfully"
              : "Set Up Your Security Credentials"}
          </h1>

          <p className={styles.intro} style={{ textAlign: "center" }}>
            {activatedSuccess
              ? "Your password has been securely established. You may now sign in to your authorized workspace."
              : "Complete your administrative onboarding by verifying your identity and choosing a secure password."}
          </p>

          {/* Verification Loading State */}
          {verifying && (
            <div className="flex flex-col items-center justify-center py-12 space-y-3">
              <Loader2 className="w-8 h-8 text-[#600b0b] animate-spin" />
              <p className="text-sm font-semibold text-slate-600">
                Verifying single-use security token...
              </p>
            </div>
          )}

          {/* Invalid / Expired Token State */}
          {!verifying && !tokenValid && !activatedSuccess && (
            <div className="mt-6 p-6 rounded-2xl bg-rose-50 border border-rose-200 text-center space-y-4">
              <div className="w-12 h-12 mx-auto rounded-full bg-rose-100 flex items-center justify-center text-rose-700">
                <AlertTriangle size={24} />
              </div>
              <div>
                <h3 className="font-bold text-rose-950 text-base">Invalid or Expired Activation Link</h3>
                <p className="text-xs text-rose-800 mt-1 max-w-md mx-auto">{tokenError}</p>
              </div>
              <div className="text-xs text-slate-500 pt-2 border-t border-rose-100">
                Activation links are time-limited and single-use. If your invitation has expired or was revoked, please request a fresh invitation from your Head Administrator.
              </div>
              <div className="pt-2">
                <Link
                  to="/auth/admin/login"
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-xl transition shadow-xs"
                >
                  Return to Official Sign In <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          )}

          {/* Activation Success State */}
          {activatedSuccess && (
            <div className="mt-6 p-6 rounded-2xl bg-emerald-50 border border-emerald-200 text-center space-y-4">
              <div className="w-12 h-12 mx-auto rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700">
                <CheckCircle2 size={26} />
              </div>
              <div>
                <h3 className="font-bold text-emerald-950 text-base">Welcome to the Administration Console</h3>
                <p className="text-xs text-emerald-800 mt-1">
                  Your official account credentials have been established and verified.
                </p>
              </div>
              <div className="pt-3">
                <Link
                  to="/auth/admin/login"
                  className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-bold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-xl transition shadow-md"
                >
                  Sign In to Administration Console <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          )}

          {/* Active Token Form State */}
          {!verifying && tokenValid && !activatedSuccess && (
            <div className="mt-4 space-y-5">
              {/* Profile Card */}
              {userData && (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500 flex items-center gap-1">
                      <UserCheck size={14} className="text-teal-700" />
                      Provisioned Officer
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#600b0b] text-white">
                      {userData.role_label || userData.role}
                    </span>
                  </div>
                  <div className="text-sm font-bold text-slate-900">{userData.full_name}</div>
                  <div className="text-xs text-slate-600 font-mono">{userData.email}</div>
                </div>
              )}

              {submitStatus.message && (
                <div
                  className={`${styles.statusMessage} ${
                    submitStatus.type === "success" ? styles.statusSuccess : styles.statusError
                  }`}
                >
                  {submitStatus.message}
                </div>
              )}

              <form onSubmit={handleSubmit} className={styles.formGrid}>
                <div className={styles.formGroup}>
                  <label htmlFor="password">Create Security Password</label>
                  <div className={styles.inputWithIcon}>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      value={formData.password}
                      onChange={handleChange}
                      placeholder="Min 8 characters (letters, numbers, symbols)"
                      autoComplete="new-password"
                      minLength={8}
                      required
                    />
                    <button
                      type="button"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className={styles.iconBtn}
                      onClick={() => setShowPassword((s) => !s)}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="confirmPassword">Confirm Security Password</label>
                  <div className={styles.inputWithIcon}>
                    <input
                      id="confirmPassword"
                      name="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      value={formData.confirmPassword}
                      onChange={handleChange}
                      placeholder="Re-enter password to confirm"
                      autoComplete="new-password"
                      minLength={8}
                      required
                    />
                    <button
                      type="button"
                      aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                      className={styles.iconBtn}
                      onClick={() => setShowConfirmPassword((s) => !s)}
                    >
                      {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-900 leading-relaxed">
                  🔒 Establishing your password will immediately activate your account and invalidate this one-time activation link.
                </div>

                <div className={styles.formActions}>
                  <button
                    type="submit"
                    className={styles.submitBtn}
                    disabled={submitting}
                  >
                    {submitting ? "Activating Account..." : "Set Password & Activate Account"}
                  </button>

                  <div className={styles.helperLinks}>
                    <Link to="/auth/admin/login" className={styles.backLink}>
                      Already activated? Sign In →
                    </Link>
                  </div>
                </div>
              </form>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
