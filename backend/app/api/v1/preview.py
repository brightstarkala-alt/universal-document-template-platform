"""
Preview Renderer endpoints (Module 9): read-only access to a generated
template's artifact for rendering, plus on-demand signed-URL refresh for
its assets. Company-scoped via `get_current_company`. No endpoint here
writes anything — this module never regenerates a template, never edits
one, and never persists a preview interaction.

Route order matters: `/preview/assets/{asset_id}/signed-url` and
`/preview/{version}` have different segment counts so there's no ambiguity,
but the more specific `assets` path is still registered first for clarity.
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_company
from app.schemas.company import CurrentCompany
from app.schemas.file import SignedUrlResponse
from app.schemas.preview import TemplatePreviewResponse
from app.services import preview_service

router = APIRouter(prefix="/files", tags=["preview"])


@router.get("/{file_id}/preview", response_model=TemplatePreviewResponse)
async def read_latest_preview(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> TemplatePreviewResponse:
    return preview_service.get_latest_preview(company_id=current_company.id, file_id=file_id)


@router.get(
    "/{file_id}/preview/assets/{asset_id}/signed-url",
    response_model=SignedUrlResponse,
)
async def refresh_preview_asset_url(
    file_id: str,
    asset_id: str,
    version: int | None = Query(default=None),
    current_company: CurrentCompany = Depends(get_current_company),
) -> SignedUrlResponse:
    return preview_service.refresh_asset_url(
        company_id=current_company.id, file_id=file_id, asset_id=asset_id, version=version
    )


@router.get("/{file_id}/preview/{version}", response_model=TemplatePreviewResponse)
async def read_preview_version(
    file_id: str,
    version: int,
    current_company: CurrentCompany = Depends(get_current_company),
) -> TemplatePreviewResponse:
    return preview_service.get_preview_by_version(
        company_id=current_company.id, file_id=file_id, version=version
    )
