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
    Authoritative authorization check for viewing an assessment report.
    Enforces strict tenant isolation and framework security:
    - Admin / Superuser: Cross-framework access.
    - Committee Chair: Cross-framework access.
    - Committee Reviewer: Only if assigned reviewer or actively authorized for the framework without COI.
    - Institutional User (principal): Strictly own college.
    - Institutional User (nodal_officer, university_admin): Strictly own university.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True

    role = getattr(user, "role", "")

    # 1. State / System Admin
    if role in ("admin", "state_admin"):
        return True

    # 2. Committee Chair has global inspection visibility across the control plane
    if role == "committee_chair":
        return True

    # 3. Screening Committee Reviewer
    if role == "committee":
        # Check direct assignment
        if assessment.assigned_reviewer_id and assessment.assigned_reviewer_id == user.pk:
            return True

        # Check Conflict of Interest (COI)
        user_inst_id = getattr(user, "institution_id", None)
        if framework == "UNIVERSITY_2026":
            target_aishe = getattr(assessment.university, "aishe_code", "")
            if user_inst_id and user_inst_id == target_aishe:
                return False  # COI: reviewer cannot inspect own institution
        elif framework == "COLLEGE_2026":
            target_aishe = getattr(assessment.college, "aishe_code", "")
            if user_inst_id and user_inst_id == target_aishe:
                return False  # COI

        # Check framework-level ReviewerAuthorization binding
        has_binding = ReviewerAuthorization.objects.filter(
            user=user,
            framework=framework,
            is_active=True,
        ).exists()
        return has_binding

    # 4. University Institutional Users (nodal_officer, university_admin)
    if role in ("nodal_officer", "university_admin"):
        if framework != "UNIVERSITY_2026":
            return False  # Cross-framework access forbidden
        user_uni = getattr(user, "university", None)
        if not user_uni:
            return False
        return bool(
            user_uni.pk == assessment.university.pk
            or (user_uni.aishe_code and user_uni.aishe_code == assessment.university.aishe_code)
        )

    # 5. College Institutional Users (principal)
    if role == "principal":
        if framework != "COLLEGE_2026":
            return False  # Cross-framework access forbidden
        user_col = getattr(user, "college", None)
        if not user_col:
            return False
        return bool(
            user_col.pk == assessment.college.pk
            or (user_col.aishe_code and user_col.aishe_code == assessment.college.aishe_code)
        )

    return False


class IsReportAuthorized(BasePermission):
    """
    Standard base permission requiring an authenticated user with a recognized role.
    """
    message = "Authentication and valid role required to access reports."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", "") in (
                "admin", "state_admin", "committee", "committee_chair",
                "nodal_officer", "university_admin", "principal"
            )
            or getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
        )


class IsAdminOrChairForAnalytics(BasePermission):
    """
    Restricts cross-framework administrative analytics to Admins and Committee Chairs.
    """
    message = "Cross-framework administrative analytics restricted to Administrators and Committee Chairs."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        return getattr(user, "role", "") in ("admin", "state_admin", "committee_chair")
