import { describe, it, expect, vi, beforeEach } from "vitest";
import { pdfApi } from "@/services/pdfApi";
import { apiClient } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("pdfApi", () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
    vi.mocked(apiClient.post).mockReset();
  });

  it("triggers generation via POST /files/:id/pdf", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    await pdfApi.generate("file-1");

    expect(apiClient.post).toHaveBeenCalledWith("/files/file-1/pdf");
  });

  it("appends ?force=true when forcing regeneration", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    await pdfApi.generate("file-1", true);

    expect(apiClient.post).toHaveBeenCalledWith("/files/file-1/pdf?force=true");
  });

  it("fetches the latest pdf metadata via GET /files/:id/pdf", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await pdfApi.getLatest("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/pdf");
  });

  it("fetches all versions via GET /files/:id/pdf/versions", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await pdfApi.getVersions("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/pdf/versions");
  });

  it("fetches a specific version via GET /files/:id/pdf/:version", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await pdfApi.getVersion("file-1", 2);

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/pdf/2");
  });

  it("fetches a signed url via GET /files/:id/pdf/signed-url", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await pdfApi.getSignedUrl("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/pdf/signed-url");
  });

  it("appends a version query param when requesting a signed url for a specific version", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await pdfApi.getSignedUrl("file-1", 2);

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/pdf/signed-url?version=2");
  });
});
