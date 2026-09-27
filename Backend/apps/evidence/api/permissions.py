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


from apps.evidence.models import ReviewerAuthorization


class IsEvidenceOwnerOrAdmin(BasePermission):
    """
    Object-level permission:
    - Institutional users may only access evidence for their own college/university institution.
    - Committee reviewers may access evidence matching their authorized framework/institution.
    - Administrators have platform-wide oversight.
    Supports both EvidenceDocument and EvidenceSubcriterionAssociation.
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
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False) or getattr(user, 'role', '') in ('admin', 'state_admin'):
            return True

        # Resolve underlying document if an association is provided
        doc = getattr(obj, 'evidence', obj)

        # Institutional users
        if getattr(user, 'role', '') in ('principal', 'nodal_officer', 'faculty', 'university_admin'):
            if doc.uploader_id == user.pk:
                return True
            user_college = getattr(user, 'college', None)
            if user_college:
                college_code = getattr(user_college, 'aishe_code', None) or str(user_college.pk)
                if doc.institution_id == college_code:
                    return True
            user_uni = getattr(user, 'university', None)
            if user_uni:
                uni_code = getattr(user_uni, 'aishe_code', None) or str(user_uni.pk)
                if doc.institution_id == uni_code:
                    return True
            return False

        # Committee reviewers & chairs
        if getattr(user, 'role', '') in ('committee', 'committee_chair'):
            # Cannot access if conflict of interest (own college)
            user_college = getattr(user, 'college', None)
            if user_college:
                college_code = getattr(user_college, 'aishe_code', None) or str(user_college.pk)
                if doc.institution_id == college_code:
                    return False
            # Cannot access if conflict of interest (own university)
            user_uni = getattr(user, 'university', None)
            if user_uni:
                uni_code = getattr(user_uni, 'aishe_code', None) or str(user_uni.pk)
                if doc.institution_id == uni_code:
                    return False

            # Check assignment
            if doc.assigned_reviewer_id and doc.assigned_reviewer_id != user.pk:
                return False

            # Check ReviewerAuthorization
            user_auths = ReviewerAuthorization.objects.filter(user=user, is_active=True)
            if user_auths.exists():
                allowed_fw = [doc.framework, 'ALL']
                if doc.framework in ('UNIVERSITY_2026', 'UNIVERSITY'):
                    allowed_fw.extend(['UNIVERSITY_2026', 'UNIVERSITY'])
                elif doc.framework in ('COLLEGE_2026', 'COLLEGE'):
                    allowed_fw.extend(['COLLEGE_2026', 'COLLEGE'])
                fw_matching = user_auths.filter(framework__in=allowed_fw)
                if not fw_matching.exists():
                    return False
                inst_matching = fw_matching.filter(institution_id__in=["", doc.institution_id])
                if not inst_matching.exists():
                    return False

            return True

        return False


class IsCommitteeRole(BasePermission):
    """Allows access only to committee reviewers, committee chairs, and administrators."""
    message = "Screening committee reviewer or administrator access required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated()
        return bool(
            getattr(user, 'is_superuser', False)
            or getattr(user, 'is_staff', False)
            or getattr(user, 'role', '') in ('committee', 'committee_chair', 'admin', 'state_admin')
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
            or getattr(user, 'is_staff', False)
            or getattr(user, 'role', '') in ('admin', 'state_admin')
        )

