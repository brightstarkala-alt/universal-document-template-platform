import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import App from "@/App";
import { supabase } from "@/lib/supabaseClient";
import { apiClient } from "@/lib/apiClient";
import { mockSession, mockAuthSubscription } from "@/test/supabaseMocks";

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      onAuthStateChange: vi.fn(),
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
      resetPasswordForEmail: vi.fn(),
    },
  },
}));

vi.mock("@/lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/apiClient")>();
  return {
    ...actual,
    apiClient: { ...actual.apiClient, get: vi.fn() },
  };
});

describe("App", () => {
  beforeEach(() => {
    vi.mocked(supabase.auth.onAuthStateChange).mockReturnValue(mockAuthSubscription());
    vi.mocked(apiClient.get).mockResolvedValue({
      id: "company-1",
      name: "Acme Inc",
      slug: "acme",
      role: "owner",
    });
  });

  it("redirects unauthenticated visitors to the login page", async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    });

    render(<App />);

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /log in/i })).toBeInTheDocument(),
    );
  });

  it("renders the home page heading for an authenticated session", async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: mockSession() },
      error: null,
    });

    render(<App />);

    await waitFor(() =>
      expect(screen.getByText(/Universal Document Template Platform/i)).toBeInTheDocument(),
    );
  });
});
