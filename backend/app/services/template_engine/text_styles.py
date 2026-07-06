"""
Text style deduplication — Module 8, Stage D (pre-pass).

Collects every distinct (font_family, font_size, bold, italic, color)
combination used across a document's `TextRun`s and assigns each a reusable
CSS class name, so the generated stylesheet has one rule per distinct style
rather than inline styling repeated on every run — the "clean, reusable
CSS" requirement.
"""

from collections import Counter
from dataclasses import dataclass

from app.schemas.document_model import TextBlock, TextRun, UniversalDocumentModel


@dataclass(frozen=True)
class RunStyle:
    font_family: str | None
    font_size: float | None
    bold: bool
    italic: bool
    color: str | None


def style_of(run: TextRun) -> RunStyle:
    return RunStyle(
        font_family=run.font_family,
        font_size=run.font_size,
        bold=run.bold,
        italic=run.italic,
        color=run.color,
    )


def collect_style_classes(udm: UniversalDocumentModel) -> dict[RunStyle, str]:
    styles: list[RunStyle] = []
    seen: set[RunStyle] = set()
    for unit in udm.units:
        for block in unit.blocks:
            if not isinstance(block, TextBlock):
                continue
            for run in block.runs:
                style = style_of(run)
                if style not in seen:
                    seen.add(style)
                    styles.append(style)
    return {style: f"run-{index}" for index, style in enumerate(styles)}


def dominant_style(block: TextBlock) -> RunStyle | None:
    """The most common style among a block's runs — a run matching this
    doesn't need its own wrapping span; a run that differs does."""
    if not block.runs:
        return None
    counts = Counter(style_of(run) for run in block.runs)
    return counts.most_common(1)[0][0]


def median_font_size(udm: UniversalDocumentModel) -> float | None:
    """Document-wide median run font size — the baseline a block's
    dominant font size is compared against to infer heading-ness
    (html_builder.py), since there's no explicit "this is a heading"
    signal anywhere upstream."""
    sizes = sorted(
        run.font_size
        for unit in udm.units
        for block in unit.blocks
        if isinstance(block, TextBlock)
        for run in block.runs
        if run.font_size is not None
    )
    if not sizes:
        return None
    mid = len(sizes) // 2
    if len(sizes) % 2 == 0:
        return (sizes[mid - 1] + sizes[mid]) / 2
    return sizes[mid]
