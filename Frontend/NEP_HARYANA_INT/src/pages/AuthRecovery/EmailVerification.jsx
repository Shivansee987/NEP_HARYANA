import { useEffect, useState, useCallback, useRef } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  verifyEmailToken,
  confirmEmailVerification,
  resendEmailVerification,
} from "../../api/auth";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Mail,
  Clock,
  ArrowRight,
  Loader2,
  RefreshCw,
  Building2,
  LogIn,
} from "lucide-react";

export default function EmailVerification() {
  const navigate = useNavigate();
  const params = useParams();
  const [searchParams] = useSearchParams();

  // Support token from path param (/auth/verify-email/:token) or query param (?token=...)
  const token = params.token || searchParams.get("token") || "";
  const initialEmail = searchParams.get("email") || "";

  // States: "verifying" | "verified_pending_approval" | "already_verified" | "expired" | "invalid" | "sent"
  const [viewState, setViewState] = useState(token ? "verifying" : "sent");
  const [maskedEmail, setMaskedEmail] = useState("");
  const [resendEmail, setResendEmail] = useState(initialEmail);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendLoading, setResendLoading] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', message: string }

  // Prevent duplicate execution during React Strict Mode mounts or fast re-renders
  const verificationStartedRef = useRef(false);

  // Cooldown countdown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Execute verification when a token is present
  const executeVerification = useCallback(async (rawToken) => {
    setViewState("verifying");
    setFeedback(null);
    try {
      // 1. Inspect token status
      const inspectRes = await verifyEmailToken(rawToken);
      if (inspectRes?.email) {
        setMaskedEmail(inspectRes.email);
      }

      // If token inspection already confirms the account is verified
      if (inspectRes?.already_verified || inspectRes?.account_already_verified) {
        setViewState("already_verified");
        setFeedback({
          type: "success",
          message: "Your email address has already been verified.",
        });
        return;
      }

      // 2. Confirm verification
      const confirmRes = await confirmEmailVerification(rawToken);
      if (confirmRes?.already_verified) {
        setViewState("already_verified");
        setFeedback({
          type: "success",
          message: confirmRes.message || "Your email address has already been verified.",
        });
      } else {
        setViewState("verified_pending_approval");
        setFeedback({
          type: "success",
          message: confirmRes.message || "Email address successfully verified.",
        });
      }
    } catch (err) {
      console.error("Email verification error:", err);
      const code = err.code || err.reason || err.data?.code || err.data?.reason || "";
      const msg = err.message || err.data?.detail || "Email verification failed.";
      const isAlreadyVerified = Boolean(
        err.account_already_verified ||
        err.already_verified ||
        err.data?.account_already_verified ||
        err.data?.already_verified
      );

      if (err.email || err.data?.email) {
        setMaskedEmail(err.email || err.data?.email);
      }

      if (isAlreadyVerified) {
        setViewState("already_verified");
        setFeedback({
          type: "success",
          message: "Your email address has already been verified.",
        });
      } else if (code === "EXPIRED_TOKEN" || msg.toLowerCase().includes("expired")) {
        setViewState("expired");
        setFeedback({
          type: "error",
          message: "This email verification link has expired. Links are valid for 24 hours.",
        });
      } else if (code === "REVOKED_TOKEN" || msg.toLowerCase().includes("superseded")) {
        setViewState("invalid");
        setFeedback({
          type: "error",
          message: "This verification link has been superseded by a newer link. Please check your inbox.",
        });
      } else {
        setViewState("invalid");
        setFeedback({
          type: "error",
          message: msg || "The verification link is invalid, malformed, or has been revoked.",
        });
      }
    }
  }, []);

  useEffect(() => {
    if (!token || verificationStartedRef.current) return;
    verificationStartedRef.current = true;
    executeVerification(token);
  }, [token, executeVerification]);

  const handleResend = async (e) => {
    if (e) e.preventDefault();
    if (!resendEmail.trim()) {
      setFeedback({ type: "error", message: "Please enter your registered email address." });
      return;
    }
    if (resendCooldown > 0) return;

    setResendLoading(true);
    setFeedback(null);
    try {
      const res = await resendEmailVerification(resendEmail.trim());
      setResendCooldown(res.cooldown_seconds || 60);
      setFeedback({
        type: "success",
        message: res.message || "If an unverified account exists for that email, a verification link has been sent.",
      });
      setViewState("sent");
    } catch (err) {
      console.error("Resend verification error:", err);
      const isCooldown = err.code === "COOLDOWN_ACTIVE";
      const retryAfter = err.retry_after_seconds || 60;
      if (isCooldown) {
        setResendCooldown(retryAfter);
      }
      setFeedback({
        type: "error",
        message: err.message || "Failed to resend verification email. Please try again shortly.",
      });
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#faf6f2] flex items-center justify-center p-4 sm:p-6 selection:bg-[#600b0b] selection:text-white">
      <div className="bg-white max-w-lg w-full rounded-2xl border border-[#ebdcd0] shadow-sm p-6 sm:p-8 space-y-6">
        {/* Header with HSHEC Seal */}
        <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
          <img
            src={hshecLogo}
            alt="HSHEC Emblem"
            className="w-12 h-12 rounded-xl object-cover border border-slate-200 shadow-2xs"
          />
          <div>
            <span className="text-[10px] font-black uppercase tracking-wider text-[#600b0b] block">
              Haryana State Higher Education Council
            </span>
            <h1 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
              NEP Haryana Excellence Awards 2026
            </h1>
          </div>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div
            role="alert"
            className={`p-3.5 rounded-xl text-xs flex gap-2.5 items-start ${
              feedback.type === "success"
                ? "bg-emerald-50 border border-emerald-200 text-emerald-900"
                : "bg-rose-50 border border-rose-200 text-rose-900"
            }`}
          >
            {feedback.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            )}
            <p className="leading-relaxed font-medium">{feedback.message}</p>
          </div>
        )}

        {/* STATE 1: VERIFYING */}
        {viewState === "verifying" && (
          <div className="text-center py-8 space-y-4">
            <Loader2 className="w-10 h-10 text-[#600b0b] animate-spin mx-auto" />
            <div className="space-y-1">
              <h2 className="text-base font-bold text-slate-900">Verifying Your Email Address</h2>
              <p className="text-xs text-slate-500 leading-relaxed max-w-sm mx-auto">
                Validating your cryptographic single-use verification token with the HSHEC security service...
              </p>
            </div>
          </div>
        )}

        {/* STATE 2: VERIFIED PENDING APPROVAL */}
        {viewState === "verified_pending_approval" && (
          <div className="space-y-5">
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-3">
              <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
              <div className="space-y-1 text-xs">
                <h2 className="font-bold text-emerald-950 text-sm">Email Address Verified</h2>
                <p className="text-emerald-800 leading-relaxed">
                  Your identity has been confirmed. You may now sign in using your registered credentials.
                </p>
              </div>
            </div>

            {/* Crucial Governance Notice: Admin approval is still pending */}
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2 text-xs text-amber-900">
              <div className="flex items-center gap-2 font-bold text-amber-950">
                <Building2 className="w-4 h-4 text-amber-700" />
                <span>Institutional Access Pending Approval</span>
              </div>
              <p className="text-amber-800 leading-relaxed">
                In compliance with State Higher Education governance rules, public registrations are created with institutional access in a <strong>PENDING</strong> state. An authorized Higher Education Department administrator must approve your institution claim before assessment editing permissions are unlocked.
              </p>
            </div>

            <div className="pt-2">
              <Link
                to="/auth/login"
                className="w-full inline-flex items-center justify-center gap-2 bg-[#600b0b] hover:bg-[#780d0d] text-white font-bold text-xs py-3 px-4 rounded-xl shadow-xs transition-colors"
              >
                <LogIn className="w-4 h-4" />
                <span>Proceed to Sign In</span>
              </Link>
            </div>
          </div>
        )}

        {/* STATE: ALREADY VERIFIED */}
        {viewState === "already_verified" && (
          <div className="space-y-5">
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-3">
              <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
              <div className="space-y-1 text-xs">
                <h2 className="font-bold text-emerald-950 text-sm">Email Already Verified</h2>
                <p className="text-emerald-800 leading-relaxed">
                  Your registered email address {maskedEmail ? `(${maskedEmail}) ` : ""}has already been verified. You can sign in to the portal with your credentials.
                </p>
              </div>
            </div>

            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2 text-xs text-amber-900">
              <div className="flex items-center gap-2 font-bold text-amber-950">
                <Building2 className="w-4 h-4 text-amber-700" />
                <span>Institutional Review Status</span>
              </div>
              <p className="text-amber-800 leading-relaxed">
                Your institution claim remains under review by Higher Education Department administrators. Once your claim is approved, assessment workspace permissions will be fully unlocked.
              </p>
            </div>

            <div className="pt-2">
              <Link
                to="/auth/login"
                className="w-full inline-flex items-center justify-center gap-2 bg-[#600b0b] hover:bg-[#780d0d] text-white font-bold text-xs py-3 px-4 rounded-xl shadow-xs transition-colors"
              >
                <LogIn className="w-4 h-4" />
                <span>Proceed to Sign In</span>
              </Link>
            </div>
          </div>
        )}

        {/* STATE 3: LINK EXPIRED */}
        {viewState === "expired" && (
          <div className="space-y-5">
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3 text-xs">
              <Clock className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h2 className="font-bold text-amber-950 text-sm">Verification Link Expired</h2>
                <p className="text-amber-800 leading-relaxed">
                  For security, verification links expire 24 hours after issuance. Please enter your email address below to receive a new link.
                </p>
              </div>
            </div>

            <form onSubmit={handleResend} className="space-y-3">
              <label htmlFor="expired-resend-email" className="block text-xs font-semibold text-slate-700">
                Registered Email Address
              </label>
              <div className="flex gap-2">
                <input
                  id="expired-resend-email"
                  type="email"
                  required
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="e.g., principal@college.edu.in"
                  className="flex-1 px-3.5 py-2.5 border border-slate-300 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#600b0b]"
                />
                <button
                  type="submit"
                  disabled={resendLoading || resendCooldown > 0}
                  className="px-4 py-2.5 bg-[#600b0b] hover:bg-[#780d0d] disabled:opacity-50 text-white rounded-xl text-xs font-bold shrink-0 transition-colors"
                >
                  {resendLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : resendCooldown > 0 ? (
                    `Wait ${resendCooldown}s`
                  ) : (
                    "Resend Link"
                  )}
                </button>
              </div>
            </form>

            <div className="pt-2 text-center">
              <Link to="/auth/login" className="text-xs font-semibold text-slate-600 hover:text-[#600b0b]">
                Back to Sign In
              </Link>
            </div>
          </div>
        )}

        {/* STATE 4: LINK INVALID OR ALREADY USED */}
        {viewState === "invalid" && (
          <div className="space-y-5">
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-3 text-xs">
              <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h2 className="font-bold text-rose-950 text-sm">Invalid or Used Link</h2>
                <p className="text-rose-800 leading-relaxed">
                  This link has either already been used, was replaced by a newer link, or is malformed.
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-xs font-bold text-slate-800">What would you like to do?</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <Link
                  to="/auth/login"
                  className="inline-flex items-center justify-center gap-1.5 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-800 text-xs font-bold transition-colors"
                >
                  <LogIn className="w-4 h-4 text-[#600b0b]" />
                  <span>Sign In</span>
                </Link>
                <button
                  type="button"
                  onClick={() => setViewState("sent")}
                  className="inline-flex items-center justify-center gap-1.5 p-3 rounded-xl bg-[#600b0b] hover:bg-[#780d0d] text-white text-xs font-bold transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Request New Link</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* STATE 5: VERIFICATION EMAIL SENT / INSTRUCTIONS */}
        {viewState === "sent" && (
          <div className="space-y-5">
            <div className="text-center py-3 space-y-2">
              <div className="w-12 h-12 bg-amber-50 text-[#600b0b] rounded-2xl flex items-center justify-center mx-auto border border-amber-200/60 shadow-2xs">
                <Mail className="w-6 h-6" />
              </div>
              <h2 className="text-base font-bold text-slate-900">Verification Link Dispatched</h2>
              <p className="text-xs text-slate-600 leading-relaxed max-w-sm mx-auto">
                We sent a secure single-use verification link to your registered email address. Please click the link to verify your identity.
              </p>
            </div>

            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs text-slate-700">
              <div className="flex items-center gap-2 font-bold text-slate-900">
                <ShieldCheck className="w-4 h-4 text-[#600b0b]" />
                <span>Next Steps in Onboarding</span>
              </div>
              <ol className="list-decimal list-inside space-y-1 text-slate-600 pl-1 leading-relaxed">
                <li>Check your inbox (and spam/junk folder) for the verification email.</li>
                <li>Click the verification link within 24 hours.</li>
                <li>After email verification, your institution claim remains under review by State Higher Education administrators.</li>
              </ol>
            </div>

            {/* Resend Action with Cooldown and Anti-Enumeration */}
            <div className="pt-2 border-t border-slate-100 space-y-2">
              <span className="text-[11px] font-semibold text-slate-500 block">
                Didn&apos;t receive the email?
              </span>
              <form onSubmit={handleResend} className="flex gap-2">
                <input
                  type="email"
                  required
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="Enter your registered email"
                  className="flex-1 px-3 py-2 border border-slate-300 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#600b0b]"
                />
                <button
                  type="submit"
                  disabled={resendLoading || resendCooldown > 0}
                  className="px-3.5 py-2 bg-[#600b0b] hover:bg-[#780d0d] disabled:opacity-50 text-white rounded-xl text-xs font-bold shrink-0 transition-colors"
                >
                  {resendLoading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : resendCooldown > 0 ? (
                    `Wait ${resendCooldown}s`
                  ) : (
                    "Resend"
                  )}
                </button>
              </form>
            </div>

            <div className="pt-2 text-center border-t border-slate-100">
              <Link to="/auth/login" className="inline-flex items-center gap-1.5 text-xs font-bold text-[#600b0b] hover:underline">
                <span>Already verified? Sign in here</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
