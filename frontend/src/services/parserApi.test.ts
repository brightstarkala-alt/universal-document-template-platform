import { describe, it, expect, vi, beforeEach } from "vitest";
import { parserApi } from "@/services/parserApi";
import { apiClient } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("parserApi", () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
    vi.mocked(apiClient.post).mockReset();
  });

  it("triggers a parse via POST /files/:id/parse", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    await parserApi.parse("file-1");

    expect(apiClient.post).toHaveBeenCalledWith("/files/file-1/parse");
  });

  it("fetches the latest parse via GET /files/:id/parsed", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    await parserApi.getLatest("file-1");

    expect(apiClient.get).toHaveBeenCalledWith("/files/file-1/parsed");
  });
});
