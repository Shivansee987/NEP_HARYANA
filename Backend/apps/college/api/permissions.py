"""
NEP Excellence Awards 2026 - College API Permissions (Phase 7B)
Enforces strict institutional isolation, framework barriers, and segregation of duties.
"""
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated

from apps.evidence.models import ReviewerAuthorization
from apps.scoring.enums import FrameworkType


class CollegePermissionDenied(PermissionDenied):
    default_code = "COLLEGE_NOT_AUTHORIZED"
    def __init__(self, detail=None, code="COLLEGE_NOT_AUTHORIZED"):
        super().__init__(detail=detail, code=code)
        self.code = code


class AssessmentPermissionDenied(PermissionDenied):
    default_code = "ASSESSMENT_NOT_AUTHORIZED"
    def __init__(self, detail=None, code="ASSESSMENT_NOT_AUTHORIZED"):
        super().__init__(detail=detail, code=code)
        self.code = code


class IsAuthenticatedUser(IsAuthenticated):
    """Requires request.user to be authenticated. Emits 401 when missing."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            raise NotAuthenticated()
        return True


class IsCollegeAdminOrOwner(BasePermission):
    """
    Controls access to College institution records:
    - Superusers and State Administrators have platform-wide access.
    - College users can access their own assigned College.
    - University-only users (with university and no college) are strictly forbidden.
    - Reviewers with college framework authorization can read records, but not create.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        # Admin / Superuser
        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin'):
            return True

        # University-only user attempting to access College endpoints
        if getattr(user, 'university', None) and not getattr(user, 'college', None):
            raise CollegePermissionDenied(
                "University users are not authorized to access College resources.",
                code="COLLEGE_NOT_AUTHORIZED"
            )

        # Committee reviewer: read-only access allowed
        if getattr(user, 'role', '') in ('committee', 'committee_chair'):
            if request.method in ('GET', 'HEAD', 'OPTIONS'):
                return True
            raise CollegePermissionDenied(
                "Reviewers are not authorized to create or modify College records.",
                code="COLLEGE_NOT_AUTHORIZED"
            )

        # College user
        user_col = getattr(user, 'college', None)
        if user_col:
            if request.method == 'POST' and view.__class__.__name__ == 'CollegeListCreateView':
                raise CollegePermissionDenied(
                    "Only administrators can register new Colleges.",
                    code="COLLEGE_NOT_AUTHORIZED"
                )
            return True

        # Unassigned user with no institutional scope
        raise CollegePermissionDenied(
            "User is not associated with an authorized College institution.",
            code="COLLEGE_NOT_AUTHORIZED"
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin'):
            return True

        # University-only user
        if getattr(user, 'university', None) and not getattr(user, 'college', None):
            raise CollegePermissionDenied(
                "University users cannot access College records.",
                code="COLLEGE_NOT_AUTHORIZED"
            )

        # Committee reviewer
        if getattr(user, 'role', '') in ('committee', 'committee_chair'):
            if request.method in ('GET', 'HEAD', 'OPTIONS'):
                return True
            raise CollegePermissionDenied(
                "Reviewers cannot modify College records.",
                code="COLLEGE_NOT_AUTHORIZED"
            )

        # College institution user
        user_col = getattr(user, 'college', None)
        if user_col:
            if obj.pk == user_col.pk or obj.aishe_code == user_col.aishe_code:
                return True
            raise CollegePermissionDenied(
                f"Institution user cannot access external College '{obj.name}'.",
                code="COLLEGE_NOT_AUTHORIZED"
            )

        raise CollegePermissionDenied(
            "Unauthorized access to College record.",
            code="COLLEGE_NOT_AUTHORIZED"
        )


class IsCollegeAssessmentOwnerOrReviewer(BasePermission):
    """
    Controls access to CollegeAssessment sessions:
    - Admin/Superuser: full access.
    - College institution user: access only to assessments for their own college.
    - University user: strictly denied (403 ASSESSMENT_NOT_AUTHORIZED).
    - Reviewer: can view, evaluate; cannot write parameter inputs or perform institutional submissions.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin'):
            return True

        # University-only user
        if getattr(user, 'university', None) and not getattr(user, 'college', None):
            raise AssessmentPermissionDenied(
                "University users cannot access College assessments.",
                code="ASSESSMENT_NOT_AUTHORIZED"
            )

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin'):
            return True

        # University-only user
        if getattr(user, 'university', None) and not getattr(user, 'college', None):
            raise AssessmentPermissionDenied(
                "University users cannot access College assessments.",
                code="ASSESSMENT_NOT_AUTHORIZED"
            )

        # Committee reviewer & chair
        if getattr(user, 'role', '') in ('committee', 'committee_chair'):
            # Conflict of interest check
            user_col = getattr(user, 'college', None)
            if user_col and obj.college_id == user_col.pk:
                raise AssessmentPermissionDenied(
                    "Conflict of interest: reviewer cannot inspect own institution assessment.",
                    code="REVIEW_CONFLICT"
                )

            # Check framework authorization if ReviewerAuthorization records exist
            auth_qs = ReviewerAuthorization.objects.filter(user=user, is_active=True)
            if auth_qs.exists():
                match = auth_qs.filter(
                    framework__in=[FrameworkType.COLLEGE_2026.value, "COLLEGE_2026", "COLLEGE", "ALL"]
                )
                if hasattr(obj, 'college') and obj.college.aishe_code:
                    match = match.filter(institution_id__in=["", obj.college.aishe_code, str(obj.college.pk)])
                if not match.exists():
                    raise AssessmentPermissionDenied(
                        "Reviewer is not authorized for the College framework.",
                        code="ASSESSMENT_NOT_AUTHORIZED"
                    )

            # Restrict write actions: reviewers cannot modify parameter inputs or submit assessment
            if view.__class__.__name__ in (
                'CollegeAssessmentParameterDetailView',
                'CollegeAssessmentSubmitView',
            ) and request.method in ('PUT', 'PATCH', 'POST'):
                raise AssessmentPermissionDenied(
                    "Reviewers are not permitted to submit parameter inputs or perform assessment submission.",
                    code="ASSESSMENT_NOT_AUTHORIZED"
                )

            return True

        # College institution user
        user_col = getattr(user, 'college', None)
        if user_col:
            if obj.college_id == user_col.pk:
                return True
            raise AssessmentPermissionDenied(
                "Institution users cannot access assessments belonging to other Colleges.",
                code="ASSESSMENT_NOT_AUTHORIZED"
            )

        raise AssessmentPermissionDenied(
            "Unauthorized access to College assessment.",
            code="ASSESSMENT_NOT_AUTHORIZED"
        )


class IsCommitteeOrAdminForEvaluation(BasePermission):
    """
    Restricts scoring evaluation execution to authorized committee reviewers
    and administrators. Institution users cannot directly evaluate scores.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin', 'committee', 'committee_chair'):
            return True

        raise AssessmentPermissionDenied(
            "Scoring evaluation requires committee reviewer or administrator authority.",
            code="ASSESSMENT_NOT_AUTHORIZED"
        )


class IsCommitteeReviewer(BasePermission):
    """
    Authorizes Screening Committee members and Administrators for review actions.
    Enforces framework authorization, blocks institutional users, and prevents conflict of interest.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True

        role = getattr(user, 'role', '')
        if role in ('admin', 'state_admin', 'committee', 'committee_chair'):
            return True

        raise AssessmentPermissionDenied(
            "Review actions require committee reviewer or administrator authority.",
            code="REVIEW_NOT_AUTHORIZED"
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True

        role = getattr(user, 'role', '')
        if role not in ('admin', 'state_admin', 'committee', 'committee_chair'):
            raise AssessmentPermissionDenied(
                "Review actions require committee reviewer authority.",
                code="REVIEW_NOT_AUTHORIZED"
            )

        # Conflict of interest check
        user_col = getattr(user, 'college', None)
        target_col = getattr(obj, 'college', obj)
        if user_col and target_col and (user_col.pk == target_col.pk or user_col.aishe_code == getattr(target_col, 'aishe_code', '')):
            raise AssessmentPermissionDenied(
                f"Conflict of interest: Reviewer belongs to institution '{target_col.name}'.",
                code="REVIEW_CONFLICT"
            )

        # Framework authorization check if specific authorizations are registered
        user_auths = ReviewerAuthorization.objects.filter(user=user, is_active=True)
        if user_auths.exists():
            fw_match = user_auths.filter(framework__in=[FrameworkType.COLLEGE_2026.value, "COLLEGE_2026", "COLLEGE", "ALL"])
            if not fw_match.exists():
                raise AssessmentPermissionDenied(
                    "Reviewer is not authorized for the College framework.",
                    code="FRAMEWORK_MISMATCH"
                )
            if hasattr(target_col, 'aishe_code') and target_col.aishe_code:
                inst_match = fw_match.filter(institution_id__in=["", target_col.aishe_code, str(target_col.pk)])
                if not inst_match.exists():
                    raise AssessmentPermissionDenied(
                        f"Reviewer is not authorized for institution '{target_col.aishe_code}'.",
                        code="REVIEW_NOT_AUTHORIZED"
                    )

        return True


class IsCertificationAuthority(BasePermission):
    """
    Authorizes certification operations.
    Restricted strictly to DHE Administrators, Superusers, and Screening Committee Chairs.
    Regular committee reviewers and institutional users are denied with CERTIFICATION_NOT_AUTHORIZED.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True

        role = getattr(user, 'role', '')
        if role in ('admin', 'state_admin', 'committee_chair'):
            return True

        raise AssessmentPermissionDenied(
            "Certification authority required. Only DHE Administrators and Committee Chairs can certify assessments.",
            code="CERTIFICATION_NOT_AUTHORIZED"
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True

        role = getattr(user, 'role', '')
        if role not in ('admin', 'state_admin', 'committee_chair'):
            raise AssessmentPermissionDenied(
                "Certification authority required. Only DHE Administrators and Committee Chairs can certify assessments.",
                code="CERTIFICATION_NOT_AUTHORIZED"
            )

        # Conflict of interest check
        user_col = getattr(user, 'college', None)
        target_col = getattr(obj, 'college', obj)
        if user_col and target_col and (user_col.pk == target_col.pk or user_col.aishe_code == getattr(target_col, 'aishe_code', '')):
            raise AssessmentPermissionDenied(
                f"Conflict of interest: Actor belongs to institution '{target_col.name}'.",
                code="REVIEW_CONFLICT"
            )

        return True
