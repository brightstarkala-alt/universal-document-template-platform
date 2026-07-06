"""
Tier-1 deterministic candidate detection — Module 7, Stage A.

Pure, rule-based, no OpenAI call. Scans a `UniversalDocumentModel`'s blocks
for label/value pairs, typed values (dates, currency, emails, ...), and
grid/repeating structures. Produces *candidates*, not final fields — Stage C
(app/services/ai_extraction_service.py, via openai_client.py) confirms,
renames, retypes, or rejects each one. Candidates exist so the LLM prompt
can ask "confirm/retype this" instead of "find everything from scratch,"
which is both cheaper (fewer tokens, see prompts.py) and safer (bounds what
the model can invent, see scoring.py).
"""

import re
from dataclasses import dataclass, field

from app.schemas.ai_extraction import FieldType
from app.schemas.document_model import CellGridBlock, TextBlock, Unit, UniversalDocumentModel

_LABEL_PATTERN = re.compile(r"^(?P<label>[A-Za-z][\w\s./#-]{0,40}):\s*(?P<inline_value>.*)$")

_CURRENCY_PATTERN = re.compile(
    r"^[$€£¥]\s?-?[\d,]+(\.\d{1,2})?$|^-?[\d,]+(\.\d{1,2})?\s?(USD|EUR|GBP)$"
)
_DATE_PATTERN = re.compile(
    r"^\d{1,4}[/-]\d{1,2}[/-]\d{1,4}$"
    r"|^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}$",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
_PHONE_PATTERN = re.compile(r"^\+?[\d\s().-]{7,20}$")
_PERCENTAGE_PATTERN = re.compile(r"^-?\d+(\.\d+)?\s?%$")
_NUMBER_PATTERN = re.compile(r"^-?[\d,]+(\.\d+)?$")


@dataclass
class FieldCandidate:
    unit_index: int
    block_index: int
    run_index: int | None
    label: str
    value: str
    provisional_type: FieldType
    heuristic_confidence: float


@dataclass
class GridCandidate:
    unit_index: int
    block_index: int
    header_row_indices: list[int]
    is_repeating: bool
    row_count: int
    col_count: int
    heuristic_confidence: float


@dataclass
class ExtractionCandidates:
    fields: list[FieldCandidate] = field(default_factory=list)
    grids: list[GridCandidate] = field(default_factory=list)


def classify_value(text: str) -> tuple[FieldType, float]:
    """Regex-based provisional type classification.

    Returns `(type, confidence)` where confidence reflects how unambiguous
    the pattern match was, not correctness — correctness is reconciled with
    the LLM's own classification in app/services/ai_extraction/scoring.py.
    """
    stripped = text.strip()
    if not stripped:
        return "text", 0.0
    if _EMAIL_PATTERN.match(stripped):
        return "email", 0.95
    if _CURRENCY_PATTERN.match(stripped):
        return "currency", 0.9
    if _PERCENTAGE_PATTERN.match(stripped):
        return "percentage", 0.9
    if _DATE_PATTERN.match(stripped):
        return "date", 0.85
    digits_only = re.sub(r"\D", "", stripped)
    if _PHONE_PATTERN.match(stripped) and len(digits_only) >= 7:
        return "phone", 0.6
    if _NUMBER_PATTERN.match(stripped):
        return "number", 0.8
    if len(stripped) > 120:
        return "long_text", 0.5
    return "text", 0.3


def detect_field_candidates(unit: Unit) -> list[FieldCandidate]:
    candidates: list[FieldCandidate] = []
    for block_index, block in enumerate(unit.blocks):
        if not isinstance(block, TextBlock):
            continue
        candidates.extend(_candidates_from_text_block(unit.index, block_index, block))
    return candidates


def _candidates_from_text_block(
    unit_index: int, block_index: int, block: TextBlock
) -> list[FieldCandidate]:
    candidates: list[FieldCandidate] = []
    runs = block.runs
    consumed_run_indices: set[int] = set()

    for run_index, run in enumerate(runs):
        if run_index in consumed_run_indices:
            continue

        text = run.text.strip()
        if not text:
            continue

        match = _LABEL_PATTERN.match(text)
        if match:
            label = match.group("label").strip()
            inline_value = match.group("inline_value").strip()
            if inline_value:
                provisional_type, confidence = classify_value(inline_value)
                candidates.append(
                    FieldCandidate(
                        unit_index=unit_index,
                        block_index=block_index,
                        run_index=run_index,
                        label=label,
                        value=inline_value,
                        provisional_type=provisional_type,
                        heuristic_confidence=max(confidence, 0.6),
                    )
                )
            elif run_index + 1 < len(runs) and runs[run_index + 1].text.strip():
                next_text = runs[run_index + 1].text.strip()
                provisional_type, confidence = classify_value(next_text)
                candidates.append(
                    FieldCandidate(
                        unit_index=unit_index,
                        block_index=block_index,
                        run_index=run_index + 1,
                        label=label,
                        value=next_text,
                        provisional_type=provisional_type,
                        heuristic_confidence=max(confidence, 0.55),
                    )
                )
                # The next run was consumed as this label's value — it must
                # not also be surfaced separately as a standalone typed value.
                consumed_run_indices.add(run_index + 1)
            continue

        # No visible label — a standalone strongly-typed value (email, date,
        # currency, ...) is still worth surfacing; the LLM assigns a label
        # from surrounding context.
        provisional_type, confidence = classify_value(text)
        if provisional_type != "text" and confidence >= 0.6:
            candidates.append(
                FieldCandidate(
                    unit_index=unit_index,
                    block_index=block_index,
                    run_index=run_index,
                    label="",
                    value=text,
                    provisional_type=provisional_type,
                    heuristic_confidence=confidence * 0.7,
                )
            )
    return candidates


def detect_grid_candidate(unit_index: int, block_index: int, block: CellGridBlock) -> GridCandidate:
    header_rows = _detect_header_rows(block)
    data_row_count = block.row_count - len(header_rows)
    is_repeating = data_row_count > 1
    confidence = 0.85 if header_rows else 0.5
    return GridCandidate(
        unit_index=unit_index,
        block_index=block_index,
        header_row_indices=header_rows,
        is_repeating=is_repeating,
        row_count=block.row_count,
        col_count=block.col_count,
        heuristic_confidence=confidence,
    )


def _detect_header_rows(block: CellGridBlock) -> list[int]:
    if block.row_count == 0:
        return []
    row0_cells = [c for c in block.cells if c.row == 0]
    if not row0_cells:
        return []
    if all(c.bold for c in row0_cells):
        return [0]
    row0_font_sizes = {c.font_size for c in row0_cells if c.font_size is not None}
    other_font_sizes = {c.font_size for c in block.cells if c.row != 0 and c.font_size is not None}
    if row0_font_sizes and other_font_sizes and row0_font_sizes.isdisjoint(other_font_sizes):
        return [0]
    return [0] if block.row_count > 1 else []


def build_candidates(udm: UniversalDocumentModel) -> dict[int, ExtractionCandidates]:
    """One `ExtractionCandidates` per unit index — Stage B batches by unit,
    so candidates stay keyed that way rather than flattened."""
    by_unit: dict[int, ExtractionCandidates] = {}
    for unit in udm.units:
        if unit.status == "error":
            continue
        result = ExtractionCandidates(
            fields=detect_field_candidates(unit),
            grids=[
                detect_grid_candidate(unit.index, block_index, block)
                for block_index, block in enumerate(unit.blocks)
                if isinstance(block, CellGridBlock)
            ],
        )
        by_unit[unit.index] = result
    return by_unit
