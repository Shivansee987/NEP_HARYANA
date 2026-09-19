/**
 * NEP Excellence Awards 2026 — Master Reports & Analytics (Phase 9)
 *
 * Read-only projection of authoritative assessment data across UNIVERSITY_2026 and COLLEGE_2026 frameworks.
 * Consumes /api/v1/reports/ endpoints.
 * Strictly adheres to server-authoritative scoring: NO client-side score calculations, NO P1–P20 legacy mappings.
 */
import { useState, useEffect, useCallback } from 'react';
import { 
  Download, 
  Search, 
  Filter, 
  FileSpreadsheet, 
  FileText, 
  RotateCcw,
  SlidersHorizontal,
  Building2,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldCheck,
  Award,
  Layers,
  Eye,
  X,
  ExternalLink,
  ChevronRight,
  AlertTriangle,
  History,
  Activity
} from 'lucide-react';
import { 
  fetchAdminReportingSummary, 
  downloadAssessmentReportCSV 
} from '../../api/reports';
import AssessmentReportModal from '../../components/Reports/AssessmentReportModal';

const LIFECYCLE_BADGES = {
  DRAFT: { bg: 'bg-slate-50 border-slate-200 text-slate-600', label: 'Draft' },
  SUBMITTED: { bg: 'bg-blue-50 border-blue-200 text-blue-700', label: 'Submitted' },
  UNDER_REVIEW: { bg: 'bg-amber-50 border-amber-200 text-amber-700', label: 'Under Review' },
  CERTIFIED: { bg: 'bg-emerald-50 border-emerald-200 text-emerald-700', label: 'Certified' },
  REJECTED: { bg: 'bg-red-50 border-red-200 text-red-700', label: 'Returned' },
  BLOCKED_BY_SPECIFICATION: { bg: 'bg-purple-50 border-purple-200 text-purple-700', label: 'Blocked by Spec' },
};

const Reports = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summaryData, setSummaryData] = useState(null);
  
  // Filtering & Search state
  const [search, setSearch] = useState('');
  const [selectedFramework, setSelectedFramework] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');

  // Modal inspection state
  const [selectedAssessmentId, setSelectedAssessmentId] = useState(null);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAdminReportingSummary();
      setSummaryData(data);
    } catch (err) {
      console.error("Failed to load reports summary:", err);
      setError(err.message || "Failed to load reports summary.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const handleOpenReport = (assessmentId) => {
    setSelectedAssessmentId(assessmentId);
  };

  const handleCloseReport = () => {
    setSelectedAssessmentId(null);
  };

  // Reset Filters
  const handleReset = () => {
    setSearch('');
    setSelectedFramework('all');
    setSelectedStatus('all');
  };

  // Filter assessments list
  const assessments = summaryData?.assessments || [];
  const filteredAssessments = assessments.filter(item => {
    const matchesSearch = 
      (item.institution_name || '').toLowerCase().includes(search.toLowerCase()) || 
      (item.institution_aishe || '').toLowerCase().includes(search.toLowerCase()) ||
      (item.assessment_id || '').toLowerCase().includes(search.toLowerCase());
    
    const matchesFramework = selectedFramework === 'all' || item.framework === selectedFramework;
    const matchesStatus = selectedStatus === 'all' || item.status === selectedStatus;

    return matchesSearch && matchesFramework && matchesStatus;
  });

  // Client-Side CSV Exporter across filtered assessments
  const handleExportSummaryCSV = () => {
    if (filteredAssessments.length === 0) {
      alert("No assessment records available to export.");
      return;
    }

    const headers = [
      'Assessment ID',
      'Framework',
      'Institution Name',
      'AISHE Code',
      'Academic Year',
      'Lifecycle Status',
      'Scoring Status',
      'Certified Score',
      'Assigned Reviewer',
      'Last Updated'
    ];

    const rows = filteredAssessments.map(item => {
      const nameEscaped = `"${(item.institution_name || '').replace(/"/g, '""')}"`;
      return [
        item.assessment_id,
        item.framework,
        nameEscaped,
        item.institution_aishe || '',
        item.academic_year || '2025-26',
        item.status,
        item.scoring_status,
        item.certified_score != null ? item.certified_score : 'N/A',
        `"${(item.assigned_reviewer_name || 'Unassigned').replace(/"/g, '""')}"`,
        item.updated_at ? new Date(item.updated_at).toLocaleDateString('en-IN') : 'N/A'
      ];
    });

    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `NEP_2026_Audit_Ledger_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider animate-pulse">Loading Authoritative Reports...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center text-red-700">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-red-500" />
        <h3 className="font-bold text-sm">Failed to Load Reports</h3>
        <p className="text-xs text-red-600 mt-1">{error}</p>
        <button
          onClick={loadSummary}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded-xl text-xs font-bold hover:bg-red-700 transition"
        >
          Retry
        </button>
      </div>
    );
  }

  const lifecycleDist = summaryData?.lifecycle_distribution || {};
  const frameworkDist = summaryData?.framework_distribution || {};

  return (
    <div className="space-y-8 animate-fadeIn print:bg-white print:p-0 print:m-0">
      
      {/* Page Title & Export Operations */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm gap-4 print:hidden">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 uppercase tracking-wide">
              Phase 9 Authoritative Projection
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
              Read-Only
            </span>
          </div>
          <h1 className="text-xl font-bold text-slate-800 tracking-tight">Master Reports & Analytics</h1>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            Cross-framework performance ledger and compliance projections. Consumes frozen scoring and verified evidence.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleExportSummaryCSV}
            className="flex items-center gap-2 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold py-2.5 px-4 rounded-xl shadow-sm cursor-pointer transition-colors"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            <span>Export Ledger CSV</span>
          </button>
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 bg-[#1D4ED8] hover:bg-blue-700 text-white text-xs font-bold py-2.5 px-4 rounded-xl shadow-md shadow-blue-500/10 cursor-pointer transition-colors"
          >
            <Download className="w-4 h-4" />
            <span>Print Audit Ledger</span>
          </button>
        </div>
      </div>

      {/* Analytics KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 print:hidden">
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Assessments</span>
            <Layers className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black text-slate-800">{summaryData?.total_assessments || 0}</div>
          <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-2">
            <span className="font-semibold text-blue-600">{frameworkDist.university_assessments || 0} Universities</span>
            <span>•</span>
            <span className="font-semibold text-purple-600">{frameworkDist.college_assessments || 0} Colleges</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Certified Evaluations</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-emerald-700">{lifecycleDist.CERTIFIED || 0}</div>
          <div className="text-[11px] text-slate-400 mt-2 font-medium">
            Formally certified by Committee Chair
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Active Review Queue</span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-black text-amber-700">
            {(lifecycleDist.SUBMITTED || 0) + (lifecycleDist.UNDER_REVIEW || 0)}
          </div>
          <div className="text-[11px] text-slate-500 mt-2">
            <span className="font-semibold text-blue-600">{lifecycleDist.SUBMITTED || 0} Submitted</span>
            <span> • </span>
            <span className="font-semibold text-amber-600">{lifecycleDist.UNDER_REVIEW || 0} Under Review</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Statutory Blocks</span>
            <AlertCircle className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-black text-purple-700">{lifecycleDist.BLOCKED_BY_SPECIFICATION || 0}</div>
          <div className="text-[11px] text-slate-400 mt-2 font-medium">
            Blocked by specification (C5/C7/C8/C16)
          </div>
        </div>
      </div>

      {/* Query Filter panel */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-4 print:hidden">
        <div className="flex justify-between items-center pb-2 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <SlidersHorizontal className="w-4.5 h-4.5 text-slate-500" />
            <h3 className="text-xs font-black uppercase text-slate-800 tracking-wider">Audit Query Filters</h3>
          </div>
          <button 
            onClick={handleReset}
            className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-red-500 transition-colors font-bold cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Clear Filters</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Search bar */}
          <div className="relative">
            <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search institution, AISHE, Assessment ID..."
              className="w-full bg-slate-50/50 border border-slate-200 rounded-xl py-2 pl-10 pr-4 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[#1D4ED8] placeholder-slate-400 transition-all"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Framework filter */}
          <div>
            <select
              className="w-full bg-slate-50/50 border border-slate-200 rounded-xl py-2 px-3.5 text-xs font-bold text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[#1D4ED8] cursor-pointer"
              value={selectedFramework}
              onChange={(e) => setSelectedFramework(e.target.value)}
            >
              <option value="all">Framework: All Frameworks</option>
              <option value="UNIVERSITY_2026">University (UNIVERSITY_2026)</option>
              <option value="COLLEGE_2026">College (COLLEGE_2026)</option>
            </select>
          </div>

          {/* Status filter */}
          <div>
            <select
              className="w-full bg-slate-50/50 border border-slate-200 rounded-xl py-2 px-3.5 text-xs font-bold text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[#1D4ED8] cursor-pointer"
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
            >
              <option value="all">Lifecycle Status: All</option>
              <option value="DRAFT">Draft</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="CERTIFIED">Certified</option>
              <option value="REJECTED">Returned for Correction</option>
            </select>
          </div>
        </div>
      </div>

      {/* Assessments Ledger Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 overflow-hidden print:border-none print:shadow-none print:p-0">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-xs font-black uppercase text-slate-800 tracking-wider">
              Assessment Records ({filteredAssessments.length})
            </h3>
            <p className="text-[11px] text-slate-400 font-medium">Click on any row to open the complete parameter & evidence audit report.</p>
          </div>
          <span className="text-[10px] text-slate-400 font-bold print:hidden">Server-Authoritative Projections</span>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-2xl">
          <table className="min-w-full divide-y divide-slate-200 text-left">
            <thead className="bg-slate-50">
              <tr className="text-[9px] font-black text-slate-500 uppercase tracking-widest divide-x divide-slate-200">
                <th scope="col" className="px-4 py-3 min-w-[200px]">Institution Details</th>
                <th scope="col" className="px-4 py-3 min-w-[120px]">Framework</th>
                <th scope="col" className="px-4 py-3 min-w-[140px]">Assessment ID</th>
                <th scope="col" className="px-4 py-3 min-w-[100px]">Year</th>
                <th scope="col" className="px-4 py-3 min-w-[110px]">Lifecycle</th>
                <th scope="col" className="px-4 py-3 min-w-[130px]">Scoring Status</th>
                <th scope="col" className="px-4 py-3 min-w-[100px] text-right">Certified Score</th>
                <th scope="col" className="px-4 py-3 min-w-[140px] text-center print:hidden">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-100 text-xs">
              {filteredAssessments.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-400 font-medium text-xs">
                    No assessments match your active filter criteria.
                  </td>
                </tr>
              ) : (
                filteredAssessments.map((item) => {
                  const badge = LIFECYCLE_BADGES[item.status] || LIFECYCLE_BADGES.DRAFT;
                  const isBlocked = item.scoring_status === 'BLOCKED_BY_SPECIFICATION';
                  return (
                    <tr key={item.assessment_id} className="hover:bg-slate-50/60 transition-colors divide-x divide-slate-100">
                      <td className="px-4 py-3">
                        <div className="font-bold text-slate-800">{item.institution_name}</div>
                        <div className="font-mono text-[10px] text-slate-400 font-semibold">{item.institution_aishe}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-[9px] font-bold border ${
                          item.framework === 'UNIVERSITY_2026'
                            ? 'bg-blue-50 border-blue-200 text-blue-700'
                            : 'bg-purple-50 border-purple-200 text-purple-700'
                        }`}>
                          {item.framework === 'UNIVERSITY_2026' ? 'University (U1–U20)' : 'College (C1–C22)'}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-600">
                        {item.assessment_id}
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-600">
                        {item.academic_year || '2025-26'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-[9px] font-bold border ${badge.bg}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {isBlocked ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                            <AlertCircle className="w-3 h-3 text-purple-600" />
                            Blocked by Spec
                          </span>
                        ) : item.status === 'CERTIFIED' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            Certified
                          </span>
                        ) : (
                          <span className="text-[10px] font-medium text-slate-500">
                            {item.status === 'DRAFT' ? 'Not Evaluated (Draft)' : 'Evaluated'}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-extrabold text-slate-800">
                        {item.certified_score != null ? (
                          <span className="text-emerald-700 font-mono text-sm">{item.certified_score}</span>
                        ) : (
                          <span className="text-slate-400 font-mono text-xs font-normal">N/A</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center print:hidden">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => handleOpenReport(item.assessment_id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:border-blue-300 bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-700 font-bold text-[10px] transition cursor-pointer shadow-sm"
                            title="Open full audit report"
                          >
                            <Eye className="w-3 h-3" />
                            Audit Report
                          </button>
                          <button
                            onClick={() => downloadAssessmentReportCSV(item.assessment_id)}
                            className="inline-flex items-center p-1.5 rounded-lg border border-slate-200 hover:border-emerald-300 bg-white hover:bg-emerald-50 text-slate-600 hover:text-emerald-700 transition cursor-pointer shadow-sm"
                            title="Download CSV"
                          >
                            <FileSpreadsheet className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Comprehensive Assessment Report Modal */}
      {selectedAssessmentId && (
        <AssessmentReportModal
          assessmentId={selectedAssessmentId}
          onClose={handleCloseReport}
        />
      )}

    </div>
  );
};

export default Reports;
