"""
NEP Excellence Awards 2026 - Evidence Domain Enums & Lifecycle Definitions
"""
from django.db import models


class EvidenceLifecycleState(models.TextChoices):
    """
    Evidence lifecycle states.
    Scoring engine strictly treats only EVIDENCE_VERIFIED as eligible to unlock earned marks.
    """
    EVIDENCE_PRESENT = "EVIDENCE_PRESENT", "Evidence Present / Uploaded"
    EVIDENCE_PENDING = "EVIDENCE_PENDING", "Pending Verification"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED", "Evidence Verified"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED", "Evidence Rejected"
    EVIDENCE_SUPERSEDED = "EVIDENCE_SUPERSEDED", "Evidence Superseded"
    EVIDENCE_WITHDRAWN = "EVIDENCE_WITHDRAWN", "Evidence Withdrawn"


class VerificationDecision(models.TextChoices):
    """
    Auditable verification decisions.
    """
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"
    PENDING = "PENDING", "Pending Review"


class AssociationVerificationDecision(models.TextChoices):
    """
    Association-level verification decisions for Step 4B.
    """
    PENDING = "PENDING", "Pending Review"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"



class EvidenceAuditAction(models.TextChoices):
    """
    Append-only evidence audit log actions.
    """
    UPLOADED = "UPLOADED", "Evidence Uploaded"
    SUBMITTED = "SUBMITTED", "Submitted For Verification"
    VERIFIED = "VERIFIED", "Verification Approved"
    REJECTED = "REJECTED", "Verification Rejected"
    SUPERSEDED = "SUPERSEDED", "Evidence Superseded"
    WITHDRAWN = "WITHDRAWN", "Evidence Withdrawn"
    ASSOCIATED = "ASSOCIATED", "Associated to Subcriterion"
    DISASSOCIATED = "DISASSOCIATED", "Disassociated from Subcriterion"
    METADATA_UPDATED = "METADATA_UPDATED", "Metadata Updated"
    ASSIGNED = "ASSIGNED", "Reviewer Assigned"
    UNASSIGNED = "UNASSIGNED", "Reviewer Unassigned"
    REASSIGNED = "REASSIGNED", "Reviewer Reassigned"


class RejectionReasonCode(models.TextChoices):
    """
    Structured, machine-readable rejection reasons for Phase 5C evidence verification.
    """
    ILLEGIBLE_DOCUMENT = "ILLEGIBLE_DOCUMENT", "Document is unreadable, corrupted, or blank"
    INCOMPLETE_DOCUMENTATION = "INCOMPLETE_DOCUMENTATION", "Required sections, annexures, or proof missing"
    OUT_OF_PERIOD = "OUT_OF_PERIOD", "Document date falls outside assessment window (2025-07-01 to 2026-06-30)"
    MISMATCHED_CRITERIA = "MISMATCHED_CRITERIA", "Document content does not support claimed parameter or subcriterion"
    UNAUTHORIZED_SIGNATORY = "UNAUTHORIZED_SIGNATORY", "Document lacks mandatory institutional signature, stamp, or seal"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH", "Document hash or version does not match inspected file"
    OTHER = "OTHER", "Other reason (requires specific explanatory text)"


class AssignmentStatus(models.TextChoices):
    """
    Status of an evidence review assignment.
    """
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    REVOKED = "REVOKED", "Revoked"
    REASSIGNED = "REASSIGNED", "Reassigned"


# Explicit state transition map
LEGAL_EVIDENCE_TRANSITIONS = {
    EvidenceLifecycleState.EVIDENCE_PRESENT: {
        EvidenceLifecycleState.EVIDENCE_PENDING,
        EvidenceLifecycleState.EVIDENCE_WITHDRAWN,
    },
    EvidenceLifecycleState.EVIDENCE_PENDING: {
        EvidenceLifecycleState.EVIDENCE_VERIFIED,
        EvidenceLifecycleState.EVIDENCE_REJECTED,
        EvidenceLifecycleState.EVIDENCE_WITHDRAWN,
    },
    EvidenceLifecycleState.EVIDENCE_VERIFIED: {
        EvidenceLifecycleState.EVIDENCE_SUPERSEDED,
        EvidenceLifecycleState.EVIDENCE_WITHDRAWN,
    },
    EvidenceLifecycleState.EVIDENCE_REJECTED: {
        EvidenceLifecycleState.EVIDENCE_SUPERSEDED,
        EvidenceLifecycleState.EVIDENCE_WITHDRAWN,
    },
    EvidenceLifecycleState.EVIDENCE_SUPERSEDED: set(),  # Terminal state
    EvidenceLifecycleState.EVIDENCE_WITHDRAWN: set(),   # Terminal state
}


class CoverageState(models.TextChoices):
    """
    Subcriterion-level evidence coverage state for Phase 5D & Step 4E.
    Distinguishes presence, review status, period validity, contract states, and scoring eligibility.
    """
    NO_EVIDENCE = "NO_EVIDENCE", "No Evidence Associated"
    EVIDENCE_PRESENT = "EVIDENCE_PRESENT", "Evidence Present / Unsubmitted"
    EVIDENCE_PENDING = "EVIDENCE_PENDING", "Evidence Pending Verification"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED", "Evidence Verified & Eligible"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED", "Evidence Rejected"
    EVIDENCE_INVALID_PERIOD = "EVIDENCE_INVALID_PERIOD", "Evidence Out of Assessment Period"
    SOURCE_SILENT = "SOURCE_SILENT", "Source Silent (No Documentary Requirement Specified)"
    UNRESOLVED = "UNRESOLVED", "Unresolved Missing Evidence Requirement"


# Semantic Aliases as mandated by Step 4E
CoverageState.COVERED = CoverageState.EVIDENCE_VERIFIED
CoverageState.MISSING = CoverageState.NO_EVIDENCE
CoverageState.PENDING = CoverageState.EVIDENCE_PENDING
CoverageState.REJECTED = CoverageState.EVIDENCE_REJECTED


class CoverageDeficiencyCode(models.TextChoices):
    """
    Machine-readable deficiency codes for implementation-level validation.
    """
    NO_ASSOCIATED_EVIDENCE = "NO_ASSOCIATED_EVIDENCE", "No evidence associated with subcriterion"
    VERIFICATION_PENDING = "VERIFICATION_PENDING", "Evidence is pending reviewer verification"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED", "Evidence was rejected by reviewer"
    PERIOD_DATA_MISSING = "PERIOD_DATA_MISSING", "Activity date is missing for period-sensitive subcriterion"
    OUTSIDE_ASSESSMENT_PERIOD = "OUTSIDE_ASSESSMENT_PERIOD", "Activity date falls outside assessment period (2025-07-01 to 2026-06-30)"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE", "Invalid activity date range (start date after end date)"
    FRAMEWORK_MISMATCH = "FRAMEWORK_MISMATCH", "Evidence framework does not match assessment framework"
    INVALID_ASSOCIATION = "INVALID_ASSOCIATION", "Association references inactive or invalid evidence"
    DUPLICATE_EVIDENCE_DETECTED = "DUPLICATE_EVIDENCE_DETECTED", "Evidence document is associated with multiple subcriteria"
    UNVERIFIED_EVIDENCE = "UNVERIFIED_EVIDENCE", "Evidence is present but not yet verified"
    QUARANTINED_EVIDENCE = "QUARANTINED_EVIDENCE", "Evidence uses quarantined/legacy coarse type"
    EVIDENCE_TYPE_MISMATCH = "EVIDENCE_TYPE_MISMATCH", "Evidence type does not satisfy subcriterion contract"
    INSTITUTION_MISMATCH = "INSTITUTION_MISMATCH", "Evidence belongs to a different institution"
    CONTRACT_SOURCE_SILENT = "CONTRACT_SOURCE_SILENT", "Subcriterion has no documentary requirement in authoritative source"
    CONTRACT_UNRESOLVED = "CONTRACT_UNRESOLVED", "Subcriterion evidence contract is unresolved in authoritative source"


