"""
Maps a file extension to the parser adapter that handles it — the only
place that knows the extension -> adapter mapping. `parser_service` calls
`resolve_parser`; nothing else needs to know these adapters exist.
"""

from app.core.exceptions import ValidationAppError
from app.services.parsers.base import Parser
from app.services.parsers.docx_parser import DocxParser
from app.services.parsers.image_parser import ImageParser
from app.services.parsers.pdf_parser import PdfParser
from app.services.parsers.xlsx_parser import XlsxParser

_PARSERS_BY_EXTENSION: dict[str, Parser] = {
    ".pdf": PdfParser(),
    ".docx": DocxParser(),
    ".xlsx": XlsxParser(),
    ".png": ImageParser(),
    ".jpg": ImageParser(),
    ".jpeg": ImageParser(),
    ".webp": ImageParser(),
}


def resolve_parser(extension: str) -> Parser:
    parser = _PARSERS_BY_EXTENSION.get(extension.lower())
    if parser is None:
        raise ValidationAppError(
            f"No parser is registered for '{extension}' files.",
            code="UNSUPPORTED_FORMAT_FOR_PARSING",
        )
    return parser
