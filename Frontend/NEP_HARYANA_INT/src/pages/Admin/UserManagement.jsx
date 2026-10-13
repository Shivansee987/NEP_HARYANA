import { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Users,
  UserPlus,
  Search,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Building,
  GraduationCap,
  CheckCircle2,
  XCircle,
  History,
  Lock,
  Unlock,
  RefreshCw,
  X,
  AlertCircle,
  Eye,
  KeyRound,
  Send,
  Clock,
  UserX,
  Mail,
  Trash2,
  Copy,
  ExternalLink,
  Check,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext.jsx';
import {
  fetchAdminUsers,
  fetchAdminUserDetail,
  createAdminUser,
  updateAdminUser,
  deleteAdminUser,
  resetAdminUserPassword,
  manageAdminUserCommittee,
  resendAdminUserInvitation,
  revokeAdminUserInvitation,
} from '../../api/admin.js';

const ROLE_OPTIONS = [
  { value: 'state_admin', label: 'State Admin (HSHEC State)', badge: 'bg-rose-100 text-rose-800 border-rose-200' },
  { value: 'committee_chair', label: 'Screening Committee Chair', badge: 'bg-amber-100 text-amber-800 border-amber-200' },
  { value: 'committee', label: 'Screening Committee Member', badge: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  { value: 'council_admin', label: 'Council Admin Overseer', badge: 'bg-blue-100 text-blue-800 border-blue-200' },
  { value: 'head_admin', label: 'Head Administrator', badge: 'bg-purple-100 text-purple-800 border-purple-200' },
  { value: 'sub_admin', label: 'Sub Administrator', badge: 'bg-indigo-100 text-indigo-800 border-indigo-200' },
  { value: 'admin', label: 'DHE Admin (Legacy)', badge: 'bg-slate-100 text-slate-800 border-slate-200' },
  { value: 'empowered_committee_chair', label: 'Empowered Committee Chair', badge: 'bg-orange-100 text-orange-800 border-orange-200' },
  { value: 'empowered_committee', label: 'Empowered Committee Member', badge: 'bg-teal-100 text-teal-800 border-teal-200' },
  { value: 'principal', label: 'College Principal', badge: 'bg-slate-100 text-slate-800 border-slate-200' },
  { value: 'nodal_officer', label: 'University Nodal Officer', badge: 'bg-cyan-100 text-cyan-800 border-cyan-200' },
  { value: 'university_admin', label: 'University Administrator', badge: 'bg-sky-100 text-sky-800 border-sky-200' },
];

const PRIVILEGED_ROLES = new Set([
  'head_admin',
  'state_admin',
  'sub_admin',
  'council_admin',
  'admin',
  'committee',
  'committee_chair',
  'empowered_committee',
  'empowered_committee_chair',
]);

export default function UserManagement() {
  const { user: currentUser } = useAuth();
  const [searchParams] = useSearchParams();
  const isHeadAdmin = currentUser?.role === 'head_admin' || currentUser?.is_superuser;

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');

  // Modals
  const [selectedUser, setSelectedUser] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(null); // user object to change role for
  const [newRoleSelection, setNewRoleSelection] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(null); // user object to permanently remove
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  // Password reset modal state
  const [showPasswordModal, setShowPasswordModal] = useState(null);
  const [newPasswordInput, setNewPasswordInput] = useState('');
  const [resetSubmitting, setResetSubmitting] = useState(false);

  // Committee authorization modal state
  const [showCommitteeModal, setShowCommitteeModal] = useState(null);
  const [committeeActionForm, setCommitteeActionForm] = useState({ framework: 'COLLEGE_2026', action: 'assign' });
  const [committeeSubmitting, setCommitteeSubmitting] = useState(false);

  // Create form state
  const [createForm, setCreateForm] = useState({
    email: '',
    fullName: '',
    role: 'state_admin',
    phoneNumber: '',
    password: '',
    committeeFramework: 'COLLEGE_2026',
    sendActivationEmail: true,
  });
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createResult, setCreateResult] = useState(null);
  const [copiedActivationUrl, setCopiedActivationUrl] = useState(false);
  const [actionLoading, setActionLoading] = useState({});

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (search) params.q = search;
      if (roleFilter) params.role = roleFilter;
      if (statusFilter !== '') params.is_active = statusFilter;
      if (typeFilter !== 'ALL') params.institution_type = typeFilter;
      params.page_size = 100;

      const res = await fetchAdminUsers(params);
      setUsers(res?.results || []);
    } catch (err) {
      setError(err?.message || 'Failed to load user list.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, [roleFilter, statusFilter, typeFilter]);

  // Support direct action from dashboard links (e.g. /admin/users?action=create)
  useEffect(() => {
    if (searchParams.get('action') === 'create') {
      setShowCreateModal(true);
    }
  }, [searchParams]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadUsers();
  };

  const handleOpenDetail = async (user) => {
    setSelectedUser(null);
    setDetailLoading(true);
    try {
      const data = await fetchAdminUserDetail(user.id);
      setSelectedUser(data);
    } catch (err) {
      setError(err?.message || 'Failed to load user details.');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleToggleActive = async (targetUser) => {
    if (!isHeadAdmin) {
      setError('Only the Head Administrator can activate or deactivate accounts.');
      return;
    }

    const nextState = !targetUser.is_active;
    const confirmMsg = nextState
      ? `Re-activate account for ${targetUser.email}?`
      : `Deactivate account for ${targetUser.email}? This will immediately revoke login access.`;

    if (!window.confirm(confirmMsg)) return;

    try {
      await updateAdminUser(targetUser.id, { is_active: nextState });
      setSuccessMsg(`Account ${nextState ? 'activated' : 'deactivated'} for ${targetUser.email}`);
      loadUsers();
    } catch (err) {
      setError(err?.detail || err?.message || 'Failed to update account status.');
    }
  };

  const handleRoleChangeSubmit = async () => {
    if (!showRoleModal || !newRoleSelection) return;
    if (!isHeadAdmin) {
      setError('Only the Head Administrator can modify user roles.');
      return;
    }

    try {
      await updateAdminUser(showRoleModal.id, { role: newRoleSelection });
      setSuccessMsg(`Role updated to '${newRoleSelection}' for ${showRoleModal.email}`);
      setShowRoleModal(null);
      loadUsers();
    } catch (err) {
      setError(err?.detail || err?.message || 'Failed to update role.');
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setCreateSubmitting(true);
    setError(null);
    try {
      const payload = {
        email: createForm.email,
        full_name: createForm.fullName,
        role: createForm.role,
        phone_number: createForm.phoneNumber,
        send_invite: createForm.sendActivationEmail,
      };
      if (!createForm.sendActivationEmail && createForm.password) {
        payload.password = createForm.password;
      }
      if (createForm.committeeFramework && ['committee', 'committee_chair', 'empowered_committee', 'empowered_committee_chair'].includes(createForm.role)) {
        payload.committee_framework = createForm.committeeFramework;
      }
      const res = await createAdminUser(payload);
      setCreateResult(res);
      setSuccessMsg(`User '${res.email}' created successfully.`);
      loadUsers();
      setCreateForm({
        email: '',
        fullName: '',
        role: 'state_admin',
        phoneNumber: '',
        password: '',
        committeeFramework: 'COLLEGE_2026',
        sendActivationEmail: true,
      });
    } catch (err) {
      setError(err?.detail || err?.message || 'Failed to create user.');
    } finally {
      setCreateSubmitting(false);
    }
  };

  const handleResendInvitation = async (targetUser) => {
    setActionLoading((prev) => ({ ...prev, [targetUser.id]: 'resend' }));
    setError(null);
    try {
      const res = await resendAdminUserInvitation(targetUser.id);
      setSuccessMsg(
        `Activation invitation resent to ${targetUser.email}. ${
          res.email_sent ? 'Email delivered via mail service.' : 'Invitation link generated and queued.'
        }`
      );
      loadUsers();
    } catch (err) {
      setError(err?.detail || err?.message || 'Failed to resend activation invitation.');
    } finally {
      setActionLoading((prev) => ({ ...prev, [targetUser.id]: null }));
    }
  };

  const handleRevokeInvitation = async (targetUser) => {
    if (
      !window.confirm(
        `Revoke outstanding activation invitation for ${targetUser.email}? Any previously sent activation link will become immediately invalid.`
      )
    ) {
      return;
    }
    setActionLoading((prev) => ({ ...prev, [targetUser.id]: 'revoke' }));
    setError(null);
    try {
      await revokeAdminUserInvitation(targetUser.id);
      setSuccessMsg(`Activation invitation revoked successfully for ${targetUser.email}.`);
      loadUsers();
    } catch (err) {
      setError(err?.detail || err?.message || 'Failed to revoke activation invitation.');
    } finally {
      setActionLoading((prev) => ({ ...prev, [targetUser.id]: null }));
    }
  };

  const handleResetPasswordSubmit = async () => {
    if (!showPasswordModal) return;
    if (!isHeadAdmin) {
      setError('Only the Head Administrator can reset user account passwords.');
      return;
    }
    setResetSubmitting(true);
    try {
      await resetAdminUserPassword(showPasswordModal.id, newPasswordInput || null);
      setSuccessMsg(`Password reset securely for ${showPasswordModal.email}`);
      setShowPasswordModal(null);
      setNewPasswordInput('');
      loadUsers();
    } catch (err) {
      setError(err?.detail || err?.message || 'Failed to reset password.');
    } finally {
      setResetSubmitting(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!showDeleteModal) return;
    if (!isHeadAdmin) {
      setError('Only the Head Administrator can remove users.');
      return;
    }
    setDeleteSubmitting(true);
    setError(null);
    try {
      const res = await deleteAdminUser(showDeleteModal.id);
      setSuccessMsg(res?.message || `User '${showDeleteModal.email}' removed successfully.`);
      setShowDeleteModal(null);
      loadUsers();
    } catch (err) {
      setError(err?.detail || err?.message || 'Failed to remove user account.');
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const handleCommitteeAssignmentSubmit = async () => {
    if (!showCommitteeModal) return;
    setCommitteeSubmitting(true);
    try {
      await manageAdminUserCommittee(showCommitteeModal.id, {
        framework: committeeActionForm.framework,
        action: committeeActionForm.action,
      });
      setSuccessMsg(`Committee framework ${committeeActionForm.action}ed successfully for ${showCommitteeModal.email}`);
      setShowCommitteeModal(null);
      loadUsers();
      if (selectedUser && selectedUser.id === showCommitteeModal.id) {
        const updated = await fetchAdminUserDetail(showCommitteeModal.id);
        setSelectedUser(updated);
      }
    } catch (err) {
      setError(err?.detail || err?.message || 'Failed to update committee authorization.');
    } finally {
      setCommitteeSubmitting(false);
    }
  };

  // Stats calculation
  const stats = useMemo(() => {
    const total = users.length;
    const active = users.filter((u) => u.is_active).length;
    const admins = users.filter((u) => ['head_admin', 'state_admin', 'sub_admin', 'council_admin', 'admin'].includes(u.role)).length;
    const committees = users.filter((u) => u.role.includes('committee')).length;
    return { total, active, admins, committees };
  }, [users]);

  const getRoleMeta = (roleKey) => {
    return (
      ROLE_OPTIONS.find((r) => r.value === roleKey) || {
        value: roleKey,
        label: roleKey,
        badge: 'bg-slate-100 text-slate-700 border-slate-200',
      }
    );
  };

  return (
    <div className="space-y-6 pb-12 max-w-7xl mx-auto px-4 sm:px-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">User & Role Management</h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#ebdcd0] text-[#600b0b]">
              <ShieldCheck className="w-3.5 h-3.5" />
              Central Control Plane
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Department of Higher Education, Haryana — Role Hierarchy, Account Governance & Append-Only Audit Logs
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={loadUsers}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => {
              setCreateResult(null);
              setShowCreateModal(true);
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-lg transition shadow-xs cursor-pointer"
          >
            <UserPlus className="w-4 h-4" />
            Create / Invite User
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1 text-sm text-red-800">
            <span className="font-semibold">Operation Error:</span> {error}
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="flex-1 text-sm text-emerald-800">
            <span className="font-semibold">Success:</span> {successMsg}
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Authority Level Callout */}
      {!isHeadAdmin && (
        <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 flex items-center gap-3 text-xs text-amber-800">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            You are signed in with Sub-Admin authority. Role assignments and account deactivations are restricted
            strictly to the Head Administrator.
          </span>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Users</span>
            <Users className="w-4 h-4 text-slate-400" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">{stats.total}</p>
          <span className="text-[11px] text-emerald-600 font-medium">{stats.active} Active accounts</span>
        </div>
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Platform Admins</span>
            <Shield className="w-4 h-4 text-purple-500" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">{stats.admins}</p>
          <span className="text-[11px] text-purple-600 font-medium">Head & Sub Admins</span>
        </div>
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Committee Officers</span>
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">{stats.committees}</p>
          <span className="text-[11px] text-emerald-600 font-medium">Screening & Empowered</span>
        </div>
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Institutions Linked</span>
            <Building className="w-4 h-4 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {users.filter((u) => u.institution_type !== 'NONE').length}
          </p>
          <span className="text-[11px] text-slate-500 font-medium">Colleges & Universities</span>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search */}
          <form onSubmit={handleSearchSubmit} className="flex-1 relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, email, phone, or AISHE code..."
              className="w-full pl-9 pr-4 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20 focus:border-[#600b0b]"
            />
          </form>

          {/* Role Filter */}
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-3 py-2 text-xs border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
          >
            <option value="">All Roles</option>
            {ROLE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 text-xs border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
          >
            <option value="">All Statuses</option>
            <option value="true">Active Only</option>
            <option value="false">Inactive / Suspended</option>
          </select>
        </div>

        {/* Institution Type Tabs */}
        <div className="flex items-center gap-1.5 border-t border-slate-100 pt-3">
          <span className="text-[11px] font-semibold text-slate-400 mr-2 uppercase tracking-wider">Institution:</span>
          {['ALL', 'UNIVERSITY', 'COLLEGE', 'NONE'].map((tab) => (
            <button
              key={tab}
              onClick={() => setTypeFilter(tab)}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition ${
                typeFilter === tab
                  ? 'bg-[#600b0b] text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {tab === 'ALL'
                ? 'All Types'
                : tab === 'UNIVERSITY'
                ? 'Universities'
                : tab === 'COLLEGE'
                ? 'Colleges'
                : 'Department Admins'}
            </button>
          ))}
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-3 border-slate-200 border-t-[#600b0b] rounded-full animate-spin" />
            <p className="text-xs text-slate-500 font-medium">Loading user directory...</p>
          </div>
        ) : users.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <Users className="w-10 h-10 text-slate-300 mx-auto" />
            <p className="text-sm font-semibold text-slate-700">No users found</p>
            <p className="text-xs text-slate-400">Try adjusting your search criteria or role filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Institution / AISHE</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => {
                  const roleMeta = getRoleMeta(u.role);
                  return (
                    <tr key={u.id} className="hover:bg-slate-50/70 transition">
                      <td className="py-3.5 px-4">
                        <div className="flex flex-col">
                          <span className="font-semibold text-slate-900">{u.full_name || 'Unnamed User'}</span>
                          <span className="text-[11px] text-slate-500 font-mono">{u.email}</span>
                          {u.phone_number && (
                            <span className="text-[10px] text-slate-400">📞 {u.phone_number}</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex flex-col gap-1">
                          <span
                            className={`inline-block px-2.5 py-1 rounded-full text-[11px] font-semibold border ${roleMeta.badge}`}
                          >
                            {roleMeta.label}
                          </span>
                          {u.reviewer_authorizations?.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {u.reviewer_authorizations.map((auth, idx) => (
                                <span
                                  key={idx}
                                  className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 font-mono border border-slate-200"
                                >
                                  {auth.framework}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        {u.institution_name ? (
                          <div className="flex flex-col">
                            <span className="text-slate-800 font-medium line-clamp-1">{u.institution_name}</span>
                            {u.aishe_code && (
                              <span className="text-[10px] text-slate-400 font-mono">
                                AISHE: {u.aishe_code}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">DHE Central</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        {!u.is_activated || u.has_pending_invitation ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">
                            <Clock className="w-3 h-3" /> Pending Activation
                          </span>
                        ) : u.is_active ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-red-700 bg-red-50 px-2 py-0.5 rounded-md border border-red-200">
                            <XCircle className="w-3 h-3" /> Suspended
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => handleOpenDetail(u)}
                            title="View Details & Audit Logs"
                            className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-md transition cursor-pointer"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          {/* Resend Invitation button */}
                          {(!u.is_activated || u.has_pending_invitation || !u.is_active) && (
                            <button
                              onClick={() => handleResendInvitation(u)}
                              disabled={Boolean(actionLoading[u.id]) || (!isHeadAdmin && currentUser?.role !== 'state_admin')}
                              title={
                                isHeadAdmin || currentUser?.role === 'state_admin'
                                  ? 'Resend Activation Invitation Email'
                                  : 'Resending invitations requires Admin authority'
                              }
                              className={`p-1.5 rounded-md transition ${
                                isHeadAdmin || currentUser?.role === 'state_admin'
                                  ? 'text-blue-600 hover:text-blue-900 hover:bg-blue-50 cursor-pointer'
                                  : 'text-slate-300 cursor-not-allowed'
                              }`}
                            >
                              <Send className={`w-4 h-4 ${actionLoading[u.id] === 'resend' ? 'animate-spin' : ''}`} />
                            </button>
                          )}

                          {/* Revoke Invitation button */}
                          {u.has_pending_invitation && isHeadAdmin && (
                            <button
                              onClick={() => handleRevokeInvitation(u)}
                              disabled={Boolean(actionLoading[u.id])}
                              title="Revoke Outstanding Activation Invitation"
                              className="p-1.5 rounded-md text-rose-500 hover:text-rose-800 hover:bg-rose-50 cursor-pointer transition"
                            >
                              <UserX className={`w-4 h-4 ${actionLoading[u.id] === 'revoke' ? 'opacity-50' : ''}`} />
                            </button>
                          )}

                          {/* Committee Assignment button */}
                          {['committee', 'committee_chair', 'empowered_committee', 'empowered_committee_chair'].includes(u.role) && (
                            <button
                              onClick={() => {
                                setShowCommitteeModal(u);
                                setCommitteeActionForm({ framework: 'COLLEGE_2026', action: 'assign' });
                              }}
                              disabled={!isHeadAdmin && currentUser?.role !== 'state_admin'}
                              title={
                                isHeadAdmin || currentUser?.role === 'state_admin'
                                  ? 'Manage Committee Authorizations'
                                  : 'Committee assignment requires Admin authority'
                              }
                              className={`p-1.5 rounded-md transition ${
                                isHeadAdmin || currentUser?.role === 'state_admin'
                                  ? 'text-teal-600 hover:text-teal-900 hover:bg-teal-50 cursor-pointer'
                                  : 'text-slate-300 cursor-not-allowed'
                              }`}
                            >
                              <GraduationCap className="w-4 h-4" />
                            </button>
                          )}

                          {/* Password Reset button - enabled only for Head Admin */}
                          <button
                            onClick={() => {
                              setShowPasswordModal(u);
                              setNewPasswordInput('');
                            }}
                            disabled={!isHeadAdmin}
                            title={isHeadAdmin ? 'Reset User Password' : 'Password reset requires Head Administrator'}
                            className={`p-1.5 rounded-md transition ${
                              isHeadAdmin
                                ? 'text-amber-600 hover:text-amber-900 hover:bg-amber-50 cursor-pointer'
                                : 'text-slate-300 cursor-not-allowed'
                            }`}
                          >
                            <KeyRound className="w-4 h-4" />
                          </button>

                          {/* Role edit button - enabled only for Head Admin */}
                          <button
                            onClick={() => {
                              setShowRoleModal(u);
                              setNewRoleSelection(u.role);
                            }}
                            disabled={!isHeadAdmin}
                            title={isHeadAdmin ? 'Modify Role' : 'Role modification requires Head Administrator'}
                            className={`p-1.5 rounded-md transition ${
                              isHeadAdmin
                                ? 'text-purple-600 hover:text-purple-900 hover:bg-purple-50 cursor-pointer'
                                : 'text-slate-300 cursor-not-allowed'
                            }`}
                          >
                            <Shield className="w-4 h-4" />
                          </button>

                          {/* Toggle Active status */}
                          <button
                            onClick={() => handleToggleActive(u)}
                            disabled={!isHeadAdmin}
                            title={
                              !isHeadAdmin
                                ? 'Account status modification requires Head Administrator'
                                : u.is_active
                                ? 'Deactivate Account'
                                : 'Activate Account'
                            }
                            className={`p-1.5 rounded-md transition ${
                              !isHeadAdmin
                                ? 'text-slate-300 cursor-not-allowed'
                                : u.is_active
                                ? 'text-amber-600 hover:text-amber-800 hover:bg-amber-50 cursor-pointer'
                                : 'text-emerald-600 hover:text-emerald-900 hover:bg-emerald-50 cursor-pointer'
                            }`}
                          >
                            {u.is_active ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                          </button>

                          {/* Permanently Remove User button - Head Admin exclusive */}
                          <button
                            onClick={() => setShowDeleteModal(u)}
                            disabled={!isHeadAdmin || u.id === currentUser?.id}
                            title={
                              !isHeadAdmin
                                ? 'Removing users requires Head Administrator authority'
                                : u.id === currentUser?.id
                                ? 'You cannot remove your own account'
                                : `Permanently remove ${u.email}`
                            }
                            className={`p-1.5 rounded-md transition ${
                              !isHeadAdmin || u.id === currentUser?.id
                                ? 'text-slate-300 cursor-not-allowed'
                                : 'text-rose-600 hover:text-rose-900 hover:bg-rose-50 cursor-pointer'
                            }`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* User Details & Audit Trail Modal */}
      {selectedUser && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-[#600b0b]" />
                <h3 className="font-bold text-slate-900 text-sm">User Details & Audit History</h3>
              </div>
              <button onClick={() => setSelectedUser(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6 overflow-y-auto">
              {/* Profile Card */}
              <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-400 font-semibold block">Full Name</span>
                  <span className="font-bold text-slate-800 text-sm">{selectedUser.full_name}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold block">Email Address</span>
                  <span className="font-mono text-slate-800">{selectedUser.email}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold block">Assigned Role</span>
                  <span className="font-semibold text-purple-700">{getRoleMeta(selectedUser.role).label}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold block">Account Status</span>
                  <span className={selectedUser.is_active ? 'text-emerald-700 font-bold' : 'text-red-700 font-bold'}>
                    {selectedUser.is_active ? 'Active' : 'Suspended'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold block">Activation Lifecycle</span>
                  <span className={selectedUser.is_activated ? 'text-emerald-700 font-bold' : 'text-amber-700 font-bold'}>
                    {selectedUser.is_activated ? 'Activated (Password Set)' : selectedUser.has_pending_invitation ? 'Pending Activation Link' : 'Pending Password Setup'}
                  </span>
                </div>
                {selectedUser.institution_name && (
                  <div className="col-span-2">
                    <span className="text-slate-400 font-semibold block">Linked Institution</span>
                    <span className="text-slate-800 font-medium">{selectedUser.institution_name}</span>
                    {selectedUser.aishe_code && (
                      <span className="text-slate-500 font-mono ml-2">({selectedUser.aishe_code})</span>
                    )}
                  </div>
                )}
              </div>

              {/* Committee Authorizations */}
              {selectedUser.reviewer_authorizations && selectedUser.reviewer_authorizations.length > 0 && (
                <div className="bg-teal-50/50 p-4 rounded-xl border border-teal-200 text-xs">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-teal-900 flex items-center gap-1.5">
                      <GraduationCap className="w-4 h-4 text-teal-700" />
                      Active Committee Framework Authorizations
                    </span>
                    {(isHeadAdmin || currentUser?.role === 'state_admin') && (
                      <button
                        onClick={() => {
                          setShowCommitteeModal(selectedUser);
                          setCommitteeActionForm({ framework: 'COLLEGE_2026', action: 'remove' });
                        }}
                        className="text-[11px] font-semibold text-teal-700 hover:text-teal-900 underline cursor-pointer"
                      >
                        Modify Frameworks
                      </button>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedUser.reviewer_authorizations.map((auth, idx) => (
                      <span key={idx} className="px-2 py-1 rounded-md bg-white border border-teal-300 font-mono text-[11px] text-teal-900">
                        {auth.framework} {auth.institution_id ? `(${auth.institution_id})` : ''}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Append-Only Audit Trail */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <History className="w-4 h-4 text-slate-500" />
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                    Chronological Audit Trail
                  </h4>
                </div>
                {selectedUser.audit_logs?.length === 0 ? (
                  <p className="text-xs text-slate-400 italic bg-slate-50 p-3 rounded-lg border border-slate-100">
                    No administrative changes recorded for this account yet.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {selectedUser.audit_logs.map((log) => (
                      <div
                        key={log.id}
                        className="p-3 bg-white border border-slate-200 rounded-lg text-xs space-y-1 hover:border-slate-300 transition"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-800">{log.action}</span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {new Date(log.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-500">
                          <span>Authorized by: {log.actor_email}</span>
                          {log.ip_address && <span className="font-mono">IP: {log.ip_address}</span>}
                        </div>
                        {log.details && Object.keys(log.details).length > 0 && (
                          <div className="bg-slate-50 p-2 rounded text-[11px] font-mono text-slate-700 mt-1">
                            {JSON.stringify(log.details)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Role Assignment Modal */}
      {showRoleModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full overflow-hidden shadow-2xl border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <h3 className="font-bold text-slate-900 text-sm">Assign New Role</h3>
              <button onClick={() => setShowRoleModal(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="text-xs bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Target Account:</span>
                <span className="font-bold text-slate-800">{showRoleModal.full_name}</span>
                <span className="font-mono text-slate-600 block text-[11px]">{showRoleModal.email}</span>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1.5">Select Role</label>
                <select
                  value={newRoleSelection}
                  onChange={(e) => setNewRoleSelection(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                >
                  {ROLE_OPTIONS.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg text-xs text-purple-900">
                ⚠️ This role assignment will take effect immediately and will be recorded in the immutable audit log.
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setShowRoleModal(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRoleChangeSubmit}
                  className="px-4 py-2 text-xs font-semibold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-lg transition shadow-xs"
                >
                  Confirm Role Change
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create / Invite User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full overflow-hidden shadow-2xl border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-[#600b0b]" />
                <h3 className="font-bold text-slate-900 text-sm">Create / Invite User</h3>
              </div>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            {createResult ? (
              <div className="p-6 space-y-4">
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-center space-y-2">
                  <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
                  <h4 className="font-bold text-emerald-900 text-sm">User Provisioned Successfully!</h4>
                  <p className="text-xs text-emerald-800">
                    Account for <span className="font-mono font-semibold">{createResult.email}</span> has been created.
                  </p>
                </div>

                {createResult.activation_url && (
                  <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-amber-900 flex items-center gap-1.5">
                        <KeyRound className="w-4 h-4 text-amber-700" />
                        Activation Link (Direct Access / Dev Testing):
                      </span>
                      <a
                        href={createResult.activation_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] font-semibold text-[#600b0b] hover:underline flex items-center gap-1"
                      >
                        Open Page <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        readOnly
                        value={createResult.activation_url}
                        className="w-full px-2.5 py-1.5 text-[11px] font-mono bg-white border border-amber-200 rounded-lg text-slate-700 select-all"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(createResult.activation_url);
                          setCopiedActivationUrl(true);
                          setTimeout(() => setCopiedActivationUrl(false), 2000);
                        }}
                        className="px-3 py-1.5 text-xs font-semibold bg-amber-700 hover:bg-amber-800 text-white rounded-lg flex items-center gap-1 shrink-0 transition shadow-xs"
                      >
                        {copiedActivationUrl ? (
                          <>
                            <Check className="w-3.5 h-3.5" /> Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" /> Copy
                          </>
                        )}
                      </button>
                    </div>
                    <p className="text-[10.5px] text-amber-800 leading-relaxed">
                      💡 <strong>How it functions:</strong> In production with SMTP configured, this single-use link is automatically emailed to <strong>{createResult.email}</strong>. For development or manual onboarding, you can copy or open it directly right now.
                    </p>
                  </div>
                )}

                <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center gap-1.5 font-bold text-blue-900">
                    <ShieldCheck className="w-4 h-4 text-blue-700" />
                    Security & Activation Lifecycle:
                  </div>
                  <p className="text-[11px] text-blue-800">
                    {createResult.has_pending_invitation || !createResult.is_activated ? (
                      <>An activation invitation was securely dispatched. The administrator must click their link to establish their password and activate their account. Tokens are hashed (SHA-256) and never logged.</>
                    ) : (
                      <>Account provisioned securely without credential leakage. The authorized officer may now log in using their credentials or request a password reset from the Head Administrator.</>
                    )}
                  </p>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => {
                      setCreateResult(null);
                      setShowCreateModal(false);
                    }}
                    className="px-4 py-2 text-xs font-semibold text-white bg-[#600b0b] rounded-lg hover:bg-[#4a0808]"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreateUser} className="p-6 space-y-4">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Full Name</label>
                  <input
                    type="text"
                    required
                    value={createForm.fullName}
                    onChange={(e) => setCreateForm({ ...createForm, fullName: e.target.value })}
                    placeholder="e.g. Dr. Rajesh Sharma"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Email Address</label>
                  <input
                    type="email"
                    required
                    value={createForm.email}
                    onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                    placeholder="officer@dhe.haryana.gov.in"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Role</label>
                  <select
                    value={createForm.role}
                    onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                  >
                    {ROLE_OPTIONS.map((r) => {
                      const isPriv = PRIVILEGED_ROLES.has(r.value);
                      if (isPriv && !isHeadAdmin) return null;
                      return (
                        <option key={r.value} value={r.value}>
                          {r.label}
                        </option>
                      );
                    })}
                  </select>
                </div>

                {['committee', 'committee_chair', 'empowered_committee', 'empowered_committee_chair'].includes(createForm.role) && (
                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1">Committee Framework Scope</label>
                    <select
                      value={createForm.committeeFramework}
                      onChange={(e) => setCreateForm({ ...createForm, committeeFramework: e.target.value })}
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                    >
                      <option value="COLLEGE_2026">Colleges of Haryana Framework (COLLEGE_2026)</option>
                      <option value="UNIVERSITY_2026">State Universities Framework (UNIVERSITY_2026)</option>
                      <option value="ALL">Unified Committee (All Frameworks)</option>
                    </select>
                  </div>
                )}

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Contact Phone (Optional)</label>
                  <input
                    type="tel"
                    value={createForm.phoneNumber}
                    onChange={(e) => setCreateForm({ ...createForm, phoneNumber: e.target.value })}
                    placeholder="9876543210"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                  />
                </div>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-3">
                  <div className="flex items-start gap-2.5">
                    <input
                      type="checkbox"
                      id="sendActivationEmail"
                      checked={createForm.sendActivationEmail}
                      onChange={(e) => setCreateForm({ ...createForm, sendActivationEmail: e.target.checked })}
                      className="mt-0.5 rounded text-[#600b0b] focus:ring-[#600b0b]"
                    />
                    <label htmlFor="sendActivationEmail" className="text-xs text-slate-800 cursor-pointer">
                      <span className="font-semibold block text-slate-900">
                        Send Secure Activation Email (Recommended)
                      </span>
                      <span className="text-[11px] text-slate-500 block mt-0.5">
                        Generates a single-use, 48-hour cryptographic token. The officer creates their own password securely upon verification.
                      </span>
                    </label>
                  </div>

                  {!createForm.sendActivationEmail && (
                    <div className="pt-2 border-t border-slate-200">
                      <label className="text-xs font-semibold text-slate-700 block mb-1">
                        Manual Initial Password (Optional — auto-generated if left blank)
                      </label>
                      <input
                        type="password"
                        value={createForm.password}
                        onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                        placeholder="Min 8 characters"
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20 bg-white"
                      />
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
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
                    {createSubmitting ? 'Creating...' : 'Create Account'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Password Reset Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full overflow-hidden shadow-2xl border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-amber-600" />
                <h3 className="font-bold text-slate-900 text-sm">Secure Password Reset</h3>
              </div>
              <button onClick={() => setShowPasswordModal(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="text-xs bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Target Account:</span>
                <span className="font-bold text-slate-800">{showPasswordModal.full_name}</span>
                <span className="font-mono text-slate-600 block text-[11px]">{showPasswordModal.email}</span>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  New Password (Optional — auto-generated if left blank)
                </label>
                <input
                  type="password"
                  value={newPasswordInput}
                  onChange={(e) => setNewPasswordInput(e.target.value)}
                  placeholder="Min 8 characters (or leave blank to auto-generate)"
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                />
              </div>

              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900">
                ⚠️ Resetting the password will immediately invalidate existing sessions and record an audit log entry.
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={resetSubmitting}
                  onClick={handleResetPasswordSubmit}
                  className="px-4 py-2 text-xs font-semibold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-lg transition shadow-xs"
                >
                  {resetSubmitting ? 'Resetting...' : 'Confirm Password Reset'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Committee Authorization Modal */}
      {showCommitteeModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full overflow-hidden shadow-2xl border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <GraduationCap className="w-5 h-5 text-teal-700" />
                <h3 className="font-bold text-slate-900 text-sm">Committee Framework Authorization</h3>
              </div>
              <button onClick={() => setShowCommitteeModal(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="text-xs bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Reviewer Account:</span>
                <span className="font-bold text-slate-800">{showCommitteeModal.full_name}</span>
                <span className="font-mono text-slate-600 block text-[11px]">{showCommitteeModal.email}</span>
                <span className="text-purple-700 font-semibold block text-[11px] mt-1">
                  Role: {getRoleMeta(showCommitteeModal.role).label}
                </span>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Action</label>
                <select
                  value={committeeActionForm.action}
                  onChange={(e) => setCommitteeActionForm({ ...committeeActionForm, action: e.target.value })}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                >
                  <option value="assign">Assign Framework Scope</option>
                  <option value="remove">Revoke / Remove Framework Scope</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Target Framework</label>
                <select
                  value={committeeActionForm.framework}
                  onChange={(e) => setCommitteeActionForm({ ...committeeActionForm, framework: e.target.value })}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#600b0b]/20"
                >
                  <option value="COLLEGE_2026">Colleges of Haryana Framework (COLLEGE_2026)</option>
                  <option value="UNIVERSITY_2026">State Universities Framework (UNIVERSITY_2026)</option>
                  <option value="ALL">Unified Committee (All Frameworks)</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCommitteeModal(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={committeeSubmitting}
                  onClick={handleCommitteeAssignmentSubmit}
                  className="px-4 py-2 text-xs font-semibold text-white bg-[#600b0b] hover:bg-[#4a0808] rounded-lg transition shadow-xs"
                >
                  {committeeSubmitting ? 'Updating...' : 'Save Authorization'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Permanently Remove User Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-rose-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="bg-rose-50 border-b border-rose-100 p-5 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-rose-100 border border-rose-200 flex items-center justify-center text-rose-700">
                  <Trash2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">Remove User Account</h3>
                  <p className="text-[11px] text-rose-700 font-medium">Head Administrator Apex Authority</p>
                </div>
              </div>
              <button
                onClick={() => setShowDeleteModal(null)}
                disabled={deleteSubmitting}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Full Name:</span>
                  <span className="font-bold text-slate-900">{showDeleteModal.full_name || 'Unnamed User'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Email:</span>
                  <span className="font-mono font-semibold text-slate-800">{showDeleteModal.email}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Assigned Role:</span>
                  <span className="font-semibold text-rose-700">{getRoleMeta(showDeleteModal.role).label}</span>
                </div>
                {showDeleteModal.institution_name && (
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Institution:</span>
                    <span className="text-slate-700 truncate max-w-[200px]">{showDeleteModal.institution_name}</span>
                  </div>
                )}
              </div>

              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-[11px] text-amber-900 space-y-1">
                <p className="font-bold">⚠️ Warning: Permanent Action</p>
                <p>
                  Removing this user will permanently delete their account credentials, committee memberships, and access authorizations.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDeleteModal(null)}
                  disabled={deleteSubmitting}
                  className="px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-lg transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDeleteUser}
                  disabled={deleteSubmitting}
                  className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 rounded-lg transition shadow-xs flex items-center gap-1.5 cursor-pointer"
                >
                  {deleteSubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Removing User...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-3.5 h-3.5" /> Permanently Remove User
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
