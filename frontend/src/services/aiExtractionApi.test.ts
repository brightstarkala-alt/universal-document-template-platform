import { describe, it, expect, vi, beforeEach } from "vitest";
import { aiExtractionApi } from "@/services/aiExtractionApi";
import { apiClient } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("aiExtractionApi", () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
    vi.mocked(apiClient.post).mockReset();
  });

  it("triggers an extraction via POST /files/:id/extract", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    await aiExtractionApi.extract("file-1");

    expect(apiClient.post).toHaveBeenCalledWith("/files/file-1/extract");
  });

  it("appends ?force=true when forcing a re-extraction", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    await aiExtractionApi.extract("file-1", true);

    expect(apiClient.post).toHaveBeenCalledWith("/files/file-1/extract?force=true");
  });

  it("fetches the latest extraction via GET /files/:id/extracted", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await aiExtractionApi.getLatest("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/extracted");
  });

  it("fetches all versions via GET /files/:id/extracted/versions", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await aiExtractionApi.listVersions("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/extracted/versions");
  });

  it("fetches a specific version via GET /files/:id/extracted/:version", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await aiExtractionApi.getVersion("file-1", 2);

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/extracted/2");
  });
});
