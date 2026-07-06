"""
Print-pagination stylesheet — Module 10.

WeasyPrint renders paged media; the browser-facing Preview does not need
real page breaks (it scrolls through `.page` sections inside an iframe),
so Module 8's own stylesheet (app/services/template_engine/css.py) never
emits `@page`/break rules — only screen-box sizing. This module adds
exactly the paged-media rules WeasyPrint needs, as a second, separate
stylesheet passed alongside the artifact's own `css`. It is never merged
into, or persisted back onto, `TemplateArtifact.css`.

Page size is taken from the first `pt`-sized unit in the manifest (real
points — PDF/DOCX sources); `px` (image) and `grid` (XLSX) units have no
physical page size to honor, so no `size` is emitted and WeasyPrint falls
back to its default. A document whose units have genuinely different
page sizes will render every PDF page at the first unit's size — a
disclosed, documented limitation, not a bug.
"""

from app.schemas.template import TemplateManifestPage


def render_print_css(pages: list[TemplateManifestPage]) -> str:
    size_declaration = _page_size_declaration(pages)
    return (
        f"@page {{ margin: 0;{size_declaration} }}\n"
        ".page { break-after: page; }\n"
        ".page:last-child { break-after: auto; }"
    )


def _page_size_declaration(pages: list[TemplateManifestPage]) -> str:
    for page in pages:
        if page.unit_system == "pt" and page.width is not None and page.height is not None:
            return f" size: {page.width}pt {page.height}pt;"
    return ""
