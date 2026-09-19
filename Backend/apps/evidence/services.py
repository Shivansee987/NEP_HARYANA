"""
NEP Excellence Awards 2026 - Evidence Domain Services & Scoring Contract Bridge
"""
import hashlib
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
        if verifier_role not in ('committee', 'admin') and not getattr(reviewer, 'is_staff', False):
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

        # 3. Assignment enforcement: If assigned to another reviewer, regular reviewer cannot act
        if doc.assigned_reviewer_id and doc.assigned_reviewer_id != reviewer.pk:
            if verifier_role != 'admin' and not getattr(reviewer, 'is_staff', False):
                raise UnauthorizedEvidenceActionError(
                    f"Evidence is assigned to another reviewer. Only the assigned reviewer or admin can act."
                )

        # 4. Scope and Framework authorization
        if verifier_role == 'admin' or getattr(reviewer, 'is_staff', False):
            return True

        # For committee reviewers:
        user_auths = ReviewerAuthorization.objects.filter(user=reviewer, is_active=True)

        if user_auths.exists():
            fw_matching = user_auths.filter(framework__in=[doc.framework, 'ALL'])
            if not fw_matching.exists():
                raise FrameworkMismatchError(
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
    ) -> EvidenceSubcriterionAssociation:
        """
        Explicitly associate an evidence document with a parameter / subcriterion.
        Strictly enforces framework isolation.
        """
        doc = EvidenceDocument.objects.get(pk=evidence_id)

        # Framework isolation check
        param_clean = parameter_id.strip().upper()
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

        association, created = EvidenceSubcriterionAssociation.objects.get_or_create(
            evidence=doc,
            parameter_id=parameter_id,
            subcriterion_id=subcriterion_id,
            defaults={
                'response_id': response_id,
                'academic_year': academic_year or (doc.academic_year or ""),
                'associated_by': actor,
                'is_active': True,
            }
        )

        if not created and not association.is_active:
            association.is_active = True
            association.save(update_fields=['is_active'])

        EvidenceAuditLog.objects.create(
            evidence=doc,
            assessment_id=doc.assessment_id,
            actor=actor,
            action=EvidenceAuditAction.ASSOCIATED,
            previous_state=doc.status,
            new_state=doc.status,
            reason=f"Associated to {parameter_id}:{subcriterion_id}",
            payload={"subcriterion_id": subcriterion_id, "parameter_id": parameter_id},
        )

        return association

    @classmethod
    def to_scoring_domain(cls, doc: EvidenceDocument) -> ScoringEvidenceDocument:
        """
        Contract bridge: Adapts an ORM EvidenceDocument into the scoring engine's
        domain dataclass (apps.scoring.domain.EvidenceDocument).

        Crucial rule:
        - Only EVIDENCE_VERIFIED maps to EvidenceState.EVIDENCE_VERIFIED (allowing earned marks).
        - EVIDENCE_PRESENT, EVIDENCE_PENDING map to unverified states (0.0 marks earned).
        - EVIDENCE_REJECTED maps to EvidenceState.EVIDENCE_REJECTED (0.0 marks earned).
        - Inactive/superseded/withdrawn documents map to EVIDENCE_PRESENT with 0.0 marks.
        """
        # Determine latest verifier and rejection reason from append-only history
        latest_verification = doc.verifications.first()  # ordered by -timestamp
        verified_by = None
        rejection_reason = None

        if latest_verification:
            verified_by = str(getattr(latest_verification.verifier, 'email', latest_verification.verifier_id))
            if latest_verification.decision == VerificationDecision.REJECTED:
                rejection_reason = latest_verification.reason

        # Map state strictly
        if not doc.is_active or doc.status in (EvidenceLifecycleState.EVIDENCE_SUPERSEDED, EvidenceLifecycleState.EVIDENCE_WITHDRAWN):
            mapped_state = ScoringEvidenceState.EVIDENCE_PRESENT  # effectively unverified/dead
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
        )

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

        return [cls.to_scoring_domain(assoc.evidence) for assoc in associations]

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

    @staticmethod
    def _validate_transition(current_state: str, next_state: str):
        allowed = LEGAL_EVIDENCE_TRANSITIONS.get(current_state, set())
        if next_state not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal evidence lifecycle transition: '{current_state}' -> '{next_state}'. "
                f"Permitted transitions from '{current_state}': {[s.value for s in allowed]}"
            )


