/**
 * AdminOverview — State Admin dashboard.
 *
 * Driven entirely by GET /api/v1/admin/institutions/: state totals, the institutions that need attention,
 * committee workload and recent audit activity. The State Admin monitors, assigns and reports here;
 * evidence decisions and score approval stay with the committee workflow.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  School,
  PlayCircle,
  FileCheck,
  Clock,
  Undo2,
  CheckCircle2,
  RefreshCw,
  AlertTriangle,
  ArrowRight,
  Users,
  FileSpreadsheet,
  History,
  ShieldCheck,
} from 'lucide-react';
import { fetchStateInstitutions } from '../../api/admin';
import { formatScore } from '../../utils/stateStages';
import { StageBadge, TypeBadge } from '../../components/Admin/StageBadges';

const ACTION_LABELS = {
  CREATED: 'Assessment started',
  PARAMETER_UPDATED: 'Parameter saved',
  SUBMITTED: 'Submitted',
  REVIEW_STARTED: 'Review started',
  REVIEW_COMPLETED: 'Review completed',
  RETURNED_FOR_CORRECTION: 'Returned for correction',
  REVIEW_BLOCKED: 'Review blocked',
  EVALUATION_TRIGGERED: 'Score evaluated',
  CERTIFICATION_SUCCEEDED: 'Certified',
  REVIEWER_ASSIGNED: 'Reviewer assigned',
  REVIEWER_REASSIGNED: 'Reviewer reassigned',
  PARAMETER_SCORE_ACCEPTED: 'Parameter approved',
  SCORE_ADJUSTED: 'Score adjusted',
};
const humanize = (action) =>
  ACTION_LABELS[action] || String(action || '').replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase());

const Card = ({ title, subtitle, action, children }) => (
  <div className="bg-white p-6 rounded-2xl border border-[#ebdcd0] shadow-xs flex flex-col">
    <div className="flex justify-between items-start gap-3 mb-4">
      <div>
        <h3 className="text-base font-bold text-slate-800 tracking-tight">{title}</h3>
        {subtitle && <p className="text-xs text-slate-400 font-medium mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
    {children}
  </div>
);

const LinkButton = ({ onClick, children }) => (
  <button
    onClick={onClick}
    className="text-xs font-bold text-[#600b0b] hover:text-[#4a0707] flex items-center gap-1 group whitespace-nowrap"
  >
    <span>{children}</span>
    <ArrowRight className="w-3 h-3 transition-transform group-hover:translate-x-1" />
  </button>
);

const AdminOverview = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const fetchData = () =>
    fetchStateInstitutions()
      .then((res) => {
        setData(res);
        setLastRefreshed(new Date());
      })
      .catch((err) => setError(err?.message || 'Failed to load the state overview.'))
      .finally(() => setLoading(false));

  const load = () => {
    setLoading(true);
    setError(null);
    fetchData();
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-[#600b0b] rounded-full animate-spin" />
        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Loading state overview...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-800 rounded-2xl p-6 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 mt-0.5 shrink-0 text-red-500" />
        <div>
          <p className="font-bold text-sm mb-1">Failed to load the state overview</p>
          <p className="text-xs text-red-600">{error}</p>
          <button onClick={load} className="mt-3 flex items-center gap-2 text-xs font-bold text-red-700">
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      </div>
    );
  }

  const { summary, committee, institutions, recent_activity: activity } = data;
  const s = summary.by_stage;
  const goTo = (query) => navigate(`/admin/institutions${query ? `?${query}` : ''}`);

  const tiles = [
    { title: 'Universities', value: summary.universities, icon: Building2, query: 'type=UNIVERSITY' },
    { title: 'Colleges', value: summary.colleges, icon: School, query: 'type=COLLEGE' },
    { title: 'Started', value: summary.started, icon: PlayCircle, query: '' },
    { title: 'Submitted', value: s.SUBMITTED, icon: FileCheck, query: 'stage=SUBMITTED' },
    { title: 'Under Review', value: s.UNDER_REVIEW + s.AWAITING_CERTIFICATION, icon: Clock, query: 'stage=UNDER_REVIEW' },
    { title: 'Returned', value: s.RETURNED, icon: Undo2, query: 'stage=RETURNED' },
    { title: 'Certified', value: s.CERTIFIED, icon: CheckCircle2, query: 'stage=CERTIFIED' },
  ];

  // Institutions waiting on someone: unassigned submissions, returned work, and pending certification.
  const attention = institutions
    .map((r) => {
      if (r.stage === 'SUBMITTED' && !r.assigned_reviewer_id) return { ...r, reason: 'Submitted — needs a reviewer' };
      if (r.stage === 'RETURNED') return { ...r, reason: 'Returned — waiting on institution' };
      if (r.stage === 'AWAITING_CERTIFICATION') return { ...r, reason: 'Review complete — awaiting Chair' };
      if (r.stage === 'NOT_STARTED') return { ...r, reason: 'Has not started the assessment' };
      return null;
    })
    .filter(Boolean);

  const certifiedPct = summary.total ? Math.round((s.CERTIFIED / summary.total) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#600b0b] via-[#4a0707] to-[#300303] border-b-3 border-[#c29b68] p-6 rounded-2xl shadow-lg text-white flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div>
          <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-white/10 border border-white/20 uppercase tracking-widest">
            State Admin · NEP Excellence Awards 2026
          </span>
          <h1 className="text-2xl font-extrabold tracking-tight mt-2">State Overview</h1>
          <p className="text-[#eaded2] text-xs mt-1 max-w-2xl">
            {summary.universities} universities and {summary.colleges} colleges registered · {summary.started} have
            started · {certifiedPct}% certified.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => goTo('')}
            className="flex items-center gap-1.5 text-xs font-bold bg-white text-[#600b0b] hover:bg-[#fdfaf6] py-2 px-3.5 rounded-xl"
          >
            <Building2 className="w-3.5 h-3.5" /> All Institutions
          </button>
          <button
            onClick={load}
            className="flex items-center gap-1.5 text-xs font-bold bg-white/10 hover:bg-white/20 border border-white/20 py-2 px-3 rounded-xl"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>
      {lastRefreshed && (
        <p className="text-[10px] text-slate-400 font-medium -mt-3 px-1">
          Updated {lastRefreshed.toLocaleTimeString()}
        </p>
      )}

      {/* State totals */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {tiles.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.title}
              onClick={() => goTo(t.query)}
              className="bg-white p-4 rounded-2xl border border-[#ebdcd0] shadow-xs hover:border-[#c29b68] text-left transition-colors"
            >
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">{t.title}</p>
                <Icon className="w-4 h-4 text-[#600b0b]" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 mt-1.5 font-mono">{t.value}</p>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Needs attention */}
        <div className="lg:col-span-2">
          <Card
            title="Needs Attention"
            subtitle="Institutions waiting on the institution, a reviewer, or the Chair"
            action={<LinkButton onClick={() => goTo('')}>View all institutions</LinkButton>}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-400 border-b border-slate-100 text-[10px] uppercase tracking-wider">
                    <th className="text-left pb-2 pr-3 font-bold">Institution</th>
                    <th className="text-left pb-2 pr-3 font-bold">Type</th>
                    <th className="text-left pb-2 pr-3 font-bold">Stage</th>
                    <th className="text-left pb-2 font-bold">Why</th>
                  </tr>
                </thead>
                <tbody>
                  {attention.slice(0, 10).map((r) => (
                    <tr
                      key={`${r.institution_type}-${r.institution_id}`}
                      onClick={() => (r.assessment_id ? navigate(`/admin/assessments/${r.assessment_id}`) : goTo(`q=${encodeURIComponent(r.aishe_code)}`))}
                      className="border-b border-slate-50 hover:bg-[#fdfaf6] cursor-pointer"
                    >
                      <td className="py-2.5 pr-3 font-semibold text-slate-700">{r.name}</td>
                      <td className="py-2.5 pr-3"><TypeBadge type={r.institution_type} /></td>
                      <td className="py-2.5 pr-3"><StageBadge stage={r.stage} /></td>
                      <td className="py-2.5 text-slate-500">{r.reason}</td>
                    </tr>
                  ))}
                  {attention.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-slate-400 font-bold">
                        Nothing is waiting — every institution is moving.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* Committee */}
        <Card title="Committee" subtitle="Reviewer workload across open reviews">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="p-3 rounded-xl bg-amber-50/60 border border-amber-200/70">
              <p className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">Pending reviews</p>
              <p className="text-xl font-extrabold text-amber-900 font-mono">{committee.pending_reviews}</p>
            </div>
            <button
              onClick={() => goTo('stage=SUBMITTED')}
              className="p-3 rounded-xl bg-red-50/60 border border-red-200/70 text-left"
            >
              <p className="text-[10px] font-bold text-red-700 uppercase tracking-wider">Unassigned</p>
              <p className="text-xl font-extrabold text-red-900 font-mono">{committee.unassigned}</p>
            </button>
          </div>
          <ul className="space-y-2">
            {committee.reviewers.map((rv) => (
              <li key={rv.id} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 min-w-0">
                  <Users className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-700 truncate">{rv.full_name}</p>
                    <p className="text-[10px] text-slate-400">{rv.role === 'committee_chair' ? 'Chairperson' : 'Reviewer'}</p>
                  </div>
                </div>
                <span className="font-mono font-bold text-slate-600">{rv.active_assignments} open</span>
              </li>
            ))}
            {committee.reviewers.length === 0 && (
              <li className="text-xs text-slate-400">No committee members registered.</li>
            )}
          </ul>
          <p className="text-[10px] text-slate-400 mt-4 flex items-start gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 shrink-0 text-emerald-600" />
            Assign reviewers from an assessment page. Evidence and score decisions stay with the committee.
          </p>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top scores */}
        <Card title="Scores So Far" subtitle="Latest calculated totals (final once certified)">
          <ul className="space-y-2">
            {institutions
              .filter((r) => r.score != null)
              .sort((a, b) => b.score - a.score)
              .slice(0, 6)
              .map((r) => (
                <li
                  key={`${r.institution_type}-${r.institution_id}`}
                  onClick={() => navigate(`/admin/assessments/${r.assessment_id}`)}
                  className="flex items-center justify-between text-xs cursor-pointer hover:text-[#600b0b]"
                >
                  <span className="font-semibold text-slate-700 truncate pr-2">{r.name}</span>
                  <span className="font-mono font-bold whitespace-nowrap">{formatScore(r.score)}</span>
                </li>
              ))}
            {institutions.every((r) => r.score == null) && (
              <li className="text-xs text-slate-400">No scores calculated yet.</li>
            )}
          </ul>
        </Card>

        {/* Audit trail */}
        <div className="lg:col-span-2">
          <Card
            title="Recent Activity"
            subtitle="Latest actions from the assessment audit trail"
            action={<LinkButton onClick={() => navigate('/admin/reports')}>Reports</LinkButton>}
          >
            <ul className="divide-y divide-slate-50 max-h-80 overflow-y-auto">
              {activity.map((a, i) => (
                <li
                  key={i}
                  onClick={() => navigate(`/admin/assessments/${a.assessment_id}`)}
                  className="py-2 flex items-center justify-between gap-3 text-xs cursor-pointer hover:bg-[#fdfaf6]"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <History className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-700 truncate">
                        {humanize(a.action)} · <span className="text-slate-500">{a.institution_name}</span>
                      </p>
                      <p className="text-[10px] text-slate-400">by {a.actor}</p>
                    </div>
                  </div>
                  <time className="text-[10px] text-slate-400 whitespace-nowrap">
                    {new Date(a.timestamp).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                  </time>
                </li>
              ))}
              {activity.length === 0 && <li className="py-6 text-center text-xs text-slate-400">No activity yet.</li>}
            </ul>
            <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
              <button
                onClick={() => navigate('/admin/reports')}
                className="flex items-center gap-1.5 text-xs font-bold text-slate-700 border border-slate-200 hover:border-[#600b0b] py-1.5 px-3 rounded-lg"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" /> State & institution reports
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AdminOverview;
