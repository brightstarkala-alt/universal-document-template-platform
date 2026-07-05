"""
Parser Engine endpoints (Module 6): trigger a parse and fetch the latest
parse result's metadata. Both are company-scoped via `get_current_company`.

`POST /files/{file_id}/parse` runs synchronously today, but its response
shape (a `parsed_documents` row with a `status` field) is exactly what a
future background-job-backed version would also return — only *when*
`status` reaches a terminal value would change, not the shape callers see.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_company
from app.schemas.company import CurrentCompany
from app.schemas.parsed_document import ParsedDocumentMetadata
from app.services import parser_service

router = APIRouter(prefix="/files", tags=["parsing"])


@router.post("/{file_id}/parse", response_model=ParsedDocumentMetadata)
async def parse_file(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> ParsedDocumentMetadata:
    return parser_service.parse_file(company_id=current_company.id, file_id=file_id)


@router.get("/{file_id}/parsed", response_model=ParsedDocumentMetadata)
async def read_latest_parsed_document(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> ParsedDocumentMetadata:
    return parser_service.get_latest_parsed_document(company_id=current_company.id, file_id=file_id)
