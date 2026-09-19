"""
NEP Excellence Awards 2026 - Evidence API Permissions
Enforces role-based access control and strict institutional data isolation.
"""
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import BasePermission, IsAuthenticated


class IsAuthenticatedUser(IsAuthenticated):
    """Requires request.user to be authenticated. Emits 401 when missing."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            raise NotAuthenticated()
        return True


class IsEvidenceOwnerOrAdmin(BasePermission):
    """
    Object-level permission:
    - Institutional users may only access evidence for their own college/institution.
    - Committee reviewers may access evidence matching their authorized framework/institution.
    - Administrators have platform-wide oversight.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            raise NotAuthenticated()
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated()

        # Admin / Superuser
        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin'):
            return True

        # Institutional users
        if getattr(user, 'role', '') in ('principal', 'nodal_officer', 'faculty'):
            if obj.uploader_id == user.pk:
                return True
            user_college = getattr(user, 'college', None)
            if user_college:
                college_code = getattr(user_college, 'aishe_code', None) or str(user_college.pk)
                if obj.institution_id == college_code:
                    return True
            return False

        # Committee reviewers
        if getattr(user, 'role', '') == 'committee':
            # Cannot access if conflict of interest (own college)
            user_college = getattr(user, 'college', None)
            if user_college:
                college_code = getattr(user_college, 'aishe_code', None) or str(user_college.pk)
                if obj.institution_id == college_code:
                    return False
            # Check assignment or authorization
            if obj.assigned_reviewer_id and obj.assigned_reviewer_id != user.pk:
                return False
            return True

        return False


class IsCommitteeRole(BasePermission):
    """Allows access only to committee reviewers and administrators."""
    message = "Screening committee reviewer or administrator access required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated()
        return bool(
            getattr(user, 'is_superuser', False)
            or getattr(user, 'role', '') in ('committee', 'admin', 'state_admin')
        )


class IsStateAdminRole(BasePermission):
    """Allows access only to State Administrators and Superusers."""
    message = "State administrator or superuser privileges required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated()
        return bool(
            getattr(user, 'is_superuser', False)
            or getattr(user, 'role', '') in ('admin', 'state_admin')
        )

