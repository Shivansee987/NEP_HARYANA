"""
NEP Excellence Awards 2026 - Evidence Domain Exceptions
"""


class EvidenceDomainError(Exception):
    """Base exception for evidence domain operations."""
    pass


class InvalidStateTransitionError(EvidenceDomainError):
    """Raised when an illegal lifecycle state transition is attempted."""
    pass


class UnauthorizedEvidenceActionError(EvidenceDomainError):
    """Raised when a user attempts an evidence action without appropriate role/authority."""
    pass


class EvidenceIntegrityError(EvidenceDomainError):
    """Raised when evidence checksum or file integrity check fails."""
    pass


class EvidenceTamperingDetectedError(EvidenceIntegrityError):
    """Raised when file hash or version mismatch indicates evidence tampering."""
    pass


class ImmutableRecordError(EvidenceDomainError):
    """Raised when modification of an append-only/immutable record or field is attempted."""
    pass


class FrameworkMismatchError(EvidenceDomainError):
    """Raised when evidence from one framework is illegitimately associated with another framework."""
    pass


class InvalidAssociationError(EvidenceDomainError):
    """Raised when an invalid subcriterion or parameter association is attempted."""
    pass


class ReviewerNotAuthorizedError(UnauthorizedEvidenceActionError):
    """Raised when a reviewer is not authorized for the requested framework or institution."""
    pass


class ReviewerConflictOfInterestError(UnauthorizedEvidenceActionError):
    """Raised when a reviewer has an institutional or self-verification conflict of interest."""
    pass


class ConcurrentVerificationConflictError(InvalidStateTransitionError):
    """Raised when concurrent reviewers attempt conflicting decisions on the same evidence."""
    pass


class MandatoryRejectionReasonError(EvidenceDomainError):
    """Raised when a rejection is attempted without a mandatory reason or valid reason code."""
    pass


class ReviewerAssignmentError(EvidenceDomainError):
    """Raised when an invalid or unauthorized reviewer assignment is attempted."""
    pass

