from app.services.parsers.image_parser import ImageParser
from app.tests.parser_fixtures import make_png_bytes


def test_parses_image_into_single_unit_with_source_file_asset() -> None:
    result = ImageParser().parse(make_png_bytes(width=120, height=80))

    assert len(result.units) == 1
    unit = result.units[0]
    assert unit.unit_type == "page"
    assert unit.status == "ok"
    assert unit.confidence == 1.0
    assert unit.dimensions.width == 120
    assert unit.dimensions.height == 80

    assert len(unit.blocks) == 1
    block = unit.blocks[0]
    assert block.type == "image"
    assert block.asset_type == "source_file"
    assert block.asset_path == ""  # backfilled by parser_service, not the adapter
    assert block.width == 120
    assert block.height == 80

    assert result.stats.image_count == 1
    assert result.stats.text_block_count == 0
    assert result.assets == []
