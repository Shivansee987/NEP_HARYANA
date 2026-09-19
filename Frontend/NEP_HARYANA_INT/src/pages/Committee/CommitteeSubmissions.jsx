import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, 
  Filter, 
  ChevronLeft, 
  ChevronRight, 
  ArrowUpDown, 
  Eye, 
  Calendar,
  Award,
  Clock,
  ClipboardList
} from 'lucide-react';
import { fetchCommitteeSubmissions } from '../../api/committee';
import { fetchAdminReviewQueue } from '../../api/admin';
import { useAuth } from '../../context/AuthContext.jsx';
import { motion } from 'framer-motion';

const CommitteeSubmissions = ({ onlyHistory = false }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isChair = user?.role === 'committee_chair';

  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  
  // Params
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState(onlyHistory ? "Approved" : "");
  const [sortBy, setSortBy] = useState("updated_at");
  const [page, setPage] = useState(1);

  const loadSubmissions = async () => {
    setLoading(true);
    try {
      if (isChair) {
        // Committee Chair loads from the Phase 8 Control Plane Review Queue
        const params = {};
        if (status) params.status = status;
        const data = await fetchAdminReviewQueue(params);
        const rawList = data?.results || [];
        const filtered = search
          ? rawList.filter(item => 
              (item.institution_name || '').toLowerCase().includes(search.toLowerCase()) ||
              (item.institution_aishe || '').toLowerCase().includes(search.toLowerCase()) ||
              (item.assessment_id || '').toLowerCase().includes(search.toLowerCase())
            )
          : rawList;
        
        const mapped = filtered.map(item => ({
          id: item.assessment_id,
          college_name: item.institution_name,
          head_name: item.framework,
          aishe_code: item.institution_aishe || '—',
          submitted_at: item.submitted_at,
          score: item.is_certified ? "Certified" : (item.status === "SUBMITTED" ? "Submitted" : "Pending"),
          status: item.status,
        }));
        setSubmissions(mapped);
        setTotalCount(data?.count ?? mapped.length);
        setTotalPages(Math.ceil((data?.count ?? mapped.length) / 10) || 1);
      } else {
        const params = {
          search,
          sort_by: sortBy,
          page,
          page_size: 10
        };
        if (status) params.status = status;
        if (onlyHistory && !status) {
          params.status = "Approved";
        }
        
        const data = await fetchCommitteeSubmissions(params);
        setSubmissions(data.results);
        setTotalCount(data.total_count);
        setTotalPages(data.total_pages);
      }
    } catch (err) {
      console.error("Error fetching committee submissions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSubmissions();
  }, [search, status, sortBy, page]);

  const handleSearchChange = (e) => {
    setSearch(e.target.value);
    setPage(1);
  };

  const handleStatusChange = (e) => {
    setStatus(e.target.value);
    setPage(1);
  };

  const handleSortChange = (field) => {
    setSortBy(field);
    setPage(1);
  };

  const getStatusBadgeClass = (statusStr) => {
    switch (statusStr) {
      case 'Approved':
        return 'bg-emerald-50 text-emerald-700 border-emerald-100';
      case 'Rejected':
        return 'bg-red-50 text-red-700 border-red-100';
      case 'Clarification Requested':
        return 'bg-purple-50 text-purple-700 border-purple-100';
      case 'Responded':
        return 'bg-blue-50 text-blue-700 border-blue-100';
      case 'Under Review':
        return 'bg-indigo-50 text-indigo-700 border-indigo-100';
      default:
        return 'bg-amber-50 text-amber-700 border-amber-100';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header card with action controls */}
      <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-[0_4px_20px_rgb(0,0,0,0.02)] flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search by college, AISHE code..."
            value={search}
            onChange={handleSearchChange}
            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-500/10 transition-all placeholder:text-slate-400"
          />
        </div>

        {/* Filters and Sorting */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Status Filter */}
          {!onlyHistory && (
            <div className="flex items-center space-x-2 border border-slate-200 rounded-xl px-3 py-2 bg-white">
              <Filter className="w-4 h-4 text-slate-400" />
              <select
                value={status}
                onChange={handleStatusChange}
                className="text-xs font-semibold text-slate-600 bg-transparent border-none outline-none pr-6 cursor-pointer"
              >
                <option value="">All Statuses</option>
                <option value="Pending Review">Pending Review</option>
                <option value="Under Review">Under Review</option>
                <option value="Clarification Requested">Clarification Requested</option>
                <option value="Responded">Responded</option>
                <option value="Approved">Approved</option>
                <option value="Rejected">Rejected</option>
              </select>
            </div>
          )}

          {/* Sorting controls */}
          <div className="flex items-center space-x-1.5 border border-slate-200 rounded-xl px-3 py-2 bg-white">
            <ArrowUpDown className="w-4 h-4 text-slate-400" />
            <select
              value={sortBy}
              onChange={(e) => handleSortChange(e.target.value)}
              className="text-xs font-semibold text-slate-600 bg-transparent border-none outline-none pr-6 cursor-pointer"
            >
              <option value="updated_at">Recently Updated</option>
              <option value="submitted_at">Submission Date</option>
              <option value="score">Score</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table grid */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.02)] overflow-hidden">
        {loading ? (
          <div className="divide-y divide-slate-100">
            {[1, 2, 3, 4, 5].map(n => (
              <div key={n} className="p-6 animate-pulse flex items-center justify-between">
                <div className="space-y-2 flex-1">
                  <div className="h-4 bg-slate-100 rounded w-1/4" />
                  <div className="h-3 bg-slate-100 rounded w-1/3" />
                </div>
                <div className="h-8 bg-slate-100 rounded w-20" />
              </div>
            ))}
          </div>
        ) : submissions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="bg-slate-50/50 border-b border-slate-100 text-slate-400 font-bold text-xs uppercase tracking-wider">
                  <th className="px-6 py-4.5 font-bold">Institution Details</th>
                  <th className="px-6 py-4.5 font-bold">AISHE</th>
                  <th className="px-6 py-4.5 font-bold">Submitted Date</th>
                  <th className="px-6 py-4.5 font-bold">Self Score</th>
                  <th className="px-6 py-4.5 font-bold">Status</th>
                  <th className="px-6 py-4.5 font-bold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700 text-sm">
                {submissions.map((sub, idx) => (
                  <motion.tr
                    key={sub.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25, delay: idx * 0.03 }}
                    className="hover:bg-slate-50/40 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="font-semibold text-slate-800">{sub.college_name}</div>
                      <div className="text-xs text-slate-400 font-medium mt-0.5">{sub.head_name || "Principal"}</div>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs font-semibold text-slate-500">
                      {sub.aishe_code}
                    </td>
                    <td className="px-6 py-4 text-xs font-medium text-slate-500">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        {sub.submitted_at ? new Date(sub.submitted_at).toLocaleDateString('en-IN') : "-"}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5">
                        <Award className="w-4 h-4 text-orange-500" />
                        <span className="font-extrabold text-slate-800">{sub.score}</span>
                        <span className="text-[10px] font-bold text-slate-400 bg-slate-100 border border-slate-200/50 px-2 py-0.5 rounded-full">{sub.award_category}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex border px-2.5 py-0.5 rounded-full text-xs font-bold ${getStatusBadgeClass(sub.status)}`}>
                        {sub.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => navigate(`/committee/submissions/${sub.id}`)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:border-orange-200 bg-white hover:bg-orange-50/50 text-slate-600 hover:text-orange-600 font-bold text-xs transition-all cursor-pointer shadow-sm"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Review
                      </button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-20 text-slate-400">
            <ClipboardList className="w-16 h-16 mx-auto mb-4 opacity-50 text-slate-300" />
            <h4 className="font-bold text-slate-800 text-lg">No submissions found</h4>
            <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
              There are no submissions matching your active search, filter, or page criteria.
            </p>
          </div>
        )}

        {/* Pagination bar */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/30 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">
              Showing page {page} of {totalPages} ({totalCount} total submissions)
            </span>
            <div className="flex items-center space-x-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="p-1.5 border border-slate-200 hover:border-slate-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed bg-white transition-colors"
              >
                <ChevronLeft className="w-4 h-4 text-slate-600" />
              </button>
              <button
                disabled={page === totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                className="p-1.5 border border-slate-200 hover:border-slate-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed bg-white transition-colors"
              >
                <ChevronRight className="w-4 h-4 text-slate-600" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CommitteeSubmissions;
