import { describe, it, expect, vi, beforeEach } from "vitest";
import { templateEngineService } from "@/services/templateEngineService";
import { templateEngineApi } from "@/services/templateEngineApi";
import type { TemplateMetadata } from "@udtp/shared";

vi.mock("@/services/templateEngineApi", () => ({
  templateEngineApi: {
    generate: vi.fn(),
    getLatest: vi.fn(),
    listVersions: vi.fn(),
    getVersion: vi.fn(),
  },
}));

const FAKE_TEMPLATE: TemplateMetadata = {
  id: "template-1",
  company_id: "company-1",
  file_id: "file-1",
  source_ai_extraction_id: "extraction-1",
  source_parsed_document_id: "parsed-1",
  version: 1,
  schema_version: "1.0",
  generator_version: "1.0",
  status: "completed",
  storage_path: "company-1/file-1/templates/1.0/1.0-v1-x.json",
  field_count: 3,
  section_count: 1,
  asset_count: 1,
  page_count: 1,
  duration_ms: 15.0,
  error_message: null,
  created_at: "2026-01-01T00:00:00Z",
};

describe("templateEngineService", () => {
  beforeEach(() => {
    vi.mocked(templateEngineApi.generate).mockReset();
    vi.mocked(templateEngineApi.getLatest).mockReset();
    vi.mocked(templateEngineApi.listVersions).mockReset();
    vi.mocked(templateEngineApi.getVersion).mockReset();
  });

  it("triggerGeneration delegates to templateEngineApi.generate", async () => {
    vi.mocked(templateEngineApi.generate).mockResolvedValue(FAKE_TEMPLATE);

    const result = await templateEngineService.triggerGeneration("file-1");

    expect(templateEngineApi.generate).toHaveBeenCalledWith("file-1", false);
    expect(result).toEqual(FAKE_TEMPLATE);
  });

  it("triggerGeneration forwards the force flag", async () => {
    vi.mocked(templateEngineApi.generate).mockResolvedValue(FAKE_TEMPLATE);

    await templateEngineService.triggerGeneration("file-1", true);

    expect(templateEngineApi.generate).toHaveBeenCalledWith("file-1", true);
  });

  it("getLatestTemplate delegates to templateEngineApi.getLatest", async () => {
    vi.mocked(templateEngineApi.getLatest).mockResolvedValue(FAKE_TEMPLATE);

    const result = await templateEngineService.getLatestTemplate("file-1");

    expect(templateEngineApi.getLatest).toHaveBeenCalledWith("file-1");
    expect(result).toEqual(FAKE_TEMPLATE);
  });

  it("listTemplateVersions delegates to templateEngineApi.listVersions", async () => {
    vi.mocked(templateEngineApi.listVersions).mockResolvedValue([FAKE_TEMPLATE]);

    const result = await templateEngineService.listTemplateVersions("file-1");

    expect(templateEngineApi.listVersions).toHaveBeenCalledWith("file-1");
    expect(result).toEqual([FAKE_TEMPLATE]);
  });

  it("getTemplateVersion delegates to templateEngineApi.getVersion", async () => {
    vi.mocked(templateEngineApi.getVersion).mockResolvedValue(FAKE_TEMPLATE);

    const result = await templateEngineService.getTemplateVersion("file-1", 1);

    expect(templateEngineApi.getVersion).toHaveBeenCalledWith("file-1", 1);
    expect(result).toEqual(FAKE_TEMPLATE);
  });
});
