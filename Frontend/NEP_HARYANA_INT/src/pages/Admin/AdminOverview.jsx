/**
 * AdminOverview — Phase 8.5
 *
 * Drives the admin dashboard exclusively from the Phase 8 review queue API.
 * Legacy P1–P20 mockData imports and client-side score calculations are removed.
 * The backend is the single source of truth for all numbers shown here.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  School,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  FileCheck,
  RefreshCw,
  Building2,
  User,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import { fetchAdminReviewQueue } from '../../api/admin';

// ─── Status colour palette ────────────────────────────────────────────────────
const STATUS_COLORS = {
  SUBMITTED:    { fill: '#1D4ED8', label: 'Submitted' },
  UNDER_REVIEW: { fill: '#D97706', label: 'Under Review' },
  CERTIFIED:    { fill: '#059669', label: 'Certified' },
  REJECTED:     { fill: '#EF4444', label: 'Rejected' },
  DRAFT:        { fill: '#94A3B8', label: 'Draft' },
};

// ─── Framework colour palette ─────────────────────────────────────────────────
const FRAMEWORK_COLORS = {
  COLLEGE_2026:    '#1D4ED8',
  UNIVERSITY_2026: '#7C3AED',
};

// ─── Custom tooltip for charts ─────────────────────────────────────────────────
const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div
      style={{
        background: '#0f172a',
        color: '#f8fafc',
        padding: '10px 14px',
        borderRadius: '10px',
        border: '1px solid rgba(255,255,255,0.1)',
        fontSize: '12px',
        fontFamily: "'Outfit', sans-serif",
      }}
    >
      <p style={{ color: '#94a3b8', margin: '0 0 4px', fontWeight: 600 }}>
        {d.label || d.name || d.framework || d.institution_name || ''}
      </p>
      <p style={{ color: '#60a5fa', margin: 0, fontWeight: 700 }}>
        Count: {payload[0].value}
      </p>
    </div>
  );
};

// ─── Component ────────────────────────────────────────────────────────────────
const AdminOverview = () => {
  const navigate = useNavigate();

  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const loadQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAdminReviewQueue();
      setQueue(data?.results || []);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err?.message || 'Failed to load review queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  // ─── Loading Spinner ────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider animate-pulse">
          Loading Console Data...
        </p>
      </div>
    );
  }

  // ─── Error Banner ───────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-2xl p-6 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 mt-0.5 shrink-0 text-red-500" />
          <div>
            <p className="font-bold text-sm mb-1">Failed to load the admin review queue</p>
            <p className="text-xs text-red-600">{error}</p>
            <button
              onClick={loadQueue}
              className="mt-3 flex items-center gap-2 text-xs font-bold text-red-700 hover:text-red-900"
            >
              <RefreshCw className="w-3 h-3" /> Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─── Derived KPIs (all from real backend data — no score computation) ───────
  const total            = queue.length;
  const submitted        = queue.filter(q => q.status === 'SUBMITTED').length;
  const underReview      = queue.filter(q => q.status === 'UNDER_REVIEW').length;
  const certified        = queue.filter(q => q.status === 'CERTIFIED').length;
  const unassigned       = queue.filter(q => !q.assigned_reviewer_id).length;
  const collegeCount     = queue.filter(q => q.framework === 'COLLEGE_2026').length;
  const universityCount  = queue.filter(q => q.framework === 'UNIVERSITY_2026').length;

  const kpis = [
    {
      title:    'Total in Queue',
      value:    total,
      desc:     'Across all frameworks',
      icon:     School,
      color:    'text-blue-600 bg-blue-50 border-blue-100',
      progress: 100,
    },
    {
      title:    'Submitted',
      value:    submitted,
      desc:     'Awaiting reviewer assignment',
      icon:     FileCheck,
      color:    'text-indigo-600 bg-indigo-50 border-indigo-100',
      progress: total ? Math.round((submitted / total) * 100) : 0,
    },
    {
      title:    'Certified',
      value:    certified,
      desc:     'Evaluation completed',
      icon:     CheckCircle2,
      color:    'text-emerald-600 bg-emerald-50 border-emerald-100',
      progress: total ? Math.round((certified / total) * 100) : 0,
    },
    {
      title:    'Under Review',
      value:    underReview,
      desc:     'Active reviewer sessions',
      icon:     Clock,
      color:    'text-amber-600 bg-amber-50 border-amber-100',
      progress: total ? Math.round((underReview / total) * 100) : 0,
    },
  ];

  // ─── Status distribution (Pie chart) ───────────────────────────────────────
  const statusCounts = {};
  queue.forEach(q => {
    statusCounts[q.status] = (statusCounts[q.status] || 0) + 1;
  });
  const pieData = Object.keys(statusCounts).map(s => ({
    name:  STATUS_COLORS[s]?.label || s,
    value: statusCounts[s],
    fill:  STATUS_COLORS[s]?.fill || '#94A3B8',
  })).filter(d => d.value > 0);

  // ─── Framework split (Bar chart) ───────────────────────────────────────────
  const frameworkData = [
    { name: 'College',    value: collegeCount,    fill: FRAMEWORK_COLORS.COLLEGE_2026 },
    { name: 'University', value: universityCount,  fill: FRAMEWORK_COLORS.UNIVERSITY_2026 },
  ];

  // ─── Recent submissions feed (last 5 SUBMITTED items) ──────────────────────
  const recentFeed = [...queue]
    .filter(q => q.submitted_at)
    .sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at))
    .slice(0, 5);

  return (
    <div className="space-y-8 animate-fadeIn">

      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-[#1E3A5F] to-[#1D4ED8] p-6 rounded-2xl shadow-lg text-white flex flex-col md:flex-row justify-between items-start md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            NEP Excellence Awards Evaluation Portal
          </h1>
          <p className="text-blue-100 text-xs mt-1 font-medium max-w-xl">
            Unified review queue across COLLEGE_2026 and UNIVERSITY_2026 frameworks.
            All data sourced from the Phase 8 control plane.
          </p>
        </div>
        <div className="mt-4 md:mt-0 flex items-center gap-3">
          <div className="flex items-center space-x-2 text-xs font-bold bg-[#172e4c]/40 border border-blue-400/20 py-2 px-4 rounded-xl">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span>
              {total ? Math.round((certified / total) * 100) : 0}% Certified
            </span>
          </div>
          <button
            onClick={loadQueue}
            className="flex items-center gap-1.5 text-xs font-bold bg-white/10 hover:bg-white/20 border border-white/20 py-2 px-3 rounded-xl transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
      </div>

      {lastRefreshed && (
        <p className="text-[10px] text-slate-400 font-medium -mt-4">
          Last refreshed at {lastRefreshed.toLocaleTimeString()}
        </p>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.title}
              className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow duration-200 flex flex-col justify-between"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-slate-500 font-bold uppercase tracking-wider">
                    {kpi.title}
                  </p>
                  <p className="text-3xl font-extrabold text-slate-800 mt-2 tracking-tight">
                    {kpi.value}
                  </p>
                </div>
                <div className={`p-3 rounded-xl border ${kpi.color}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
              <div className="mt-5">
                <div className="flex justify-between items-center text-[10px] text-slate-400 font-bold uppercase mb-1">
                  <span>{kpi.desc}</span>
                  <span>{kpi.progress}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-[#1D4ED8] h-1.5 rounded-full transition-all duration-500"
                    style={{ width: `${kpi.progress}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Empty State */}
      {queue.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center">
          <Building2 className="w-10 h-10 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-700 font-bold text-sm mb-2">No assessments in the review queue yet</p>
          <p className="text-slate-400 text-xs max-w-sm mx-auto">
            Assessments will appear here once institutions submit their self-appraisals and they are ingested into the Phase 8 control plane.
          </p>
        </div>
      )}

      {queue.length > 0 && (
        <>
          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

            {/* Framework Distribution Bar */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm lg:col-span-2">
              <div className="mb-6">
                <h3 className="text-lg font-bold text-slate-800 tracking-tight">
                  Framework Distribution
                </h3>
                <p className="text-xs text-slate-400 font-medium">
                  Assessments by framework in the Phase 8 control plane
                </p>
              </div>
              <div className="h-52 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={frameworkData}
                    margin={{ top: 10, right: 20, left: 10, bottom: 10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: '#64748b', fontSize: 11, fontWeight: 600 }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={80}>
                      {frameworkData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Status Breakdown Pie */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-800 tracking-tight">
                  Status Breakdown
                </h3>
                <p className="text-xs text-slate-400 font-medium mb-4">
                  Current lifecycle state distribution
                </p>
              </div>

              <div className="h-40 flex items-center justify-center relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={52}
                      outerRadius={70}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {pieData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute text-center">
                  <span className="block text-2xl font-black text-slate-800 leading-none">
                    {total}
                  </span>
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                    Total
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-2 mt-4 pt-4 border-t border-slate-100">
                {pieData.map(d => (
                  <div key={d.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: d.fill }}
                      />
                      <span className="font-semibold text-slate-700">{d.name}</span>
                    </div>
                    <span className="font-bold text-slate-500">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Queue Table + Unassigned Feed */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

            {/* Unassigned Items (needs attention) */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm lg:col-span-2">
              <div className="flex justify-between items-center mb-5">
                <div>
                  <h3 className="text-lg font-bold text-slate-800 tracking-tight">
                    Unassigned Assessments
                  </h3>
                  <p className="text-xs text-slate-400 font-medium">
                    {unassigned} {unassigned === 1 ? 'assessment needs' : 'assessments need'} a reviewer assigned
                  </p>
                </div>
                <button
                  onClick={() => navigate('/admin/colleges')}
                  className="text-xs font-bold text-[#1D4ED8] hover:text-blue-700 flex items-center gap-1 group cursor-pointer"
                >
                  <span>View All</span>
                  <ArrowRight className="w-3 h-3 transition-transform group-hover:translate-x-1" />
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-100">
                      <th className="text-left pb-2 font-bold uppercase tracking-wider text-[10px] pr-4">
                        Assessment
                      </th>
                      <th className="text-left pb-2 font-bold uppercase tracking-wider text-[10px] pr-4">
                        Institution
                      </th>
                      <th className="text-left pb-2 font-bold uppercase tracking-wider text-[10px] pr-4">
                        Framework
                      </th>
                      <th className="text-left pb-2 font-bold uppercase tracking-wider text-[10px]">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {queue
                      .filter(q => !q.assigned_reviewer_id)
                      .slice(0, 8)
                      .map(item => {
                        const sc = STATUS_COLORS[item.status] || STATUS_COLORS.DRAFT;
                        return (
                          <tr
                            key={item.assessment_id}
                            className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors"
                            onClick={() => navigate(`/admin/assessments/${item.assessment_id}`)}
                          >
                            <td className="py-2.5 pr-4 font-mono text-slate-400 text-[10px]">
                              {item.assessment_id}
                            </td>
                            <td className="py-2.5 pr-4 font-semibold text-slate-700 max-w-[160px] truncate">
                              {item.institution_name}
                            </td>
                            <td className="py-2.5 pr-4">
                              <span
                                className="text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase"
                                style={{
                                  background: item.framework === 'UNIVERSITY_2026' ? '#f5f3ff' : '#eff6ff',
                                  color:      item.framework === 'UNIVERSITY_2026' ? '#6d28d9' : '#1e40af',
                                }}
                              >
                                {item.framework === 'UNIVERSITY_2026' ? 'University' : 'College'}
                              </span>
                            </td>
                            <td className="py-2.5">
                              <span
                                className="text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase"
                                style={{
                                  background: sc.fill + '20',
                                  color:      sc.fill,
                                  border:     `1px solid ${sc.fill}40`,
                                }}
                              >
                                {sc.label}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    {unassigned === 0 && (
                      <tr>
                        <td colSpan={4} className="py-8 text-center text-slate-400 text-xs font-bold uppercase tracking-wider">
                          All assessments have reviewers assigned.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Recent Submissions Feed */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col">
              <div className="flex justify-between items-center mb-5">
                <div>
                  <h3 className="text-lg font-bold text-slate-800 tracking-tight">
                    Recent Submissions
                  </h3>
                  <p className="text-xs text-slate-400 font-medium">
                    Latest 5 by submission date
                  </p>
                </div>
              </div>

              <div className="flow-root flex-1 overflow-y-auto max-h-72">
                <ul className="-mb-8">
                  {recentFeed.length === 0 ? (
                    <div className="text-center py-12 text-slate-400 text-xs font-bold uppercase tracking-wider">
                      No submissions yet.
                    </div>
                  ) : (
                    recentFeed.map((item, index) => {
                      const sc = STATUS_COLORS[item.status] || STATUS_COLORS.DRAFT;
                      return (
                        <li key={item.assessment_id}>
                          <div className="relative pb-8">
                            {index !== recentFeed.length - 1 && (
                              <span
                                className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-slate-100"
                                aria-hidden="true"
                              />
                            )}
                            <div className="relative flex space-x-3">
                              <span
                                className="h-8 w-8 rounded-lg flex items-center justify-center ring-4 ring-white"
                                style={{
                                  background: sc.fill + '15',
                                  border: `1px solid ${sc.fill}30`,
                                  color: sc.fill,
                                }}
                              >
                                <School className="w-4 h-4" />
                              </span>
                              <div className="min-w-0 flex-1 pt-1 flex justify-between space-x-4">
                                <div>
                                  <p
                                    onClick={() => navigate(`/admin/assessments/${item.assessment_id}`)}
                                    className="text-xs font-bold text-slate-700 hover:text-[#1D4ED8] transition-colors cursor-pointer truncate max-w-[130px]"
                                    title={item.institution_name}
                                  >
                                    {item.institution_name}
                                  </p>
                                  <div className="flex items-center gap-1.5 mt-1">
                                    <span
                                      className="text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase"
                                      style={{
                                        background: sc.fill + '20',
                                        color: sc.fill,
                                        border: `1px solid ${sc.fill}40`,
                                      }}
                                    >
                                      {sc.label}
                                    </span>
                                    <span className="text-[9px] text-slate-400">
                                      {item.framework === 'UNIVERSITY_2026' ? 'Univ.' : 'College'}
                                    </span>
                                  </div>
                                </div>
                                <div className="text-right text-[10px] whitespace-nowrap text-slate-400 font-medium">
                                  <time>
                                    {item.submitted_at
                                      ? new Date(item.submitted_at).toLocaleDateString('en-IN', {
                                          day: '2-digit',
                                          month: 'short',
                                        })
                                      : '—'}
                                  </time>
                                  <span className="block text-[8px] text-slate-400/80 mt-0.5">
                                    {item.assigned_reviewer_name || 'Unassigned'}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </li>
                      );
                    })
                  )}
                </ul>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default AdminOverview;
