"""
NEP Excellence Awards 2026 - Reports & Analytics Security & Tenant Permissions (Phase 9)
Enforces framework isolation, tenant data isolation, reviewer authorization, and read-only projection.
"""
from typing import Any, Tuple
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

from apps.evidence.models import ReviewerAuthorization


class ReportPermissionDenied(PermissionDenied):
    """Specific permission denied error for reporting tenant/framework violations."""
    default_code = "REPORT_PERMISSION_DENIED"


def can_user_view_assessment(user: Any, assessment: Any, framework: str) -> bool:
    """
    Report visibility follows apps.evidence.access_policy:
    - Oversight administrators: every assessment (read-only).
    - Screening Committee members and chairs: submitted assessments inside their review scope, never their own
      institution.
    - Institution users: only their own (bound) institution's assessment, and only for its own framework.
    """
    from apps.evidence import access_policy as policy

    if not user or not getattr(user, "is_authenticated", False):
        return False
    if policy.is_oversight(user):
        return True
    fw = policy.normalize_framework(framework)
    institution = getattr(assessment, "college", None) if fw == policy.COLLEGE else getattr(assessment, "university", None)
    if policy.is_reviewer(user):
        return policy.reviewer_can_view_assessment(
            user, fw, institution, getattr(assessment, "status", None), getattr(assessment, "assigned_reviewer_id", None))
    if policy.role_of(user) in policy.INSTITUTION_ROLES:
        return policy.institution_owns_assessment(user, assessment)
    return False


class IsReportAuthorized(BasePermission):
    """
    Standard base permission requiring an authenticated user with a recognized role.
    """
    message = "Authentication and valid role required to access reports."

    def has_permission(self, request, view):
        from apps.evidence import access_policy as policy
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return policy.is_oversight(user) or policy.is_reviewer(user) or policy.role_of(user) in policy.INSTITUTION_ROLES


class IsAdminOrChairForAnalytics(BasePermission):
    """
    Restricts cross-framework administrative analytics to Admins and Committee Chairs.
    """
    message = "Cross-framework administrative analytics restricted to Administrators and Committee Chairs."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        from apps.evidence import access_policy as policy
        return policy.is_oversight(user) or getattr(user, "role", "") == "committee_chair"
