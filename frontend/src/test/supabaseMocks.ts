import type { Session } from "@supabase/supabase-js";
import { vi } from "vitest";

/** Builds a minimally valid Supabase session for tests. */
export function mockSession(overrides: Partial<Session> = {}): Session {
  return {
    access_token: "test-access-token",
    refresh_token: "test-refresh-token",
    expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    token_type: "bearer",
    user: {
      id: "test-user-id",
      email: "test@example.com",
      app_metadata: {},
      user_metadata: {},
      aud: "authenticated",
      created_at: new Date().toISOString(),
    },
    ...overrides,
  } as Session;
}

/** Matches the shape `supabase.auth.onAuthStateChange` resolves to. */
export function mockAuthSubscription() {
  return {
    data: {
      subscription: {
        id: "test-subscription",
        callback: () => {},
        unsubscribe: vi.fn(),
      },
    },
  };
}
