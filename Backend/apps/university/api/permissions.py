"""
NEP Excellence Awards 2026 - University API Permissions.
Institution isolation, framework barriers and segregation of duties; the role rules themselves live in
apps.evidence.access_policy (oversight is read-only, reviewers need review scope, chair-only certification).
"""
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated

from apps.evidence import access_policy as policy


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


def _require_auth(request):
    user = request.user
    if not (user and user.is_authenticated):
        raise NotAuthenticated()
    return user


def _college_only(user):
    return getattr(user, 'college', None) and not getattr(user, 'university', None)


class IsAuthenticatedUser(IsAuthenticated):
    """Requires request.user to be authenticated. Emits 401 when missing."""
    def has_permission(self, request, view):
        _require_auth(request)
        return True


class IsUniversityAdminOrOwner(BasePermission):
    """
    University institution records:
    - Oversight administrators read every University; only Head/State/legacy Admin may register a new one.
    - Committee reviewers may read University records.
    - University users read only their own University. College-only and unbound users are refused.
    """
    REGISTRY_WRITERS = ('head_admin', 'state_admin', 'admin')

    def has_permission(self, request, view):
        user = _require_auth(request)
        if policy.is_oversight(user):
            if request.method in SAFE_METHODS or getattr(user, 'is_superuser', False) or policy.role_of(user) in self.REGISTRY_WRITERS:
                return True
            raise UniversityPermissionDenied("Administrators other than the Head/State Admin have read-only access.")
        if _college_only(user):
            raise UniversityPermissionDenied("College users are not authorized to access University resources.")
        if policy.is_reviewer(user):
            if request.method in SAFE_METHODS:
                return True
            raise UniversityPermissionDenied("Reviewers are not authorized to create or modify University records.")
        if getattr(user, 'university', None):
            if request.method == 'POST' and view.__class__.__name__ == 'UniversityListCreateView':
                raise UniversityPermissionDenied("Only administrators can register new Universities.")
            return True
        raise UniversityPermissionDenied("User is not associated with an authorized University institution.")

    def has_object_permission(self, request, view, obj):
        user = _require_auth(request)
        if policy.is_oversight(user) or policy.is_reviewer(user):
            if request.method in SAFE_METHODS:
                return True
            raise UniversityPermissionDenied("University records are read-only for this role.")
        if _college_only(user):
            raise UniversityPermissionDenied("College users cannot access University records.")
        user_uni = getattr(user, 'university', None)
        if user_uni and obj.pk == user_uni.pk:
            return True
        raise UniversityPermissionDenied(f"Institution user cannot access external University '{obj.name}'.")


class IsUniversityAssessmentOwnerOrReviewer(BasePermission):
    """
    UniversityAssessment access:
    - Oversight administrators: read-only.
    - University institution user: only their own University's assessments.
    - Reviewer: read assessments in their review scope once submitted; never parameter writes or submission.
    - College users and unbound applicants: refused.
    """
    REVIEWER_FORBIDDEN_WRITES = ('UniversityAssessmentParameterDetailView', 'UniversityAssessmentSubmitView',
                                 'UniversityAssessmentDetailView', 'UniversityAssessmentListCreateView')

    def has_permission(self, request, view):
        user = _require_auth(request)
        if policy.is_oversight(user):
            if request.method in SAFE_METHODS:
                return True
            raise AssessmentPermissionDenied(
                "Administrators have read-only oversight of assessments; institutions and the committee perform these actions.")
        if _college_only(user):
            raise AssessmentPermissionDenied("College users cannot access University assessments.")
        if policy.is_reviewer(user) and request.method not in SAFE_METHODS \
                and view.__class__.__name__ in self.REVIEWER_FORBIDDEN_WRITES:
            raise AssessmentPermissionDenied(
                "Reviewers are not permitted to create, edit or submit institution assessments.")
        return True

    def has_object_permission(self, request, view, obj):
        user = _require_auth(request)
        if policy.is_oversight(user):
            if request.method in SAFE_METHODS:
                return True
            raise AssessmentPermissionDenied("Administrators have read-only oversight of assessments.")
        if _college_only(user):
            raise AssessmentPermissionDenied("College users cannot access University assessments.")

        if policy.is_reviewer(user):
            university = getattr(obj, 'university', None)
            if policy.has_conflict_of_interest(user, university):
                raise AssessmentPermissionDenied(
                    "Conflict of interest: reviewer cannot inspect own institution assessment.", code="REVIEW_CONFLICT")
            if getattr(obj, 'status', None) in policy.INSTITUTION_EDITING_STATES:
                raise AssessmentPermissionDenied("This assessment has not been submitted for review.")
            if not policy.has_review_scope(user, policy.UNIVERSITY, university, getattr(obj, 'assigned_reviewer_id', None)):
                raise AssessmentPermissionDenied(
                    "Reviewer is not assigned to, or authorized for, this University assessment.",
                    code=policy.scope_denial_code(user, policy.UNIVERSITY))
            if request.method not in SAFE_METHODS and view.__class__.__name__ in self.REVIEWER_FORBIDDEN_WRITES:
                raise AssessmentPermissionDenied(
                    "Reviewers are not permitted to submit parameter inputs or perform assessment submission.")
            return True

        user_uni = getattr(user, 'university', None)
        if user_uni and obj.university_id == user_uni.pk:
            return True
        raise AssessmentPermissionDenied("Institution users cannot access assessments belonging to other Universities.")


class IsCommitteeOrAdminForEvaluation(BasePermission):
    """
    Scoring evaluation: committee reviewers may run it; oversight administrators and the owning University may
    read (never persist) the live breakdown. Ownership/scope is enforced by the object permission.
    """
    def has_permission(self, request, view):
        user = _require_auth(request)
        if policy.is_reviewer(user):
            return True
        if request.method in SAFE_METHODS and (policy.is_oversight(user) or getattr(user, 'university', None)):
            return True
        raise AssessmentPermissionDenied(
            "Scoring evaluation requires committee reviewer authority.", code="ASSESSMENT_NOT_AUTHORIZED")


class IsCommitteeReviewer(BasePermission):
    """
    Review actions (start, accept/adjust, complete, return, reject) and the review queue:
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
        university = getattr(obj, 'university', obj)
        if policy.has_conflict_of_interest(user, university):
            raise AssessmentPermissionDenied(
                f"Conflict of interest: Reviewer belongs to institution '{university.name}'.", code="REVIEW_CONFLICT")
        if not policy.has_review_scope(user, policy.UNIVERSITY, university, getattr(obj, 'assigned_reviewer_id', None)):
            raise AssessmentPermissionDenied(
                "Reviewer is not assigned to, or authorized for, this University assessment.",
                code=policy.scope_denial_code(user, policy.UNIVERSITY))
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
        university = getattr(obj, 'university', obj)
        if policy.has_conflict_of_interest(user, university):
            raise AssessmentPermissionDenied(
                f"Conflict of interest: Actor belongs to institution '{university.name}'.", code="REVIEW_CONFLICT")
        if not policy.has_review_scope(user, policy.UNIVERSITY, university, getattr(obj, 'assigned_reviewer_id', None)):
            raise AssessmentPermissionDenied(
                "The Chair is not authorized for this University assessment.", code=policy.scope_denial_code(user, policy.UNIVERSITY))
        return True
