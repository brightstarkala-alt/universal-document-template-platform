from datetime import UTC, datetime

from app.schemas.template import (
    TemplateArtifact,
    TemplateManifest,
    TemplateManifestAsset,
    TemplateManifestField,
    TemplateManifestMetadata,
)
from app.services.document_renderer import (
    build_default_asset_map,
    build_default_value_map,
    render_html,
)


def test_replaces_a_single_field_value_by_field_id() -> None:
    html = '<p><span data-field-id="f1" data-machine-key="invoice_number">INV-1001</span></p>'

    result = render_html(html, {"f1": "INV-9999"}, {})

    assert result == '<p><span data-field-id="f1" data-machine-key="invoice_number">INV-9999</span></p>'


def test_never_touches_surrounding_text_outside_the_marker() -> None:
    html = (
        '<p>Invoice: <span data-field-id="f1" data-machine-key="invoice_number">'
        "INV-1001</span> (paid)</p>"
    )

    result = render_html(html, {"f1": "INV-9999"}, {})

    assert result == (
        '<p>Invoice: <span data-field-id="f1" data-machine-key="invoice_number">'
        "INV-9999</span> (paid)</p>"
    )


def test_replaces_multiple_fields_independently() -> None:
    html = (
        '<span data-field-id="f1" data-machine-key="invoice_number">INV-1001</span>'
        '<span data-field-id="f2" data-machine-key="total">100.00</span>'
    )

    result = render_html(html, {"f1": "INV-9999", "f2": "250.50"}, {})

    assert result == (
        '<span data-field-id="f1" data-machine-key="invoice_number">INV-9999</span>'
        '<span data-field-id="f2" data-machine-key="total">250.50</span>'
    )


def test_field_marker_left_unchanged_when_field_id_missing_from_value_map() -> None:
    html = '<span data-field-id="f1" data-machine-key="invoice_number">INV-1001</span>'

    result = render_html(html, {}, {})

    assert result == html


def test_never_uses_machine_key_for_lookup() -> None:
    html = '<span data-field-id="f1" data-machine-key="invoice_number">INV-1001</span>'

    # A value keyed by machine_key (not field_id) must not match.
    result = render_html(html, {"invoice_number": "INV-9999"}, {})

    assert result == html


def test_escapes_replacement_value() -> None:
    html = '<span data-field-id="f1" data-machine-key="note">old</span>'

    result = render_html(html, {"f1": "<script>alert(1)</script>"}, {})

    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_injects_src_when_asset_is_present() -> None:
    html = '<img data-asset-id="asset-1" alt="" width="50" height="30">'

    result = render_html(html, {}, {"asset-1": "https://signed.example/a.png"})

    assert result == (
        '<img src="https://signed.example/a.png" data-asset-id="asset-1" alt="" '
        'width="50" height="30">'
    )


def test_image_tag_left_unchanged_when_asset_missing_from_asset_map() -> None:
    html = '<img data-asset-id="asset-1" alt="" width="50" height="30">'

    result = render_html(html, {}, {})

    assert result == html


def test_replaces_multiple_assets_independently() -> None:
    html = (
        '<img data-asset-id="asset-1" alt="" width="1" height="1">'
        '<img data-asset-id="asset-2" alt="" width="2" height="2">'
    )

    result = render_html(
        html,
        {},
        {
            "asset-1": "https://signed.example/a.png",
            "asset-2": "data:image/png;base64,QQ==",
        },
    )

    assert result == (
        '<img src="https://signed.example/a.png" data-asset-id="asset-1" alt="" width="1" height="1">'
        '<img src="data:image/png;base64,QQ==" data-asset-id="asset-2" alt="" width="2" height="2">'
    )


def test_field_and_asset_substitution_compose_in_one_call() -> None:
    html = (
        '<span data-field-id="f1" data-machine-key="invoice_number">INV-1001</span>'
        '<img data-asset-id="asset-1" alt="" width="1" height="1">'
    )

    result = render_html(html, {"f1": "INV-9999"}, {"asset-1": "https://signed.example/a.png"})

    assert result == (
        '<span data-field-id="f1" data-machine-key="invoice_number">INV-9999</span>'
        '<img src="https://signed.example/a.png" data-asset-id="asset-1" alt="" width="1" height="1">'
    )


def _artifact() -> TemplateArtifact:
    return TemplateArtifact(
        schema_version="1.0",
        generator_version="1.0",
        source_ai_extraction_id="extraction-1",
        source_parsed_document_id="parsed-1",
        version=1,
        generated_at=datetime.now(UTC),
        html=(
            '<section class="page" data-unit-index="0">'
            '<p><span data-field-id="f1" data-machine-key="invoice_number">INV-1001</span></p>'
            '<p><span data-field-id="f2" data-machine-key="total">100.00</span></p>'
            '<img data-asset-id="asset-1" alt="" width="50" height="30">'
            "</section>"
        ),
        css="body { margin: 0; }",
        manifest=TemplateManifest(
            pages=[],
            fields=[
                TemplateManifestField(
                    field_id="f1",
                    machine_key="invoice_number",
                    display_label="Invoice Number",
                    type="identifier",
                    sample_value="INV-1001",
                    confidence=0.9,
                    confidence_tier="high",
                    unit_index=0,
                ),
                TemplateManifestField(
                    field_id="f2",
                    machine_key="total",
                    display_label="Total",
                    type="currency",
                    sample_value="100.00",
                    confidence=0.8,
                    confidence_tier="high",
                    unit_index=0,
                ),
            ],
            repeating_sections=[],
            assets=[
                TemplateManifestAsset(
                    asset_id="asset-1",
                    original_path="company-1/file-1/parsed/assets/asset-1.png",
                    mime_type="image/png",
                    width=50,
                    height=30,
                    role="content_image",
                )
            ],
            metadata=TemplateManifestMetadata(
                source_format="pdf",
                page_count=1,
                sheet_count=0,
                field_count=2,
                section_count=0,
                asset_count=1,
                unmapped_field_count=0,
                unmapped_section_count=0,
                duration_ms=1.0,
            ),
        ),
    )


def test_build_default_value_map_uses_manifest_sample_values() -> None:
    artifact = _artifact()

    value_map = build_default_value_map(artifact.manifest)

    assert value_map == {"f1": "INV-1001", "f2": "100.00"}


def test_build_default_asset_map_is_empty() -> None:
    artifact = _artifact()

    assert build_default_asset_map(artifact.manifest) == {}


def test_render_html_is_identity_with_default_maps() -> None:
    """Regression guard: rendering an artifact's own HTML through the
    identity value map (sample values) and the empty default asset map
    must reproduce the artifact's stored HTML byte-for-byte. This is the
    property Module 9's Preview refactor depends on to keep its response
    unchanged after routing through this shared renderer."""
    artifact = _artifact()

    result = render_html(
        artifact.html,
        build_default_value_map(artifact.manifest),
        build_default_asset_map(artifact.manifest),
    )

    assert result == artifact.html
