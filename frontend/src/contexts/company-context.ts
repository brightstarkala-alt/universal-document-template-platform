import { createContext } from "react";
import type { CurrentCompany } from "@udtp/shared";

export interface CompanyContextValue {
  company: CurrentCompany | null;
  isLoading: boolean;
  error: string | null;
}

export const CompanyContext = createContext<CompanyContextValue | undefined>(undefined);
