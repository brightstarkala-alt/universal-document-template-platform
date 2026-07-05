from app.services.parsers.docx_parser import DocxParser
from app.tests.parser_fixtures import make_docx_bytes


def test_parses_docx_into_single_unit_with_text_table_and_image() -> None:
    result = DocxParser().parse(make_docx_bytes(with_image=True))

    assert len(result.units) == 1
    unit = result.units[0]
    assert unit.unit_type == "page"
    assert unit.status == "ok"
    assert unit.confidence == 1.0

    block_types = [block.type for block in unit.blocks]
    assert "text" in block_types
    assert "cell_grid" in block_types
    assert "image" in block_types

    assert result.stats.text_block_count == 1
    assert result.stats.cell_grid_count == 1
    assert result.stats.cell_count == 4
    assert result.stats.image_count == 1

    assert len(result.assets) == 1
    assert result.assets[0].mime_type == "image/png"
    assert len(result.assets[0].content) > 0

    image_block = next(block for block in unit.blocks if block.type == "image")
    assert image_block.asset_type == "extracted_image"
    assert image_block.asset_id == result.assets[0].asset_id
    assert image_block.asset_path == ""  # backfilled by parser_service, not the adapter


def test_parses_docx_without_embedded_image() -> None:
    result = DocxParser().parse(make_docx_bytes(with_image=False))

    assert result.stats.image_count == 0
    assert result.assets == []
