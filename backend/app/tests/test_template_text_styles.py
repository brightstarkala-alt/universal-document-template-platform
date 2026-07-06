from app.schemas.document_model import (
    BoundingBox,
    Dimensions,
    TextBlock,
    TextRun,
    Unit,
    UniversalDocumentModel,
)
from app.services.template_engine.text_styles import (
    RunStyle,
    collect_style_classes,
    dominant_style,
    median_font_size,
    style_of,
)

_BOX = BoundingBox(x=0, y=0, width=100, height=10)


def _udm(units: list[Unit]) -> UniversalDocumentModel:
    return UniversalDocumentModel(
        schema_version="1.0",
        source_file_id="file-1",
        source_checksum_sha256="abc",
        source_format="pdf",
        parser={"name": "pdf_parser", "version": "1.0.0"},
        extracted_at="2026-01-01T00:00:00Z",
        stats={
            "unit_count": len(units),
            "text_block_count": 0,
            "image_count": 0,
            "cell_grid_count": 0,
            "cell_count": 0,
            "character_count": 0,
            "duration_ms": 1.0,
        },
        units=units,
    )


def test_style_of_extracts_all_style_fields() -> None:
    run = TextRun(
        text="x", font_family="Arial", font_size=12.0, bold=True, italic=False, color="#000"
    )
    assert style_of(run) == RunStyle(
        font_family="Arial", font_size=12.0, bold=True, italic=False, color="#000"
    )


def test_collect_style_classes_deduplicates_identical_styles() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            TextBlock(
                bounding_box=_BOX,
                runs=[
                    TextRun(text="a", font_size=12.0, bold=True),
                    TextRun(text="b", font_size=12.0, bold=True),
                    TextRun(text="c", font_size=18.0, bold=False),
                ],
            )
        ],
    )

    classes = collect_style_classes(_udm([unit]))

    assert len(classes) == 2
    assert len(set(classes.values())) == 2


def test_dominant_style_picks_the_most_common_style() -> None:
    block = TextBlock(
        bounding_box=_BOX,
        runs=[
            TextRun(text="a", font_size=12.0),
            TextRun(text="b", font_size=12.0),
            TextRun(text="c", font_size=18.0),
        ],
    )

    assert dominant_style(block) == RunStyle(
        font_family=None, font_size=12.0, bold=False, italic=False, color=None
    )


def test_dominant_style_returns_none_for_empty_block() -> None:
    block = TextBlock(bounding_box=_BOX, runs=[])
    assert dominant_style(block) is None


def test_median_font_size_computes_correctly_for_even_and_odd_counts() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[
            TextBlock(
                bounding_box=_BOX,
                runs=[TextRun(text="a", font_size=10.0), TextRun(text="b", font_size=20.0)],
            )
        ],
    )
    assert median_font_size(_udm([unit])) == 15.0


def test_median_font_size_returns_none_when_no_sizes_present() -> None:
    unit = Unit(
        index=0,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        blocks=[TextBlock(bounding_box=_BOX, runs=[TextRun(text="a")])],
    )
    assert median_font_size(_udm([unit])) is None
