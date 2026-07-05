import { describe, it, expect, vi, beforeEach } from "vitest";
import { fileService } from "@/services/fileService";
import { fileApi } from "@/services/fileApi";
import type { FileMetadata } from "@udtp/shared";

vi.mock("@/services/fileApi", () => ({
  fileApi: {
    list: vi.fn(),
    get: vi.fn(),
    getSignedUrl: vi.fn(),
  },
}));

const FAKE_FILE: FileMetadata = {
  id: "file-1",
  company_id: "company-1",
  storage_bucket: "documents",
  storage_path: "company-1/file-1.pdf",
  original_filename: "invoice.pdf",
  content_type: "application/pdf",
  size_bytes: 1024,
  checksum_sha256: null,
  uploaded_by: "user-1",
  created_at: "2026-01-01T00:00:00Z",
};

describe("fileService", () => {
  beforeEach(() => {
    vi.mocked(fileApi.list).mockReset();
    vi.mocked(fileApi.get).mockReset();
  });

  it("listFiles delegates to fileApi.list", async () => {
    vi.mocked(fileApi.list).mockResolvedValue([FAKE_FILE]);

    const result = await fileService.listFiles();

    expect(fileApi.list).toHaveBeenCalled();
    expect(result).toEqual([FAKE_FILE]);
  });

  it("getFile delegates to fileApi.get", async () => {
    vi.mocked(fileApi.get).mockResolvedValue(FAKE_FILE);

    const result = await fileService.getFile("file-1");

    expect(fileApi.get).toHaveBeenCalledWith("file-1");
    expect(result).toEqual(FAKE_FILE);
  });
});
