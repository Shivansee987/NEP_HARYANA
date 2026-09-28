/**
 * StateInstitutions — every University and College in the state with its assessment stage.
 * Read-only for the State Admin: rows open the assessment inspection page; nothing here changes scores.
 */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, X, RefreshCw, AlertTriangle, ArrowRight, FileDown } from 'lucide-react';
import { fetchStateInstitutions } from '../../api/admin';
import { STAGES, formatScore } from '../../utils/stateStages';
import { StageBadge, TypeBadge } from '../../components/Admin/StageBadges';

const TYPE_TABS = [
  { key: 'ALL', label: 'All' },
  { key: 'UNIVERSITY', label: 'Universities' },
  { key: 'COLLEGE', label: 'Colleges' },
];

const StateInstitutions = () => {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const type = params.get('type') || 'ALL';
  const stage = params.get('stage') || '';
  const search = params.get('q') || '';

  const setParam = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const fetchRows = () =>
    fetchStateInstitutions()
      .then((data) => setRows(data?.institutions || []))
      .catch((err) => setError(err?.message || 'Failed to load institutions.'))
      .finally(() => setLoading(false));

  const load = () => {
    setLoading(true);
    setError(null);
    fetchRows();
  };

  useEffect(() => {
    fetchRows();
  }, []);

  const ofType = useMemo(() => rows.filter((r) => type === 'ALL' || r.institution_type === type), [rows, type]);

  const stageCounts = useMemo(() => {
    const counts = {};
    ofType.forEach((r) => {
      counts[r.stage] = (counts[r.stage] || 0) + 1;
    });
    return counts;
  }, [ofType]);

  const visible = useMemo(() => {
    const term = search.toLowerCase();
    return ofType.filter(
      (r) =>
        (!stage || r.stage === stage) &&
        (!term ||
          r.name.toLowerCase().includes(term) ||
          (r.aishe_code || '').toLowerCase().includes(term) ||
          (r.contact_email || '').toLowerCase().includes(term))
    );
  }, [ofType, stage, search]);

  const exportCsv = () => {
    const header = 'Institution,Type,AISHE Code,Stage,Score,Reviewer,Contact,Assessment ID\n';
    const body = visible
      .map((r) =>
        [r.name, r.institution_type, r.aishe_code, STAGES[r.stage]?.label || r.stage, r.score ?? '',
          r.assigned_reviewer_name || '', r.contact_email, r.assessment_id || '']
          .map((v) => `"${String(v).replace(/"/g, '""')}"`)
          .join(',')
      )
      .join('\n');
    const url = URL.createObjectURL(new Blob([header + body], { type: 'text/csv;charset=utf-8;' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'nep2026_institutions.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-[#600b0b] rounded-full animate-spin" />
        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Loading institutions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-800 rounded-2xl p-6 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 mt-0.5 shrink-0 text-red-500" />
        <div>
          <p className="font-bold text-sm mb-1">Could not load institutions</p>
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
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Institutions</h1>
          <p className="text-xs text-slate-500 mt-1">
            Every University (U1–U20) and College (C1–C22) in the state, with where its assessment currently stands.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="flex items-center gap-1.5 text-xs font-bold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 py-2 px-3 rounded-xl"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button
            onClick={exportCsv}
            className="flex items-center gap-1.5 text-xs font-bold bg-[#600b0b] hover:bg-[#4a0707] text-white py-2 px-3 rounded-xl"
          >
            <FileDown className="w-3.5 h-3.5" /> Export CSV
          </button>
        </div>
      </div>

      <div className="bg-white p-5 rounded-2xl border border-[#ebdcd0] shadow-xs space-y-4">
        <div className="flex flex-col lg:flex-row gap-3 lg:items-center justify-between">
          <div className="inline-flex rounded-xl border border-[#ebdcd0] overflow-hidden self-start">
            {TYPE_TABS.map((t) => {
              const count = t.key === 'ALL' ? rows.length : rows.filter((r) => r.institution_type === t.key).length;
              return (
                <button
                  key={t.key}
                  onClick={() => setParam('type', t.key === 'ALL' ? '' : t.key)}
                  className={`px-4 py-2 text-xs font-bold transition-colors ${
                    type === t.key ? 'bg-[#600b0b] text-white' : 'bg-white text-slate-600 hover:bg-[#fdfaf6]'
                  }`}
                >
                  {t.label} <span className="opacity-70">({count})</span>
                </button>
              );
            })}
          </div>
          <div className="relative lg:w-96">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setParam('q', e.target.value)}
              placeholder="Search name, AISHE code or contact email..."
              className="w-full pl-9 pr-8 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 focus:outline-none focus:border-[#600b0b]"
            />
            {search && (
              <button onClick={() => setParam('q', '')} className="absolute right-2.5 top-2.5 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setParam('stage', '')}
            className={`px-3 py-1 rounded-full text-[11px] font-bold border ${
              !stage ? 'bg-[#600b0b] text-white border-[#600b0b]' : 'bg-white text-slate-600 border-slate-200'
            }`}
          >
            All stages ({ofType.length})
          </button>
          {Object.entries(STAGES).map(([key, s]) => (
            <button
              key={key}
              onClick={() => setParam('stage', stage === key ? '' : key)}
              disabled={!stageCounts[key]}
              className={`px-3 py-1 rounded-full text-[11px] font-bold border disabled:opacity-40 ${
                stage === key ? 'bg-[#600b0b] text-white border-[#600b0b]' : `${s.cls}`
              }`}
            >
              {s.label} ({stageCounts[key] || 0})
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#ebdcd0] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="bg-[#fdfaf6] text-slate-500">
              <tr>
                {['Institution', 'Type', 'Stage', 'Score', 'Reviewer', 'Contact', ''].map((h) => (
                  <th key={h} className="px-5 py-3 text-left text-[10px] font-bold uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {visible.map((r) => (
                <tr
                  key={`${r.institution_type}-${r.institution_id}`}
                  onClick={() => r.assessment_id && navigate(`/admin/assessments/${r.assessment_id}`)}
                  className={r.assessment_id ? 'hover:bg-[#fdfaf6] cursor-pointer' : ''}
                >
                  <td className="px-5 py-3.5">
                    <p className="font-bold text-slate-800">{r.name}</p>
                    <p className="text-[10px] text-slate-400 font-mono mt-0.5">AISHE {r.aishe_code}</p>
                  </td>
                  <td className="px-5 py-3.5"><TypeBadge type={r.institution_type} /></td>
                  <td className="px-5 py-3.5"><StageBadge stage={r.stage} /></td>
                  <td className="px-5 py-3.5 font-mono font-bold text-slate-700 whitespace-nowrap">{formatScore(r.score)}</td>
                  <td className="px-5 py-3.5 text-slate-600">
                    {r.assigned_reviewer_name || <span className="text-slate-300">—</span>}
                  </td>
                  <td className="px-5 py-3.5">
                    <p className="text-slate-700 font-semibold">{r.contact_name || '—'}</p>
                    <p className="text-[10px] text-slate-400">{r.contact_email}</p>
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    {r.assessment_id ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#600b0b]">
                        Open <ArrowRight className="w-3 h-3" />
                      </span>
                    ) : (
                      <span className="text-[10px] text-slate-400">No assessment yet</span>
                    )}
                  </td>
                </tr>
              ))}
              {visible.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-400 font-bold">
                    No institutions match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="bg-[#fdfaf6] px-5 py-3 border-t border-slate-100 text-[11px] text-slate-500 font-semibold">
          Showing {visible.length} of {rows.length} institutions
        </div>
      </div>
    </div>
  );
};

export default StateInstitutions;
