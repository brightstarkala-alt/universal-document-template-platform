import { describe, it, expect, vi, beforeEach } from "vitest";
import { parserService } from "@/services/parserService";
import { parserApi } from "@/services/parserApi";
import type { ParsedDocumentMetadata } from "@udtp/shared";

vi.mock("@/services/parserApi", () => ({
  parserApi: {
    parse: vi.fn(),
    getLatest: vi.fn(),
  },
}));

const FAKE_PARSED_DOCUMENT: ParsedDocumentMetadata = {
  id: "parsed-1",
  company_id: "company-1",
  file_id: "file-1",
  schema_version: "1.0",
  parser_name: "image_parser",
  parser_version: "1.0.0",
  status: "completed",
  storage_path: "company-1/file-1/parsed/1.0/1.0.0-x.json",
  unit_count: 1,
  text_block_count: 0,
  image_count: 1,
  cell_grid_count: 0,
  cell_count: 0,
  character_count: 0,
  duration_ms: 12.3,
  error_message: null,
  created_at: "2026-01-01T00:00:00Z",
};

describe("parserService", () => {
  beforeEach(() => {
    vi.mocked(parserApi.parse).mockReset();
    vi.mocked(parserApi.getLatest).mockReset();
  });

  it("triggerParse delegates to parserApi.parse", async () => {
    vi.mocked(parserApi.parse).mockResolvedValue(FAKE_PARSED_DOCUMENT);

    const result = await parserService.triggerParse("file-1");

    expect(parserApi.parse).toHaveBeenCalledWith("file-1");
    expect(result).toEqual(FAKE_PARSED_DOCUMENT);
  });

  it("getParsedDocument delegates to parserApi.getLatest", async () => {
    vi.mocked(parserApi.getLatest).mockResolvedValue(FAKE_PARSED_DOCUMENT);

    const result = await parserService.getParsedDocument("file-1");

    expect(parserApi.getLatest).toHaveBeenCalledWith("file-1");
    expect(result).toEqual(FAKE_PARSED_DOCUMENT);
  });
});
