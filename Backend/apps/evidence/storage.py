"""
NEP Excellence Awards 2026 - Evidence Storage Abstraction
Provides pluggable, secure storage backends for immutable evidence objects.
"""
from abc import ABC, abstractmethod
import os
import shutil
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.utils.module_loading import import_string

from .exceptions import EvidenceDomainError


class StorageError(EvidenceDomainError):
    """Raised when an operation against the evidence storage layer fails."""
    pass


class StorageSecurityError(StorageError):
    """Raised when an unauthorized path traversal or storage escape is detected."""
    pass


class BaseEvidenceStorage(ABC):
    """
    Abstract interface for evidence storage.
    Decouples evidence persistence from local filesystem vs cloud object storage.
    """

    @abstractmethod
    def save(self, storage_key: str, content: bytes, mime_type: str = "application/octet-stream") -> str:
        """Save file bytes under storage_key and return confirmed storage key."""
        pass

    @abstractmethod
    def retrieve(self, storage_key: str) -> bytes:
        """Retrieve raw file bytes for given storage_key."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if an object exists at storage_key."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete object at storage_key (used for rollback/cleanup)."""
        pass

    @abstractmethod
    def quarantine(self, storage_key: str, reason: str) -> str:
        """Isolate a compromised or rejected object into a quarantine location."""
        pass


class FileSystemEvidenceStorage(BaseEvidenceStorage):
    """
    Local filesystem storage backend for evidence vault.
    Enforces path confinement within the configured vault directory.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            configured_vault = getattr(settings, 'EVIDENCE_STORAGE_VAULT', None)
            if configured_vault:
                self.base_dir = Path(configured_vault)
            else:
                self.base_dir = Path(settings.MEDIA_ROOT) / 'evidence_vault'
        else:
            self.base_dir = Path(base_dir)

        self.quarantine_dir = self.base_dir / 'quarantine'
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, storage_key: str, allow_quarantine: bool = False) -> Path:
        """
        Safely resolve a storage key ensuring it stays strictly within the vault.
        Prevents directory traversal and escaping the vault root.
        """
        clean_key = storage_key.strip().lstrip('/\\')
        target_path = (self.base_dir / clean_key).resolve()

        base_resolved = self.base_dir.resolve()
        try:
            target_path.relative_to(base_resolved)
        except ValueError:
            raise StorageSecurityError(
                f"Storage path traversal detected: key '{storage_key}' resolves outside vault '{base_resolved}'"
            )

        return target_path

    def save(self, storage_key: str, content: bytes, mime_type: str = "application/octet-stream") -> str:
        target_path = self._resolve_safe_path(storage_key)
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            # Write to a temporary file first then atomic rename
            temp_path = target_path.with_suffix(target_path.suffix + '.tmp')
            with open(temp_path, 'wb') as f:
                f.write(content)
            temp_path.replace(target_path)
            return storage_key
        except Exception as e:
            if 'temp_path' in locals() and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise StorageError(f"Failed to save evidence object to storage: {str(e)}") from e

    def retrieve(self, storage_key: str) -> bytes:
        target_path = self._resolve_safe_path(storage_key)
        if not target_path.is_file():
            raise StorageError(f"Evidence object does not exist at key: {storage_key}")
        try:
            with open(target_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise StorageError(f"Failed to read evidence object from storage: {str(e)}") from e

    def exists(self, storage_key: str) -> bool:
        try:
            target_path = self._resolve_safe_path(storage_key)
            return target_path.is_file()
        except StorageSecurityError:
            return False

    def delete(self, storage_key: str) -> bool:
        target_path = self._resolve_safe_path(storage_key)
        if target_path.is_file():
            try:
                target_path.unlink()
                return True
            except Exception as e:
                raise StorageError(f"Failed to delete evidence object: {str(e)}") from e
        return False

    def quarantine(self, storage_key: str, reason: str) -> str:
        target_path = self._resolve_safe_path(storage_key)
        if not target_path.is_file():
            raise StorageError(f"Evidence object to quarantine does not exist: {storage_key}")

        rel_key = Path(storage_key.strip().lstrip('/\\'))
        quarantine_target = (self.quarantine_dir / rel_key).resolve()
        quarantine_target.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(target_path), str(quarantine_target))
            # Save companion metadata with quarantine reason
            meta_path = quarantine_target.with_suffix(quarantine_target.suffix + '.meta')
            with open(meta_path, 'w', encoding='utf-8') as f:
                f.write(f"Reason: {reason}\nOriginalKey: {storage_key}\n")
            
            quarantine_key = str(quarantine_target.relative_to(self.base_dir.resolve())).replace('\\', '/')
            return quarantine_key
        except Exception as e:
            raise StorageError(f"Failed to quarantine evidence object: {str(e)}") from e


def generate_storage_key(assessment_id: str, framework: str, document_id: str, file_checksum: str, safe_ext: str) -> str:
    """
    Generate a server-controlled, collision-free, hierarchical storage key.
    Format: evidence/{framework}/{assessment_id}/{checksum_prefix}/{checksum}_{document_id}.{safe_ext}
    """
    clean_framework = framework.strip().upper()
    clean_assessment = assessment_id.strip()
    clean_checksum = file_checksum.strip().lower()
    prefix = clean_checksum[:2] if len(clean_checksum) >= 2 else "xx"
    ext = safe_ext.strip().lstrip('.').lower()
    return f"evidence/{clean_framework}/{clean_assessment}/{prefix}/{clean_checksum}_{document_id}.{ext}"


def get_evidence_storage() -> BaseEvidenceStorage:
    """
    Factory function loading configured storage backend.
    """
    backend_path = getattr(
        settings,
        'EVIDENCE_STORAGE_BACKEND',
        'apps.evidence.storage.FileSystemEvidenceStorage'
    )
    if isinstance(backend_path, str):
        storage_cls = import_string(backend_path)
        return storage_cls()
    return backend_path
