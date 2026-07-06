import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { PreviewPage } from "@/routes/PreviewPage";
import { previewService } from "@/services/previewService";
import { pdfService } from "@/services/pdfService";
import { triggerDownload } from "@/lib/downloadHelper";
import { ApiError } from "@/lib/apiClient";
import type { PDFMetadata, TemplatePreviewResponse } from "@udtp/shared";

vi.mock("@/services/previewService", () => ({
  previewService: {
    getLatestPreview: vi.fn(),
    getPreviewVersion: vi.fn(),
    refreshAssetUrl: vi.fn(),
  },
}));

vi.mock("@/services/pdfService", () => ({
  pdfService: {
    generateLatest: vi.fn(),
    getLatestPdf: vi.fn(),
    getSignedUrl: vi.fn(),
  },
}));

vi.mock("@/lib/downloadHelper", () => ({
  triggerDownload: vi.fn(),
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
  beforeEach(() => {
    vi.clearAllMocks();
  });

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

  it("generates and downloads a PDF when the Download PDF button is clicked", async () => {
    vi.mocked(previewService.getLatestPreview).mockResolvedValue(FAKE_PREVIEW);
    const fakePdf: PDFMetadata = {
      id: "pdf-1",
      company_id: "company-1",
      file_id: "file-1",
      source_template_id: "template-1",
      version: 3,
      schema_version: "1.0",
      generator_version: "1.0",
      status: "completed",
      storage_path: "company-1/file-1/pdfs/1.0-v3-x.pdf",
      page_count: 1,
      size_bytes: 100,
      duration_ms: 5.0,
      error_message: null,
      created_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(pdfService.generateLatest).mockResolvedValue(fakePdf);
    vi.mocked(pdfService.getSignedUrl).mockResolvedValue({
      url: "https://signed.example/document.pdf",
      expires_in: 300,
    });

    renderPreviewPage();

    const button = await screen.findByRole("button", { name: /download pdf/i });
    fireEvent.click(button);

    await waitFor(() => expect(triggerDownload).toHaveBeenCalledTimes(1));

    expect(pdfService.generateLatest).toHaveBeenCalledWith("file-1");
    expect(pdfService.getSignedUrl).toHaveBeenCalledWith("file-1", 3);
    expect(triggerDownload).toHaveBeenCalledWith(
      "https://signed.example/document.pdf",
      "document-v3.pdf",
    );
  });

  it("shows an error message when PDF generation fails", async () => {
    vi.mocked(previewService.getLatestPreview).mockResolvedValue(FAKE_PREVIEW);
    vi.mocked(pdfService.generateLatest).mockRejectedValue(
      new ApiError("This file's template has not finished generating yet.", "TEMPLATE_NOT_READY", 400),
    );

    renderPreviewPage();

    const button = await screen.findByRole("button", { name: /download pdf/i });
    fireEvent.click(button);

    await waitFor(() =>
      expect(screen.getByText(/has not finished generating yet/i)).toBeInTheDocument(),
    );
    expect(triggerDownload).not.toHaveBeenCalled();
  });
});
