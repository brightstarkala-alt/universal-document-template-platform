"""
Preview Renderer response schema — Module 9.

`TemplatePreviewResponse` wraps `TemplateArtifact` (Module 8) completely
unchanged — `artifact` is byte-for-byte what Module 8 persisted, never
modified here. Asset URLs are a sibling map, never baked into the artifact
itself, because a signed URL expires and a stored template must not
contain anything that does; resolving them is deliberately a presentation-
layer concern this module owns, per Module 8's own documented boundary
("resolving `asset_id` to a fetchable URL... a later rendering module").
"""

from pydantic import BaseModel

from app.schemas.template import TemplateArtifact


class TemplatePreviewResponse(BaseModel):
    artifact: TemplateArtifact
    asset_urls: dict[str, str]
