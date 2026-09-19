"""
NEP Excellence Awards 2026 - Evidence Domain Models
Implements audit-grade, append-only verification and lifecycle tracking for evidence.
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .enums import (
    AssignmentStatus,
    EvidenceAuditAction,
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
)
from .exceptions import (
    EvidenceIntegrityError,
    ImmutableRecordError,
)


class EvidenceDocument(models.Model):
    """
    Core Evidence Document entity.
    Stores immutable metadata, cryptographic checksum, and lifecycle state.
    """
    document_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text=_("Stable, immutable unique identifier for the evidence document.")
    )
    assessment_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text=_("Authoritative assessment session ID to which this evidence belongs.")
    )
    framework = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Framework isolation identifier: UNIVERSITY_2026 or COLLEGE_2026.")
    )
    institution_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Institution type: UNIVERSITY or COLLEGE.")
    )
    institution_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text=_("Identifier of the institution (e.g., AISHE code or University ID).")
    )
    nomination = models.ForeignKey(
        'nominations.Nomination',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidence_documents',
        help_text=_("Optional link to existing Nomination record.")
    )
    original_filename = models.CharField(
        max_length=255,
        help_text=_("Original file name as provided during upload.")
    )
    file_path = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text=_("Storage reference/key to document media (not binary DB blob).")
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        default="application/octet-stream",
        help_text=_("MIME / Content type of the file.")
    )
    file_size = models.BigIntegerField(
        default=0,
        help_text=_("File size in bytes.")
    )
    file_checksum = models.CharField(
        max_length=64,
        db_index=True,
        help_text=_("SHA-256 cryptographic hex digest of document bytes.")
    )
    upload_timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("Timestamp when evidence was uploaded.")
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_evidences',
        help_text=_("Identity of the user who uploaded the evidence.")
    )
    evidence_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text=_("Controlled evidence type identifier (e.g. EVID_U4_IDP, EVID_GENERAL).")
    )
    document_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Actual date of the activity/record. MUST NOT substitute upload or HOI date.")
    )
    academic_year = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Optional academic year relevance (e.g. 2024-25, 2025-26).")
    )
    status = models.CharField(
        max_length=30,
        choices=EvidenceLifecycleState.choices,
        default=EvidenceLifecycleState.EVIDENCE_PRESENT,
        db_index=True,
        help_text=_("Current lifecycle state.")
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text=_("Version number of the document across supersessions.")
    )
    superseded_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='superseded_documents',
        help_text=_("Pointer to the newer evidence document that superseded this one.")
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Extensible audit metadata.")
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Flag indicating if this is the active document (superseded/withdrawn = False).")
    )
    assigned_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_evidence_documents',
        help_text=_("Screening committee reviewer assigned to verify this evidence.")
    )
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when evidence was assigned to reviewer.")
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidence_assignments_made',
        help_text=_("Administrator who assigned the reviewer.")
    )

    class Meta:
        verbose_name = _("Evidence Document")
        verbose_name_plural = _("Evidence Documents")
        indexes = [
            models.Index(fields=['assessment_id', 'framework']),
            models.Index(fields=['file_checksum']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['assigned_reviewer', 'status']),
        ]

    def __str__(self):
        return f"Evidence({self.document_id}, {self.original_filename}, {self.status})"

    def save(self, *args, **kwargs):
        """
        Enforce strict field immutability on existing records.
        """
        if self.pk is not None:
            orig = EvidenceDocument.objects.get(pk=self.pk)
            # Immutability protections
            if str(orig.document_id) != str(self.document_id):
                raise ImmutableRecordError("document_id is immutable and cannot be altered.")
            if orig.file_checksum != self.file_checksum:
                raise EvidenceIntegrityError("file_checksum is immutable. Replace with a new document instead.")
            if orig.uploader_id != self.uploader_id:
                raise ImmutableRecordError("uploader identity is immutable.")
            if orig.upload_timestamp != self.upload_timestamp:
                raise ImmutableRecordError("upload_timestamp is immutable.")
            if orig.framework != self.framework:
                raise ImmutableRecordError("framework is immutable once set.")
        super().save(*args, **kwargs)


class EvidenceVerification(models.Model):
    """
    Append-only verification record.
    Each verification or rejection creates a permanent, immutable historical record.
    """
    verification_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
    evidence = models.ForeignKey(
        EvidenceDocument,
        on_delete=models.CASCADE,
        related_name='verifications'
    )
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='evidence_verifications'
    )
    decision = models.CharField(
        max_length=20,
        choices=VerificationDecision.choices
    )
    reason = models.TextField(
        blank=True,
        default="",
        help_text=_("Mandatory justification for rejections; optional remarks for verifications.")
    )
    previous_state = models.CharField(
        max_length=30,
        choices=EvidenceLifecycleState.choices
    )
    resulting_state = models.CharField(
        max_length=30,
        choices=EvidenceLifecycleState.choices
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    inspected_checksum = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=_("Cryptographic SHA-256 hash inspected and verified by the reviewer.")
    )
    inspected_version = models.PositiveIntegerField(
        default=1,
        help_text=_("Document version inspected by the reviewer.")
    )
    rejection_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text=_("Machine-readable structured rejection code (RejectionReasonCode).")
    )
    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    class Meta:
        verbose_name = _("Evidence Verification")
        verbose_name_plural = _("Evidence Verifications")
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['evidence', 'timestamp']),
            models.Index(fields=['decision', 'verifier']),
        ]

    def __str__(self):
        return f"Verification({self.verification_id}, {self.decision}, by={self.verifier_id})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ImmutableRecordError("EvidenceVerification records are append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ImmutableRecordError("EvidenceVerification records are audit logs and cannot be deleted.")


class EvidenceSubcriterionAssociation(models.Model):
    """
    Explicit, traceable link between an EvidenceDocument and a Subcriterion.
    Allows evidence document reuse across permitted criteria while maintaining
    strict isolation and preventing automatic score duplication.
    """
    association_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
    evidence = models.ForeignKey(
        EvidenceDocument,
        on_delete=models.CASCADE,
        related_name='associations'
    )
    parameter_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Parameter ID, e.g. U4, C1")
    )
    subcriterion_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Subcriterion ID, e.g. U4.1, U4.A, C1.1")
    )
    response_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=_("Optional specific response identifier")
    )
    academic_year = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text=_("Academic year context of this association")
    )
    associated_at = models.DateTimeField(
        auto_now_add=True
    )
    associated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='evidence_associations'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = _("Evidence Subcriterion Association")
        verbose_name_plural = _("Evidence Subcriterion Associations")
        constraints = [
            models.UniqueConstraint(
                fields=['evidence', 'parameter_id', 'subcriterion_id'],
                name='unique_active_evidence_subcriterion_association'
            )
        ]
        indexes = [
            models.Index(fields=['parameter_id', 'subcriterion_id']),
        ]

    def __str__(self):
        return f"Association({self.evidence.document_id} -> {self.parameter_id}:{self.subcriterion_id})"


class EvidenceAuditLog(models.Model):
    """
    Append-only general audit trail for evidence lifecycle events.
    Completely separate from reviewer score adjustments.
    """
    log_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
    evidence = models.ForeignKey(
        EvidenceDocument,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    assessment_id = models.CharField(
        max_length=100,
        db_index=True
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidence_audit_events'
    )
    action = models.CharField(
        max_length=30,
        choices=EvidenceAuditAction.choices
    )
    previous_state = models.CharField(
        max_length=30,
        blank=True,
        default=""
    )
    new_state = models.CharField(
        max_length=30,
        blank=True,
        default=""
    )
    reason = models.TextField(
        blank=True,
        default=""
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    payload = models.JSONField(
        default=dict,
        blank=True
    )

    class Meta:
        verbose_name = _("Evidence Audit Log")
        verbose_name_plural = _("Evidence Audit Logs")
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['evidence', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f"AuditLog({self.action} on {self.evidence.document_id} at {self.timestamp})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ImmutableRecordError("EvidenceAuditLog records are append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ImmutableRecordError("EvidenceAuditLog records cannot be deleted.")


class ReviewerAuthorization(models.Model):
    """
    Domain-level authorization binding a reviewer to a framework and/or institution.
    Enforces segregation of duties and framework isolation.
    """
    authorization_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviewer_authorizations'
    )
    framework = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Authorized framework: UNIVERSITY_2026, COLLEGE_2026, or ALL.")
    )
    institution_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        help_text=_("Optional specific institution scope (e.g. AISHE code). If blank, applies to all institutions in framework.")
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Flag indicating if this authorization is currently active.")
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_authorizations'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        verbose_name = _("Reviewer Authorization")
        verbose_name_plural = _("Reviewer Authorizations")
        indexes = [
            models.Index(fields=['user', 'framework', 'is_active']),
            models.Index(fields=['framework', 'institution_id']),
        ]

    def __str__(self):
        inst_str = f" for {self.institution_id}" if self.institution_id else " (all institutions)"
        return f"ReviewerAuth({self.user.email} -> {self.framework}{inst_str}, active={self.is_active})"


class EvidenceReviewAssignment(models.Model):
    """
    Audit-grade, append-only history of evidence reviewer assignments.
    Prevents unauthorized assignment, cross-framework leakage, and tracks lifecycle.
    """
    assignment_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
    evidence = models.ForeignKey(
        EvidenceDocument,
        on_delete=models.CASCADE,
        related_name='review_assignments'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='evidence_review_assignments'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_assignments'
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ACTIVE,
        db_index=True
    )
    notes = models.TextField(
        blank=True,
        default=""
    )

    class Meta:
        verbose_name = _("Evidence Review Assignment")
        verbose_name_plural = _("Evidence Review Assignments")
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['evidence', 'status']),
            models.Index(fields=['reviewer', 'status']),
        ]

    def __str__(self):
        return f"Assignment({self.evidence.document_id} -> {self.reviewer.email}, status={self.status})"

