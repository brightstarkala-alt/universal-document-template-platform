import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { PreviewPage } from "@/routes/PreviewPage";
import { previewService } from "@/services/previewService";
import { ApiError } from "@/lib/apiClient";
import type { TemplatePreviewResponse } from "@udtp/shared";

vi.mock("@/services/previewService", () => ({
  previewService: {
    getLatestPreview: vi.fn(),
    getPreviewVersion: vi.fn(),
    refreshAssetUrl: vi.fn(),
  },
}));

const FAKE_PREVIEW: TemplatePreviewResponse = {
  artifact: {
    schema_version: "1.0",
    generator_version: "1.0",
    source_ai_extraction_id: "extraction-1",
    source_parsed_document_id: "parsed-1",
    version: 1,
    generated_at: "2026-01-01T00:00:00Z",
    html: '<section class="page"><span data-field-id="f1" data-machine-key="invoice_number">INV-1001</span></section>',
    css: "body { margin: 0; }",
    manifest: {
      pages: [],
      fields: [
        {
          field_id: "f1",
          machine_key: "invoice_number",
          display_label: "Invoice Number",
          type: "identifier",
          sample_value: "INV-1001",
          confidence: 0.9,
          confidence_tier: "high",
          unit_index: 0,
        },
      ],
      repeating_sections: [],
      assets: [],
      metadata: {
        source_format: "pdf",
        page_count: 1,
        sheet_count: 0,
        field_count: 1,
        section_count: 0,
        asset_count: 0,
        unmapped_field_count: 0,
        unmapped_section_count: 0,
        duration_ms: 1.0,
        warnings: [],
      },
    },
  },
  asset_urls: {},
};

function renderPreviewPage(fileId = "file-1") {
  return render(
    <MemoryRouter initialEntries={[`/files/${fileId}/preview`]}>
      <Routes>
        <Route path="/files/:fileId/preview" element={<PreviewPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PreviewPage", () => {
  it("shows a loading state while the preview is being fetched", () => {
    vi.mocked(previewService.getLatestPreview).mockReturnValue(new Promise(() => {}));

    renderPreviewPage();

    expect(screen.getByText(/loading preview/i)).toBeInTheDocument();
  });

  it("shows an error message when the preview fails to load", async () => {
    vi.mocked(previewService.getLatestPreview).mockRejectedValue(
      new ApiError(
        "This file's template has not finished generating yet.",
        "TEMPLATE_NOT_READY",
        400,
      ),
    );

    renderPreviewPage();

    await waitFor(() =>
      expect(screen.getByText(/has not finished generating yet/i)).toBeInTheDocument(),
    );
  });

  it("renders the preview iframe with the artifact's html and css assembled together", async () => {
    vi.mocked(previewService.getLatestPreview).mockResolvedValue(FAKE_PREVIEW);

    renderPreviewPage();

    const iframe = await screen.findByTitle("Template preview");
    const srcDoc = iframe.getAttribute("srcdoc") ?? "";
    expect(srcDoc).toContain('data-field-id="f1"');
    expect(srcDoc).toContain("body { margin: 0; }");
  });

  it("shows the inspector panel placeholder before any field is clicked", async () => {
    vi.mocked(previewService.getLatestPreview).mockResolvedValue(FAKE_PREVIEW);

    renderPreviewPage();

    expect(await screen.findByText(/click a highlighted field/i)).toBeInTheDocument();
  });

  it("shows a message when no file id is present in the route", () => {
    render(
      <MemoryRouter initialEntries={["/files//preview"]}>
        <Routes>
          <Route path="/files/:fileId/preview" element={<PreviewPage />} />
          <Route path="/files//preview" element={<PreviewPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText(/no file selected/i)).toBeInTheDocument();
  });
});
