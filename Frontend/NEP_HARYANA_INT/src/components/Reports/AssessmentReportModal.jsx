/**
 * AssessmentReportModal — Reusable Comprehensive Assessment Audit & Analytics Modal
 *
 * Phase 9 Reports & Analytics
 * Authoritative read-only projection of NEP 2026 assessment data.
 * Consumes /api/v1/reports/assessments/<id>/
 * Zero client-side score calculations.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  X,
  FileSpreadsheet,
  Printer,
  Building2,
  Layers,
  ShieldCheck,
  Award,
  History,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  RotateCcw,
  ExternalLink,
  ListTree,
} from 'lucide-react';
import {
  fetchAssessmentReport,
  downloadAssessmentReportCSV,
} from '../../api/reports';

export default function AssessmentReportModal({ assessmentId, onClose, initialTab = 'overview' }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState(initialTab);
  const [exporting, setExporting] = useState(false);

  const loadReport = useCallback(async () => {
    if (!assessmentId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAssessmentReport(assessmentId);
      setReport(data);
    } catch (err) {
      console.error('Failed to load assessment report:', err);
      setError(err?.message || 'Failed to load assessment report.');
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleExportCSV = async () => {
    if (!assessmentId) return;
    setExporting(true);
    try {
      await downloadAssessmentReportCSV(assessmentId);
    } catch (err) {
      alert(`Export failed: ${err.message}`);
    } finally {
      setExporting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (!assessmentId) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white w-full max-w-5xl rounded-2xl shadow-2xl border border-slate-200 flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in duration-150">
        
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 uppercase tracking-wide">
                {report?.framework || 'NEP 2026'}
              </span>
              <span className="font-mono text-xs text-slate-500 font-bold">{assessmentId}</span>
              {report?.scoring?.is_blocked_by_specification && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 uppercase tracking-wide">
                  Blocked by Spec
                </span>
              )}
            </div>
            <h2 className="text-base font-bold text-slate-800">
              {report?.institution?.name || 'Assessment Audit Report'}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportCSV}
              disabled={exporting}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-bold transition cursor-pointer disabled:opacity-50"
              title="Download official CSV export"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>{exporting ? 'Exporting...' : 'Export CSV'}</span>
            </button>

            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold transition cursor-pointer"
              title="Print audit ledger"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-xl transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="flex border-b border-slate-200 px-5 bg-white text-xs font-bold overflow-x-auto">
          {[
            { id: 'overview', label: 'Overview', icon: Building2 },
            { id: 'parameters', label: `Parameters (${report?.parameters?.length || 0})`, icon: Layers },
            { id: 'subcriteria', label: 'Subcriteria Traces', icon: ListTree },
            { id: 'evidence', label: 'Evidence Readiness', icon: ShieldCheck },
            { id: 'scoring', label: 'Scoring Engine Output', icon: Award },
            { id: 'review', label: 'Review & Certification', icon: History },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 py-3 px-3.5 border-b-2 transition whitespace-nowrap cursor-pointer ${
                  isActive
                    ? 'border-[#1D4ED8] text-[#1D4ED8]'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-3">
              <div className="w-8 h-8 border-3 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
              <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">
                Loading Authoritative Assessment Report...
              </p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <AlertCircle className="w-10 h-10 text-red-500" />
              <div className="text-center">
                <p className="font-bold text-slate-800 text-sm">{error}</p>
                <p className="text-xs text-slate-500 mt-1">
                  Could not retrieve authoritative report. Verify your session and permissions.
                </p>
              </div>
              <button
                onClick={loadReport}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 font-bold rounded-lg text-xs"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Retry
              </button>
            </div>
          ) : report ? (
            <>
              {/* TAB 1: OVERVIEW */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/60">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Institution
                      </span>
                      <div className="font-bold text-slate-800 text-sm">{report.institution?.name}</div>
                      <div className="text-xs text-slate-500 font-mono mt-0.5">
                        AISHE: {report.institution?.aishe_code}
                      </div>
                      <div className="text-[11px] text-slate-500 mt-1">{report.institution?.type}</div>
                    </div>

                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/60">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Statutory Window
                      </span>
                      <div className="font-bold text-slate-800 text-sm">
                        Academic Year {report.period?.academic_year}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {report.period?.period_start} to {report.period?.period_end}
                      </div>
                      <div className="text-[10px] font-bold text-blue-600 mt-1 uppercase">
                        Statutory Window Gated
                      </div>
                    </div>

                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/60">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Assigned Reviewer
                      </span>
                      <div className="font-bold text-slate-800 text-sm">
                        {report.assigned_reviewer?.full_name || 'Unassigned'}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {report.assigned_reviewer?.email || 'Awaiting reviewer assignment'}
                      </div>
                      <div className="text-[10px] font-bold text-purple-600 mt-1 uppercase">
                        Screening Committee
                      </div>
                    </div>
                  </div>

                  {/* Certification Eligibility Card */}
                  <div
                    className={`p-4 rounded-xl border ${
                      report.certification?.is_certified
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                        : report.certification?.certification_eligibility?.is_eligible
                        ? 'bg-blue-50 border-blue-200 text-blue-800'
                        : 'bg-amber-50 border-amber-200 text-amber-800'
                    }`}
                  >
                    <div className="flex items-center gap-2 font-bold text-xs">
                      {report.certification?.is_certified ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-amber-600" />
                      )}
                      <span>
                        {report.certification?.is_certified
                          ? `Assessment Formally Certified (Score: ${report.certification.certified_score})`
                          : report.certification?.certification_eligibility?.is_eligible
                          ? 'Eligible for Committee Chair Certification'
                          : 'Certification Blocked by Statutory Gates'}
                      </span>
                    </div>
                    {!report.certification?.is_certified &&
                      report.certification?.certification_eligibility?.blocking_gates?.length > 0 && (
                        <ul className="mt-2 space-y-1 text-[11px] list-disc pl-5">
                          {report.certification.certification_eligibility.blocking_gates.map((g, idx) => (
                            <li key={idx}>{g}</li>
                          ))}
                        </ul>
                      )}
                  </div>

                  {/* Quick Summary Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Assessment Status</span>
                      <span className="font-bold text-slate-800 text-sm mt-0.5 block">{report.status}</span>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Parameters</span>
                      <span className="font-bold text-slate-800 text-sm mt-0.5 block">
                        {report.parameters?.length || 0} Statutory
                      </span>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Evidence Coverage</span>
                      <span className="font-bold text-slate-800 text-sm mt-0.5 block">
                        {report.evidence?.verified_subcriteria ?? 0} / {report.evidence?.total_subcriteria ?? 0}
                      </span>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Certified Score</span>
                      <span className="font-bold text-emerald-700 text-sm font-mono mt-0.5 block">
                        {report.scoring?.final_certified_total != null ? `${report.scoring.final_certified_total} pts` : 'Pending'}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: PARAMETERS */}
              {activeTab === 'parameters' && (
                <div className="space-y-4">
                  <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    <table className="min-w-full divide-y divide-slate-200 text-left">
                      <thead className="bg-slate-50 text-[9px] font-black text-slate-500 uppercase tracking-wider">
                        <tr className="divide-x divide-slate-200">
                          <th className="px-3 py-2.5 w-16 text-center">Code</th>
                          <th className="px-3 py-2.5">Parameter Title</th>
                          <th className="px-3 py-2.5 text-center w-20">Max</th>
                          <th className="px-3 py-2.5 text-center w-24">Input Status</th>
                          <th className="px-3 py-2.5 text-center w-24">Coverage</th>
                          <th className="px-3 py-2.5 text-right w-24">Earned Marks</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-xs">
                        {report.parameters?.map((p) => (
                          <tr key={p.parameter_code} className="hover:bg-slate-50/50 divide-x divide-slate-100">
                            <td className="px-3 py-2.5 text-center font-mono font-bold text-slate-700 bg-slate-50/30">
                              {p.parameter_code}
                            </td>
                            <td className="px-3 py-2.5 font-medium text-slate-800">
                              {p.parameter_title}
                              {p.blocking_reasons?.length > 0 && (
                                <span className="block text-[10px] text-purple-600 font-bold mt-0.5">
                                  {p.blocking_reasons.join(', ')}
                                </span>
                              )}
                            </td>
                            <td className="px-3 py-2.5 text-center font-bold text-slate-600">
                              {p.max_marks}
                            </td>
                            <td className="px-3 py-2.5 text-center">
                              <span
                                className={`inline-flex px-2 py-0.5 rounded-full text-[9px] font-bold ${
                                  p.submitted ? 'bg-blue-50 text-blue-700' : 'bg-slate-100 text-slate-500'
                                }`}
                              >
                                {p.submitted ? 'Submitted' : 'Missing'}
                              </span>
                            </td>
                            <td className="px-3 py-2.5 text-center">
                              <span
                                className={`inline-flex px-2 py-0.5 rounded-full text-[9px] font-bold ${
                                  p.evidence_coverage_state === 'COVERED'
                                    ? 'bg-emerald-50 text-emerald-700'
                                    : p.evidence_coverage_state === 'PENDING'
                                    ? 'bg-amber-50 text-amber-700'
                                    : p.evidence_coverage_state === 'REJECTED'
                                    ? 'bg-red-50 text-red-700'
                                    : 'bg-slate-100 text-slate-500'
                                }`}
                              >
                                {p.evidence_coverage_state}
                              </span>
                            </td>
                            <td className="px-3 py-2.5 text-right font-mono font-bold text-slate-800">
                              {p.final_score != null ? p.final_score : p.raw_score != null ? p.raw_score : 'N/A'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 3: SUBCRITERIA TRACES */}
              {activeTab === 'subcriteria' && (
                <div className="space-y-4">
                  <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                      <thead className="bg-slate-50 text-[9px] font-black text-slate-500 uppercase tracking-wider">
                        <tr className="divide-x divide-slate-200">
                          <th className="px-3 py-2.5 w-24 text-center">Subcriterion</th>
                          <th className="px-3 py-2.5">Parameter Code</th>
                          <th className="px-3 py-2.5 text-center w-16">Max</th>
                          <th className="px-3 py-2.5 text-center w-16">Raw</th>
                          <th className="px-3 py-2.5 text-center w-16">Gated</th>
                          <th className="px-3 py-2.5 text-center w-24">Resolution</th>
                          <th className="px-3 py-2.5">Evaluator Trace</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {report.subcriteria && report.subcriteria.length > 0 ? (
                          report.subcriteria.map((sc, idx) => (
                            <tr key={idx} className="hover:bg-slate-50/50 divide-x divide-slate-100">
                              <td className="px-3 py-2 text-center font-mono font-bold text-blue-700 bg-slate-50/30">
                                {sc.subcriterion_code}
                              </td>
                              <td className="px-3 py-2 font-mono text-slate-600">{sc.parameter_code}</td>
                              <td className="px-3 py-2 text-center font-semibold text-slate-600">{sc.max_score}</td>
                              <td className="px-3 py-2 text-center font-mono text-slate-800">{sc.raw_score ?? '—'}</td>
                              <td className="px-3 py-2 text-center font-mono font-bold text-emerald-700">
                                {sc.gated_score ?? '—'}
                              </td>
                              <td className="px-3 py-2 text-center">
                                <span
                                  className={`inline-flex px-2 py-0.5 rounded-full text-[9px] font-bold ${
                                    sc.resolution_status === 'RESOLVED'
                                      ? 'bg-emerald-50 text-emerald-700'
                                      : sc.resolution_status === 'BLOCKED'
                                      ? 'bg-purple-50 text-purple-700'
                                      : 'bg-slate-100 text-slate-600'
                                  }`}
                                >
                                  {sc.resolution_status || 'UNRESOLVED'}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-[11px] text-slate-500 font-mono">
                                {sc.trace || '—'}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={7} className="text-center py-6 text-slate-400">
                              No subcriteria evaluations recorded yet.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 4: EVIDENCE READINESS */}
              {activeTab === 'evidence' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                      <span className="text-[10px] font-bold text-slate-400 uppercase block">
                        Subcriteria Evaluated
                      </span>
                      <span className="text-xl font-black text-slate-800">
                        {report.evidence?.total_subcriteria || 0}
                      </span>
                    </div>
                    <div className="bg-emerald-50 p-3.5 rounded-xl border border-emerald-200">
                      <span className="text-[10px] font-bold text-emerald-600 uppercase block">
                        Verified Covered
                      </span>
                      <span className="text-xl font-black text-emerald-800">
                        {report.evidence?.verified_subcriteria || 0}
                      </span>
                    </div>
                    <div className="bg-amber-50 p-3.5 rounded-xl border border-amber-200">
                      <span className="text-[10px] font-bold text-amber-600 uppercase block">
                        Pending Verification
                      </span>
                      <span className="text-xl font-black text-amber-800">
                        {report.evidence?.verification_pending || 0}
                      </span>
                    </div>
                    <div className="bg-red-50 p-3.5 rounded-xl border border-red-200">
                      <span className="text-[10px] font-bold text-red-600 uppercase block">
                        Rejected / Period Invalid
                      </span>
                      <span className="text-xl font-black text-red-800">
                        {(report.evidence?.rejected_evidence || 0) + (report.evidence?.period_invalid || 0)}
                      </span>
                    </div>
                  </div>

                  {report.evidence?.blocking_reasons?.length > 0 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-800">
                      <h4 className="font-bold text-xs flex items-center gap-1 mb-2">
                        <AlertTriangle className="w-4 h-4 text-amber-600" />
                        Evidence Readiness Blockers
                      </h4>
                      <ul className="text-xs space-y-1 list-disc pl-5">
                        {report.evidence.blocking_reasons.map((b, idx) => (
                          <li key={idx}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 5: SCORING ENGINE OUTPUT */}
              {activeTab === 'scoring' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                      <span className="text-[10px] font-bold uppercase text-slate-400 block">Raw Sum Before Cap</span>
                      <span className="text-2xl font-black text-slate-700">
                        {report.scoring?.raw_total != null ? report.scoring.raw_total : 'N/A'}
                      </span>
                    </div>
                    <div className="bg-blue-50 p-4 rounded-xl border border-blue-200">
                      <span className="text-[10px] font-bold uppercase text-blue-600 block">
                        Evidence Gated Score
                      </span>
                      <span className="text-2xl font-black text-blue-800">
                        {report.scoring?.evidence_gated_total != null ? report.scoring.evidence_gated_total : 'N/A'}
                      </span>
                    </div>
                    <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200">
                      <span className="text-[10px] font-bold uppercase text-emerald-600 block">
                        Final Certified Marks
                      </span>
                      <span className="text-2xl font-black text-emerald-800">
                        {report.scoring?.final_certified_total != null ? report.scoring.final_certified_total : 'N/A'}
                      </span>
                      <span className="text-[10px] text-emerald-600 block mt-0.5">Max: 100.00 Marks</span>
                    </div>
                  </div>

                  {report.scoring?.is_blocked_by_specification && (
                    <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 text-purple-800">
                      <h4 className="font-bold text-xs flex items-center gap-1.5 mb-2">
                        <AlertCircle className="w-4 h-4 text-purple-600" />
                        Scoring Blocked by Statutory Specification
                      </h4>
                      <p className="text-xs">
                        This assessment contains unresolved statutory specifications (e.g. C5, C7, C8, C16) and cannot
                        be certified until statutory clarification is resolved.
                      </p>
                      {report.scoring?.blocking_reasons?.length > 0 && (
                        <ul className="text-xs space-y-1 list-disc pl-5 mt-2">
                          {report.scoring.blocking_reasons.map((b, idx) => (
                            <li key={idx}>{b}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 6: REVIEW & AUDIT */}
              {activeTab === 'review' && (
                <div className="space-y-4">
                  <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                      <thead className="bg-slate-50 text-[9px] font-black text-slate-500 uppercase tracking-wider">
                        <tr>
                          <th className="px-3 py-2.5">Action</th>
                          <th className="px-3 py-2.5">Actor</th>
                          <th className="px-3 py-2.5">State Transition</th>
                          <th className="px-3 py-2.5">Comments</th>
                          <th className="px-3 py-2.5">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {report.review?.review_history?.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="text-center py-6 text-slate-400">
                              No formal review records logged yet.
                            </td>
                          </tr>
                        ) : (
                          report.review?.review_history?.map((r, idx) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="px-3 py-2 font-bold text-slate-700">{r.action}</td>
                              <td className="px-3 py-2 text-slate-600">{r.actor}</td>
                              <td className="px-3 py-2 font-mono text-[11px] text-slate-500">
                                {r.status_before} → {r.status_after}
                              </td>
                              <td className="px-3 py-2 text-slate-600 max-w-[200px] truncate">
                                {r.comments || r.reason || '—'}
                              </td>
                              <td className="px-3 py-2 text-slate-400 text-[10px]">
                                {r.timestamp ? new Date(r.timestamp).toLocaleString('en-IN') : '—'}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Read-Only Statutory Projection • NEP 2026 Engine</span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold rounded-xl transition cursor-pointer"
          >
            Close Audit Report
          </button>
        </div>
      </div>
    </div>
  );
}
