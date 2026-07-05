import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { useContext } from "react";
import { CompanyProvider } from "@/contexts/CompanyContext";
import { CompanyContext } from "@/contexts/company-context";
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

function Consumer() {
  const context = useContext(CompanyContext);
  if (!context) return null;
  return (
    <div>
      <span data-testid="loading">{String(context.isLoading)}</span>
      <span data-testid="company">{context.company?.name ?? "none"}</span>
      <span data-testid="error">{context.error ?? "none"}</span>
    </div>
  );
}

describe("CompanyProvider", () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
  });

  it("does not fetch and clears state when there is no session", async () => {
    vi.mocked(useAuth).mockReturnValue({
      session: null,
      user: null,
      isLoading: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      requestPasswordReset: vi.fn(),
    });

    render(
      <CompanyProvider>
        <Consumer />
      </CompanyProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("false"));
    expect(screen.getByTestId("company").textContent).toBe("none");
    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it("loads the company once a session exists", async () => {
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

    render(
      <CompanyProvider>
        <Consumer />
      </CompanyProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("company").textContent).toBe("Acme Inc"));
    expect(apiClient.get).toHaveBeenCalledWith("/companies/me");
  });

  it("exposes an error message when the company fetch fails", async () => {
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

    render(
      <CompanyProvider>
        <Consumer />
      </CompanyProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("error").textContent).toBe(
        "This account is not linked to a company.",
      ),
    );
  });
});
