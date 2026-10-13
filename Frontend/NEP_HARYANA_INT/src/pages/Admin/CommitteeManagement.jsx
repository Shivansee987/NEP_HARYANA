import { useEffect, useState, useMemo } from 'react';
import {
  Users,
  Award,
  Search,
  Plus,
  Shield,
  ShieldCheck,
  Building,
  GraduationCap,
  CheckCircle2,
  XCircle,
  AlertCircle,
  X,
  RefreshCw,
  UserPlus,
  UserMinus,
  Edit,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext.jsx';
import {
  fetchAdminCommittees,
  fetchAdminCommitteeDetail,
  createAdminCommittee,
  updateAdminCommittee,
  assignAdminCommitteeChair,
  addAdminCommitteeMember,
  removeAdminCommitteeMember,
  fetchAdminUsers,
} from '../../api/admin.js';

export default function CommitteeManagement() {
  const { user: currentUser } = useAuth();
  const isAdmin = currentUser?.role === 'head_admin' || currentUser?.role === 'state_admin' || currentUser?.is_superuser;
  const isCouncilAdmin = currentUser?.role === 'council_admin';

  const [committees, setCommittees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [frameworkFilter, setFrameworkFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    framework: 'COLLEGE_2026',
    committee_type: 'SCREENING',
    chair_id: '',
  });

  // Selected Committee Detail Modal
  const [selectedCommittee, setSelectedCommittee] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Chair assignment modal
  const [showChairModal, setShowChairModal] = useState(false);
  const [chairSubmitting, setChairSubmitting] = useState(false);
  const [selectedChairId, setSelectedChairId] = useState('');

  // Add Member modal
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [memberSubmitting, setMemberSubmitting] = useState(false);
  const [newMemberForm, setNewMemberForm] = useState({
    user_id: '',
    role_in_committee: 'member',
  });

  // Available users for chair / member assignment
  const [availableUsers, setAvailableUsers] = useState([]);

  const loadCommittees = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAdminCommittees({
        framework: frameworkFilter,
        is_active: statusFilter,
        search,
      });
      setCommittees(res.results || []);
    } catch (err) {
      setError(err.message || 'Failed to load committees');
    } finally {
      setLoading(false);
    }
  };

  const loadEligibleUsers = async () => {
    try {
      const res = await fetchAdminUsers({ page_size: 100 });
      setAvailableUsers(res.results || []);
    } catch (e) {
      // Ignore background load error
    }
  };

  useEffect(() => {
    loadCommittees();
  }, [frameworkFilter, statusFilter]);

  useEffect(() => {
    loadEligibleUsers();
  }, []);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadCommittees();
  };

  const openCommitteeDetail = async (committeeId) => {
    setDetailLoading(true);
    setSelectedCommittee(null);
    try {
      const data = await fetchAdminCommitteeDetail(committeeId);
      setSelectedCommittee(data);
    } catch (err) {
      setError(err.message || 'Failed to load committee details');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setCreateSubmitting(true);
    setError(null);
    try {
      const payload = {
        name: createForm.name,
        description: createForm.description,
        framework: createForm.framework,
        committee_type: createForm.committee_type,
        chair_id: createForm.chair_id ? parseInt(createForm.chair_id, 10) : null,
      };
      await createAdminCommittee(payload);
      setSuccessMsg(`Committee "${createForm.name}" created successfully.`);
      setShowCreateModal(false);
      setCreateForm({
        name: '',
        description: '',
        framework: 'COLLEGE_2026',
        committee_type: 'SCREENING',
        chair_id: '',
      });
      loadCommittees();
    } catch (err) {
      setError(err.message || 'Failed to create committee');
    } finally {
      setCreateSubmitting(false);
    }
  };

  const handleAssignChairSubmit = async (e) => {
    e.preventDefault();
    if (!selectedChairId || !selectedCommittee) return;
    setChairSubmitting(true);
    setError(null);
    try {
      const updated = await assignAdminCommitteeChair(selectedCommittee.id, parseInt(selectedChairId, 10));
      setSelectedCommittee(updated);
      setSuccessMsg('Committee Chair updated successfully.');
      setShowChairModal(false);
      setSelectedChairId('');
      loadCommittees();
    } catch (err) {
      setError(err.message || 'Failed to assign committee chair');
    } finally {
      setChairSubmitting(false);
    }
  };

  const handleAddMemberSubmit = async (e) => {
    e.preventDefault();
    if (!newMemberForm.user_id || !selectedCommittee) return;
    setMemberSubmitting(true);
    setError(null);
    try {
      await addAdminCommitteeMember(selectedCommittee.id, {
        user_id: parseInt(newMemberForm.user_id, 10),
        role_in_committee: newMemberForm.role_in_committee,
      });
      const updated = await fetchAdminCommitteeDetail(selectedCommittee.id);
      setSelectedCommittee(updated);
      setSuccessMsg('Member added to committee successfully.');
      setShowAddMemberModal(false);
      setNewMemberForm({ user_id: '', role_in_committee: 'member' });
      loadCommittees();
    } catch (err) {
      setError(err.message || 'Failed to add member to committee');
    } finally {
      setMemberSubmitting(false);
    }
  };

  const handleRemoveMember = async (userId, memberName) => {
    if (!window.confirm(`Are you sure you want to remove "${memberName}" from this committee?`)) {
      return;
    }
    setError(null);
    try {
      await removeAdminCommitteeMember(selectedCommittee.id, userId);
      const updated = await fetchAdminCommitteeDetail(selectedCommittee.id);
      setSelectedCommittee(updated);
      setSuccessMsg(`Removed "${memberName}" from committee.`);
      loadCommittees();
    } catch (err) {
      setError(err.message || 'Failed to remove member from committee');
    }
  };

  // Eligible chairs (committee_chair or empowered_committee_chair)
  const eligibleChairs = useMemo(() => {
    return availableUsers.filter((u) => u.role === 'committee_chair' || u.role === 'empowered_committee_chair');
  }, [availableUsers]);

  // Eligible members (committee, committee_chair, empowered_committee)
  const eligibleMembers = useMemo(() => {
    return availableUsers.filter((u) =>
      ['committee', 'committee_chair', 'empowered_committee', 'empowered_committee_chair'].includes(u.role)
    );
  }, [availableUsers]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-[#600b0b]/10 text-[#600b0b]">
              <GraduationCap className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Committee Management</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Establish assessment committees, appoint authorized Chairs, and manage reviewer memberships across institutional frameworks.
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-xl transition shadow-xs"
          >
            <Plus className="w-4 h-4" />
            Create Committee
          </button>
        )}
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-600 hover:text-rose-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-600 hover:text-emerald-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Search & Filters */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search committees or chair..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
          />
        </form>

        <div className="flex flex-wrap gap-2 w-full md:w-auto">
          <select
            value={frameworkFilter}
            onChange={(e) => setFrameworkFilter(e.target.value)}
            className="px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
          >
            <option value="">All Frameworks</option>
            <option value="COLLEGE_2026">Colleges (COLLEGE_2026)</option>
            <option value="UNIVERSITY_2026">Universities (UNIVERSITY_2026)</option>
            <option value="ALL">Unified (ALL)</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
          >
            <option value="">All Statuses</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>

          <button
            onClick={loadCommittees}
            className="p-2 text-slate-600 hover:text-slate-900 border border-slate-200 rounded-xl hover:bg-slate-50 transition"
            title="Refresh List"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Committees Table / Grid */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">Loading committees...</div>
        ) : committees.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500 space-y-2">
            <Award className="w-8 h-8 mx-auto text-slate-300" />
            <p>No committees found matching your criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-50 border-b border-slate-100 font-semibold text-slate-600">
                <tr>
                  <th className="py-3 px-4">Committee Name</th>
                  <th className="py-3 px-4">Framework</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Committee Chair</th>
                  <th className="py-3 px-4">Members</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {committees.map((comm) => (
                  <tr key={comm.id} className="hover:bg-slate-50/50 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{comm.name}</div>
                      {comm.description && (
                        <div className="text-[11px] text-slate-500 line-clamp-1">{comm.description}</div>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-50 text-teal-800 border border-teal-200">
                        {comm.framework}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-800 border border-purple-200">
                        {comm.committee_type}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {comm.chair_name ? (
                        <div>
                          <div className="font-semibold text-slate-900">{comm.chair_name}</div>
                          <div className="text-[11px] text-slate-500 font-mono">{comm.chair_email}</div>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">No Chair Assigned</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700">
                        <Users className="w-3 h-3" />
                        {comm.member_count} member{comm.member_count !== 1 ? 's' : ''}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {comm.is_active ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-slate-400 font-semibold text-[11px]">
                          <XCircle className="w-3.5 h-3.5" /> Inactive
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => openCommitteeDetail(comm.id)}
                        className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
                      >
                        Manage Committee &rarr;
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Committee Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full overflow-hidden shadow-2xl border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Plus className="w-4 h-4 text-[#600b0b]" />
                Create Assessment Committee
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateSubmit} className="p-6 space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Committee Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. State Screening Committee - Colleges North"
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Description</label>
                <textarea
                  rows="2"
                  placeholder="Mandate and scope of this committee..."
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Framework *</label>
                  <select
                    value={createForm.framework}
                    onChange={(e) => setCreateForm({ ...createForm, framework: e.target.value })}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                  >
                    <option value="COLLEGE_2026">Colleges of Haryana (COLLEGE_2026)</option>
                    <option value="UNIVERSITY_2026">State Universities (UNIVERSITY_2026)</option>
                    <option value="ALL">Unified Committee (ALL)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Committee Type *</label>
                  <select
                    value={createForm.committee_type}
                    onChange={(e) => setCreateForm({ ...createForm, committee_type: e.target.value })}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                  >
                    <option value="SCREENING">Screening Committee</option>
                    <option value="EMPOWERED">Empowered Committee</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Appoint Initial Chair (Optional)</label>
                <select
                  value={createForm.chair_id}
                  onChange={(e) => setCreateForm({ ...createForm, chair_id: e.target.value })}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                >
                  <option value="">No Chair (Appoint Later)</option>
                  {eligibleChairs.map((chair) => (
                    <option key={chair.id} value={chair.id}>
                      {chair.full_name} ({chair.email}) &bull; {chair.role}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  Only users provisioned with the &quot;Screening Committee Chair&quot; role can be appointed as Chair.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSubmitting}
                  className="px-4 py-2 text-xs font-semibold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-lg transition shadow-xs"
                >
                  {createSubmitting ? 'Creating...' : 'Create Committee'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Committee Detail & Member Management Drawer / Modal */}
      {selectedCommittee && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl border border-slate-200">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-slate-900 text-sm">{selectedCommittee.name}</h3>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-50 text-teal-800 border border-teal-200">
                    {selectedCommittee.framework}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{selectedCommittee.description || 'No description provided'}</p>
              </div>
              <button onClick={() => setSelectedCommittee(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 overflow-y-auto space-y-6">
              {/* Chair Section */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1 flex items-center gap-1.5">
                    <Award className="w-3.5 h-3.5 text-amber-600" />
                    Committee Chair
                  </div>
                  {selectedCommittee.chair_name ? (
                    <div>
                      <div className="text-sm font-bold text-slate-900">{selectedCommittee.chair_name}</div>
                      <div className="text-xs text-slate-500 font-mono">{selectedCommittee.chair_email}</div>
                    </div>
                  ) : (
                    <div className="text-xs text-amber-700 italic">No Chair appointed for this committee.</div>
                  )}
                </div>

                {isAdmin && (
                  <button
                    onClick={() => {
                      setSelectedChairId(selectedCommittee.chair_id ? String(selectedCommittee.chair_id) : '');
                      setShowChairModal(true);
                    }}
                    className="px-3 py-1.5 text-xs font-semibold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-lg transition shrink-0"
                  >
                    {selectedCommittee.chair_name ? 'Replace Chair' : 'Assign Chair'}
                  </button>
                )}
              </div>

              {/* Members Section */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-slate-700" />
                    <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider">
                      Committee Members ({selectedCommittee.members?.length || 0})
                    </h4>
                  </div>
                  {isAdmin && (
                    <button
                      onClick={() => setShowAddMemberModal(true)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-teal-800 bg-teal-50 hover:bg-teal-100 rounded-lg border border-teal-200 transition"
                    >
                      <UserPlus className="w-3.5 h-3.5" />
                      Add Member
                    </button>
                  )}
                </div>

                {selectedCommittee.members?.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                    No members currently appointed to this committee.
                  </div>
                ) : (
                  <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-slate-100 font-semibold text-slate-600">
                        <tr>
                          <th className="py-2.5 px-3">Name & Email</th>
                          <th className="py-2.5 px-3">Role in Committee</th>
                          <th className="py-2.5 px-3">System Role</th>
                          {isAdmin && <th className="py-2.5 px-3 text-right">Action</th>}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {selectedCommittee.members.map((m) => (
                          <tr key={m.id} className="hover:bg-slate-50/50">
                            <td className="py-2.5 px-3">
                              <div className="font-semibold text-slate-900">{m.full_name}</div>
                              <div className="text-[11px] text-slate-500 font-mono">{m.email}</div>
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  m.role_in_committee === 'chair'
                                    ? 'bg-amber-100 text-amber-800'
                                    : 'bg-slate-100 text-slate-700'
                                }`}
                              >
                                {m.role_in_committee.toUpperCase()}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-[11px] text-slate-600 font-mono">
                              {m.user_role}
                            </td>
                            {isAdmin && (
                              <td className="py-2.5 px-3 text-right">
                                <button
                                  onClick={() => handleRemoveMember(m.user_id, m.full_name)}
                                  className="text-rose-600 hover:text-rose-800 p-1 rounded hover:bg-rose-50 transition"
                                  title="Remove member"
                                >
                                  <UserMinus className="w-3.5 h-3.5" />
                                </button>
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t border-slate-100 flex justify-end bg-slate-50">
              <button
                onClick={() => setSelectedCommittee(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-200 rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assign Chair Modal */}
      {showChairModal && selectedCommittee && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full overflow-hidden shadow-2xl border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <h3 className="font-bold text-slate-900 text-sm">Assign Committee Chair</h3>
              <button onClick={() => setShowChairModal(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleAssignChairSubmit} className="p-6 space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Select Chair Candidate *</label>
                <select
                  required
                  value={selectedChairId}
                  onChange={(e) => setSelectedChairId(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                >
                  <option value="">-- Choose Authorized Chair --</option>
                  {eligibleChairs.map((chair) => (
                    <option key={chair.id} value={chair.id}>
                      {chair.full_name} ({chair.email}) &bull; {chair.role}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  Assigning a chair will automatically reconcile their statutory ReviewerAuthorization for framework &quot;{selectedCommittee.framework}&quot;.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowChairModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={chairSubmitting}
                  className="px-4 py-2 text-xs font-semibold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-lg transition shadow-xs"
                >
                  {chairSubmitting ? 'Saving...' : 'Confirm Chair'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Member Modal */}
      {showAddMemberModal && selectedCommittee && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full overflow-hidden shadow-2xl border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <h3 className="font-bold text-slate-900 text-sm">Add Committee Member</h3>
              <button onClick={() => setShowAddMemberModal(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleAddMemberSubmit} className="p-6 space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Select Reviewer Candidate *</label>
                <select
                  required
                  value={newMemberForm.user_id}
                  onChange={(e) => setNewMemberForm({ ...newMemberForm, user_id: e.target.value })}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                >
                  <option value="">-- Choose Authorized Reviewer --</option>
                  {eligibleMembers
                    .filter((m) => !selectedCommittee.members?.some((existing) => existing.user_id === m.id))
                    .map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.full_name} ({m.email}) &bull; {m.role}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Role in Committee</label>
                <select
                  value={newMemberForm.role_in_committee}
                  onChange={(e) => setNewMemberForm({ ...newMemberForm, role_in_committee: e.target.value })}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                >
                  <option value="member">Committee Member (Reviewer)</option>
                  <option value="chair">Committee Chair</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddMemberModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={memberSubmitting}
                  className="px-4 py-2 text-xs font-semibold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-lg transition shadow-xs"
                >
                  {memberSubmitting ? 'Adding...' : 'Add Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
