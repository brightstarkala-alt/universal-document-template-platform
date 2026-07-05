import { useEffect, useState, type ReactNode } from "react";
import type { CurrentCompany } from "@udtp/shared";
import { apiClient, ApiError } from "@/lib/apiClient";
import { logger } from "@/lib/logger";
import { useAuth } from "@/hooks/useAuth";
import { CompanyContext, type CompanyContextValue } from "@/contexts/company-context";

/**
 * Resolves the authenticated user's company once a session exists, mirroring
 * the backend's Current User -> Current Company dependency chain. Rendered
 * inside `ProtectedRoute`, so a session is always present by the time this
 * mounts; it still guards on `isAuthLoading` in case of remounts.
 */
export function CompanyProvider({ children }: { children: ReactNode }) {
  const { session, isLoading: isAuthLoading } = useAuth();
  const [company, setCompany] = useState<CurrentCompany | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthLoading) return;

    if (!session) {
      setCompany(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    apiClient
      .get<CurrentCompany>("/companies/me")
      .then((data) => {
        if (!isMounted) return;
        setCompany(data);
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        const message = err instanceof ApiError ? err.message : "Failed to load company.";
        logger.error("Failed to load current company", { message });
        setCompany(null);
        setError(message);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [session, isAuthLoading]);

  const value: CompanyContextValue = { company, isLoading, error };

  return <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>;
}
