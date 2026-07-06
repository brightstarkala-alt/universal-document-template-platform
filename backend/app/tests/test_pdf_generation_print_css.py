from app.schemas.template import TemplateManifestPage
from app.services.pdf_generation import print_css


def test_render_print_css_includes_break_rules() -> None:
    css = print_css.render_print_css([])

    assert ".page { break-after: page; }" in css
    assert ".page:last-child { break-after: auto; }" in css
    assert "@page { margin: 0; }" in css


def test_render_print_css_uses_first_pt_page_size() -> None:
    pages = [
        TemplateManifestPage(
            unit_index=0, unit_type="page", unit_system="pt", width=612, height=792
        ),
        TemplateManifestPage(
            unit_index=1, unit_type="page", unit_system="pt", width=595, height=842
        ),
    ]

    css = print_css.render_print_css(pages)

    assert "size: 612.0pt 792.0pt;" in css
    # Only the first pt-sized page's dimensions are used (documented limitation).
    assert "595.0pt" not in css


def test_render_print_css_omits_size_when_no_pt_page_exists() -> None:
    pages = [
        TemplateManifestPage(unit_index=0, unit_type="sheet", unit_system="grid", row_count=5, col_count=3),
        TemplateManifestPage(unit_index=1, unit_type="page", unit_system="px", width=800, height=600),
    ]

    css = print_css.render_print_css(pages)

    assert "size:" not in css
    assert "@page { margin: 0; }" in css


def test_render_print_css_skips_pt_page_missing_dimensions() -> None:
    pages = [
        TemplateManifestPage(unit_index=0, unit_type="page", unit_system="pt", width=None, height=None),
        TemplateManifestPage(
            unit_index=1, unit_type="page", unit_system="pt", width=200, height=300
        ),
    ]

    css = print_css.render_print_css(pages)

    assert "size: 200.0pt 300.0pt;" in css
