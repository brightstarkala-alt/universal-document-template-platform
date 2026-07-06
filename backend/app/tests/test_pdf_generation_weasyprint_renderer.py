"""
Real, end-to-end WeasyPrint smoke test. `pdf_generation_service`'s own
tests mock `weasyprint_renderer.render_pdf` entirely (see
test_pdf_generation_service.py) so they don't depend on WeasyPrint's
native GTK/Pango/cairo runtime being installed. This test exercises the
real thing, and self-skips in an environment (such as a plain Windows
dev machine) where those native libraries are absent — it should run for
real in CI/production, where they are.
"""

import pytest

from app.services.pdf_generation.weasyprint_renderer import render_pdf


def test_render_pdf_produces_real_pdf_bytes() -> None:
    try:
        pdf_bytes, page_count = render_pdf(
            html='<section class="page">hello</section>',
            stylesheets=["body { margin: 0; }", "@page { margin: 0; }"],
        )
    except OSError:
        pytest.skip(
            "WeasyPrint native libraries (GTK/Pango/cairo) are not installed "
            "in this environment"
        )
        return

    assert pdf_bytes.startswith(b"%PDF")
    assert page_count == 1
