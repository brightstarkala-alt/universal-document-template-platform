"""
OpenAI prompt architecture — Module 7, Stage C.

Structured Outputs (`response_format={"type": "json_object"}`, temperature 0)
plus explicit pydantic validation of the returned JSON — no free-text
parsing of the model's response. The system prompt encodes the anti-
hallucination contract (a field's `sample_value` must be text actually
present in what was sent) and generic *structural* few-shot examples
("label: value", "bold header row") rather than domain-specific ones
("this is what an invoice looks like"), so one prompt generalizes across
invoices, contracts, purchase orders, HR forms, shipping documents, legal
documents, and any future document type — no per-document-type prompt
variants, and no multi-provider abstraction (OpenAI only, per Module 7's
scope).
"""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.ai_extraction import FieldType
from app.schemas.document_model import CellGridBlock, TextBlock, Unit
from app.services.ai_extraction.candidates import ExtractionCandidates

PROMPT_VERSION = "2026-07-06.1"

SYSTEM_PROMPT = """You are a document field extraction engine. You are given \
a JSON object with a `units` array. Each entry is structural candidates and \
raw text/grid content extracted from ONE page or sheet of a business \
document (it could be an invoice, contract, purchase order, HR form, \
shipping document, legal document, or any other type — treat every \
document generically, never assume a specific document type). There may be \
one or several units in a single request; tag every field and table you \
return with the `unit_index` of the unit it came from.

Your job:
1. For each candidate field, confirm or correct its `display_label`, \
`machine_key` (snake_case), `type`, and `sample_value`. Set `accepted` to \
false if it is not actually a meaningful field (e.g. page furniture, a \
running header/footer, decorative text).
2. You may add fields the candidates missed, but ONLY if the exact text of \
`sample_value` appears verbatim in the `context_blocks` or `grids` you were \
given. Never invent a value that is not present in the provided text.
3. For each grid candidate, confirm the header row(s), decide whether it is \
a repeating line-item table (`is_repeating=true`) or a static label/value \
layout (`is_repeating=false`), and name each column (`display_label`, \
`machine_key`, `type`).
4. You may also report a repeating table you notice from `context_blocks` \
alone (stacked repeated text with no grid) — set its `block_index` to null \
and include a `row_count` (how many repeats you found). For a grid-based \
table (non-null `block_index`), omit `row_count` — it is computed directly \
from the grid, not from your response.
5. Report your own `confidence` (0 to 1) for every field and table.

Valid `type` values: text, long_text, number, currency, date, boolean, \
email, phone, identifier, address, signature_image, percentage.

Respond with ONLY a JSON object matching this shape:
{
  "fields": [
    {"unit_index": int, "block_index": int, "run_index": int|null,
     "display_label": str, "machine_key": str, "type": str,
     "sample_value": str, "confidence": float, "accepted": bool}
  ],
  "tables": [
    {"unit_index": int, "block_index": int|null,
     "header_row_indices": [int], "is_repeating": bool,
     "row_count": int|null,
     "columns": [{"display_label": str, "machine_key": str, "type": str}],
     "confidence": float}
  ]
}
"""


class LLMFieldResult(BaseModel):
    unit_index: int
    block_index: int
    run_index: int | None = None
    display_label: str
    machine_key: str
    type: FieldType
    sample_value: str
    confidence: float
    accepted: bool = True


class LLMTableColumnResult(BaseModel):
    display_label: str
    machine_key: str
    type: FieldType


class LLMTableResult(BaseModel):
    unit_index: int
    block_index: int | None = None
    header_row_indices: list[int] = Field(default_factory=list)
    is_repeating: bool
    row_count: int | None = None
    columns: list[LLMTableColumnResult]
    confidence: float


class LLMBatchResponse(BaseModel):
    fields: list[LLMFieldResult] = Field(default_factory=list)
    tables: list[LLMTableResult] = Field(default_factory=list)


def build_unit_payload(unit: Unit, candidates: ExtractionCandidates) -> dict[str, Any]:
    """Compact, token-conscious JSON payload for one unit: Stage-A
    candidates plus just enough raw context (block text, grid cells — no
    bounding boxes, no font metadata) for the model to confirm/rename/retype
    them or spot a rare miss."""
    context_blocks = [
        {"block_index": block_index, "text": " ".join(run.text for run in block.runs)}
        for block_index, block in enumerate(unit.blocks)
        if isinstance(block, TextBlock)
    ]
    grids = [
        {
            "block_index": block_index,
            "row_count": block.row_count,
            "col_count": block.col_count,
            "cells": [
                {"row": cell.row, "col": cell.col, "text": cell.text} for cell in block.cells
            ],
        }
        for block_index, block in enumerate(unit.blocks)
        if isinstance(block, CellGridBlock)
    ]
    return {
        "unit_index": unit.index,
        "unit_type": unit.unit_type,
        "field_candidates": [
            {
                "block_index": c.block_index,
                "run_index": c.run_index,
                "label": c.label,
                "value": c.value,
                "provisional_type": c.provisional_type,
            }
            for c in candidates.fields
        ],
        "grid_candidates": [
            {
                "block_index": g.block_index,
                "header_row_indices": g.header_row_indices,
                "is_repeating": g.is_repeating,
            }
            for g in candidates.grids
        ],
        "context_blocks": context_blocks,
        "grids": grids,
    }


def build_batch_payload(units: list[dict[str, Any]]) -> dict[str, Any]:
    """Wraps one or more `build_unit_payload` results into a single request
    payload — Stage B packs multiple small units into one OpenAI call up to
    a character budget instead of always issuing one call per unit."""
    return {"units": units}
