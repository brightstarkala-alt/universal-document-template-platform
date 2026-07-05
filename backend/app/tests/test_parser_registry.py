import pytest

from app.core.exceptions import ValidationAppError
from app.services.parser_registry import resolve_parser
from app.services.parsers.docx_parser import DocxParser
from app.services.parsers.image_parser import ImageParser
from app.services.parsers.pdf_parser import PdfParser
from app.services.parsers.xlsx_parser import XlsxParser


@pytest.mark.parametrize(
    ("extension", "expected_type"),
    [
        (".pdf", PdfParser),
        (".docx", DocxParser),
        (".xlsx", XlsxParser),
        (".png", ImageParser),
        (".jpg", ImageParser),
        (".jpeg", ImageParser),
        (".webp", ImageParser),
        (".PDF", PdfParser),
    ],
)
def test_resolve_parser_returns_expected_adapter(extension: str, expected_type: type) -> None:
    assert isinstance(resolve_parser(extension), expected_type)


def test_resolve_parser_raises_for_unsupported_extension() -> None:
    with pytest.raises(ValidationAppError) as exc_info:
        resolve_parser(".xls")
    assert exc_info.value.code == "UNSUPPORTED_FORMAT_FOR_PARSING"
