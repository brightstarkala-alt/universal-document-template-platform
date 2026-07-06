"""
Template Engine endpoints (Module 8): trigger template generation and read
template metadata. Both are company-scoped via `get_current_company`.

Every template is versioned (backend/sql/010_templates.sql) — `POST` mints
a new version rather than overwriting a previous one, unless an identical
(source AI extraction, generator version) template is already cached (see
`template_engine_service.generate_template`). Pass `?force=true` to always
mint a new version.

Route order matters: the literal `/template/versions` path must be
registered before the `/template/{version}` path, or FastAPI would try to
parse "versions" as the integer `version` path parameter.
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_company
from app.schemas.company import CurrentCompany
from app.schemas.template_metadata import TemplateMetadata
from app.services import template_engine_service

router = APIRouter(prefix="/files", tags=["template-engine"])


@router.post("/{file_id}/template", response_model=TemplateMetadata)
async def generate_template(
    file_id: str,
    force: bool = Query(default=False),
    current_company: CurrentCompany = Depends(get_current_company),
) -> TemplateMetadata:
    return template_engine_service.generate_template(
        company_id=current_company.id, file_id=file_id, force=force
    )


@router.get("/{file_id}/template", response_model=TemplateMetadata)
async def read_latest_template(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> TemplateMetadata:
    return template_engine_service.get_latest_template(
        company_id=current_company.id, file_id=file_id
    )


@router.get("/{file_id}/template/versions", response_model=list[TemplateMetadata])
async def read_template_versions(
    file_id: str,
    current_company: CurrentCompany = Depends(get_current_company),
) -> list[TemplateMetadata]:
    return template_engine_service.list_templates(company_id=current_company.id, file_id=file_id)


@router.get("/{file_id}/template/{version}", response_model=TemplateMetadata)
async def read_template_version(
    file_id: str,
    version: int,
    current_company: CurrentCompany = Depends(get_current_company),
) -> TemplateMetadata:
    return template_engine_service.get_template_by_version(
        company_id=current_company.id, file_id=file_id, version=version
    )
