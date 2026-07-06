import { describe, it, expect, vi, beforeEach } from "vitest";
import { previewService } from "@/services/previewService";
import { previewApi } from "@/services/previewApi";
import type { TemplatePreviewResponse, SignedUrlResponse } from "@udtp/shared";

vi.mock("@/services/previewApi", () => ({
  previewApi: {
    getLatest: vi.fn(),
    getVersion: vi.fn(),
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
    html: '<section class="page">hello</section>',
    css: "body { margin: 0; }",
    manifest: {
      pages: [],
      fields: [],
      repeating_sections: [],
      assets: [],
      metadata: {
        source_format: "pdf",
        page_count: 1,
        sheet_count: 0,
        field_count: 0,
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

const FAKE_SIGNED_URL: SignedUrlResponse = { url: "https://signed.example/x.png", expires_in: 300 };

describe("previewService", () => {
  beforeEach(() => {
    vi.mocked(previewApi.getLatest).mockReset();
    vi.mocked(previewApi.getVersion).mockReset();
    vi.mocked(previewApi.refreshAssetUrl).mockReset();
  });

  it("getLatestPreview delegates to previewApi.getLatest", async () => {
    vi.mocked(previewApi.getLatest).mockResolvedValue(FAKE_PREVIEW);

    const result = await previewService.getLatestPreview("file-1");

    expect(previewApi.getLatest).toHaveBeenCalledWith("file-1");
    expect(result).toEqual(FAKE_PREVIEW);
  });

  it("getPreviewVersion delegates to previewApi.getVersion", async () => {
    vi.mocked(previewApi.getVersion).mockResolvedValue(FAKE_PREVIEW);

    const result = await previewService.getPreviewVersion("file-1", 1);

    expect(previewApi.getVersion).toHaveBeenCalledWith("file-1", 1);
    expect(result).toEqual(FAKE_PREVIEW);
  });

  it("refreshAssetUrl delegates to previewApi.refreshAssetUrl", async () => {
    vi.mocked(previewApi.refreshAssetUrl).mockResolvedValue(FAKE_SIGNED_URL);

    const result = await previewService.refreshAssetUrl("file-1", "asset-1");

    expect(previewApi.refreshAssetUrl).toHaveBeenCalledWith("file-1", "asset-1", undefined);
    expect(result).toEqual(FAKE_SIGNED_URL);
  });

  it("refreshAssetUrl forwards an explicit version", async () => {
    vi.mocked(previewApi.refreshAssetUrl).mockResolvedValue(FAKE_SIGNED_URL);

    await previewService.refreshAssetUrl("file-1", "asset-1", 2);

    expect(previewApi.refreshAssetUrl).toHaveBeenCalledWith("file-1", "asset-1", 2);
  });
});
