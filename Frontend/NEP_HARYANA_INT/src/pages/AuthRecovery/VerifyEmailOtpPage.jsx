import { useState, useEffect, useCallback, useRef } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  verifyEmailOtp,
  resendEmailOtp,
  requestEmailOtp,
} from "../../api/auth";
import OtpInput from "../../components/common/OtpInput";
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
  Edit3,
} from "lucide-react";

export default function VerifyEmailOtpPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const urlEmail = searchParams.get("email") || "";

  // Component state
  const [email, setEmail] = useState(urlEmail.trim().toLowerCase());
  const [inputEmail, setInputEmail] = useState(urlEmail.trim().toLowerCase());
  const [isEditingEmail, setIsEditingEmail] = useState(!urlEmail);
  const [otp, setOtp] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  // Expiration countdown (default 10 minutes = 600s)
  const [expiresInSeconds, setExpiresInSeconds] = useState(600);

  // Feedback states: null | { type: 'success' | 'error' | 'info', message: string, code?: string }
  const [feedback, setFeedback] = useState(null);
  const [isVerified, setIsVerified] = useState(false);
  const [isAlreadyVerified, setIsAlreadyVerified] = useState(false);

  // Cooldown countdown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Expiration countdown timer
  useEffect(() => {
    if (expiresInSeconds <= 0 || isVerified || isAlreadyVerified) return;
    const timer = setInterval(() => {
      setExpiresInSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [expiresInSeconds, isVerified, isAlreadyVerified]);

  // Synchronize URL search params when email changes
  const updateEmail = (newEmail) => {
    const clean = newEmail.trim().toLowerCase();
    setEmail(clean);
    setInputEmail(clean);
    setIsEditingEmail(false);
    setSearchParams(clean ? { email: clean } : {});
  };

  const maskEmail = (raw) => {
    if (!raw || !raw.includes("@")) return raw || "";
    const [user, domain] = raw.split("@");
    if (user.length <= 2) return `${user[0]}***@${domain}`;
    return `${user[0]}***${user[user.length - 1]}@${domain}`;
  };

  const formatCountdown = (totalSeconds) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  // Submit OTP Verification
  const handleVerify = async (e) => {
    if (e) e.preventDefault();
    if (!email) {
      setFeedback({ type: "error", message: "Please provide a valid registered email address." });
      setIsEditingEmail(true);
      return;
    }
    if (otp.length !== 6) {
      setFeedback({ type: "error", message: "Please enter all 6 numeric digits of your verification code." });
      return;
    }

    setIsSubmitting(true);
    setFeedback(null);

    try {
      const res = await verifyEmailOtp(email, otp);
      if (res.already_verified || res.account_already_verified) {
        setIsAlreadyVerified(true);
        setFeedback({
          type: "success",
          message: "Your email address is already verified. You can proceed to log in.",
        });
      } else {
        setIsVerified(true);
        setFeedback({
          type: "success",
          message: "Email address verified successfully! Redirecting to login...",
        });
      }

      // Redirect to login page after short delay
      setTimeout(() => {
        navigate("/auth/login", {
          state: {
            verifiedEmail: email,
            message: "Email verified successfully! Please log in with your credentials.",
          },
        });
      }, 2000);
    } catch (err) {
      console.error("OTP verification error:", err);
      const code = err.code || err.reason || err.data?.code || "";
      const msg = err.message || err.data?.detail || "Verification failed.";

      if (code === "ALREADY_VERIFIED" || err.account_already_verified || err.already_verified) {
        setIsAlreadyVerified(true);
        setFeedback({
          type: "success",
          message: "Your email address is already verified. You can sign in.",
        });
      } else if (code === "OTP_ATTEMPTS_EXCEEDED") {
        setFeedback({
          type: "error",
          message: "Maximum verification attempts exceeded. This code is now invalid. Please click 'Resend Code'.",
          code,
        });
        setOtp("");
      } else if (code === "OTP_EXPIRED" || expiresInSeconds === 0) {
        setFeedback({
          type: "error",
          message: "This verification code has expired. Please request a new code.",
          code: "OTP_EXPIRED",
        });
      } else {
        setFeedback({
          type: "error",
          message: msg,
          code,
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Resend OTP
  const handleResend = async () => {
    if (!email) {
      setFeedback({ type: "error", message: "Please enter your email address to request a verification code." });
      setIsEditingEmail(true);
      return;
    }
    if (resendCooldown > 0 || isResending) return;

    setIsResending(true);
    setFeedback(null);

    try {
      const res = await resendEmailOtp(email);
      if (res.already_verified || res.account_already_verified) {
        setIsAlreadyVerified(true);
        setFeedback({
          type: "success",
          message: res.message || "This email address is already verified. Please sign in to your account.",
        });
        return;
      }
      setResendCooldown(res.cooldown_seconds || 60);
      setExpiresInSeconds((res.expires_in_minutes || 10) * 60);
      setOtp("");
      setFeedback({
        type: "success",
        message: res.message || `A new 6-digit verification code has been sent to ${maskEmail(email)}.`,
      });
    } catch (err) {
      console.error("Resend OTP error:", err);
      const isAlreadyVerified = Boolean(
        err.account_already_verified ||
        err.already_verified ||
        err.data?.account_already_verified ||
        err.data?.already_verified
      );

      if (isAlreadyVerified) {
        setIsAlreadyVerified(true);
        setFeedback({
          type: "success",
          message: "This email address is already verified. Please sign in to your account.",
        });
        return;
      }

      const retryAfter = err.data?.retry_after_seconds || 60;
      if (err.code === "OTP_COOLDOWN" || err.code === "COOLDOWN_ACTIVE") {
        setResendCooldown(retryAfter);
        setFeedback({
          type: "info",
          message: `Please wait ${retryAfter} seconds before requesting another code.`,
        });
      } else if (err.code === "OTP_RATE_LIMITED" || err.code === "RATE_LIMIT_EXCEEDED") {
        setFeedback({
          type: "error",
          message: "Too many verification requests. Please check your spam folder or try again later.",
        });
      } else {
        setFeedback({
          type: "error",
          message: err.message || err.data?.detail || "Failed to resend code. Please try again.",
        });
      }
    } finally {
      setIsResending(false);
    }
  };

  // Handle direct request when user inputs email
  const handleRequestCode = async (e) => {
    e.preventDefault();
    if (!inputEmail.trim()) {
      setFeedback({ type: "error", message: "Please enter your registered email address." });
      return;
    }

    setIsSubmitting(true);
    setFeedback(null);

    try {
      const res = await requestEmailOtp(inputEmail.trim().toLowerCase());
      updateEmail(inputEmail);
      setResendCooldown(res.cooldown_seconds || 60);
      setExpiresInSeconds((res.expires_in_minutes || 10) * 60);
      setOtp("");

      if (res.already_verified || res.account_already_verified) {
        setIsAlreadyVerified(true);
        setFeedback({
          type: "success",
          message: res.message || "This email address is already verified. Please sign in to your account.",
        });
      } else {
        setFeedback({
          type: "success",
          message: res.message || "Verification code sent successfully. Please check your inbox.",
        });
      }
    } catch (err) {
      const isAlreadyVerified = Boolean(
        err.account_already_verified ||
        err.already_verified ||
        err.data?.account_already_verified ||
        err.data?.already_verified
      );

      if (isAlreadyVerified) {
        setIsAlreadyVerified(true);
        setFeedback({
          type: "success",
          message: "This email address is already verified. Please sign in to your account.",
        });
      } else {
        setFeedback({
          type: "error",
          message: err.message || "Unable to request verification code. Please try again.",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Header Branding */}
        <div className="text-center">
          <Link to="/" className="inline-block" aria-label="HSHEC Home">
            <img
              src={hshecLogo}
              alt="HSHEC Haryana"
              className="mx-auto h-16 w-16 rounded-full shadow-md object-contain border-2 border-slate-100"
            />
          </Link>
          <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[#600b0b]/10 text-[#600b0b] tracking-wide uppercase">
            <ShieldCheck className="w-3.5 h-3.5" />
            Two-Step Email Verification
          </div>
          <h1 className="mt-2 text-2xl font-extrabold text-slate-900 tracking-tight sm:text-3xl">
            Verify Your Email
          </h1>
          <p className="mt-1 text-sm text-slate-600 max-w-sm mx-auto">
            Haryana State Higher Education Council NEP Excellence Awards 2026
          </p>
        </div>

        {/* Main Card */}
        <div className="mt-6 bg-white py-8 px-6 sm:px-10 shadow-xl shadow-slate-200/50 rounded-2xl border border-slate-200/80">
          {/* Feedback Banner */}
          {feedback && (
            <div
              role="alert"
              className={`mb-6 p-4 rounded-xl text-sm flex items-start gap-3 transition-all duration-200 ${
                feedback.type === "success"
                  ? "bg-emerald-50 text-emerald-900 border border-emerald-200"
                  : feedback.type === "info"
                  ? "bg-amber-50 text-amber-900 border border-amber-200"
                  : "bg-red-50 text-red-900 border border-red-200"
              }`}
            >
              {feedback.type === "success" ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              ) : feedback.type === "info" ? (
                <Clock className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              )}
              <div className="flex-1 font-medium leading-relaxed">{feedback.message}</div>
            </div>
          )}

          {/* Already Verified State */}
          {isAlreadyVerified ? (
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-9 h-9" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Email Already Verified</h3>
              <p className="text-sm text-slate-600 mt-2">
                This email address is already verified. Please sign in to your account.
              </p>
              <div className="mt-6">
                <Link
                  to="/auth/login"
                  className="w-full inline-flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white bg-[#600b0b] hover:bg-[#7a0e0e] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#600b0b] transition-all"
                >
                  <LogIn className="w-4 h-4" />
                  Sign In
                </Link>
              </div>
            </div>
          ) : isVerified ? (
            /* Successful Verification State */
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4 animate-bounce">
                <CheckCircle2 className="w-9 h-9" />
              </div>
              <h3 className="text-lg font-bold text-emerald-900">Verification Successful!</h3>
              <p className="text-sm text-slate-600 mt-2">
                Your email has been confirmed. Redirecting you to the login page...
              </p>
              <div className="mt-6">
                <Link
                  to="/auth/login"
                  className="w-full inline-flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white bg-[#600b0b] hover:bg-[#7a0e0e] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#600b0b]"
                >
                  Continue to Login <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          ) : isEditingEmail || !email ? (
            /* Direct Email Request State */
            <form onSubmit={handleRequestCode} className="space-y-4">
              <div>
                <label htmlFor="directEmail" className="block text-sm font-semibold text-slate-700 mb-1">
                  Enter Your Registered Email Address
                </label>
                <div className="relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail className="w-5 h-5" />
                  </div>
                  <input
                    type="email"
                    id="directEmail"
                    required
                    value={inputEmail}
                    onChange={(e) => setInputEmail(e.target.value)}
                    placeholder="applicant@college.edu.in"
                    className="block w-full pl-11 pr-4 py-3 text-sm rounded-xl border border-slate-300 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20 focus:border-[#600b0b] transition-all"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1.5">
                  We will send a 6-digit verification code to this email address.
                </p>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !inputEmail.trim()}
                className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl shadow-sm text-sm font-bold text-white bg-[#600b0b] hover:bg-[#7a0e0e] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#600b0b] disabled:opacity-60 disabled:cursor-not-allowed transition-all"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Sending Code...
                  </>
                ) : (
                  <>
                    Send Verification Code <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          ) : (
            /* OTP Verification Form */
            <form onSubmit={handleVerify} className="space-y-6">
              {/* Recipient Notice */}
              <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-200/70 flex items-center justify-between">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-full bg-[#600b0b]/10 text-[#600b0b] flex items-center justify-center shrink-0">
                    <Mail className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500 font-medium">Code sent to</p>
                    <p className="text-sm font-bold text-slate-800 truncate" title={email}>
                      {maskEmail(email)}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsEditingEmail(true)}
                  className="text-xs text-[#600b0b] font-semibold hover:underline flex items-center gap-1 shrink-0 ml-2"
                >
                  <Edit3 className="w-3 h-3" /> Change
                </button>
              </div>

              {/* Segmented 6-digit OTP Input */}
              <div>
                <label className="block text-center text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                  Enter 6-Digit Verification Code
                </label>
                <OtpInput
                  value={otp}
                  onChange={(val) => {
                    setOtp(val);
                    if (feedback?.type === "error") setFeedback(null);
                  }}
                  onComplete={(val) => {
                    // Automatically trigger verification when all 6 digits are entered
                    if (val.length === 6 && !isSubmitting) {
                      setOtp(val);
                    }
                  }}
                  disabled={isSubmitting}
                  hasError={feedback?.type === "error"}
                />
              </div>

              {/* Expiry Countdown */}
              <div className="flex items-center justify-center gap-1.5 text-xs text-slate-500">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                {expiresInSeconds > 0 ? (
                  <span>
                    Code expires in:{" "}
                    <span className="font-bold text-slate-700 tabular-nums">
                      {formatCountdown(expiresInSeconds)}
                    </span>
                  </span>
                ) : (
                  <span className="font-bold text-red-600">
                    Code expired. Please request a new code.
                  </span>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting || otp.length !== 6 || expiresInSeconds === 0}
                className="w-full flex justify-center items-center gap-2 py-3.5 px-4 rounded-xl shadow-md text-sm font-bold text-white bg-[#600b0b] hover:bg-[#7a0e0e] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#600b0b] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Verifying Code...
                  </>
                ) : (
                  <>
                    Verify Email & Continue <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              {/* Resend Controls */}
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                <span>Didn't receive the email?</span>
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={resendCooldown > 0 || isResending}
                  className="font-bold text-[#600b0b] hover:text-[#7a0e0e] hover:underline disabled:text-slate-400 disabled:no-underline flex items-center gap-1 cursor-pointer disabled:cursor-not-allowed"
                >
                  <RefreshCw className={`w-3 h-3 ${isResending ? "animate-spin" : ""}`} />
                  {resendCooldown > 0
                    ? `Resend in ${resendCooldown}s`
                    : isResending
                    ? "Sending..."
                    : "Resend Code"}
                </button>
              </div>
            </form>
          )}

          {/* Governance Notice */}
          <div className="mt-6 pt-4 border-t border-slate-100">
            <div className="bg-amber-50/70 border border-amber-200/70 rounded-xl p-3 flex gap-2.5">
              <Building2 className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-900/90 leading-relaxed">
                <strong>Governance Rule:</strong> Email verification authenticates your contact identity. Access to institution nomination worksheets remains subject to State Higher Education Department approval.
              </p>
            </div>
          </div>
        </div>

        {/* Footer Navigation */}
        <div className="mt-6 text-center text-xs text-slate-500">
          Already verified?{" "}
          <Link to="/auth/login" className="font-bold text-[#600b0b] hover:underline">
            Go to Applicant Login
          </Link>
          <span className="mx-2">·</span>
          <Link to="/contact" className="hover:underline">
            Need Help?
          </Link>
        </div>
      </div>
    </div>
  );
}
