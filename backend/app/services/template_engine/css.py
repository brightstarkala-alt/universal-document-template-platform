"""
Stylesheet assembly — Module 8, Stage D.

Deduplicated run-style classes plus physically-meaningful `@page`-equivalent
sizing per unit (real points for PDF/DOCX, pixels for a standalone image,
no fixed size at all for an XLSX sheet — see `TemplateManifestPage.unit_system`).
Never emits position/coordinate rules — layout comes from normal document
flow (semantic HTML + these rules), not pixel placement, per the project's
"never use coordinate overlays" rule.

Font names and colors originate from untrusted third-party documents
(same trust boundary Module 6's parsers already document) and are
sanitized before being embedded in generated CSS text.
"""

import re

from app.schemas.template import TemplateManifestPage
from app.services.template_engine.text_styles import RunStyle

_UNSAFE_CSS_CHARS = re.compile(r'["{};]')

_BASE_CSS = """
body { margin: 0; font-family: sans-serif; }
.page { margin: 0 auto 2rem auto; padding: 2rem; box-sizing: border-box; }
table { border-collapse: collapse; width: 100%; margin: 0.5rem 0; }
th, td { border: 1px solid #ccc; padding: 0.25rem 0.5rem; text-align: left; }
th { background: #f4f4f4; font-weight: bold; }
img { max-width: 100%; height: auto; }
p, h1, h2, h3, h4 { margin: 0.25rem 0; }
""".strip()


def render_stylesheet(style_classes: dict[RunStyle, str], pages: list[TemplateManifestPage]) -> str:
    rules = [_BASE_CSS]

    for style, class_name in style_classes.items():
        declarations = _declarations_for(style)
        if declarations:
            rules.append(f".{class_name} {{ {declarations} }}")

    for page in pages:
        page_rule = _page_size_rule(page)
        if page_rule:
            rules.append(page_rule)

    return "\n".join(rules)


def _declarations_for(style: RunStyle) -> str:
    parts: list[str] = []
    if style.font_family:
        parts.append(f'font-family: "{_sanitize(style.font_family)}", sans-serif;')
    if style.font_size:
        parts.append(f"font-size: {style.font_size}pt;")
    if style.bold:
        parts.append("font-weight: bold;")
    if style.italic:
        parts.append("font-style: italic;")
    if style.color:
        parts.append(f"color: {_sanitize(style.color)};")
    return " ".join(parts)


def _page_size_rule(page: TemplateManifestPage) -> str | None:
    if page.unit_system == "grid" or page.width is None or page.height is None:
        return None
    selector = f'.page[data-unit-index="{page.unit_index}"]'
    return f"{selector} {{ width: {page.width}{page.unit_system}; min-height: {page.height}{page.unit_system}; }}"


def _sanitize(value: str) -> str:
    return _UNSAFE_CSS_CHARS.sub("", value)
