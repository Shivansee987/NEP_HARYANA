"""
NEP Excellence Awards 2026 - Evidence File & Content Safety Validators
Enforces deep server-side content inspection, magic byte verification, and filename security.
"""
import os
import re
from pathlib import Path
from typing import Tuple

from django.conf import settings

from .exceptions import EvidenceDomainError


class FileValidationError(EvidenceDomainError):
    """Base exception for file validation failures."""
    pass


class FileEmptyError(FileValidationError):
    """Raised when an uploaded file is 0 bytes."""
    pass


class FileTooLargeError(FileValidationError):
    """Raised when an uploaded file exceeds the configured maximum size."""
    pass


class UnsafeFilenameError(FileValidationError):
    """Raised when an uploaded filename contains path traversal, null bytes, or dangerous patterns."""
    pass


class UnsupportedFileTypeError(FileValidationError):
    """Raised when an uploaded file format or extension is not in the allowed catalogue."""
    pass


class MaliciousContentError(FileValidationError):
    """Raised when executable, script, or disguised attack payloads are detected."""
    pass


class MimeMismatchError(FileValidationError):
    """Raised when the detected file bytes do not match the expected extension or MIME type."""
    pass


# Disallowed executable / script extensions
DANGEROUS_EXTENSIONS = {
    'exe', 'dll', 'so', 'dylib', 'bin', 'com', 'scr', 'msi',
    'bat', 'cmd', 'ps1', 'sh', 'bash', 'csh', 'ksh', 'zsh',
    'php', 'phtml', 'php3', 'php4', 'php5', 'phps',
    'py', 'pyc', 'pyo', 'pyd', 'pl', 'pm', 'cgi', 'rb',
    'js', 'jsp', 'asp', 'aspx', 'cfm', 'vbs', 'vbe', 'wsf', 'wsh',
    'jar', 'war', 'ear', 'class', 'hta', 'reg',
}

# Allowed evidence extensions mapped to expected MIME types
ALLOWED_EVIDENCE_TYPES = {
    'pdf': 'application/pdf',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'webp': 'image/webp',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}


class FilenameValidator:
    """
    Validates and sanitizes evidence filenames.
    Prevents path traversal, drive injection, null-byte attacks, and double-extension tricks.
    """

    @classmethod
    def validate_and_sanitize(cls, filename: str) -> Tuple[str, str]:
        """
        Validates filename security and returns (sanitized_name, safe_extension).
        Raises UnsafeFilenameError or UnsupportedFileTypeError on violation.
        """
        if not filename or not filename.strip():
            raise UnsafeFilenameError("Filename cannot be empty.")

        raw_name = filename.strip()

        # 1. Null byte check
        if '\x00' in raw_name or '%00' in raw_name.lower():
            raise UnsafeFilenameError("Null byte injection detected in filename.")

        # 2. Control characters (ASCII < 32)
        if any(ord(c) < 32 for c in raw_name):
            raise UnsafeFilenameError("Control characters detected in filename.")

        # 3. Path traversal patterns
        if '..' in raw_name or '/' in raw_name or '\\' in raw_name:
            raise UnsafeFilenameError(f"Path traversal characters detected in filename: '{filename}'")

        # 4. Windows drive path patterns (e.g., C:, D:)
        if re.match(r'^[a-zA-Z]:', raw_name):
            raise UnsafeFilenameError("Windows drive letter path detected in filename.")

        # Extract name parts and extension
        parts = raw_name.split('.')
        if len(parts) < 2:
            raise UnsupportedFileTypeError("Filename must include an extension.")

        ext = parts[-1].lower().strip()
        base_stem = ".".join(parts[:-1])

        # 5. Check all internal parts for double-extension evasion
        # e.g., document.exe.pdf, report.php.png
        for part in parts[:-1]:
            clean_part = part.lower().strip()
            if clean_part in DANGEROUS_EXTENSIONS:
                raise MaliciousContentError(
                    f"Double-extension evasion detected with dangerous extension '.{clean_part}' in '{filename}'"
                )

        # 6. Validate primary extension
        if ext in DANGEROUS_EXTENSIONS:
            raise MaliciousContentError(f"Executable or script extension '.{ext}' is strictly prohibited.")

        if ext not in ALLOWED_EVIDENCE_TYPES:
            raise UnsupportedFileTypeError(
                f"File extension '.{ext}' is not supported. Allowed formats: {list(ALLOWED_EVIDENCE_TYPES.keys())}"
            )

        # 7. Sanitize filename for safe display
        safe_stem = re.sub(r'[^a-zA-Z0-9_\-.]', '_', base_stem)
        sanitized_filename = f"{safe_stem}.{ext}"

        return sanitized_filename, ext


class ContentValidator:
    """
    Inspects raw file bytes to verify size, detect true MIME types,
    and prevent executable / script payload uploads.
    """

    @classmethod
    def get_max_file_size(cls) -> int:
        return getattr(settings, 'MAX_EVIDENCE_FILE_SIZE', 25 * 1024 * 1024)

    @classmethod
    def validate_content(cls, content: bytes, claimed_ext: str) -> Tuple[str, int]:
        """
        Validates content bytes, detects authentic MIME type, and checks magic bytes.
        Returns (detected_mime_type, file_size_bytes).
        """
        if not content or len(content) == 0:
            raise FileEmptyError("Uploaded file is empty (0 bytes).")

        file_size = len(content)
        max_size = cls.get_max_file_size()
        if file_size > max_size:
            raise FileTooLargeError(
                f"File size ({file_size} bytes) exceeds maximum permitted limit ({max_size} bytes)."
            )

        # 1. Executable / Binary Signature Detection
        if content.startswith(b'MZ'):
            raise MaliciousContentError("Executable Windows PE binary payload detected (MZ magic header).")

        if content.startswith(b'\x7fELF'):
            raise MaliciousContentError("Executable Linux ELF binary payload detected.")

        if content.startswith(b'#!'):
            raise MaliciousContentError("Script shebang payload detected.")

        if content.startswith(b'\xca\xfe\xba\xbe'):
            raise MaliciousContentError("Compiled Java class payload detected.")

        # 2. Active Script Tag Inspection (first 4096 bytes)
        sample = content[:4096].lower()
        if b'<script' in sample or b'<?php' in sample or b'eval(' in sample:
            raise MaliciousContentError("Active script / HTML injection payload detected in file stream.")

        # 3. Genuine Magic Byte Identification
        clean_ext = claimed_ext.lower().strip()
        detected_mime = cls._detect_mime_from_magic_bytes(content)

        if not detected_mime:
            raise UnsupportedFileTypeError(
                "Unable to identify valid document format from file header magic bytes."
            )

        # 4. Cross-validate detected MIME with claimed extension
        expected_mime = ALLOWED_EVIDENCE_TYPES.get(clean_ext)
        if not expected_mime:
            raise UnsupportedFileTypeError(f"Extension '{clean_ext}' is not in allowed evidence catalogue.")

        # For OpenXML documents (docx, xlsx), both share PK zip magic bytes
        if expected_mime in (
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ):
            if detected_mime != 'application/zip':
                raise MimeMismatchError(
                    f"File with extension '.{clean_ext}' does not have valid Office OpenXML (ZIP) header."
                )
            # Use specific OpenXML MIME type
            detected_mime = expected_mime
        elif detected_mime != expected_mime:
            raise MimeMismatchError(
                f"MIME type mismatch: extension '.{clean_ext}' expects '{expected_mime}', "
                f"but file header identifies as '{detected_mime}'."
            )

        return detected_mime, file_size

    @staticmethod
    def _detect_mime_from_magic_bytes(content: bytes) -> str:
        """
        Determines MIME type by inspecting magic byte signatures.
        """
        if content.startswith(b'%PDF-'):
            return 'application/pdf'

        if content.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'

        if content.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'

        if len(content) >= 12 and content.startswith(b'RIFF') and content[8:12] == b'WEBP':
            return 'image/webp'

        if content.startswith(b'PK\x03\x04'):
            return 'application/zip'

        return ""
