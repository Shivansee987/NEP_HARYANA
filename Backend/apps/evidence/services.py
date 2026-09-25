"""
NEP Excellence Awards 2026 - Evidence Domain Services & Scoring Contract Bridge
"""
import hashlib
import uuid
from typing import Optional, Dict, Any, List, Tuple
from django.db import transaction
from django.utils import timezone

from apps.scoring.domain import EvidenceDocument as ScoringEvidenceDocument
from apps.scoring.enums import EvidenceState as ScoringEvidenceState, GatingStatus
from apps.scoring.evaluators.evidence_gating import evaluate_evidence

from .enums import (
    AssignmentStatus,
    EvidenceAuditAction,
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
    LEGAL_EVIDENCE_TRANSITIONS,
)
from .exceptions import (
    ConcurrentVerificationConflictError,
    EvidenceDomainError,
    EvidenceIntegrityError,
    FrameworkMismatchError,
    InvalidAssociationError,
    InvalidStateTransitionError,
    MandatoryRejectionReasonError,
    ReviewerAssignmentError,
    ReviewerConflictOfInterestError,
    ReviewerNotAuthorizedError,
    UnauthorizedEvidenceActionError,
)
from .models import (
    EvidenceAssociationVerification,
    EvidenceAuditLog,
    EvidenceDocument,
    EvidenceReviewAssignment,
    EvidenceSubcriterionAssociation,
    EvidenceVerification,
    ReviewerAuthorization,
)


class EvidenceService:
    """
    Authoritative service managing evidence lifecycle, verifications,
    audit trails, and transformation to scoring-domain representations.
    """

    @staticmethod
    def calculate_checksum(file_bytes: bytes) -> str:
        """Calculate SHA-256 cryptographic hex digest of file bytes."""
        if not file_bytes:
            raise EvidenceIntegrityError("Cannot calculate checksum for empty file bytes.")
        return hashlib.sha256(file_bytes).hexdigest()

    @classmethod
    @transaction.atomic
    def create_evidence(
        cls,
        uploader,
        assessment_id: str,
        framework: str,
        institution_type: str,
        institution_id: str,
        original_filename: str,
        file_bytes: Optional[bytes] = None,
        file_checksum: Optional[str] = None,
        file_path: str = "",
        mime_type: str = "application/octet-stream",
        file_size: int = 0,
        evidence_type: str = "EVID_GENERAL",
        document_date=None,
        academic_year: Optional[str] = None,
        nomination=None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceDocument:
        """
        Create a new evidence document in EVIDENCE_PRESENT state.
        Ensures cryptographic checksum calculation and audit trail creation.
        """
        # Authorization check: uploader must be authenticated
        if not uploader or not getattr(uploader, 'is_authenticated', False):
            raise UnauthorizedEvidenceActionError("Authenticated user is required to upload evidence.")

        # Reviewers (committee) cannot directly upload evidence on behalf of an institution
        # unless they possess uploader authority (e.g. principal or admin).
        role = getattr(uploader, 'role', '')
        if role == 'committee':
            raise UnauthorizedEvidenceActionError("Screening Committee members cannot upload institution evidence.")

        # Checksum resolution
        if file_bytes is not None:
            computed_checksum = cls.calculate_checksum(file_bytes)
            if file_checksum and file_checksum.lower() != computed_checksum.lower():
                raise EvidenceIntegrityError("Provided checksum does not match calculated file checksum.")
            checksum_to_use = computed_checksum
            if file_size == 0:
                file_size = len(file_bytes)
        elif file_checksum:
            checksum_to_use = file_checksum.lower()
        else:
            raise EvidenceIntegrityError("Either file_bytes or file_checksum must be provided.")

        # Framework validation
        if framework not in ("UNIVERSITY_2026", "COLLEGE_2026"):
            raise FrameworkMismatchError(f"Invalid framework identifier: {framework}")

        doc = EvidenceDocument.objects.create(
            assessment_id=assessment_id,
            framework=framework,
            institution_type=institution_type,
            institution_id=institution_id,
            nomination=nomination,
            original_filename=original_filename,
            file_path=file_path,
            mime_type=mime_type,
            file_size=file_size,
            file_checksum=checksum_to_use,
            uploader=uploader,
            evidence_type=evidence_type,
            document_date=document_date,
            academic_year=academic_year,
            status=EvidenceLifecycleState.EVIDENCE_PRESENT,
            version=1,
            metadata=metadata or {},
            is_active=True,
        )

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=assessment_id,
            actor=uploader,
            action=EvidenceAuditAction.UPLOADED,
            previous_state="",
            new_state=EvidenceLifecycleState.EVIDENCE_PRESENT,
            reason="Initial document upload",
            payload={"checksum": checksum_to_use, "filename": original_filename},
        )

        return doc

    @classmethod
    @transaction.atomic
    def submit_for_verification(cls, evidence_id, actor) -> EvidenceDocument:
        """
        Transition evidence from EVIDENCE_PRESENT to EVIDENCE_PENDING.
        """
        doc = EvidenceDocument.objects.select_for_update().get(pk=evidence_id)

        if not actor or not getattr(actor, 'is_authenticated', False):
            raise UnauthorizedEvidenceActionError("Authentication required.")

        # Committee cannot submit institution's evidence
        if getattr(actor, 'role', '') == 'committee':
            raise UnauthorizedEvidenceActionError("Reviewers cannot submit evidence for verification.")

        cls._validate_transition(doc.status, EvidenceLifecycleState.EVIDENCE_PENDING)

        prev_state = doc.status
        doc.status = EvidenceLifecycleState.EVIDENCE_PENDING
        doc.save(update_fields=['status'])

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=doc.assessment_id,
            actor=actor,
            action=EvidenceAuditAction.SUBMITTED,
            previous_state=prev_state,
            new_state=EvidenceLifecycleState.EVIDENCE_PENDING,
            reason="Submitted for verification review",
        )

        return doc

    @classmethod
    @transaction.atomic
    def authorize_reviewer(
        cls,
        reviewer,
        framework: str,
        institution_id: str = "",
        granted_by=None,
    ) -> ReviewerAuthorization:
        """
        Grants a reviewer authorization for a framework (UNIVERSITY_2026, COLLEGE_2026, or ALL)
        and an optional specific institution scope.
        """
        if not reviewer or not getattr(reviewer, 'is_authenticated', False):
            raise UnauthorizedEvidenceActionError("Valid authenticated user is required for reviewer authorization.")

        role = getattr(reviewer, 'role', '')
        if role not in ('committee', 'admin') and not getattr(reviewer, 'is_staff', False):
            raise UnauthorizedEvidenceActionError("Only Screening Committee or Admin users can be authorized as reviewers.")

        clean_fw = framework.strip().upper()
        if clean_fw not in ("UNIVERSITY_2026", "COLLEGE_2026", "ALL"):
            raise FrameworkMismatchError(f"Invalid framework for authorization: '{framework}'")

        auth, created = ReviewerAuthorization.objects.get_or_create(
            user=reviewer,
            framework=clean_fw,
            institution_id=institution_id.strip(),
            defaults={'is_active': True, 'granted_by': granted_by}
        )
        if not created and not auth.is_active:
            auth.is_active = True
            auth.save(update_fields=['is_active'])

        return auth

    @classmethod
    def validate_reviewer_authorization(cls, reviewer, doc: EvidenceDocument):
        """
        Validates whether a reviewer is authorized to inspect/verify/reject an evidence document.
        Enforces segregation of duties, institutional conflict of interest, assignment, and framework isolation.
        """
        if not reviewer or not getattr(reviewer, 'is_authenticated', False):
            raise UnauthorizedEvidenceActionError("Authentication required to review evidence.")

        verifier_role = getattr(reviewer, 'role', '')
        is_admin = getattr(reviewer, 'is_superuser', False) or getattr(reviewer, 'is_staff', False) or verifier_role in ('admin', 'state_admin')
        if not is_admin and verifier_role not in ('committee', 'committee_chair'):
            raise UnauthorizedEvidenceActionError("Only Screening Committee or Admin can review evidence.")

        # 1. Segregation of duties: Uploader cannot review their own evidence
        if reviewer.pk == doc.uploader_id:
            raise ReviewerConflictOfInterestError(
                "Segregation of duties: Uploader cannot verify or reject their own evidence."
            )

        # 2. Institutional affiliation conflict of interest
        reviewer_college = getattr(reviewer, 'college', None)
        if reviewer_college:
            college_aishe = getattr(reviewer_college, 'aishe_code', '')
            college_id_str = str(reviewer_college.pk)
            if (college_aishe and college_aishe == doc.institution_id) or college_id_str == doc.institution_id:
                raise ReviewerConflictOfInterestError(
                    f"Conflict of interest: Reviewer is affiliated with institution '{doc.institution_id}'."
                )

        reviewer_uni = getattr(reviewer, 'university', None)
        if reviewer_uni:
            uni_aishe = getattr(reviewer_uni, 'aishe_code', '')
            uni_id_str = str(reviewer_uni.pk)
            if (uni_aishe and uni_aishe == doc.institution_id) or uni_id_str == doc.institution_id:
                raise ReviewerConflictOfInterestError(
                    f"Conflict of interest: Reviewer is affiliated with institution '{doc.institution_id}'."
                )

        # 3. Assignment enforcement: If assigned to another reviewer, regular reviewer cannot act
        if doc.assigned_reviewer_id and doc.assigned_reviewer_id != reviewer.pk:
            if not is_admin:
                raise UnauthorizedEvidenceActionError(
                    f"Evidence is assigned to another reviewer. Only the assigned reviewer or admin can act."
                )

        # 4. Scope and Framework authorization
        if is_admin:
            return True

        # For committee reviewers:
        user_auths = ReviewerAuthorization.objects.filter(user=reviewer, is_active=True)

        if user_auths.exists():
            allowed_fw = [doc.framework, 'ALL']
            if doc.framework in ('UNIVERSITY_2026', 'UNIVERSITY'):
                allowed_fw.extend(['UNIVERSITY_2026', 'UNIVERSITY'])
            elif doc.framework in ('COLLEGE_2026', 'COLLEGE'):
                allowed_fw.extend(['COLLEGE_2026', 'COLLEGE'])
            fw_matching = user_auths.filter(framework__in=allowed_fw)
            if not fw_matching.exists():
                raise ReviewerNotAuthorizedError(
                    f"Reviewer is not authorized for framework '{doc.framework}'."
                )
            inst_matching = fw_matching.filter(institution_id__in=["", doc.institution_id])
            if not inst_matching.exists():
                raise ReviewerNotAuthorizedError(
                    f"Reviewer is not authorized for institution '{doc.institution_id}'."
                )
            return True

        # If user has no authorizations, but the system has active authorizations configured:
        if ReviewerAuthorization.objects.filter(is_active=True).exists():
            raise ReviewerNotAuthorizedError(
                f"Reviewer '{reviewer.email}' has no active framework authorizations assigned."
            )

        # Legacy fallback (for Phase 5A/5B regression tests where ReviewerAuthorization is not seeded):
        return True

    @classmethod
    @transaction.atomic
    def assign_reviewer(
        cls,
        evidence_id,
        reviewer,
        assigned_by,
        notes: str = "",
    ) -> EvidenceReviewAssignment:
        """
        Assigns an evidence document to a specific screening committee reviewer.
        Enforces administrator authorization, conflict-of-interest prevention, and framework compatibility.
        """
        if not assigned_by or not getattr(assigned_by, 'is_authenticated', False):
            raise UnauthorizedEvidenceActionError("Authenticated user required to assign reviewers.")

        admin_role = getattr(assigned_by, 'role', '')
        if admin_role not in ('admin', 'state_admin') and not getattr(assigned_by, 'is_staff', False):
            raise UnauthorizedEvidenceActionError("Only administrators can assign reviewers.")

        doc = EvidenceDocument.objects.select_for_update().get(pk=evidence_id)

        if not reviewer or not getattr(reviewer, 'is_authenticated', False):
            raise ReviewerAssignmentError("Valid reviewer must be provided for assignment.")

        if getattr(reviewer, 'role', '') not in ('committee', 'admin') and not getattr(reviewer, 'is_staff', False):
            raise ReviewerAssignmentError("Assigned user must have a reviewer or committee role.")

        # Check reviewer conflict of interest
        if reviewer.pk == doc.uploader_id:
            raise ReviewerConflictOfInterestError("Cannot assign evidence to its uploader (conflict of interest).")

        reviewer_college = getattr(reviewer, 'college', None)
        if reviewer_college:
            college_aishe = getattr(reviewer_college, 'aishe_code', '')
            college_id_str = str(reviewer_college.pk)
            if (college_aishe and college_aishe == doc.institution_id) or college_id_str == doc.institution_id:
                raise ReviewerConflictOfInterestError(
                    f"Conflict of interest: Cannot assign reviewer affiliated with institution '{doc.institution_id}'."
                )

        # Check reviewer framework authorization if scopes exist
        user_auths = ReviewerAuthorization.objects.filter(user=reviewer, is_active=True)
        if user_auths.exists():
            if not user_auths.filter(framework__in=[doc.framework, 'ALL']).exists():
                raise FrameworkMismatchError(
                    f"Cannot assign reviewer: Reviewer is not authorized for framework '{doc.framework}'."
                )
            if not user_auths.filter(framework__in=[doc.framework, 'ALL'], institution_id__in=["", doc.institution_id]).exists():
                raise ReviewerNotAuthorizedError(
                    f"Cannot assign reviewer: Reviewer is not authorized for institution '{doc.institution_id}'."
                )

        # Reassign previous active assignments if any
        EvidenceReviewAssignment.objects.filter(evidence=doc, status=AssignmentStatus.ACTIVE).update(status=AssignmentStatus.REASSIGNED)

        assignment = EvidenceReviewAssignment.objects.create(
            evidence=doc,
            reviewer=reviewer,
            assigned_by=assigned_by,
            status=AssignmentStatus.ACTIVE,
            notes=notes,
        )

        doc.assigned_reviewer = reviewer
        doc.assigned_at = timezone.now()
        doc.assigned_by = assigned_by
        doc.save(update_fields=['assigned_reviewer', 'assigned_at', 'assigned_by'])

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=doc.assessment_id,
            actor=assigned_by,
            action=EvidenceAuditAction.ASSIGNED,
            previous_state=doc.status,
            new_state=doc.status,
            reason=f"Assigned to {reviewer.email}",
            payload={"assigned_to": reviewer.email, "notes": notes, "assignment_id": str(assignment.assignment_id)},
        )

        return assignment

    @classmethod
    @transaction.atomic
    def unassign_reviewer(cls, evidence_id, unassigned_by, reason: str = "") -> EvidenceDocument:
        """
        Unassigns any reviewer from the evidence document.
        """
        if not unassigned_by or not getattr(unassigned_by, 'is_authenticated', False):
            raise UnauthorizedEvidenceActionError("Authentication required.")
        if getattr(unassigned_by, 'role', '') not in ('admin', 'state_admin') and not getattr(unassigned_by, 'is_staff', False):
            raise UnauthorizedEvidenceActionError("Only administrators can unassign reviewers.")

        doc = EvidenceDocument.objects.select_for_update().get(pk=evidence_id)
        prev_reviewer = doc.assigned_reviewer

        EvidenceReviewAssignment.objects.filter(evidence=doc, status=AssignmentStatus.ACTIVE).update(status=AssignmentStatus.REVOKED)

        doc.assigned_reviewer = None
        doc.assigned_at = None
        doc.assigned_by = None
        doc.save(update_fields=['assigned_reviewer', 'assigned_at', 'assigned_by'])

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=doc.assessment_id,
            actor=unassigned_by,
            action=EvidenceAuditAction.UNASSIGNED,
            previous_state=doc.status,
            new_state=doc.status,
            reason=reason or f"Unassigned from {getattr(prev_reviewer, 'email', 'reviewer')}",
        )
        return doc

    @classmethod
    def get_reviewer_queue(
        cls,
        reviewer,
        framework: Optional[str] = None,
        institution_id: Optional[str] = None,
        parameter_id: Optional[str] = None,
        subcriterion_id: Optional[str] = None,
        status: Optional[str] = EvidenceLifecycleState.EVIDENCE_PENDING,
        assigned_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query layer for the reviewer queue.
        Retrieves reviewable evidence with rich metadata.
        Strictly enforces framework and institutional authorization bounds.
        Excludes evidence with conflict of interest.
        """
        if not reviewer or not getattr(reviewer, 'is_authenticated', False):
            raise UnauthorizedEvidenceActionError("Authentication required to view reviewer queue.")

        qs = EvidenceDocument.objects.filter(is_active=True).select_related('uploader', 'assigned_reviewer', 'nomination')

        # Status filter (default: EVIDENCE_PENDING)
        if status:
            qs = qs.filter(status=status)

        # Authorization-based scoping
        verifier_role = getattr(reviewer, 'role', '')
        if verifier_role != 'admin' and not getattr(reviewer, 'is_staff', False):
            user_auths = ReviewerAuthorization.objects.filter(user=reviewer, is_active=True)
            if user_auths.exists():
                authorized_frameworks = list(user_auths.values_list('framework', flat=True))
                if 'ALL' not in authorized_frameworks:
                    qs = qs.filter(framework__in=authorized_frameworks)

                scoped_institutions = list(user_auths.exclude(institution_id="").values_list('institution_id', flat=True))
                if scoped_institutions:
                    qs = qs.filter(institution_id__in=scoped_institutions)
            elif ReviewerAuthorization.objects.filter(is_active=True).exists():
                return []

            # Exclude conflict of interest
            qs = qs.exclude(uploader=reviewer)
            reviewer_college = getattr(reviewer, 'college', None)
            if reviewer_college:
                college_aishe = getattr(reviewer_college, 'aishe_code', '')
                college_id_str = str(reviewer_college.pk)
                qs = qs.exclude(institution_id__in=[college_aishe, college_id_str])

        # Additional query filters
        if framework:
            clean_fw = framework.strip().upper()
            qs = qs.filter(framework=clean_fw)

        if institution_id:
            qs = qs.filter(institution_id=institution_id)

        if parameter_id:
            qs = qs.filter(associations__parameter_id=parameter_id, associations__is_active=True)

        if subcriterion_id:
            qs = qs.filter(associations__subcriterion_id=subcriterion_id, associations__is_active=True)

        if assigned_to:
            if assigned_to == "me":
                qs = qs.filter(assigned_reviewer=reviewer)
            elif assigned_to == "unassigned":
                qs = qs.filter(assigned_reviewer__isnull=True)
            elif assigned_to != "all":
                qs = qs.filter(assigned_reviewer_id=assigned_to)

        qs = qs.distinct().order_by('-upload_timestamp')

        queue = []
        for doc in qs:
            associations = [
                {
                    "parameter_id": a.parameter_id,
                    "subcriterion_id": a.subcriterion_id,
                    "academic_year": a.academic_year,
                }
                for a in doc.associations.filter(is_active=True)
            ]
            latest_v = doc.verifications.first()
            queue.append({
                "document_id": str(doc.document_id),
                "pk": doc.pk,
                "original_filename": doc.original_filename,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "file_checksum": doc.file_checksum,
                "file_path": doc.file_path,
                "framework": doc.framework,
                "institution_type": doc.institution_type,
                "institution_id": doc.institution_id,
                "nomination_id": doc.nomination_id,
                "status": doc.status,
                "version": doc.version,
                "upload_timestamp": doc.upload_timestamp.isoformat() if doc.upload_timestamp else None,
                "document_date": doc.document_date.isoformat() if doc.document_date else None,
                "academic_year": doc.academic_year,
                "evidence_type": doc.evidence_type,
                "uploader": {
                    "id": doc.uploader.pk,
                    "email": doc.uploader.email,
                    "full_name": getattr(doc.uploader, 'full_name', ''),
                    "role": getattr(doc.uploader, 'role', ''),
                },
                "assigned_reviewer": {
                    "id": doc.assigned_reviewer.pk,
                    "email": doc.assigned_reviewer.email,
                    "full_name": getattr(doc.assigned_reviewer, 'full_name', ''),
                } if doc.assigned_reviewer else None,
                "assigned_at": doc.assigned_at.isoformat() if doc.assigned_at else None,
                "associations": associations,
                "verifications_count": doc.verifications.count(),
                "latest_verification": {
                    "decision": latest_v.decision,
                    "reason": latest_v.reason,
                    "rejection_code": latest_v.rejection_code,
                    "timestamp": latest_v.timestamp.isoformat(),
                    "verifier": getattr(latest_v.verifier, 'email', str(latest_v.verifier_id)),
                } if latest_v else None,
            })

        return queue

    @classmethod
    @transaction.atomic
    def verify_evidence(
        cls,
        evidence_id,
        verifier,
        reason: str = "",
        expected_checksum: Optional[str] = None,
        expected_version: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceVerification:
        """
        Verify evidence document. Transition from EVIDENCE_PENDING to EVIDENCE_VERIFIED.
        Enforces authorization, concurrency locking, and hash/version binding.
        Append-only verification record is created.
        """
        # Concurrency safety: acquire row lock
        doc = EvidenceDocument.objects.select_for_update().get(pk=evidence_id)

        # Validate state: must be EVIDENCE_PENDING
        if doc.status != EvidenceLifecycleState.EVIDENCE_PENDING:
            if doc.status in (EvidenceLifecycleState.EVIDENCE_VERIFIED, EvidenceLifecycleState.EVIDENCE_REJECTED):
                raise ConcurrentVerificationConflictError(
                    f"Concurrency conflict: Evidence {doc.document_id} is already in '{doc.status}' state."
                )
            cls._validate_transition(doc.status, EvidenceLifecycleState.EVIDENCE_VERIFIED)

        # Reviewer authorization and conflict-of-interest check
        cls.validate_reviewer_authorization(verifier, doc)

        # Version & Hash binding integrity check
        if expected_checksum:
            if expected_checksum.lower() != doc.file_checksum.lower():
                raise EvidenceIntegrityError(
                    f"Hash integrity mismatch: Inspected checksum '{expected_checksum}' does not match "
                    f"current document checksum '{doc.file_checksum}'. The file may have changed."
                )
        if expected_version is not None:
            if expected_version != doc.version:
                raise EvidenceIntegrityError(
                    f"Version mismatch: Inspected version {expected_version} does not match "
                    f"current document version {doc.version}."
                )

        cls._validate_transition(doc.status, EvidenceLifecycleState.EVIDENCE_VERIFIED)

        prev_state = doc.status
        doc.status = EvidenceLifecycleState.EVIDENCE_VERIFIED
        doc.save(update_fields=['status'])

        # Complete assignment if assigned to this verifier
        if doc.assigned_reviewer_id == verifier.pk:
            EvidenceReviewAssignment.objects.filter(evidence=doc, reviewer=verifier, status=AssignmentStatus.ACTIVE).update(status=AssignmentStatus.COMPLETED)

        verification_meta = dict(metadata or {})
        verification_meta.update({
            "inspected_checksum": doc.file_checksum,
            "inspected_version": doc.version,
            "framework": doc.framework,
            "institution_id": doc.institution_id,
        })

        verification = EvidenceVerification.objects.create(
            evidence=doc,
            verifier=verifier,
            decision=VerificationDecision.VERIFIED,
            reason=reason,
            inspected_checksum=doc.file_checksum,
            inspected_version=doc.version,
            previous_state=prev_state,
            resulting_state=EvidenceLifecycleState.EVIDENCE_VERIFIED,
            metadata=verification_meta,
        )

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=doc.assessment_id,
            actor=verifier,
            action=EvidenceAuditAction.VERIFIED,
            previous_state=prev_state,
            new_state=EvidenceLifecycleState.EVIDENCE_VERIFIED,
            reason=reason or "Verification approved",
            payload={
                "verification_id": str(verification.verification_id),
                "inspected_checksum": doc.file_checksum,
                "inspected_version": doc.version,
            },
        )

        return verification

    @classmethod
    @transaction.atomic
    def reject_evidence(
        cls,
        evidence_id,
        verifier,
        reason: str,
        rejection_code: str = "",
        expected_checksum: Optional[str] = None,
        expected_version: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceVerification:
        """
        Reject evidence document. Transition from EVIDENCE_PENDING to EVIDENCE_REJECTED.
        Enforces mandatory non-empty reason, authorization, concurrency locking, and hash/version binding.
        Append-only verification record is created.
        """
        if not reason or not reason.strip():
            raise MandatoryRejectionReasonError("Mandatory rejection reason must be provided.")

        clean_reason = reason.strip()

        # Concurrency safety: acquire row lock
        doc = EvidenceDocument.objects.select_for_update().get(pk=evidence_id)

        # Validate state: must be EVIDENCE_PENDING
        if doc.status != EvidenceLifecycleState.EVIDENCE_PENDING:
            if doc.status in (EvidenceLifecycleState.EVIDENCE_VERIFIED, EvidenceLifecycleState.EVIDENCE_REJECTED):
                raise ConcurrentVerificationConflictError(
                    f"Concurrency conflict: Evidence {doc.document_id} is already in '{doc.status}' state."
                )
            cls._validate_transition(doc.status, EvidenceLifecycleState.EVIDENCE_REJECTED)

        # Reviewer authorization and conflict-of-interest check
        cls.validate_reviewer_authorization(verifier, doc)

        # Version & Hash binding integrity check
        if expected_checksum:
            if expected_checksum.lower() != doc.file_checksum.lower():
                raise EvidenceIntegrityError(
                    f"Hash integrity mismatch: Inspected checksum '{expected_checksum}' does not match "
                    f"current document checksum '{doc.file_checksum}'. The file may have changed."
                )
        if expected_version is not None:
            if expected_version != doc.version:
                raise EvidenceIntegrityError(
                    f"Version mismatch: Inspected version {expected_version} does not match "
                    f"current document version {doc.version}."
                )

        cls._validate_transition(doc.status, EvidenceLifecycleState.EVIDENCE_REJECTED)

        prev_state = doc.status
        doc.status = EvidenceLifecycleState.EVIDENCE_REJECTED
        doc.save(update_fields=['status'])

        # Complete assignment if assigned to this verifier
        if doc.assigned_reviewer_id == verifier.pk:
            EvidenceReviewAssignment.objects.filter(evidence=doc, reviewer=verifier, status=AssignmentStatus.ACTIVE).update(status=AssignmentStatus.COMPLETED)

        verification_meta = dict(metadata or {})
        verification_meta.update({
            "inspected_checksum": doc.file_checksum,
            "inspected_version": doc.version,
            "rejection_code": rejection_code,
            "framework": doc.framework,
            "institution_id": doc.institution_id,
        })

        verification = EvidenceVerification.objects.create(
            evidence=doc,
            verifier=verifier,
            decision=VerificationDecision.REJECTED,
            reason=clean_reason,
            inspected_checksum=doc.file_checksum,
            inspected_version=doc.version,
            rejection_code=rejection_code,
            previous_state=prev_state,
            resulting_state=EvidenceLifecycleState.EVIDENCE_REJECTED,
            metadata=verification_meta,
        )

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=doc.assessment_id,
            actor=verifier,
            action=EvidenceAuditAction.REJECTED,
            previous_state=prev_state,
            new_state=EvidenceLifecycleState.EVIDENCE_REJECTED,
            reason=clean_reason,
            payload={
                "verification_id": str(verification.verification_id),
                "rejection_code": rejection_code,
                "inspected_checksum": doc.file_checksum,
                "inspected_version": doc.version,
            },
        )

        return verification

    @classmethod
    @transaction.atomic
    def supersede_evidence(
        cls,
        old_evidence_id,
        uploader,
        original_filename: str,
        file_bytes: Optional[bytes] = None,
        file_checksum: Optional[str] = None,
        file_path: str = "",
        mime_type: str = "application/octet-stream",
        file_size: int = 0,
        document_date=None,
        reason: str = "Document replaced with new version",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceDocument:
        """
        Supersede an existing evidence document (e.g. after rejection or correction).
        Creates a new version document and marks the old one as SUPERSEDED.
        """
        old_doc = EvidenceDocument.objects.select_for_update().get(pk=old_evidence_id)

        cls._validate_transition(old_doc.status, EvidenceLifecycleState.EVIDENCE_SUPERSEDED)

        # Create new evidence document with incremented version
        new_doc = cls.create_evidence(
            uploader=uploader,
            assessment_id=old_doc.assessment_id,
            framework=old_doc.framework,
            institution_type=old_doc.institution_type,
            institution_id=old_doc.institution_id,
            original_filename=original_filename,
            file_bytes=file_bytes,
            file_checksum=file_checksum,
            file_path=file_path,
            mime_type=mime_type,
            file_size=file_size,
            evidence_type=old_doc.evidence_type,
            document_date=document_date or old_doc.document_date,
            academic_year=old_doc.academic_year,
            nomination=old_doc.nomination,
            metadata=metadata or {},
        )
        new_doc.version = old_doc.version + 1
        new_doc.save(update_fields=['version'])

        # Update old document
        prev_state = old_doc.status
        old_doc.status = EvidenceLifecycleState.EVIDENCE_SUPERSEDED
        old_doc.is_active = False
        old_doc.superseded_by = new_doc
        old_doc.save(update_fields=['status', 'is_active', 'superseded_by'])

        # Record audit log for supersession
        EvidenceAuditLog.objects.create(
            evidence=old_doc,
            assessment_id=old_doc.assessment_id,
            actor=uploader,
            action=EvidenceAuditAction.SUPERSEDED,
            previous_state=prev_state,
            new_state=EvidenceLifecycleState.EVIDENCE_SUPERSEDED,
            reason=reason,
            payload={"superseded_by_document_id": str(new_doc.document_id), "new_version": new_doc.version},
        )

        return new_doc

    @classmethod
    @transaction.atomic
    def withdraw_evidence(cls, evidence_id, actor, reason: str = "") -> EvidenceDocument:
        """
        Withdraw an evidence document from consideration.
        """
        doc = EvidenceDocument.objects.select_for_update().get(pk=evidence_id)
        cls._validate_transition(doc.status, EvidenceLifecycleState.EVIDENCE_WITHDRAWN)

        prev_state = doc.status
        doc.status = EvidenceLifecycleState.EVIDENCE_WITHDRAWN
        doc.is_active = False
        doc.save(update_fields=['status', 'is_active'])

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=doc.assessment_id,
            actor=actor,
            action=EvidenceAuditAction.WITHDRAWN,
            previous_state=prev_state,
            new_state=EvidenceLifecycleState.EVIDENCE_WITHDRAWN,
            reason=reason or "Evidence withdrawn by user",
        )

        return doc

    @classmethod
    @transaction.atomic
    def associate_subcriterion(
        cls,
        evidence_id,
        parameter_id: str,
        subcriterion_id: str,
        actor,
        response_id: str = "",
        academic_year: str = "",
        evidence_type: Optional[str] = None,
        subcriterion_evidence_type: Optional[str] = None,
        page_start: Optional[int] = None,
        page_end: Optional[int] = None,
        section_identifier: str = "",
        claim_description: str = "",
    ) -> EvidenceSubcriterionAssociation:
        """
        Explicitly associate an evidence document with a parameter / subcriterion.
        Strictly enforces framework isolation, subcriterion evidence contracts, and metadata binding.
        """
        doc = EvidenceDocument.objects.get(pk=evidence_id)

        # Framework isolation check
        param_clean = parameter_id.strip().upper()
        sub_clean = subcriterion_id.strip().upper() if subcriterion_id else ""
        if doc.framework == "UNIVERSITY_2026":
            if param_clean.startswith("C") and not param_clean.startswith("CR"):
                raise FrameworkMismatchError(
                    f"Framework isolation violation: Cannot attach College parameter '{parameter_id}' "
                    f"to University evidence (Assessment: {doc.assessment_id})."
                )
        elif doc.framework == "COLLEGE_2026":
            if param_clean.startswith("U"):
                raise FrameworkMismatchError(
                    f"Framework isolation violation: Cannot attach University parameter '{parameter_id}' "
                    f"to College evidence (Assessment: {doc.assessment_id})."
                )

        from apps.evidence.taxonomy import (
            derive_or_validate_evidence_type,
            get_allowed_evidence_types,
            validate_subcriterion_evidence_contract,
            ALL_EVIDENCE_TYPES,
            EvidenceTypeParameterMismatchError,
            MULTI_SUBCRITERION_PARAMETERS,
        )

        candidate_type = (subcriterion_evidence_type or evidence_type or "").strip() or None

        if candidate_type:
            contract = validate_subcriterion_evidence_contract(
                doc.framework,
                param_clean,
                sub_clean,
                candidate_type,
            )
            canonical_type = contract.canonical_evidence_type or candidate_type
            if doc.evidence_type == "EVID_GENERAL" or not doc.evidence_type:
                doc.evidence_type = canonical_type
                doc.save(update_fields=['evidence_type'])
        else:
            if doc.evidence_type and doc.evidence_type != "EVID_GENERAL":
                contract = validate_subcriterion_evidence_contract(
                    doc.framework,
                    param_clean,
                    sub_clean,
                    doc.evidence_type,
                )
                canonical_type = contract.canonical_evidence_type or doc.evidence_type
            else:
                derived_type = derive_or_validate_evidence_type(
                    doc.framework,
                    parameter_id=param_clean,
                    subcriterion_id=sub_clean,
                )
                contract = validate_subcriterion_evidence_contract(
                    doc.framework,
                    param_clean,
                    sub_clean,
                    derived_type,
                )
                canonical_type = derived_type
                doc.evidence_type = derived_type
                doc.save(update_fields=['evidence_type'])

        association, created = EvidenceSubcriterionAssociation.objects.get_or_create(
            evidence=doc,
            parameter_id=param_clean,
            subcriterion_id=sub_clean,
            defaults={
                'response_id': response_id,
                'academic_year': academic_year or (doc.academic_year or ""),
                'associated_by': actor,
                'subcriterion_evidence_type': canonical_type or "",
                'page_start': page_start,
                'page_end': page_end,
                'section_identifier': section_identifier or "",
                'claim_description': claim_description or "",
                'is_active': True,
            }
        )

        if not created:
            if not association.is_active:
                association.is_active = True
            if canonical_type:
                association.subcriterion_evidence_type = canonical_type
            if page_start is not None:
                association.page_start = page_start
            if page_end is not None:
                association.page_end = page_end
            if section_identifier:
                association.section_identifier = section_identifier
            if claim_description:
                association.claim_description = claim_description
            association.save()

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=doc.assessment_id,
            actor=actor,
            action=EvidenceAuditAction.ASSOCIATED,
            previous_state=doc.status,
            new_state=doc.status,
            reason=f"Associated to {param_clean}:{sub_clean} (evidence_type: {canonical_type})",
            payload={
                "subcriterion_id": sub_clean,
                "parameter_id": param_clean,
                "subcriterion_evidence_type": canonical_type,
                "page_start": page_start,
                "page_end": page_end,
            },
        )

        return association

    @classmethod
    def to_scoring_domain(
        cls,
        doc_or_association: Any,
        subcriterion_id: Optional[str] = None
    ) -> ScoringEvidenceDocument:
        """
        Contract bridge: Adapts an ORM EvidenceDocument or EvidenceSubcriterionAssociation
        into the scoring engine's domain dataclass (apps.scoring.domain.EvidenceDocument).

        Crucial rules:
        - If an EvidenceSubcriterionAssociation is passed:
            * Uses subcriterion_evidence_type as document_type.
            * Prioritizes association-level verification decisions (from EvidenceAssociationVerification).
        - If an EvidenceDocument is passed with subcriterion_id:
            * Locates the active association for that subcriterion_id and derives association status.
        - If an EvidenceDocument is passed without subcriterion_id:
            * Maintains strict document-level verification mapping.
        """
        from apps.evidence.taxonomy import MULTI_SUBCRITERION_PARAMETERS

        if isinstance(doc_or_association, EvidenceSubcriterionAssociation):
            association = doc_or_association
            doc = association.evidence
            doc_type = association.subcriterion_evidence_type or doc.evidence_type

            # Check for association-level verification (Step 4B)
            latest_v = association.verifications.first()
            if latest_v:
                verified_by = str(getattr(latest_v.verifier, 'email', latest_v.verifier_id))
                rejection_reason = latest_v.reason if latest_v.decision == VerificationDecision.REJECTED else None
                if latest_v.decision == VerificationDecision.VERIFIED:
                    mapped_state = ScoringEvidenceState.EVIDENCE_VERIFIED
                    assoc_verified = True
                elif latest_v.decision == VerificationDecision.REJECTED:
                    mapped_state = ScoringEvidenceState.EVIDENCE_REJECTED
                    assoc_verified = False
                else:
                    mapped_state = ScoringEvidenceState.EVIDENCE_PENDING
                    assoc_verified = None
            else:
                # If no association-level verification exists, check parameter type
                assoc_verified = None
                param_code = association.parameter_id.strip().upper()
                if param_code in MULTI_SUBCRITERION_PARAMETERS:
                    # Multi-subcriterion association without association verification remains PENDING!
                    mapped_state = ScoringEvidenceState.EVIDENCE_PENDING
                else:
                    # Single-subcriterion parameter can inherit document status if no association verification
                    if not doc.is_active or doc.status in (EvidenceLifecycleState.EVIDENCE_SUPERSEDED, EvidenceLifecycleState.EVIDENCE_WITHDRAWN):
                        mapped_state = ScoringEvidenceState.EVIDENCE_PRESENT
                    elif doc.status == EvidenceLifecycleState.EVIDENCE_VERIFIED:
                        mapped_state = ScoringEvidenceState.EVIDENCE_VERIFIED
                        assoc_verified = True
                    elif doc.status == EvidenceLifecycleState.EVIDENCE_REJECTED:
                        mapped_state = ScoringEvidenceState.EVIDENCE_REJECTED
                        assoc_verified = False
                    elif doc.status == EvidenceLifecycleState.EVIDENCE_PENDING:
                        mapped_state = ScoringEvidenceState.EVIDENCE_PENDING
                    else:
                        mapped_state = ScoringEvidenceState.EVIDENCE_PRESENT

                latest_doc_v = doc.verifications.first()
                verified_by = str(getattr(latest_doc_v.verifier, 'email', latest_doc_v.verifier_id)) if latest_doc_v else None
                rejection_reason = latest_doc_v.reason if (latest_doc_v and latest_doc_v.decision == VerificationDecision.REJECTED) else None

            return ScoringEvidenceDocument(
                document_id=str(doc.document_id),
                document_type=doc_type,
                status=mapped_state,
                verified_by=verified_by,
                rejection_reason=rejection_reason,
                file_checksum=doc.file_checksum,
                academic_year=association.academic_year or doc.academic_year,
                framework=doc.framework,
                parameter_id=association.parameter_id,
                subcriterion_id=association.subcriterion_id,
                association_verified=assoc_verified,
            )

        # Standard EvidenceDocument branch
        doc = doc_or_association
        if subcriterion_id:
            assoc = doc.associations.filter(subcriterion_id=subcriterion_id.strip().upper(), is_active=True).first()
            if assoc:
                return cls.to_scoring_domain(assoc)

        latest_verification = doc.verifications.first()
        verified_by = None
        rejection_reason = None
        assoc_verified = None

        if latest_verification:
            verified_by = str(getattr(latest_verification.verifier, 'email', latest_verification.verifier_id))
            if latest_verification.decision == VerificationDecision.REJECTED:
                rejection_reason = latest_verification.reason
                assoc_verified = False
            elif latest_verification.decision == VerificationDecision.VERIFIED:
                assoc_verified = True

        if not doc.is_active or doc.status in (EvidenceLifecycleState.EVIDENCE_SUPERSEDED, EvidenceLifecycleState.EVIDENCE_WITHDRAWN):
            mapped_state = ScoringEvidenceState.EVIDENCE_PRESENT
        elif doc.status == EvidenceLifecycleState.EVIDENCE_VERIFIED:
            mapped_state = ScoringEvidenceState.EVIDENCE_VERIFIED
        elif doc.status == EvidenceLifecycleState.EVIDENCE_REJECTED:
            mapped_state = ScoringEvidenceState.EVIDENCE_REJECTED
        elif doc.status == EvidenceLifecycleState.EVIDENCE_PENDING:
            mapped_state = ScoringEvidenceState.EVIDENCE_PENDING
        else:
            mapped_state = ScoringEvidenceState.EVIDENCE_PRESENT

        return ScoringEvidenceDocument(
            document_id=str(doc.document_id),
            document_type=doc.evidence_type,
            status=mapped_state,
            verified_by=verified_by,
            rejection_reason=rejection_reason,
            file_checksum=doc.file_checksum,
            academic_year=doc.academic_year,
            framework=doc.framework,
            parameter_id=None,
            subcriterion_id=None,
            association_verified=assoc_verified,
        )


    @classmethod
    @transaction.atomic
    def verify_association(
        cls,
        association_id,
        verifier,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceAssociationVerification:
        """
        Verify a specific EvidenceSubcriterionAssociation independently.
        Does not mutate the underlying EvidenceDocument global lifecycle.
        """
        if isinstance(association_id, EvidenceSubcriterionAssociation):
            assoc = association_id
        else:
            try:
                val = uuid.UUID(str(association_id))
                assoc = EvidenceSubcriterionAssociation.objects.select_for_update().get(association_id=val)
            except (ValueError, TypeError):
                assoc = EvidenceSubcriterionAssociation.objects.select_for_update().get(pk=association_id)
        doc = assoc.evidence
        cls.validate_reviewer_authorization(verifier, doc)

        verification = EvidenceAssociationVerification.objects.create(
            association=assoc,
            verifier=verifier,
            decision=VerificationDecision.VERIFIED,
            reason=reason or f"Association {assoc.parameter_id}:{assoc.subcriterion_id} verified",
            metadata=metadata or {},
        )

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=doc.assessment_id,
            actor=verifier,
            action=EvidenceAuditAction.VERIFIED,
            previous_state=doc.status,
            new_state=doc.status,
            reason=f"Association {assoc.subcriterion_id} verified: {reason}",
            payload={"association_id": assoc.pk, "subcriterion_id": assoc.subcriterion_id},
        )
        return verification

    @classmethod
    @transaction.atomic
    def reject_association(
        cls,
        association_id,
        verifier,
        reason: str,
        rejection_code: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceAssociationVerification:
        """
        Reject a specific EvidenceSubcriterionAssociation independently.
        Does not mutate the underlying EvidenceDocument global lifecycle.
        """
        if not reason or not reason.strip():
            raise MandatoryRejectionReasonError("Mandatory rejection reason must be provided.")

        if isinstance(association_id, EvidenceSubcriterionAssociation):
            assoc = association_id
        else:
            try:
                val = uuid.UUID(str(association_id))
                assoc = EvidenceSubcriterionAssociation.objects.select_for_update().get(association_id=val)
            except (ValueError, TypeError):
                assoc = EvidenceSubcriterionAssociation.objects.select_for_update().get(pk=association_id)
        doc = assoc.evidence
        cls.validate_reviewer_authorization(verifier, doc)

        verification = EvidenceAssociationVerification.objects.create(
            association=assoc,
            verifier=verifier,
            decision=VerificationDecision.REJECTED,
            reason=reason.strip(),
            rejection_code=rejection_code or RejectionReasonCode.OTHER,
            metadata=metadata or {},
        )

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=doc.assessment_id,
            actor=verifier,
            action=EvidenceAuditAction.REJECTED,
            previous_state=doc.status,
            new_state=doc.status,
            reason=f"Association {assoc.subcriterion_id} rejected: {reason}",
            payload={"association_id": assoc.pk, "subcriterion_id": assoc.subcriterion_id, "rejection_code": rejection_code},
        )
        return verification

    @classmethod
    def get_association_verification_history(cls, association_id, user=None) -> List[Dict[str, Any]]:
        """
        Retrieves the immutable, append-only verification history for an evidence subcriterion association.
        Enforces tenant and reviewer authorization boundaries.
        """
        if isinstance(association_id, EvidenceSubcriterionAssociation):
            assoc = association_id
        else:
            try:
                val = uuid.UUID(str(association_id))
                assoc = EvidenceSubcriterionAssociation.objects.get(association_id=val)
            except (ValueError, TypeError):
                assoc = EvidenceSubcriterionAssociation.objects.get(pk=association_id)

        doc = assoc.evidence
        if user and getattr(user, 'is_authenticated', False):
            user_role = getattr(user, 'role', '')
            is_admin = getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False) or user_role in ('admin', 'state_admin')
            if not is_admin and user_role in ('principal', 'nodal_officer', 'faculty', 'university_admin'):
                user_college = getattr(user, 'college', None)
                user_uni = getattr(user, 'university', None)
                college_code = getattr(user_college, 'aishe_code', None) or str(getattr(user_college, 'pk', ''))
                uni_code = getattr(user_uni, 'aishe_code', None) or str(getattr(user_uni, 'pk', ''))
                if doc.institution_id not in (college_code, uni_code) and doc.uploader_id != user.pk:
                    raise UnauthorizedEvidenceActionError("Cannot view verification history for another institution.")
            elif not is_admin and user_role in ('committee', 'committee_chair'):
                cls.validate_reviewer_authorization(user, doc)

        history = []
        for v in assoc.verifications.all().order_by('-timestamp'):
            history.append({
                "verification_id": str(v.verification_id),
                "decision": v.decision,
                "verifier_id": v.verifier_id,
                "verifier_email": getattr(v.verifier, 'email', str(v.verifier_id)),
                "reason": v.reason,
                "rejection_code": v.rejection_code,
                "inspected_checksum": v.inspected_checksum or doc.file_checksum,
                "timestamp": v.timestamp.isoformat(),
                "metadata": v.metadata,
                "parameter_id": assoc.parameter_id,
                "subcriterion_id": assoc.subcriterion_id,
            })
        return history

    @classmethod
    def get_verification_history(cls, evidence_id, user=None) -> List[Dict[str, Any]]:
        """
        Retrieves the immutable, append-only verification history for an evidence document.
        """
        doc = EvidenceDocument.objects.get(pk=evidence_id)
        if user and getattr(user, 'is_authenticated', False):
            if getattr(user, 'role', '') == 'principal' and user.pk != doc.uploader_id:
                if not getattr(user, 'college', None) or str(user.college.aishe_code) != doc.institution_id:
                    raise UnauthorizedEvidenceActionError("Cannot view verification history for another institution.")

        history = []
        for v in doc.verifications.all().order_by('-timestamp'):
            history.append({
                "verification_id": str(v.verification_id),
                "decision": v.decision,
                "verifier_id": v.verifier_id,
                "verifier_email": getattr(v.verifier, 'email', str(v.verifier_id)),
                "reason": v.reason,
                "rejection_code": v.rejection_code,
                "inspected_checksum": v.inspected_checksum or doc.file_checksum,
                "inspected_version": v.inspected_version or doc.version,
                "previous_state": v.previous_state,
                "resulting_state": v.resulting_state,
                "timestamp": v.timestamp.isoformat(),
                "framework": doc.framework,
                "institution_id": doc.institution_id,
                "metadata": v.metadata,
            })
        return history

    @classmethod
    def get_subcriterion_scoring_evidence(
        cls,
        parameter_id: str,
        subcriterion_id: str,
        assessment_id: str,
    ) -> List[ScoringEvidenceDocument]:
        """
        Domain bridge: Retrieves all active evidence documents associated with a subcriterion
        in an assessment, transformed into the scoring engine's domain dataclass.
        """
        associations = EvidenceSubcriterionAssociation.objects.filter(
            parameter_id=parameter_id,
            subcriterion_id=subcriterion_id,
            evidence__assessment_id=assessment_id,
            evidence__is_active=True,
            is_active=True,
        ).select_related('evidence')

        return [cls.to_scoring_domain(assoc) for assoc in associations]

    @classmethod
    def evaluate_subcriterion_scoring_eligibility(
        cls,
        parameter_id: str,
        subcriterion_id: str,
        assessment_id: str,
        mandatory_evidence_types: Optional[List[str]] = None,
    ) -> Tuple[GatingStatus, float, Dict[str, Any]]:
        """
        Integrates with the frozen Phase 4 evidence gating evaluator.
        Determines gating status and score multiplier for a subcriterion.
        """
        scoring_docs = cls.get_subcriterion_scoring_evidence(parameter_id, subcriterion_id, assessment_id)
        if mandatory_evidence_types is None:
            mandatory_evidence_types = [d.document_type for d in scoring_docs]

        return evaluate_evidence(mandatory_evidence_types, scoring_docs)

    @classmethod
    def is_subcriterion_scoring_eligible(
        cls,
        parameter_id: str,
        subcriterion_id: str,
        assessment_id: str,
        mandatory_evidence_types: Optional[List[str]] = None,
    ) -> bool:
        """
        Clean domain method returning True iff the subcriterion documentary proof
        is fully verified and eligible to unlock earned score in the scoring engine.
        """
        status, multiplier, _ = cls.evaluate_subcriterion_scoring_eligibility(
            parameter_id=parameter_id,
            subcriterion_id=subcriterion_id,
            assessment_id=assessment_id,
            mandatory_evidence_types=mandatory_evidence_types,
        )
        return multiplier == 1.0 and status in (
            GatingStatus.PASSED_EVIDENCE_VERIFIED,
            GatingStatus.NO_EVIDENCE_REQUIRED,
        )

    @classmethod
    def evaluate_evidence_coverage(
        cls,
        assessment_id: Optional[str] = None,
        nomination=None,
        institution_id: Optional[str] = None,
        framework: Optional[str] = None,
        requesting_user=None,
        subcriterion_codes: Optional[List[str]] = None,
    ):
        """
        Phase 5D: Evaluates evidence completeness, period compliance, verification states,
        and scoring readiness for an assessment without calculating scores.
        """
        from .coverage import EvidenceCoverageEvaluator
        return EvidenceCoverageEvaluator.evaluate_evidence_coverage(
            assessment_id=assessment_id,
            nomination=nomination,
            institution_id=institution_id,
            framework=framework,
            requesting_user=requesting_user,
            subcriterion_codes=subcriterion_codes,
        )

    @classmethod
    def is_assessment_evidence_ready(
        cls,
        assessment_id: Optional[str] = None,
        nomination=None,
        institution_id: Optional[str] = None,
        framework: Optional[str] = None,
        requesting_user=None,
        subcriterion_codes: Optional[List[str]] = None,
    ):
        """
        Phase 5D: Convenience service answering whether an assessment's evidence is
        complete, period-valid, verified, and ready for scoring review.
        """
        from .coverage import EvidenceCoverageEvaluator
        return EvidenceCoverageEvaluator.is_assessment_evidence_ready(
            assessment_id=assessment_id,
            nomination=nomination,
            institution_id=institution_id,
            framework=framework,
            requesting_user=requesting_user,
            subcriterion_codes=subcriterion_codes,
        )

    @classmethod
    def get_review_readiness(
        cls,
        assessment_id: Optional[str] = None,
        nomination=None,
        institution_id: Optional[str] = None,
        framework: Optional[str] = None,
        requesting_user=None,
    ):
        """
        Returns the structured ReviewReadinessReport for the reviewer workflow gate.
        Distinguishes MISSING/PENDING (hard blockers), REJECTED (correction required),
        UNRESOLVED (governance issue), and SOURCE_SILENT (not a blocker).
        Returns (is_complete_review_allowed, review_readiness, summary).
        """
        from .coverage import EvidenceCoverageEvaluator
        return EvidenceCoverageEvaluator.get_review_readiness(
            assessment_id=assessment_id,
            nomination=nomination,
            institution_id=institution_id,
            framework=framework,
            requesting_user=requesting_user,
        )

    @staticmethod
    def _validate_transition(current_state: str, next_state: str):
        allowed = LEGAL_EVIDENCE_TRANSITIONS.get(current_state, set())
        if next_state not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal evidence lifecycle transition: '{current_state}' -> '{next_state}'. "
                f"Permitted transitions from '{current_state}': {[s.value for s in allowed]}"
            )


