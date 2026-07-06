import base64
from unittest.mock import patch

from app.schemas.template import TemplateManifest, TemplateManifestAsset, TemplateManifestMetadata
from app.services.pdf_generation import asset_inliner


def _manifest(assets: list[TemplateManifestAsset]) -> TemplateManifest:
    return TemplateManifest(
        pages=[],
        fields=[],
        repeating_sections=[],
        assets=assets,
        metadata=TemplateManifestMetadata(
            source_format="pdf",
            page_count=1,
            sheet_count=0,
            field_count=0,
            section_count=0,
            asset_count=len(assets),
            unmapped_field_count=0,
            unmapped_section_count=0,
            duration_ms=1.0,
        ),
    )


def _asset(asset_id: str, path: str, mime_type: str = "image/png") -> TemplateManifestAsset:
    return TemplateManifestAsset(
        asset_id=asset_id,
        original_path=path,
        mime_type=mime_type,
        width=10,
        height=10,
        role="content_image",
    )


def test_build_asset_map_encodes_downloaded_bytes_as_base64_data_uri() -> None:
    manifest = _manifest([_asset("asset-1", "company-1/file-1/parsed/assets/asset-1.png")])

    with patch(
        "app.services.pdf_generation.asset_inliner.storage_service.download_object",
        return_value=b"fake-image-bytes",
    ) as mock_download:
        asset_map = asset_inliner.build_asset_map(manifest)

    mock_download.assert_called_once_with(path="company-1/file-1/parsed/assets/asset-1.png")
    expected = f"data:image/png;base64,{base64.b64encode(b'fake-image-bytes').decode('ascii')}"
    assert asset_map == {"asset-1": expected}


def test_build_asset_map_handles_multiple_assets() -> None:
    manifest = _manifest(
        [
            _asset("asset-1", "path/a.png", "image/png"),
            _asset("asset-2", "path/b.jpg", "image/jpeg"),
        ]
    )

    with patch(
        "app.services.pdf_generation.asset_inliner.storage_service.download_object",
        side_effect=[b"aaa", b"bbb"],
    ):
        asset_map = asset_inliner.build_asset_map(manifest)

    assert set(asset_map.keys()) == {"asset-1", "asset-2"}
    assert asset_map["asset-1"].startswith("data:image/png;base64,")
    assert asset_map["asset-2"].startswith("data:image/jpeg;base64,")


def test_build_asset_map_skips_asset_that_fails_to_download() -> None:
    manifest = _manifest(
        [
            _asset("asset-1", "path/a.png"),
            _asset("asset-2", "path/missing.png"),
        ]
    )

    with patch(
        "app.services.pdf_generation.asset_inliner.storage_service.download_object",
        side_effect=[b"aaa", RuntimeError("object not found")],
    ):
        asset_map = asset_inliner.build_asset_map(manifest)

    assert "asset-1" in asset_map
    assert "asset-2" not in asset_map


def test_build_asset_map_returns_empty_for_no_assets() -> None:
    manifest = _manifest([])

    assert asset_inliner.build_asset_map(manifest) == {}
