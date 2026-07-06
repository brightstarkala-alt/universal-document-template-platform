import { describe, it, expect, vi, beforeEach } from "vitest";
import { pdfService } from "@/services/pdfService";
import { pdfApi } from "@/services/pdfApi";

vi.mock("@/services/pdfApi", () => ({
  pdfApi: {
    generate: vi.fn(),
    getLatest: vi.fn(),
    getVersions: vi.fn(),
    getVersion: vi.fn(),
    getSignedUrl: vi.fn(),
  },
}));

describe("pdfService", () => {
  beforeEach(() => {
    vi.mocked(pdfApi.generate).mockReset();
    vi.mocked(pdfApi.getLatest).mockReset();
    vi.mocked(pdfApi.getSignedUrl).mockReset();
  });

  it("generateLatest delegates to pdfApi.generate", async () => {
    vi.mocked(pdfApi.generate).mockResolvedValue({} as never);

    await pdfService.generateLatest("file-1");

    expect(pdfApi.generate).toHaveBeenCalledWith("file-1", false);
  });

  it("generateLatest forwards the force flag", async () => {
    vi.mocked(pdfApi.generate).mockResolvedValue({} as never);

    await pdfService.generateLatest("file-1", true);

    expect(pdfApi.generate).toHaveBeenCalledWith("file-1", true);
  });

  it("getLatestPdf delegates to pdfApi.getLatest", async () => {
    vi.mocked(pdfApi.getLatest).mockResolvedValue({} as never);

    await pdfService.getLatestPdf("file-1");

    expect(pdfApi.getLatest).toHaveBeenCalledWith("file-1");
  });

  it("getSignedUrl delegates to pdfApi.getSignedUrl", async () => {
    vi.mocked(pdfApi.getSignedUrl).mockResolvedValue({} as never);

    await pdfService.getSignedUrl("file-1", 2);

    expect(pdfApi.getSignedUrl).toHaveBeenCalledWith("file-1", 2);
  });
});
