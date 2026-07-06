import { describe, it, expect, vi, beforeEach } from "vitest";
import { templateEngineApi } from "@/services/templateEngineApi";
import { apiClient } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("templateEngineApi", () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
    vi.mocked(apiClient.post).mockReset();
  });

  it("triggers template generation via POST /files/:id/template", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    await templateEngineApi.generate("file-1");

    expect(apiClient.post).toHaveBeenCalledWith("/files/file-1/template");
  });

  it("appends ?force=true when forcing regeneration", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    await templateEngineApi.generate("file-1", true);

    expect(apiClient.post).toHaveBeenCalledWith("/files/file-1/template?force=true");
  });

  it("fetches the latest template via GET /files/:id/template", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await templateEngineApi.getLatest("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/template");
  });

  it("fetches all versions via GET /files/:id/template/versions", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await templateEngineApi.listVersions("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/template/versions");
  });

  it("fetches a specific version via GET /files/:id/template/:version", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await templateEngineApi.getVersion("file-1", 2);

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/template/2");
  });
});
