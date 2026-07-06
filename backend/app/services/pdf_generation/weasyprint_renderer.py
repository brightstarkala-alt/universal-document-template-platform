"""
The only place in this codebase that imports the `weasyprint` SDK —
isolated behind one function, mirroring how `ai_extraction/openai_client.py`
isolates the OpenAI SDK. `weasyprint` requires native GTK/Pango/cairo
libraries that are not guaranteed to be present in every environment
(notably, plain Windows dev machines without them installed); importing
it lazily, inside this function rather than at module load time, keeps
the rest of Module 10 (and everything that transitively imports it, e.g.
the FastAPI app) importable and testable without that native runtime.
`pdf_generation_service` tests mock this function directly rather than
depending on WeasyPrint actually being installed.
"""


def render_pdf(*, html: str, stylesheets: list[str]) -> tuple[bytes, int]:
    from weasyprint import CSS, HTML  # intentionally lazy — see module docstring

    document = HTML(string=html).render(stylesheets=[CSS(string=sheet) for sheet in stylesheets])
    pdf_bytes = document.write_pdf()
    return pdf_bytes, len(document.pages)
