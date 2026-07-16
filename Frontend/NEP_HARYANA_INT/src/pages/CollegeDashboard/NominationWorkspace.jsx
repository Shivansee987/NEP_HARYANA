import { useState, useEffect, useRef } from "react";
import { useAuth } from "../../context/AuthContext.jsx";
import { HelpCircle } from "lucide-react";
import {
  fetchNominationDetails,
  saveNomination,
  submitNomination,
  uploadEvidenceToCloudinary,
} from "../../api/nomination";
import {
  fetchPrincipalClarification,
  submitPrincipalClarification
} from "../../api/committee";
import styles from "./NominationWorkspace.module.css";
import AwardJourney from "./AwardJourney";

// Dynamic configuration of the 20 indicators
const INDICATORS = [
  {
    num: 1,
    title: "Indicator 1 — Two Simultaneous Academic Programmes",
    max: 4,
    type: "yes_no_text",
    label: "Do you have provision for two simultaneous academic programmes?",
    additionalLabel: "Relevant document reference notes",
    rule: "Yes = 4 Marks, No = 0 Marks",
  },
  {
    num: 2,
    title: "Indicator 2 — Internship/Apprenticeship Embedded Degree Programmes",
    max: 4,
    type: "yes_no_text",
    label: "Do you offer Internship/Apprenticeship embedded degree programmes?",
    additionalLabel: "Name of the programme",
    rule: "Yes = 4 Marks, No = 0 Marks",
  },
  {
    num: 3,
    title: "Indicator 3 — Courses Offered in Indian Languages",
    max: 4,
    type: "yes_no_list",
    label: "Do you offer courses in Indian languages?",
    listLabel: "Course Name",
    maxItems: 4,
    rule: "1 Mark per course, maximum 4 Marks",
  },
  {
    num: 4,
    title: "Indicator 4 — Special Programmes in IKS (Indian Knowledge System)",
    max: 4,
    type: "yes_no_list",
    label: "Do you conduct special programmes in IKS?",
    listLabel: "Programme Name",
    maxItems: 4,
    rule: "1 Mark per programme, maximum 4 Marks",
  },
  {
    num: 5,
    title: "Indicator 5 — Institutional Development Plan (IDP) Developed",
    max: 6,
    type: "yes_no_url",
    label: "Has the IDP been developed and uploaded?",
    urlLabel: "URL link to IDP on website",
    rule: "Yes = 6 Marks, No = 0 Marks",
  },
  {
    num: 6,
    title: "Indicator 6 — Appointment of Ombudsperson",
    max: 2,
    type: "yes_no_text",
    label: "Is an Ombudsperson appointed?",
    additionalLabel: "Name of Ombudsperson",
    rule: "Yes = 2 Marks, No = 0 Marks",
  },
  {
    num: 7,
    title: "Indicator 7 — NAAC Accreditation Status",
    max: 8,
    type: "naac_dropdown",
    label: "Select your current NAAC accreditation grade",
    rule: "A++ = 8 Marks, A+ = 6 Marks, A = 4 Marks, B+ = 3 Marks, B or C = 2 Marks, Not Accredited = 0 Marks",
  },
  {
    num: 8,
    title: "Indicator 8 — Adoption of National Credit Framework (NCrF)",
    max: 2,
    type: "yes_no_flat",
    label: "Has the NCrF been adopted by the HEI?",
    rule: "Yes = 2 Marks, No = 0 Marks",
  },
  {
    num: 9,
    title: "Indicator 9 — Academic Bank of Credits (ABC) Registered Students",
    max: 8,
    type: "yes_no_pct",
    label: "Is the HEI registered on the ABC platform?",
    pctLabel: "% of enrolled students registered",
    rule: "More than 75% = 8 Marks, 51-75% = 6 Marks, 26-50% = 4 Marks, 1-25% = 2 Marks, No/0% = 0 Marks",
  },
  {
    num: 10,
    title: "Indicator 10 — Annual Update on AISHE Portal",
    max: 4,
    type: "yes_no_flat",
    label: "Is the AISHE portal updated annually?",
    rule: "Yes = 4 Marks, No = 0 Marks",
  },
  {
    num: 11,
    title: "Indicator 11 — Professor of Practice Appointed",
    max: 4,
    type: "yes_no_list",
    label: "Have you appointed Professors of Practice?",
    listLabel: "PoP Name",
    maxItems: 2,
    rule: "2 Marks per PoP, maximum 4 Marks",
  },
  {
    num: 12,
    title: "Indicator 12 — Incubation/Startup Cell Functional",
    max: 6,
    type: "yes_no_count_list",
    label: "Is there a functional Incubation/Startup Cell?",
    listLabel: "Registered Startup/Company Name",
    rule: "More than 10 startups = 6 Marks, 6 to 10 startups = 4 Marks, 1 to 5 startups = 2 Marks",
  },
  {
    num: 13,
    title: "Indicator 13 — National Innovation and Start-up Policy Implemented",
    max: 4,
    type: "yes_no_text",
    label: "Is the Innovation and Start-up Policy implemented?",
    additionalLabel: "Policy document reference note",
    rule: "Yes = 4 Marks, No = 0 Marks",
  },
  {
    num: 14,
    title: "Indicator 14 — Academic/Research Collaboration with Foreign HEIs",
    max: 6,
    type: "yes_no_list",
    label:
      "Do you have active research/academic collaboration with foreign HEIs?",
    listLabel: "Foreign Institution Name",
    maxItems: 6,
    rule: "1 Mark per active collaboration, maximum 6 Marks",
  },
  {
    num: 15,
    title: "Indicator 15 — Alumni Connect Cell Functional",
    max: 6,
    type: "yes_no_list",
    label: "Is the Alumni Connect Cell functional?",
    listLabel: "Activity Description (July 2024 to June 2025)",
    maxItems: 6,
    note: "Activities from July 2024 to June 2025 only",
    rule: "1 Mark per activity, maximum 6 Marks",
  },
  {
    num: 16,
    title: "Indicator 16 — Gender Parity Initiatives",
    max: 6,
    type: "yes_no_list",
    label: "Do you conduct Gender Parity initiatives?",
    listLabel: "Activity Description (July 2024 to June 2025)",
    maxItems: 6,
    note: "Activities from July 2024 to June 2025 only",
    rule: "1 Mark per activity, maximum 6 Marks",
  },
  {
    num: 17,
    title: "Indicator 17 — Psychological and Emotional Well-Being Programmes",
    max: 6,
    type: "yes_no_list",
    label: "Do you offer psychological/well-being support programmes?",
    listLabel: "Activity Description (July 2024 to June 2025)",
    maxItems: 6,
    note: "Activities from July 2024 to June 2025 only",
    rule: "1 Mark per activity, maximum 6 Marks",
  },
  {
    num: 18,
    title: "Indicator 18 — UGC Guidelines on Student Welfare & Fitness",
    max: 6,
    type: "yes_no_list",
    label: "Have you implemented UGC Guidelines on Student Welfare?",
    listLabel: "Activity Description (July 2024 to June 2025)",
    maxItems: 6,
    note: "Activities from July 2024 to June 2025 only",
    rule: "1 Mark per activity, maximum 6 Marks",
  },
  {
    num: 19,
    title: "Indicator 19 — Provision for Online Courses / MOOCs Policy",
    max: 4,
    type: "yes_no_text",
    label: "Do you have a policy for online/MOOCs courses?",
    additionalLabel: "Policy document reference note",
    rule: "Yes = 4 Marks, No = 0 Marks",
  },
  {
    num: 20,
    title: "Indicator 20 — Teachers Trained & Certified under MMTTC",
    max: 6,
    type: "flat_pct",
    label: "Percentage of faculty trained under MMTTC",
    rule: "More than 75% faculty = 6 Marks, 51-75% = 4 Marks, 1-50% = 2 Marks, 0% = 0 Marks",
  },
];

export default function NominationWorkspace({ formId, onBack }) {
  const { user } = useAuth();

  // Role check — colleges/principals must never see scoring info
  const isCollege = user?.role === "principal" || user?.role === "college";

  // States
  const [nomination, setNomination] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [activeStep, setActiveStep] = useState(0); // 0: Basic Info, 1: Ind 1-5, 2: Ind 6-10, 3: Ind 11-15, 4: Ind 16-20, 5: Document Index, 6: Submit
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Local answers state (synchronized with server)
  const [basicInfo, setBasicInfo] = useState({
    head_name: "",
    head_contact: "",
    address: "",
    institution_type: "Government College",
  });
  const [answers, setAnswers] = useState({});
  const [declarationAccepted, setDeclarationAccepted] = useState(false);
  const [uploadingIndicator, setUploadingIndicator] = useState(null);

  // Local dynamic input temporary strings
  const [tempListInputs, setTempListInputs] = useState({});

  // Clarification workflow states
  const [activeClarification, setActiveClarification] = useState(null);
  const [allowedFields, setAllowedFields] = useState([]);
  const [clarificationResponse, setClarificationResponse] = useState("");
  const [submittingClarification, setSubmittingClarification] = useState(false);

  // Coerce submission state into a reliable boolean. Backend may send strings.
  const isFormLocked = nomination
    ? nomination.is_submitted === true ||
      String(nomination.is_submitted).toLowerCase() === "true" ||
      nomination.status === "submitted"
    : false;

  const isFieldLocked = (num) => {
    if (!nomination) return true;
    const isSubmitted = nomination.is_submitted === true ||
      String(nomination.is_submitted).toLowerCase() === "true" ||
      nomination.status === "submitted" ||
      nomination.status === "Clarification Requested";
      
    if (!isSubmitted) return false;
    
    if (nomination.status === "Clarification Requested") {
      return !allowedFields.includes(`indicator_${num}`);
    }
    
    return true;
  };

  useEffect(() => {
    async function loadData() {
      try {
        if (!formId) {
          setErrorMessage("No form selected. Please go back and open a form again.");
          setLoading(false);
          return;
        }
        const data = await fetchNominationDetails(formId);
        setNomination(data);
        setBasicInfo({
          head_name: data.head_name || "",
          head_contact: data.head_contact || "",
          address: data.address || "",
          institution_type: data.institution_type || "Government College",
        });
        setAnswers(data.answers || {});
        setDeclarationAccepted(false);

        if (data.status === "Clarification Requested") {
          try {
            const clars = await fetchPrincipalClarification(formId);
            const active = clars.find(c => c.status === "Pending");
            if (active) {
              setActiveClarification(active);
              setAllowedFields(active.fields_to_edit || []);
            }
          } catch (err) {
            console.error("Error loading clarification details:", err);
          }
        }
      } catch (err) {
        console.error("Error loading nomination details:", err);
        setErrorMessage(err.message || "Failed to load form details.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [formId]);

  // Live Score Calculator
  const getLiveScore = () => {
    let score = 0;

    // 1
    if (answers.indicator_1?.value === "Yes") score += 4;
    // 2
    if (answers.indicator_2?.value === "Yes") score += 4;
    // 3
    if (answers.indicator_3?.value === "Yes")
      score += Math.min(answers.indicator_3?.items?.length || 0, 4);
    // 4
    if (answers.indicator_4?.value === "Yes")
      score += Math.min(answers.indicator_4?.items?.length || 0, 4);
    // 5
    if (answers.indicator_5?.value === "Yes") score += 6;
    // 6
    if (answers.indicator_6?.value === "Yes") score += 2;
    // 7
    const naac = answers.indicator_7?.value;
    if (naac === "A++") score += 8;
    else if (naac === "A+") score += 6;
    else if (naac === "A") score += 4;
    else if (naac === "B+") score += 3;
    else if (naac === "B" || naac === "C") score += 2;
    // 8
    if (answers.indicator_8?.value === "Yes") score += 2;
    // 9
    if (answers.indicator_9?.value === "Yes") {
      const pct = parseFloat(answers.indicator_9?.percentage || 0);
      if (pct > 75) score += 8;
      else if (pct > 50) score += 6;
      else if (pct > 25) score += 4;
      else if (pct > 0) score += 2;
    }
    // 10
    if (answers.indicator_10?.value === "Yes") score += 4;
    // 11
    if (answers.indicator_11?.value === "Yes")
      score += Math.min((answers.indicator_11?.items?.length || 0) * 2, 4);
    // 12
    if (answers.indicator_12?.value === "Yes") {
      const count = parseInt(answers.indicator_12?.count || 0, 10);
      if (count > 10) score += 6;
      else if (count >= 6) score += 4;
      else if (count >= 1) score += 2;
    }
    // 13
    if (answers.indicator_13?.value === "Yes") score += 4;
    // 14
    if (answers.indicator_14?.value === "Yes")
      score += Math.min(answers.indicator_14?.items?.length || 0, 6);
    // 15
    if (answers.indicator_15?.value === "Yes")
      score += Math.min(answers.indicator_15?.items?.length || 0, 6);
    // 16
    if (answers.indicator_16?.value === "Yes")
      score += Math.min(answers.indicator_16?.items?.length || 0, 6);
    // 17
    if (answers.indicator_17?.value === "Yes")
      score += Math.min(answers.indicator_17?.items?.length || 0, 6);
    // 18
    if (answers.indicator_18?.value === "Yes")
      score += Math.min(answers.indicator_18?.items?.length || 0, 6);
    // 19
    if (answers.indicator_19?.value === "Yes") score += 4;
    // 20
    const pct20 = parseFloat(answers.indicator_20?.percentage || 0);
    if (pct20 > 75) score += 6;
    else if (pct20 > 50) score += 4;
    else if (pct20 > 0) score += 2;

    let award = "No Award";
    if (score > 90) award = "Platinum";
    else if (score >= 75) award = "Gold";
    else if (score > 50) award = "Silver";

    return { score, award };
  };

  const { score: liveScore, award: liveAward } = getLiveScore();
  const displayScore = nomination?.is_submitted ? (nomination.score ?? 0) : liveScore;
  const displayAward = nomination?.is_submitted ? (nomination.award_category ?? "No Award") : liveAward;


  // Basic Info Change Handler
  const handleBasicInfoChange = (e) => {
    setBasicInfo({
      ...basicInfo,
      [e.target.name]: e.target.value,
    });
  };

  // Answers Change Handler
  const updateIndicatorValue = (num, field, val) => {
    if (isFieldLocked(num)) return;
    const key = `indicator_${num}`;
    setAnswers((prevAnswers) => {
      const current = prevAnswers[key] || {};
      return {
        ...prevAnswers,
        [key]: {
          ...current,
          [field]: val,
        },
      };
    });
  };

  // Add Item to Dynamic List
  const handleAddListItem = (num) => {
    if (isFieldLocked(num)) return;
    const val = tempListInputs[num] || "";
    if (!val.trim()) return;

    const key = `indicator_${num}`;
    const current = answers[key] || {};
    const items = current.items || [];

    updateIndicatorValue(num, "items", [...items, val.trim()]);
    setTempListInputs({
      ...tempListInputs,
      [num]: "",
    });
  };

  // Remove Item from Dynamic List
  const handleRemoveListItem = (num, indexToRemove) => {
    if (isFieldLocked(num)) return;
    const key = `indicator_${num}`;
    const current = answers[key] || {};
    const items = current.items || [];

    updateIndicatorValue(
      num,
      "items",
      items.filter((_, idx) => idx !== indexToRemove),
    );
  };

  // Cloudinary File Upload Handler
  const handleFileUpload = async (num, e) => {
    if (isFieldLocked(num)) return;
    const file = e.target.files[0];
    if (!file) return;

    setUploadingIndicator(num);
    setErrorMessage("");
    try {
      const res = await uploadEvidenceToCloudinary(file);
      updateIndicatorValue(num, "evidence_url", res.url);
      updateIndicatorValue(num, "evidence_name", res.original_filename);
    } catch (err) {
      setErrorMessage(err.message || "File upload failed.");
    } finally {
      setUploadingIndicator(null);
    }
  };

  const isSaveDisabled = nomination
    ? (nomination.is_submitted === true || String(nomination.is_submitted).toLowerCase() === "true" || nomination.status === "submitted") && nomination.status !== "Clarification Requested"
    : false;

  // Save Draft Action
  const handleSaveDraft = async () => {
    if (saving || isSaveDisabled) return;
    setSaving(true);
    setErrorMessage("");
    setSuccessMessage("");
    try {
      const payload = {
        ...basicInfo,
        answers,
      };
      const res = await saveNomination(formId, payload);
      setNomination(res.nomination);
      setSuccessMessage(res.message || "Draft saved successfully.");
    } catch (err) {
      setErrorMessage(err.message || "Could not save draft.");
    } finally {
      setSaving(false);
    }
  };

  // Submit Nomination Action
  const handleSubmitNomination = async () => {
    if (submitting || isFormLocked) return;
    setSubmitting(true);
    setErrorMessage("");
    setSuccessMessage("");
    try {
      // First save latest answers
      const payloadSave = {
        ...basicInfo,
        answers,
      };
      await saveNomination(formId, payloadSave);

      // Then trigger final submission locking
      const res = await submitNomination(formId, {
        declaration_accepted: declarationAccepted,
      });
      setNomination(res.nomination);
      setSuccessMessage(res.message || "Nomination submitted successfully!");
      setActiveStep(6); // stay on final lock screen
    } catch (err) {
      setErrorMessage(err.message || "Could not submit nomination.");
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Clarification Response Action
  const handleSubmitClarification = async () => {
    if (!clarificationResponse.trim()) {
      alert("Please enter your clarification response text.");
      return;
    }
    setSubmittingClarification(true);
    setErrorMessage("");
    setSuccessMessage("");
    try {
      // First save the latest values of allowed fields
      const payloadSave = {
        ...basicInfo,
        answers,
      };
      await saveNomination(formId, payloadSave);

      // Then submit the clarification response
      const res = await submitPrincipalClarification(formId, {
        response: clarificationResponse
      });
      setSuccessMessage(res.message || "Clarification response submitted successfully.");
      setActiveClarification(null);
      // Reload nomination status
      const updatedNom = await fetchNominationDetails(formId);
      setNomination(updatedNom);
    } catch (err) {
      setErrorMessage(err.message || "Could not submit clarification response.");
    } finally {
      setSubmittingClarification(false);
    }
  };

  // Ref to always hold the latest state for unmount auto-save
  const latestStateRef = useRef({ basicInfo, answers, isSaveDisabled, formId });
  useEffect(() => {
    latestStateRef.current = { basicInfo, answers, isSaveDisabled, formId };
  }, [basicInfo, answers, isSaveDisabled, formId]);

  // Auto-save on component unmount (navigating away / redirect / logout)
  useEffect(() => {
    return () => {
      const { basicInfo: bInfo, answers: ans, isSaveDisabled: saveDisabled, formId: fId } = latestStateRef.current;
      const token = localStorage.getItem("nep_haryana_access_token");
      if (!saveDisabled && fId && token && bInfo && (bInfo.head_name || bInfo.head_contact || bInfo.address)) {
        saveNomination(fId, { ...bInfo, answers: ans }).catch((err) => {
          console.error("Auto-save on unmount failed:", err);
        });
      }
    };
  }, []);

  // Auto-save on tab change (activeStep change)
  const prevActiveStepRef = useRef(activeStep);
  useEffect(() => {
    if (prevActiveStepRef.current !== activeStep) {
      if (!isSaveDisabled && formId) {
        saveNomination(formId, { ...basicInfo, answers }).catch((err) => {
          console.error("Auto-save on tab change failed:", err);
        });
      }
      prevActiveStepRef.current = activeStep;
    }
  }, [activeStep, basicInfo, answers, isSaveDisabled, formId]);

  // Back to Forms button click handler with automatic draft save
  const handleBackWithSave = async () => {
    if (!isSaveDisabled && formId) {
      setSaving(true);
      try {
        await saveNomination(formId, { ...basicInfo, answers });
      } catch (err) {
        console.error("Auto-save on exit failed:", err);
      } finally {
        setSaving(false);
      }
    }
    onBack();
  };

  // Navigation handlers
  const handleNextStep = () => {
    setActiveStep((prev) => Math.min(prev + 1, 6));
  };

  const handlePrevStep = () => {
    setActiveStep((prev) => Math.max(prev - 1, 0));
  };

  // Check which indicators are complete
  const getIndicatorStatus = (num) => {
    const key = `indicator_${num}`;
    const ans = answers[key] || {};
    const value = ans.value;
    const hasEvidence = !!ans.evidence_url;

    if (!value) return "empty";
    if (hasEvidence) return "evidence";
    return "filled";
  };

  const getIndicatorsCount = () => {
    let filled = 0;
    for (let i = 1; i <= 20; i++) {
      if (getIndicatorStatus(i) !== "empty") filled++;
    }
    return filled;
  };

  // ---- Loading state ----
  if (loading) {
    return (
      <div className={styles.loadingSpinnerContainer}>
        <div className={styles.spinner}></div>
        <p>Loading nomination form data...</p>
      </div>
    );
  }

  // ---- Fallback: loading finished but nomination failed to load ----
  if (!nomination) {
    return (
      <div className={styles.loadingSpinnerContainer}>
        <p style={{ color: "#ef4444", fontWeight: 600, marginBottom: "16px" }}>
          {errorMessage || "Could not load this form. Please go back and try again."}
        </p>
        <button className={styles.secondaryBtn} onClick={onBack}>
          ← Back to Forms
        </button>
      </div>
    );
  }

  // Get active step indicators
  const getStepIndicators = () => {
    if (activeStep === 1) return INDICATORS.slice(0, 5);
    if (activeStep === 2) return INDICATORS.slice(5, 10);
    if (activeStep === 3) return INDICATORS.slice(10, 15);
    if (activeStep === 4) return INDICATORS.slice(15, 20);
    return [];
  };

  // Build Document Index Table
  const renderDocumentIndexTable = () => {
    const rows = [];
    INDICATORS.forEach((ind) => {
      const key = `indicator_${ind.num}`;
      const ans = answers[key] || {};
      if (ans.evidence_url) {
        rows.push({
          num: ind.num,
          title: ind.title,
          fileName: ans.evidence_name || "Attachment",
          url: ans.evidence_url,
          pageNo: ans.page_no || "N/A",
        });
      }
    });

    if (rows.length === 0) {
      return (
        <p
          style={{
            color: "#64748b",
            fontStyle: "italic",
            fontSize: "0.875rem",
          }}
        >
          No evidence documents uploaded yet.
        </p>
      );
    }

    return (
      <table className={styles.documentIndexTable}>
        <thead>
          <tr>
            <th>Sr. No.</th>
            <th>Indicator No.</th>
            <th>Indicator Name</th>
            <th>Document Name</th>
            <th>Page No.</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={row.num}>
              <td>{idx + 1}</td>
              <td>{row.num}</td>
              <td>{row.title}</td>
              <td>
                <a
                  href={row.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "#2563eb", textDecoration: "underline" }}
                >
                  {row.fileName}
                </a>
              </td>
              <td>
                <strong>{row.pageNo}</strong>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  return (
    <div className={styles.workspaceContainer}>
      {/* Header */}
      <header className={styles.workspaceHeader}>
        <div className={styles.headerTitleGroup}>
          <button
            onClick={handleBackWithSave}
            className={styles.secondaryBtn}
            style={{
              marginBottom: "12px",
              padding: "6px 12px",
              fontSize: "0.75rem",
            }}
          >
            ← Back to Forms
          </button>
          <h1>Nomination Workspace</h1>
          <p>
            {nomination?.form_id === "nep-excellence-nomination-2025"
              ? "Nomination Form for Haryana State NEP 2020 Implementation Excellence Award"
              : "Institutional Form"}
          </p>
        </div>
        <div>
          <span
            className={`${styles.statusBadge} ${isFormLocked ? styles.submitted : nomination ? styles.draft : styles.not_started}`}
          >
            {isFormLocked ? "Submitted (Locked)" : "Draft"}
          </span>
        </div>
      </header>

      {/* Award Journey Milestones — hidden from College/Principal users */}
      {!isCollege && (
        <div style={{ gridColumn: "1 / -1", marginBottom: "16px" }}>
          <AwardJourney score={displayScore} award={displayAward} />
        </div>
      )}

      {/* Sidebar Panel (Live score) */}
      <aside className={styles.summaryPanel}>
        {!isCollege && (
          <div className={styles.scoreWidget}>
            <h3>Nomination Score</h3>
            <div className={styles.scoreValue}>
              {displayScore}
              <span>/100</span>
            </div>
            <span
              className={`${styles.awardBadge} ${styles[displayAward.replace(/\s+/g, "")]}`}
            >
              {displayAward}
            </span>
          </div>
        )}

        <div className={styles.completionProgress}>
          <div className={styles.completionText}>
            <span>Completion Status</span>
            <span>{getIndicatorsCount()} / 20 filled</span>
          </div>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${(getIndicatorsCount() / 20) * 100}%` }}
            ></div>
          </div>
        </div>

        <div>
          <h4 className={styles.indicatorListTitle}>Indicator Map</h4>
          <div className={styles.checklistItems}>
            {INDICATORS.map((ind) => {
              const status = getIndicatorStatus(ind.num);
              return (
                <div
                  key={ind.num}
                  className={`${styles.checklistItem} ${activeStep === Math.ceil(ind.num / 5) ? styles.active : ""}`}
                  onClick={() => setActiveStep(Math.ceil(ind.num / 5))}
                >
                  <span
                    className={`${styles.statusIndicator} ${styles[status]}`}
                  ></span>
                  <span className={styles.indicatorLabel}>
                    Ind {ind.num}: {ind.title.split(" — ")[1]}
                    {allowedFields.includes(`indicator_${ind.num}`) && (
                      <span style={{ color: "#d97706", fontSize: "0.6875rem", fontWeight: "bold", marginLeft: "6px", backgroundColor: "#fef3c7", padding: "1px 6px", borderRadius: "4px", border: "1px solid #f59e0b" }}>
                        Edit Open
                      </span>
                    )}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </aside>

      {/* Main Workspace Panels */}
      <main className={styles.formPanel}>
        {errorMessage && (
          <div
            className={styles.errorMessageBlock}
            style={{
              backgroundColor: "#fee2e2",
              borderLeft: "4px solid #ef4444",
              color: "#b91c1c",
              padding: "12px",
              borderRadius: "8px",
              fontSize: "0.875rem",
            }}
          >
            {errorMessage}
          </div>
        )}
        {successMessage && (
          <div
            className={styles.successMessageBlock}
            style={{
              backgroundColor: "#d1fae5",
              borderLeft: "4px solid #10b981",
              color: "#065f46",
              padding: "12px",
              borderRadius: "8px",
              fontSize: "0.875rem",
            }}
          >
            {successMessage}
          </div>
        )}

        {activeClarification && (
          <div
            style={{
              backgroundColor: "#fef3c7",
              border: "1px solid #f59e0b",
              borderRadius: "12px",
              padding: "20px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              boxShadow: "0 4px 15px rgba(245, 158, 11, 0.08)",
              marginBottom: "16px"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#b45309" }}>
              <HelpCircle className="w-5 h-5" />
              <h4 style={{ fontWeight: "700", margin: 0, fontSize: "1rem" }}>
                Clarification Requested by Screening Committee
              </h4>
            </div>
            
            <p style={{ fontSize: "0.875rem", color: "#78350f", margin: 0, lineHeight: "1.5" }}>
              <strong>Query:</strong> {activeClarification.query}
            </p>

            <p style={{ fontSize: "0.8125rem", color: "#78350f", margin: 0 }}>
              <strong>Fields open for editing:</strong>{" "}
              <span style={{ textDecoration: "underline", fontWeight: "600" }}>
                {activeClarification.fields_to_edit?.map(f => f.replace("indicator_", "Indicator ")).join(", ") || "None"}
              </span>
            </p>
            
            <div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "0.75rem", fontWeight: "700", color: "#78350f", textTransform: "uppercase" }}>
                Your Response / Clarification
              </label>
              <textarea
                rows="3"
                value={clarificationResponse}
                onChange={(e) => setClarificationResponse(e.target.value)}
                placeholder="Explain the changes made or provide the requested information..."
                style={{
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: "1px solid #d97706",
                  fontSize: "0.875rem",
                  color: "#1e293b",
                  backgroundColor: "#ffffff",
                  width: "100%",
                  outline: "none"
                }}
              />
            </div>
            
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "4px" }}>
              <button
                type="button"
                className={styles.submitBtn}
                style={{
                  backgroundColor: "#d97706",
                  background: "#d97706",
                  fontSize: "0.8125rem",
                  padding: "8px 20px",
                  boxShadow: "0 2px 8px rgba(217, 119, 6, 0.2)"
                }}
                disabled={submittingClarification || !clarificationResponse.trim()}
                onClick={handleSubmitClarification}
              >
                {submittingClarification ? "Submitting Response..." : "Submit Response & Resubmit Form"}
              </button>
            </div>
          </div>
        )}

        {/* Tab Selection */}
        <div className={styles.stepperTabs}>
          <button
            className={`${styles.stepperTab} ${activeStep === 0 ? styles.active : ""}`}
            onClick={() => setActiveStep(0)}
          >
            Basic Info
          </button>
          <button
            className={`${styles.stepperTab} ${activeStep === 1 ? styles.active : ""}`}
            onClick={() => setActiveStep(1)}
          >
            1 - 5
          </button>
          <button
            className={`${styles.stepperTab} ${activeStep === 2 ? styles.active : ""}`}
            onClick={() => setActiveStep(2)}
          >
            6 - 10
          </button>
          <button
            className={`${styles.stepperTab} ${activeStep === 3 ? styles.active : ""}`}
            onClick={() => setActiveStep(3)}
          >
            11 - 15
          </button>
          <button
            className={`${styles.stepperTab} ${activeStep === 4 ? styles.active : ""}`}
            onClick={() => setActiveStep(4)}
          >
            16 - 20
          </button>
          <button
            className={`${styles.stepperTab} ${activeStep === 5 ? styles.active : ""}`}
            onClick={() => setActiveStep(5)}
          >
            Document Index
          </button>
          <button
            className={`${styles.stepperTab} ${activeStep === 6 ? styles.active : ""}`}
            onClick={() => setActiveStep(6)}
          >
            Declaration
          </button>
        </div>

        {/* Section 1: Basic Info */}
        {activeStep === 0 && (
          <section className={styles.cardSection}>
            <h3 className={styles.sectionTitle}>
              Section 1 — Institution Basic Info
            </h3>
            <div className={styles.basicInfoGrid}>
              <div className={styles.formGroup}>
                <label>Institution Name</label>
                <input type="text" value={user?.college_name || ""} readOnly />
              </div>
              <div className={styles.formGroup}>
                <label>AISHE Code</label>
                <input type="text" value={user?.aishe_code || ""} readOnly />
              </div>
              <div className={styles.formGroup}>
                <label>Name of Head of Institute</label>
                <input
                  type="text"
                  name="head_name"
                  value={basicInfo.head_name}
                  onChange={handleBasicInfoChange}
                  disabled={isFormLocked}
                  placeholder="Enter name"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Contact of Head of Institute</label>
                <input
                  type="text"
                  name="head_contact"
                  value={basicInfo.head_contact}
                  onChange={handleBasicInfoChange}
                  disabled={isFormLocked}
                  placeholder="e.g. +91 9876543210"
                />
              </div>
              <div
                className={styles.formGroup}
                style={{ gridColumn: "1 / -1" }}
              >
                <label>Address of HEI</label>
                <textarea
                  name="address"
                  rows="3"
                  value={basicInfo.address}
                  onChange={handleBasicInfoChange}
                  disabled={isFormLocked}
                  placeholder="Enter address details"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Institution Type</label>
                <select
                  name="institution_type"
                  value={basicInfo.institution_type}
                  onChange={handleBasicInfoChange}
                  disabled={isFormLocked}
                >
                  <option value="University (State)">University (State)</option>
                  <option value="University (Private)">
                    University (Private)
                  </option>
                  <option value="Government College">Government College</option>
                  <option value="Government-aided College">
                    Government-aided College
                  </option>
                  <option value="Private College">Private College</option>
                </select>
              </div>
            </div>
          </section>
        )}

        {/* Section 2: Stepper Indicators */}
        {activeStep >= 1 && activeStep <= 4 && (
          <div className={styles.indicatorsWrapper}>
            {getStepIndicators().map((ind) => {
              const key = `indicator_${ind.num}`;
              const data = answers[key] || {};
              const evidenceName = data.evidence_name || "";
              const pageNo = data.page_no || "";

              return (
                <article key={ind.num} className={styles.indicatorCard}>
                  <div className={styles.indicatorHeader}>
                    <div className={styles.indicatorTitleGroup}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        <h4>{ind.title}</h4>
                        {allowedFields.includes(`indicator_${ind.num}`) && (
                          <span style={{ color: "#d97706", fontSize: "0.6875rem", fontWeight: "bold", backgroundColor: "#fef3c7", border: "1px solid #f59e0b", padding: "2px 8px", borderRadius: "9999px" }}>
                            ✏️ Edit Unlocked
                          </span>
                        )}
                      </div>
                      <p
                        style={{
                          fontSize: "0.75rem",
                          color: "#64748b",
                          marginTop: "4px",
                        }}
                      >
                        <strong>Benchmarks / Scoring Logic:</strong> {ind.rule}
                      </p>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px" }}>
                      <span className={styles.indicatorMaxScore}>
                        Max: {ind.max} Marks
                      </span>
                      {!isCollege && nomination?.is_submitted && nomination?.reviewer_scores?.[`indicator_${ind.num}`] !== undefined && (
                        <span style={{ fontSize: "0.725rem", fontWeight: "bold", color: "#10b981", backgroundColor: "#ecfdf5", border: "1px solid #a7f3d0", padding: "2px 8px", borderRadius: "4px" }}>
                          Verified: {nomination.reviewer_scores[`indicator_${ind.num}`]} / {ind.max}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className={styles.indicatorBody}>
                    <p
                      style={{
                        fontSize: "0.875rem",
                        color: "#475569",
                        marginBottom: "12px",
                      }}
                    >
                      {ind.label}
                    </p>

                    {/* Render inputs based on indicator type */}
                    {ind.type === "yes_no_flat" && (
                      <div className="flex gap-4">
                        <label className="inline-flex items-center gap-2 mr-4">
                          <input
                            type="radio"
                            disabled={isFieldLocked(ind.num)}
                            checked={data.value === "Yes"}
                            onChange={() =>
                              updateIndicatorValue(ind.num, "value", "Yes")
                            }
                          />{" "}
                          Yes
                        </label>
                        <label className="inline-flex items-center gap-2">
                          <input
                            type="radio"
                            disabled={isFieldLocked(ind.num)}
                            checked={data.value === "No"}
                            onChange={() =>
                              updateIndicatorValue(ind.num, "value", "No")
                            }
                          />{" "}
                          No
                        </label>
                      </div>
                    )}

                    {ind.type === "yes_no_text" && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "12px",
                        }}
                      >
                        <div>
                          <label className="inline-flex items-center gap-2 mr-4">
                            <input
                              type="radio"
                              disabled={isFieldLocked(ind.num)}
                              checked={data.value === "Yes"}
                              onChange={() =>
                                updateIndicatorValue(ind.num, "value", "Yes")
                              }
                            />{" "}
                              Yes
                          </label>
                          <label className="inline-flex items-center gap-2">
                            <input
                              type="radio"
                              disabled={isFieldLocked(ind.num)}
                              checked={data.value === "No"}
                              onChange={() =>
                                updateIndicatorValue(ind.num, "value", "No")
                              }
                            />{" "}
                              No
                          </label>
                        </div>
                        {data.value === "Yes" && (
                          <div className={styles.formGroup}>
                            <label style={{ fontSize: "0.75rem" }}>
                              {ind.additionalLabel}
                            </label>
                            <input
                              type="text"
                              disabled={isFieldLocked(ind.num)}
                              value={data.note || ""}
                              onChange={(e) =>
                                updateIndicatorValue(
                                  ind.num,
                                  "note",
                                  e.target.value,
                                )
                              }
                              placeholder="Enter details"
                            />
                          </div>
                        )}
                      </div>
                    )}

                    {ind.type === "yes_no_url" && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "12px",
                        }}
                      >
                        <div>
                          <label className="inline-flex items-center gap-2 mr-4">
                            <input
                              type="radio"
                              disabled={isFieldLocked(ind.num)}
                              checked={data.value === "Yes"}
                              onChange={() =>
                                updateIndicatorValue(ind.num, "value", "Yes")
                              }
                            />{" "}
                              Yes
                          </label>
                          <label className="inline-flex items-center gap-2">
                            <input
                              type="radio"
                              disabled={isFieldLocked(ind.num)}
                              checked={data.value === "No"}
                              onChange={() =>
                                updateIndicatorValue(ind.num, "value", "No")
                              }
                            />{" "}
                              No
                          </label>
                        </div>
                        {data.value === "Yes" && (
                          <div className={styles.formGroup}>
                            <label style={{ fontSize: "0.75rem" }}>
                              {ind.urlLabel}
                            </label>
                            <input
                              type="url"
                              disabled={isFieldLocked(ind.num)}
                              value={data.url || ""}
                              onChange={(e) =>
                                updateIndicatorValue(
                                  ind.num,
                                  "url",
                                  e.target.value,
                                )
                              }
                              placeholder="https://college.edu.in/idp"
                            />
                          </div>
                        )}
                      </div>
                    )}

                    {ind.type === "naac_dropdown" && (
                      <div
                        className={styles.formGroup}
                        style={{ maxWidth: "250px" }}
                      >
                        <select
                          disabled={isFieldLocked(ind.num)}
                          value={data.value || ""}
                          onChange={(e) =>
                            updateIndicatorValue(
                              ind.num,
                              "value",
                              e.target.value,
                            )
                          }
                        >
                          <option value="">-- Select Grade --</option>
                          <option value="A++">A++ (8 Marks)</option>
                          <option value="A+">A+ (6 Marks)</option>
                          <option value="A">A (4 Marks)</option>
                          <option value="B+">B+ (3 Marks)</option>
                          <option value="B">B (2 Marks)</option>
                          <option value="C">C (2 Marks)</option>
                          <option value="Not Accredited">
                            Not Accredited (0 Marks)
                          </option>
                        </select>
                      </div>
                    )}

                    {ind.type === "yes_no_pct" && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "16px",
                        }}
                      >
                        <div>
                          <label className="inline-flex items-center gap-2 mr-4">
                            <input
                              type="radio"
                              disabled={isFieldLocked(ind.num)}
                              checked={data.value === "Yes"}
                              onChange={() =>
                                updateIndicatorValue(ind.num, "value", "Yes")
                              }
                            />{" "}
                            Yes
                          </label>
                          <label className="inline-flex items-center gap-2">
                            <input
                              type="radio"
                              disabled={isFieldLocked(ind.num)}
                              checked={data.value === "No"}
                              onChange={() => {
                                updateIndicatorValue(ind.num, "value", "No");
                                updateIndicatorValue(ind.num, "percentage", "");
                              }}
                            />{" "}
                            No
                          </label>
                        </div>
                        {data.value === "Yes" && (
                          <div
                            style={{
                              display: "flex",
                              flexDirection: "column",
                              gap: "12px",
                            }}
                          >
                            <div
                              className={styles.formGroup}
                              style={{ maxWidth: "160px" }}
                            >
                              <label
                                style={{
                                  fontSize: "0.75rem",
                                  fontWeight: "600",
                                  color: "#475569",
                                }}
                              >
                                {ind.pctLabel}
                              </label>
                              <div className={styles.percentageInputWrapper}>
                                <input
                                  type="number"
                                  disabled={isFieldLocked(ind.num)}
                                  min="0"
                                  max="100"
                                  value={data.percentage || ""}
                                  onChange={(e) =>
                                    updateIndicatorValue(
                                      ind.num,
                                      "percentage",
                                      e.target.value,
                                    )
                                  }
                                  placeholder="e.g. 80"
                                />
                              </div>
                            </div>

                            {/* Slab cards grid */}
                            <div className={styles.slabGrid}>
                              <div
                                className={`${styles.slabCard} ${parseFloat(data.percentage) > 75 ? styles.highlighted : ""}`}
                              >
                                <span className={styles.slabCardTitle}>
                                  More than 75%
                                </span>
                                <span className={styles.slabCardMarks}>
                                  8 Marks
                                </span>
                              </div>
                              <div
                                className={`${styles.slabCard} ${parseFloat(data.percentage) <= 75 && parseFloat(data.percentage) > 50 ? styles.highlighted : ""}`}
                              >
                                <span className={styles.slabCardTitle}>
                                  51% to 75%
                                </span>
                                <span className={styles.slabCardMarks}>
                                  6 Marks
                                </span>
                              </div>
                              <div
                                className={`${styles.slabCard} ${parseFloat(data.percentage) <= 50 && parseFloat(data.percentage) > 25 ? styles.highlighted : ""}`}
                              >
                                <span className={styles.slabCardTitle}>
                                  26% to 50%
                                </span>
                                <span className={styles.slabCardMarks}>
                                  4 Marks
                                </span>
                              </div>
                              <div
                                className={`${styles.slabCard} ${parseFloat(data.percentage) <= 25 && parseFloat(data.percentage) > 0 ? styles.highlighted : ""}`}
                              >
                                <span className={styles.slabCardTitle}>
                                  1% to 25%
                                </span>
                                <span className={styles.slabCardMarks}>
                                  2 Marks
                                </span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {ind.type === "flat_pct" && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "12px",
                        }}
                      >
                        <div
                          className={styles.formGroup}
                          style={{ maxWidth: "160px" }}
                        >
                          <div className={styles.percentageInputWrapper}>
                            <input
                              type="number"
                              disabled={isFieldLocked(ind.num)}
                              min="0"
                              max="100"
                              value={data.percentage || ""}
                              onChange={(e) => {
                                const val = e.target.value;
                                updateIndicatorValue(
                                  ind.num,
                                  "percentage",
                                  val,
                                );
                                updateIndicatorValue(
                                  ind.num,
                                  "value",
                                  val !== "" ? "Yes" : "",
                                );
                              }}
                              placeholder="e.g. 65"
                            />
                          </div>
                        </div>

                        {/* Slab cards grid */}
                        <div className={styles.slabGrid}>
                          <div
                            className={`${styles.slabCard} ${parseFloat(data.percentage) > 75 ? styles.highlighted : ""}`}
                          >
                            <span className={styles.slabCardTitle}>
                              More than 75% faculty
                            </span>
                            <span className={styles.slabCardMarks}>
                              6 Marks
                            </span>
                          </div>
                          <div
                            className={`${styles.slabCard} ${parseFloat(data.percentage) <= 75 && parseFloat(data.percentage) > 50 ? styles.highlighted : ""}`}
                          >
                            <span className={styles.slabCardTitle}>
                              51% to 75% faculty
                            </span>
                            <span className={styles.slabCardMarks}>
                              4 Marks
                            </span>
                          </div>
                          <div
                            className={`${styles.slabCard} ${parseFloat(data.percentage) <= 50 && parseFloat(data.percentage) > 0 ? styles.highlighted : ""}`}
                          >
                            <span className={styles.slabCardTitle}>
                              1% to 50% faculty
                            </span>
                            <span className={styles.slabCardMarks}>
                              2 Marks
                            </span>
                          </div>
                        </div>
                      </div>
                    )}

                    {ind.type === "yes_no_list" && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "12px",
                        }}
                      >
                        <div>
                          <label className="inline-flex items-center gap-2 mr-4">
                            <input
                              type="radio"
                              disabled={isFieldLocked(ind.num)}
                              checked={data.value === "Yes"}
                              onChange={() =>
                                updateIndicatorValue(ind.num, "value", "Yes")
                              }
                            />{" "}
                            Yes
                          </label>
                          <label className="inline-flex items-center gap-2">
                            <input
                              type="radio"
                              disabled={isFieldLocked(ind.num)}
                              checked={data.value === "No"}
                              onChange={() =>
                                updateIndicatorValue(ind.num, "value", "No")
                              }
                            />{" "}
                            No
                          </label>
                        </div>
                        {ind.note && (
                          <span
                            style={{
                              fontSize: "0.75rem",
                              color: "#d97706",
                              fontWeight: "500",
                            }}
                          >
                            {ind.note}
                          </span>
                        )}
                        {data.value === "Yes" && (
                          <div className={styles.dynamicListWrapper}>
                            <div className={styles.dynamicListInputRow}>
                              <input
                                type="text"
                                disabled={
                                  isFieldLocked(ind.num) ||
                                  data.items?.length >= ind.maxItems
                                }
                                value={tempListInputs[ind.num] || ""}
                                onChange={(e) =>
                                  setTempListInputs({
                                    ...tempListInputs,
                                    [ind.num]: e.target.value,
                                  })
                                }
                                placeholder={`Enter ${ind.listLabel}`}
                              />
                              <button
                                type="button"
                                className={styles.secondaryBtn}
                                disabled={
                                  isFieldLocked(ind.num) ||
                                  data.items?.length >= ind.maxItems
                                }
                                onClick={() => handleAddListItem(ind.num)}
                              >
                                Add
                              </button>
                            </div>
                            <div>
                              {(data.items || []).map((item, idx) => (
                                <div
                                  key={idx}
                                  className={styles.dynamicListItem}
                                >
                                  <span>
                                    {idx + 1}. {item}
                                  </span>
                                  {!isFieldLocked(ind.num) && (
                                    <button
                                      type="button"
                                      className={styles.removeBtn}
                                      onClick={() =>
                                        handleRemoveListItem(ind.num, idx)
                                      }
                                    >
                                      Remove
                                    </button>
                                  )}
                                </div>
                              ))}
                              {data.items?.length >= ind.maxItems && (
                                <p
                                  style={{
                                    fontSize: "0.6875rem",
                                    color: "#64748b",
                                  }}
                                >
                                  Maximum of {ind.maxItems} items reached.
                                </p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {ind.type === "yes_no_count_list" && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "12px",
                        }}
                      >
                        <div>
                          <label className="inline-flex items-center gap-2 mr-4">
                            <input
                              type="radio"
                              disabled={isFieldLocked(ind.num)}
                              checked={data.value === "Yes"}
                              onChange={() =>
                                updateIndicatorValue(ind.num, "value", "Yes")
                              }
                            />{" "}
                            Yes
                          </label>
                          <label className="inline-flex items-center gap-2">
                            <input
                              type="radio"
                              disabled={isFieldLocked(ind.num)}
                              checked={data.value === "No"}
                              onChange={() =>
                                updateIndicatorValue(ind.num, "value", "No")
                              }
                            />{" "}
                            No
                          </label>
                        </div>
                        {data.value === "Yes" && (
                          <div className={styles.dynamicListWrapper}>
                            <div
                              className={styles.formGroup}
                              style={{
                                maxWidth: "180px",
                                marginBottom: "16px",
                              }}
                            >
                              <label
                                style={{
                                  fontSize: "0.75rem",
                                  fontWeight: "600",
                                  color: "#475569",
                                }}
                              >
                                Registered Startups Count
                              </label>
                              <input
                                type="number"
                                min="0"
                                disabled={isFieldLocked(ind.num)}
                                value={data.count || ""}
                                onChange={(e) =>
                                  updateIndicatorValue(
                                    ind.num,
                                    "count",
                                    e.target.value,
                                  )
                                }
                                placeholder="Total startups"
                              />
                            </div>

                            {/* Slab cards grid */}
                            <div
                              className={styles.slabGrid}
                              style={{ marginBottom: "16px" }}
                            >
                              <div
                                className={`${styles.slabCard} ${parseInt(data.count) > 10 ? styles.highlighted : ""}`}
                              >
                                <span className={styles.slabCardTitle}>
                                  More than 10 startups
                                </span>
                                <span className={styles.slabCardMarks}>
                                  6 Marks
                                </span>
                              </div>
                              <div
                                className={`${styles.slabCard} ${parseInt(data.count) <= 10 && parseInt(data.count) >= 6 ? styles.highlighted : ""}`}
                              >
                                <span className={styles.slabCardTitle}>
                                  6 to 10 startups
                                </span>
                                <span className={styles.slabCardMarks}>
                                  4 Marks
                                </span>
                              </div>
                              <div
                                className={`${styles.slabCard} ${parseInt(data.count) <= 5 && parseInt(data.count) >= 1 ? styles.highlighted : ""}`}
                              >
                                <span className={styles.slabCardTitle}>
                                  1 to 5 startups
                                </span>
                                <span className={styles.slabCardMarks}>
                                  2 Marks
                                </span>
                              </div>
                            </div>

                            <div className={styles.dynamicListInputRow}>
                              <input
                                type="text"
                                disabled={isFieldLocked(ind.num)}
                                value={tempListInputs[ind.num] || ""}
                                onChange={(e) =>
                                  setTempListInputs({
                                    ...tempListInputs,
                                    [ind.num]: e.target.value,
                                  })
                                }
                                placeholder={`Enter ${ind.listLabel}`}
                              />
                              <button
                                type="button"
                                className={styles.secondaryBtn}
                                disabled={isFieldLocked(ind.num)}
                                onClick={() => handleAddListItem(ind.num)}
                              >
                                Add
                              </button>
                            </div>
                            <div>
                              {(data.items || []).map((item, idx) => (
                                <div
                                  key={idx}
                                  className={styles.dynamicListItem}
                                >
                                  <span>
                                    {idx + 1}. {item}
                                  </span>
                                  {!isFieldLocked(ind.num) && (
                                    <button
                                      type="button"
                                      className={styles.removeBtn}
                                      onClick={() =>
                                        handleRemoveListItem(ind.num, idx)
                                      }
                                    >
                                      Remove
                                    </button>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Common Upload and Page No Element */}
                    <div className={styles.commonInputs}>
                      <div className={styles.uploadSlot}>
                        <label
                          style={{
                            fontSize: "0.75rem",
                            fontWeight: "600",
                            color: "#475569",
                          }}
                        >
                          Evidence Document (PDF/Image)
                        </label>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "12px",
                            flexWrap: "wrap",
                            marginTop: "4px",
                          }}
                        >
                          {!isFieldLocked(ind.num) ? (
                            <label
                              className={styles.uploadButtonLabel}
                              style={{ margin: 0 }}
                            >
                              <input
                                type="file"
                                accept=".pdf,image/*"
                                style={{ display: "none" }}
                                onChange={(e) => handleFileUpload(ind.num, e)}
                              />
                              {uploadingIndicator === ind.num
                                ? "Uploading..."
                                : "Choose File"}
                            </label>
                          ) : null}

                          {uploadingIndicator === ind.num && (
                            <span
                              style={{
                                fontSize: "0.8125rem",
                                color: "#64748b",
                              }}
                            >
                              Uploading...
                            </span>
                          )}

                          {data.evidence_url && (
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                              }}
                            >
                              {data.evidence_url.match(
                                /\.(jpeg|jpg|gif|png|webp)$/i,
                              ) && (
                                <img
                                  src={data.evidence_url}
                                  alt="Preview"
                                  style={{
                                    width: "32px",
                                    height: "32px",
                                    borderRadius: "4px",
                                    objectFit: "cover",
                                    border: "1px solid #cbd5e1",
                                  }}
                                />
                              )}
                              <a
                                href={data.evidence_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={styles.uploadedFileLink}
                                style={{ margin: 0 }}
                              >
                                {data.evidence_url.match(
                                  /\.(jpeg|jpg|gif|png|webp)$/i,
                                )
                                  ? "🖼️"
                                  : "📄"}{" "}
                                {evidenceName || "View Evidence Document"}
                              </a>
                              {!isFieldLocked(ind.num) && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    updateIndicatorValue(
                                      ind.num,
                                      "evidence_url",
                                      "",
                                    );
                                    updateIndicatorValue(
                                      ind.num,
                                      "evidence_name",
                                      "",
                                    );
                                  }}
                                  style={{
                                    background: "none",
                                    border: "none",
                                    color: "#ef4444",
                                    cursor: "pointer",
                                    padding: "4px 8px",
                                    fontSize: "0.8125rem",
                                    fontWeight: "600",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "4px",
                                  }}
                                >
                                  ❌ Remove
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className={styles.formGroup}>
                        <label
                          style={{
                            fontSize: "0.75rem",
                            fontWeight: "600",
                            color: "#475569",
                          }}
                        >
                          Doc Page No.
                        </label>
                        <input
                          type="number"
                          disabled={isFieldLocked(ind.num)}
                          min="1"
                          value={pageNo}
                          onChange={(e) =>
                            updateIndicatorValue(
                              ind.num,
                              "page_no",
                              e.target.value,
                            )
                          }
                          placeholder="Page"
                        />
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}

        {/* Section 3: Auto-Generated Document Index */}
        {activeStep === 5 && (
          <section className={styles.cardSection}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "18px",
              }}
            >
              <h3
                className={styles.sectionTitle}
                style={{ border: "none", margin: 0, padding: 0 }}
              >
                Section 3 — Auto-Generated Document Index
              </h3>
              <button
                type="button"
                className={styles.secondaryBtn}
                onClick={() => window.print()}
                style={{ fontSize: "0.8125rem" }}
              >
                Print/Download Index
              </button>
            </div>
            <p
              style={{
                fontSize: "0.8125rem",
                color: "#64748b",
                marginBottom: "18px",
              }}
            >
              This index is dynamically compiled from all indicators where you
              have uploaded evidence. Include this index as the first page of
              your physical submission dossier.
            </p>
            {renderDocumentIndexTable()}
          </section>
        )}

        {/* Section 4: Declaration & Submit */}
        {activeStep === 6 && (
          <section className={styles.cardSection}>
            <h3 className={styles.sectionTitle}>
              Section 5 — Declaration & Submit
            </h3>
            <div className={styles.submitBlock}>
              <div
                style={{
                  backgroundColor: "#f8fafc",
                  padding: "20px",
                  borderRadius: "12px",
                  border: "1px solid #cbd5e1",
                }}
              >
                <p
                  style={{
                    fontSize: "0.875rem",
                    lineHeight: "1.6",
                    fontWeight: "500",
                  }}
                >
                  I hereby declare that the information provided in this
                  nomination form is true, correct, and verified against
                  institutional records. All uploaded evidence documents are
                  authentic and attested copies. I understand that any false
                  declaration will lead to the immediate rejection of the
                  institution's nomination.
                </p>
                <div
                  style={{
                    display: "flex",
                    gap: "16px",
                    marginTop: "16px",
                    borderTop: "1px solid #e2e8f0",
                    paddingTop: "16px",
                    fontSize: "0.8125rem",
                    color: "#475569",
                  }}
                >
                  <div>
                    <span>Authorized Signatory:</span>
                    <strong
                      style={{
                        display: "block",
                        color: "#0f172a",
                        fontSize: "0.9375rem",
                      }}
                    >
                      {basicInfo.head_name || "Head of Institution"}
                    </strong>
                  </div>
                  <div>
                    <span>Designation:</span>
                    <strong
                      style={{
                        display: "block",
                        color: "#0f172a",
                        fontSize: "0.9375rem",
                      }}
                    >
                      Principal / Head of Institute
                    </strong>
                  </div>
                </div>
              </div>

              {!isFormLocked ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                    width: "100%",
                  }}
                >
                  <label
                    className="inline-flex items-center gap-3"
                    style={{
                      fontSize: "0.875rem",
                      cursor: "pointer",
                      fontWeight: "600",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={declarationAccepted}
                      onChange={(e) => setDeclarationAccepted(e.target.checked)}
                      style={{ width: "18px", height: "18px" }}
                    />
                    I accept this declaration and attest the physical copies.
                  </label>
                  <button
                    type="button"
                    className={styles.submitBtn}
                    onClick={handleSubmitNomination}
                    disabled={
                      submitting ||
                      !declarationAccepted ||
                      getIndicatorsCount() < 10 ||
                      !basicInfo.head_name
                    }
                  >
                    {submitting
                      ? "Submitting..."
                      : "Submit Nomination (Lock Form)"}
                  </button>
                  {getIndicatorsCount() < 10 && (
                    <p
                      style={{
                        color: "#ef4444",
                        fontSize: "0.75rem",
                        fontWeight: "600",
                      }}
                    >
                      ⚠️ You must fill out at least 10 indicators to submit
                      (current: {getIndicatorsCount()}).
                    </p>
                  )}
                  {!basicInfo.head_name && (
                    <p
                      style={{
                        color: "#ef4444",
                        fontSize: "0.75rem",
                        fontWeight: "600",
                      }}
                    >
                      ⚠️ Please enter the name of the Head of Institute in
                      Section 1 (Basic Info).
                    </p>
                  )}
                </div>
              ) : (
                <div
                  style={{
                    backgroundColor: "#ecfdf5",
                    border: "1px solid #10b981",
                    padding: "16px",
                    borderRadius: "8px",
                    width: "100%",
                    textAlign: "center",
                  }}
                >
                  <h4
                    style={{
                      color: "#065f46",
                      fontWeight: "700",
                      marginBottom: "4px",
                    }}
                  >
                    Nomination Locked & Submitted
                  </h4>
                  <p style={{ fontSize: "0.8125rem", color: "#047857" }}>
                    This form is now read-only. Submitted on{" "}
                    {nomination?.submitted_at
                      ? new Date(nomination.submitted_at).toLocaleString()
                      : "Date N/A"}
                    .
                  </p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Stepper Navigation buttons */}
        <div className={styles.actionButtonRow}>
          {activeStep > 0 ? (
            <button
              type="button"
              className={styles.secondaryBtn}
              onClick={handlePrevStep}
            >
              Back
            </button>
          ) : (
            <div />
          )}

          <div style={{ display: "flex", gap: "10px" }}>
            {!isFormLocked && (
              <button
                type="button"
                className={styles.secondaryBtn}
                style={{ borderColor: "#10b981", color: "#10b981" }}
                disabled={saving}
                onClick={handleSaveDraft}
              >
                {saving ? "Saving..." : "Save Draft"}
              </button>
            )}
            {activeStep < 6 && (
              <button
                type="button"
                className={styles.submitBtn}
                style={{ boxShadow: "none" }}
                onClick={handleNextStep}
              >
                Next
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}