"""
Semantic HTML emission with immutable-ID markers — Module 8, Stage C.

No templating syntax of any kind (no `{{ }}`, no `{% %}`) — markers are
plain HTML5 `data-*` attributes. `data-field-id` / `data-section-id` /
`data-asset-id` are the immutable, authoritative keys a renderer binds
against; `data-machine-key` / `data-section-key` are editable,
human-readable mirrors kept only for legibility when a raw template is
inspected — nothing should ever depend on them, and a rename operation is
free to leave them stale without touching the HTML.

A field's `sample_value` is substring-replaced within its source run's
text (never the whole run) because Module 7's inline "Label: Value" case
can put the label and the value in the *same* run — replacing the whole
run would destroy the label. This is safe because Module 7's
anti-hallucination check already guarantees `sample_value` is a literal
substring of the run's text.
"""

from dataclasses import dataclass, field
from html import escape

from app.schemas.ai_extraction import ExtractedField, ExtractedTable
from app.schemas.document_model import CellGridBlock, ImageBlock, TextBlock, TextRun, Unit
from app.services.template_engine.field_index import FieldIndex
from app.services.template_engine.layout import reading_order
from app.services.template_engine.text_styles import RunStyle, dominant_style, style_of

_HEADING_FONT_SIZE_RATIO = 1.4


@dataclass
class UnitRenderResult:
    html: str
    placed_field_ids: set[str] = field(default_factory=set)
    placed_section_ids: set[str] = field(default_factory=set)
    placed_asset_ids: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)


def render_unit(
    *,
    unit: Unit,
    field_index: FieldIndex,
    style_classes: dict[RunStyle, str],
    median_font_size: float | None,
    section_keys: dict[str, str],
) -> UnitRenderResult:
    result = UnitRenderResult(html="")
    parts: list[str] = [f'<section class="page" data-unit-index="{unit.index}">']

    for block_index in reading_order(unit):
        block = unit.blocks[block_index]
        if isinstance(block, TextBlock):
            parts.append(
                _render_text_block(
                    unit=unit,
                    block_index=block_index,
                    block=block,
                    field_index=field_index,
                    style_classes=style_classes,
                    median_font_size=median_font_size,
                    result=result,
                )
            )
        elif isinstance(block, CellGridBlock):
            parts.append(
                _render_grid_block(
                    unit=unit,
                    block_index=block_index,
                    block=block,
                    field_index=field_index,
                    section_keys=section_keys,
                    result=result,
                )
            )
        elif isinstance(block, ImageBlock):
            parts.append(_render_image_block(block=block, result=result))

    parts.append("</section>")
    result.html = "\n".join(parts)
    return result


def _render_text_block(
    *,
    unit: Unit,
    block_index: int,
    block: TextBlock,
    field_index: FieldIndex,
    style_classes: dict[RunStyle, str],
    median_font_size: float | None,
    result: UnitRenderResult,
) -> str:
    dominant = dominant_style(block)
    tag = _tag_for_block(dominant, median_font_size)

    raw_texts: list[str] = []
    rendered_parts: list[str] = []
    for run_index, run in enumerate(block.runs):
        raw_texts.append(run.text)
        rendered_parts.append(
            _render_run(
                unit_index=unit.index,
                block_index=block_index,
                run_index=run_index,
                run=run,
                dominant=dominant,
                style_classes=style_classes,
                field_index=field_index,
                result=result,
            )
        )

    return f"<{tag}>{_join_runs(rendered_parts, raw_texts)}</{tag}>"


def _join_runs(rendered_parts: list[str], raw_texts: list[str]) -> str:
    """PDF's `TextBlock.runs` are per-word (`pdf_parser.py` groups
    extracted words into lines) and need a space inserted between them;
    DOCX's runs are per-formatting-span (`python-docx`) and already
    contain their own whitespace. Nothing in the schema flags which
    convention applies, so a space is inserted between two runs only when
    neither side already ends/starts with whitespace — correct for both
    cases except a mid-word formatting change (rare; disclosed limitation,
    not specially handled)."""
    output: list[str] = []
    for index, part in enumerate(rendered_parts):
        if index > 0:
            previous_text = raw_texts[index - 1]
            current_text = raw_texts[index]
            if (
                previous_text
                and current_text
                and not previous_text[-1].isspace()
                and not current_text[0].isspace()
            ):
                output.append(" ")
        output.append(part)
    return "".join(output)


def _tag_for_block(dominant: RunStyle | None, median_font_size: float | None) -> str:
    if (
        dominant
        and dominant.font_size
        and median_font_size
        and median_font_size > 0
        and dominant.font_size >= median_font_size * _HEADING_FONT_SIZE_RATIO
    ):
        return "h2"
    return "p"


def _render_run(
    *,
    unit_index: int,
    block_index: int,
    run_index: int,
    run: TextRun,
    dominant: RunStyle | None,
    style_classes: dict[RunStyle, str],
    field_index: FieldIndex,
    result: UnitRenderResult,
) -> str:
    style = style_of(run)
    class_name = style_classes.get(style) if dominant is not None and style != dominant else None

    matched_field = field_index.by_run.get((unit_index, block_index, run_index))
    inner_html = _mark_field_in_text(run.text, matched_field, result)

    if class_name:
        return f'<span class="{class_name}">{inner_html}</span>'
    return inner_html


def _mark_field_in_text(
    text: str, matched_field: ExtractedField | None, result: UnitRenderResult
) -> str:
    if matched_field is None:
        return escape(text)

    position = text.find(matched_field.sample_value)
    if position == -1:
        # Should be unreachable: Module 7 already guarantees sample_value
        # is a substring of the source text. Defensive fallback only.
        result.warnings.append(
            f"field '{matched_field.machine_key}' ({matched_field.field_id}) sample_value "
            "not found in its source run at render time; rendered as plain text"
        )
        return escape(text)

    before = text[:position]
    matched_text = matched_field.sample_value
    after = text[position + len(matched_text) :]

    result.placed_field_ids.add(matched_field.field_id)

    marker = (
        f'<span data-field-id="{escape(matched_field.field_id, quote=True)}" '
        f'data-machine-key="{escape(matched_field.machine_key, quote=True)}">'
        f"{escape(matched_text)}</span>"
    )
    return f"{escape(before)}{marker}{escape(after)}"


def _render_grid_block(
    *,
    unit: Unit,
    block_index: int,
    block: CellGridBlock,
    field_index: FieldIndex,
    section_keys: dict[str, str],
    result: UnitRenderResult,
) -> str:
    table = field_index.tables_by_block.get((unit.index, block_index))
    if table is not None and table.is_repeating:
        rendered = _render_repeating_grid(
            table=table, block=block, section_keys=section_keys, result=result
        )
        if rendered is not None:
            return rendered

    header_row_indices = set(table.header_row_indices) if table is not None else set()
    return _render_static_grid(block, header_row_indices)


def _render_repeating_grid(
    *,
    table: ExtractedTable,
    block: CellGridBlock,
    section_keys: dict[str, str],
    result: UnitRenderResult,
) -> str | None:
    if len(table.columns) != block.col_count:
        result.warnings.append(
            f"table {table.table_id}: column count mismatch between extraction "
            f"({len(table.columns)}) and source grid ({block.col_count}); rendered as static"
        )
        return None

    header_rows = sorted(set(table.header_row_indices))
    all_rows = sorted({cell.row for cell in block.cells})
    data_rows = [r for r in all_rows if r not in header_rows]
    if not data_rows:
        result.warnings.append(
            f"table {table.table_id}: no data row found to template; rendered as static"
        )
        return None

    template_row_index = data_rows[0]
    section_key = section_keys.get(table.table_id, table.table_id)
    result.placed_section_ids.add(table.table_id)

    parts = ["<table>"]
    if header_rows:
        parts.append("<thead>")
        parts.extend(_render_static_row(block, row_index, header=True) for row_index in header_rows)
        parts.append("</thead>")

    section_id_attr = escape(table.table_id, quote=True)
    section_key_attr = escape(section_key, quote=True)
    parts.append(
        f'<tbody data-section-id="{section_id_attr}" data-section-key="{section_key_attr}">'
    )
    parts.append(_render_template_row(block, template_row_index, table, section_key))
    parts.append("</tbody>")
    parts.append("</table>")
    return "\n".join(parts)


def _render_template_row(
    block: CellGridBlock, row_index: int, table: ExtractedTable, section_key: str
) -> str:
    cells = sorted((c for c in block.cells if c.row == row_index), key=lambda c: c.col)
    cell_html: list[str] = []
    for cell in cells:
        column = table.columns[cell.col] if cell.col < len(table.columns) else None
        column_key = column.machine_key if column else f"col_{cell.col}"
        span_attrs = _span_attrs(cell.row_span, cell.col_span)
        column_key_attr = escape(column_key, quote=True)
        cell_html.append(
            f'<td data-column-key="{column_key_attr}"{span_attrs}>{escape(cell.text)}</td>'
        )

    section_id_attr = escape(table.table_id, quote=True)
    section_key_attr = escape(section_key, quote=True)
    return (
        f'<tr data-section-id="{section_id_attr}" data-section-key="{section_key_attr}" '
        f'data-repeating-row="true">{"".join(cell_html)}</tr>'
    )


def _render_static_grid(block: CellGridBlock, header_row_indices: set[int]) -> str:
    all_rows = sorted({cell.row for cell in block.cells})
    header_rows = [r for r in all_rows if r in header_row_indices]
    data_rows = [r for r in all_rows if r not in header_row_indices]

    parts = ["<table>"]
    if header_rows:
        parts.append("<thead>")
        parts.extend(_render_static_row(block, row_index, header=True) for row_index in header_rows)
        parts.append("</thead>")
    parts.append("<tbody>")
    parts.extend(_render_static_row(block, row_index, header=False) for row_index in data_rows)
    parts.append("</tbody>")
    parts.append("</table>")
    return "\n".join(parts)


def _render_static_row(block: CellGridBlock, row_index: int, *, header: bool) -> str:
    cells = sorted((c for c in block.cells if c.row == row_index), key=lambda c: c.col)
    tag = "th" if header else "td"
    cell_html = []
    for cell in cells:
        span_attrs = _span_attrs(cell.row_span, cell.col_span)
        cell_html.append(f"<{tag}{span_attrs}>{escape(cell.text)}</{tag}>")
    return f"<tr>{''.join(cell_html)}</tr>"


def _span_attrs(row_span: int, col_span: int) -> str:
    attrs = ""
    if row_span > 1:
        attrs += f' rowspan="{row_span}"'
    if col_span > 1:
        attrs += f' colspan="{col_span}"'
    return attrs


def _render_image_block(*, block: ImageBlock, result: UnitRenderResult) -> str:
    result.placed_asset_ids.add(block.asset_id)
    asset_id_attr = escape(block.asset_id, quote=True)
    return f'<img data-asset-id="{asset_id_attr}" alt="" width="{block.width}" height="{block.height}">'
