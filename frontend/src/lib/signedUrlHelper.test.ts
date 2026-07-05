import { describe, it, expect, vi, beforeEach } from "vitest";
import { getSignedDownloadUrl } from "@/lib/signedUrlHelper";
import { fileApi } from "@/services/fileApi";

vi.mock("@/services/fileApi", () => ({
  fileApi: {
    getSignedUrl: vi.fn(),
  },
}));

describe("getSignedDownloadUrl", () => {
  beforeEach(() => {
    vi.mocked(fileApi.getSignedUrl).mockReset();
  });

  it("returns the url from the signed-url response", async () => {
    vi.mocked(fileApi.getSignedUrl).mockResolvedValue({
      url: "https://example.supabase.co/signed/file-1.pdf",
      expires_in: 300,
    });

    const url = await getSignedDownloadUrl("file-1");

    expect(fileApi.getSignedUrl).toHaveBeenCalledWith("file-1");
    expect(url).toBe("https://example.supabase.co/signed/file-1.pdf");
  });
});
