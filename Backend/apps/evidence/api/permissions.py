"""
NEP Excellence Awards 2026 - Evidence API Permissions
Role-based access and institution isolation; the rules live in apps.evidence.access_policy.
"""
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import BasePermission, IsAuthenticated

from apps.evidence import access_policy as policy


class IsAuthenticatedUser(IsAuthenticated):
    """Requires request.user to be authenticated. Emits 401 when missing."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            raise NotAuthenticated()
        return True


class IsEvidenceOwnerOrAdmin(BasePermission):
    """
    Object-level permission for EvidenceDocument / EvidenceSubcriterionAssociation:
    - Read (GET): oversight administrators; the institution that owns the assessment (resolved through the
      assessment, not the AISHE code); reviewers in scope once the assessment is submitted.
    - Write (submit, withdraw, associate): only the owning institution's users. Administrators and reviewers
      never change an institution's evidence.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            raise NotAuthenticated()
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated()
        doc = getattr(obj, 'evidence', obj)
        if request.method in policy.SAFE_METHODS:
            return policy.can_read_document(user, doc)
        if policy.role_of(user) not in policy.INSTITUTION_ROLES:
            return False
        assessment = policy.resolve_assessment(doc.assessment_id, doc.framework)
        if assessment is None:
            return doc.uploader_id == user.pk and policy.uploader_still_bound(user, doc)
        return policy.institution_owns_assessment(user, assessment)


class IsCommitteeRole(BasePermission):
    """
    Evidence decisions (verify / reject) and the evidence review queue: Screening Committee members and chairs.
    Oversight administrators may read the queue but never decide.
    """
    message = "Screening Committee authority required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated()
        if policy.is_reviewer(user):
            return True
        return request.method in policy.SAFE_METHODS and policy.is_oversight(user)


class IsStateAdminRole(BasePermission):
    """Reviewer assignment for evidence: Head/State/Sub/legacy Admin (the Council Admin Overseer is read-only)."""
    message = "Administrator privileges required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated()
        return bool(getattr(user, 'is_superuser', False)
                    or policy.role_of(user) in ('head_admin', 'state_admin', 'sub_admin', 'admin'))
