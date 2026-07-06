"""
Asset inlining for PDF Generation — Module 10.

Builds an `AssetMap` (app/schemas/rendering.py) of base64 data URIs for
`document_renderer.render_html` to inject as `<img src="...">`.
WeasyPrint has no browser-side JS to resolve a signed URL against, and a
signed URL could expire mid-render on a large document, so each asset is
downloaded once via the existing `storage_service` and embedded directly
— self-contained, no network round trip during rendering.

This module never touches HTML — it only produces the map the shared
`document_renderer.render_html` consumes. There is no rendering or
substitution logic here; that stays the renderer's alone.
"""

import base64

from app.core.logging import get_logger
from app.schemas.rendering import AssetMap
from app.schemas.template import TemplateManifest
from app.services import storage_service

logger = get_logger(__name__)


def build_asset_map(manifest: TemplateManifest) -> AssetMap:
    """An asset that fails to download is skipped rather than raised —
    the caller (`pdf_generation_service`) treats a partial AssetMap as a
    `completed_with_errors` result (missing image, PDF still produced),
    never a hard failure, mirroring Module 8's own warnings philosophy."""
    asset_map: AssetMap = {}
    for asset in manifest.assets:
        try:
            content = storage_service.download_object(path=asset.original_path)
        except Exception as exc:  # noqa: BLE001 - a missing/unreadable asset must not fail the whole PDF
            logger.warning(
                "Failed to download asset for PDF inlining; image will be omitted",
                extra={"asset_id": asset.asset_id, "path": asset.original_path, "error": str(exc)},
            )
            continue
        encoded = base64.b64encode(content).decode("ascii")
        asset_map[asset.asset_id] = f"data:{asset.mime_type};base64,{encoded}"
    return asset_map
