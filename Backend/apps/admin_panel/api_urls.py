"""
NEP Excellence Awards 2026 - Admin Control Plane API URL Routing (Phase 8)
Mounted at /api/v1/admin/
"""
from django.urls import path

from .api_views import (
    AdminAssessmentAssignReviewerView,
    AdminAssessmentCertifyView,
    AdminAssessmentInspectView,
    AdminControlCentreSummaryView,
    AdminGlobalUserAuditLogsView,
    AdminReviewQueueView,
    AdminReviewerAuthorizationsView,
    AdminStateInstitutionsView,
    AdminUserListCreateView,
    AdminUserDetailView,
    AdminUserAuditLogsView,
    AdminUserResetPasswordView,
    AdminUserCommitteeView,
    AdminUserResendInvitationView,
    AdminUserRevokeInvitationView,
    AdminCommitteeListCreateView,
    AdminCommitteeDetailView,
    AdminCommitteeAssignChairView,
    AdminCommitteeMembersView,
)

urlpatterns = [
    # Head Admin Control Centre Summary
    path('control-centre/summary/', AdminControlCentreSummaryView.as_view(), name='admin-control-centre-summary'),

    # Centralized User Management & Role Governance
    path('users/audit-trail/', AdminGlobalUserAuditLogsView.as_view(), name='admin-users-global-audit-trail'),
    path('users/', AdminUserListCreateView.as_view(), name='admin-users-list-create'),
    path('users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin-users-detail'),
    path('users/<int:user_id>/audit/', AdminUserAuditLogsView.as_view(), name='admin-users-audit'),
    path('users/<int:user_id>/reset-password/', AdminUserResetPasswordView.as_view(), name='admin-users-reset-password'),
    path('users/<int:user_id>/committee/', AdminUserCommitteeView.as_view(), name='admin-users-committee-assignment'),
    path('users/<int:user_id>/resend-invitation/', AdminUserResendInvitationView.as_view(), name='admin-users-resend-invitation'),
    path('users/<int:user_id>/revoke-invitation/', AdminUserRevokeInvitationView.as_view(), name='admin-users-revoke-invitation'),

    # Committee Management
    path('committees/', AdminCommitteeListCreateView.as_view(), name='admin-committees-list-create'),
    path('committees/<int:committee_id>/', AdminCommitteeDetailView.as_view(), name='admin-committees-detail'),
    path('committees/<int:committee_id>/chair/', AdminCommitteeAssignChairView.as_view(), name='admin-committees-assign-chair'),
    path('committees/<int:committee_id>/members/', AdminCommitteeMembersView.as_view(), name='admin-committees-members'),
    path('committees/<int:committee_id>/members/<int:user_id>/', AdminCommitteeMembersView.as_view(), name='admin-committees-remove-member'),

    # Unified Review Queue
    path('review-queue/', AdminReviewQueueView.as_view(), name='admin-review-queue'),
    path('queue/', AdminReviewQueueView.as_view(), name='admin-queue-alias'),

    # Assessment Inspection & Administration
    path('assessments/<str:assessment_id>/inspect/', AdminAssessmentInspectView.as_view(), name='admin-assessment-inspect'),
    path('assessments/<str:assessment_id>/review/', AdminAssessmentInspectView.as_view(), name='admin-assessment-review'),
    path('assessments/<str:assessment_id>/assign/', AdminAssessmentAssignReviewerView.as_view(), name='admin-assessment-assign'),
    path('assessments/<str:assessment_id>/certify/', AdminAssessmentCertifyView.as_view(), name='admin-assessment-certify'),

    # State Admin institution overview (read-only)
    path('institutions/', AdminStateInstitutionsView.as_view(), name='admin-state-institutions'),

    # Reviewer Authorizations Management
    path('authorizations/', AdminReviewerAuthorizationsView.as_view(), name='admin-authorizations'),
]

