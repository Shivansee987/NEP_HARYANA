import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Filter,
  RefreshCw,
  Building2,
  GraduationCap,
  Calendar,
  Eye,
  ClipboardList,
  CheckCircle2,
  Clock,
  AlertCircle,
  ShieldCheck,
  ChevronRight,
  Layers,
  Award,
} from "lucide-react";
import { fetchReviewQueue } from "../../api/checker";
import { useAuth } from "../../context/AuthContext.jsx";
import { StatusBadge, DashboardSkeleton, EmptyState, ErrorState } from "../../components/common";

export default function CheckerQueue() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [queueItems, setQueueItems] = useState([]);
  const [totalCount, setTotalCount] = useState(0);

  // Filters
  const [search, setSearch] = useState("");
  const [frameworkFilter, setFrameworkFilter] = useState("ALL"); // 'ALL' | 'UNIVERSITY_2026' | 'COLLEGE_2026'
  const [statusFilter, setStatusFilter] = useState(""); // '' | 'SUBMITTED' | 'UNDER_REVIEW' | 'CERTIFIED'
  const [lastUpdated, setLastUpdated] = useState(null);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (frameworkFilter !== "ALL") {
        params.framework = frameworkFilter;
      }
      if (statusFilter) {
        params.status = statusFilter;
      }
      const data = await fetchReviewQueue(params);
      const results = data?.results || (Array.isArray(data) ? data : []);
      setQueueItems(results);
      setTotalCount(data?.count ?? results.length);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Failed to load review queue:", err);
      setError(err.message || "Failed to load assessment review queue.");
    } finally {
      setLoading(false);
    }
  }, [frameworkFilter, statusFilter]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  // Client-side search filtering on the fetched page/list
  const filteredItems = queueItems.filter((item) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    const instName = (item.institution_name || "").toLowerCase();
    const aishe = (item.institution_aishe || "").toLowerCase();
    const assessId = (item.assessment_id || "").toLowerCase();
    return instName.includes(q) || aishe.includes(q) || assessId.includes(q);
  });

  // Calculate real metrics directly from authoritative queue items
  const stats = {
    total: queueItems.length,
    universities: queueItems.filter((i) => i.framework === "UNIVERSITY_2026").length,
    colleges: queueItems.filter((i) => i.framework === "COLLEGE_2026").length,
    submitted: queueItems.filter((i) => i.status === "SUBMITTED").length,
    underReview: queueItems.filter((i) => i.status === "UNDER_REVIEW").length,
    completed: queueItems.filter((i) => i.status === "CERTIFIED" || i.is_certified).length,
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wide uppercase bg-amber-50 text-amber-800 border border-amber-200/60">
              Screening Committee
            </span>
            <span className="text-xs text-slate-400 font-medium">Statutory Cycle 2025–26</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
            Institutional Review Queue
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Evaluate, verify, and substantiate subcriterion-level evidence for submitted Higher Education Institutions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={loadQueue}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4.5 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Total in Queue</span>
            <ClipboardList className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-extrabold text-slate-900 mt-2">{stats.total}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            {stats.universities} Universities · {stats.colleges} Colleges
          </p>
        </div>

        <div className="bg-white p-4.5 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Pending Review</span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <p className="text-2xl font-extrabold text-amber-700 mt-2">{stats.submitted}</p>
          <p className="text-[11px] text-amber-700/80 mt-0.5">Awaiting first reviewer action</p>
        </div>

        <div className="bg-white p-4.5 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Under Active Review</span>
            <AlertCircle className="w-4 h-4 text-purple-600" />
          </div>
          <p className="text-2xl font-extrabold text-purple-700 mt-2">{stats.underReview}</p>
          <p className="text-[11px] text-purple-700/80 mt-0.5">Evaluation in progress</p>
        </div>

        <div className="bg-white p-4.5 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Certified / Completed</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-extrabold text-emerald-700 mt-2">{stats.completed}</p>
          <p className="text-[11px] text-emerald-700/80 mt-0.5">Evaluation finalized</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        {/* Framework Selector Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100/80 rounded-lg text-xs font-semibold">
          <button
            type="button"
            onClick={() => setFrameworkFilter("ALL")}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
              frameworkFilter === "ALL"
                ? "bg-white text-slate-900 shadow-2xs font-bold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            All Frameworks ({stats.total})
          </button>
          <button
            type="button"
            onClick={() => setFrameworkFilter("UNIVERSITY_2026")}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 cursor-pointer ${
              frameworkFilter === "UNIVERSITY_2026"
                ? "bg-white text-indigo-900 shadow-2xs font-bold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Building2 className="w-3.5 h-3.5 text-indigo-600" />
            <span>Universities ({stats.universities})</span>
          </button>
          <button
            type="button"
            onClick={() => setFrameworkFilter("COLLEGE_2026")}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 cursor-pointer ${
              frameworkFilter === "COLLEGE_2026"
                ? "bg-white text-amber-900 shadow-2xs font-bold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <GraduationCap className="w-3.5 h-3.5 text-amber-600" />
            <span>Colleges ({stats.colleges})</span>
          </button>
        </div>

        {/* Right side search & status dropdown */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          {/* Status Dropdown */}
          <div className="flex items-center gap-1.5 w-full sm:w-auto">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 outline-none focus:ring-2 focus:ring-amber-500/20 cursor-pointer w-full sm:w-auto"
            >
              <option value="">All Statuses</option>
              <option value="SUBMITTED">Submitted (Pending)</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="RETURNED">Returned for Correction</option>
              <option value="CERTIFIED">Certified</option>
            </select>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search institution / AISHE..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-xs font-medium pl-8.5 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:bg-white focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 transition-all"
            />
          </div>
        </div>
      </div>

      {/* Main Table / Card Content */}
      {loading ? (
        <DashboardSkeleton />
      ) : error ? (
        <ErrorState
          title="Could Not Load Review Queue"
          message={error}
          onRetry={loadQueue}
        />
      ) : filteredItems.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No Assessments in Review Queue"
          description={
            search || frameworkFilter !== "ALL" || statusFilter
              ? "No assessments matched the active filter criteria. Try clearing search or status filters."
              : "There are currently no submitted assessments assigned or available in the screening queue."
          }
          actionLabel={search || frameworkFilter !== "ALL" || statusFilter ? "Clear Filters" : null}
          onAction={() => {
            setSearch("");
            setFrameworkFilter("ALL");
            setStatusFilter("");
          }}
        />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="px-6 py-4">Institution Name & Scope</th>
                  <th className="px-6 py-4">AISHE Code</th>
                  <th className="px-6 py-4">Framework</th>
                  <th className="px-6 py-4">Submission Date</th>
                  <th className="px-6 py-4">Lifecycle Status</th>
                  <th className="px-6 py-4">Reviewer</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {filteredItems.map((item) => {
                  const isUniv = item.framework === "UNIVERSITY_2026";
                  return (
                    <tr
                      key={item.assessment_id}
                      className="hover:bg-slate-50/60 transition-colors group cursor-pointer"
                      onClick={() => navigate(`/checker/assessment/${item.assessment_id}`)}
                    >
                      <td className="px-6 py-4">
                        <div className="font-bold text-slate-900 group-hover:text-amber-800 transition-colors flex items-center gap-2">
                          {isUniv ? (
                            <Building2 className="w-4 h-4 text-indigo-600 shrink-0" />
                          ) : (
                            <GraduationCap className="w-4 h-4 text-amber-600 shrink-0" />
                          )}
                          <span>{item.institution_name}</span>
                        </div>
                        <span className="text-[11px] text-slate-400 font-mono mt-0.5 block">
                          ID: {item.assessment_id}
                        </span>
                      </td>

                      <td className="px-6 py-4 font-mono text-xs font-semibold text-slate-600">
                        {item.institution_aishe || "—"}
                      </td>

                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                            isUniv
                              ? "bg-indigo-50 text-indigo-800 border-indigo-200"
                              : "bg-amber-50 text-amber-800 border-amber-200"
                          }`}
                        >
                          {isUniv ? "University" : "College"}
                        </span>
                      </td>

                      <td className="px-6 py-4 text-xs font-medium text-slate-500">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          <span>
                            {item.submitted_at
                              ? new Date(item.submitted_at).toLocaleDateString("en-IN", {
                                  day: "2-digit",
                                  month: "short",
                                  year: "numeric",
                                })
                              : item.created_at
                              ? new Date(item.created_at).toLocaleDateString("en-IN", {
                                  day: "2-digit",
                                  month: "short",
                                  year: "numeric",
                                })
                              : "—"}
                          </span>
                        </div>
                      </td>

                      <td className="px-6 py-4">
                        <StatusBadge status={item.status} size="sm" />
                      </td>

                      <td className="px-6 py-4 text-xs text-slate-600">
                        {item.assigned_reviewer_name ? (
                          <div className="flex items-center gap-1.5">
                            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                            <span className="font-medium truncate max-w-[140px]">
                              {item.assigned_reviewer_name}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Unassigned</span>
                        )}
                      </td>

                      <td className="px-6 py-4 text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/checker/assessment/${item.assessment_id}`);
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Open Review</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
