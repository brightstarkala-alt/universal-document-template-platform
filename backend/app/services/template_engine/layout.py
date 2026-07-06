"""
Reading-order reconstruction — Module 8, Stage A.

`Unit.blocks` order is not always visual reading order. Two concrete cases
from the actual Module 6 adapters:

- `pdf_parser.py` appends every text-line block first (sorted top-to-bottom),
  then appends every table afterward in a second loop — so a table that
  visually sits in the middle of a page still lands at the end of the
  array. PDF blocks carry genuine `x`/`y`, so re-sorting by position fixes
  this.
- `docx_parser.py` emits every paragraph/table block with
  `BoundingBox(x=0, y=0, width=0, height=0)` — DOCX has no native position
  data, so array order (already correct document order from the XML body)
  must be trusted as-is; sorting by a uniformly-zero position would be a
  no-op at best and must never be treated as meaningful.

This is why the choice below is conditional on whether *any* block in the
unit has a non-zero position, not on document format.
"""

from app.schemas.document_model import Unit


def reading_order(unit: Unit) -> list[int]:
    """Returns `unit.blocks` indices in reading order."""
    if not _has_meaningful_positions(unit):
        return list(range(len(unit.blocks)))
    return sorted(
        range(len(unit.blocks)),
        key=lambda i: (unit.blocks[i].bounding_box.y, unit.blocks[i].bounding_box.x),
    )


def _has_meaningful_positions(unit: Unit) -> bool:
    return any(block.bounding_box.x != 0 or block.bounding_box.y != 0 for block in unit.blocks)
