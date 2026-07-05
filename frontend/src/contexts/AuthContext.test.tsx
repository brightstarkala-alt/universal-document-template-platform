import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { useContext } from "react";
import { AuthProvider } from "@/contexts/AuthContext";
import { AuthContext } from "@/contexts/auth-context";
import { supabase } from "@/lib/supabaseClient";
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

function Consumer() {
  const context = useContext(AuthContext);
  if (!context) return null;
  return (
    <div>
      <span data-testid="loading">{String(context.isLoading)}</span>
      <span data-testid="email">{context.user?.email ?? "none"}</span>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    });
    vi.mocked(supabase.auth.onAuthStateChange).mockReturnValue(mockAuthSubscription());
  });

  it("starts loading and resolves to no session", async () => {
    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("false"));
    expect(screen.getByTestId("email").textContent).toBe("none");
  });

  it("exposes the signed-in user once a session is loaded", async () => {
    const session = mockSession();
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session },
      error: null,
    });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("email").textContent).toBe(session.user.email));
  });

  it("returns an error message when sign in fails", async () => {
    vi.mocked(supabase.auth.signInWithPassword).mockResolvedValue({
      data: { user: null, session: null },
      error: { message: "Invalid login credentials", name: "AuthApiError", status: 400 },
    } as Awaited<ReturnType<typeof supabase.auth.signInWithPassword>>);

    let capturedError: string | null = null;
    function SignInTrigger() {
      const context = useContext(AuthContext);
      return (
        <button
          onClick={() =>
            void context?.signIn("test@example.com", "wrong-password").then(({ error }) => {
              capturedError = error;
            })
          }
        >
          sign in
        </button>
      );
    }

    render(
      <AuthProvider>
        <SignInTrigger />
      </AuthProvider>,
    );

    screen.getByText("sign in").click();

    await waitFor(() => expect(capturedError).toBe("Invalid login credentials"));
  });
});
