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
  Shield,
  ShieldAlert,
  UserCheck,
  UserPlus,
  Lock,
  Unlock,
  AlertCircle,
  Award,
} from 'lucide-react';
import { fetchStateInstitutions, fetchAdminControlCentreSummary } from '../../api/admin';
import { useAuth } from '../../context/AuthContext.jsx';
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
  USER_CREATED: 'User created',
  ROLE_CHANGED: 'Role changed',
  ACCOUNT_ACTIVATED: 'Account activated',
  ACCOUNT_DEACTIVATED: 'Account deactivated',
  PASSWORD_RESET: 'Password reset',
  PROFILE_UPDATED: 'Profile updated',
  HEAD_ADMIN_PROVISIONED: 'Head Admin provisioned',
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
    className="text-xs font-bold text-[#600b0b] hover:text-[#4a0707] flex items-center gap-1 group whitespace-nowrap cursor-pointer"
  >
    <span>{children}</span>
    <ArrowRight className="w-3 h-3 transition-transform group-hover:translate-x-1" />
  </button>
);

const AdminOverview = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isHeadAdmin = user?.role === 'head_admin' || user?.is_superuser;

  const [data, setData] = useState(null);
  const [controlCentreData, setControlCentreData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [activeTab, setActiveTab] = useState('control_centre'); // 'control_centre' | 'institutions'

  const fetchData = async () => {
    try {
      if (isHeadAdmin) {
        const [instRes, ccRes] = await Promise.all([
          fetchStateInstitutions().catch(() => null),
          fetchAdminControlCentreSummary(),
        ]);
        setData(instRes);
        setControlCentreData(ccRes);
      } else {
        const instRes = await fetchStateInstitutions();
        setData(instRes);
        setControlCentreData(null);
      }
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err?.message || 'Failed to load the administrative overview.');
    } finally {
      setLoading(false);
    }
  };

  const load = () => {
    setLoading(true);
    setError(null);
    fetchData();
  };

  useEffect(() => {
    fetchData();
  }, [isHeadAdmin]);

  if (loading && !data && !controlCentreData) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-[#600b0b] rounded-full animate-spin" />
        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">
          {isHeadAdmin ? 'Loading Head Admin Control Centre...' : 'Loading state overview...'}
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-800 rounded-2xl p-6 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 mt-0.5 shrink-0 text-red-500" />
        <div>
          <p className="font-bold text-sm mb-1">
            {isHeadAdmin ? 'Failed to load Control Centre' : 'Failed to load the state overview'}
          </p>
          <p className="text-xs text-red-600">{error}</p>
          <button onClick={load} className="mt-3 flex items-center gap-2 text-xs font-bold text-red-700 cursor-pointer">
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      </div>
    );
  }

  const summary = data?.summary || controlCentreData?.institutions || { universities: 0, colleges: 0, started: 0, total: 0, by_stage: {} };
  const s = summary.by_stage || {};
  const committee = data?.committee || { pending_reviews: 0, unassigned: 0, reviewers: [] };
  const institutions = data?.institutions || [];
  const activity = data?.recent_activity || [];

  const tiles = [
    { title: 'Universities', value: summary.universities, icon: Building2, query: 'type=UNIVERSITY' },
    { title: 'Colleges', value: summary.colleges, icon: School, query: 'type=COLLEGE' },
    { title: 'Started', value: summary.started, icon: PlayCircle, query: '' },
    { title: 'Submitted', value: s.SUBMITTED || 0, icon: FileCheck, query: 'stage=SUBMITTED' },
    { title: 'Under Review', value: (s.UNDER_REVIEW || 0) + (s.AWAITING_CERTIFICATION || 0), icon: Clock, query: 'stage=UNDER_REVIEW' },
    { title: 'Returned', value: s.RETURNED || 0, icon: Undo2, query: 'stage=RETURNED' },
    { title: 'Certified', value: s.CERTIFIED || 0, icon: CheckCircle2, query: 'stage=CERTIFIED' },
  ];

  const attention = institutions
    .map((r) => {
      if (r.stage === 'SUBMITTED' && !r.assigned_reviewer_id) return { ...r, reason: 'Submitted — needs a reviewer' };
      if (r.stage === 'RETURNED') return { ...r, reason: 'Returned — waiting on institution' };
      if (r.stage === 'AWAITING_CERTIFICATION') return { ...r, reason: 'Review complete — awaiting Chair' };
      if (r.stage === 'NOT_STARTED') return { ...r, reason: 'Has not started the assessment' };
      return null;
    })
    .filter(Boolean);

  const certifiedPct = summary.total ? Math.round(((s.CERTIFIED || 0) / summary.total) * 100) : 0;

  // Head Admin Control Centre variables
  const cc = controlCentreData;
  const gov = cc?.governance;
  const ops = cc?.operations;
  const warnings = cc?.warnings || [];
  const privilegedActions = cc?.recent_privileged_actions || [];

  return (
    <div className="space-y-6">
      {/* Role-Aware Header Banner */}
      <div className="bg-gradient-to-r from-[#600b0b] via-[#4a0707] to-[#300303] border-b-3 border-[#c29b68] p-6 rounded-2xl shadow-lg text-white flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div>
          <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-white/10 border border-white/20 uppercase tracking-widest inline-flex items-center gap-1.5">
            <ShieldCheck className="w-3 h-3 text-[#c29b68]" />
            {isHeadAdmin ? 'Head Administrator · Control Centre' : 'State Admin · NEP Excellence Awards 2026'}
          </span>
          <h1 className="text-2xl font-extrabold tracking-tight mt-2">
            {isHeadAdmin ? 'Head Admin Control Centre' : 'State Overview'}
          </h1>
          <p className="text-[#eaded2] text-xs mt-1 max-w-2xl">
            {isHeadAdmin
              ? 'Authoritative platform governance, multi-tier committee administration, and statutory assessment workflow oversight.'
              : `${summary.universities} universities and ${summary.colleges} colleges registered · ${summary.started} have started · ${certifiedPct}% certified.`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isHeadAdmin && (
            <>
              <button
                onClick={() => navigate('/admin/users?action=create')}
                className="flex items-center gap-1.5 text-xs font-bold bg-white text-[#600b0b] hover:bg-[#fff1f2] py-2 px-3.5 rounded-xl shadow-xs transition-colors cursor-pointer"
              >
                <UserPlus className="w-3.5 h-3.5" /> + Add User
              </button>
              <button
                onClick={() => navigate('/admin/users')}
                className="flex items-center gap-1.5 text-xs font-bold bg-[#c29b68] hover:bg-[#b08852] text-slate-900 py-2 px-3.5 rounded-xl shadow-xs transition-colors cursor-pointer"
              >
                <UserCheck className="w-3.5 h-3.5" /> User Governance
              </button>
            </>
          )}
          <button
            onClick={() => goTo('')}
            className="flex items-center gap-1.5 text-xs font-bold bg-white text-[#600b0b] hover:bg-[#fdfaf6] py-2 px-3.5 rounded-xl transition-colors cursor-pointer"
          >
            <Building2 className="w-3.5 h-3.5" /> All Institutions
          </button>
          <button
            onClick={load}
            className="flex items-center gap-1.5 text-xs font-bold bg-white/10 hover:bg-white/20 border border-white/20 py-2 px-3 rounded-xl transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {lastRefreshed && (
        <p className="text-[10px] text-slate-400 font-medium -mt-3 px-1">
          Last synchronized {lastRefreshed.toLocaleTimeString()}
        </p>
      )}

      {/* Head Admin View Tabs */}
      {isHeadAdmin && (
        <div className="flex items-center gap-2 border-b border-[#ebdcd0] pb-2">
          <button
            onClick={() => setActiveTab('control_centre')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'control_centre'
                ? 'bg-[#600b0b] text-white shadow-xs'
                : 'text-slate-600 hover:bg-[#fdfaf6]'
            }`}
          >
            <Shield className="w-3.5 h-3.5" /> Governance & Control Centre
          </button>
          <button
            onClick={() => setActiveTab('institutions')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'institutions'
                ? 'bg-[#600b0b] text-white shadow-xs'
                : 'text-slate-600 hover:bg-[#fdfaf6]'
            }`}
          >
            <Building2 className="w-3.5 h-3.5" /> State Institutions Overview
          </button>
        </div>
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* HEAD ADMIN CONTROL CENTRE TAB CONTENT */}
      {/* ───────────────────────────────────────────────────────────── */}
      {isHeadAdmin && activeTab === 'control_centre' && cc && (
        <div className="space-y-6">
          {/* Actionable Warnings / Alerts */}
          {warnings.length > 0 && (
            <div className="space-y-2">
              {warnings.map((w, idx) => {
                const isUrgent = w.level === 'CRITICAL' || w.level === 'URGENT';
                const isWarn = w.level === 'WARNING';
                return (
                  <div
                    key={idx}
                    className={`rounded-2xl p-4 border flex items-start gap-3 transition-all ${
                      isUrgent
                        ? 'bg-rose-50/90 border-rose-200 text-rose-900'
                        : isWarn
                        ? 'bg-amber-50/90 border-amber-200 text-amber-900'
                        : 'bg-blue-50/90 border-blue-200 text-blue-900'
                    }`}
                  >
                    {isUrgent ? (
                      <ShieldAlert className="w-5 h-5 mt-0.5 shrink-0 text-rose-600" />
                    ) : isWarn ? (
                      <AlertTriangle className="w-5 h-5 mt-0.5 shrink-0 text-amber-600" />
                    ) : (
                      <AlertCircle className="w-5 h-5 mt-0.5 shrink-0 text-blue-600" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[9px] font-extrabold uppercase px-2 py-0.5 rounded-full ${
                            isUrgent
                              ? 'bg-rose-200/80 text-rose-900'
                              : isWarn
                              ? 'bg-amber-200/80 text-amber-900'
                              : 'bg-blue-200/80 text-blue-900'
                          }`}
                        >
                          {w.level}
                        </span>
                        <h4 className="text-xs font-bold">{w.title}</h4>
                      </div>
                      <p className="text-xs mt-1 leading-relaxed opacity-90">{w.message}</p>
                    </div>
                    {w.code === 'UNASSIGNED_SUBMISSIONS' && (
                      <button
                        onClick={() => goTo('stage=SUBMITTED')}
                        className="text-xs font-bold text-rose-800 underline hover:text-rose-950 shrink-0 cursor-pointer"
                      >
                        Assign Reviewers &rarr;
                      </button>
                    )}
                    {w.code === 'SINGLE_HEAD_ADMIN' && (
                      <button
                        onClick={() => navigate('/admin/users')}
                        className="text-xs font-bold text-amber-800 underline hover:text-amber-950 shrink-0 cursor-pointer"
                      >
                        Manage Users &rarr;
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Control Centre KPI Tiles */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-white p-4 rounded-2xl border border-[#ebdcd0] shadow-xs">
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Institutions</p>
                <Building2 className="w-4 h-4 text-[#600b0b]" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 mt-1.5 font-mono">{cc.institutions.total}</p>
              <p className="text-[10px] text-slate-500 font-medium mt-1">
                {cc.institutions.colleges} Colleges · {cc.institutions.universities} Universities
              </p>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-[#ebdcd0] shadow-xs">
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Active Admins</p>
                <ShieldCheck className="w-4 h-4 text-purple-700" />
              </div>
              <p className="text-2xl font-extrabold text-purple-900 mt-1.5 font-mono">
                {gov?.administrators?.total_active || 0}
              </p>
              <p className="text-[10px] text-purple-700/80 font-medium mt-1">
                {gov?.administrators?.head_admins?.active || 0} Head · {gov?.administrators?.sub_admins?.active || 0} Sub
              </p>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-[#ebdcd0] shadow-xs">
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Screening Comm.</p>
                <Users className="w-4 h-4 text-emerald-700" />
              </div>
              <p className="text-2xl font-extrabold text-emerald-900 mt-1.5 font-mono">
                {gov?.screening_committee?.total_active || 0}
              </p>
              <p className="text-[10px] text-emerald-700/80 font-medium mt-1">
                {gov?.screening_committee?.chairs?.active || 0} Chairs · {gov?.screening_committee?.reviewers?.active || 0} Reviewers
              </p>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-[#ebdcd0] shadow-xs">
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Empowered Comm.</p>
                <Award className="w-4 h-4 text-teal-700" />
              </div>
              <p className="text-2xl font-extrabold text-teal-900 mt-1.5 font-mono">
                {gov?.empowered_committee?.total_active || 0}
              </p>
              <p className="text-[10px] text-teal-700/80 font-medium mt-1">
                {gov?.empowered_committee?.chairs?.active || 0} Chairs · {gov?.empowered_committee?.reviewers?.active || 0} Reviewers
              </p>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-[#ebdcd0] shadow-xs">
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Unassigned</p>
                <Clock className="w-4 h-4 text-amber-700" />
              </div>
              <p className="text-2xl font-extrabold text-amber-900 mt-1.5 font-mono">
                {ops?.unassigned_count || 0}
              </p>
              <p className="text-[10px] text-amber-700/80 font-medium mt-1">
                Awaiting reviewer assignment
              </p>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-[#ebdcd0] shadow-xs">
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Certified</p>
                <CheckCircle2 className="w-4 h-4 text-[#600b0b]" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 mt-1.5 font-mono">
                {cc.institutions.by_stage.CERTIFIED || 0}
              </p>
              <p className="text-[10px] text-slate-500 font-medium mt-1">
                Awards finalized by Chair
              </p>
            </div>
          </div>

          {/* Governance & Committee Staffing Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Card 1: Executive Administration */}
            <Card
              title="Platform Administrators"
              subtitle="Executive authorization & governance authority"
              action={<LinkButton onClick={() => navigate('/admin/users')}>Manage Users</LinkButton>}
            >
              <div className="space-y-3 mt-1">
                <div className="flex items-center justify-between p-3 rounded-xl bg-purple-50/60 border border-purple-200/60">
                  <div>
                    <p className="text-xs font-bold text-purple-950">Head Administrators</p>
                    <p className="text-[10px] text-purple-700">Highest authority; provisioning & security</p>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-extrabold text-sm text-purple-900">
                      {gov?.administrators?.head_admins?.active || 0} active
                    </span>
                    <span className="text-[10px] text-slate-400 block font-mono">
                      / {gov?.administrators?.head_admins?.total || 0} total
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-indigo-50/60 border border-indigo-200/60">
                  <div>
                    <p className="text-xs font-bold text-indigo-950">Sub-Administrators</p>
                    <p className="text-[10px] text-indigo-700">DHE state operations & review queue management</p>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-extrabold text-sm text-indigo-900">
                      {gov?.administrators?.sub_admins?.active || 0} active
                    </span>
                    <span className="text-[10px] text-slate-400 block font-mono">
                      / {gov?.administrators?.sub_admins?.total || 0} total
                    </span>
                  </div>
                </div>
              </div>
            </Card>

            {/* Card 2: Screening Committee */}
            <Card
              title="Screening Committee"
              subtitle="Tier-1 review, verification, and certification"
              action={<LinkButton onClick={() => navigate('/admin/users?role=committee')}>Roster</LinkButton>}
            >
              <div className="space-y-3 mt-1">
                <div className="flex items-center justify-between p-3 rounded-xl bg-amber-50/60 border border-amber-200/60">
                  <div>
                    <p className="text-xs font-bold text-amber-950">Screening Committee Chairs</p>
                    <p className="text-[10px] text-amber-700">Sole domain certification authority</p>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-extrabold text-sm text-amber-900">
                      {gov?.screening_committee?.chairs?.active || 0} active
                    </span>
                    <span className="text-[10px] text-slate-400 block font-mono">
                      / {gov?.screening_committee?.chairs?.total || 0} total
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-emerald-50/60 border border-emerald-200/60">
                  <div>
                    <p className="text-xs font-bold text-emerald-950">Screening Reviewers</p>
                    <p className="text-[10px] text-emerald-700">Evidence audit & parameter evaluation</p>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-extrabold text-sm text-emerald-900">
                      {gov?.screening_committee?.reviewers?.active || 0} active
                    </span>
                    <span className="text-[10px] text-slate-400 block font-mono">
                      / {gov?.screening_committee?.reviewers?.total || 0} total
                    </span>
                  </div>
                </div>
              </div>
            </Card>

            {/* Card 3: Empowered Committee */}
            <Card
              title="Empowered Committee"
              subtitle="Tier-2 apex committee & policy ratification"
              action={<LinkButton onClick={() => navigate('/admin/users?role=empowered_committee')}>Roster</LinkButton>}
            >
              <div className="space-y-3 mt-1">
                <div className="flex items-center justify-between p-3 rounded-xl bg-orange-50/60 border border-orange-200/60">
                  <div>
                    <p className="text-xs font-bold text-orange-950">Empowered Chairs</p>
                    <p className="text-[10px] text-orange-700">Apex statutory ratification</p>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-extrabold text-sm text-orange-900">
                      {gov?.empowered_committee?.chairs?.active || 0} active
                    </span>
                    <span className="text-[10px] text-slate-400 block font-mono">
                      / {gov?.empowered_committee?.chairs?.total || 0} total
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-teal-50/60 border border-teal-200/60">
                  <div>
                    <p className="text-xs font-bold text-teal-950">Empowered Members</p>
                    <p className="text-[10px] text-teal-700">High-level award committee</p>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-extrabold text-sm text-teal-900">
                      {gov?.empowered_committee?.reviewers?.active || 0} active
                    </span>
                    <span className="text-[10px] text-slate-400 block font-mono">
                      / {gov?.empowered_committee?.reviewers?.total || 0} total
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Operational Bottlenecks & Exceptions Monitoring */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Exceptions & Action Queue */}
            <Card
              title="Operational Bottlenecks & Exceptions"
              subtitle="Items requiring reviewer assignment, correction, or specification clearance"
              action={<LinkButton onClick={() => goTo('stage=SUBMITTED')}>View Queue</LinkButton>}
            >
              <div className="space-y-4">
                {/* Unassigned reviews */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-amber-600" /> Unassigned Submissions ({ops?.unassigned_count || 0})
                    </span>
                  </div>
                  {ops?.unassigned_items?.length > 0 ? (
                    <div className="space-y-1.5 max-h-40 overflow-y-auto">
                      {ops.unassigned_items.slice(0, 5).map((item) => (
                        <div
                          key={item.assessment_id}
                          onClick={() => navigate(`/admin/assessments/${item.assessment_id}`)}
                          className="p-2 rounded-xl bg-[#fdfaf6] border border-[#ebdcd0] flex items-center justify-between text-xs cursor-pointer hover:border-[#600b0b]"
                        >
                          <div className="min-w-0 pr-2">
                            <p className="font-semibold text-slate-800 truncate">{item.institution_name}</p>
                            <p className="text-[10px] text-slate-400">{item.aishe_code} · {item.framework}</p>
                          </div>
                          <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full shrink-0">
                            Needs Reviewer
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No unassigned submissions in queue.</p>
                  )}
                </div>

                {/* Statutory blocks */}
                <div className="pt-3 border-t border-slate-100">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-purple-600" /> Statutory Specification Blocks ({ops?.blocked_count || 0})
                    </span>
                  </div>
                  {ops?.blocked_items?.length > 0 ? (
                    <div className="space-y-1.5 max-h-40 overflow-y-auto">
                      {ops.blocked_items.slice(0, 5).map((item) => (
                        <div
                          key={item.assessment_id}
                          onClick={() => navigate(`/admin/assessments/${item.assessment_id}`)}
                          className="p-2 rounded-xl bg-purple-50/40 border border-purple-200/60 flex items-center justify-between text-xs cursor-pointer hover:border-purple-600"
                        >
                          <div className="min-w-0 pr-2">
                            <p className="font-semibold text-slate-800 truncate">{item.institution_name}</p>
                            <p className="text-[10px] text-purple-700">{item.reason}</p>
                          </div>
                          <span className="text-[10px] font-bold text-purple-800 bg-purple-100 px-2 py-0.5 rounded-full shrink-0">
                            C5, C7, C8, C16
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No statutory specification blocks active.</p>
                  )}
                </div>
              </div>
            </Card>

            {/* Privileged Security & Account Audit Log */}
            <Card
              title="Privileged Security & Account Audit Stream"
              subtitle="Append-only record of administrative role changes, activations, and user lifecycle"
              action={<LinkButton onClick={() => navigate('/admin/users')}>All Audit Logs</LinkButton>}
            >
              <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                {privilegedActions.length > 0 ? (
                  privilegedActions.map((act) => (
                    <div key={act.id} className="py-2.5 flex items-start justify-between gap-3 text-xs">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-800 border border-slate-200">
                            {act.action_label || humanize(act.action)}
                          </span>
                          <span className="font-semibold text-slate-800 truncate">{act.target_user_email}</span>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          by <span className="text-slate-600 font-medium">{act.actor_name || act.actor_email}</span>
                          {act.details?.role && ` · Role: ${act.details.role}`}
                          {act.details?.new_role && ` · New role: ${act.details.new_role}`}
                        </p>
                      </div>
                      <time className="text-[10px] text-slate-400 whitespace-nowrap shrink-0">
                        {act.timestamp
                          ? new Date(act.timestamp).toLocaleString('en-IN', {
                              day: '2-digit',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '—'}
                      </time>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 italic py-6 text-center">No privileged audit activity recorded yet.</p>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* INSTITUTIONS OVERVIEW (Default for non-HeadAdmin, or Tab for Head Admin) */}
      {/* ───────────────────────────────────────────────────────────── */}
      {(!isHeadAdmin || activeTab === 'institutions') && data && (
        <div className="space-y-6">
          {/* State totals */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {tiles.map((t) => {
              const Icon = t.icon;
              return (
                <button
                  key={t.title}
                  onClick={() => goTo(t.query)}
                  className="bg-white p-4 rounded-2xl border border-[#ebdcd0] shadow-xs hover:border-[#c29b68] text-left transition-colors cursor-pointer"
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
                          onClick={() =>
                            r.assessment_id
                              ? navigate(`/admin/assessments/${r.assessment_id}`)
                              : goTo(`q=${encodeURIComponent(r.aishe_code)}`)
                          }
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
                  className="p-3 rounded-xl bg-red-50/60 border border-red-200/70 text-left cursor-pointer"
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
                        <p className="text-[10px] text-slate-400">
                          {rv.role === 'committee_chair' ? 'Chairperson' : 'Reviewer'}
                        </p>
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

            {/* Assessment Audit trail */}
            <div className="lg:col-span-2">
              <Card
                title="Recent Assessment Activity"
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
                        {new Date(a.timestamp).toLocaleString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </time>
                    </li>
                  ))}
                  {activity.length === 0 && <li className="py-6 text-center text-xs text-slate-400">No activity yet.</li>}
                </ul>
                <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
                  <button
                    onClick={() => navigate('/admin/reports')}
                    className="flex items-center gap-1.5 text-xs font-bold text-slate-700 border border-slate-200 hover:border-[#600b0b] py-1.5 px-3 rounded-lg cursor-pointer"
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5" /> State & institution reports
                  </button>
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminOverview;

