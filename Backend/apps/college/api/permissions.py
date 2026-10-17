"""
NEP Excellence Awards 2026 - College API Permissions.
Institution isolation, framework barriers and segregation of duties; the role rules themselves live in
apps.evidence.access_policy (oversight is read-only, reviewers need review scope, chair-only certification).
"""
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated

from apps.evidence import access_policy as policy


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


def _require_auth(request):
    user = request.user
    if not (user and user.is_authenticated):
        raise NotAuthenticated()
    return user


def _university_only(user):
    return getattr(user, 'university', None) and not getattr(user, 'college', None)


class IsAuthenticatedUser(IsAuthenticated):
    """Requires request.user to be authenticated. Emits 401 when missing."""
    def has_permission(self, request, view):
        _require_auth(request)
        return True


class IsCollegeAdminOrOwner(BasePermission):
    """
    College institution records:
    - Oversight administrators read every College; only Head/State/legacy Admin may register a new College.
    - Committee reviewers may read College records.
    - College users read only their own College. University-only and unbound users are refused.
    """
    REGISTRY_WRITERS = ('head_admin', 'state_admin', 'admin')

    def has_permission(self, request, view):
        user = _require_auth(request)
        if policy.is_oversight(user):
            if request.method in policy.SAFE_METHODS or getattr(user, 'is_superuser', False) or policy.role_of(user) in self.REGISTRY_WRITERS:
                return True
            raise CollegePermissionDenied("Administrators other than the Head/State Admin have read-only access.")
        if _university_only(user):
            raise CollegePermissionDenied("University users are not authorized to access College resources.")
        if policy.is_reviewer(user):
            if request.method in policy.SAFE_METHODS:
                return True
            raise CollegePermissionDenied("Reviewers are not authorized to create or modify College records.")
        if getattr(user, 'college', None):
            if request.method == 'POST' and view.__class__.__name__ == 'CollegeListCreateView':
                raise CollegePermissionDenied("Only administrators can register new Colleges.")
            return True
        raise CollegePermissionDenied("User is not associated with an authorized College institution.")

    def has_object_permission(self, request, view, obj):
        user = _require_auth(request)
        if policy.is_oversight(user) or policy.is_reviewer(user):
            if request.method in policy.SAFE_METHODS:
                return True
            raise CollegePermissionDenied("College records are read-only for this role.")
        if _university_only(user):
            raise CollegePermissionDenied("University users cannot access College records.")
        user_col = getattr(user, 'college', None)
        if user_col and obj.pk == user_col.pk:
            return True
        raise CollegePermissionDenied(f"Institution user cannot access external College '{obj.name}'.")


class IsCollegeAssessmentOwnerOrReviewer(BasePermission):
    """
    CollegeAssessment access:
    - Oversight administrators: read-only.
    - College institution user: only their own College's assessments (read and write while editable).
    - Reviewer: read assessments in their review scope once submitted; never parameter writes or submission.
    - University users and unbound applicants: refused.
    """
    REVIEWER_FORBIDDEN_WRITES = ('CollegeAssessmentParameterDetailView', 'CollegeAssessmentSubmitView',
                                 'CollegeAssessmentDetailView', 'CollegeAssessmentListCreateView')

    def has_permission(self, request, view):
        user = _require_auth(request)
        if policy.is_oversight(user):
            if request.method in policy.SAFE_METHODS:
                return True
            raise AssessmentPermissionDenied(
                "Administrators have read-only oversight of assessments; institutions and the committee perform these actions.")
        if _university_only(user):
            raise AssessmentPermissionDenied("University users cannot access College assessments.")
        if policy.is_reviewer(user) and request.method not in policy.SAFE_METHODS \
                and view.__class__.__name__ in self.REVIEWER_FORBIDDEN_WRITES:
            raise AssessmentPermissionDenied(
                "Reviewers are not permitted to create, edit or submit institution assessments.")
        return True

    def has_object_permission(self, request, view, obj):
        user = _require_auth(request)
        if policy.is_oversight(user):
            if request.method in policy.SAFE_METHODS:
                return True
            raise AssessmentPermissionDenied("Administrators have read-only oversight of assessments.")
        if _university_only(user):
            raise AssessmentPermissionDenied("University users cannot access College assessments.")

        if policy.is_reviewer(user):
            college = getattr(obj, 'college', None)
            if policy.has_conflict_of_interest(user, college):
                raise AssessmentPermissionDenied(
                    "Conflict of interest: reviewer cannot inspect own institution assessment.", code="REVIEW_CONFLICT")
            if getattr(obj, 'status', None) in policy.INSTITUTION_EDITING_STATES:
                raise AssessmentPermissionDenied("This assessment has not been submitted for review.")
            if not policy.has_review_scope(user, policy.COLLEGE, college, getattr(obj, 'assigned_reviewer_id', None)):
                raise AssessmentPermissionDenied(
                    "Reviewer is not assigned to, or authorized for, this College assessment.",
                    code=policy.scope_denial_code(user, policy.COLLEGE))
            if request.method not in policy.SAFE_METHODS and view.__class__.__name__ in self.REVIEWER_FORBIDDEN_WRITES:
                raise AssessmentPermissionDenied(
                    "Reviewers are not permitted to submit parameter inputs or perform assessment submission.")
            return True

        user_col = getattr(user, 'college', None)
        if user_col and obj.college_id == user_col.pk:
            return True
        raise AssessmentPermissionDenied("Institution users cannot access assessments belonging to other Colleges.")


class IsCommitteeOrAdminForEvaluation(BasePermission):
    """Scoring evaluation: committee reviewers act; oversight administrators may only read."""
    def has_permission(self, request, view):
        user = _require_auth(request)
        if policy.is_reviewer(user) or (policy.is_oversight(user) and request.method in policy.SAFE_METHODS):
            return True
        raise AssessmentPermissionDenied("Scoring evaluation requires committee reviewer authority.")


class IsCommitteeReviewer(BasePermission):
    """
    Review actions (start, evaluate, accept/adjust, complete, return, reject) and the review queue:
    Screening Committee members and chairs only, inside their review scope, never on their own institution.
    """
    def has_permission(self, request, view):
        user = _require_auth(request)
        if policy.is_reviewer(user):
            return True
        raise AssessmentPermissionDenied(
            "Review actions require Screening Committee authority.", code="REVIEW_NOT_AUTHORIZED")

    def has_object_permission(self, request, view, obj):
        user = _require_auth(request)
        if not policy.is_reviewer(user):
            raise AssessmentPermissionDenied("Review actions require Screening Committee authority.", code="REVIEW_NOT_AUTHORIZED")
        college = getattr(obj, 'college', obj)
        if policy.has_conflict_of_interest(user, college):
            raise AssessmentPermissionDenied(
                f"Conflict of interest: Reviewer belongs to institution '{college.name}'.", code="REVIEW_CONFLICT")
        if not policy.has_review_scope(user, policy.COLLEGE, college, getattr(obj, 'assigned_reviewer_id', None)):
            raise AssessmentPermissionDenied(
                "Reviewer is not assigned to, or authorized for, this College assessment.",
                code=policy.scope_denial_code(user, policy.COLLEGE))
        return True


class IsCertificationAuthority(BasePermission):
    """Certification: the Screening Committee Chair only, within review scope and without conflict of interest."""
    MESSAGE = "Certification authority required. Only the Screening Committee Chair can certify assessments."

    def has_permission(self, request, view):
        user = _require_auth(request)
        if policy.role_of(user) == 'committee_chair':
            return True
        raise AssessmentPermissionDenied(self.MESSAGE, code="CERTIFICATION_NOT_AUTHORIZED")

    def has_object_permission(self, request, view, obj):
        user = _require_auth(request)
        if policy.role_of(user) != 'committee_chair':
            raise AssessmentPermissionDenied(self.MESSAGE, code="CERTIFICATION_NOT_AUTHORIZED")
        college = getattr(obj, 'college', obj)
        if policy.has_conflict_of_interest(user, college):
            raise AssessmentPermissionDenied(
                f"Conflict of interest: Actor belongs to institution '{college.name}'.", code="REVIEW_CONFLICT")
        if not policy.has_review_scope(user, policy.COLLEGE, college, getattr(obj, 'assigned_reviewer_id', None)):
            raise AssessmentPermissionDenied(
                "The Chair is not authorized for this College assessment.", code=policy.scope_denial_code(user, policy.COLLEGE))
        return True
