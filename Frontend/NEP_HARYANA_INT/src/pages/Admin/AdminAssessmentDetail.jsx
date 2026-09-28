import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  FileText, 
  Eye, 
  Save,
  MessageSquare,
  History,
  Calendar,
  Layers,
  Award,
  Building2,
  GraduationCap,
  ShieldCheck,
  RotateCcw,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  UserCheck,
  Clock,
  Sparkles,
  Download,
  AlertTriangle,
  Info,
  Check
} from 'lucide-react';
import { fetchAssessmentReviewDetail, fetchAssessmentScoring } from '../../api/checker';
import { inspectAdminAssessment, assignAdminReviewer, fetchAdminAuthorizations } from '../../api/admin';
import { useAuth } from '../../context/AuthContext.jsx';
import DocumentPreviewModal from '../../components/Institution/DocumentPreviewModal';
import ParameterSubmittedDataViewer from '../../components/Admin/ParameterSubmittedDataViewer';
import { 
  getParameterTitle, 
  COLLEGE_PARAMETER_CODES, 
  UNIVERSITY_PARAMETER_CODES,
  COLLEGE_FRAMEWORK_DATA,
  UNIVERSITY_FRAMEWORK_DATA 
} from '../../utils/nepTaxonomy';

const LIFECYCLE_STATUS_CONFIG = {
  DRAFT: { label: 'Draft', bg: 'bg-slate-100 text-slate-700 border-slate-200' },
  SUBMITTED: { label: 'Submitted', bg: 'bg-blue-50 text-blue-800 border-blue-200' },
  UNDER_REVIEW: { label: 'Under Review', bg: 'bg-amber-50 text-amber-800 border-amber-200' },
  EVALUATED: { label: 'Evaluated', bg: 'bg-indigo-50 text-indigo-800 border-indigo-200' },
  CERTIFICATION_PENDING: { label: 'Pending Certification', bg: 'bg-purple-50 text-purple-800 border-purple-200' },
  CERTIFIED: { label: 'Certified Award', bg: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
  REJECTED: { label: 'Returned / Rejected', bg: 'bg-rose-50 text-rose-800 border-rose-200' },
  BLOCKED_BY_SPECIFICATION: { label: 'Blocked by Spec', bg: 'bg-purple-50 text-purple-800 border-purple-200' }
};

export default function AdminAssessmentDetail() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [assessmentData, setAssessmentData] = useState(null);
  const [scoringData, setScoringData] = useState(null);
  
  // Navigation & Parameter Tabs
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'parameters' | 'evidence' | 'scoring' | 'audit'
  const [selectedParamCode, setSelectedParamCode] = useState(null);

  // Reviewer Assignment State
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assigneeList, setAssigneeList] = useState([]);
  const [selectedReviewerId, setSelectedReviewerId] = useState('');
  const [assignReason, setAssignReason] = useState('');
  const [assignLoading, setAssignLoading] = useState(false);


  // Evidence Preview Modal State
  const [previewModal, setPreviewModal] = useState({
    isOpen: false,
    documentId: '',
    associationId: '',
    filename: '',
    mimeType: ''
  });

  const loadData = useCallback(async () => {
    if (!assessmentId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAssessmentReviewDetail(assessmentId);
      setAssessmentData(data);
      
      const defaultParam = data.framework === 'UNIVERSITY_2026' ? 'U1' : 'C1';
      setSelectedParamCode(prev => prev || defaultParam);

      // Load authoritative backend scoring engine output
      try {
        const scoring = await fetchAssessmentScoring(data.framework, assessmentId);
        setScoringData(scoring);
      } catch (sErr) {
        console.warn("Authoritative scoring not yet computed:", sErr);
      }
    } catch (err) {
      console.error("Failed to load admin assessment inspect data:", err);
      setError(err?.message || "Failed to retrieve assessment inspection data.");
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load Reviewer Authorizations when assignment modal opens
  const openAssignModal = async () => {
    setShowAssignModal(true);
    try {
      const res = await fetchAdminAuthorizations();
      const auths = res?.results || res || [];
      // Filter distinct active reviewers
      const distinctUsers = [];
      const seen = new Set();
      (Array.isArray(auths) ? auths : []).forEach(a => {
        const u = a.user;
        if (u && !seen.has(u.id)) {
          seen.add(u.id);
          distinctUsers.push(u);
        }
      });
      setAssigneeList(distinctUsers);
    } catch (err) {
      console.warn("Could not load reviewer list:", err);
    }
  };

  const handleAssignReviewer = async (e) => {
    e.preventDefault();
    if (!selectedReviewerId) {
      alert("Please select a screening committee reviewer.");
      return;
    }
    setAssignLoading(true);
    try {
      await assignAdminReviewer(assessmentId, Number(selectedReviewerId), assignReason);
      alert("Reviewer successfully assigned to assessment.");
      setShowAssignModal(false);
      setAssignReason('');
      setSelectedReviewerId('');
      loadData();
    } catch (err) {
      alert(`Assignment failed: ${err.message || 'Unknown error'}`);
    } finally {
      setAssignLoading(false);
    }
  };

  const handleOpenDocPreview = (assoc) => {
    if (!assoc) return;
    setPreviewModal({
      isOpen: true,
      documentId: String(assoc.evidence_id || assoc.document_id || ''),
      associationId: String(assoc.association_id || assoc.id || ''),
      filename: assoc.original_filename || 'Evidence File',
      mimeType: assoc.mime_type || ''
    });
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-28 space-y-4">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-[#600b0b] rounded-full animate-spin" />
        <p className="text-xs text-slate-500 font-bold uppercase tracking-wider animate-pulse">
          Loading Detailed Admin Application Dossier...
        </p>
      </div>
    );
  }

  if (error || !assessmentData) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4 max-w-lg mx-auto text-center">
        <div className="p-4 bg-rose-50 text-rose-600 rounded-full border border-rose-200">
          <AlertCircle className="w-10 h-10" />
        </div>
        <h2 className="text-lg font-bold text-slate-800">Unable to Load Assessment Dossier</h2>
        <p className="text-xs text-slate-500">{error || "Assessment not found or access denied."}</p>
        <div className="flex items-center gap-3 pt-2">
          <button 
            onClick={() => navigate('/admin/institutions')} 
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-colors"
          >
            Back to Dashboard
          </button>
          <button 
            onClick={loadData} 
            className="px-4 py-2 bg-[#600b0b] hover:bg-[#4a0808] text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  const {
    institution = {},
    framework,
    academic_year,
    status = 'DRAFT',
    assigned_reviewer,
    parameter_data = {},
    evidence_associations = [],
    evidence_readiness = {},
    scoring = {},
    review_history = [],
    audit_trail = [],
    certification_eligibility = {}
  } = assessmentData;

  const statusConfig = LIFECYCLE_STATUS_CONFIG[status] || LIFECYCLE_STATUS_CONFIG.DRAFT;
  const isCollege = framework === 'COLLEGE_2026';
  const paramCodes = isCollege ? COLLEGE_PARAMETER_CODES : UNIVERSITY_PARAMETER_CODES;

  // Active parameter submitted data
  const currentParamData = parameter_data[selectedParamCode] || {};
  const currentParamAssocs = evidence_associations.filter(a => a.parameter_id === selectedParamCode);

  // Score summary
  const certifiedScore = scoring?.certified_score ?? scoringData?.certified_score ?? null;
  const rawTotalScore = scoringData?.raw_total_score ?? null;
  const awardCategory = scoringData?.award_level || (certifiedScore !== null ? (certifiedScore >= 85 ? 'Platinum' : certifiedScore >= 70 ? 'Gold' : certifiedScore >= 55 ? 'Silver' : 'Bronze') : 'Under Evaluation');

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Top Breadcrumbs & Action Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center space-x-3">
          <button 
            onClick={() => navigate('/admin/institutions')}
            className="p-2 bg-white rounded-xl border border-[#ebdcd0] text-slate-600 hover:text-[#600b0b] hover:border-[#c29b68] hover:bg-[#fbf5ee] transition-all cursor-pointer shadow-xs"
            title="Back to Admin Dashboard"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-[#600b0b] uppercase tracking-widest bg-[#eaded2]/60 px-2 py-0.5 rounded-md border border-[#ebdcd0]">
                Admin Evaluation Desk
              </span>
              <span className="text-[10px] font-mono text-slate-400 font-bold">{assessmentId}</span>
            </div>
            <h1 className="text-xl font-bold text-slate-800 tracking-tight mt-0.5">
              Comprehensive Institutional Dossier
            </h1>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={openAssignModal}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold transition-all shadow-xs"
          >
            <UserCheck className="w-4 h-4 text-[#600b0b]" />
            <span>{assigned_reviewer ? 'Reassign Reviewer' : 'Assign Reviewer'}</span>
          </button>

          {/* Quick link to Screening Committee Review console */}
          <Link
            to={`/checker/assessment/${assessmentId}`}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#fbf5ee] hover:bg-[#eaded2] text-[#600b0b] border border-[#ebdcd0] rounded-xl text-xs font-bold transition-all shadow-xs"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Screening Console</span>
          </Link>

          {/* Certification is the Committee Chair's decision; the State Admin only monitors it here. */}
        </div>
      </div>

      {/* Main Institutional Header Card */}
      <div className="bg-white rounded-2xl border border-[#ebdcd0] shadow-xs p-6 relative overflow-hidden">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-md border bg-[#eaded2]/60 border-[#ebdcd0] text-[#600b0b]">
                {framework === 'UNIVERSITY_2026' ? 'State University' : 'Affiliated College'}
              </span>
              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-md border ${statusConfig.bg}`}>
                {statusConfig.label}
              </span>
              <span className="text-[10px] bg-slate-50 border border-slate-200 text-slate-500 font-bold px-2.5 py-0.5 rounded-md">
                Academic Session {academic_year || '2025–2026'}
              </span>
            </div>

            <div>
              <h2 className="text-xl font-extrabold text-slate-800 leading-tight">
                {institution.name || 'Institutional Assessment'}
              </h2>
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 mt-1">
                <span>AISHE Code: <strong className="font-mono text-slate-700">{institution.aishe_code || 'N/A'}</strong></span>
                {institution.district && <span>District: <strong className="text-slate-700">{institution.district}</strong></span>}
                <span>Assigned Reviewer: <strong className="text-slate-700">{assigned_reviewer?.full_name || 'Unassigned'}</strong></span>
              </div>
            </div>
          </div>

          {/* Quick Score Snapshot */}
          <div className="flex items-center space-x-6 shrink-0 bg-[#fdfaf6] border border-[#ebdcd0] p-4 rounded-2xl">
            <div className="text-center border-r border-[#ebdcd0] pr-6">
              <span className="block text-[10px] text-slate-400 font-bold uppercase tracking-wider">Certified Score</span>
              <span className="block text-3xl font-black text-slate-800 mt-0.5">
                {certifiedScore !== null ? certifiedScore : '—'}
                <span className="text-xs text-slate-400 font-bold">/100</span>
              </span>
            </div>
            <div className="text-center">
              <span className="block text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1.5">Award Tier</span>
              <span className="text-xs font-black tracking-wide px-3 py-1.5 rounded-full border bg-amber-50 text-amber-800 border-amber-300">
                {awardCategory}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 bg-white px-4 rounded-2xl border shadow-xs overflow-x-auto">
        {[
          { id: 'overview', label: 'Overview & Readiness', icon: Building2 },
          { id: 'parameters', label: `Submitted Parameters (${paramCodes.length})`, icon: Layers },
          { id: 'evidence', label: `Evidence Repository (${evidence_associations.length})`, icon: ShieldCheck },
          { id: 'scoring', label: 'Authoritative Scoring Ledger', icon: Award },
          { id: 'audit', label: `Audit & History (${audit_trail.length + review_history.length})`, icon: History },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 py-4 px-4 text-xs font-bold uppercase tracking-wider border-b-2 transition-all cursor-pointer whitespace-nowrap ${
                isActive
                  ? 'border-[#600b0b] text-[#600b0b] bg-[#fbf5ee]/50'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-[#600b0b]' : 'text-slate-400'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT: 1. OVERVIEW & READINESS */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Institutional Context */}
          <div className="bg-white p-6 rounded-2xl border border-[#ebdcd0] shadow-xs space-y-4 lg:col-span-2">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-[#600b0b]" />
                <h3 className="text-sm font-bold text-slate-800">Administrative Profile & Scope</h3>
              </div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest font-mono">
                FRAMEWORK: {framework}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">Affiliation / Entity</span>
                <p className="text-xs font-bold text-slate-700">{institution.name}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">AISHE: {institution.aishe_code}</p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">Assigned Evaluator</span>
                <p className="text-xs font-bold text-slate-700">
                  {assigned_reviewer ? assigned_reviewer.full_name : 'No Reviewer Assigned'}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {assigned_reviewer ? assigned_reviewer.email : 'Pending admin assignment'}
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">Statutory Cycle</span>
                <p className="text-xs font-bold text-slate-700">Academic Year {academic_year}</p>
                <p className="text-[11px] text-emerald-600 font-bold mt-0.5">Statutory Window Active</p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">Evidence Status</span>
                <p className="text-xs font-bold text-slate-700">
                  {evidence_readiness.is_ready ? 'All Criteria Covered' : 'Missing/Pending Evidence'}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {evidence_associations.length} Attached Artifacts
                </p>
              </div>
            </div>

            {/* Certification Eligibility Status */}
            <div className="pt-2">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Certification Eligibility Gates</h4>
              <div className={`p-4 rounded-xl border ${
                certification_eligibility.is_eligible 
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800' 
                  : 'bg-amber-50 border-amber-200 text-amber-800'
              }`}>
                <div className="flex items-center gap-2 font-bold text-xs">
                  {certification_eligibility.is_eligible ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                  )}
                  <span>
                    {certification_eligibility.is_eligible 
                      ? "All statutory gates verified — application is eligible for Council Certification." 
                      : "Certification is currently gated pending resolution of requirements below:"}
                  </span>
                </div>
                {certification_eligibility.blocking_reasons?.length > 0 && (
                  <ul className="mt-2 text-xs list-disc list-inside space-y-1 pl-1 font-medium">
                    {certification_eligibility.blocking_reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>

          {/* Quick Metrics & Gating */}
          <div className="bg-white p-6 rounded-2xl border border-[#ebdcd0] shadow-xs space-y-5">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <ShieldCheck className="w-5 h-5 text-[#600b0b]" />
              <h3 className="text-sm font-bold text-slate-800">Verification Readiness</h3>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 rounded-xl bg-slate-50">
                <span className="text-xs font-bold text-slate-600">Total Uploaded Artifacts</span>
                <span className="text-xs font-black text-slate-800 font-mono">{evidence_associations.length}</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-xl bg-emerald-50/70 text-emerald-800">
                <span className="text-xs font-bold">Verified Subcriteria</span>
                <span className="text-xs font-black font-mono">
                  {evidence_associations.filter(a => a.verification_status === 'VERIFIED').length}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-xl bg-amber-50/70 text-amber-800">
                <span className="text-xs font-bold">Pending Review</span>
                <span className="text-xs font-black font-mono">
                  {evidence_associations.filter(a => !a.verification_status || a.verification_status === 'PENDING').length}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-xl bg-rose-50/70 text-rose-800">
                <span className="text-xs font-bold">Rejected Evidence</span>
                <span className="text-xs font-black font-mono">
                  {evidence_associations.filter(a => a.verification_status === 'REJECTED').length}
                </span>
              </div>
            </div>

            <div className="pt-2">
              <button
                onClick={() => setActiveTab('parameters')}
                className="w-full py-2.5 bg-[#fbf5ee] hover:bg-[#eaded2] text-[#600b0b] font-bold text-xs rounded-xl border border-[#ebdcd0] transition-colors flex items-center justify-center gap-1.5"
              >
                <span>Inspect Parameter Inputs</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 2. SUBMITTED PARAMETERS */}
      {activeTab === 'parameters' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Parameter Selector */}
          <div className="bg-white p-4 rounded-2xl border border-[#ebdcd0] shadow-xs space-y-2 h-fit max-h-[750px] overflow-y-auto">
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 px-2 mb-2">
              Statutory Parameters
            </h3>
            {paramCodes.map(code => {
              const isSelected = selectedParamCode === code;
              const hasData = parameter_data[code] !== undefined;
              const title = getParameterTitle(code);
              const assocs = evidence_associations.filter(a => a.parameter_id === code);

              return (
                <button
                  key={code}
                  onClick={() => setSelectedParamCode(code)}
                  className={`w-full text-left p-3 rounded-xl transition-all border flex items-start justify-between gap-2 ${
                    isSelected
                      ? 'bg-[#600b0b] text-white border-[#600b0b] shadow-xs'
                      : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-100'
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${
                        isSelected ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-700'
                      }`}>
                        {code}
                      </span>
                      {hasData && (
                        <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded-full ${
                          isSelected ? 'bg-emerald-500/30 text-emerald-200' : 'bg-emerald-50 text-emerald-700'
                        }`}>
                          Submitted
                        </span>
                      )}
                    </div>
                    <p className={`text-xs font-semibold line-clamp-1 ${isSelected ? 'text-white' : 'text-slate-800'}`}>
                      {title}
                    </p>
                  </div>
                  {assocs.length > 0 && (
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ${
                      isSelected ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-500'
                    }`}>
                      {assocs.length} doc{assocs.length > 1 ? 's' : ''}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Right Parameter Detailed View */}
          <div className="bg-white p-6 rounded-2xl border border-[#ebdcd0] shadow-xs lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-black px-2 py-0.5 rounded bg-[#eaded2] text-[#600b0b]">
                    {selectedParamCode}
                  </span>
                  <h3 className="text-base font-bold text-slate-800">
                    {getParameterTitle(selectedParamCode)}
                  </h3>
                </div>
              </div>
            </div>

            {/* Submitted Values Display with Human-Readable Formatter */}
            <div className="space-y-4">
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Submitted Institutional Data & Subcriteria
              </h4>

              <ParameterSubmittedDataViewer
                parameterCode={selectedParamCode}
                framework={framework}
                submittedData={currentParamData}
              />
            </div>

            {/* Attached Documentary Evidence for Selected Parameter */}
            <div className="space-y-3 pt-4 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Documentary Evidence ({currentParamAssocs.length})
                </h4>
                {currentParamAssocs.length > 0 && (
                  <span className="text-[10px] text-slate-400 font-medium">
                    {currentParamAssocs.length} verified/provisional proof artifact{currentParamAssocs.length > 1 ? 's' : ''}
                  </span>
                )}
              </div>

              {currentParamAssocs.length === 0 ? (
                <div className="p-6 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  <FileText className="w-7 h-7 text-slate-300 mx-auto mb-1.5" />
                  <p className="text-xs text-slate-500 font-bold">
                    No supporting documents uploaded for this parameter.
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Subcriteria evaluated based on statutory declarations or non-mandatory requirements.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {currentParamAssocs.map(assoc => {
                    const isVerified = assoc.verification_status === 'VERIFIED';
                    const isRejected = assoc.verification_status === 'REJECTED';
                    const uploadDate = assoc.associated_at ? new Date(assoc.associated_at).toLocaleDateString('en-IN', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric'
                    }) : 'Uploaded';

                    return (
                      <div 
                        key={assoc.association_id || assoc.id}
                        className="p-4 rounded-xl border border-slate-200/90 bg-white flex flex-col justify-between gap-3.5 hover:border-[#c29b68] hover:shadow-xs transition-all"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="text-[10px] font-black px-2 py-0.5 rounded bg-blue-50 text-blue-800 font-mono border border-blue-200/60">
                              {assoc.subcriterion_id || selectedParamCode}
                            </span>
                            <span className={`text-[9px] font-black px-2 py-0.5 rounded-full uppercase border ${
                              isVerified ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                              isRejected ? 'bg-rose-50 text-rose-800 border-rose-200' :
                              'bg-amber-50 text-amber-800 border-amber-200'
                            }`}>
                              {assoc.verification_status || 'PENDING'}
                            </span>
                          </div>

                          <div className="flex items-start gap-2.5">
                            <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 text-slate-600 shrink-0">
                              <FileText className="w-4 h-4 text-[#600b0b]" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-bold text-slate-800 truncate" title={assoc.original_filename}>
                                {assoc.original_filename}
                              </p>
                              <p className="text-[10px] text-slate-400 font-medium mt-0.5">
                                {assoc.mime_type ? assoc.mime_type.split('/')[1]?.toUpperCase() : 'PDF'} · {uploadDate}
                                {assoc.file_size ? ` · ${Math.round(assoc.file_size / 1024)} KB` : ''}
                              </p>
                            </div>
                          </div>

                          {assoc.claim_description && (
                            <p className="text-[11px] text-slate-600 line-clamp-2 mt-2 bg-slate-50 p-2 rounded-lg border border-slate-100">
                              {assoc.claim_description}
                            </p>
                          )}
                        </div>

                        <div className="flex items-center justify-between border-t border-slate-100 pt-2.5">
                          <span className="text-[10px] text-slate-400 font-mono">
                            {assoc.page_start ? `pp. ${assoc.page_start}–${assoc.page_end || assoc.page_start}` : 'Complete Artifact'}
                          </span>
                          <button
                            onClick={() => handleOpenDocPreview(assoc)}
                            className="inline-flex items-center gap-1 text-xs font-bold text-[#600b0b] hover:text-[#4a0808] hover:underline cursor-pointer bg-[#fbf5ee] px-2.5 py-1 rounded-lg border border-[#ebdcd0] transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>View Document</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 3. EVIDENCE REPOSITORY */}
      {activeTab === 'evidence' && (
        <div className="bg-white p-6 rounded-2xl border border-[#ebdcd0] shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-800">Master Evidence Ledger</h3>
            <span className="text-xs font-bold text-slate-500 font-mono">
              Total Uploads: {evidence_associations.length}
            </span>
          </div>

          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Parameter / Subcriterion</th>
                  <th className="px-4 py-3">Document Title</th>
                  <th className="px-4 py-3">Pages / Section</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {evidence_associations.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-10 text-slate-400 font-bold uppercase text-xs">
                      No documentary evidence submitted for this assessment.
                    </td>
                  </tr>
                ) : (
                  evidence_associations.map(assoc => (
                    <tr key={assoc.association_id || assoc.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded text-[11px]">
                          {assoc.subcriterion_id || assoc.parameter_id}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-800 max-w-xs truncate">
                        {assoc.original_filename}
                      </td>
                      <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                        {assoc.page_start ? `pp. ${assoc.page_start}–${assoc.page_end || assoc.page_start}` : assoc.section_identifier || 'Entire Doc'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase ${
                          assoc.verification_status === 'VERIFIED' ? 'bg-emerald-100 text-emerald-800' :
                          assoc.verification_status === 'REJECTED' ? 'bg-rose-100 text-rose-800' :
                          'bg-amber-100 text-amber-800'
                        }`}>
                          {assoc.verification_status || 'PENDING'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleOpenDocPreview(assoc)}
                          className="px-3 py-1.5 bg-[#fbf5ee] hover:bg-[#eaded2] text-[#600b0b] font-bold text-xs rounded-lg transition-colors inline-flex items-center gap-1 cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 4. SCORING LEDGER */}
      {activeTab === 'scoring' && (
        <div className="bg-white p-6 rounded-2xl border border-[#ebdcd0] shadow-xs space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-800">Authoritative Frozen Scoring Ledger</h3>
              <p className="text-xs text-slate-500">
                Server-side evaluated scores with statutory evidence gating rules.
              </p>
            </div>
            <div className="text-right">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Certified</span>
              <span className="text-xl font-black text-slate-800 font-mono">
                {certifiedScore !== null ? certifiedScore : '—'}/100
              </span>
            </div>
          </div>

          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 w-20">Code</th>
                  <th className="px-4 py-3">Parameter Name</th>
                  <th className="px-4 py-3 text-center w-24">Max Score</th>
                  <th className="px-4 py-3 text-center w-24">Gated Score</th>
                  <th className="px-4 py-3 text-center w-32">Gating Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {paramCodes.map(code => {
                  const paramRes = scoringData?.parameter_results?.[code] || {};
                  const title = getParameterTitle(code);
                  const maxPts = isCollege ? (COLLEGE_FRAMEWORK_DATA?.[code]?.max_score || 5) : 5;
                  const score = paramRes.gated_score ?? paramRes.score ?? '—';
                  const gating = paramRes.gating_status || (score > 0 ? 'PASSED' : 'PENDING');

                  return (
                    <tr key={code} className="hover:bg-slate-50/60">
                      <td className="px-4 py-3 font-mono font-bold text-[#600b0b]">{code}</td>
                      <td className="px-4 py-3 font-medium text-slate-800">{title}</td>
                      <td className="px-4 py-3 text-center font-semibold text-slate-500">{maxPts}</td>
                      <td className="px-4 py-3 text-center font-bold text-slate-800 font-mono">{score}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase ${
                          gating === 'PASSED' || gating === 'VERIFIED' ? 'bg-emerald-50 text-emerald-700' :
                          gating === 'FAILED' ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {gating}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 5. AUDIT TRAIL */}
      {activeTab === 'audit' && (
        <div className="bg-white p-6 rounded-2xl border border-[#ebdcd0] shadow-xs space-y-6">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <History className="w-5 h-5 text-[#600b0b]" />
            <h3 className="text-sm font-bold text-slate-800">Immutable Audit Trail & Lifecycle History</h3>
          </div>

          <div className="flow-root">
            <ul className="-mb-8">
              {[...review_history, ...audit_trail].map((hist, idx) => (
                <li key={idx}>
                  <div className="relative pb-8">
                    {idx !== (review_history.length + audit_trail.length) - 1 && (
                      <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-slate-100" aria-hidden="true" />
                    )}
                    <div className="relative flex space-x-3">
                      <span className="h-8 w-8 rounded-full bg-[#fbf5ee] border border-[#ebdcd0] flex items-center justify-center text-[#600b0b] font-bold ring-4 ring-white">
                        <Clock className="w-3.5 h-3.5" />
                      </span>
                      <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                        <div>
                          <p className="text-xs font-bold text-slate-700">
                            {hist.action || hist.new_status || 'Status Transition'}
                          </p>
                          <p className="text-[11px] text-slate-500 mt-0.5">
                            Actor: <strong>{hist.actor || hist.reviewer_name || 'Admin User'}</strong> {hist.actor_email && `(${hist.actor_email})`}
                          </p>
                          {hist.reason && <p className="text-[11px] text-slate-600 italic mt-1 bg-slate-50 p-2 rounded">Reason: {hist.reason}</p>}
                        </div>
                        <div className="text-right text-[10px] font-mono text-slate-400 whitespace-nowrap">
                          {hist.timestamp ? new Date(hist.timestamp).toLocaleString() : 'Recent'}
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Reviewer Assignment Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-800">Assign Screening Reviewer</h3>
              <button onClick={() => setShowAssignModal(false)} className="text-slate-400 hover:text-slate-600">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAssignReviewer} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1.5">Select Committee Reviewer</label>
                <select
                  value={selectedReviewerId}
                  onChange={(e) => setSelectedReviewerId(e.target.value)}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 focus:outline-none focus:border-[#600b0b]"
                  required
                >
                  <option value="">Select a reviewer...</option>
                  {assigneeList.map(u => (
                    <option key={u.id} value={u.id}>
                      {u.full_name || u.email} ({u.email})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1.5">Assignment Reason / Notes</label>
                <textarea
                  rows="3"
                  value={assignReason}
                  onChange={(e) => setAssignReason(e.target.value)}
                  placeholder="Provide reason for assignment or reassignment..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 focus:outline-none focus:border-[#600b0b]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAssignModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={assignLoading}
                  className="px-4 py-2 bg-[#600b0b] hover:bg-[#4a0808] text-white font-bold text-xs rounded-xl transition-all disabled:opacity-50"
                >
                  {assignLoading ? 'Assigning...' : 'Confirm Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Embedded Document Preview Modal */}
      <DocumentPreviewModal
        isOpen={previewModal.isOpen}
        onClose={() => setPreviewModal(prev => ({ ...prev, isOpen: false }))}
        documentId={previewModal.documentId}
        associationId={previewModal.associationId}
        documentName={previewModal.filename}
        mimeType={previewModal.mimeType}
      />
    </div>
  );
}
