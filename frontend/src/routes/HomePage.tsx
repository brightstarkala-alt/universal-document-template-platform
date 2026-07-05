import { useAuth } from "@/hooks/useAuth";

/**
 * Temporary placeholder landing route for Module 1.
 *
 * This is intentionally minimal — it exists only to prove the frontend
 * foundation (routing, Tailwind, TanStack Query, shared package import)
 * wires together end-to-end. The real application shell (left Variables
 * Panel / right Live Preview) is built in its own module.
 */
export function HomePage() {
  const { user, signOut } = useAuth();

  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-3 text-center">
      <h1 className="text-2xl font-bold text-gray-900">Universal Document Template Platform</h1>
      <p className="max-w-lg text-sm text-gray-500">
        Project foundation is up and running. Feature modules (auth, upload, template engine, live
        preview, PDF export) will be implemented incrementally.
      </p>
      {user?.email && <p className="text-sm text-gray-400">Signed in as {user.email}</p>}
      <button
        type="button"
        onClick={() => void signOut()}
        className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700"
      >
        Log out
      </button>
    </div>
  );
}
