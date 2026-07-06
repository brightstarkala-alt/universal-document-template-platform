"""
Preview Renderer — Module 9.

Strictly read-only: fetches the latest (or a specific) `TemplateArtifact`
Module 8 already generated and never modifies it in Storage or the
database — the stored artifact is, and remains, immutable. What this
module returns to the caller is a *rendered copy* of that artifact: its
`html` is produced by `app/services/document_renderer.py::render_html`,
the same shared renderer PDF Generation (Module 10) uses, so there is
exactly one implementation of "turn a TemplateArtifact into concrete
HTML" anywhere in the codebase — never two independent ones.

Today's rendering inputs are both defaults, computed fresh on every
request and never persisted:
  * a `ValueMap` built from the manifest's own `sample_value`s
    (`document_renderer.build_default_value_map`) — every field renders
    with the same text it already had, so this is a no-op for field
    content.
  * an `AssetMap` built from freshly-signed Storage URLs (the same map
    returned as `asset_urls`) — so the response's `<img>` tags carry a
    real, working `src`, unlike the stored artifact's raw HTML, which
    never has one (asset resolution has always been deferred past
    Module 8; Module 9 is where it happens, now via the shared renderer
    instead of ad hoc string handling).

A future document-filling module supplies a different `ValueMap` (real
user-entered values instead of samples) to this exact same `render_html`
call — nothing in this module needs to change when that happens.

Every other interaction (marker detection, hover highlighting, ephemeral
in-preview value overrides, the field inspector) happens entirely
client-side against this response and is never sent back here.

Never regenerates a template, never persists anything a user does in a
preview, and never introduces coordinate (x/y) positioning.
"""

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.schemas.file import SignedUrlResponse
from app.schemas.preview import TemplatePreviewResponse
from app.schemas.rendering import AssetMap
from app.schemas.template import TemplateArtifact
from app.schemas.template_metadata import TemplateMetadata
from app.services import document_renderer, storage_service, template_engine_service

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
    asset_urls = _build_asset_urls(artifact)

    value_map = document_renderer.build_default_value_map(artifact.manifest)
    rendered_html = document_renderer.render_html(artifact.html, value_map, asset_urls)
    # `artifact` above is what was just read back from Storage, unmodified.
    # Only this in-memory copy — built for the response only — carries the
    # rendered html; nothing here is written back to Storage or the
    # `templates` table.
    rendered_artifact = artifact.model_copy(update={"html": rendered_html})

    return TemplatePreviewResponse(artifact=rendered_artifact, asset_urls=asset_urls)


def _build_asset_urls(artifact: TemplateArtifact) -> AssetMap:
    return {
        asset.asset_id: _sign_asset(asset.original_path).url for asset in artifact.manifest.assets
    }


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
