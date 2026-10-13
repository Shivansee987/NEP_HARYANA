"""
NEP Excellence Awards 2026 - Admin Control Plane Permissions (Phase 8)
Enforces strict segregation of duties, framework barriers, and conflict-of-interest controls.
"""
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated

from apps.evidence.models import ReviewerAuthorization
from apps.scoring.enums import FrameworkType


class AdminPermissionDenied(PermissionDenied):
    default_code = "ADMIN_NOT_AUTHORIZED"
    def __init__(self, detail=None, code="ADMIN_NOT_AUTHORIZED"):
        super().__init__(detail=detail, code=code)
        self.code = code


class FrameworkMismatchError(PermissionDenied):
    default_code = "FRAMEWORK_MISMATCH"
    def __init__(self, detail=None, code="FRAMEWORK_MISMATCH"):
        super().__init__(detail=detail, code=code)
        self.code = code


class ReviewConflictError(PermissionDenied):
    default_code = "REVIEW_CONFLICT"
    def __init__(self, detail=None, code="REVIEW_CONFLICT"):
        super().__init__(detail=detail, code=code)
        self.code = code


class IsAuthenticatedUser(IsAuthenticated):
    """Requires request.user to be authenticated."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            raise NotAuthenticated()
        return True


class IsControlPlaneAuthorized(BasePermission):
    """
    Authorizes users with reviewer, chair, or administrator roles for control plane access.
    Institutional users (principals, nodal officers, university admins) are strictly denied.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True

        role = getattr(user, 'role', '')
        if role in (
            'head_admin', 'sub_admin', 'admin', 'state_admin',
            'committee', 'committee_chair',
            'empowered_committee', 'empowered_committee_chair'
        ):
            return True

        raise AdminPermissionDenied(
            "Control plane requires committee reviewer, chair, or administrator authority.",
            code="CONTROL_PLANE_NOT_AUTHORIZED"
        )


class IsAdminOrCommitteeChair(BasePermission):
    """
    Restricted to Administrators (Head Admin, Sub-Admin, DHE Admin, Superuser) and Committee Chairs.
    Used for reviewer assignment, reassignment, and queue management.
    Standard committee reviewers and institutional users are denied.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        role = getattr(user, 'role', '')
        if role == 'council_admin':
            raise AdminPermissionDenied(
                "Reviewer assignment requires Committee Chair or Administrator authority. Council Admin Overseer is restricted.",
                code="ASSIGNMENT_NOT_AUTHORIZED"
            )

        if getattr(user, 'is_superuser', False):
            return True

        if getattr(user, 'is_staff', False) and role not in ('council_admin', 'committee'):
            return True

        if role in ('head_admin', 'sub_admin', 'admin', 'state_admin', 'committee_chair', 'empowered_committee_chair'):
            return True

        raise AdminPermissionDenied(
            "Reviewer assignment requires Committee Chair or Administrator authority.",
            code="ASSIGNMENT_NOT_AUTHORIZED"
        )


class IsAdminOnly(BasePermission):
    """
    Restricted to Head Admins, Sub-Admins, DHE Administrators, and Superusers.
    Used for platform authorizations and global configuration.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        role = getattr(user, 'role', '')
        if role == 'council_admin':
            raise AdminPermissionDenied(
                "Platform administration authority required. Council Admin Overseer is restricted.",
                code="ADMIN_REQUIRED"
            )

        if getattr(user, 'is_superuser', False):
            return True

        if getattr(user, 'is_staff', False) and role not in ('council_admin', 'committee'):
            return True

        if role in ('head_admin', 'sub_admin', 'admin', 'state_admin'):
            return True

        raise AdminPermissionDenied(
            "Platform administration authority required.",
            code="ADMIN_REQUIRED"
        )


class IsHeadAdminOnly(BasePermission):
    """
    Restricted strictly to the Head Administrator or Django Superuser.
    Required for privileged role assignments, sub-admin creation, and committee governance.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False):
            return True

        if getattr(user, 'role', '') == 'head_admin':
            return True

        raise AdminPermissionDenied(
            "Head Administrator authority required for this operation.",
            code="HEAD_ADMIN_REQUIRED"
        )


class IsAnyAdminUserManagement(BasePermission):
    """
    Allows read-access or restricted management access to any administrator (Head Admin, Sub-Admin, Admin).
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True

        role = getattr(user, 'role', '')
        if role in ('head_admin', 'sub_admin', 'admin', 'state_admin', 'council_admin'):
            return True

        raise AdminPermissionDenied(
            "Administrator authority required to access user management.",
            code="ADMIN_REQUIRED"
        )


class IsControlPlaneCertificationAuthority(BasePermission):
    """
    Authorizes certification operations via the control plane.
    Restricted to the Screening Committee Chair.
    Regular committee reviewers and institutional users are denied.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        # Certification is the Chair's decision alone; Head Admin, State Admin, and superusers oversee but do not certify.
        if getattr(user, 'role', '') == 'committee_chair':
            return True

        raise AdminPermissionDenied(
            "Certification authority required. Only the Screening Committee Chair can certify assessments.",
            code="CERTIFICATION_NOT_AUTHORIZED"
        )



def validate_reviewer_framework_and_coi(user, assessment):
    """
    Enforces framework authorization and institutional conflict-of-interest for an assessment.
    Raises FrameworkMismatchError or ReviewConflictError if checks fail.
    """
    is_admin = (
        getattr(user, "is_superuser", False)
        or getattr(user, "role", "") in ("admin", "state_admin", "head_admin", "sub_admin")
        or (getattr(user, "is_staff", False) and getattr(user, "role", "") not in ("council_admin", "committee"))
    )

    framework = getattr(assessment, "framework", "")

    # Institutional conflict of interest check
    if framework == "COLLEGE_2026":
        user_college = getattr(user, "college", None)
        assessment_college = getattr(assessment, "college", None)
        if user_college and assessment_college:
            if (
                user_college.pk == assessment_college.pk
                or getattr(user_college, "aishe_code", "") == getattr(assessment_college, "aishe_code", "")
            ):
                raise ReviewConflictError(
                    f"Conflict of interest: User is affiliated with institution '{assessment_college.name}'."
                )
    elif framework == "UNIVERSITY_2026":
        user_uni = getattr(user, "university", None)
        assessment_uni = getattr(assessment, "university", None)
        if user_uni and assessment_uni:
            if (
                user_uni.pk == assessment_uni.pk
                or getattr(user_uni, "aishe_code", "") == getattr(assessment_uni, "aishe_code", "")
            ):
                raise ReviewConflictError(
                    f"Conflict of interest: User is affiliated with institution '{assessment_uni.name}'."
                )

    # Framework authorization check (non-admin)
    if not is_admin:
        user_auths = ReviewerAuthorization.objects.filter(user=user, is_active=True)
        if not user_auths.exists():
            if getattr(assessment, "assigned_reviewer_id", None) != user.pk:
                raise FrameworkMismatchError(
                    f"Reviewer has no active committee authorizations and is not assigned to this assessment."
                )
        else:
            matching_fw = user_auths.filter(framework__in=[framework, "ALL"])
            if not matching_fw.exists():
                raise FrameworkMismatchError(
                    f"Reviewer is not authorized for framework '{framework}'."
                )
            # Scoped institution check
            if framework == "COLLEGE_2026" and hasattr(assessment, "college"):
                col = assessment.college
                if col and getattr(col, "aishe_code", ""):
                    inst_match = matching_fw.filter(institution_id__in=["", col.aishe_code, str(col.pk)])
                    if not inst_match.exists():
                        raise AdminPermissionDenied(
                            f"Reviewer is not authorized for institution '{col.aishe_code}'.",
                            code="REVIEW_NOT_AUTHORIZED"
                        )
            elif framework == "UNIVERSITY_2026" and hasattr(assessment, "university"):
                uni = assessment.university
                if uni and getattr(uni, "aishe_code", ""):
                    inst_match = matching_fw.filter(institution_id__in=["", uni.aishe_code, str(uni.pk)])
                    if not inst_match.exists():
                        raise AdminPermissionDenied(
                            f"Reviewer is not authorized for institution '{uni.aishe_code}'.",
                            code="REVIEW_NOT_AUTHORIZED"
                        )
