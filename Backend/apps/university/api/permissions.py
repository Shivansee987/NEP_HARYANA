"""
NEP Excellence Awards 2026 - University API Permissions
Enforces strict institutional isolation, framework barriers, and segregation of duties.
"""
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated

from apps.evidence.models import ReviewerAuthorization
from apps.scoring.enums import FrameworkType


class UniversityPermissionDenied(PermissionDenied):
    default_code = "UNIVERSITY_NOT_AUTHORIZED"
    def __init__(self, detail=None, code="UNIVERSITY_NOT_AUTHORIZED"):
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


class IsUniversityAdminOrOwner(BasePermission):
    """
    Controls access to University records:
    - Superusers and State Administrators have platform-wide access.
    - University users can only access their own assigned University.
    - College users (with college and no university) are strictly forbidden.
    - Reviewers with university framework authorization can read records, but not create.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        # Admin / Superuser
        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin'):
            return True

        # College-only user attempting to access University endpoints
        if getattr(user, 'college', None) and not getattr(user, 'university', None):
            raise UniversityPermissionDenied(
                "College users are not authorized to access University resources.",
                code="UNIVERSITY_NOT_AUTHORIZED"
            )

        # Committee reviewer: read-only access allowed if authorized for university framework
        if getattr(user, 'role', '') in ('committee', 'committee_chair'):
            if request.method in ('GET', 'HEAD', 'OPTIONS'):
                return True
            raise UniversityPermissionDenied(
                "Reviewers are not authorized to create or modify University records.",
                code="UNIVERSITY_NOT_AUTHORIZED"
            )

        # University user
        user_uni = getattr(user, 'university', None)
        if user_uni:
            # Institution users cannot create universities via public POST (admin only)
            if request.method == 'POST' and view.__class__.__name__ == 'UniversityListCreateView':
                raise UniversityPermissionDenied(
                    "Only administrators can register new Universities.",
                    code="UNIVERSITY_NOT_AUTHORIZED"
                )
            return True

        # Unassigned user with no institutional scope
        raise UniversityPermissionDenied(
            "User is not associated with an authorized University institution.",
            code="UNIVERSITY_NOT_AUTHORIZED"
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin'):
            return True

        # College-only user
        if getattr(user, 'college', None) and not getattr(user, 'university', None):
            raise UniversityPermissionDenied(
                "College users cannot access University records.",
                code="UNIVERSITY_NOT_AUTHORIZED"
            )

        # Committee reviewer
        if getattr(user, 'role', '') == 'committee':
            if request.method in ('GET', 'HEAD', 'OPTIONS'):
                return True
            raise UniversityPermissionDenied(
                "Reviewers cannot modify University records.",
                code="UNIVERSITY_NOT_AUTHORIZED"
            )

        # University institution user
        user_uni = getattr(user, 'university', None)
        if user_uni:
            if obj.pk == user_uni.pk or obj.aishe_code == user_uni.aishe_code:
                return True
            raise UniversityPermissionDenied(
                f"Institution user cannot access external University '{obj.name}'.",
                code="UNIVERSITY_NOT_AUTHORIZED"
            )

        raise UniversityPermissionDenied(
            "Unauthorized access to University record.",
            code="UNIVERSITY_NOT_AUTHORIZED"
        )


class IsUniversityAssessmentOwnerOrReviewer(BasePermission):
    """
    Controls access to UniversityAssessment sessions:
    - Admin/Superuser: full access.
    - University institution user: access only to assessments for their own university.
    - College user: strictly denied (403 ASSESSMENT_NOT_AUTHORIZED).
    - Reviewer: can view, evaluate; cannot write parameter inputs or perform institutional submissions.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin'):
            return True

        # College-only user
        if getattr(user, 'college', None) and not getattr(user, 'university', None):
            raise AssessmentPermissionDenied(
                "College users cannot access University assessments.",
                code="ASSESSMENT_NOT_AUTHORIZED"
            )

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            raise NotAuthenticated()

        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin'):
            return True

        # College-only user
        if getattr(user, 'college', None) and not getattr(user, 'university', None):
            raise AssessmentPermissionDenied(
                "College users cannot access University assessments.",
                code="ASSESSMENT_NOT_AUTHORIZED"
            )

        # Committee reviewer & chair
        if getattr(user, 'role', '') in ('committee', 'committee_chair'):
            # Conflict of interest check
            user_uni = getattr(user, 'university', None)
            if user_uni and obj.university_id == user_uni.pk:
                raise AssessmentPermissionDenied(
                    "Conflict of interest: reviewer cannot inspect own institution assessment.",
                    code="ASSESSMENT_NOT_AUTHORIZED"
                )

            # Check framework authorization if ReviewerAuthorization records exist
            auth_qs = ReviewerAuthorization.objects.filter(user=user, is_active=True)
            if auth_qs.exists():
                match = auth_qs.filter(
                    framework__in=[FrameworkType.UNIVERSITY_2026.value, "UNIVERSITY_2026", "UNIVERSITY", "ALL"]
                )
                if obj.university.aishe_code:
                    match = match.filter(institution_id__in=["", obj.university.aishe_code])
                if not match.exists():
                    raise AssessmentPermissionDenied(
                        "Reviewer is not authorized for the University framework.",
                        code="ASSESSMENT_NOT_AUTHORIZED"
                    )

            # Restrict write actions: reviewers cannot modify parameter inputs or submit assessment
            if view.__class__.__name__ in (
                'UniversityAssessmentParameterDetailView',
                'UniversityAssessmentSubmitView',
            ) and request.method in ('PUT', 'PATCH', 'POST'):
                raise AssessmentPermissionDenied(
                    "Reviewers are not permitted to submit parameter inputs or perform assessment submission.",
                    code="ASSESSMENT_NOT_AUTHORIZED"
                )

            return True

        # Institution user
        user_uni = getattr(user, 'university', None)
        if user_uni:
            if obj.university_id == user_uni.pk:
                return True
            raise AssessmentPermissionDenied(
                "Institution users cannot access assessments belonging to other Universities.",
                code="ASSESSMENT_NOT_AUTHORIZED"
            )

        raise AssessmentPermissionDenied(
            "Unauthorized access to University assessment.",
            code="ASSESSMENT_NOT_AUTHORIZED"
        )


class IsCommitteeOrAdminForEvaluation(BasePermission):
    """
    Restricts scoring evaluation execution and certification to authorized committee reviewers
    and administrators. Institution users cannot directly evaluate or certify scores.
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
        user_uni = getattr(user, 'university', None)
        target_uni = getattr(obj, 'university', obj)
        if user_uni and target_uni and (user_uni.pk == target_uni.pk or user_uni.aishe_code == getattr(target_uni, 'aishe_code', '')):
            raise AssessmentPermissionDenied(
                f"Conflict of interest: Reviewer belongs to institution '{target_uni.name}'.",
                code="REVIEW_CONFLICT"
            )

        # Framework authorization check if specific authorizations are registered
        user_auths = ReviewerAuthorization.objects.filter(user=user, is_active=True)
        if user_auths.exists():
            fw_match = user_auths.filter(framework__in=[FrameworkType.UNIVERSITY_2026.value, "ALL"])
            if not fw_match.exists():
                raise AssessmentPermissionDenied(
                    "Reviewer is not authorized for the University framework.",
                    code="FRAMEWORK_MISMATCH"
                )
            if hasattr(target_uni, 'aishe_code') and target_uni.aishe_code:
                inst_match = fw_match.filter(institution_id__in=["", target_uni.aishe_code])
                if not inst_match.exists():
                    raise AssessmentPermissionDenied(
                        f"Reviewer is not authorized for institution '{target_uni.aishe_code}'.",
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
        user_uni = getattr(user, 'university', None)
        target_uni = getattr(obj, 'university', obj)
        if user_uni and target_uni and (user_uni.pk == target_uni.pk or user_uni.aishe_code == getattr(target_uni, 'aishe_code', '')):
            raise AssessmentPermissionDenied(
                f"Conflict of interest: Actor belongs to institution '{target_uni.name}'.",
                code="REVIEW_CONFLICT"
            )

        return True
