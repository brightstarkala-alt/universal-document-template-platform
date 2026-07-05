import pytest

from app.core.exceptions import ValidationAppError
from app.services.file_validation_service import validate_file


def test_accepts_a_supported_pdf() -> None:
    extension = validate_file(
        filename="invoice.pdf", content_type="application/pdf", size_bytes=1024
    )
    assert extension == ".pdf"


def test_accepts_uppercase_extension() -> None:
    extension = validate_file(
        filename="Invoice.PDF", content_type="application/pdf", size_bytes=1024
    )
    assert extension == ".pdf"


def test_rejects_unsupported_extension() -> None:
    with pytest.raises(ValidationAppError) as exc_info:
        validate_file(filename="archive.zip", content_type="application/zip", size_bytes=1024)
    assert exc_info.value.code == "UNSUPPORTED_FILE_TYPE"


def test_rejects_content_type_mismatch() -> None:
    with pytest.raises(ValidationAppError) as exc_info:
        validate_file(filename="invoice.pdf", content_type="image/png", size_bytes=1024)
    assert exc_info.value.code == "CONTENT_TYPE_MISMATCH"


def test_rejects_empty_file() -> None:
    with pytest.raises(ValidationAppError) as exc_info:
        validate_file(filename="invoice.pdf", content_type="application/pdf", size_bytes=0)
    assert exc_info.value.code == "EMPTY_FILE"


def test_rejects_file_over_max_size() -> None:
    from app.core.config import settings

    with pytest.raises(ValidationAppError) as exc_info:
        validate_file(
            filename="invoice.pdf",
            content_type="application/pdf",
            size_bytes=settings.MAX_UPLOAD_FILE_SIZE_BYTES + 1,
        )
    assert exc_info.value.code == "FILE_TOO_LARGE"
