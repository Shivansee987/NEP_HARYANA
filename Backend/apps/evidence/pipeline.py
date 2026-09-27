"""
NEP Excellence Awards 2026 - Master Evidence Upload & Storage Pipeline
Enforces the mandatory intake sequence:
UPLOAD -> VALIDATE -> HASH -> STORE -> CREATE EVIDENCE RECORD -> ASSOCIATE -> SUBMIT / PENDING
Guarantees transaction safety and zero orphaned storage files.
"""
import hashlib
import uuid
from datetime import date
from typing import Any, Dict, Optional, Union

from django.db import transaction
from django.core.files.uploadedfile import UploadedFile

from .enums import (
    EvidenceAuditAction,
    EvidenceLifecycleState,
)
from .exceptions import (
    EvidenceDomainError,
    FrameworkMismatchError,
    UnauthorizedEvidenceActionError,
)
from .models import (
    EvidenceAuditLog,
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
)
from .storage import generate_storage_key, get_evidence_storage
from .validators import ContentValidator, FilenameValidator


class EvidenceUploadPipeline:
    """
    Server-authoritative pipeline managing the intake, validation, hashing,
    storage, and database persistence of documentary evidence.
    """

    @classmethod
    def process_upload(
        cls,
        uploader,
        assessment_id: str,
        framework: str,
        institution_type: str,
        institution_id: str,
        file_data: Union[bytes, UploadedFile],
        filename: Optional[str] = None,
        evidence_type: Optional[str] = None,
        document_date: Optional[date] = None,
        academic_year: Optional[str] = None,
        parameter_id: Optional[str] = None,
        subcriterion_id: Optional[str] = None,
        response_id: str = "",
        auto_submit: bool = False,
        nomination=None,
        metadata: Optional[Dict[str, Any]] = None,
        validate_taxonomy: bool = False,
    ) -> EvidenceDocument:
        """
        Executes the atomic upload intake pipeline.
        """
        # Step 1: Authorization
        if not uploader or not getattr(uploader, 'is_authenticated', False):
            raise UnauthorizedEvidenceActionError("Authenticated user is required to upload evidence.")

        uploader_role = getattr(uploader, 'role', '')
        if uploader_role == 'committee':
            raise UnauthorizedEvidenceActionError("Screening Committee members cannot upload institutional evidence.")

        # Step 2: Framework identity validation
        clean_framework = framework.strip().upper()
        if clean_framework not in ("UNIVERSITY_2026", "COLLEGE_2026"):
            raise FrameworkMismatchError(f"Invalid framework identifier: {framework}")

        # Parameter framework isolation pre-check
        if parameter_id:
            param_clean = parameter_id.strip().upper()
            if clean_framework == "UNIVERSITY_2026" and param_clean.startswith("C") and not param_clean.startswith("CR"):
                raise FrameworkMismatchError(
                    f"Framework isolation violation: Cannot associate College parameter '{parameter_id}' "
                    f"to University assessment '{assessment_id}'."
                )
            if clean_framework == "COLLEGE_2026" and param_clean.startswith("U"):
                raise FrameworkMismatchError(
                    f"Framework isolation violation: Cannot associate University parameter '{parameter_id}' "
                    f"to College assessment '{assessment_id}'."
                )

        # Step 2b: Taxonomy validation & deterministic derivation (DEF-01)
        from apps.evidence.taxonomy import derive_or_validate_evidence_type
        if validate_taxonomy:
            resolved_evidence_type = derive_or_validate_evidence_type(
                framework=clean_framework,
                evidence_type=evidence_type,
                parameter_id=parameter_id,
                subcriterion_id=subcriterion_id,
            )
        else:
            if not evidence_type and parameter_id:
                try:
                    resolved_evidence_type = derive_or_validate_evidence_type(
                        framework=clean_framework,
                        evidence_type=evidence_type,
                        parameter_id=parameter_id,
                        subcriterion_id=subcriterion_id,
                    )
                except Exception:
                    resolved_evidence_type = evidence_type or "EVID_GENERAL"
            else:
                resolved_evidence_type = evidence_type or "EVID_GENERAL"

        # Step 3: Extract bytes and filename
        if isinstance(file_data, bytes):
            content_bytes = file_data
            orig_filename = filename or "evidence.pdf"
        elif hasattr(file_data, 'read'):
            content_bytes = file_data.read()
            orig_filename = filename or getattr(file_data, 'name', 'evidence.pdf')
        else:
            raise EvidenceDomainError("Invalid file_data provided. Expected bytes or file-like object.")

        # Step 4: Validate Filename
        safe_filename, safe_ext = FilenameValidator.validate_and_sanitize(orig_filename)

        # Step 5: Validate Content & Magic Bytes
        detected_mime, file_size = ContentValidator.validate_content(content_bytes, safe_ext)

        # Step 6: Cryptographic SHA-256 Hashing
        file_checksum = hashlib.sha256(content_bytes).hexdigest()

        # Step 7: Storage Key Generation & Storage Persistence
        doc_uuid = uuid.uuid4()
        storage = get_evidence_storage()
        storage_key = generate_storage_key(
            assessment_id=assessment_id,
            framework=clean_framework,
            document_id=str(doc_uuid),
            file_checksum=file_checksum,
            safe_ext=safe_ext,
        )

        # Save to storage layer
        storage.save(storage_key, content_bytes, mime_type=detected_mime)

        # Step 8: Atomic Database Persistence with Rollback Cleanup
        try:
            with transaction.atomic():
                # Duplicate binary content check in same assessment
                existing_docs = EvidenceDocument.objects.filter(
                    assessment_id=assessment_id,
                    file_checksum=file_checksum,
                    is_active=True,
                )
                audit_metadata = dict(metadata or {})
                if existing_docs.exists():
                    first_dup = existing_docs.first()
                    audit_metadata['duplicate_checksum_detected'] = True
                    audit_metadata['duplicate_of_document_id'] = str(first_dup.document_id)

                initial_status = (
                    EvidenceLifecycleState.EVIDENCE_PENDING
                    if auto_submit
                    else EvidenceLifecycleState.EVIDENCE_PRESENT
                )

                doc = EvidenceDocument.objects.create(
                    document_id=doc_uuid,
                    assessment_id=assessment_id,
                    framework=clean_framework,
                    institution_type=institution_type,
                    institution_id=institution_id,
                    nomination=nomination,
                    original_filename=orig_filename,
                    file_path=storage_key,
                    mime_type=detected_mime,
                    file_size=file_size,
                    file_checksum=file_checksum,
                    uploader=uploader,
                    evidence_type=resolved_evidence_type,
                    document_date=document_date,
                    academic_year=academic_year,
                    status=initial_status,
                    version=1,
                    metadata=audit_metadata,
                    is_active=True,
                )

                # Record upload audit log
                EvidenceAuditLog.objects.create(
                    evidence=doc,
                    assessment_id=assessment_id,
                    actor=uploader,
                    action=EvidenceAuditAction.UPLOADED,
                    previous_state="",
                    new_state=EvidenceLifecycleState.EVIDENCE_PRESENT,
                    reason="Document uploaded via evidence intake pipeline",
                    payload={
                        "storage_key": storage_key,
                        "file_checksum": file_checksum,
                        "mime_type": detected_mime,
                        "file_size": file_size,
                        "original_filename": orig_filename,
                    },
                )

                # Optional: Associate to subcriterion
                if parameter_id and subcriterion_id:
                    EvidenceSubcriterionAssociation.objects.create(
                        evidence=doc,
                        parameter_id=parameter_id,
                        subcriterion_id=subcriterion_id,
                        response_id=response_id,
                        academic_year=academic_year or "",
                        subcriterion_evidence_type=resolved_evidence_type or "",
                        associated_by=uploader,
                        is_active=True,
                    )
                    EvidenceAuditLog.objects.create(
                        evidence=doc,
                        assessment_id=assessment_id,
                        actor=uploader,
                        action=EvidenceAuditAction.ASSOCIATED,
                        previous_state=initial_status,
                        new_state=initial_status,
                        reason=f"Associated to {parameter_id}:{subcriterion_id}",
                        payload={"parameter_id": parameter_id, "subcriterion_id": subcriterion_id},
                    )

                # If auto-submitted, record submission audit log
                if auto_submit:
                    EvidenceAuditLog.objects.create(
                        evidence=doc,
                        assessment_id=assessment_id,
                        actor=uploader,
                        action=EvidenceAuditAction.SUBMITTED,
                        previous_state=EvidenceLifecycleState.EVIDENCE_PRESENT,
                        new_state=EvidenceLifecycleState.EVIDENCE_PENDING,
                        reason="Auto-submitted for verification upon upload",
                    )

                return doc

        except Exception as db_err:
            # Transaction failed: clean up stored file so no orphaned file remains
            try:
                storage.delete(storage_key)
            except Exception:
                pass
            raise db_err
