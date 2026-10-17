import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  fetchUniversities,
  verifyUniversityAishe,
  getDashboardPathForUser,
} from "../../api/auth";
import { useAuth } from "../../context/AuthContext.jsx";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import styles from "../Signup/Signup.module.css";
import {
  Landmark,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Building2,
  MapPin,
  ShieldCheck,
  Eye,
  EyeOff,
  ArrowRight,
  School,
  Sparkles,
  Mail,
} from "lucide-react";

export default function UniversitySignup() {
  const navigate = useNavigate();
  const { registerUniversityAccount } = useAuth();

  // Applicant fields
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    designation: "University Nodal Officer",
    aisheCode: "",
    universityName: "",
    universityId: "",
    password: "",
    confirmPassword: "",
  });

  // Institution verification state
  // verificationStatus: 'idle' | 'verifying' | 'verified' | 'invalid' | 'not_found' | 'error'
  const [verificationStatus, setVerificationStatus] = useState("idle");
  const [verifiedInstitution, setVerifiedInstitution] = useState(null);
  const [verificationError, setVerificationError] = useState("");
  const [universities, setUniversities] = useState([]);
  const [universitiesLoading, setUniversitiesLoading] = useState(true);

  // Load universities registry
  useEffect(() => {
    let active = true;
    const loadUniversities = async () => {
      try {
        const items = await fetchUniversities();
        if (active) {
          setUniversities(items || []);
        }
      } catch (err) {
        // Fallback silently if offline
      } finally {
        if (active) {
          setUniversitiesLoading(false);
        }
      }
    };
    loadUniversities();
    return () => {
      active = false;
    };
  }, []);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionStatus, setSubmissionStatus] = useState({ type: "", message: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;

    // If changing AISHE code, reset previous verification state unless it matches a known university
    if (name === "aisheCode") {
      const upper = value.toUpperCase().trim();
      setFormData((prev) => ({ ...prev, aisheCode: upper }));

      const matched = universities.find(
        (u) => u.aishe_code && u.aishe_code.toUpperCase() === upper
      );
      if (matched) {
        setVerificationStatus("verified");
        setVerifiedInstitution(matched);
        setVerificationError("");
        setFormData((prev) => ({
          ...prev,
          aisheCode: upper,
          universityName: matched.name,
          universityId: String(matched.id),
        }));
      } else {
        if (verificationStatus !== "idle") {
          setVerificationStatus("idle");
          setVerifiedInstitution(null);
          setVerificationError("");
        }
      }
      return;
    }

    // If changing University Name, check for matching university in registry
    if (name === "universityName") {
      setFormData((prev) => ({ ...prev, universityName: value }));

      const matched = universities.find(
        (u) => u.name.toLowerCase() === value.trim().toLowerCase()
      );
      if (matched) {
        setVerificationStatus("verified");
        setVerifiedInstitution(matched);
        setVerificationError("");
        setFormData((prev) => ({
          ...prev,
          universityName: matched.name,
          universityId: String(matched.id),
          aisheCode: matched.aishe_code || "",
        }));
      } else {
        if (verificationStatus !== "idle") {
          setVerificationStatus("idle");
          setVerifiedInstitution(null);
          setVerificationError("");
        }
      }
      return;
    }

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleVerifyAishe = async (e) => {
    if (e) e.preventDefault();
    const code = formData.aisheCode.trim();
    const name = formData.universityName.trim();

    if (!code && !name) {
      setVerificationStatus("invalid");
      setVerificationError("Please enter an AISHE code or University Name to verify.");
      return;
    }

    // Basic format heuristic check
    if (code && code.startsWith("C-")) {
      setVerificationStatus("invalid");
      setVerificationError(
        "The entered code appears to be a College AISHE code. Please use College Registration or enter a University AISHE code (e.g., U-0123)."
      );
      return;
    }

    setVerificationStatus("verifying");
    setVerificationError("");
    setVerifiedInstitution(null);

    try {
      const localMatch = universities.find(
        (u) =>
          (code && u.aishe_code && u.aishe_code.toUpperCase() === code.toUpperCase()) ||
          (name && u.name.toLowerCase() === name.toLowerCase())
      );

      const res = await verifyUniversityAishe(code, {
        name,
        universityId: localMatch?.id || formData.universityId,
      });
      if (res.verified && res.institution) {
        setVerifiedInstitution(res.institution);
        setVerificationStatus("verified");
        setFormData((prev) => ({
          ...prev,
          aisheCode: res.institution.aishe_code || prev.aisheCode,
          universityName: res.institution.name,
          universityId: String(res.institution.id),
        }));
      } else {
        setVerificationStatus("not_found");
        setVerificationError(
          res.detail || `No active University found matching '${code || name}'.`
        );
      }
    } catch (err) {
      const msg = err.message || "Failed to verify institution.";
      if (msg.toLowerCase().includes("not found") || msg.toLowerCase().includes("no active university")) {
        setVerificationStatus("not_found");
        setVerificationError(msg);
      } else if (msg.toLowerCase().includes("invalid") || msg.toLowerCase().includes("college")) {
        setVerificationStatus("invalid");
        setVerificationError(msg);
      } else {
        setVerificationStatus("error");
        setVerificationError(msg);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmissionStatus({ type: "", message: "" });

    // Enforce verified institution gate
    if (verificationStatus !== "verified" || !verifiedInstitution) {
      setSubmissionStatus({
        type: "error",
        message: "You must select or verify your University before proceeding with registration.",
      });
      return;
    }

    // Client-side password validation
    if (formData.password !== formData.confirmPassword) {
      setSubmissionStatus({
        type: "error",
        message: "Passwords do not match. Please verify your entry.",
      });
      return;
    }

    if (formData.password.length < 8) {
      setSubmissionStatus({
        type: "error",
        message: "Password must be at least 8 characters in length.",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        fullName: formData.fullName.trim(),
        email: formData.email.trim().toLowerCase(),
        aisheCode: verifiedInstitution.aishe_code || "",
        universityName: verifiedInstitution.name,
        universityId: verifiedInstitution.id,
        designation: formData.designation.trim() || "University Nodal Officer",
        institutionType: "UNIVERSITY",
        role: "nodal_officer",
        password: formData.password,
        confirmPassword: formData.confirmPassword,
      };

      const response = await registerUniversityAccount(payload);
      setSubmissionStatus({
        type: "success",
        message: response.message || "Account created successfully. A verification link has been sent to your email.",
      });

      // Navigate to Email Verification page
      setTimeout(() => {
        navigate(`/auth/verify-email?email=${encodeURIComponent(formData.email.trim().toLowerCase())}`);
      }, 500);
    } catch (err) {
      setSubmissionStatus({
        type: "error",
        message: err.message || "Could not complete University registration. Please check the details.",
      });
      setIsSubmitting(false);
    }
  };

  return (
    <main className={styles.pageShell}>
      <div className={styles.pageGlow} aria-hidden="true" />
      <div className={`${styles.pageContainer} ${styles.centerFormWrapper}`}>
        <section className={styles.formPanel} aria-labelledby="university-signup-title">
          {/* Header */}
          <div className={styles.formHeader}>
            <div className={styles.logoWrapper}>
              <img src={hshecLogo} alt="HSHEC Council Logo" className={styles.logoImage} />
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className={styles.formBadge}>
                <Landmark className="w-3 h-3 inline-block mr-1" />
                UNIVERSITY APPLICANT REGISTRATION
              </span>
            </div>
            <h2 id="university-signup-title" className={styles.formTitle}>
              University Nodal Officer Registration
            </h2>
            <p className={styles.formIntro}>
              Register the authorized institutional nodal account for Haryana State Higher Education Council NEP Excellence Awards 2026.
            </p>
          </div>

          {/* Submission status banner */}
          {submissionStatus.message && (
            <div
              className={`${styles.statusMessage} ${
                submissionStatus.type === "success" ? styles.statusSuccess : styles.statusError
              }`}
              role="alert"
            >
              {submissionStatus.message}
            </div>
          )}

          <form onSubmit={handleSubmit} className={styles.formGrid}>
            {/* Applicant Full Name */}
            <div className={styles.formGroup}>
              <label htmlFor="fullName">Applicant Full Name *</label>
              <input
                type="text"
                id="fullName"
                name="fullName"
                value={formData.fullName}
                onChange={handleChange}
                required
                placeholder="e.g. Dr. Ramesh Kumar"
                autoComplete="name"
              />
            </div>

            {/* Official Designation */}
            <div className={styles.formGroup}>
              <label htmlFor="designation">Official Designation *</label>
              <input
                type="text"
                id="designation"
                name="designation"
                value={formData.designation}
                onChange={handleChange}
                required
                placeholder="e.g. University Nodal Officer"
              />
            </div>

            {/* Official Email */}
            <div className={styles.formGroup}>
              <div className="flex items-center justify-between mb-1">
                <label htmlFor="email" className="m-0 flex items-center gap-1.5 font-semibold text-slate-800 text-xs">
                  <Mail size={13} className="text-[#600b0b]" />
                  Official Email Address *
                </label>
                <span className="text-[11px] font-bold text-amber-900 bg-amber-100/90 px-2.5 py-0.5 rounded-full flex items-center gap-1 border border-amber-200">
                  <ShieldCheck size={12} className="text-amber-700" />
                  Email Verification Required
                </span>
              </div>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                placeholder="nodal.officer@university.ac.in"
                autoComplete="email"
              />
              <div className="mt-2 p-3 bg-amber-50/80 border border-amber-200/70 rounded-xl text-xs text-amber-950 space-y-1.5">
                <div className="flex items-center gap-1.5 font-bold text-amber-900">
                  <Mail size={14} className="text-[#600b0b]" />
                  <span>Email Verification Option &amp; Protocol</span>
                </div>
                <p className="text-amber-900/90 leading-relaxed text-[11px]">
                  To protect institutional security, an email verification link is automatically sent to <strong>{formData.email.trim() || "your official email"}</strong> upon clicking Register. You must click the link to verify before signing in.
                </p>
                <div className="pt-1 flex items-center justify-between border-t border-amber-200/60 mt-1">
                  <span className="text-[11px] text-amber-800">Already registered or need a new link?</span>
                  <Link
                    to={`/auth/verify-email${formData.email.trim() ? `?email=${encodeURIComponent(formData.email.trim())}` : ""}`}
                    className="text-[11px] font-bold text-[#600b0b] hover:underline"
                  >
                    Open Email Verification / Resend Link →
                  </Link>
                </div>
              </div>
            </div>

            {/* Fixed Institution Type */}
            <div className={styles.formGroup}>
              <label htmlFor="institutionType">Institution Type</label>
              <div className="flex items-center gap-2 p-2.5 bg-amber-50/70 border border-amber-200/80 rounded-xl text-amber-900 font-semibold text-sm">
                <Landmark className="w-4 h-4 text-amber-700" />
                <span>UNIVERSITY (Fixed for this flow)</span>
                <span className="ml-auto text-xs font-normal text-amber-700 bg-amber-100/80 px-2 py-0.5 rounded-full">
                  U1–U20 Awards
                </span>
              </div>
            </div>

            {/* University Name field with autocomplete / registry datalist */}
            <div className={`${styles.formGroup} ${styles.fullWidth}`}>
              <div className="flex items-center justify-between mb-0.5">
                <label htmlFor="universityName" className="m-0 flex items-center gap-1.5">
                  <Building2 size={13} className="text-[#600b0b]" />
                  University Name *
                </label>
                {verificationStatus === "verified" && verifiedInstitution && (
                  <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                    <CheckCircle2 size={12} /> {verifiedInstitution.aishe_code ? "Verified from AISHE" : "Verified by Name"}
                  </span>
                )}
              </div>
              <div className="relative">
                <input
                  type="text"
                  id="universityName"
                  name="universityName"
                  list="registered-universities-list-uni"
                  value={formData.universityName}
                  onChange={handleChange}
                  required={!formData.aisheCode}
                  placeholder="Type or select University Name (e.g. Ashoka University, Kurukshetra University)"
                  className="w-full min-h-[50px] px-4 rounded-xl border border-slate-300 bg-white text-slate-900 font-medium focus:border-[#600b0b] focus:ring-1 focus:ring-[#600b0b] transition-all"
                  disabled={verificationStatus === "verifying" || isSubmitting}
                  autoComplete="off"
                />
                <datalist id="registered-universities-list-uni">
                  {universities.map((uni) => (
                    <option key={uni.id} value={uni.name}>
                      {uni.aishe_code ? `AISHE: ${uni.aishe_code}` : "No AISHE Code Registered"}
                    </option>
                  ))}
                </datalist>
              </div>
              <span className="text-[11px] text-slate-500 mt-1 block">
                If your university does not have an AISHE code, select or write your University Name here to register.
              </span>
            </div>

            {/* AISHE Code & Verification Section */}
            <div className={`${styles.formGroup} ${styles.fullWidth}`}>
              <div className="flex items-center justify-between mb-0.5">
                <label htmlFor="aisheCode">
                  University AISHE Code
                  <span className="text-xs font-normal text-slate-500 ml-1.5">
                    (Optional if registering by University Name)
                  </span>
                </label>
                {!formData.aisheCode && verifiedInstitution && (
                  <span className="text-[11px] text-amber-800 bg-amber-50 px-2 py-0.5 rounded-md font-medium border border-amber-200">
                    No AISHE Code Required
                  </span>
                )}
              </div>
              <div className="flex gap-2.5">
                <input
                  type="text"
                  id="aisheCode"
                  name="aisheCode"
                  value={formData.aisheCode}
                  onChange={handleChange}
                  placeholder="Enter AISHE Code (e.g. U-0123)"
                  autoComplete="off"
                  className="flex-1"
                  disabled={verificationStatus === "verifying" || isSubmitting}
                />
                <button
                  type="button"
                  onClick={handleVerifyAishe}
                  disabled={
                    (!formData.aisheCode.trim() && !formData.universityName.trim()) ||
                    verificationStatus === "verifying" ||
                    isSubmitting
                  }
                  className="px-5 py-2.5 bg-[#600b0b] hover:bg-[#7a0f0f] active:bg-[#4a0808] disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl transition-all shadow-sm flex items-center gap-1.5"
                  id="verify-aishe-btn"
                >
                  {verificationStatus === "verifying" ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Verifying...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      <span>Verify Institution</span>
                    </>
                  )}
                </button>
              </div>

              {/* Verification Feedback Cards */}
              {verificationStatus === "verified" && verifiedInstitution && (
                <div
                  className="mt-3 p-4 bg-emerald-50/90 border border-emerald-300/80 rounded-2xl flex flex-col gap-2 transition-all shadow-xs"
                  id="institution-verified-panel"
                >
                  <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                    <span>Institution Verified Successfully</span>
                  </div>
                  <div className="pl-7 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-700">
                    <div>
                      <span className="font-semibold text-slate-900 block text-sm">
                        {verifiedInstitution.name}
                      </span>
                      <span className="text-slate-500">
                        AISHE: {verifiedInstitution.aishe_code || "Not Assigned (Registered by Name)"} · {verifiedInstitution.university_type}
                      </span>
                    </div>
                    {verifiedInstitution.address && (
                      <div className="flex items-start gap-1 text-slate-500">
                        <MapPin className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-slate-400" />
                        <span>{verifiedInstitution.address}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {verificationStatus === "invalid" && (
                <div
                  className="mt-2.5 p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start gap-2"
                  id="institution-invalid-panel"
                >
                  <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold block mb-0.5">Invalid AISHE Code</span>
                    <span>{verificationError}</span>
                  </div>
                </div>
              )}

              {verificationStatus === "not_found" && (
                <div
                  className="mt-2.5 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2"
                  id="institution-notfound-panel"
                >
                  <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold block mb-0.5">Institution Not Found</span>
                    <span>{verificationError}</span>
                  </div>
                </div>
              )}

              {verificationStatus === "error" && (
                <div
                  className="mt-2.5 p-3.5 bg-slate-100 border border-slate-300 rounded-xl text-xs text-slate-700 flex items-start gap-2"
                  id="institution-error-panel"
                >
                  <AlertCircle className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold block mb-0.5">Verification Service Error</span>
                    <span>{verificationError}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Password */}
            <div className={styles.formGroup}>
              <label htmlFor="password">Password *</label>
              <div className={styles.inputWithIcon}>
                <input
                  type={showPassword ? "text" : "password"}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  placeholder="Min. 8 characters"
                  autoComplete="new-password"
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

            {/* Confirm Password */}
            <div className={styles.formGroup}>
              <label htmlFor="confirmPassword">Confirm Password *</label>
              <div className={styles.inputWithIcon}>
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  id="confirmPassword"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                  placeholder="Re-enter password"
                  autoComplete="new-password"
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

            {/* Action buttons */}
            <div className={`${styles.formActions} ${styles.fullWidth}`}>
              <button
                type="submit"
                className={styles.submitBtn}
                disabled={isSubmitting || verificationStatus !== "verified"}
                id="university-register-submit-btn"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Creating Account...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    Register &amp; Send Email Verification Link
                    <ArrowRight className="w-4 h-4" />
                  </span>
                )}
              </button>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-2 pt-2 text-xs text-slate-500">
                <p className={styles.loginPrompt}>
                  Already registered?{" "}
                  <Link to="/auth/login" className={styles.loginLink}>
                    Sign in here
                  </Link>
                </p>

                <p className={styles.loginPrompt}>
                  College Principal?{" "}
                  <Link to="/auth/signup" className={styles.loginLink}>
                    College Registration →
                  </Link>
                </p>
              </div>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}
