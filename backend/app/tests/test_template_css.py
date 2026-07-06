from app.schemas.template import TemplateManifestPage
from app.services.template_engine.css import render_stylesheet
from app.services.template_engine.text_styles import RunStyle


def test_render_stylesheet_includes_base_rules() -> None:
    css = render_stylesheet({}, [])
    assert "table { border-collapse: collapse" in css


def test_render_stylesheet_emits_a_rule_per_style_class() -> None:
    style = RunStyle(font_family="Arial", font_size=14.0, bold=True, italic=False, color="#ff0000")
    css = render_stylesheet({style: "run-0"}, [])

    assert ".run-0 {" in css
    assert "font-size: 14.0pt;" in css
    assert "font-weight: bold;" in css
    assert "color: #ff0000;" in css


def test_render_stylesheet_sanitizes_unsafe_font_family_characters() -> None:
    style = RunStyle(
        font_family='Arial"; } body { display:none',
        font_size=None,
        bold=False,
        italic=False,
        color=None,
    )
    css = render_stylesheet({style: "run-0"}, [])

    rule_start = css.index(".run-0 {")
    rule_end = css.index("}", rule_start) + 1
    rule = css[rule_start:rule_end]

    # The malicious input tried to close the quoted value, close the rule,
    # and open a new `body { ... }` rule. Our own wrapper contributes
    # exactly one `{`/`}` pair and one pair of quotes around the
    # font-family value — any more means the injection escaped sanitizing.
    assert rule.count("{") == 1
    assert rule.count("}") == 1
    assert rule.count('"') == 2


def test_render_stylesheet_emits_physical_page_size_for_pt_and_px_units() -> None:
    pages = [
        TemplateManifestPage(
            unit_index=0, unit_type="page", unit_system="pt", width=612, height=792
        ),
        TemplateManifestPage(
            unit_index=1, unit_type="page", unit_system="px", width=800, height=600
        ),
    ]
    css = render_stylesheet({}, pages)

    assert '.page[data-unit-index="0"] { width: 612.0pt; min-height: 792.0pt; }' in css
    assert '.page[data-unit-index="1"] { width: 800.0px; min-height: 600.0px; }' in css


def test_render_stylesheet_skips_size_rule_for_grid_pages() -> None:
    pages = [
        TemplateManifestPage(
            unit_index=0, unit_type="sheet", unit_system="grid", row_count=5, col_count=3
        )
    ]
    css = render_stylesheet({}, pages)

    assert "data-unit-index" not in css
