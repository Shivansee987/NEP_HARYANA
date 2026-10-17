"""
Single source of truth for who may see and act on assessments and their evidence.

Roles
- Oversight (head_admin, state_admin, sub_admin, admin, council_admin, superuser): READ-ONLY on assessments,
  evidence and scores. They never fill forms, upload or verify evidence, approve marks, or move an assessment
  through review. (Reviewer assignment and user/committee governance live in admin_panel.)
- Reviewers (committee, committee_chair): act only on assessments inside their review scope, never on their own
  institution, and never on an assessment the institution is still editing. Certification is chair-only.
- Institution users (principal, nodal_officer, university_admin): only their own bound institution. A
  self-registered applicant has no binding (user.college / user.university are empty) until approved.

Review scope
A reviewer may act on an assessment if they are its assigned reviewer, or hold an active ReviewerAuthorization
for the assessment's framework (or ALL) that is global (institution_id "") or names the institution.
There is no implicit "unrestricted" scope for reviewers without authorization rows.
"""
from apps.evidence.models import ReviewerAuthorization

OVERSIGHT_ROLES = frozenset({'head_admin', 'state_admin', 'sub_admin', 'admin', 'council_admin'})
REVIEWER_ROLES = frozenset({'committee', 'committee_chair'})
INSTITUTION_ROLES = frozenset({'principal', 'nodal_officer', 'university_admin', 'faculty'})

COLLEGE = 'COLLEGE_2026'
UNIVERSITY = 'UNIVERSITY_2026'
FRAMEWORK_ALIASES = {
    COLLEGE: (COLLEGE, 'COLLEGE', 'ALL'),
    UNIVERSITY: (UNIVERSITY, 'UNIVERSITY', 'ALL'),
}

# States in which the institution owns the assessment: reviewers can neither see nor act on it.
INSTITUTION_EDITING_STATES = frozenset({'DRAFT', 'RETURNED'})
# States in which review actions (verify evidence, accept/adjust marks, return, reject) are allowed.
REVIEWABLE_STATES = frozenset({'SUBMITTED', 'UNDER_REVIEW', 'EVALUATED', 'CERTIFICATION_PENDING'})
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


def role_of(user):
    return getattr(user, 'role', '') or ''


def is_oversight(user):
    return bool(getattr(user, 'is_superuser', False) or role_of(user) in OVERSIGHT_ROLES)


def is_reviewer(user):
    return role_of(user) in REVIEWER_ROLES


def normalize_framework(framework):
    f = str(framework or '').upper()
    if f.startswith('UNIVERSITY'):
        return UNIVERSITY
    if f.startswith('COLLEGE'):
        return COLLEGE
    return f


def institution_codes(institution):
    if institution is None:
        return []
    return [c for c in (getattr(institution, 'aishe_code', '') or '', str(institution.pk)) if c]


def has_conflict_of_interest(user, institution):
    """True when the actor belongs to the institution under review (by binding, not by shared AISHE code)."""
    if institution is None:
        return False
    for own in (getattr(user, 'college', None), getattr(user, 'university', None)):
        if own is not None and own.__class__ is institution.__class__ and own.pk == institution.pk:
            return True
    return False


def active_authorizations(user, framework):
    return ReviewerAuthorization.objects.filter(
        user=user, is_active=True, framework__in=FRAMEWORK_ALIASES.get(normalize_framework(framework), (framework,)))


def has_review_scope(user, framework, institution, assigned_reviewer_id=None):
    if not is_reviewer(user):
        return False
    if assigned_reviewer_id and assigned_reviewer_id == user.pk:
        return True
    return active_authorizations(user, framework).filter(institution_id__in=[''] + institution_codes(institution)).exists()


def scope_denial_code(user, framework):
    """FRAMEWORK_MISMATCH when the reviewer holds no authorization for the framework at all."""
    return 'REVIEW_NOT_AUTHORIZED' if active_authorizations(user, framework).exists() else 'FRAMEWORK_MISMATCH'


def review_scope_filter(user, framework):
    """
    Returns (global_scope, institution_codes, assigned_only) describing which assessments of `framework` a
    reviewer may see: everything (global authorization), assessments of the listed institutions, and always
    the ones assigned to them.
    """
    auths = active_authorizations(user, framework)
    if auths.filter(institution_id='').exists():
        return True, [], False
    return False, list(auths.exclude(institution_id='').values_list('institution_id', flat=True)), True


def reviewer_can_view_assessment(user, framework, institution, status, assigned_reviewer_id=None):
    return (is_reviewer(user)
            and status not in INSTITUTION_EDITING_STATES
            and not has_conflict_of_interest(user, institution)
            and has_review_scope(user, framework, institution, assigned_reviewer_id))


def resolve_assessment(assessment_id, framework=None):
    """Returns the College/University assessment an evidence document belongs to, or None."""
    if not assessment_id:
        return None
    fw = normalize_framework(framework)
    if fw != UNIVERSITY:
        from apps.college.models import CollegeAssessment
        found = CollegeAssessment.objects.select_related('college').filter(assessment_id=assessment_id).first()
        if found or fw == COLLEGE:
            return found
    from apps.university.models import UniversityAssessment
    return UniversityAssessment.objects.select_related('university').filter(assessment_id=assessment_id).first()


def assessment_institution(assessment):
    return getattr(assessment, 'college', None) or getattr(assessment, 'university', None)


def institution_owns_assessment(user, assessment):
    """True when the user is bound to the institution that owns the assessment."""
    if assessment is None:
        return False
    if hasattr(assessment, 'college_id'):
        return bool(getattr(user, 'college_id', None)) and user.college_id == assessment.college_id
    return bool(getattr(user, 'university_id', None)) and user.university_id == assessment.university_id


def can_read_document(user, doc):
    """
    Read access to an evidence document (metadata, file, history):
    - oversight administrators: always (read-only);
    - institution users: only documents of an assessment their institution currently owns. Having uploaded a
      document grants nothing by itself, so a user moved to another institution loses access (FIN-25); the one
      exception is a legacy document with no assessment, readable by its uploader while still bound to the
      institution it was filed for;
    - reviewers: documents of a submitted assessment within their scope and without conflict of interest.
    Ownership is resolved through the assessment, never through the AISHE code alone, so institutions that
    legitimately share an AISHE code cannot read each other's evidence.
    """
    if is_oversight(user):
        return True
    assessment = resolve_assessment(getattr(doc, 'assessment_id', None), getattr(doc, 'framework', None))
    if is_reviewer(user):
        if doc.assigned_reviewer_id and doc.assigned_reviewer_id == user.pk:
            return True
        if assessment is None:
            return active_authorizations(user, doc.framework).filter(institution_id__in=['', doc.institution_id]).exists()
        return reviewer_can_view_assessment(user, doc.framework, assessment_institution(assessment), assessment.status,
                                            getattr(assessment, 'assigned_reviewer_id', None))
    if role_of(user) in INSTITUTION_ROLES:
        if assessment is None:
            return doc.uploader_id == user.pk and uploader_still_bound(user, doc)
        return institution_owns_assessment(user, assessment)
    return False


def uploader_still_bound(user, doc):
    """True when the user is still bound to the institution a (legacy, assessment-less) document was filed for."""
    own = getattr(user, 'college', None) or getattr(user, 'university', None)
    return bool(own) and getattr(doc, 'institution_id', '') in institution_codes(own)


def readable_assessment_ids(user):
    """
    Assessment ids whose evidence the user may list, or None for "all" (oversight administrators).
    Institution users: their own institution's assessments. Reviewers: submitted assessments in their review
    queue for either framework (scope, conflict-of-interest and draft rules applied there).
    """
    if is_oversight(user):
        return None
    from apps.college.models import CollegeAssessment
    from apps.university.models import UniversityAssessment
    if is_reviewer(user):
        from apps.college.services import CollegeReviewService
        from apps.university.services import UniversityReviewService
        ids = set(CollegeReviewService.get_review_queue(user=user).values_list('assessment_id', flat=True))
        ids |= set(UniversityReviewService.get_review_queue(user=user).values_list('assessment_id', flat=True))
        return ids
    ids = set()
    if getattr(user, 'college_id', None):
        ids |= set(CollegeAssessment.objects.filter(college_id=user.college_id).values_list('assessment_id', flat=True))
    if getattr(user, 'university_id', None):
        ids |= set(UniversityAssessment.objects.filter(university_id=user.university_id).values_list('assessment_id', flat=True))
    return ids
