"""
Shared document renderer — the single source of truth for turning a
`TemplateArtifact`'s stored HTML (Module 8) into concrete, displayable
markup, for any consumer. Preview (Module 9) and PDF Generation
(Module 10) both call `render_html` instead of each maintaining their own
value/asset substitution logic.

Completely transport-agnostic and pure: this module never fetches an
asset, never reads Storage, never calls Supabase, and never imports
WeasyPrint. It performs exactly two deterministic substitutions against
the stable, internally-controlled marker shapes `html_builder.py`
(Module 8) always emits:

  * `<span data-field-id="ID" ...>TEXT</span>` — TEXT is replaced by
    `values[ID]`, looked up by the immutable `field_id` only. `machine_key`
    is editable and not a stable binding, so it is never used for lookup.
  * `<img data-asset-id="ID" ...>` — a `src="..."` attribute is injected
    from `assets[ID]`.

A field or asset absent from its map is left completely unchanged, not
blanked — a partial map degrades to "unfilled fields keep showing their
sample/placeholder text" rather than losing content. This is also what
makes `render_html` a provable no-op when handed the identity maps built
by `build_default_value_map`/`build_default_asset_map` (see
`test_document_renderer.py`'s regression test), which is the property
Preview's refactor depends on to keep its output unchanged.

Callers decide where `ValueMap`/`AssetMap` come from — today both default
to a template's own manifest (see the two `build_default_*` helpers
below); a future document-filling module builds a `ValueMap` from real
user input instead and passes it to this exact same function unchanged.
"""

import re
from html import escape

from app.schemas.rendering import AssetMap, ValueMap
from app.schemas.template import TemplateManifest

_FIELD_SPAN_RE = re.compile(r'(<span data-field-id="([^"]+)"[^>]*>)(.*?)(</span>)', re.DOTALL)
_IMG_TAG_RE = re.compile(r'<img\b([^>]*?data-asset-id="([^"]+)"[^>]*)>')


def render_html(html: str, values: ValueMap, assets: AssetMap) -> str:
    html = _substitute_field_values(html, values)
    return _substitute_asset_sources(html, assets)


def build_default_value_map(manifest: TemplateManifest) -> ValueMap:
    """Every field's value defaults to its own `sample_value` — the literal
    text already sitting inside its marker. This makes `render_html` a
    no-op for today's callers; a future ValueMap built from real
    user-entered values is a drop-in replacement, not a renderer change."""
    return {field.field_id: field.sample_value for field in manifest.fields}


def build_default_asset_map(manifest: TemplateManifest) -> AssetMap:
    """No-op default: nothing is resolved, so every `<img>` is left exactly
    as Module 8 emitted it (no `src`). Real callers (Preview's signed
    URLs, PDF generation's inlined data URIs) build their own AssetMap and
    pass that instead — the unused `manifest` parameter keeps this
    function's signature symmetric with `build_default_value_map`."""
    return {}


def _substitute_field_values(html: str, values: ValueMap) -> str:
    def replace(match: re.Match[str]) -> str:
        opening_tag = match.group(1)
        field_id = match.group(2)
        closing_tag = match.group(4)
        value = values.get(field_id)
        if value is None:
            return match.group(0)
        return f"{opening_tag}{escape(value)}{closing_tag}"

    return _FIELD_SPAN_RE.sub(replace, html)


def _substitute_asset_sources(html: str, assets: AssetMap) -> str:
    def replace(match: re.Match[str]) -> str:
        attrs = match.group(1)
        asset_id = match.group(2)
        reference = assets.get(asset_id)
        if reference is None:
            return match.group(0)
        return f'<img src="{escape(reference, quote=True)}"{attrs}>'

    return _IMG_TAG_RE.sub(replace, html)
