from app.schemas.document_model import (
    BoundingBox,
    Cell,
    CellGridBlock,
    Dimensions,
    TextBlock,
    TextRun,
    Unit,
    UniversalDocumentModel,
)
from app.services.ai_extraction.candidates import (
    build_candidates,
    classify_value,
    detect_field_candidates,
    detect_grid_candidate,
)

_BOX = BoundingBox(x=0, y=0, width=100, height=10)


def _text_unit(*texts: str, index: int = 0, confidence: float | None = 1.0) -> Unit:
    return Unit(
        index=index,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        confidence=confidence,
        blocks=[TextBlock(bounding_box=_BOX, runs=[TextRun(text=t) for t in texts])],
    )


def test_classify_value_email() -> None:
    assert classify_value("jane@example.com") == ("email", 0.95)


def test_classify_value_currency() -> None:
    field_type, confidence = classify_value("$1,250.00")
    assert field_type == "currency"
    assert confidence > 0.5


def test_classify_value_date() -> None:
    field_type, _ = classify_value("2026-07-06")
    assert field_type == "date"


def test_classify_value_percentage() -> None:
    field_type, _ = classify_value("42%")
    assert field_type == "percentage"


def test_classify_value_number() -> None:
    field_type, _ = classify_value("1234")
    assert field_type == "number"


def test_classify_value_long_text() -> None:
    field_type, _ = classify_value("x" * 121)
    assert field_type == "long_text"


def test_classify_value_empty_string() -> None:
    field_type, confidence = classify_value("   ")
    assert field_type == "text"
    assert confidence == 0.0


def test_detect_field_candidates_inline_label_value() -> None:
    unit = _text_unit("Invoice Number: INV-1001")

    candidates = detect_field_candidates(unit)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.label == "Invoice Number"
    assert candidate.value == "INV-1001"
    assert candidate.run_index == 0


def test_detect_field_candidates_label_then_separate_value_run() -> None:
    unit = _text_unit("Date:", "2026-07-06")

    candidates = detect_field_candidates(unit)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.label == "Date"
    assert candidate.value == "2026-07-06"
    assert candidate.run_index == 1
    assert candidate.provisional_type == "date"


def test_detect_field_candidates_standalone_typed_value_without_label() -> None:
    unit = _text_unit("jane@example.com")

    candidates = detect_field_candidates(unit)

    assert len(candidates) == 1
    assert candidates[0].label == ""
    assert candidates[0].provisional_type == "email"


def test_detect_field_candidates_ignores_plain_text_without_label_or_type() -> None:
    unit = _text_unit("Thank you for your business.")

    candidates = detect_field_candidates(unit)

    assert candidates == []


def test_detect_grid_candidate_bold_header_row_is_repeating() -> None:
    block = CellGridBlock(
        bounding_box=_BOX,
        row_count=3,
        col_count=2,
        cells=[
            Cell(row=0, col=0, text="Item", bold=True),
            Cell(row=0, col=1, text="Price", bold=True),
            Cell(row=1, col=0, text="Widget"),
            Cell(row=1, col=1, text="$10"),
            Cell(row=2, col=0, text="Gadget"),
            Cell(row=2, col=1, text="$20"),
        ],
    )

    candidate = detect_grid_candidate(0, 0, block)

    assert candidate.header_row_indices == [0]
    assert candidate.is_repeating is True
    assert candidate.row_count == 3


def test_detect_grid_candidate_single_data_row_is_not_repeating() -> None:
    block = CellGridBlock(
        bounding_box=_BOX,
        row_count=2,
        col_count=2,
        cells=[
            Cell(row=0, col=0, text="Field", bold=True),
            Cell(row=0, col=1, text="Value", bold=True),
            Cell(row=1, col=0, text="Name"),
            Cell(row=1, col=1, text="Acme Inc"),
        ],
    )

    candidate = detect_grid_candidate(0, 0, block)

    assert candidate.is_repeating is False


def test_build_candidates_skips_error_units() -> None:
    ok_unit = _text_unit("Total: $100")
    error_unit = Unit(
        index=1,
        unit_type="page",
        dimensions=Dimensions(width=100, height=100),
        status="error",
        error="boom",
    )
    udm = UniversalDocumentModel(
        schema_version="1.0",
        source_file_id="file-1",
        source_checksum_sha256="deadbeef",
        source_format="pdf",
        parser={"name": "pdf_parser", "version": "1.0.0"},
        extracted_at="2026-01-01T00:00:00Z",
        stats={
            "unit_count": 2,
            "text_block_count": 1,
            "image_count": 0,
            "cell_grid_count": 0,
            "cell_count": 0,
            "character_count": 10,
            "duration_ms": 1.0,
        },
        units=[ok_unit, error_unit],
    )

    result = build_candidates(udm)

    assert 0 in result
    assert 1 not in result
