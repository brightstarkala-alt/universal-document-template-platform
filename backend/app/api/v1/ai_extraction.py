"""
AI Field Extraction endpoints (Module 7): trigger an extraction and read
extraction results. Both are company-scoped via `get_current_company`.

Every extraction is versioned (backend/sql/009_ai_extractions.sql) — `POST`
mints a new version rather than overwriting a previous one, unless an
identical (file content, model, prompt version) extraction is already
cached (see `ai_extraction_service.extract_fields`). Pass `?force=true` to
always mint a new version.

Route order matters: the literal `/extracted/versions` path must be
registered before the `/extracted/{version}` path, or FastAPI would try to
parse "versions" as the integer `version` path parameter.
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_company
from app.schemas.ai_extraction_metadata import AIExtractionMetadata
from app.schemas.company import CurrentCompany
from app.services import ai_extraction_service

router = APIRouter(prefix="/files", tags=["ai-extraction"])


@router.post("/{file_id}/extract", response_model=AIExtractionMetadata)
async def extract_fields(
    file_id: str,
    force: bool = Query(default=False),
    current_company: CurrentCompany = Depends(get_current_company),
) -> AIExtractionMetadata:
    return ai_extraction_service.extract_fields(
        company_id=current_company.id, file_id=file_id, force=force
    )


@router.get("/{file_id}/extracted", response_model=AIExtractionMetadata)
async def read_latest_extraction(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> AIExtractionMetadata:
    return ai_extraction_service.get_latest_extraction(
        company_id=current_company.id, file_id=file_id
    )


@router.get("/{file_id}/extracted/versions", response_model=list[AIExtractionMetadata])
async def read_extraction_versions(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> list[AIExtractionMetadata]:
    return ai_extraction_service.list_extractions(company_id=current_company.id, file_id=file_id)


@router.get("/{file_id}/extracted/{version}", response_model=AIExtractionMetadata)
async def read_extraction_version(
    file_id: str,
    version: int,
    current_company: CurrentCompany = Depends(get_current_company),
) -> AIExtractionMetadata:
    return ai_extraction_service.get_extraction_by_version(
        company_id=current_company.id, file_id=file_id, version=version
    )
