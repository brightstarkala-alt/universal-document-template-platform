"""
Preview Renderer — Module 9.

Strictly read-only and renderer-only: fetches the latest (or a specific)
`TemplateArtifact` Module 8 already generated and returns it completely
unchanged, alongside freshly-minted signed URLs for its assets. This is
the only new capability Module 9 adds server-side — every other
interaction (marker detection, hover highlighting, live value overrides,
the field inspector) happens entirely client-side against this response
and is never sent back here.

Never regenerates a template, never modifies a `TemplateArtifact`, never
persists anything a user does in a preview, and never introduces
coordinate (x/y) positioning — it has no rendering logic of its own beyond
resolving asset references, which Module 8's own design explicitly
deferred to "a later module" (see app/schemas/template.py).
"""

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.schemas.file import SignedUrlResponse
from app.schemas.preview import TemplatePreviewResponse
from app.schemas.template import TemplateArtifact
from app.schemas.template_metadata import TemplateMetadata
from app.services import storage_service, template_engine_service

_ACCEPTABLE_TEMPLATE_STATUSES = {"completed", "completed_with_errors"}


def get_latest_preview(*, company_id: str, file_id: str) -> TemplatePreviewResponse:
    metadata = template_engine_service.get_latest_template(company_id=company_id, file_id=file_id)
    return _build_preview_response(metadata)


def get_preview_by_version(
    *, company_id: str, file_id: str, version: int
) -> TemplatePreviewResponse:
    metadata = template_engine_service.get_template_by_version(
        company_id=company_id, file_id=file_id, version=version
    )
    return _build_preview_response(metadata)


def refresh_asset_url(
    *, company_id: str, file_id: str, asset_id: str, version: int | None = None
) -> SignedUrlResponse:
    """Mints a fresh signed URL for one asset — called by the frontend when
    an `<img>` fails to load because its previous URL expired, so the
    preview can recover without a full reload."""
    metadata = (
        template_engine_service.get_template_by_version(
            company_id=company_id, file_id=file_id, version=version
        )
        if version is not None
        else template_engine_service.get_latest_template(company_id=company_id, file_id=file_id)
    )
    artifact = _load_artifact(metadata)
    asset = next((a for a in artifact.manifest.assets if a.asset_id == asset_id), None)
    if asset is None:
        raise NotFoundError(f"Asset '{asset_id}' was not found in this template.")
    return _sign_asset(asset.original_path)


def _build_preview_response(metadata: TemplateMetadata) -> TemplatePreviewResponse:
    artifact = _load_artifact(metadata)
    asset_urls = {
        asset.asset_id: _sign_asset(asset.original_path).url for asset in artifact.manifest.assets
    }
    return TemplatePreviewResponse(artifact=artifact, asset_urls=asset_urls)


def _load_artifact(metadata: TemplateMetadata) -> TemplateArtifact:
    if metadata.status not in _ACCEPTABLE_TEMPLATE_STATUSES or not metadata.storage_path:
        raise ValidationAppError(
            "This file's template has not finished generating yet.", code="TEMPLATE_NOT_READY"
        )
    return TemplateArtifact.model_validate_json(
        storage_service.download_object(path=metadata.storage_path)
    )


def _sign_asset(original_path: str) -> SignedUrlResponse:
    expires_in = settings.SIGNED_URL_EXPIRES_IN_SECONDS
    url = storage_service.create_signed_url(path=original_path, expires_in=expires_in)
    return SignedUrlResponse(url=url, expires_in=expires_in)
