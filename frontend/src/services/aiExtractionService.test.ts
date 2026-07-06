import { describe, it, expect, vi, beforeEach } from "vitest";
import { aiExtractionService } from "@/services/aiExtractionService";
import { aiExtractionApi } from "@/services/aiExtractionApi";
import type { AIExtractionMetadata } from "@udtp/shared";

vi.mock("@/services/aiExtractionApi", () => ({
  aiExtractionApi: {
    extract: vi.fn(),
    getLatest: vi.fn(),
    listVersions: vi.fn(),
    getVersion: vi.fn(),
  },
}));

const FAKE_EXTRACTION: AIExtractionMetadata = {
  id: "extraction-1",
  company_id: "company-1",
  file_id: "file-1",
  parsed_document_id: "parsed-1",
  version: 1,
  schema_version: "1.0",
  source_checksum_sha256: "checksum-abc",
  model: "gpt-4o-mini",
  prompt_version: "2026-07-06.1",
  status: "completed",
  storage_path: "company-1/file-1/extracted/1.0/2026-07-06.1-v1-x.json",
  field_count: 3,
  table_count: 1,
  low_confidence_count: 0,
  prompt_tokens: 120,
  completion_tokens: 40,
  duration_ms: 850.0,
  error_message: null,
  created_at: "2026-01-01T00:00:00Z",
};

describe("aiExtractionService", () => {
  beforeEach(() => {
    vi.mocked(aiExtractionApi.extract).mockReset();
    vi.mocked(aiExtractionApi.getLatest).mockReset();
    vi.mocked(aiExtractionApi.listVersions).mockReset();
    vi.mocked(aiExtractionApi.getVersion).mockReset();
  });

  it("triggerExtraction delegates to aiExtractionApi.extract", async () => {
    vi.mocked(aiExtractionApi.extract).mockResolvedValue(FAKE_EXTRACTION);

    const result = await aiExtractionService.triggerExtraction("file-1");

    expect(aiExtractionApi.extract).toHaveBeenCalledWith("file-1", false);
    expect(result).toEqual(FAKE_EXTRACTION);
  });

  it("triggerExtraction forwards the force flag", async () => {
    vi.mocked(aiExtractionApi.extract).mockResolvedValue(FAKE_EXTRACTION);

    await aiExtractionService.triggerExtraction("file-1", true);

    expect(aiExtractionApi.extract).toHaveBeenCalledWith("file-1", true);
  });

  it("getLatestExtraction delegates to aiExtractionApi.getLatest", async () => {
    vi.mocked(aiExtractionApi.getLatest).mockResolvedValue(FAKE_EXTRACTION);

    const result = await aiExtractionService.getLatestExtraction("file-1");

    expect(aiExtractionApi.getLatest).toHaveBeenCalledWith("file-1");
    expect(result).toEqual(FAKE_EXTRACTION);
  });

  it("listExtractionVersions delegates to aiExtractionApi.listVersions", async () => {
    vi.mocked(aiExtractionApi.listVersions).mockResolvedValue([FAKE_EXTRACTION]);

    const result = await aiExtractionService.listExtractionVersions("file-1");

    expect(aiExtractionApi.listVersions).toHaveBeenCalledWith("file-1");
    expect(result).toEqual([FAKE_EXTRACTION]);
  });

  it("getExtractionVersion delegates to aiExtractionApi.getVersion", async () => {
    vi.mocked(aiExtractionApi.getVersion).mockResolvedValue(FAKE_EXTRACTION);

    const result = await aiExtractionService.getExtractionVersion("file-1", 1);

    expect(aiExtractionApi.getVersion).toHaveBeenCalledWith("file-1", 1);
    expect(result).toEqual(FAKE_EXTRACTION);
  });
});
