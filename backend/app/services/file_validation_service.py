"""
Validates a file against the platform's supported formats
(see CLAUDE.md -> Supported Formats) before it is written to storage.

Pure validation logic — no I/O — so future upload flows (and tests) can
call it cheaply and repeatedly.
"""

from pathlib import PurePosixPath

from app.core.config import settings
from app.core.exceptions import ValidationAppError

CONTENT_TYPE_BY_EXTENSION: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def validate_file(*, filename: str, content_type: str, size_bytes: int) -> str:
    """Validates type and size; returns the validated lowercase extension."""
    extension = PurePosixPath(filename).suffix.lower()

    if extension not in CONTENT_TYPE_BY_EXTENSION:
        raise ValidationAppError(
            f"Unsupported file type '{extension or filename}'.",
            code="UNSUPPORTED_FILE_TYPE",
        )

    expected_content_type = CONTENT_TYPE_BY_EXTENSION[extension]
    if content_type != expected_content_type:
        raise ValidationAppError(
            f"Content type '{content_type}' does not match the expected "
            f"'{expected_content_type}' for '{extension}' files.",
            code="CONTENT_TYPE_MISMATCH",
        )

    if size_bytes <= 0:
        raise ValidationAppError("File is empty.", code="EMPTY_FILE")

    if size_bytes > settings.MAX_UPLOAD_FILE_SIZE_BYTES:
        raise ValidationAppError(
            f"File exceeds the maximum allowed size of "
            f"{settings.MAX_UPLOAD_FILE_SIZE_BYTES} bytes.",
            code="FILE_TOO_LARGE",
        )

    return extension
