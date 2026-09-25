import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import {
  COLLEGE_PARAMETER_CODES,
  COLLEGE_PARAMETER_TITLES,
  COLLEGE_FRAMEWORK_DATA,
} from "../../utils/nepTaxonomy.js";
import {
  fetchCollegeAssessmentDetail,
  fetchCollegeAssessmentParameters,
  updateCollegeAssessmentParameter,
  submitCollegeAssessment,
} from "../../api/college";
import {
  fetchAssessmentEvidenceAssociations,
  fetchAssessmentEvidenceDocuments,
} from "../../api/evidence";
import AssessmentStepperSidebar from "../../components/Institution/AssessmentStepperSidebar";
import AssessmentOverviewView from "../../components/Institution/AssessmentOverviewView";
import ParameterFormView from "../../components/Institution/ParameterFormView";
import ReviewSubmitView from "../../components/Institution/ReviewSubmitView";
import EvidenceUploadModal from "../../components/Institution/EvidenceUploadModal";
import { DashboardSkeleton, ErrorState } from "../../components/common";
import { Menu, ShieldCheck } from "lucide-react";
import hshecLogo from "../../assets/hshec_logo.jpeg";

export default function CollegeAssessmentWorkspace() {
  const { institutionName, institutionAisheCode, assessmentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  // Navigation State
  const [activeStep, setActiveStep] = useState("overview"); // 'overview' | 'C1'..'C22' | 'review'
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Data State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [parametersMap, setParametersMap] = useState({});
  const [evidenceAssociations, setEvidenceAssociations] = useState([]);
  const [existingDocs, setExistingDocs] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  // Modal State for Evidence Upload
  const [evidenceModal, setEvidenceModal] = useState({
    isOpen: false,
    parameterCode: "",
    subcriterionCode: "",
    subcriterionTitle: "",
    mandatoryEvidenceType: "",
  });

  // Calculate status for each parameter from saved inputs
  const computeParameterStatus = (code, paramDetail) => {
    const raw = paramDetail?.submitted_input?.raw_inputs || paramDetail?.submitted_input || {};
    const def = COLLEGE_FRAMEWORK_DATA[code];
    if (!def) return "NOT_STARTED";

    const subcriteria = def.subcriteria || [];
    if (subcriteria.length === 0) return "NOT_STARTED";

    const hasAny = Object.keys(raw).some((subCode) => {
      const vals = raw[subCode];
      return vals && Object.values(vals).some((v) => v !== "" && v !== null && v !== undefined);
    });

    if (!hasAny) return "NOT_STARTED";

    const allComplete = subcriteria.every((sub) => {
      const vals = raw[sub.code];
      if (!vals || typeof vals !== "object") return false;
      const fields = sub.fields || [];
      return (
        fields.length > 0 &&
        fields.every((f) => vals[f.key] !== undefined && vals[f.key] !== "" && vals[f.key] !== null)
      );
    });

    return allComplete ? "COMPLETE" : "IN_PROGRESS";
  };

  const loadWorkspaceData = useCallback(async () => {
    if (!assessmentId) return;
    setLoading(true);
    setError(null);
    try {
      // Parallel fetch of assessment detail, parameters list, and evidence associations
      const [detailRes, paramsRes, assocsRes, docsRes] = await Promise.all([
        fetchCollegeAssessmentDetail(assessmentId).catch((err) => {
          throw new Error("Unable to load College assessment session: " + err.message);
        }),
        fetchCollegeAssessmentParameters(assessmentId).catch(() => []),
        fetchAssessmentEvidenceAssociations(assessmentId).catch(() => []),
        fetchAssessmentEvidenceDocuments(assessmentId).catch(() => []),
      ]);

      setAssessment(detailRes);

      // Build parameters map keyed by C1..C22
      const pMap = {};
      const paramsList = Array.isArray(paramsRes) ? paramsRes : paramsRes?.results || [];
      paramsList.forEach((p) => {
        pMap[p.parameter_code] = p;
      });
      setParametersMap(pMap);

      const assocsList = Array.isArray(assocsRes) ? assocsRes : assocsRes?.results || [];
      setEvidenceAssociations(assocsList);

      const docsList = Array.isArray(docsRes) ? docsRes : docsRes?.results || [];
      setExistingDocs(docsList);
    } catch (err) {
      console.error("College Assessment Workspace load error:", err);
      setError(err?.message || "Failed to load College Assessment session.");
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    loadWorkspaceData();
  }, [loadWorkspaceData]);

  // Derived parameter status map for all 22 College parameters
  const parameterStatusMap = {};
  COLLEGE_PARAMETER_CODES.forEach((code) => {
    parameterStatusMap[code] = computeParameterStatus(code, parametersMap[code]);
  });

  // Action: Save Parameter Draft
  const handleSaveParameterDraft = async (parameterCode, formData) => {
    await updateCollegeAssessmentParameter(assessmentId, parameterCode, {
      raw_inputs: formData,
    });

    // Update local state smoothly
    setParametersMap((prev) => ({
      ...prev,
      [parameterCode]: {
        ...(prev[parameterCode] || {}),
        parameter_code: parameterCode,
        submitted_input: { raw_inputs: formData },
      },
    }));
  };

  // Action: Open Evidence Attachment Modal
  const handleOpenEvidenceModal = (subcriterionCode, mandatoryEvidenceType) => {
    const pCode = activeStep;
    const def = COLLEGE_FRAMEWORK_DATA[pCode];
    const sub = def?.subcriteria?.find((s) => s.code === subcriterionCode);
    const resolvedType = mandatoryEvidenceType || sub?.canonicalEvidenceType || "";

    setEvidenceModal({
      isOpen: true,
      parameterCode: pCode,
      subcriterionCode: subcriterionCode,
      subcriterionTitle: sub?.title || "",
      mandatoryEvidenceType: resolvedType,
    });
  };

  // Action: Evidence Uploaded/Associated
  const handleEvidenceSuccess = async () => {
    try {
      const [assocsRes, docsRes] = await Promise.all([
        fetchAssessmentEvidenceAssociations(assessmentId),
        fetchAssessmentEvidenceDocuments(assessmentId),
      ]);
      setEvidenceAssociations(Array.isArray(assocsRes) ? assocsRes : assocsRes?.results || []);
      setExistingDocs(Array.isArray(docsRes) ? docsRes : docsRes?.results || []);
    } catch (err) {
      console.warn("Evidence refresh failed:", err);
    }
  };

  // Action: Submit College Assessment
  const handleSubmitAssessment = async () => {
    setSubmitting(true);
    try {
      const res = await submitCollegeAssessment(assessmentId);
      setAssessment((prev) => ({
        ...prev,
        status: "SUBMITTED",
        submitted_at: res?.submitted_at || new Date().toISOString(),
      }));
    } finally {
      setSubmitting(false);
    }
  };

  // Stepper Next / Prev Navigation
  const handlePrevParam = () => {
    const idx = COLLEGE_PARAMETER_CODES.indexOf(activeStep);
    if (idx > 0) {
      setActiveStep(COLLEGE_PARAMETER_CODES[idx - 1]);
    } else {
      setActiveStep("overview");
    }
  };

  const handleNextParam = () => {
    const idx = COLLEGE_PARAMETER_CODES.indexOf(activeStep);
    if (idx >= 0 && idx < COLLEGE_PARAMETER_CODES.length - 1) {
      setActiveStep(COLLEGE_PARAMETER_CODES[idx + 1]);
    } else {
      setActiveStep("review");
    }
  };

  const handleBackToDashboard = () => {
    const cSlug = institutionName || "college";
    const aSlug = institutionAisheCode || "code";
    navigate(`/institution/${cSlug}/${aSlug}/dashboard`);
  };

  if (loading && !assessment) {
    return (
      <div className="min-h-screen bg-slate-50 p-8 max-w-6xl mx-auto">
        <DashboardSkeleton />
      </div>
    );
  }

  if (error && !assessment) {
    return (
      <div className="min-h-screen bg-slate-50 p-8 max-w-4xl mx-auto">
        <ErrorState
          title="College Assessment Session Error"
          message={error}
          onRetry={loadWorkspaceData}
        />
        <div className="mt-4 text-center">
          <button
            onClick={handleBackToDashboard}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-bold"
          >
            Return to College Dashboard
          </button>
        </div>
      </div>
    );
  }

  const isReadOnly = assessment?.status === "SUBMITTED";

  return (
    <div className="min-h-screen bg-slate-50 flex font-sans antialiased text-slate-800">
      {/* College Stepper Sidebar (Strictly C1–C22) */}
      <AssessmentStepperSidebar
        framework="COLLEGE_2026"
        institutionName={user?.college_name || "College Self-Appraisal"}
        assessmentId={assessmentId}
        parameterCodes={COLLEGE_PARAMETER_CODES}
        parameterTitles={COLLEGE_PARAMETER_TITLES}
        parameterStatusMap={parameterStatusMap}
        activeStep={activeStep}
        onSelectStep={setActiveStep}
        onBackToDashboard={handleBackToDashboard}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        status={assessment?.status || "DRAFT"}
      />

      {/* Main Workspace Body */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Mobile Top Header */}
        <header className="lg:hidden h-14 bg-white border-b border-slate-200 px-4 flex items-center justify-between shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-slate-600 hover:text-slate-900 p-1"
          >
            <Menu size={20} />
          </button>
          <span className="font-bold text-xs text-slate-800">
            College Assessment ({activeStep.toUpperCase()})
          </span>
          <span className="text-[10px] font-mono font-bold bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-200">
            C1–C22
          </span>
        </header>

        {/* Content View Container */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-6xl w-full mx-auto space-y-6">
          {/* VIEW 1: OVERVIEW */}
          {activeStep === "overview" && (
            <AssessmentOverviewView
              framework="COLLEGE_2026"
              assessment={assessment || {}}
              parameterCodes={COLLEGE_PARAMETER_CODES}
              parameterTitles={COLLEGE_PARAMETER_TITLES}
              parameterStatusMap={parameterStatusMap}
              evidenceAssociations={evidenceAssociations}
              onNavigateToParam={(code) => setActiveStep(code)}
              onNavigateToReview={() => setActiveStep("review")}
            />
          )}

          {/* VIEW 2: PARAMETER INPUT FORM (C1..C22) */}
          {COLLEGE_PARAMETER_CODES.includes(activeStep) && (
            <ParameterFormView
              key={activeStep}
              framework="COLLEGE_2026"
              parameterCode={activeStep}
              parameterDef={COLLEGE_FRAMEWORK_DATA[activeStep]}
              parameterDetail={parametersMap[activeStep] || {}}
              evidenceAssociations={evidenceAssociations}
              isReadOnly={isReadOnly}
              onSaveDraft={handleSaveParameterDraft}
              onOpenEvidenceModal={handleOpenEvidenceModal}
              onPrevParam={handlePrevParam}
              onNextParam={handleNextParam}
              isFirst={activeStep === COLLEGE_PARAMETER_CODES[0]}
              isLast={activeStep === COLLEGE_PARAMETER_CODES[COLLEGE_PARAMETER_CODES.length - 1]}
            />
          )}

          {/* VIEW 3: REVIEW & SUBMIT */}
          {activeStep === "review" && (
            <ReviewSubmitView
              framework="COLLEGE_2026"
              assessment={assessment || {}}
              parameterCodes={COLLEGE_PARAMETER_CODES}
              parameterDefs={COLLEGE_FRAMEWORK_DATA}
              parameterStatusMap={parameterStatusMap}
              rawInputsMap={parametersMap}
              evidenceAssociations={evidenceAssociations}
              onNavigateToParam={(code) => setActiveStep(code)}
              onSubmitAssessment={handleSubmitAssessment}
              submitting={submitting}
            />
          )}
        </main>
      </div>

      {/* Evidence Upload / Link Modal */}
      <EvidenceUploadModal
        isOpen={evidenceModal.isOpen}
        onClose={() => setEvidenceModal((prev) => ({ ...prev, isOpen: false }))}
        assessmentId={assessmentId}
        framework="COLLEGE_2026"
        institutionType="COLLEGE"
        parameterCode={evidenceModal.parameterCode}
        subcriterionCode={evidenceModal.subcriterionCode}
        subcriterionTitle={evidenceModal.subcriterionTitle}
        mandatoryEvidenceType={evidenceModal.mandatoryEvidenceType}
        existingDocuments={existingDocs}
        onSuccess={handleEvidenceSuccess}
      />
    </div>
  );
}
