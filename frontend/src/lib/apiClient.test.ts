import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "@/lib/apiClient";
import { supabase } from "@/lib/supabaseClient";
import { mockSession } from "@/test/supabaseMocks";

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
    },
  },
}));

describe("apiClient", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { ok: true } }),
      }),
    );
  });

  it("attaches a Bearer token when a session exists", async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: mockSession() },
      error: null,
    });

    await apiClient.get("/companies/me");

    const [, requestInit] = vi.mocked(fetch).mock.calls[0];
    const headers = requestInit?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer test-access-token");
  });

  it("omits the Authorization header when there is no session", async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    });

    await apiClient.get("/companies/me");

    const [, requestInit] = vi.mocked(fetch).mock.calls[0];
    const headers = requestInit?.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });
});
