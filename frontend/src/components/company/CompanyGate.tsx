import type { ReactNode } from "react";
import { useCompany } from "@/hooks/useCompany";

/**
 * Blocks rendering of tenant-scoped content until the current company has
 * resolved. Sits inside `ProtectedRoute`, which already guarantees a
 * session exists — this only concerns itself with the User -> Company step.
 * No company creation/switching UI here by design (out of scope for this
 * module); an account with no company just sees the error state below.
 */
export function CompanyGate({ children }: { children: ReactNode }) {
  const { company, isLoading, error } = useCompany();

  if (isLoading) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <p className="text-sm text-gray-500">Loading company…</p>
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <p className="max-w-md text-center text-sm text-red-600">
          {error ?? "Your account is not yet linked to a company. Contact your administrator."}
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
