import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { LoginPage } from "@/routes/auth/LoginPage";
import { useAuth } from "@/hooks/useAuth";

vi.mock("@/hooks/useAuth");

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<div>Home page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  it("submits credentials and navigates home on success", async () => {
    const signIn = vi.fn().mockResolvedValue({ error: null });
    vi.mocked(useAuth).mockReturnValue({
      session: null,
      user: null,
      isLoading: false,
      signIn,
      signOut: vi.fn(),
      requestPasswordReset: vi.fn(),
    });

    renderLoginPage();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "correct-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    expect(signIn).toHaveBeenCalledWith("test@example.com", "correct-password");
    await waitFor(() => expect(screen.getByText("Home page")).toBeInTheDocument());
  });

  it("shows an error message when sign in fails", async () => {
    const signIn = vi.fn().mockResolvedValue({ error: "Invalid login credentials" });
    vi.mocked(useAuth).mockReturnValue({
      session: null,
      user: null,
      isLoading: false,
      signIn,
      signOut: vi.fn(),
      requestPasswordReset: vi.fn(),
    });

    renderLoginPage();

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "wrong-password" } });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid login credentials");
  });

  it("redirects home immediately when already signed in", () => {
    vi.mocked(useAuth).mockReturnValue({
      session: {
        access_token: "token",
        refresh_token: "refresh",
        expires_in: 3600,
        expires_at: 0,
        token_type: "bearer",
        user: {
          id: "user-1",
          email: "test@example.com",
          app_metadata: {},
          user_metadata: {},
          aud: "authenticated",
          created_at: new Date().toISOString(),
        },
      },
      user: null,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      requestPasswordReset: vi.fn(),
    });

    renderLoginPage();

    expect(screen.getByText("Home page")).toBeInTheDocument();
  });
});
