"""
Rendering contracts shared between Preview (Module 9) and PDF Generation
(Module 10) — see `app/services/document_renderer.py`, the single renderer
both consume.

Plain dict aliases, not Pydantic models: neither map is ever serialized
over the wire as its own contract (Preview's `asset_urls` response field
and Module 10's persisted PDF bytes are the actual wire/storage
artifacts), so wrapping them in a model class would be pure ceremony.
"""

from typing import TypeAlias

ValueMap: TypeAlias = dict[str, str]
"""field_id -> the value that should be displayed in its marker."""

AssetMap: TypeAlias = dict[str, str]
"""asset_id -> a src-attribute-ready reference (signed URL, base64 data
URI, CDN URL, local path, ...). Opaque to the renderer by design — it is
only ever dropped into a `src="..."` attribute, never inspected or
interpreted."""
