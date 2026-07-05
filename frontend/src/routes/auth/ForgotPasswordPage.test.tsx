import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ForgotPasswordPage } from "@/routes/auth/ForgotPasswordPage";
import { useAuth } from "@/hooks/useAuth";

vi.mock("@/hooks/useAuth");

function renderForgotPasswordPage() {
  return render(
    <MemoryRouter>
      <ForgotPasswordPage />
    </MemoryRouter>,
  );
}

describe("ForgotPasswordPage", () => {
  it("submits the email and shows a confirmation message", async () => {
    const requestPasswordReset = vi.fn().mockResolvedValue({ error: null });
    vi.mocked(useAuth).mockReturnValue({
      session: null,
      user: null,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      requestPasswordReset,
    });

    renderForgotPasswordPage();

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(requestPasswordReset).toHaveBeenCalledWith("test@example.com");
    expect(await screen.findByText(/password reset link has been sent/i)).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    const requestPasswordReset = vi.fn().mockResolvedValue({ error: "Something went wrong" });
    vi.mocked(useAuth).mockReturnValue({
      session: null,
      user: null,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      requestPasswordReset,
    });

    renderForgotPasswordPage();

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong");
  });
});
