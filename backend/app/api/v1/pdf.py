"""
PDF Generation endpoints (Module 10): trigger PDF generation, read PDF
metadata, and mint a signed download URL. All company-scoped via
`get_current_company`, mirroring Module 8/9's endpoints.

Every PDF is versioned (backend/sql/011_generated_pdfs.sql) — `POST`
mints a new version rather than overwriting a previous one, unless an
identical (source template, generator version) PDF is already cached
(see `pdf_generation_service.generate_pdf`). Pass `?force=true` to always
mint a new version.

Route order matters: the literal `/pdf/versions` and `/pdf/signed-url`
paths must be registered before the `/pdf/{version}` path, or FastAPI
would try to parse "versions"/"signed-url" as the integer `version` path
parameter.
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_company
from app.schemas.company import CurrentCompany
from app.schemas.file import SignedUrlResponse
from app.schemas.pdf_metadata import PDFMetadata
from app.services import pdf_generation_service

router = APIRouter(prefix="/files", tags=["pdf-generation"])


@router.post("/{file_id}/pdf", response_model=PDFMetadata)
async def generate_pdf(
    file_id: str,
    force: bool = Query(default=False),
    current_company: CurrentCompany = Depends(get_current_company),
) -> PDFMetadata:
    return pdf_generation_service.generate_pdf(
        company_id=current_company.id, file_id=file_id, force=force
    )


@router.get("/{file_id}/pdf", response_model=PDFMetadata)
async def read_latest_pdf(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> PDFMetadata:
    return pdf_generation_service.get_latest_pdf(company_id=current_company.id, file_id=file_id)


@router.get("/{file_id}/pdf/versions", response_model=list[PDFMetadata])
async def read_pdf_versions(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> list[PDFMetadata]:
    return pdf_generation_service.list_pdfs(company_id=current_company.id, file_id=file_id)


@router.get("/{file_id}/pdf/signed-url", response_model=SignedUrlResponse)
async def read_pdf_signed_url(
    file_id: str,
    version: int | None = Query(default=None),
    current_company: CurrentCompany = Depends(get_current_company),
) -> SignedUrlResponse:
    return pdf_generation_service.get_download_url(
        company_id=current_company.id, file_id=file_id, version=version
    )


@router.get("/{file_id}/pdf/{version}", response_model=PDFMetadata)
async def read_pdf_version(
    file_id: str,
    version: int,
    current_company: CurrentCompany = Depends(get_current_company),
) -> PDFMetadata:
    return pdf_generation_service.get_pdf_by_version(
        company_id=current_company.id, file_id=file_id, version=version
    )
