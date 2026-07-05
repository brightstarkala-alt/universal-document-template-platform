import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";
import { apiClient, ApiError } from "@/lib/apiClient";
import { mockSession } from "@/test/supabaseMocks";

vi.mock("@/hooks/useAuth");
vi.mock("@/lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/apiClient")>();
  return {
    ...actual,
    apiClient: { ...actual.apiClient, get: vi.fn() },
  };
});

function renderProtected(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<div>Protected content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("shows a loading state while the session is resolving", () => {
    vi.mocked(useAuth).mockReturnValue({
      session: null,
      user: null,
      isLoading: true,
      signIn: vi.fn(),
      signOut: vi.fn(),
      requestPasswordReset: vi.fn(),
    });

    renderProtected();

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("redirects to /login when there is no session", () => {
    vi.mocked(useAuth).mockReturnValue({
      session: null,
      user: null,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      requestPasswordReset: vi.fn(),
    });

    renderProtected();

    expect(screen.getByText("Login page")).toBeInTheDocument();
  });

  it("renders the nested route once the company has loaded", async () => {
    const session = mockSession();
    vi.mocked(useAuth).mockReturnValue({
      session,
      user: session.user,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      requestPasswordReset: vi.fn(),
    });
    vi.mocked(apiClient.get).mockResolvedValue({
      id: "company-1",
      name: "Acme Inc",
      slug: "acme",
      role: "owner",
    });

    renderProtected();

    await waitFor(() => expect(screen.getByText("Protected content")).toBeInTheDocument());
  });

  it("shows an error state when the account has no company", async () => {
    const session = mockSession();
    vi.mocked(useAuth).mockReturnValue({
      session,
      user: session.user,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      requestPasswordReset: vi.fn(),
    });
    vi.mocked(apiClient.get).mockRejectedValue(
      new ApiError("This account is not linked to a company.", "NO_COMPANY_MEMBERSHIP", 403),
    );

    renderProtected();

    await waitFor(() => expect(screen.getByText(/not linked to a company/i)).toBeInTheDocument());
  });
});
