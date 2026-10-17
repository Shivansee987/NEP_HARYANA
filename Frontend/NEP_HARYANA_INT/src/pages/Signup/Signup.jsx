import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  fetchColleges,
  fetchUniversities,
  verifyUniversityAishe,
  verifyCollegeAishe,
  getDashboardPathForUser,
} from "../../api/auth";
import { useAuth } from "../../context/AuthContext.jsx";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import styles from "./Signup.module.css";
import {
  Landmark,
  School,
  Building2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ShieldCheck,
  Eye,
  EyeOff,
  ArrowRight,
  MapPin,
  Sparkles,
  Phone,
  Mail,
  KeyRound,
  RotateCw,
} from "lucide-react";

export default function Signup({ initialType = null }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { register, registerUniversityAccount } = useAuth();

  // Determine initial institution type: prop -> query param -> null (no silent default)
  const queryType = searchParams.get("type");
  const normalizedQueryType =
    queryType && queryType.toUpperCase() === "UNIVERSITY"
      ? "UNIVERSITY"
      : queryType && queryType.toUpperCase() === "COLLEGE"
        ? "COLLEGE"
        : null;

  const [institutionType, setInstitutionType] = useState(
    initialType || normalizedQueryType || null
  );

  // Common applicant credentials (safely preserved across type toggles)
  const [commonFields, setCommonFields] = useState({
    fullName: "",
    email: "",
    phoneNumber: "",
    password: "",
    confirmPassword: "",
  });


  // University-specific state
  const [uniFields, setUniFields] = useState({
    designation: "University Nodal Officer",
    aisheCode: "",
    universityName: "",
    universityId: "",
  });
  const [uniVerificationStatus, setUniVerificationStatus] = useState("idle"); // idle | verifying | verified | invalid | not_found | error
  const [uniVerifiedInstitution, setUniVerifiedInstitution] = useState(null);
  const [uniVerificationError, setUniVerificationError] = useState("");
  const [universities, setUniversities] = useState([]);
  const [universitiesLoading, setUniversitiesLoading] = useState(true);
  const [universitiesError, setUniversitiesError] = useState("");

  // Load available universities for University workflow
  useEffect(() => {
    let active = true;
    const loadUniversities = async () => {
      try {
        const items = await fetchUniversities();
        if (active) {
          setUniversities(items || []);
        }
      } catch (err) {
        if (active) {
          setUniversitiesError(err.message || "Could not load universities.");
        }
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

  // College-specific state (with first-class AISHE code verification option)
  const [collegeFields, setCollegeFields] = useState({
    collegeId: "",
    aisheCode: "",
  });
  const [collegeVerificationStatus, setCollegeVerificationStatus] = useState("idle"); // idle | verifying | verified | invalid | not_found | error
  const [collegeVerifiedInstitution, setCollegeVerifiedInstitution] = useState(null);
  const [collegeVerificationError, setCollegeVerificationError] = useState("");
  const [colleges, setColleges] = useState([]);
  const [collegesLoading, setCollegesLoading] = useState(true);
  const [collegesError, setCollegesError] = useState("");

  // Shared UX and validation state
  const [fieldErrors, setFieldErrors] = useState({});
  const [status, setStatus] = useState({ type: "", message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Load available colleges for the College workflow
  useEffect(() => {
    let active = true;
    const loadColleges = async () => {
      try {
        const items = await fetchColleges();
        if (active) {
          setColleges(items);
        }
      } catch (err) {
        if (active) {
          setCollegesError(err.message || "Could not load affiliated colleges.");
        }
      } finally {
        if (active) {
          setCollegesLoading(false);
        }
      }
    };

    loadColleges();
    return () => {
      active = false;
    };
  }, []);

  const selectedCollege = useMemo(() => {
    return (
      colleges.find((c) => String(c.id) === String(collegeFields.collegeId)) ||
      collegeVerifiedInstitution ||
      null
    );
  }, [colleges, collegeFields.collegeId, collegeVerifiedInstitution]);

  // Handle switching between University and College
  const handleTypeChange = (newType) => {
    if (newType === institutionType) return;
    setInstitutionType(newType);
    setStatus({ type: "", message: "" });
    setFieldErrors({});

    // Reset verification when switching away
    if (newType === "COLLEGE") {
      setUniVerificationStatus("idle");
      setUniVerifiedInstitution(null);
      setUniVerificationError("");
    } else if (newType === "UNIVERSITY") {
      setCollegeVerificationStatus("idle");
      setCollegeVerifiedInstitution(null);
      setCollegeVerificationError("");
    }
  };

  const handleCommonFieldChange = (e) => {
    const { name, value } = e.target;
    setCommonFields((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const handlePhoneNumberChange = (e) => {
    const raw = e.target.value;
    const cleaned = raw.replace(/[^\d]/g, "").slice(0, 10);
    setCommonFields((prev) => ({ ...prev, phoneNumber: cleaned }));
    if (fieldErrors.phoneNumber) {
      setFieldErrors((prev) => ({ ...prev, phoneNumber: "" }));
    }
  };

  const renderPhoneNumberSection = () => (
    <div className={`${styles.formGroup} ${styles.fullWidth}`}>
      <label htmlFor="phoneNumber" className="flex items-center gap-1.5 mb-1 font-semibold text-slate-800 text-xs">
        <Phone size={13} className="text-[#600b0b]" />
        Applicant Mobile Number (Optional)
      </label>
      <div className={styles.phoneInputWrapper}>
        <span className={styles.countryCodePrefix}>+91</span>
        <input
          type="tel"
          id="phoneNumber"
          name="phoneNumber"
          value={commonFields.phoneNumber}
          onChange={handlePhoneNumberChange}
          placeholder="10-digit mobile number"
          maxLength={10}
          className="flex-1"
          disabled={isSubmitting}
          autoComplete="tel"
        />
      </div>
      {fieldErrors.phoneNumber && (
        <span className={styles.fieldError}>
          <AlertCircle size={12} /> {fieldErrors.phoneNumber}
        </span>
      )}
    </div>
  );

  const handleUniFieldChange = (e) => {
    const { name, value } = e.target;
    if (name === "aisheCode") {
      const upper = value.toUpperCase().trim();
      setUniFields((prev) => ({ ...prev, aisheCode: upper }));

      // Instant match if typed code matches known university in universities list
      const matched = universities.find(
        (u) => u.aishe_code && u.aishe_code.toUpperCase() === upper
      );
      if (matched) {
        setUniVerificationStatus("verified");
        setUniVerifiedInstitution(matched);
        setUniVerificationError("");
        setUniFields((prev) => ({
          ...prev,
          aisheCode: upper,
          universityName: matched.name,
          universityId: String(matched.id),
        }));
      } else {
        if (uniVerificationStatus !== "idle") {
          setUniVerificationStatus("idle");
          setUniVerifiedInstitution(null);
          setUniVerificationError("");
        }
      }
      if (fieldErrors.aisheCode) {
        setFieldErrors((prev) => ({ ...prev, aisheCode: "" }));
      }
      return;
    }

    if (name === "universityName") {
      setUniFields((prev) => ({ ...prev, universityName: value }));

      // Instant match if typed/selected name matches known university in universities list
      const matched = universities.find(
        (u) => u.name.toLowerCase() === value.trim().toLowerCase()
      );
      if (matched) {
        setUniVerificationStatus("verified");
        setUniVerifiedInstitution(matched);
        setUniVerificationError("");
        setUniFields((prev) => ({
          ...prev,
          universityName: matched.name,
          universityId: String(matched.id),
          aisheCode: matched.aishe_code || "",
        }));
      } else {
        if (uniVerificationStatus !== "idle") {
          setUniVerificationStatus("idle");
          setUniVerifiedInstitution(null);
          setUniVerificationError("");
        }
      }
      if (fieldErrors.universityName) {
        setFieldErrors((prev) => ({ ...prev, universityName: "" }));
      }
      return;
    }

    setUniFields((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const handleCollegeFieldChange = (e) => {
    const { name, value } = e.target;
    if (name === "aisheCode") {
      const upper = value.toUpperCase().trim();
      setCollegeFields((prev) => ({ ...prev, aisheCode: upper }));

      // Instant autofill if typed code matches known college
      const matched = colleges.find(
        (c) => c.aishe_code && c.aishe_code.toUpperCase() === upper
      );
      if (matched) {
        setCollegeVerificationStatus("verified");
        setCollegeVerifiedInstitution(matched);
        setCollegeVerificationError("");
        setCollegeFields({
          collegeId: String(matched.id),
          aisheCode: upper,
        });
      } else {
        if (collegeVerificationStatus !== "idle") {
          setCollegeVerificationStatus("idle");
          setCollegeVerifiedInstitution(null);
          setCollegeVerificationError("");
        }
      }

      if (fieldErrors.aisheCode) {
        setFieldErrors((prev) => ({ ...prev, aisheCode: "" }));
      }
      return;
    }
    setCollegeFields((prev) => ({ ...prev, [name]: value }));
  };

  // =========================================================================
  // AISHE Lookup Action for University Flow
  // =========================================================================
  const handleVerifyUniAishe = async (e) => {
    if (e) e.preventDefault();
    const code = uniFields.aisheCode.trim();
    const name = uniFields.universityName.trim();

    if (!code && !name) {
      setUniVerificationStatus("invalid");
      setUniVerificationError("Please enter an AISHE code or University Name to verify.");
      return;
    }

    if (code && code.startsWith("C-")) {
      setUniVerificationStatus("invalid");
      setUniVerificationError(
        "The entered code appears to be a College AISHE code. Please switch to College Registration or enter a University AISHE code (e.g., U-0123)."
      );
      return;
    }

    setUniVerificationStatus("verifying");
    setUniVerificationError("");
    setUniVerifiedInstitution(null);

    try {
      const localMatch = universities.find(
        (u) =>
          (code && u.aishe_code && u.aishe_code.toUpperCase() === code.toUpperCase()) ||
          (name && u.name.toLowerCase() === name.toLowerCase())
      );

      const res = await verifyUniversityAishe(code, {
        name,
        universityId: localMatch?.id || uniFields.universityId,
      });
      if (res.verified && res.institution) {
        setUniVerifiedInstitution(res.institution);
        setUniVerificationStatus("verified");
        setUniFields((prev) => ({
          ...prev,
          aisheCode: res.institution.aishe_code || prev.aisheCode,
          universityName: res.institution.name,
          universityId: String(res.institution.id),
        }));
      } else {
        setUniVerificationStatus("not_found");
        setUniVerificationError(
          res.detail || `No active University found matching '${code || name}'.`
        );
      }
    } catch (err) {
      const msg = err.message || "Failed to verify institution.";
      if (
        msg.toLowerCase().includes("not found") ||
        msg.toLowerCase().includes("no active university")
      ) {
        setUniVerificationStatus("not_found");
        setUniVerificationError(msg);
      } else if (
        msg.toLowerCase().includes("invalid") ||
        msg.toLowerCase().includes("college")
      ) {
        setUniVerificationStatus("invalid");
        setUniVerificationError(msg);
      } else {
        setUniVerificationStatus("error");
        setUniVerificationError(msg);
      }
    }
  };

  // =========================================================================
  // AISHE Lookup Action for College Flow
  // =========================================================================
  const handleVerifyCollegeAishe = async (e) => {
    if (e) e.preventDefault();
    const code = collegeFields.aisheCode.trim();

    if (!code) {
      setCollegeVerificationStatus("invalid");
      setCollegeVerificationError("Please enter an AISHE code to verify.");
      return;
    }

    if (code.startsWith("U-")) {
      setCollegeVerificationStatus("invalid");
      setCollegeVerificationError(
        "The entered code appears to be a University AISHE code. Please switch to University Registration or enter a valid College AISHE code (e.g., C-10001)."
      );
      return;
    }

    setCollegeVerificationStatus("verifying");
    setCollegeVerificationError("");
    setCollegeVerifiedInstitution(null);

    try {
      const res = await verifyCollegeAishe(code);
      if (res.verified && res.institution) {
        setCollegeVerifiedInstitution(res.institution);
        setCollegeVerificationStatus("verified");
        setCollegeFields((prev) => ({
          ...prev,
          collegeId: String(res.institution.id),
          aisheCode: res.institution.aishe_code,
        }));
      } else {
        setCollegeVerificationStatus("not_found");
        setCollegeVerificationError(
          res.detail || `No active College found matching AISHE code '${code}'.`
        );
      }
    } catch (err) {
      const msg = err.message || "Failed to verify institution.";
      if (
        msg.toLowerCase().includes("not found") ||
        msg.toLowerCase().includes("no active college")
      ) {
        setCollegeVerificationStatus("not_found");
        setCollegeVerificationError(msg);
      } else if (
        msg.toLowerCase().includes("invalid") ||
        msg.toLowerCase().includes("university")
      ) {
        setCollegeVerificationStatus("invalid");
        setCollegeVerificationError(msg);
      } else {
        setCollegeVerificationStatus("error");
        setCollegeVerificationError(msg);
      }
    }
  };

  // =========================================================================
  // University Form Submission
  // =========================================================================
  const handleUniversitySubmit = async (e) => {
    e.preventDefault();
    setStatus({ type: "", message: "" });
    setFieldErrors({});

    const errors = {};
    if (!commonFields.fullName.trim()) {
      errors.fullName = "Applicant full name is required.";
    }
    if (!commonFields.email.trim()) {
      errors.email = "Official email address is required.";
    }
    if (commonFields.phoneNumber.trim() && commonFields.phoneNumber.trim().length !== 10) {
      errors.phoneNumber = "Please enter a valid 10-digit mobile number.";
    }
    if (uniVerificationStatus !== "verified" || !uniVerifiedInstitution) {
      errors.aisheCode = "You must select or verify your University before proceeding.";
    }
    if (!commonFields.password) {
      errors.password = "Password is required.";
    } else if (commonFields.password.length < 8) {
      errors.password = "Password must be at least 8 characters.";
    }
    if (commonFields.password !== commonFields.confirmPassword) {
      errors.confirmPassword = "Passwords do not match.";
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setStatus({
        type: "error",
        message: "Please correct the highlighted errors before submitting.",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        fullName: commonFields.fullName.trim(),
        email: commonFields.email.trim().toLowerCase(),
        phoneNumber: commonFields.phoneNumber.trim(),
        aisheCode: uniVerifiedInstitution.aishe_code || "",
        universityName: uniVerifiedInstitution.name,
        universityId: uniVerifiedInstitution.id,
        designation: uniFields.designation.trim() || "University Nodal Officer",
        institutionType: "UNIVERSITY",
        role: "nodal_officer",
        password: commonFields.password,
        confirmPassword: commonFields.confirmPassword,
      };

      const response = await registerUniversityAccount(payload);
      setStatus({
        type: "success",
        message:
          response.message ||
          "University account created successfully. A verification link has been sent to your email.",
      });

      setTimeout(() => {
        navigate(`/auth/verify-email?email=${encodeURIComponent(commonFields.email.trim().toLowerCase())}`);
      }, 500);
    } catch (err) {
      setStatus({
        type: "error",
        message:
          err.message ||
          "Could not complete University registration. Please check the details.",
      });
      setIsSubmitting(false);
    }
  };

  // =========================================================================
  // College Form Submission
  // =========================================================================
  const handleCollegeSubmit = async (e) => {
    e.preventDefault();
    setStatus({ type: "", message: "" });
    setFieldErrors({});

    const errors = {};
    if (!commonFields.fullName.trim()) {
      errors.fullName = "Applicant full name is required.";
    }
    if (!commonFields.email.trim()) {
      errors.email = "Official email address is required.";
    }
    if (commonFields.phoneNumber.trim() && commonFields.phoneNumber.trim().length !== 10) {
      errors.phoneNumber = "Please enter a valid 10-digit mobile number.";
    }
    if (collegeVerificationStatus !== "verified" || (!collegeVerifiedInstitution && !selectedCollege)) {
      errors.aisheCode = "You must enter and verify your College's AISHE code before proceeding.";
    }
    if (!commonFields.password) {
      errors.password = "Password is required.";
    } else if (commonFields.password.length < 8) {
      errors.password = "Password must be at least 8 characters.";
    }
    if (commonFields.password !== commonFields.confirmPassword) {
      errors.confirmPassword = "Passwords do not match.";
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setStatus({
        type: "error",
        message: "Please correct the highlighted errors before submitting.",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const targetCollege = collegeVerifiedInstitution || selectedCollege;
      const payload = {
        fullName: commonFields.fullName.trim(),
        email: commonFields.email.trim().toLowerCase(),
        phoneNumber: commonFields.phoneNumber.trim(),
        role: "principal",
        collegeId: Number(collegeFields.collegeId),
        aisheCode: collegeFields.aisheCode,
        password: commonFields.password,
      };

      const response = await register(payload);
      setStatus({
        type: "success",
        message:
          response.message ||
          "College account created successfully. A verification link has been sent to your email.",
      });

      setTimeout(() => {
        navigate(`/auth/verify-email?email=${encodeURIComponent(commonFields.email.trim().toLowerCase())}`);
      }, 500);
    } catch (err) {
      setStatus({
        type: "error",
        message:
          err.message ||
          "Could not complete College registration. Please check the details.",
      });
      setIsSubmitting(false);
    }
  };

  return (
    <main className={styles.pageShell}>
      <div className={styles.pageGlow} aria-hidden="true" />
      <div className={`${styles.pageContainer} ${styles.centerFormWrapper}`}>
        <section
          className={`${styles.formPanel} ${styles.unifiedFormPanel}`}
          aria-labelledby="signup-title"
        >
          {/* Header */}
          <div className={styles.formHeader}>
            <div className={styles.logoWrapper}>
              <img src={hshecLogo} alt="HSHEC Council Logo" className={styles.logoImage} />
            </div>
            <span className={styles.formBadge}>APPLICANT REGISTRATION</span>
            <h1 id="signup-title" className={styles.formTitle}>
              Create Applicant Account
            </h1>
            <p className={styles.formIntro}>
              Choose your institution type below to begin your application for Haryana
              State Higher Education Council NEP Excellence Awards 2026.
            </p>
          </div>

          {/* Status notification banner */}
          {status.message && (
            <div
              className={`${styles.statusMessage} ${
                status.type === "success" ? styles.statusSuccess : styles.statusError
              }`}
              role="alert"
            >
              {status.message}
            </div>
          )}

          {/* Top Institution-Type Selector */}
          <div className={styles.typeSelectorSection}>
            <span id="institution-type-label" className={styles.typeSelectorLabel}>
              Select Institution Type *
            </span>
            <div
              className={styles.typeSelectorGrid}
              role="radiogroup"
              aria-labelledby="institution-type-label"
            >
              {/* University Card */}
              <label
                htmlFor="type-university"
                className={`${styles.typeCard} ${
                  institutionType === "UNIVERSITY" ? styles.typeCardSelected : ""
                }`}
              >
                <input
                  type="radio"
                  id="type-university"
                  name="institutionType"
                  value="UNIVERSITY"
                  checked={institutionType === "UNIVERSITY"}
                  onChange={() => handleTypeChange("UNIVERSITY")}
                  className={styles.typeCardRadio}
                  disabled={isSubmitting}
                />
                <div className={styles.typeIconWrapper}>
                  <Landmark size={22} />
                </div>
                <h2 className={styles.typeTitle}>University</h2>
                <p className={styles.typeSubtitle}>
                  State Public & Recognized Universities in Haryana
                </p>
                <span className={styles.typeBadge}>U1–U20 Awards</span>
              </label>

              {/* College Card */}
              <label
                htmlFor="type-college"
                className={`${styles.typeCard} ${
                  institutionType === "COLLEGE" ? styles.typeCardSelected : ""
                }`}
              >
                <input
                  type="radio"
                  id="type-college"
                  name="institutionType"
                  value="COLLEGE"
                  checked={institutionType === "COLLEGE"}
                  onChange={() => handleTypeChange("COLLEGE")}
                  className={styles.typeCardRadio}
                  disabled={isSubmitting}
                />
                <div className={styles.typeIconWrapper}>
                  <School size={22} />
                </div>
                <h2 className={styles.typeTitle}>College</h2>
                <p className={styles.typeSubtitle}>
                  Government & Affiliated Colleges in Haryana
                </p>
                <span className={styles.typeBadge}>C1–C22 Awards</span>
              </label>
            </div>
          </div>

          {/* Initial State: Neither Type Selected */}
          {!institutionType && (
            <div className={styles.emptyPromptCard} id="institution-prompt-card">
              <div className={styles.emptyPromptIcon}>
                <Sparkles size={24} />
              </div>
              <h3 className={styles.emptyPromptTitle}>Please Select Your Institution Type</h3>
              <p className={styles.emptyPromptDesc}>
                Select whether you are registering for a <strong>University</strong> or a{" "}
                <strong>College</strong> above to load the appropriate institutional verification
                steps and applicant registration form.
              </p>
            </div>
          )}

          {/* =========================================================================
              Conditional Form 1: University Applicant Registration Form
             ========================================================================= */}
          {institutionType === "UNIVERSITY" && (
            <form
              onSubmit={handleUniversitySubmit}
              className={styles.formGrid}
              id="university-registration-form"
            >
              <div className={`${styles.fullWidth} pb-1 border-b border-amber-100 flex items-center justify-between`}>
                <span className="text-xs font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1.5">
                  <Landmark size={14} className="text-amber-700" />
                  University Nodal Officer Registration
                </span>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800">
                  U1–U20 Framework
                </span>
              </div>

              {/* Applicant Full Name */}
              <div className={styles.formGroup}>
                <label htmlFor="fullName">Applicant Full Name *</label>
                <input
                  type="text"
                  id="fullName"
                  name="fullName"
                  value={commonFields.fullName}
                  onChange={handleCommonFieldChange}
                  required
                  placeholder="e.g. Dr. Ramesh Kumar"
                  autoComplete="name"
                  disabled={isSubmitting}
                />
                {fieldErrors.fullName && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.fullName}
                  </span>
                )}
              </div>

              {/* Official Designation */}
              <div className={styles.formGroup}>
                <label htmlFor="designation">Official Designation *</label>
                <input
                  type="text"
                  id="designation"
                  name="designation"
                  value={uniFields.designation}
                  onChange={handleUniFieldChange}
                  required
                  placeholder="e.g. University Nodal Officer"
                  disabled={isSubmitting}
                />
                {fieldErrors.designation && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.designation}
                  </span>
                )}
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
                  value={commonFields.email}
                  onChange={handleCommonFieldChange}
                  required
                  placeholder="nodal.officer@university.ac.in"
                  autoComplete="email"
                  disabled={isSubmitting}
                />
                {fieldErrors.email && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.email}
                  </span>
                )}
                <div className="mt-2 p-3 bg-amber-50/80 border border-amber-200/70 rounded-xl text-xs text-amber-950 space-y-1.5">
                  <div className="flex items-center gap-1.5 font-bold text-amber-900">
                    <Mail size={14} className="text-[#600b0b]" />
                    <span>Email Verification Option &amp; Protocol</span>
                  </div>
                  <p className="text-amber-900/90 leading-relaxed text-[11px]">
                    To ensure secure institutional onboarding, an email verification link is automatically sent to <strong>{commonFields.email.trim() || "your official email"}</strong> upon clicking Register. You must click the link to verify your identity before signing in.
                  </p>
                  <div className="pt-1 flex items-center justify-between border-t border-amber-200/60 mt-1">
                    <span className="text-[11px] text-amber-800">Already have a pending account?</span>
                    <Link
                      to={`/auth/verify-email${commonFields.email.trim() ? `?email=${encodeURIComponent(commonFields.email.trim())}` : ""}`}
                      className="text-[11px] font-bold text-[#600b0b] hover:underline"
                    >
                      Open Email Verification / Resend Link →
                    </Link>
                  </div>
                </div>
              </div>

              {/* Fixed Institution Type */}
              <div className={styles.formGroup}>
                <label>Institution Type</label>
                <div className="flex items-center gap-2 p-2.5 bg-amber-50/70 border border-amber-200/80 rounded-xl text-amber-900 font-semibold text-sm min-h-[50px]">
                  <Landmark className="w-4 h-4 text-amber-700" />
                  <span>UNIVERSITY (Fixed for this flow)</span>
                  <span className="ml-auto text-xs font-normal text-amber-700 bg-amber-100/80 px-2 py-0.5 rounded-full">
                    U1–U20 Awards
                  </span>
                </div>
              </div>

              {/* Applicant Mobile Number */}
              {renderPhoneNumberSection()}

              {/* University Name Selection / Input (Supports Universities without AISHE Code) */}
              <div className={`${styles.formGroup} ${styles.fullWidth}`}>
                <div className="flex items-center justify-between mb-0.5">
                  <label htmlFor="universityName" className="m-0 flex items-center gap-1.5">
                    <Building2 size={13} className="text-[#600b0b]" />
                    University Name *
                  </label>
                  {uniVerificationStatus === "verified" && uniVerifiedInstitution && (
                    <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                      <CheckCircle2 size={12} /> {uniVerifiedInstitution.aishe_code ? "Verified from AISHE" : "Verified by Name"}
                    </span>
                  )}
                </div>
                <div className="relative">
                  <input
                    type="text"
                    id="universityName"
                    name="universityName"
                    list="registered-universities-list"
                    value={uniFields.universityName}
                    onChange={handleUniFieldChange}
                    required={!uniFields.aisheCode}
                    placeholder="Type or select University Name (e.g. Ashoka University, Kurukshetra University)"
                    className="w-full min-h-[50px] px-4 rounded-xl border border-slate-300 bg-white text-slate-900 font-medium focus:border-[#600b0b] focus:ring-1 focus:ring-[#600b0b] transition-all"
                    disabled={uniVerificationStatus === "verifying" || isSubmitting}
                    autoComplete="off"
                  />
                  <datalist id="registered-universities-list">
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
                {fieldErrors.universityName && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.universityName}
                  </span>
                )}
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
                  {!uniFields.aisheCode && uniVerifiedInstitution && (
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
                    value={uniFields.aisheCode}
                    onChange={handleUniFieldChange}
                    placeholder="Enter AISHE Code (e.g. U-0160)"
                    autoComplete="off"
                    className="flex-1"
                    disabled={uniVerificationStatus === "verifying" || isSubmitting}
                  />
                  <button
                    type="button"
                    onClick={handleVerifyUniAishe}
                    disabled={
                      (!uniFields.aisheCode.trim() && !uniFields.universityName.trim()) ||
                      uniVerificationStatus === "verifying" ||
                      isSubmitting
                    }
                    className="px-5 py-2.5 bg-[#600b0b] hover:bg-[#7a0f0f] active:bg-[#4a0808] disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl transition-all shadow-sm flex items-center gap-1.5"
                    id="verify-aishe-btn"
                  >
                    {uniVerificationStatus === "verifying" ? (
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
                {fieldErrors.aisheCode && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.aisheCode}
                  </span>
                )}

                {/* Verification Feedback Panels */}
                {uniVerificationStatus === "verified" && uniVerifiedInstitution && (
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
                          {uniVerifiedInstitution.name}
                        </span>
                        <span className="text-slate-500">
                          AISHE: {uniVerifiedInstitution.aishe_code || "Not Assigned (Registered by Name)"} ·{" "}
                          {uniVerifiedInstitution.university_type}
                        </span>
                      </div>
                      {uniVerifiedInstitution.address && (
                        <div className="flex items-start gap-1 text-slate-500">
                          <MapPin className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-slate-400" />
                          <span>{uniVerifiedInstitution.address}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {uniVerificationStatus === "invalid" && (
                  <div
                    className="mt-2.5 p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start gap-2"
                    id="institution-invalid-panel"
                  >
                    <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold block mb-0.5">Invalid AISHE Code</span>
                      <span>{uniVerificationError}</span>
                    </div>
                  </div>
                )}

                {uniVerificationStatus === "not_found" && (
                  <div
                    className="mt-2.5 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2"
                    id="institution-notfound-panel"
                  >
                    <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold block mb-0.5">Institution Not Found</span>
                      <span>{uniVerificationError}</span>
                    </div>
                  </div>
                )}

                {uniVerificationStatus === "error" && (
                  <div
                    className="mt-2.5 p-3.5 bg-slate-100 border border-slate-300 rounded-xl text-xs text-slate-700 flex items-start gap-2"
                    id="institution-error-panel"
                  >
                    <AlertCircle className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold block mb-0.5">
                        Verification Service Error
                      </span>
                      <span>{uniVerificationError}</span>
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
                    value={commonFields.password}
                    onChange={handleCommonFieldChange}
                    required
                    placeholder="Min. 8 characters"
                    autoComplete="new-password"
                    disabled={isSubmitting}
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
                {fieldErrors.password && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.password}
                  </span>
                )}
              </div>

              {/* Confirm Password */}
              <div className={styles.formGroup}>
                <label htmlFor="confirmPassword">Confirm Password *</label>
                <div className={styles.inputWithIcon}>
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    id="confirmPassword"
                    name="confirmPassword"
                    value={commonFields.confirmPassword}
                    onChange={handleCommonFieldChange}
                    required
                    placeholder="Re-enter password"
                    autoComplete="new-password"
                    disabled={isSubmitting}
                  />
                  <button
                    type="button"
                    aria-label={
                      showConfirmPassword ? "Hide confirm password" : "Show confirm password"
                    }
                    className={styles.iconBtn}
                    onClick={() => setShowConfirmPassword((s) => !s)}
                  >
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {fieldErrors.confirmPassword && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.confirmPassword}
                  </span>
                )}
              </div>

              {/* Action Buttons */}
              <div className={`${styles.formActions} ${styles.fullWidth}`}>
                <button
                  type="submit"
                  className={styles.submitBtn}
                  disabled={isSubmitting || uniVerificationStatus !== "verified"}
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

                <p className={styles.loginPrompt}>
                  Already registered?{" "}
                  <Link to="/auth/login" className={styles.loginLink}>
                    Sign in here
                  </Link>
                </p>
              </div>
            </form>
          )}

          {/* =========================================================================
              Conditional Form 2: College Applicant Registration Form
             ========================================================================= */}
          {institutionType === "COLLEGE" && (
            <form
              onSubmit={handleCollegeSubmit}
              className={styles.formGrid}
              id="college-registration-form"
            >
              <div className={`${styles.fullWidth} pb-1 border-b border-amber-100 flex items-center justify-between`}>
                <span className="text-xs font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1.5">
                  <Building2 size={14} className="text-amber-700" />
                  College Principal Registration
                </span>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800">
                  C1–C22 Framework
                </span>
              </div>

              {/* Applicant Full Name */}
              <div className={styles.formGroup}>
                <label htmlFor="fullName">Applicant Full Name *</label>
                <input
                  type="text"
                  id="fullName"
                  name="fullName"
                  value={commonFields.fullName}
                  onChange={handleCommonFieldChange}
                  required
                  placeholder="e.g. Dr. Sunita Verma"
                  autoComplete="name"
                  disabled={isSubmitting}
                />
                {fieldErrors.fullName && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.fullName}
                  </span>
                )}
              </div>

              {/* Official Designation */}
              <div className={styles.formGroup}>
                <label>Official Role</label>
                <div className="flex items-center gap-2 p-2.5 bg-amber-50/70 border border-amber-200/80 rounded-xl text-amber-900 font-semibold text-sm min-h-[50px]">
                  <School className="w-4 h-4 text-amber-700" />
                  <span>College Principal</span>
                  <span className="ml-auto text-xs font-normal text-amber-700 bg-amber-100/80 px-2 py-0.5 rounded-full">
                    C1–C22 Awards
                  </span>
                </div>
              </div>

              {/* Official Email */}
              <div className={`${styles.formGroup} ${styles.fullWidth}`}>
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
                  value={commonFields.email}
                  onChange={handleCommonFieldChange}
                  required
                  placeholder="principal@college.edu.in"
                  autoComplete="email"
                  disabled={isSubmitting}
                />
                {fieldErrors.email && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.email}
                  </span>
                )}
                <div className="mt-2 p-3 bg-amber-50/80 border border-amber-200/70 rounded-xl text-xs text-amber-950 space-y-1.5">
                  <div className="flex items-center gap-1.5 font-bold text-amber-900">
                    <Mail size={14} className="text-[#600b0b]" />
                    <span>Email Verification Option &amp; Protocol</span>
                  </div>
                  <p className="text-amber-900/90 leading-relaxed text-[11px]">
                    To ensure secure institutional onboarding, an email verification link is automatically sent to <strong>{commonFields.email.trim() || "your official email"}</strong> upon clicking Register. You must click the link to verify your identity before signing in.
                  </p>
                  <div className="pt-1 flex items-center justify-between border-t border-amber-200/60 mt-1">
                    <span className="text-[11px] text-amber-800">Already have a pending account?</span>
                    <Link
                      to={`/auth/verify-email${commonFields.email.trim() ? `?email=${encodeURIComponent(commonFields.email.trim())}` : ""}`}
                      className="text-[11px] font-bold text-[#600b0b] hover:underline"
                    >
                      Open Email Verification / Resend Link →
                    </Link>
                  </div>
                </div>
              </div>

              {/* Applicant Mobile Number */}
              {renderPhoneNumberSection()}

              {/* College AISHE Code & Verification Section */}
              <div className={`${styles.formGroup} ${styles.fullWidth}`}>
                <label htmlFor="aisheCode">College AISHE Code *</label>
                <div className="flex gap-2.5">
                  <input
                    type="text"
                    id="aisheCode"
                    name="aisheCode"
                    value={collegeFields.aisheCode}
                    onChange={handleCollegeFieldChange}
                    required
                    placeholder="Enter College AISHE Code (e.g. C-DEMO-01)"
                    autoComplete="off"
                    className="flex-1"
                    disabled={collegeVerificationStatus === "verifying" || isSubmitting}
                  />
                  <button
                    type="button"
                    onClick={handleVerifyCollegeAishe}
                    disabled={
                      !collegeFields.aisheCode.trim() ||
                      collegeVerificationStatus === "verifying" ||
                      isSubmitting
                    }
                    className="px-5 py-2.5 bg-[#600b0b] hover:bg-[#7a0f0f] active:bg-[#4a0808] disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl transition-all shadow-sm flex items-center gap-1.5"
                    id="verify-college-aishe-btn"
                  >
                    {collegeVerificationStatus === "verifying" ? (
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
                {fieldErrors.aisheCode && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.aisheCode}
                  </span>
                )}

                {/* College Verification Feedback Panels */}
                {collegeVerificationStatus === "verified" && (collegeVerifiedInstitution || selectedCollege) && (
                  <div
                    className="mt-3 p-4 bg-emerald-50/90 border border-emerald-300/80 rounded-2xl flex flex-col gap-2 transition-all shadow-xs"
                    id="college-verified-panel"
                  >
                    <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                      <span>College Verified Successfully</span>
                    </div>
                    <div className="pl-7 text-xs text-slate-700">
                      <span className="font-semibold text-slate-900 block text-sm">
                        {(collegeVerifiedInstitution || selectedCollege)?.name}
                      </span>
                      <span className="text-slate-500">
                        AISHE: {(collegeVerifiedInstitution || selectedCollege)?.aishe_code} · Government & Affiliated College
                      </span>
                    </div>
                  </div>
                )}

                {collegeVerificationStatus === "invalid" && (
                  <div
                    className="mt-2.5 p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start gap-2"
                    id="college-invalid-panel"
                  >
                    <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold block mb-0.5">Invalid AISHE Code</span>
                      <span>{collegeVerificationError}</span>
                    </div>
                  </div>
                )}

                {collegeVerificationStatus === "not_found" && (
                  <div
                    className="mt-2.5 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2"
                    id="college-notfound-panel"
                  >
                    <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold block mb-0.5">College Not Found</span>
                      <span>{collegeVerificationError}</span>
                    </div>
                  </div>
                )}

                {collegeVerificationStatus === "error" && (
                  <div
                    className="mt-2.5 p-3.5 bg-slate-100 border border-slate-300 rounded-xl text-xs text-slate-700 flex items-start gap-2"
                    id="college-error-panel"
                  >
                    <AlertCircle className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold block mb-0.5">Verification Service Error</span>
                      <span>{collegeVerificationError}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Autofilled Institution Name from Verified AISHE Code */}
              <div className={`${styles.formGroup} ${styles.fullWidth}`}>
                <div className="flex items-center justify-between mb-0.5">
                  <label htmlFor="institutionName" className="m-0 flex items-center gap-1.5">
                    <Building2 size={13} className="text-[#600b0b]" />
                    Institution Name *
                  </label>
                  {collegeVerificationStatus === "verified" && (collegeVerifiedInstitution || selectedCollege) && (
                    <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                      <CheckCircle2 size={12} /> Autofilled from AISHE
                    </span>
                  )}
                </div>
                <div className="relative">
                  <input
                    type="text"
                    id="institutionName"
                    name="institutionName"
                    value={(collegeVerifiedInstitution || selectedCollege)?.name || ""}
                    placeholder="Institution name will autofill upon entering/verifying AISHE code"
                    readOnly
                    className="w-full min-h-[50px] px-4 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 font-medium cursor-not-allowed"
                    disabled={isSubmitting}
                  />
                  {collegeVerificationStatus === "verifying" && (
                    <div className="absolute right-3.5 top-1/2 -translate-y-1/2 flex items-center gap-1.5 text-xs text-amber-700">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Fetching name...</span>
                    </div>
                  )}
                </div>
                <input
                  type="hidden"
                  id="collegeId"
                  name="collegeId"
                  value={(collegeVerifiedInstitution || selectedCollege)?.id || ""}
                />
                {fieldErrors.collegeId && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.collegeId}
                  </span>
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
                    value={commonFields.password}
                    onChange={handleCommonFieldChange}
                    required
                    placeholder="Min. 8 characters"
                    autoComplete="new-password"
                    disabled={isSubmitting}
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
                {fieldErrors.password && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.password}
                  </span>
                )}
              </div>

              {/* Confirm Password */}
              <div className={styles.formGroup}>
                <label htmlFor="confirmPassword">Confirm Password *</label>
                <div className={styles.inputWithIcon}>
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    id="confirmPassword"
                    name="confirmPassword"
                    value={commonFields.confirmPassword}
                    onChange={handleCommonFieldChange}
                    required
                    placeholder="Re-enter password"
                    autoComplete="new-password"
                    disabled={isSubmitting}
                  />
                  <button
                    type="button"
                    aria-label={
                      showConfirmPassword ? "Hide confirm password" : "Show confirm password"
                    }
                    className={styles.iconBtn}
                    onClick={() => setShowConfirmPassword((s) => !s)}
                  >
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {fieldErrors.confirmPassword && (
                  <span className={styles.fieldError}>
                    <AlertCircle size={12} /> {fieldErrors.confirmPassword}
                  </span>
                )}
              </div>

              {/* Action Buttons */}
              <div className={`${styles.formActions} ${styles.fullWidth}`}>
                <button
                  type="submit"
                  className={styles.submitBtn}
                  disabled={
                    isSubmitting ||
                    collegeVerificationStatus !== "verified" ||
                    (!collegeVerifiedInstitution && !selectedCollege)
                  }
                  id="college-register-submit-btn"
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

                <p className={styles.loginPrompt}>
                  Already registered?{" "}
                  <Link to="/auth/login" className={styles.loginLink}>
                    Sign in here
                  </Link>
                </p>
              </div>
            </form>
          )}
        </section>
      </div>
    </main>
  );
}
