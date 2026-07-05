import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";
import { mockSession } from "@/test/supabaseMocks";

vi.mock("@/hooks/useAuth");

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

  it("renders the nested route when a session exists", () => {
    const session = mockSession();
    vi.mocked(useAuth).mockReturnValue({
      session,
      user: session.user,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      requestPasswordReset: vi.fn(),
    });

    renderProtected();

    expect(screen.getByText("Protected content")).toBeInTheDocument();
  });
});
