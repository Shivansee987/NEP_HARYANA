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

    # Assessment states in which the institution may still add evidence
    EDITABLE_STATUSES = {
        "UNIVERSITY_2026": ("DRAFT", "RETURNED"),
        "COLLEGE_2026": ("DRAFT",),
    }

    @classmethod
    def _authorize_assessment_target(cls, uploader, assessment_id: str, framework: str, institution_id: str) -> str:
        """
        When the target assessment exists, the uploader must belong to its institution (administrators have
        read-only oversight and never upload an institution's evidence),
        the assessment must still be editable, and the evidence is filed under the assessment's own
        institution rather than a client-supplied one. Returns the institution id to record.
        """
        if framework == "UNIVERSITY_2026":
            from apps.university.models import UniversityAssessment
            assessment = UniversityAssessment.objects.select_related("university").filter(assessment_id=assessment_id).first()
            owner = assessment.university if assessment else None
            user_inst = getattr(uploader, "university", None)
        else:
            from apps.college.models import CollegeAssessment
            assessment = CollegeAssessment.objects.select_related("college").filter(assessment_id=assessment_id).first()
            owner = assessment.college if assessment else None
            user_inst = getattr(uploader, "college", None)

        if assessment is None:
            return institution_id

        if not (user_inst and user_inst.pk == owner.pk):
            raise UnauthorizedEvidenceActionError(
                f"User '{getattr(uploader, 'email', '')}' cannot upload evidence to another institution's assessment."
            )

        if assessment.status not in cls.EDITABLE_STATUSES[framework]:
            raise UnauthorizedEvidenceActionError(
                f"Assessment '{assessment_id}' is in '{assessment.status}' status; evidence can no longer be added."
            )

        return owner.aishe_code or str(owner.pk)

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
        if uploader_role in ('committee', 'committee_chair'):
            raise UnauthorizedEvidenceActionError("Screening Committee members cannot upload institutional evidence.")

        # Step 2: Framework identity validation
        clean_framework = framework.strip().upper()
        if clean_framework not in ("UNIVERSITY_2026", "COLLEGE_2026"):
            raise FrameworkMismatchError(f"Invalid framework identifier: {framework}")

        # Step 2a: Target assessment ownership & edit lock
        institution_id = cls._authorize_assessment_target(uploader, assessment_id, clean_framework, institution_id)

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

        # Step 3: Extract bytes or stream and filename
        is_stream = hasattr(file_data, 'chunks') or (hasattr(file_data, 'read') and not isinstance(file_data, bytes))
        if isinstance(file_data, bytes):
            content_bytes = file_data
            orig_filename = filename or "evidence.pdf"
            file_stream = None
        elif is_stream:
            orig_filename = filename or getattr(file_data, 'name', 'evidence.pdf')
            file_stream = file_data
            # Read first 8KB to inspect magic bytes and header structure without loading full file
            if hasattr(file_stream, 'seek'):
                file_stream.seek(0)
            initial_chunk = file_stream.read(8192)
            if hasattr(file_stream, 'seek'):
                file_stream.seek(0)
            content_bytes = initial_chunk
        else:
            raise EvidenceDomainError("Invalid file_data provided. Expected bytes or file-like object.")

        # Step 4: Validate Filename
        safe_filename, safe_ext = FilenameValidator.validate_and_sanitize(orig_filename)

        # Step 4b: Enforce subcriterion file format restrictions (e.g. PDF-only for U6.A, U6.B, U18.3)
        from apps.evidence.taxonomy import get_subcriterion_contract, SINGLE_SUBCRITERION_PARAMETERS
        target_contract = None
        if parameter_id and subcriterion_id:
            target_contract = get_subcriterion_contract(clean_framework, parameter_id, subcriterion_id)
        elif parameter_id:
            p_clean = parameter_id.strip().upper()
            if p_clean in SINGLE_SUBCRITERION_PARAMETERS:
                target_contract = get_subcriterion_contract(clean_framework, p_clean, SINGLE_SUBCRITERION_PARAMETERS[p_clean][0])

        is_pdf_only = (
            target_contract is not None
            and getattr(target_contract, "allowed_file_formats", None)
            and tuple(target_contract.allowed_file_formats) == ("pdf",)
        )

        if target_contract and getattr(target_contract, "allowed_file_formats", None):
            if safe_ext not in target_contract.allowed_file_formats:
                from apps.evidence.validators import UnsupportedFileTypeError
                raise UnsupportedFileTypeError(
                    f"Subcriterion {parameter_id}:{subcriterion_id or ''} requires evidence in {list(target_contract.allowed_file_formats)} format; "
                    f"file format '.{safe_ext}' is strictly not permitted."
                )

        # Step 5: Validate Content & Magic Bytes
        if is_stream:
            total_size = getattr(file_stream, 'size', None)
            detected_mime, _ = ContentValidator.validate_content(content_bytes, safe_ext)
            max_size = ContentValidator.get_max_file_size()
            if total_size and total_size > max_size:
                from apps.evidence.validators import FileTooLargeError
                raise FileTooLargeError(f"Uploaded file size ({total_size} bytes) exceeds maximum limit ({max_size} bytes).")
            file_size = total_size or len(content_bytes)
        else:
            detected_mime, file_size = ContentValidator.validate_content(content_bytes, safe_ext)

        # Step 5b: Perform deep PDF structure verification for PDF-only criteria
        if is_pdf_only:
            ContentValidator.validate_pdf_structure(content_bytes)

        # Step 6: Cryptographic SHA-256 Hashing (Chunked Streaming in 64KB buffers)
        sha256_hasher = hashlib.sha256()
        if is_stream:
            if hasattr(file_stream, 'seek'):
                file_stream.seek(0)
            if hasattr(file_stream, 'chunks'):
                for chunk in file_stream.chunks(65536):
                    sha256_hasher.update(chunk)
            else:
                while True:
                    chunk = file_stream.read(65536)
                    if not chunk:
                        break
                    sha256_hasher.update(chunk)
            if hasattr(file_stream, 'seek'):
                file_stream.seek(0)
            file_checksum = sha256_hasher.hexdigest()
        else:
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

        # Save to storage layer (via streaming or bytes)
        if is_stream:
            storage.save_stream(storage_key, file_stream, mime_type=detected_mime)
        else:
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
