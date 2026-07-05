import { describe, it, expect, vi, beforeEach } from "vitest";
import { fileApi } from "@/services/fileApi";
import { apiClient } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

describe("fileApi", () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
  });

  it("lists files via GET /files", async () => {
    vi.mocked(apiClient.get).mockResolvedValue([]);

    await fileApi.list();

    expect(apiClient.get).toHaveBeenCalledWith("/files");
  });

  it("gets a single file via GET /files/:id", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await fileApi.get("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1");
  });

  it("gets a signed url via GET /files/:id/signed-url", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ url: "https://x", expires_in: 300 });

    await fileApi.getSignedUrl("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/signed-url");
  });
});
