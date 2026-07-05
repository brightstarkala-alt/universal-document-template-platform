import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { CompanyProvider } from "@/contexts/CompanyContext";
import { CompanyGate } from "@/components/company/CompanyGate";

/**
 * Gate for authenticated-only routes. Rendered as a layout route in
 * `App.tsx` so every nested route requires a session without repeating this
 * check in each page component.
 *
 * Once a session exists, it also resolves the Current User -> Current
 * Company step: nested routes only render once a company has loaded.
 */
export function ProtectedRoute() {
  const { session, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <p className="text-sm text-gray-500">Loading…</p>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <CompanyProvider>
      <CompanyGate>
        <Outlet />
      </CompanyGate>
    </CompanyProvider>
  );
}
