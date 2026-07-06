import { describe, it, expect, vi, beforeEach } from "vitest";
import { previewApi } from "@/services/previewApi";
import { apiClient } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

describe("previewApi", () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
  });

  it("fetches the latest preview via GET /files/:id/preview", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await previewApi.getLatest("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/preview");
  });

  it("fetches a specific version via GET /files/:id/preview/:version", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await previewApi.getVersion("file-1", 2);

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/preview/2");
  });

  it("refreshes an asset url via GET .../preview/assets/:assetId/signed-url", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await previewApi.refreshAssetUrl("file-1", "asset-1");

    expect(apiClient.get).toHaveBeenCalledWith(
      "/files/file-1/preview/assets/asset-1/signed-url",
    );
  });

  it("appends a version query param when refreshing an asset url for a specific version", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await previewApi.refreshAssetUrl("file-1", "asset-1", 2);

    expect(apiClient.get).toHaveBeenCalledWith(
      "/files/file-1/preview/assets/asset-1/signed-url?version=2",
    );
  });
});
