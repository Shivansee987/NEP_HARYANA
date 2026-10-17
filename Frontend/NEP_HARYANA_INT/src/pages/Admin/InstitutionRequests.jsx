/**
 * InstitutionRequests — self-registered principals / nodal officers waiting for their institution request to be
 * approved. Until approved an applicant has no institution binding and cannot open any assessment.
 * Approve binds the account to the requested institution; Reject (reason required) leaves it unbound.
 * The Council Admin Overseer sees the queue read-only (the API refuses its decisions).
 */
import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, RefreshCw, ShieldAlert, UserCheck, XCircle } from 'lucide-react';
import { decideInstitutionAccess, fetchPendingInstitutionRequests } from '../../api/admin';
import { useAuth } from '../../context/AuthContext.jsx';

const INSTITUTION_APPROVER_ROLES = ['head_admin', 'state_admin', 'sub_admin', 'admin'];
const MIN_REJECTION_REASON = 10;

const InstitutionRequests = () => {
  const { user } = useAuth();
  const canDecide = INSTITUTION_APPROVER_ROLES.includes(user?.role);

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', message }
  const [busyId, setBusyId] = useState(null);
  const [rejecting, setRejecting] = useState(null); // applicant row being rejected
  const [reason, setReason] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPendingInstitutionRequests();
      setRows(data?.results || (Array.isArray(data) ? data : []));
    } catch (err) {
      setError(err?.message || 'Failed to load institution requests.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const decide = async (row, decision, rejectionReason = '') => {
    setBusyId(row.id);
    setFeedback(null);
    try {
      await decideInstitutionAccess(row.id, decision, rejectionReason);
      setRows((prev) => prev.filter((r) => r.id !== row.id));
      const institution = row.requested_institution?.name || 'the requested institution';
      setFeedback({
        type: 'success',
        message: decision === 'approve'
          ? `${row.full_name} can now act for ${institution}.`
          : `${row.full_name}'s request for ${institution} was rejected.`,
      });
      setRejecting(null);
      setReason('');
    } catch (err) {
      setFeedback({ type: 'error', message: err?.message || 'The decision could not be recorded.' });
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-[#600b0b] rounded-full animate-spin" />
        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Loading institution requests...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-800 rounded-2xl p-6 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 mt-0.5 shrink-0 text-red-500" />
        <div>
          <p className="font-bold text-sm mb-1">Could not load institution requests</p>
          <p className="text-xs text-red-600">{error}</p>
          <button onClick={load} className="mt-3 flex items-center gap-2 text-xs font-bold text-red-700">
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-2xl border border-[#ebdcd0] shadow-xs flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Institution Access Requests</h1>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Applicants who registered themselves as a College Principal or University Nodal Officer. Confirm each
            person's identity and authority with the institution before approving: approval gives them full control
            of that institution's assessment.
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-xs font-bold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 py-2 px-3 rounded-xl self-start"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {!canDecide && (
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 flex items-start gap-2">
          <ShieldAlert className="w-4 h-4 text-slate-500 shrink-0" />
          <span>Read-only view. Only the Head Admin and State Admins can approve or reject institution requests.</span>
        </div>
      )}

      {feedback && (
        <div role="status" className={`p-4 rounded-xl border text-sm font-medium ${feedback.type === 'success'
          ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-red-50 border-red-200 text-red-800'}`}>
          {feedback.message}
        </div>
      )}

      <div className="bg-white rounded-2xl border border-[#ebdcd0] shadow-xs overflow-x-auto">
        {rows.length === 0 ? (
          <div className="p-10 text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            <p className="text-sm font-bold text-slate-800">No pending requests</p>
            <p className="text-xs text-slate-500 mt-1">New self-registrations will appear here for approval.</p>
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider text-[10px]">
              <tr>
                <th className="text-left px-4 py-3">Applicant</th>
                <th className="text-left px-4 py-3">Role requested</th>
                <th className="text-left px-4 py-3">Institution requested</th>
                <th className="text-left px-4 py-3">Verified mobile</th>
                {canDecide && <th className="text-right px-4 py-3">Decision</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-slate-100 align-top">
                  <td className="px-4 py-3">
                    <p className="font-bold text-slate-900">{row.full_name}</p>
                    <p className="text-slate-500 break-all">{row.email}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {row.role === 'nodal_officer' ? 'University Nodal Officer' : 'College Principal'}
                  </td>
                  <td className="px-4 py-3">
                    <p className="font-semibold text-slate-800">{row.requested_institution?.name || '—'}</p>
                    <p className="text-slate-500 font-mono">
                      {row.requested_institution?.type || ''}{row.requested_institution?.aishe_code ? ` · ${row.requested_institution.aishe_code}` : ''}
                    </p>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-700">{row.phone_number || '—'}</td>
                  {canDecide && (
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => decide(row, 'approve')}
                          disabled={busyId === row.id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold disabled:opacity-50"
                        >
                          <UserCheck className="w-3.5 h-3.5" /> Approve
                        </button>
                        <button
                          type="button"
                          onClick={() => { setRejecting(row); setReason(''); }}
                          disabled={busyId === row.id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-red-50 text-red-700 border border-red-300 rounded-lg font-bold disabled:opacity-50"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Reject
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {rejecting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60"
          role="dialog" aria-modal="true" aria-labelledby="reject-request-title">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <h2 id="reject-request-title" className="text-sm font-bold text-red-700">Reject institution request</h2>
            <p className="text-xs text-slate-600">
              {rejecting.full_name} will not be able to act for {rejecting.requested_institution?.name || 'this institution'}.
            </p>
            <div>
              <label htmlFor="reject-request-reason" className="block text-xs font-bold text-slate-700 mb-1">
                Reason (required, recorded in the audit trail)
              </label>
              <textarea id="reject-request-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
                className="w-full text-xs p-3 border border-slate-200 rounded-lg outline-none focus:border-red-400" />
              {reason.trim().length > 0 && reason.trim().length < MIN_REJECTION_REASON && (
                <p className="text-[11px] text-red-600 mt-1">Enter at least {MIN_REJECTION_REASON} characters.</p>
              )}
            </div>
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setRejecting(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold">Cancel</button>
              <button type="button" onClick={() => decide(rejecting, 'reject', reason.trim())}
                disabled={busyId === rejecting.id || reason.trim().length < MIN_REJECTION_REASON}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold disabled:opacity-50">
                Reject request
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InstitutionRequests;
